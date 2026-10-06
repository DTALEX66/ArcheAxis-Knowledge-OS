//! Legacy migration tooling (v0.6.14 -> vNext), read-only on the legacy side.
//!
//! Contract (PROJECT_CONTRACT.yaml): consistent snapshot -> read-only export ->
//! Rust dry-run -> staging import -> diff -> human confirmation. This crate
//! implements export + dry-run: it never writes to the legacy database and it
//! never dual-writes.

use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::Write;
use std::path::Path;

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TableSummary {
    pub name: String,
    pub row_count: i64,
    pub columns: Vec<String>,
}

fn quote_identifier(name: &str) -> String {
    format!("\"{}\"", name.replace('"', "\"\""))
}

fn export_filename(name: &str) -> String {
    let is_plain = !name.starts_with("__table_")
        && !name.is_empty()
        && name
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-');
    if is_plain {
        format!("{name}.jsonl")
    } else {
        format!("__table_{}.jsonl", hex::encode(name.as_bytes()))
    }
}

fn manifest_digest(tables: &BTreeMap<String, TableExport>) -> String {
    let mut h = Sha256::new();
    for (name, table) in tables {
        h.update(name.as_bytes());
        h.update(table.rows.to_le_bytes());
        h.update(table.sha256.as_bytes());
    }
    hex::encode(h.finalize())
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
        let count: i64 = conn.query_row(
            &format!("SELECT count(*) FROM {}", quote_identifier(&name)),
            [],
            |r| r.get(0),
        )?;
        let cols: Vec<String> = conn
            .prepare("SELECT name FROM pragma_table_info(?1)")?
            .query_map([&name], |r| r.get(0))?
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
    let mut manifest = ExportManifest {
        exported_at_unix: 0,
        tables: BTreeMap::new(),
        manifest_sha256: String::new(),
    };
    for t in &summary {
        let path = Path::new(out_dir).join(export_filename(&t.name));
        let mut fh = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)
            .map_err(MigrationError::Io)?;
        let mut rows = conn
            .prepare(&format!("SELECT * FROM {}", quote_identifier(&t.name)))
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
        manifest.tables.insert(
            t.name.clone(),
            TableExport {
                rows: lines,
                sha256: digest,
            },
        );
    }
    manifest.manifest_sha256 = manifest_digest(&manifest.tables);
    let mpath = Path::new(out_dir).join("export-manifest.json");
    let mut manifest_file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&mpath)
        .map_err(MigrationError::Io)?;
    manifest_file
        .write_all(serde_json::to_string_pretty(&manifest)?.as_bytes())
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
    pub attachments_loss_rows: u64,
    pub links_loss_rows: u64,
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
    if manifest.manifest_sha256 != manifest_digest(&manifest.tables) {
        return Err(MigrationError::Io(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "export manifest digest mismatch",
        )));
    }
    let expected_files: BTreeSet<String> = manifest
        .tables
        .keys()
        .map(|name| export_filename(name))
        .collect();
    for (name, table) in &manifest.tables {
        let path = Path::new(export_dir).join(export_filename(name));
        let metadata = std::fs::symlink_metadata(&path).map_err(MigrationError::Io)?;
        if !metadata.file_type().is_file() {
            return Err(MigrationError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("{} is not a regular file", export_filename(name)),
            )));
        }
        let bytes = std::fs::read(&path).map_err(MigrationError::Io)?;
        if hex_sha256_bytes(&bytes) != table.sha256 {
            return Err(MigrationError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("{} hash mismatch", export_filename(name)),
            )));
        }
        let lines = bytes.iter().filter(|b| **b == b'\n').count() as u64;
        if lines != table.rows {
            return Err(MigrationError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("{} row count mismatch", export_filename(name)),
            )));
        }
    }
    for entry in std::fs::read_dir(export_dir).map_err(MigrationError::Io)? {
        let entry = entry.map_err(MigrationError::Io)?;
        let path = entry.path();
        if path.extension().and_then(|ext| ext.to_str()) == Some("jsonl") {
            let filename = entry.file_name().to_string_lossy().into_owned();
            if !expected_files.contains(&filename) {
                return Err(MigrationError::Io(std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    format!("unlisted export file: {filename}"),
                )));
            }
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

    let mut conn =
        archeaxis_store_sqlite::init_workspace(staging_db).map_err(MigrationError::Sql)?;
    let tx = conn
        .transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)
        .map_err(MigrationError::Sql)?;
    let mut result = DemoStageResult::default();
    let mut leftover: Vec<String> = manifest.tables.keys().cloned().collect();

    if let Some(note_table) = manifest.tables.get("notes") {
        leftover.retain(|t| t != "notes");
        result.notes_seen = note_table.rows;
        let path = Path::new(export_dir).join(export_filename("notes"));
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
    if let Some(att) = manifest.tables.get("attachments") {
        leftover.retain(|t| t != "attachments");
        result.attachments_loss_rows = att.rows;
        result.losses.push(
            "attachments: vNext has no attachment table yet; all attachment rows are counted as losses (never silently dropped)"
                .to_string(),
        );
    }
    if let Some(links) = manifest.tables.get("links") {
        leftover.retain(|t| t != "links");
        result.links_loss_rows = links.rows;
        result.losses.push(
            "links: vNext has no note-relationship table yet; all link rows are counted as losses with reasons (never silently dropped)"
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
    format!(
        "k_{}",
        &hex_sha256_bytes(format!("{kind}|{body}|{created_by}").as_bytes())[..24]
    )
}

fn demo_receipt(kind: &str, body: &str, status: &str) -> String {
    hex_sha256_bytes(format!("{kind}|{body}|{status}|").as_bytes())
}

/// R07: outcome of staging legacy learning history.
#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq)]
pub struct LegacyLearningResult {
    pub rows_seen: u64,
    /// Events staged with the legacy schedule preserved.
    pub staged_scheduled: u64,
    /// Events staged with no schedule (the legacy row carried none) - recorded
    /// as unscheduled, never given an invented interval.
    pub staged_unscheduled: u64,
    /// Re-runs replay the original receipt instead of accumulating history.
    pub replayed: u64,
    pub row_errors: u64,
    pub unmapped_tables: Vec<String>,
}

/// R07: stage legacy learning history as historical events.
///
/// Fidelity rules:
/// - a row that carries its own `next_review_days` keeps that value (an existing
///   schedule is preserved, not recomputed by a different algorithm);
/// - a row without one is recorded as *unscheduled* (`next_review` NULL), never
///   given an invented interval;
/// - the persistent event key is derived from the legacy table + row id, so
///   re-running the migration replays the original receipt (idempotent) instead
///   of duplicating history.
///
/// Learning writes go through `archeaxis_domain::learning`, so the Rust Core
/// stays the only authority for learning events.
pub fn stage_legacy_learning_history(
    export_dir: &str,
    staging_db: &str,
    table: &str,
) -> Result<LegacyLearningResult, MigrationError> {
    let manifest_path = Path::new(export_dir).join("export-manifest.json");
    let manifest_raw = std::fs::read_to_string(&manifest_path).map_err(MigrationError::Io)?;
    let manifest: ExportManifest =
        serde_json::from_str(&manifest_raw).map_err(MigrationError::Json)?;
    verify_export(export_dir, &manifest)?;

    let mut result = LegacyLearningResult {
        unmapped_tables: manifest
            .tables
            .keys()
            .filter(|name| name.as_str() != table)
            .cloned()
            .collect(),
        ..Default::default()
    };
    let Some(entry) = manifest.tables.get(table) else {
        return Ok(result);
    };
    result.rows_seen = entry.rows;
    let raw = std::fs::read_to_string(Path::new(export_dir).join(export_filename(table)))
        .map_err(MigrationError::Io)?;
    let mut conn =
        archeaxis_store_sqlite::init_workspace(staging_db).map_err(MigrationError::Sql)?;

    for line in raw.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let row: serde_json::Value = serde_json::from_str(line).map_err(MigrationError::Json)?;
        let Some(legacy_id) = row.get("id").and_then(serde_json::Value::as_i64) else {
            result.row_errors += 1;
            continue;
        };
        let item = row
            .get("item")
            .or_else(|| row.get("item_key"))
            .and_then(serde_json::Value::as_str)
            .unwrap_or("");
        if item.is_empty() {
            result.row_errors += 1;
            continue;
        }
        let kind = row
            .get("kind")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("legacy_review");
        let outcome = row
            .get("outcome")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("reviewed");
        let correct = outcome.eq_ignore_ascii_case("correct")
            || outcome.eq_ignore_ascii_case("true")
            || outcome == "1";
        // Only a POSITIVE legacy interval is a schedule we can preserve. vNext
        // stores next_review as an absolute date and has no due-today
        // representation for past history (next_review_iso returns None for
        // days <= 0), so a legacy 0 or negative value is recorded as unscheduled
        // and counted exactly as it will be stored - never as a schedule.
        let legacy_days = row
            .get("next_review_days")
            .and_then(serde_json::Value::as_i64)
            .filter(|days| *days > 0);
        let key = format!("legacy-{table}-{legacy_id}");
        match archeaxis_domain::learning::record_review_scheduled(
            &mut conn,
            item,
            kind,
            correct,
            &key,
            legacy_days,
        ) {
            Ok((_event_id, _streak, _days, duplicate)) => {
                if duplicate {
                    result.replayed += 1;
                } else if legacy_days.is_some() {
                    result.staged_scheduled += 1;
                } else {
                    result.staged_unscheduled += 1;
                }
            }
            Err(_) => result.row_errors += 1,
        }
    }
    Ok(result)
}

// Typed preservation export. This is not a semantic 98-table migration.
use serde_json::json;

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TypedTableExport {
    pub columns: Vec<String>,
    pub rowid_alias: Option<String>,
    pub rowid_disposition: String,
    pub rows: u64,
    pub file: String,
    pub sha256: String,
    pub bytes: u64,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TypedExportManifest {
    pub schema: String,
    pub schema_file: String,
    pub schema_sha256: String,
    pub tables: BTreeMap<String, TypedTableExport>,
    pub disposition: String,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub unqueried_tables: BTreeMap<String, String>,
}

fn invalid_export(message: &'static str) -> MigrationError {
    MigrationError::Io(std::io::Error::new(
        std::io::ErrorKind::InvalidInput,
        message,
    ))
}

fn reject_export_links(path: &Path) -> Result<(), MigrationError> {
    for ancestor in path.ancestors() {
        match std::fs::symlink_metadata(ancestor) {
            Ok(metadata) => {
                #[cfg(windows)]
                let reparse = {
                    use std::os::windows::fs::MetadataExt;
                    metadata.file_attributes() & 0x400 != 0
                };
                #[cfg(not(windows))]
                let reparse = false;
                if metadata.file_type().is_symlink() || reparse {
                    return Err(invalid_export("export path contains a link"));
                }
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(MigrationError::Io(error)),
        }
    }
    Ok(())
}

fn typed_file_digest(path: &Path) -> Result<(String, u64), MigrationError> {
    use std::io::Read;
    let mut file = std::fs::File::open(path).map_err(MigrationError::Io)?;
    let mut hash = Sha256::new();
    let mut bytes = 0u64;
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer).map_err(MigrationError::Io)?;
        if read == 0 {
            break;
        }
        hash.update(&buffer[..read]);
        bytes = bytes
            .checked_add(read as u64)
            .ok_or_else(|| invalid_export("export byte count overflow"))?;
    }
    Ok((hex::encode(hash.finalize()), bytes))
}

/// CLI boundary: outputs must be a fresh directory below the explicitly selected
/// project's existing .project-local root. Never infer an external runtime DB.
pub fn validate_typed_export_output(project: &Path, output: &Path) -> Result<(), MigrationError> {
    reject_export_links(project)?;
    reject_export_links(output)?;
    let project = project.canonicalize().map_err(MigrationError::Io)?;
    let allowed = project
        .join(".project-local")
        .canonicalize()
        .map_err(MigrationError::Io)?;
    let parent = output
        .parent()
        .ok_or_else(|| invalid_export("output lacks parent"))?
        .canonicalize()
        .map_err(MigrationError::Io)?;
    if !parent.starts_with(&allowed) || output.exists() || output.file_name().is_none() {
        return Err(invalid_export("output must be fresh and project-local"));
    }
    Ok(())
}

/// Preserve SQLite storage classes and exact cell bytes in a single read-only
/// transaction. REAL is its IEEE-754 bit pattern, TEXT is bytes (not lossy UTF8).
/// Schema SQL and all tables, including internal/unknown/shadow tables, are
/// archived. No semantic import or reconstructed database is claimed.
pub fn export_typed_jsonl(
    db_path: &str,
    out_dir: &str,
) -> Result<TypedExportManifest, MigrationError> {
    export_typed_snapshot(db_path, out_dir, || Ok(()))
}

/// Exact product document/card scope. Other tables remain in schema only and in
/// the unchanged original database; no all-table or semantic qualification.
/// Lease/credential/Agent-memory rows are never selected by this entrypoint.
pub fn export_typed_document_content_jsonl(
    db_path: &str,
    out_dir: &str,
) -> Result<TypedExportManifest, MigrationError> {
    export_typed_snapshot_scoped(
        db_path,
        out_dir,
        || Ok(()),
        Some(&["kb_documents", "kb_cards"]),
    )
}

/// Exact legacy intake-card scope; all other rows remain unqueried in the retained original.
pub fn export_typed_intake_content_jsonl(
    db_path: &str,
    out_dir: &str,
) -> Result<TypedExportManifest, MigrationError> {
    export_typed_snapshot_scoped(db_path, out_dir, || Ok(()), Some(&["ir_intake_cards"]))
}

fn export_typed_snapshot<F>(
    db_path: &str,
    out_dir: &str,
    after_snapshot: F,
) -> Result<TypedExportManifest, MigrationError>
where
    F: FnOnce() -> Result<(), MigrationError>,
{
    export_typed_snapshot_scoped(db_path, out_dir, after_snapshot, None)
}

fn export_typed_snapshot_scoped<F>(
    db_path: &str,
    out_dir: &str,
    after_snapshot: F,
    selected_tables: Option<&[&str]>,
) -> Result<TypedExportManifest, MigrationError>
where
    F: FnOnce() -> Result<(), MigrationError>,
{
    reject_export_links(Path::new(db_path))?;
    let output = Path::new(out_dir);
    reject_export_links(output)?;
    if output.exists() {
        return Err(invalid_export("export output already exists"));
    }
    let mut conn =
        Connection::open_with_flags(db_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    conn.execute_batch("PRAGMA query_only=ON")?;
    let transaction = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Deferred)?;
    let schema_rows: Vec<serde_json::Value> = {
        let mut stmt = transaction
            .prepare("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name")?;
        let rows = stmt
            .query_map([], |row| {
                Ok(json!({
                    "type": row.get::<_, String>(0)?, "name": row.get::<_, String>(1)?,
                    "table": row.get::<_, String>(2)?, "sql": row.get::<_, Option<String>>(3)?
                }))
            })?
            .collect::<Result<_, _>>()?;
        rows
    };
    if let Some(selected) = selected_tables {
        for required in selected {
            if !schema_rows
                .iter()
                .any(|object| object["type"] == "table" && object["name"] == *required)
            {
                return Err(invalid_export("selected content scope is incomplete"));
            }
        }
    }
    // The schema read above establishes the same SQLite snapshot used for rows.
    after_snapshot()?;
    std::fs::create_dir(output).map_err(MigrationError::Io)?;
    let schema_bytes = serde_json::to_vec_pretty(&schema_rows)?;
    std::fs::write(output.join("schema.json"), &schema_bytes).map_err(MigrationError::Io)?;
    let mut manifest = TypedExportManifest {
        schema: "archeaxis.legacy-typed-export/v1".into(),
        schema_file: "schema.json".into(),
        schema_sha256: hex_sha256_bytes(&schema_bytes),
        tables: BTreeMap::new(),
        disposition: if selected_tables.is_some() {
            "SELECTED_CONTENT_PRESERVED_ORIGINAL_RETAINED_NOT_SEMANTICALLY_MIGRATED"
        } else {
            "PRESERVED_NOT_SEMANTICALLY_MIGRATED"
        }
        .into(),
        unqueried_tables: BTreeMap::new(),
    };
    for object in schema_rows
        .iter()
        .filter(|object| object["type"] == "table")
    {
        let name = object["name"]
            .as_str()
            .ok_or_else(|| invalid_export("invalid table name"))?;
        if selected_tables.is_some_and(|selected| !selected.contains(&name)) {
            manifest.unqueried_tables.insert(
                name.to_owned(),
                "schema_only_outside_authorized_content_scope_original_retained".into(),
            );
            continue;
        }
        // Fixed SHA names bound Windows basenames; the manifest retains the exact original table name.
        let filename = format!("table-{}.jsonl", hex_sha256_bytes(name.as_bytes()));
        let columns: Vec<String> = {
            let mut stmt =
                transaction.prepare("SELECT name FROM pragma_table_xinfo(?1) ORDER BY cid")?;
            let rows = stmt
                .query_map([name], |row| row.get(0))?
                .collect::<Result<_, _>>()?;
            rows
        };
        if selected_tables.is_some()
            && columns.iter().any(|column| {
                let name = column.to_ascii_lowercase();
                [
                    "token",
                    "secret",
                    "password",
                    "credential",
                    "api_key",
                    "cookie",
                    "oauth",
                ]
                .iter()
                .any(|part| name.contains(part))
            })
        {
            return Err(invalid_export(
                "selected content table contains protected columns",
            ));
        }
        let file = std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join(&filename))
            .map_err(MigrationError::Io)?;
        let mut writer = std::io::BufWriter::new(file);
        let rowid_alias = ["rowid", "_rowid_", "oid"]
            .iter()
            .find(|alias| {
                !columns
                    .iter()
                    .any(|column| column.eq_ignore_ascii_case(alias))
            })
            .filter(|alias| {
                transaction
                    .prepare(&format!(
                        "SELECT {} FROM {} LIMIT 0",
                        alias,
                        quote_identifier(name)
                    ))
                    .is_ok()
            })
            .map(|alias| (*alias).to_owned());
        let rowid_disposition = if rowid_alias.is_some() {
            "available"
        } else {
            "without_rowid_or_shadowed_or_unavailable"
        }
        .to_owned();
        let mut projection: Vec<String> = rowid_alias.iter().cloned().collect();
        projection.extend(columns.iter().map(|column| quote_identifier(column)));
        let mut statement = transaction.prepare(&format!(
            "SELECT {} FROM {}",
            projection.join(","),
            quote_identifier(name)
        ))?;
        let cell_offset = usize::from(rowid_alias.is_some());
        let mut rows = statement.query([])?;
        let mut count = 0u64;
        while let Some(row) = rows.next()? {
            let mut cells = Vec::with_capacity(columns.len());
            for index in 0..columns.len() {
                use rusqlite::types::ValueRef;
                cells.push(match row.get_ref(index + cell_offset)? {
                    ValueRef::Null => json!({"type":"null"}),
                    ValueRef::Integer(value) => json!({"type":"integer","value":value}),
                    ValueRef::Real(value) => {
                        json!({"type":"real","bits":format!("{:016x}",value.to_bits())})
                    }
                    ValueRef::Text(bytes) => json!({"type":"text","hex":hex::encode(bytes)}),
                    ValueRef::Blob(bytes) => json!({"type":"blob","hex":hex::encode(bytes)}),
                });
            }
            let rowid: Option<i64> = if rowid_alias.is_some() {
                row.get(0)?
            } else {
                None
            };
            serde_json::to_writer(&mut writer, &json!({"rowid": rowid, "cells": cells}))?;
            writer.write_all(b"\n").map_err(MigrationError::Io)?;
            count += 1;
        }
        writer.flush().map_err(MigrationError::Io)?;
        writer.get_ref().sync_all().map_err(MigrationError::Io)?;
        drop(writer);
        let (sha256, bytes) = typed_file_digest(&output.join(&filename))?;
        manifest.tables.insert(
            name.to_owned(),
            TypedTableExport {
                columns,
                rowid_alias,
                rowid_disposition,
                rows: count,
                file: filename,
                sha256,
                bytes,
            },
        );
    }
    transaction.commit()?;
    let manifest_bytes = serde_json::to_vec_pretty(&manifest)?;
    let mut file = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(output.join("typed-export-manifest.json"))
        .map_err(MigrationError::Io)?;
    file.write_all(&manifest_bytes)
        .map_err(MigrationError::Io)?;
    file.sync_all().map_err(MigrationError::Io)?;
    Ok(manifest)
}

