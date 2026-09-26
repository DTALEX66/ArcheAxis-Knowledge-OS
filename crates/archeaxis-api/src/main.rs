//! archeaxis-api standalone server (the process a Supervisor starts).
//!
//! Usage: archeaxis-api <workspace-db-path> [port]
//! Requires a <=4096-byte launch JSON on stdin, closed by the parent within 5s.
//! See packages/contracts/v1/protocol-mapping.md (native launch slice).
//! Port defaults to 47831 (override with ARCHAXIS_VNEXT_PORT).
//! Serves the vNext local HTTP API on 127.0.0.1 — the handshake target for the
//! Avalonia Supervisor (sidecar-protocol versioned envelope is the message
//! contract; /api/v1/system/version is the first exchange).

use std::net::{Ipv4Addr, SocketAddr};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

async fn run_maintenance(action: &str, database: &Path, artifact: &Path) -> Result<serde_json::Value, String> {
    if !database.is_file() {
        return Err("workspace database does not exist".into());
    }
    archeaxis_store_sqlite::raw_objects::reject_links(database)
        .map_err(|error| error.to_string())?;
    archeaxis_store_sqlite::raw_objects::reject_links(artifact)
        .map_err(|error| error.to_string())?;
    let store = archeaxis_store_sqlite::writer::Store::open(database)
        .map_err(|error| error.to_string())?;
    let database = database.canonicalize().map_err(|error| error.to_string())?;
    let artifact = if artifact.is_absolute() {
        artifact.to_owned()
    } else {
        std::env::current_dir()
            .map_err(|error| error.to_string())?
            .join(artifact)
    };
    if artifact.exists() && database == artifact.canonicalize().map_err(|error| error.to_string())? {
        return Err("database and maintenance artifact must be different files".into());
    }
    match action {
        "backup" => {
            let target = artifact.to_string_lossy().into_owned();
            let result = store.submit(move |connection| {
                let version = connection.query_row(
                    "SELECT value FROM workspace_meta WHERE key='schema_version'",
                    [],
                    |row| row.get::<_, String>(0),
                )?;
                archeaxis_domain::backup::backup(connection, &target)?;
                Ok::<_, rusqlite::Error>(version)
            })
                .await
                .map_err(|error| error.to_string())?
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "ok": true,
                "action": "backup",
                "database": database,
                "backup": artifact,
                "schema_version": result,
                "objects_directory": format!("{}.objects", artifact.display()),
            }))
        }
        "restore" => {
            if !artifact.is_file() {
                return Err("backup file does not exist".into());
            }
            let canonical_artifact = artifact.canonicalize().map_err(|error| error.to_string())?;
            if database == canonical_artifact {
                return Err("database cannot be restored from itself".into());
            }
            let stamp = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_err(|error| error.to_string())?
                .as_nanos();
            let name = database.file_name().ok_or("database path has no file name")?.to_string_lossy();
            let preserved = database.with_file_name(format!("{name}.pre-restore-{stamp}.sqlite"));
            let preserved_text = preserved.to_string_lossy().into_owned();
            store.submit(move |connection| archeaxis_domain::backup::backup(connection, &preserved_text))
                .await
                .map_err(|error| error.to_string())?
                .map_err(|error| error.to_string())?;

            let snapshot = canonical_artifact.to_string_lossy().into_owned();
            let restored = store.submit(move |connection| {
                archeaxis_domain::backup::restore(&snapshot, connection)?;
                let snapshot = rusqlite::Connection::open_with_flags(
                    &snapshot,
                    rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
                )?;
                archeaxis_domain::backup::verify_counts(&snapshot, connection)
            })
            .await
            .map_err(|error| error.to_string())?;
            let restore_error = match restored {
                Ok(true) => None,
                Ok(false) => Some("restored workspace does not match the backup".to_owned()),
                Err(error) => Some(error.to_string()),
            };
            if let Some(error) = restore_error {
                let rollback_snapshot = preserved.to_string_lossy().into_owned();
                let rollback = store.submit(move |connection| {
                    archeaxis_domain::backup::restore(&rollback_snapshot, connection)?;
                    let previous = rusqlite::Connection::open_with_flags(
                        &rollback_snapshot,
                        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
                    )?;
                    archeaxis_domain::backup::verify_counts(&previous, connection)
                })
                .await
                .map_err(|rollback| format!("restore failed: {error}; rollback scheduling failed: {rollback}"))?
                .map_err(|rollback| format!("restore failed: {error}; rollback failed: {rollback}"))?;
                if !rollback {
                    return Err(format!("restore failed: {error}; rollback verification failed"));
                }
                return Ok(serde_json::json!({
                    "ok": false,
                    "action": "restore",
                    "error": error,
                    "database": database,
                    "backup": canonical_artifact,
                    "preserved_previous": preserved,
                    "rolled_back": true,
                }));
            }
            Ok(serde_json::json!({
                "ok": true,
                "action": "restore",
                "database": database,
                "backup": canonical_artifact,
                "preserved_previous": preserved,
                "preserved_objects_directory": format!("{}.objects", preserved.display()),
                "verified": true,
            }))
        }
        _ => Err("unsupported maintenance action".into()),
    }
}

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    if let Some(mode) = args.get(1).and_then(|arg| arg.strip_prefix("--maintenance-")) {
        if args.len() != 4 || !matches!(mode, "backup" | "restore") {
            eprintln!("usage: archeaxis-api --maintenance-backup|--maintenance-restore <workspace-db-path> <artifact-path>");
            std::process::exit(2);
        }
        match run_maintenance(mode, Path::new(&args[2]), Path::new(&args[3])).await {
            Ok(receipt) => {
                let ok = receipt.get("ok").and_then(serde_json::Value::as_bool).unwrap_or(false);
                println!("{}", receipt);
                if !ok {
                    std::process::exit(1);
                }
            }
            Err(error) => {
                println!("{}", serde_json::json!({"ok": false, "action": mode, "error": error}));
                std::process::exit(1);
            }
        }
        return;
    }
    if args.len() < 2 {
        eprintln!("usage: archeaxis-api <workspace-db-path> [port]");
        std::process::exit(2);
    }
    let db_path = &args[1];
    let port: u16 = args
        .get(2)
        .and_then(|p| p.parse().ok())
        .or_else(|| {
            std::env::var("ARCHAXIS_VNEXT_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
        })
        .unwrap_or(47831);

    let launch=match archeaxis_api::launch::Launch::from_stdin(){
        Ok(launch)=>launch,
        Err(message)=>{eprintln!("{message}");std::process::exit(2);}
    };
    let (store,router)=if let Some(profile)=&launch.text_worker {
        match archeaxis_application::executor::Executor::open(std::path::Path::new(db_path),&profile.staging,&profile.python,&profile.script).await {
            Ok(executor)=>(executor.store().clone(),archeaxis_api::runtime::router(executor)),
            Err(_)=>{eprintln!("failed to initialize execution workspace");std::process::exit(1);}
        }
    }else{
        match archeaxis_store_sqlite::writer::Store::open(std::path::Path::new(db_path)) {
            Ok(store)=>(store.clone(),archeaxis_api::projections(store,false)),
            Err(_)=>{eprintln!("failed to open workspace");std::process::exit(1);}
        }
    };
    let router=match archeaxis_api::launch::protect(router,&store,launch).await {
        Ok(router)=>router,Err(_)=>{eprintln!("workspace identity unavailable");std::process::exit(1);}
    };
    let addr = SocketAddr::from((Ipv4Addr::LOCALHOST, port));
    let listener = match tokio::net::TcpListener::bind(addr).await {
        Ok(l) => l,
        Err(e) => {
            eprintln!("cannot bind {addr}: {e}");
            std::process::exit(1);
        }
    };
    let bound_addr = listener.local_addr().expect("bound listener address");
    println!("archeaxis-api ready on http://{bound_addr}");
    axum::serve(listener, router).await.unwrap();
}
