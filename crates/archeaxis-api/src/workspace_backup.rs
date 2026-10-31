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

// v1 has one fixed-width SHA per actual SQLite source row. This budget grows
// with the verified artifact, never a count supplied by an untrusted manifest.
// Both the producer and every reader use it; no fixed library-size cutoff.
fn manifest_budget(source_count: u64, database_bytes: u64) -> rusqlite::Result<u64> {
    let by_rows = source_count.checked_mul(128);
    let by_file = database_bytes.checked_mul(4);
    by_rows
        .zip(by_file)
        .and_then(|(rows, bytes)| rows.min(bytes).checked_add(16 * 1024))
        .ok_or(rusqlite::Error::InvalidQuery)
}

fn verified_manifest(root: &Path, id: &str) -> rusqlite::Result<serde_json::Value> {
    let filename = format!("{id}.sqlite");
    let artifact = root.join(&filename);
    let (sha, bytes) = digest(&artifact)?;
    let snapshot = rusqlite::Connection::open_with_flags(
        artifact.canonicalize().map_err(io)?,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )?;
    // A forged view/virtual table must not supply an unbounded or recursive
    // source-count query. The canonical v1 inventory uses ordinary b-tree tables.
    for table in ["sources", "workspace_meta"] {
        let ordinary: bool = snapshot.query_row(
            "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE name=?1 AND type='table' AND rootpage>0)",
            [table], |r| r.get(0),
        )?;
        if !ordinary {
            return Err(rusqlite::Error::InvalidQuery);
        }
    }
    let count: i64 = snapshot.query_row("SELECT count(*) FROM sources", [], |r| r.get(0))?;
    let count = u64::try_from(count).map_err(|_| rusqlite::Error::InvalidQuery)?;
    let budget = manifest_budget(count, bytes)?;
    let mut file = regular_file(&root.join(format!("{filename}.manifest.json")))?;
    let length = file.metadata().map_err(io)?.len();
    if length > budget {
        return Err(rusqlite::Error::InvalidQuery);
    }
    let value: serde_json::Value = serde_json::from_reader(std::io::BufReader::new(
        Read::by_ref(&mut file).take(budget + 1),
    ))
    .map_err(|_| rusqlite::Error::InvalidQuery)?;
    let schema: String = snapshot.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'",
        [],
        |r| r.get(0),
    )?;
    if file.metadata().map_err(io)?.len() != length
        || value["schema"] != "archeaxis-core-backup-1"
        || value["backup_id"] != id
        || value["filename"] != filename
        || value["sha256"] != sha
        || value["bytes"] != bytes
        || value["schema_version"] != schema
        || value["sqlite_version"].as_str().is_none()
    {
        return Err(rusqlite::Error::InvalidQuery);
    }
    let sources = value["source_sha_list"]
        .as_array()
        .ok_or(rusqlite::Error::InvalidQuery)?;
    if u64::try_from(sources.len()).ok() != Some(count) {
        return Err(rusqlite::Error::InvalidQuery);
    }
    let mut statement = snapshot.prepare("SELECT sha256 FROM sources ORDER BY sha256")?;
    for (index, actual) in statement
        .query_map([], |r| r.get::<_, String>(0))?
        .enumerate()
    {
        let actual = actual?;
        if !hex(&actual, 64) || sources[index].as_str() != Some(actual.as_str()) {
            return Err(rusqlite::Error::InvalidQuery);
        }
    }
    Ok(value)
}

