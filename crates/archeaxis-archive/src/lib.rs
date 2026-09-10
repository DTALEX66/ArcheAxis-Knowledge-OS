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
    "workspace_meta",
    "sources",
    "transforms",
    "anchors",
    "knowledge",
    "review_events",
    "learning_events",
    "jobs",
    "job_attempts",
    "job_outputs",
    "source_origins",
    "learning_event_keys",
    "knowledge_supersedes",
];

/// ARCHIVE-01: the older v3 wire layout. Schema version 3 shipped twice: first
/// with these eleven tables, then with the thirteen-table set now exported
/// (`knowledge_supersedes` and `learning_event_keys` were added while the
/// reported version stayed 3). Both are real historical layouts and must be
/// restorable; anything else at version 3 is an unknown layout and is rejected
/// rather than guessed.
pub const V3_TABLES_ELEVEN: &[&str] = &[
    "workspace_meta",
    "sources",
    "transforms",
    "anchors",
    "knowledge",
    "review_events",
    "learning_events",
    "jobs",
    "job_attempts",
    "job_outputs",
    "source_origins",
];

/// ARCHIVE-01: resolve the exact table set an archive claims to contain. The
/// layout is identified by the manifest's table set, never by version alone.
fn archive_tables(manifest: &ArchiveManifest) -> Result<&'static [&'static str], ArchiveError> {
    let names: Vec<&str> = manifest.tables.keys().map(String::as_str).collect();
    let same_set = |expected: &[&str]| {
        expected.len() == names.len() && expected.iter().all(|t| names.contains(t))
    };
    match manifest.schema_version {
        2 => {
            if same_set(&EXPORT_TABLES[..8]) {
                Ok(&EXPORT_TABLES[..8])
            } else {
                Err(ArchiveError::Table(
                    "archive layout does not match the v2 table set".into(),
                ))
            }
        }
        3 => {
            if same_set(V3_TABLES_ELEVEN) {
                Ok(V3_TABLES_ELEVEN)
            } else if same_set(EXPORT_TABLES) {
                Ok(EXPORT_TABLES)
            } else {
                Err(ArchiveError::Table("unknown v3 archive layout".into()))
            }
        }
        version if version == archeaxis_store_sqlite::SCHEMA_VERSION => {
            if same_set(EXPORT_TABLES) {
                Ok(EXPORT_TABLES)
            } else {
                Err(ArchiveError::Table(
                    "archive layout does not match the current table set".into(),
                ))
            }
        }
        _ => Err(ArchiveError::Table("unsupported archive version".into())),
    }
}

