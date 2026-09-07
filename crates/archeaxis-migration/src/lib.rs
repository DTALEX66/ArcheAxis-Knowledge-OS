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
    Json(serde_json::Error),
}

impl std::fmt::Display for MigrationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MigrationError::Sql(e) => write!(f, "sql: {e}"),
            MigrationError::Io(e) => write!(f, "io: {e}"),
            MigrationError::Json(e) => write!(f, "json: {e}"),
        }
    }
}

impl From<rusqlite::Error> for MigrationError {
    fn from(e: rusqlite::Error) -> Self {
        MigrationError::Sql(e)
    }
}

impl From<serde_json::Error> for MigrationError {
    fn from(e: serde_json::Error) -> Self {
        MigrationError::Json(e)
    }
}


// ---------- X10 bounded demo: semantic staging of a declared fixture set -----
// This is a DEMO mapping slice, not a claim of full legacy coverage. C04
// fixes: legal knowledge_type PERSONAL_DEFINITION (contract vocabulary),
// exported-file hash/row-count verification before any write, one staging
// transaction (atomic; late errors roll back), honest inserted/reused counts,
// and a stable legacy-row mapping embedded in created_by so equal bodies from
// different legacy rows are not collapsed.


#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq)]
pub struct DemoStageResult {
    pub notes_seen: u64,
    pub notes_inserted: u64,
    pub notes_reused: u64,
    pub notes_row_errors: u64,
    pub docs_loss_rows: u64,
    pub other_unmapped_tables: Vec<String>,
    pub losses: Vec<String>,
}

fn hex_sha256_bytes(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    hex::encode(h.finalize())
}

/// Verify every exported table file against the manifest (hash + row count).
fn verify_export(export_dir: &str, manifest: &ExportManifest) -> Result<(), MigrationError> {
    for (name, table) in &manifest.tables {
        let path = Path::new(export_dir).join(format!("{name}.jsonl"));
        let bytes = std::fs::read(&path).map_err(MigrationError::Io)?;
        if hex_sha256_bytes(&bytes) != table.sha256 {
            return Err(MigrationError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("{name}.jsonl hash mismatch"),
            )));
        }
        let lines = bytes.iter().filter(|b| **b == b'\n').count() as u64;
        if lines != table.rows {
            return Err(MigrationError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("{name}.jsonl row count mismatch"),
            )));
        }
    }
    Ok(())
}

/// Read an exported JSONL table and stage its rows into vNext `knowledge` as
/// PERSONAL_DEFINITION candidates inside one staging transaction. Every row is
/// keyed by its legacy id (embedded in created_by), so identical bodies from
/// different legacy rows are distinct and re-runs are idempotent
/// (INSERT OR IGNORE; ignored rows count as reused, never as new inserts).
pub fn stage_demo_semantic_import(
    export_dir: &str,
    staging_db: &str,
) -> Result<DemoStageResult, MigrationError> {
    let manifest_path = Path::new(export_dir).join("export-manifest.json");
    let manifest_raw = std::fs::read_to_string(&manifest_path).map_err(MigrationError::Io)?;
    let manifest: ExportManifest =
        serde_json::from_str(&manifest_raw).map_err(MigrationError::Json)?;
    verify_export(export_dir, &manifest)?;

    let mut conn = archeaxis_store_sqlite::init_workspace(staging_db).map_err(MigrationError::Sql)?;
    let tx = conn
        .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)
        .map_err(MigrationError::Sql)?;
    let mut result = DemoStageResult::default();
    let mut leftover: Vec<String> = manifest.tables.keys().cloned().collect();

    if let Some(note_table) = manifest.tables.get("notes") {
        leftover.retain(|t| t != "notes");
        result.notes_seen = note_table.rows;
        let path = Path::new(export_dir).join("notes.jsonl");
        let raw = std::fs::read_to_string(&path).map_err(MigrationError::Io)?;
        for (i, line) in raw.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let row: serde_json::Value =
                serde_json::from_str(line).map_err(MigrationError::Json)?;
            let body = row.get("body").and_then(serde_json::Value::as_str);
            let legacy_id = row
                .get("id")
                .and_then(serde_json::Value::as_i64)
                .map(|v| v.to_string())
                .unwrap_or_else(|| format!("line{}", i + 1));
            match body {
                Some(text) if !text.trim().is_empty() => {
                    let kind = "PERSONAL_DEFINITION";
                    let created_by = format!("legacy_migration_demo:notes:{legacy_id}");
                    let kid = demo_knowledge_id(kind, text, &created_by);
                    let changed = tx
                        .execute(
                            "INSERT OR IGNORE INTO knowledge
                               (knowledge_id, knowledge_type, body, status, evidence_status,
                                anchor_id, created_by, receipt_hash)
                             VALUES(?1,?2,?3,'candidate',NULL,NULL,?4,?5)",
                            rusqlite::params![
                                kid,
                                kind,
                                text,
                                created_by,
                                demo_receipt(kind, text, "candidate")
                            ],
                        )
                        .map_err(MigrationError::Sql)?;
                    if changed > 0 {
                        result.notes_inserted += 1;
                    } else {
                        result.notes_reused += 1;
                    }
                }
                _ => {
                    result.notes_row_errors += 1;
                    result.losses.push(format!(
                        "notes line {}: empty/non-string body, not staged",
                        i + 1
                    ));
                }
            }
        }
        result.losses.push(
            "notes.created_at (legacy) is not carried: vNext knowledge records its own import time"
                .to_string(),
        );
    } else if manifest.tables.contains_key("notes") {
        result
            .losses
            .push("notes: exported with 0 rows; nothing staged".to_string());
    }

    if let Some(docs) = manifest.tables.get("docs") {
        leftover.retain(|t| t != "docs");
        result.docs_loss_rows = docs.rows;
        result.losses.push(
            "docs: exported rows are metadata-only (title/sha256), no byte content to become a vNext source; mapped to loss ledger"
                .to_string(),
        );
    }

    for table in &leftover {
        result.losses.push(format!(
            "{table}: unmapped demo table, preserved in export, not staged"
        ));
    }
    result.other_unmapped_tables = leftover;
    tx.commit().map_err(MigrationError::Sql)?;
    drop(conn);
    Ok(result)
}

fn demo_knowledge_id(kind: &str, body: &str, created_by: &str) -> String {
    format!("k_{}", &hex_sha256_bytes(format!("{kind}|{body}|{created_by}").as_bytes())[..24])
}

fn demo_receipt(kind: &str, body: &str, status: &str) -> String {
    hex_sha256_bytes(format!("{kind}|{body}|{status}|").as_bytes())
}
