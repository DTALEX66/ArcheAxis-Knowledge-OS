//! Open-format archive for a vNext workspace: JSONL per table + sha256
//! manifest + restore into a fresh database (FK-order aware).

use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::Write;
use std::path::Path;

/// Tables exported in FK-safe order (parents first).
pub const EXPORT_TABLES: &[&str] = &[
    "sources",
    "transforms",
    "anchors",
    "knowledge",
    "review_events",
    "learning_events",
    "jobs",
];

#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq)]
pub struct ArchiveManifest {
    pub tables: BTreeMap<String, TableFile>,
    pub manifest_sha256: String,
}

#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq)]
pub struct TableFile {
    pub rows: u64,
    pub sha256: String,
}

#[derive(Debug)]
pub enum ArchiveError {
    Sql(rusqlite::Error),
    Io(std::io::Error),
    Json(serde_json::Error),
    Table(String),
}

impl std::fmt::Display for ArchiveError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ArchiveError::Sql(e) => write!(f, "sql: {e}"),
            ArchiveError::Io(e) => write!(f, "io: {e}"),
            ArchiveError::Json(e) => write!(f, "json: {e}"),
            ArchiveError::Table(t) => write!(f, "table: {t}"),
        }
    }
}

impl From<rusqlite::Error> for ArchiveError {
    fn from(e: rusqlite::Error) -> Self {
        ArchiveError::Sql(e)
    }
}

fn column_names(conn: &Connection, table: &str) -> Result<Vec<String>, ArchiveError> {
    let mut stmt = conn.prepare(&format!("SELECT name FROM pragma_table_info('{table}')"))?;
    Ok(stmt
        .query_map([], |r| r.get(0))?
        .collect::<Result<Vec<String>, _>>()?)
}

fn row_to_json(row: &rusqlite::Row, cols: &[String]) -> Result<serde_json::Value, ArchiveError> {
    let mut obj = serde_json::Map::new();
    for (i, col) in cols.iter().enumerate() {
        let v = match row.get_ref(i)? {
            rusqlite::types::ValueRef::Null => serde_json::Value::Null,
            rusqlite::types::ValueRef::Integer(x) => serde_json::Value::from(x),
            rusqlite::types::ValueRef::Real(x) => serde_json::Value::from(x),
            rusqlite::types::ValueRef::Text(x) => {
                serde_json::Value::String(String::from_utf8_lossy(x).into_owned())
            }
            rusqlite::types::ValueRef::Blob(b) => serde_json::Value::String(hex::encode(b)),
        };
        obj.insert(col.clone(), v);
    }
    Ok(serde_json::Value::Object(obj))
}

/// Export every EXPORT_TABLES table of a vNext DB to JSONL in `out_dir`.
/// `manifest.json` captures per-table rows + sha256; `manifest_sha256` is the
/// digest over the whole manifest map (stable order).
pub fn export_workspace(db_path: &str, out_dir: &str) -> Result<ArchiveManifest, ArchiveError> {
    let conn = Connection::open_with_flags(db_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    std::fs::create_dir_all(out_dir).map_err(ArchiveError::Io)?;
    let mut manifest = ArchiveManifest::default();
    let mut file_hashes: BTreeMap<String, String> = BTreeMap::new();
    for table in EXPORT_TABLES {
        let cols = column_names(&conn, table)?;
        if cols.is_empty() {
            return Err(ArchiveError::Table(format!("missing table {table}")));
        }
        let path = Path::new(out_dir).join(format!("{table}.jsonl"));
        let mut fh = std::fs::File::create(&path).map_err(ArchiveError::Io)?;
        let mut stmt = conn.prepare(&format!("SELECT * FROM \"{table}\""))?;
        let mut rows = stmt.query([])?;
        let mut count = 0u64;
        while let Some(row) = rows.next()? {
            writeln!(fh, "{}", row_to_json(row, &cols)?).map_err(ArchiveError::Io)?;
            count += 1;
        }
        fh.flush().map_err(ArchiveError::Io)?;
        let bytes = std::fs::read(&path).map_err(ArchiveError::Io)?;
        let mut h = Sha256::new();
        h.update(&bytes);
        let digest = hex::encode(h.finalize());
        file_hashes.insert(table.to_string(), digest.clone());
        manifest.tables.insert(
            table.to_string(),
            TableFile {
                rows: count,
                sha256: digest,
            },
        );
    }
    let mut h = Sha256::new();
    for (t, tf) in &manifest.tables {
        h.update(t.as_bytes());
        h.update(tf.rows.to_le_bytes());
        h.update(tf.sha256.as_bytes());
    }
    manifest.manifest_sha256 = hex::encode(h.finalize());
    let mp = Path::new(out_dir).join("manifest.json");
    std::fs::write(&mp, serde_json::to_string_pretty(&manifest).unwrap())
        .map_err(ArchiveError::Io)?;
    Ok(manifest)
}

/// Restore JSONL files from `archive_dir` into a fresh vNext workspace DB.
/// Insert order follows EXPORT_TABLES so foreign keys hold.
pub fn restore_workspace(
    archive_dir: &str,
    target_db: &str,
) -> Result<ArchiveManifest, ArchiveError> {
    let conn = archeaxis_store_sqlite::init_workspace(target_db)?;
    let mp = Path::new(archive_dir).join("manifest.json");
    let raw = std::fs::read_to_string(&mp).map_err(ArchiveError::Io)?;
    let manifest: ArchiveManifest = serde_json::from_str(&raw).map_err(ArchiveError::Json)?;
    for table in EXPORT_TABLES {
        let tf = manifest
            .tables
            .get(*table)
            .ok_or_else(|| ArchiveError::Table(table.to_string()))?;
        if tf.rows == 0 {
            continue;
        }
        let path = Path::new(archive_dir).join(format!("{table}.jsonl"));
        let content = std::fs::read_to_string(&path).map_err(ArchiveError::Io)?;
        let cols = column_names(&conn, table)?;
        let placeholders = vec!["?"; cols.len()].join(",");
        let sql = format!(
            "INSERT INTO \"{table}\" ({}) VALUES ({placeholders})",
            cols.join(",")
        );
        let mut stmt = conn.prepare(&sql)?;
        for line in content.lines() {
            let v: serde_json::Value = serde_json::from_str(line).map_err(ArchiveError::Json)?;
            let obj = v
                .as_object()
                .ok_or_else(|| ArchiveError::Table("row not object".into()))?;
            let mut params: Vec<rusqlite::types::Value> = Vec::new();
            for c in &cols {
                params.push(json_to_value(
                    obj.get(c).cloned().unwrap_or(serde_json::Value::Null),
                ));
            }
            stmt.execute(rusqlite::params_from_iter(params.iter()))?;
        }
    }
    Ok(manifest)
}

fn json_to_value(v: serde_json::Value) -> rusqlite::types::Value {
    match v {
        serde_json::Value::Null => rusqlite::types::Value::Null,
        serde_json::Value::Bool(b) => rusqlite::types::Value::Integer(b as i64),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                rusqlite::types::Value::Integer(i)
            } else if let Some(f) = n.as_f64() {
                rusqlite::types::Value::Real(f)
            } else {
                rusqlite::types::Value::Null
            }
        }
        serde_json::Value::String(s) => rusqlite::types::Value::Text(s),
        serde_json::Value::Array(_) | serde_json::Value::Object(_) => rusqlite::types::Value::Null,
    }
}