#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq)]
pub struct ArchiveManifest {
    pub schema_version: i64,
    pub raw_objects: BTreeMap<String, u64>,
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
    archeaxis_store_sqlite::raw_objects::reject_links(Path::new(db_path))?;
    archeaxis_store_sqlite::raw_objects::reject_links(Path::new(out_dir))?;
    let conn = Connection::open_with_flags(db_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    conn.execute_batch("BEGIN DEFERRED;")?;
    let schema_version: String = conn.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'", [], |r| r.get(0),
    )?;
    let schema_version = schema_version.parse::<i64>()
        .map_err(|_| ArchiveError::Table("invalid schema version".into()))?;
    if schema_version != archeaxis_store_sqlite::SCHEMA_VERSION {
        return Err(ArchiveError::Table("unsupported archive schema version".into()));
    }
    std::fs::create_dir(out_dir).map_err(ArchiveError::Io)?;
    let mut manifest = ArchiveManifest { schema_version, ..Default::default() };
    let mut file_hashes: BTreeMap<String, String> = BTreeMap::new();
    for table in EXPORT_TABLES {
        let cols = column_names(&conn, table)?;
        if cols.is_empty() {
            return Err(ArchiveError::Table(format!("missing table {table}")));
        }
        let path = Path::new(out_dir).join(format!("{table}.jsonl"));
        let mut fh = std::fs::File::create(&path).map_err(ArchiveError::Io)?;
        let mut stmt = conn.prepare(&format!("SELECT * FROM \"{table}\" ORDER BY rowid"))?;
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
    let object_dir = Path::new(out_dir).join("objects");
    std::fs::create_dir(&object_dir).map_err(ArchiveError::Io)?;
    let mut sources = conn.prepare("SELECT sha256 FROM sources ORDER BY sha256")?;
    for digest in sources.query_map([], |row| row.get::<_, String>(0))? {
        let digest = digest?;
        let bytes = archeaxis_store_sqlite::raw_objects::read(&conn, &digest)?;
        let mut file = std::fs::OpenOptions::new().write(true).create_new(true)
            .open(object_dir.join(&digest)).map_err(ArchiveError::Io)?;
        file.write_all(&bytes).map_err(ArchiveError::Io)?;
        file.sync_all().map_err(ArchiveError::Io)?;
        manifest.raw_objects.insert(digest, bytes.len() as u64);
    }
    manifest.manifest_sha256 = manifest_digest(&manifest);
    let mp = Path::new(out_dir).join("manifest.json");
    std::fs::write(&mp, serde_json::to_string_pretty(&manifest).map_err(ArchiveError::Json)?)
        .map_err(ArchiveError::Io)?;
    conn.execute_batch("COMMIT;")?;
    Ok(manifest)
}

/// Restore JSONL files from `archive_dir` into a fresh vNext workspace DB.
/// Insert order follows EXPORT_TABLES so foreign keys hold.
pub fn restore_workspace(
    archive_dir: &str,
    target_db: &str,
) -> Result<ArchiveManifest, ArchiveError> {
    let target = Path::new(target_db);
    archeaxis_store_sqlite::raw_objects::reject_links(target)?;
    archeaxis_store_sqlite::raw_objects::reject_links(Path::new(archive_dir))?;
    if std::fs::symlink_metadata(target).is_ok() {
        return Err(ArchiveError::Table("restore target already exists".into()));
    }
    let mp = Path::new(archive_dir).join("manifest.json");
    archeaxis_store_sqlite::raw_objects::reject_links(&mp)?;
    let raw = std::fs::read_to_string(&mp).map_err(ArchiveError::Io)?;
    let manifest: ArchiveManifest = serde_json::from_str(&raw).map_err(ArchiveError::Json)?;
    // ARCHIVE-01: the archive's own table set selects the layout; v3 covers the
    // eleven-table and thirteen-table historical shapes, and any other v3 set is
    // rejected instead of being completed by guesswork.
    let tables = archive_tables(&manifest)?;
    if manifest_digest(&manifest) != manifest.manifest_sha256 {
        return Err(ArchiveError::Table(
            "archive manifest integrity mismatch".into(),
        ));
    }
    // Validate every table, including zero-row tables, before creating a database.
    // Keep the validated bytes in memory so a changed archive cannot be reread
    // between verification and insertion.
    let mut validated = BTreeMap::new();
    for table in tables {
        let tf = manifest
            .tables
            .get(*table)
            .ok_or_else(|| ArchiveError::Table(table.to_string()))?;
        let path = Path::new(archive_dir).join(format!("{table}.jsonl"));
        archeaxis_store_sqlite::raw_objects::reject_links(&path)?;
        let bytes = std::fs::read(&path).map_err(ArchiveError::Io)?;
        if hex::encode(Sha256::digest(&bytes)) != tf.sha256 {
            return Err(ArchiveError::Table(format!("table hash mismatch: {table}")));
        }
        let content = String::from_utf8(bytes)
            .map_err(|_| ArchiveError::Table(format!("invalid UTF-8: {table}")))?;
        let rows: Vec<serde_json::Value> = content.lines()
            .map(serde_json::from_str).collect::<Result<_, _>>().map_err(ArchiveError::Json)?;
        if rows.len() as u64 != tf.rows {
            return Err(ArchiveError::Table(format!("table row-count mismatch: {table}")));
        }
        validated.insert(*table, rows);
    }
    let mut raw_bytes = BTreeMap::new();
    for (digest, size) in &manifest.raw_objects {
        if digest.len() != 64 || !digest.bytes().all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase()) {
            return Err(ArchiveError::Table("invalid object digest".into()));
        }
        let path = Path::new(archive_dir).join("objects").join(digest);
        archeaxis_store_sqlite::raw_objects::reject_links(&path)?;
        let bytes = std::fs::read(&path).map_err(ArchiveError::Io)?;
        if bytes.len() as u64 != *size || hex::encode(Sha256::digest(&bytes)) != *digest {
            return Err(ArchiveError::Table("raw object integrity mismatch".into()));
        }
        raw_bytes.insert(digest.clone(), bytes);
    }
    if validated["sources"].len() != raw_bytes.len() || validated["sources"].iter().any(|row| {
        let digest = row.get("sha256").and_then(|v| v.as_str()).unwrap_or("");
        !raw_bytes.contains_key(digest) || row.get("raw_path").and_then(|v| v.as_str()) != Some(digest)
    }) {
        return Err(ArchiveError::Table("source/object reference mismatch".into()));
    }
    let parent = target.parent().filter(|p| !p.as_os_str().is_empty()).unwrap_or(Path::new("."));
    let staging = tempfile::tempdir_in(parent).map_err(ArchiveError::Io)?;
    let staged = staging.path().join("restored.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(
        staged.to_str().ok_or_else(|| ArchiveError::Table("invalid target path".into()))?,
    )?;
    let staged_objects = archeaxis_store_sqlite::raw_objects::root(&conn)?;
    std::fs::create_dir_all(&staged_objects).map_err(ArchiveError::Io)?;
    for bytes in raw_bytes.values() { archeaxis_store_sqlite::raw_objects::persist(&conn, bytes)?; }
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    tx.execute("DELETE FROM workspace_meta", [])?;
    for table in tables {
        let cols = column_names(&tx, table)?;
        let placeholders = vec!["?"; cols.len()].join(",");
        let sql = format!(
            "INSERT INTO \"{table}\" ({}) VALUES ({placeholders})",
            cols.join(",")
        );
        let mut stmt = tx.prepare(&sql)?;
        for v in &validated[table] {
            let obj = v
                .as_object()
                .ok_or_else(|| ArchiveError::Table("row not object".into()))?;
            // ARCHIVE-01 upgrade path: columns added after an older archive was
            // written are absent from its rows and are filled with NULL here
            // (they are additive and nullable). An unknown extra column means the
            // row does not belong to a layout we understand, so reject it rather
            // than silently dropping or guessing data.
            if obj.keys().any(|c| !cols.contains(c)) {
                return Err(ArchiveError::Table(format!(
                    "unknown column in archive row: {table}"
                )));
            }
            let mut params: Vec<rusqlite::types::Value> = Vec::new();
            for c in &cols {
                params.push(json_to_value(
                    obj.get(c).cloned().unwrap_or(serde_json::Value::Null),
                ));
            }
            stmt.execute(rusqlite::params_from_iter(params.iter()))?;
        }
    }
    let restored_version: String = tx.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'", [], |r| r.get(0),
    )?;
    if restored_version != manifest.schema_version.to_string() {
        return Err(ArchiveError::Table("workspace metadata version mismatch".into()));
    }
    tx.execute("UPDATE workspace_meta SET value=?1 WHERE key='schema_version'",
        [archeaxis_store_sqlite::SCHEMA_VERSION.to_string()])?;
    let violation = tx.prepare("PRAGMA foreign_key_check")?.exists([])?;
    if violation { return Err(ArchiveError::Table("restored foreign key mismatch".into())); }
    tx.commit()?;
    conn.execute_batch("PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;")?;
    drop(conn);
    std::fs::OpenOptions::new().read(true).write(true).open(&staged)
        .map_err(ArchiveError::Io)?.sync_all().map_err(ArchiveError::Io)?;
    // Same-filesystem atomic publication with no overwrite even if another
    // process creates target after preflight. Unsupported filesystems fail closed.
    let final_objects = std::path::PathBuf::from(format!("{target_db}.objects"));
    archeaxis_store_sqlite::raw_objects::reject_links(&final_objects)?;
    std::fs::create_dir(&final_objects).map_err(ArchiveError::Io)?;
    let mut publication = ObjectPublication { directory: final_objects.clone(), files: Vec::new(), committed: false };
    for digest in raw_bytes.keys() {
        let path = final_objects.join(digest);
        std::fs::hard_link(staged_objects.join(digest), &path).map_err(ArchiveError::Io)?;
        publication.files.push(path);
    }
    std::fs::hard_link(&staged, target).map_err(ArchiveError::Io)?;
    publication.committed = true;
    Ok(manifest)
}