#[cfg(test)]
mod typed_preservation_tests {
    use super::*;

    #[test]
    fn typed_export_preserves_bytes_types_schema_and_source() {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("legacy.sqlite");
        let conn = Connection::open(&db).unwrap();
        conn.execute_batch("CREATE TABLE \"未知表\"(t,b,r,n,i); CREATE INDEX legacy_index ON \"未知表\"(i);
            INSERT INTO \"未知表\" VALUES(CAST(X'ff0061' AS TEXT),X'ff0061',1.2345678901234567,NULL,-9223372036854775808);
            CREATE TABLE empty_unknown(x); CREATE TABLE sequenced(id INTEGER PRIMARY KEY AUTOINCREMENT); INSERT INTO sequenced DEFAULT VALUES;").unwrap();
        drop(conn);
        let before = std::fs::read(&db).unwrap();
        let output = dir.path().join("typed");
        let manifest = export_typed_jsonl(db.to_str().unwrap(), output.to_str().unwrap()).unwrap();
        let table = &manifest.tables["未知表"];
        let bytes = std::fs::read(output.join(&table.file)).unwrap();
        let exported: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(exported["rowid"], 1);
        let cells = exported["cells"].as_array().unwrap();
        assert_eq!(cells[0], json!({"type":"text","hex":"ff0061"}));
        assert_eq!(cells[1], json!({"type":"blob","hex":"ff0061"}));
        assert_eq!(
            cells[2]["bits"],
            format!("{:016x}", 1.2345678901234567f64.to_bits())
        );
        assert_eq!(cells[3], json!({"type":"null"}));
        assert_eq!(cells[4]["value"], i64::MIN);
        assert_eq!(table.sha256, hex_sha256_bytes(&bytes));
        assert_eq!(manifest.tables["empty_unknown"].rows, 0);
        assert_eq!(manifest.tables["sqlite_sequence"].rows, 1);
        let schema = std::fs::read(output.join("schema.json")).unwrap();
        assert_eq!(manifest.schema_sha256, hex_sha256_bytes(&schema));
        assert!(String::from_utf8(schema).unwrap().contains("legacy_index"));
        assert_eq!(before, std::fs::read(&db).unwrap());
        assert!(export_typed_jsonl(db.to_str().unwrap(), output.to_str().unwrap()).is_err());
    }

    #[test]
    fn typed_export_uses_one_snapshot_even_after_other_connection_commits() {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("legacy.sqlite");
        let writer = Connection::open(&db).unwrap();
        writer
            .execute_batch(
                "PRAGMA journal_mode=WAL; CREATE TABLE known(x); INSERT INTO known VALUES(37);",
            )
            .unwrap();
        let output = dir.path().join("typed");
        let manifest =
            export_typed_snapshot(db.to_str().unwrap(), output.to_str().unwrap(), || {
                writer.execute_batch("UPDATE known SET x=99; CREATE TABLE late_table(x);")?;
                Ok(())
            })
            .unwrap();
        assert!(!manifest.tables.contains_key("late_table"));
        let exported: serde_json::Value = serde_json::from_slice(
            &std::fs::read(output.join(&manifest.tables["known"].file)).unwrap(),
        )
        .unwrap();
        assert_eq!(exported["cells"][0]["value"], 37);
        assert_eq!(
            writer
                .query_row("SELECT x FROM known", [], |row| row.get::<_, i64>(0))
                .unwrap(),
            99
        );
    }

    #[test]
    fn typed_export_preserves_rowid_shadow_and_generated_columns() {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("legacy.sqlite");
        let conn = Connection::open(&db).unwrap();
        conn.execute_batch("CREATE TABLE shadow(rowid TEXT,x INTEGER,y INTEGER GENERATED ALWAYS AS(x+1) VIRTUAL); INSERT INTO shadow(_rowid_,rowid,x) VALUES(37,'visible',8); CREATE TABLE no_rowid(k TEXT PRIMARY KEY) WITHOUT ROWID; INSERT INTO no_rowid VALUES('a');").unwrap();
        drop(conn);
        let out = dir.path().join("typed");
        let manifest = export_typed_jsonl(db.to_str().unwrap(), out.to_str().unwrap()).unwrap();
        let table = &manifest.tables["shadow"];
        assert_eq!(table.rowid_alias.as_deref(), Some("_rowid_"));
        let row: serde_json::Value =
            serde_json::from_slice(&std::fs::read(out.join(&table.file)).unwrap()).unwrap();
        assert_eq!(row["rowid"], 37);
        assert_eq!(row["cells"][0]["hex"], hex::encode(b"visible"));
        assert_eq!(row["cells"][2]["value"], 9);
        let table = &manifest.tables["no_rowid"];
        assert!(table.rowid_alias.is_none());
        let row: serde_json::Value =
            serde_json::from_slice(&std::fs::read(out.join(&table.file)).unwrap()).unwrap();
        assert!(row["rowid"].is_null());
    }

    #[test]
    fn typed_export_bounds_long_unicode_table_filenames_and_preserves_original_names() {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("synthetic.sqlite");
        let conn = Connection::open(&db).unwrap();
        let names = [
            format!("{}\"CON:/\\?", "知识资料".repeat(96)),
            format!("{}续", "知识资料".repeat(96)),
        ];
        for name in &names {
            conn.execute_batch(&format!(
                "CREATE TABLE {}(x TEXT); INSERT INTO {} VALUES('kept');",
                quote_identifier(name),
                quote_identifier(name)
            ))
            .unwrap();
        }
        drop(conn);
        let out = dir.path().join("export");
        let manifest = export_typed_jsonl(db.to_str().unwrap(), out.to_str().unwrap()).unwrap();
        assert_eq!(manifest.tables.len(), 2);
        assert_ne!(
            manifest.tables[&names[0]].file,
            manifest.tables[&names[1]].file
        );
        for name in &names {
            let table = &manifest.tables[name];
            assert_eq!(
                table.file,
                format!("table-{}.jsonl", hex_sha256_bytes(name.as_bytes()))
            );
            assert_eq!(table.file.len(), 76);
            assert!(table.file.is_ascii());
            assert_eq!(table.rows, 1);
            assert!(out.join(&table.file).is_file());
        }
        let stored: TypedExportManifest =
            serde_json::from_slice(&std::fs::read(out.join("typed-export-manifest.json")).unwrap())
                .unwrap();
        assert_eq!(
            stored.tables.keys().collect::<Vec<_>>(),
            manifest.tables.keys().collect::<Vec<_>>()
        );
    }

    #[test]
    fn typed_export_streaming_hash_matches_large_multirow_expected_bytes() {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("synthetic.sqlite");
        let mut conn = Connection::open(&db).unwrap();
        conn.execute_batch("CREATE TABLE many_rows(i INTEGER,t TEXT,b BLOB)")
            .unwrap();
        let count = 4097i64;
        let text = "真实工程夹具".repeat(96);
        let blob = [0u8, 0xff, 37, 83];
        let mut expected_hash = Sha256::new();
        let mut expected_bytes = 0u64;
        {
            let tx = conn.transaction().unwrap();
            let mut insert = tx
                .prepare("INSERT INTO many_rows VALUES(?1,?2,?3)")
                .unwrap();
            for i in 0..count {
                insert
                    .execute(rusqlite::params![i, &text, &blob[..]])
                    .unwrap();
                let expected = json!({"rowid":i+1,"cells":[{"type":"integer","value":i},{"type":"text","hex":hex::encode(text.as_bytes())},{"type":"blob","hex":hex::encode(blob)}]});
                let bytes = serde_json::to_vec(&expected).unwrap();
                expected_hash.update(&bytes);
                expected_hash.update(b"\n");
                expected_bytes += bytes.len() as u64 + 1;
            }
            drop(insert);
            tx.commit().unwrap();
        }
        drop(conn);
        let out = dir.path().join("export");
        let manifest = export_typed_jsonl(db.to_str().unwrap(), out.to_str().unwrap()).unwrap();
        let table = &manifest.tables["many_rows"];
        assert_eq!(table.rows, count as u64);
        assert!(expected_bytes > 100 * 64 * 1024);
        assert_eq!(table.bytes, expected_bytes);
        assert_eq!(table.sha256, hex::encode(expected_hash.finalize()));
        assert_eq!(
            std::fs::metadata(out.join(&table.file)).unwrap().len(),
            expected_bytes
        );
    }

    #[test]
    fn typed_cli_boundary_rejects_external_existing_and_non_directory_outputs() {
        let dir = tempfile::tempdir().unwrap();
        let project = dir.path().join("project");
        std::fs::create_dir_all(project.join(".project-local")).unwrap();
        assert!(
            validate_typed_export_output(&project, &project.join(".project-local/export")).is_ok()
        );
        assert!(validate_typed_export_output(&project, &dir.path().join("outside")).is_err());
        std::fs::write(project.join(".project-local/existing"), b"keep").unwrap();
        assert!(
            validate_typed_export_output(&project, &project.join(".project-local/existing"))
                .is_err()
        );
        assert!(
            validate_typed_export_output(&project, &project.join(".project-local/../escape"))
                .is_err()
        );
    }
}
