//! Human-only consistent snapshot on the already-owned canonical writer.
use crate::AppState;
use axum::{
    Json,
    extract::State,
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    io::{Read, Write},
    path::{Path, PathBuf},
};

fn io(error: std::io::Error) -> rusqlite::Error {
    rusqlite::Error::ToSqlConversionFailure(Box::new(error))
}
fn directory(conn: &rusqlite::Connection) -> rusqlite::Result<PathBuf> {
    Ok(Path::new(conn.path().ok_or(rusqlite::Error::InvalidQuery)?)
        .parent()
        .ok_or(rusqlite::Error::InvalidQuery)?
        .join("backups"))
}
fn digest(path: &Path) -> rusqlite::Result<(String, u64)> {
    archeaxis_store_sqlite::raw_objects::reject_links(path)?;
    let mut file = regular_file(path)?;
    let bytes = file.metadata().map_err(io)?.len();
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let count = file.read(&mut buffer).map_err(io)?;
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
    }
    Ok((format!("{:x}", hash.finalize()), bytes))
}
fn hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn regular_file(path: &Path) -> rusqlite::Result<std::fs::File> {
    archeaxis_store_sqlite::raw_objects::reject_links(path)?;
    let file = std::fs::File::open(path).map_err(io)?;
    if !file.metadata().map_err(io)?.is_file() {
        return Err(rusqlite::Error::InvalidQuery);
    }
    Ok(file)
}

pub(crate) async fn list(State(state): State<AppState>) -> Response {
    crate::with_store(state, |conn| {
        let result = (|| -> rusqlite::Result<Vec<serde_json::Value>> {
            let directory = directory(conn)?;
            archeaxis_store_sqlite::raw_objects::reject_links(&directory)?;
            if !directory.exists() {
                return Ok(Vec::new());
            }
            let mut results = Vec::new();
            for entry in std::fs::read_dir(&directory).map_err(io)? {
                let entry = entry.map_err(io)?;
                let filename = entry.file_name().to_string_lossy().into_owned();
                let Some(id) = filename.strip_suffix(".sqlite") else {
                    continue;
                };
                if !hex(id, 32) {
                    continue;
                }
                let manifest = directory.join(format!("{filename}.manifest.json"));
                if !manifest.exists() {
                    continue;
                }
                archeaxis_store_sqlite::raw_objects::reject_links(&manifest)?;
                let file = regular_file(&manifest)?;
                if file.metadata().map_err(io)?.len() > 1024 * 1024 {
                    return Err(rusqlite::Error::InvalidQuery);
                }
                let value: serde_json::Value =
                    serde_json::from_reader(file).map_err(|_| rusqlite::Error::InvalidQuery)?;
                if value["schema"] != "archeaxis-core-backup-1"
                    || value["backup_id"] != id
                    || value["filename"] != filename
                    || value["schema_version"].as_str().is_none()
                    || value["sqlite_version"].as_str().is_none()
                    || value["source_sha_list"].as_array().is_none_or(|v| {
                        v.iter().any(|sha| sha.as_str().is_none_or(|s| !hex(s, 64)))
                    })
                {
                    return Err(rusqlite::Error::InvalidQuery);
                }
                let (sha, bytes) = digest(&entry.path())?;
                if value["sha256"] != sha || value["bytes"] != bytes {
                    return Err(rusqlite::Error::InvalidQuery);
                }
                results.push(value);
            }
            results.sort_by_key(|v| v["backup_id"].as_str().unwrap().to_owned());
            Ok(results)
        })();
        match result {
            Ok(backups) => Json(json!({"backups":backups})).into_response(),
            Err(error) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"code":"AAK-BACKUP-002","message":error.to_string()})),
            )
                .into_response(),
        }
    })
    .await
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Empty {}

pub(crate) async fn create(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(_): Json<Empty>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state,|conn| {
        let result=(|| -> rusqlite::Result<serde_json::Value> {
            let directory=directory(conn)?;
            archeaxis_store_sqlite::raw_objects::reject_links(&directory)?;
            if !directory.exists() {
                std::fs::create_dir(&directory).map_err(|error|rusqlite::Error::ToSqlConversionFailure(Box::new(error)))?;
            }
            archeaxis_store_sqlite::raw_objects::reject_links(&directory)?;
            let backup_id:String=conn.query_row("SELECT lower(hex(randomblob(16)))",[],|r|r.get(0))?;
            let filename=format!("{backup_id}.sqlite");
            let artifact=directory.join(&filename);
            archeaxis_domain::backup::backup(conn,artifact.to_str().ok_or(rusqlite::Error::InvalidQuery)?)?;
            let snapshot=rusqlite::Connection::open_with_flags(artifact.canonicalize().map_err(|error|rusqlite::Error::ToSqlConversionFailure(Box::new(error)))?,rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
            if !archeaxis_domain::backup::verify_counts(conn,&snapshot)? {return Err(rusqlite::Error::InvalidQuery);}
            let schema_version:String=snapshot.query_row("SELECT value FROM workspace_meta WHERE key='schema_version'",[],|r|r.get(0))?;
            let sqlite_version:String=snapshot.query_row("SELECT sqlite_version()",[],|r|r.get(0))?;
            let source_sha_list=snapshot.prepare("SELECT sha256 FROM sources ORDER BY sha256")?.query_map([],|r|r.get::<_,String>(0))?.collect::<rusqlite::Result<Vec<_>>>()?;
            let (sha256,bytes)=digest(&artifact)?;
            let receipt=json!({"schema":"archeaxis-core-backup-1","backup_id":backup_id,"filename":filename,"sha256":sha256,"bytes":bytes,"schema_version":schema_version,"sqlite_version":sqlite_version,"source_sha_list":source_sha_list,"verified":true});
            let manifest=directory.join(format!("{filename}.manifest.json"));
            let staging=directory.join(format!(".{backup_id}.manifest.tmp"));
            let mut staged=std::fs::OpenOptions::new().create_new(true).write(true).open(&staging).map_err(io)?;
            staged.write_all(serde_json::to_string_pretty(&receipt).map_err(|_|rusqlite::Error::InvalidQuery)?.as_bytes()).map_err(io)?;
            staged.sync_all().map_err(io)?;
            drop(staged);
            std::fs::hard_link(&staging,&manifest).map_err(io)?;
            std::fs::remove_file(&staging).map_err(io)?;
            Ok(receipt)
        })();
        match result {Ok(receipt)=>(StatusCode::CREATED,Json(receipt)).into_response(),Err(error)=>(StatusCode::INTERNAL_SERVER_ERROR,Json(json!({"code":"AAK-BACKUP-001","message":error.to_string()}))).into_response()}
    }).await
}
