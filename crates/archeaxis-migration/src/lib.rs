//! Legacy migration tooling (v0.6.14 -> vNext), read-only on the legacy side.
//!
//! Contract (PROJECT_CONTRACT.yaml): consistent snapshot -> read-only export ->
//! Rust dry-run -> staging import -> diff -> human confirmation. This crate
//! implements export + dry-run: it never writes to the legacy database and it
//! never dual-writes.

use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::Write;
use std::path::Path;

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TableSummary {
    pub name: String,
    pub row_count: i64,
    pub columns: Vec<String>,
}

/// Inventory user tables of a legacy DB (read-only; excludes sqlite internals).
pub fn inventory(db_path: &str) -> rusqlite::Result<Vec<TableSummary>> {
    let conn = Connection::open_with_flags(db_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    let mut stmt = conn.prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'knowledge_fts%' ORDER BY name",
    )?;
    let names: Vec<String> = stmt
        .query_map([], |r| r.get(0))?
        .collect::<Result<_, _>>()?;
    let mut out = Vec::new();
    for name in names {
        let count: i64 = conn.query_row(&format!("SELECT count(*) FROM \"{name}\""), [], |r| {
            r.get(0)
        })?;
        let cols: Vec<String> = conn
            .prepare(&format!("SELECT name FROM pragma_table_info('{name}')"))?
            .query_map([], |r| r.get(0))?
            .collect::<Result<_, _>>()?;
        out.push(TableSummary {
            name,
            row_count: count,
            columns: cols,
        });
    }
    Ok(out)
}

/// Export every user table to JSONL in `out_dir`; returns per-table files with
/// a content manifest. One line per row (JSON object of column -> value).
pub fn export_jsonl(db_path: &str, out_dir: &str) -> Result<ExportManifest, MigrationError> {
    let conn = Connection::open_with_flags(db_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    std::fs::create_dir_all(out_dir).map_err(MigrationError::Io)?;
    let summary = inventory(db_path).map_err(MigrationError::Sql)?;
    let mut files = BTreeMap::new();
    let mut manifest = ExportManifest {
        exported_at_unix: 0,
        tables: BTreeMap::new(),
        manifest_sha256: String::new(),
    };
    for t in &summary {
        if t.row_count == 0 {
            continue;
        }
        let path = Path::new(out_dir).join(format!("{}.jsonl", t.name));
        let mut fh = std::fs::File::create(&path).map_err(MigrationError::Io)?;
        let mut rows = conn
            .prepare(&format!("SELECT * FROM \"{}\"", t.name))
            .map_err(MigrationError::Sql)?;
        let mut row_iter = rows.query([]).map_err(MigrationError::Sql)?;
        let mut lines = 0u64;
        while let Some(row) = row_iter.next().map_err(MigrationError::Sql)? {
            let mut obj = serde_json::Map::new();
            for (i, col) in t.columns.iter().enumerate() {
                let v = match row.get_ref(i).map_err(MigrationError::Sql)? {
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
            writeln!(fh, "{}", serde_json::Value::Object(obj)).map_err(MigrationError::Io)?;
            lines += 1;
        }
        fh.flush().map_err(MigrationError::Io)?;
        let bytes = std::fs::read(&path).map_err(MigrationError::Io)?;
        let mut h = Sha256::new();
        h.update(&bytes);
        let digest = hex::encode(h.finalize());
        files.insert(t.name.clone(), (lines, digest.clone()));
        manifest.tables.insert(
            t.name.clone(),
            TableExport {
                rows: lines,
                sha256: digest,
            },
        );
    }
    // manifest digest over the file map (stable ordering via BTreeMap)
    let mut h = Sha256::new();
    for (name, (lines, digest)) in &files {
        h.update(name.as_bytes());
        h.update(lines.to_le_bytes());
        h.update(digest.as_bytes());
    }
    manifest.manifest_sha256 = hex::encode(h.finalize());
    let mpath = Path::new(out_dir).join("export-manifest.json");
    std::fs::write(&mpath, serde_json::to_string_pretty(&manifest).unwrap())
        .map_err(MigrationError::Io)?;
    Ok(manifest)
}

#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq)]
pub struct TableExport {
    pub rows: u64,
    pub sha256: String,
}

#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq)]
pub struct ExportManifest {
    pub exported_at_unix: u64,
    pub tables: BTreeMap<String, TableExport>,
    #[serde(default)]
    pub manifest_sha256: String,
}

#[derive(Debug)]
pub enum MigrationError {
    Sql(rusqlite::Error),
    Io(std::io::Error),
}

impl std::fmt::Display for MigrationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MigrationError::Sql(e) => write!(f, "sql: {e}"),
            MigrationError::Io(e) => write!(f, "io: {e}"),
        }
    }
}

impl From<rusqlite::Error> for MigrationError {
    fn from(e: rusqlite::Error) -> Self {
        MigrationError::Sql(e)
    }
}
