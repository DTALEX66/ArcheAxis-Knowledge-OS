//! vNext database schema and workspace init (Rust sole writer).
use rusqlite::Connection;

pub mod raw_objects;
pub mod writer;

pub const SCHEMA_VERSION: i64 = 2;

const SCHEMA_SQL: &str = r#"
CREATE TABLE IF NOT EXISTS workspace_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL,
    raw_path TEXT,
    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS transforms (
    transform_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    engine TEXT NOT NULL,
    text TEXT NOT NULL,
    loss_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS anchors (
    anchor_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_revision TEXT NOT NULL,
    position TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id TEXT PRIMARY KEY,
    knowledge_type TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_status TEXT,
    anchor_id TEXT REFERENCES anchors(anchor_id),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    receipt_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL REFERENCES knowledge(knowledge_id),
    action TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    state TEXT NOT NULL,            -- canonical job-status vocabulary
    input_ref TEXT,
    engine TEXT,
    loss_receipt TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS learning_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    outcome TEXT NOT NULL,
    next_review TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"#;

/// Open (or create) the vNext database and apply the schema.
/// Per contract this is the only place a writable handle is created.
pub fn init_workspace(db_path: &str) -> rusqlite::Result<Connection> {
    raw_objects::reject_links(std::path::Path::new(db_path))?;
    let mut conn = Connection::open(db_path)?;
    conn.busy_timeout(std::time::Duration::from_secs(5))?;
    // Read the version before any schema or journal write. Never initialize an
    // unrelated legacy database or downgrade a workspace from a future build.
    let has_meta: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='workspace_meta')",
        [], |r| r.get(0),
    )?;
    let version = if has_meta {
        let value: String = conn.query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'", [], |r| r.get(0),
        )?;
        value.parse::<i64>().map_err(|_| rusqlite::Error::InvalidQuery)?
    } else {
        let existing: i64 = conn.query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            [], |r| r.get(0),
        )?;
        if existing != 0 { return Err(rusqlite::Error::InvalidQuery); }
        0
    };
    if !(0..=SCHEMA_VERSION).contains(&version) {
        return Err(rusqlite::Error::InvalidQuery);
    }
    conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    // Another opener may have migrated between the read-only preflight and
    // acquisition of the write transaction. Decide from the locked snapshot.
    let has_meta: bool = tx.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='workspace_meta')",
        [], |r| r.get(0),
    )?;
    let version = if has_meta {
        let value: String = tx.query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'", [], |r| r.get(0),
        )?;
        value.parse::<i64>().map_err(|_| rusqlite::Error::InvalidQuery)?
    } else { 0 };
    if !(0..=SCHEMA_VERSION).contains(&version) {
        return Err(rusqlite::Error::InvalidQuery);
    }
    tx.execute_batch(SCHEMA_SQL)?;
    if version < 2 {
        tx.execute_batch(
            "ALTER TABLE jobs ADD COLUMN completion_digest TEXT;
             ALTER TABLE jobs ADD COLUMN transform_id INTEGER REFERENCES transforms(transform_id);
             UPDATE jobs SET state='succeeded' WHERE state='completed';",
        )?;
    }
    tx.execute(
        "INSERT OR REPLACE INTO workspace_meta(key, value) VALUES('schema_version', ?1)",
        [SCHEMA_VERSION.to_string()],
    )?;
    tx.commit()?;
    Ok(conn)
}

/// Compact workspace info string: schema_version + object counts.
pub fn workspace_info_json(conn: &Connection) -> rusqlite::Result<String> {
    let ver: String = conn.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'",
        [],
        |r| r.get(0),
    )?;
    let counts: (i64, i64, i64, i64, i64) = conn.query_row(
        "SELECT (SELECT count(*) FROM sources),(SELECT count(*) FROM transforms),
                (SELECT count(*) FROM knowledge),(SELECT count(*) FROM anchors),
                (SELECT count(*) FROM learning_events)",
        [],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
    )?;
    let mut s = String::from("{");
    let mut field = |k: &str, v: &str, last: bool| {
        s.push('"');
        s.push_str(k);
        s.push('"');
        s.push(':');
        s.push_str(v);
        if !last {
            s.push(',');
        }
    };
    field("schema_version", &ver, false);
    field("sources", &counts.0.to_string(), false);
    field("transforms", &counts.1.to_string(), false);
    field("knowledge", &counts.2.to_string(), false);
    field("anchors", &counts.3.to_string(), false);
    field("learning_events", &counts.4.to_string(), true);
    s.push('}');
    Ok(s)
}