fn manifest_digest(manifest: &ArchiveManifest) -> String {
    let mut h = Sha256::new();
    h.update(manifest.schema_version.to_le_bytes());
    for (table, file) in &manifest.tables {
        h.update(table.as_bytes());
        h.update(file.rows.to_le_bytes());
        h.update(file.sha256.as_bytes());
    }
    for (digest, bytes) in &manifest.raw_objects {
        h.update(digest.as_bytes());
        h.update(bytes.to_le_bytes());
    }
    hex::encode(h.finalize())
}

/// Roll back only files created by this attempt if publication fails.
/// Never recursively remove a destination or an existing user object tree.
struct ObjectPublication {
    directory: std::path::PathBuf,
    files: Vec<std::path::PathBuf>,
    committed: bool,
}
impl Drop for ObjectPublication {
    fn drop(&mut self) {
        if !self.committed {
            for path in &self.files { let _ = std::fs::remove_file(path); }
            let _ = std::fs::remove_dir(&self.directory);
        }
    }
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

#[cfg(test)]
mod version_tests {
    use super::*;
    #[test]
    fn v2_archive_remains_readable_after_attempt_schema_migration() {
        let dir=tempfile::tempdir().unwrap();
        let db=dir.path().join("v2.sqlite");
        drop(archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap());
        let archive=dir.path().join("archive");
        let mut manifest=export_workspace(db.to_str().unwrap(),archive.to_str().unwrap()).unwrap();
        // Reconstruct the previous public v2 wire shape (same old table columns).
        manifest.schema_version=2;
        manifest.tables.remove("job_attempts"); manifest.tables.remove("job_outputs");
        manifest.tables.remove("source_origins"); // v2 wire predates provenance table
        manifest.tables.remove("learning_event_keys"); // v2 wire predates dedup keys
        manifest.tables.remove("knowledge_supersedes"); // v2 wire predates supersedes
        let rows=serde_json::json!({"key":"schema_version","value":"2"}).to_string()+"\n";
        std::fs::write(archive.join("workspace_meta.jsonl"),&rows).unwrap();
        manifest.tables.get_mut("workspace_meta").unwrap().sha256=hex::encode(Sha256::digest(rows.as_bytes()));
        manifest.manifest_sha256=manifest_digest(&manifest);
        std::fs::write(archive.join("manifest.json"),serde_json::to_vec(&manifest).unwrap()).unwrap();
        let target=dir.path().join("upgraded.sqlite");
        restore_workspace(archive.to_str().unwrap(),target.to_str().unwrap()).unwrap();
        let conn=Connection::open_with_flags(target,rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
        assert_eq!(conn.query_row("SELECT value FROM workspace_meta WHERE key='schema_version'",[],|r|r.get::<_,String>(0)).unwrap(),"4");
        assert_eq!(conn.query_row("SELECT count(*) FROM job_attempts",[],|r|r.get::<_,i64>(0)).unwrap(),0);
    }

    /// Rewrite one table file and keep the manifest entry (rows + hash) honest.
    fn rewrite_table(manifest: &mut ArchiveManifest, archive: &Path, table: &str, content: &str) {
        std::fs::write(archive.join(format!("{table}.jsonl")), content.as_bytes()).unwrap();
        let tf = manifest.tables.get_mut(table).unwrap();
        tf.rows = content.lines().count() as u64;
        tf.sha256 = hex::encode(Sha256::digest(content.as_bytes()));
    }

    fn seal(manifest: &mut ArchiveManifest, archive: &Path) {
        manifest.manifest_sha256 = manifest_digest(manifest);
        std::fs::write(archive.join("manifest.json"), serde_json::to_vec(manifest).unwrap()).unwrap();
    }

    fn exported_fixture(dir: &tempfile::TempDir) -> (String, ArchiveManifest) {
        let db = dir.path().join("seed.sqlite");
        drop(archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap());
        let archive = dir.path().join("archive");
        let manifest = export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
        (archive.to_str().unwrap().to_string(), manifest)
    }

    /// ARCHIVE-01: the older v3 wire shape carried eleven tables (no supersedes
    /// and no learning-event key table) and must still restore and upgrade.
    #[test]
    fn v3_eleven_table_archive_restores_and_upgrades() {
        let dir = tempfile::tempdir().unwrap();
        let (archive, mut manifest) = exported_fixture(&dir);
        let archive_path = Path::new(archive.as_str());
        manifest.schema_version = 3;
        for gone in ["learning_event_keys", "knowledge_supersedes"] {
            manifest.tables.remove(gone);
            let _ = std::fs::remove_file(archive_path.join(format!("{gone}.jsonl")));
        }
        let meta = serde_json::json!({"key":"schema_version","value":"3"}).to_string() + "\n";
        rewrite_table(&mut manifest, archive_path, "workspace_meta", &meta);
        assert_eq!(manifest.tables.len(), V3_TABLES_ELEVEN.len());
        seal(&mut manifest, archive_path);

        let target = dir.path().join("eleven.sqlite");
        let restored = restore_workspace(&archive, target.to_str().unwrap()).unwrap();
        assert_eq!(restored.schema_version, 3);
        let conn = Connection::open_with_flags(target, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
        assert_eq!(
            conn.query_row("SELECT value FROM workspace_meta WHERE key='schema_version'",[],|r|r.get::<_,String>(0)).unwrap(),
            "4"
        );
        assert_eq!(conn.query_row("SELECT count(*) FROM learning_event_keys",[],|r|r.get::<_,i64>(0)).unwrap(), 0);
    }

    /// ARCHIVE-01: the later v3 shape already had thirteen tables, but its
    /// learning-event key rows predate the v4 receipt columns. Additive columns
    /// are filled with NULL instead of rejecting the archive.
    #[test]
    fn v3_thirteen_table_archive_upgrades_legacy_event_key_rows() {
        let dir = tempfile::tempdir().unwrap();
        let (archive, mut manifest) = exported_fixture(&dir);
        let archive_path = Path::new(archive.as_str());
        manifest.schema_version = 3;
        let meta = serde_json::json!({"key":"schema_version","value":"3"}).to_string() + "\n";
        rewrite_table(&mut manifest, archive_path, "workspace_meta", &meta);
        let legacy = serde_json::json!({
            "event_key":"legacy-key-1","item_key":"card-1","created_at":"2026-09-01 00:00:00"
        }).to_string() + "\n";
        rewrite_table(&mut manifest, archive_path, "learning_event_keys", &legacy);
        seal(&mut manifest, archive_path);

        let target = dir.path().join("thirteen.sqlite");
        restore_workspace(&archive, target.to_str().unwrap()).unwrap();
        let conn = Connection::open_with_flags(target, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
        assert_eq!(
            conn.query_row("SELECT value FROM workspace_meta WHERE key='schema_version'",[],|r|r.get::<_,String>(0)).unwrap(),
            "4"
        );
        let (key, payload, event_id): (String, Option<String>, Option<i64>) = conn
            .query_row("SELECT event_key, payload_hash, event_id FROM learning_event_keys", [], |r| {
                Ok((r.get(0)?, r.get(1)?, r.get(2)?))
            })
            .unwrap();
        assert_eq!(key, "legacy-key-1");
        assert_eq!(payload, None, "added columns stay NULL, never invented");
        assert_eq!(event_id, None);
    }

    /// ARCHIVE-01: a v3 table set that is neither historical layout is refused.
    #[test]
    fn v3_unknown_table_set_is_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let (archive, mut manifest) = exported_fixture(&dir);
        let archive_path = Path::new(archive.as_str());
        manifest.schema_version = 3;
        manifest.tables.remove("knowledge_supersedes");
        let _ = std::fs::remove_file(archive_path.join("knowledge_supersedes.jsonl"));
        let meta = serde_json::json!({"key":"schema_version","value":"3"}).to_string() + "\n";
        rewrite_table(&mut manifest, archive_path, "workspace_meta", &meta);
        seal(&mut manifest, archive_path);

        let target = dir.path().join("unknown.sqlite");
        let err = restore_workspace(&archive, target.to_str().unwrap()).unwrap_err();
        assert!(
            format!("{err}").contains("unknown v3 archive layout"),
            "unexpected error: {err}"
        );
        assert!(!target.exists(), "no database is published for an unknown layout");
    }

    /// ARCHIVE-01: a current-version archive missing an exported table is refused
    /// rather than restored as a silently partial workspace.
    #[test]
    fn current_archive_with_missing_table_is_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let (archive, mut manifest) = exported_fixture(&dir);
        let archive_path = Path::new(archive.as_str());
        manifest.tables.remove("review_events");
        let _ = std::fs::remove_file(archive_path.join("review_events.jsonl"));
        seal(&mut manifest, archive_path);

        let target = dir.path().join("partial.sqlite");
        let err = restore_workspace(&archive, target.to_str().unwrap()).unwrap_err();
        assert!(
            format!("{err}").contains("current table set"),
            "unexpected error: {err}"
        );
    }

    /// ARCHIVE-01: a row carrying a column the target schema does not know is
    /// refused; the restore never drops or guesses unknown fields.
    #[test]
    fn archive_row_with_unknown_column_is_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let (archive, mut manifest) = exported_fixture(&dir);
        let archive_path = Path::new(archive.as_str());
        let rogue = serde_json::json!({"key":"schema_version","value":"4","rogue_field":"x"}).to_string() + "\n";
        rewrite_table(&mut manifest, archive_path, "workspace_meta", &rogue);
        seal(&mut manifest, archive_path);

        let target = dir.path().join("rogue.sqlite");
        let err = restore_workspace(&archive, target.to_str().unwrap()).unwrap_err();
        assert!(
            format!("{err}").contains("unknown column in archive row"),
            "unexpected error: {err}"
        );
        assert!(!target.exists(), "no database is published for an unknown column");
    }
}