pub(crate) async fn list(State(state): State<AppState>) -> Response {
    crate::with_store(state, |conn| {
        let result = (|| -> rusqlite::Result<serde_json::Value> {
            let directory = directory(conn)?;
            archeaxis_store_sqlite::raw_objects::reject_links(&directory)?;
            if !directory.exists() {
                return Ok(json!({"backups":[], "unavailable_backups":[]}));
            }
            let mut results = Vec::new();
            let mut unavailable = Vec::new();
            for entry in std::fs::read_dir(&directory).map_err(io)? {
                let entry = entry.map_err(io)?;
                let filename = entry.file_name().to_string_lossy().into_owned();
                let Some(id) = filename.strip_suffix(".sqlite") else {
                    continue;
                };
                if !hex(id, 32) {
                    continue;
                }
                match verified_manifest(&directory, id) {
                    Ok(value) => results.push(value),
                    Err(_) => unavailable.push(json!({"backup_id":id,"filename":filename,
                        "code":"AAK-BACKUP-INVALID",
                        "message":"Backup manifest, database identity or source inventory could not be verified; this backup was preserved."})),
                }
            }
            results.sort_by_key(|v| v["backup_id"].as_str().unwrap().to_owned());
            unavailable.sort_by_key(|v| v["backup_id"].as_str().unwrap().to_owned());
            Ok(json!({"backups":results,"unavailable_backups":unavailable}))
        })();
        match result {
            Ok(backups) => Json(backups).into_response(),
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
            let encoded=serde_json::to_vec_pretty(&receipt).map_err(|_|rusqlite::Error::InvalidQuery)?;
            if encoded.len() as u64 > manifest_budget(receipt["source_sha_list"].as_array().unwrap().len() as u64,bytes)? {return Err(rusqlite::Error::InvalidQuery);}
            let manifest=directory.join(format!("{filename}.manifest.json"));
            let staging=directory.join(format!(".{backup_id}.manifest.tmp"));
            let mut staged=std::fs::OpenOptions::new().create_new(true).write(true).open(&staging).map_err(io)?;
            staged.write_all(&encoded).map_err(io)?;
            staged.sync_all().map_err(io)?;
            drop(staged);
            archeaxis_domain::backup::publish_backup_file_noclobber(&staging,&manifest)?;
            Ok(receipt)
        })();
        match result {Ok(receipt)=>(StatusCode::CREATED,Json(receipt)).into_response(),Err(error)=>(StatusCode::INTERNAL_SERVER_ERROR,Json(json!({"code":"AAK-BACKUP-001","message":error.to_string()}))).into_response()}
    }).await
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PreviewRequest {
    pub backup_id: String,
    pub expected_sha256: String,
}

/// Version 2 recovery contract; v1 create/list remains byte-compatible.
pub(crate) async fn preview(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<PreviewRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    if !hex(&body.backup_id, 32) || !hex(&body.expected_sha256, 64) {
        return StatusCode::BAD_REQUEST.into_response();
    }
    crate::with_store(state, move |conn| {
        let result=(|| -> rusqlite::Result<serde_json::Value> {
            let root=directory(conn)?;
            archeaxis_store_sqlite::raw_objects::reject_links(&root)?;
            let filename=format!("{}.sqlite",body.backup_id);
            let artifact=root.join(&filename);
            let manifest=verified_manifest(&root,&body.backup_id)?;
            let sha=manifest["sha256"].as_str().ok_or(rusqlite::Error::InvalidQuery)?;
            if sha!=body.expected_sha256 { return Err(rusqlite::Error::InvalidQuery); }
            archeaxis_domain::backup::preview(&artifact)?;
            let snapshot=rusqlite::Connection::open_with_flags(artifact.canonicalize().map_err(io)?,rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
            let schema:String=snapshot.query_row("SELECT value FROM workspace_meta WHERE key='schema_version'",[],|r|r.get(0))?;
            let source_sha_list=snapshot.prepare("SELECT sha256 FROM sources ORDER BY sha256")?.query_map([],|r|r.get::<_,String>(0))?.collect::<rusqlite::Result<Vec<_>>>()?;
            if manifest["schema_version"]!=schema || manifest["source_sha_list"]!=json!(source_sha_list) {return Err(rusqlite::Error::InvalidQuery);}
            Ok(json!({"schema":"archeaxis.workspace-restore-preview/v2","backup_id":body.backup_id,"sha256":sha,"schema_version":schema,"source_count":source_sha_list.len(),"compatible":true,"verified":true}))
        })();
        match result {Ok(value)=>Json(value).into_response(),Err(_)=>(StatusCode::CONFLICT,Json(json!({"code":"AAK-RESTORE-PREFLIGHT-409","message":"Backup identity, schema, integrity or CAS verification failed; current workspace was not changed."}))).into_response()}
    }).await
}
