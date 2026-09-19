//! vNext database schema and workspace init (Rust sole writer).
use rusqlite::Connection;

pub mod raw_objects;
pub mod writer;

// Assessment and the V3 governance sidecar are additive schema changes.
pub const SCHEMA_VERSION: i64 = 6;

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
CREATE TABLE IF NOT EXISTS source_origins (
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    origin_kind TEXT NOT NULL CHECK(origin_kind IN ('path','url','import','manual')),
    origin_ref TEXT NOT NULL,
    original_name TEXT,
    received_at TEXT,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(source_id, origin_kind, origin_ref)
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
CREATE TABLE IF NOT EXISTS knowledge_v3_metadata (
    knowledge_id TEXT PRIMARY KEY REFERENCES knowledge(knowledge_id),
    source_type TEXT NOT NULL CHECK(source_type IN (
        'personal_experience','personal_note','personal_definition',
        'project_observation','external_document','authoritative_reference',
        'derived_inference','machine_candidate','imported_legacy','research_result'
    )),
    owner TEXT NOT NULL CHECK(owner IN ('human','machine','system')),
    support_level TEXT NOT NULL CHECK(support_level IN ('none','weak','moderate','strong','authoritative')),
    confidence REAL CHECK(confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    risk_level TEXT NOT NULL CHECK(risk_level IN ('low','medium','high','critical')),
    valid_from TEXT,
    valid_to TEXT,
    external_evidence TEXT NOT NULL DEFAULT '[]',
    requires_human_review INTEGER NOT NULL CHECK(requires_human_review IN (0,1)),
    CHECK(valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from)
);
CREATE TABLE IF NOT EXISTS knowledge_supersedes (
    old_knowledge_id TEXT NOT NULL REFERENCES knowledge(knowledge_id),
    new_knowledge_id TEXT NOT NULL REFERENCES knowledge(knowledge_id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(old_knowledge_id, new_knowledge_id)
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
CREATE TABLE IF NOT EXISTS learning_event_keys (
    event_key TEXT PRIMARY KEY,
    item_key TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    payload_hash TEXT,
    event_id INTEGER,
    streak_after INTEGER,
    next_review_days INTEGER
);
CREATE TABLE IF NOT EXISTS learning_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    outcome TEXT NOT NULL,
    next_review TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS learning_assessments (
    assessment_id TEXT PRIMARY KEY,
    item_key TEXT NOT NULL,
    knowledge_id TEXT NOT NULL REFERENCES knowledge(knowledge_id),
    knowledge_version TEXT NOT NULL,
    question TEXT NOT NULL,
    content TEXT NOT NULL,
    source_id TEXT REFERENCES sources(source_id),
    anchor_id TEXT REFERENCES anchors(anchor_id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(item_key, knowledge_id)
);
CREATE TABLE IF NOT EXISTS job_attempts (
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    attempt INTEGER NOT NULL CHECK(attempt > 0),
    request_id TEXT NOT NULL UNIQUE,
    request_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('running','succeeded','failed','rejected','cancelled')),
    response_json TEXT,
    result_digest TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    PRIMARY KEY(job_id, attempt)
);
CREATE TABLE IF NOT EXISTS job_outputs (
    job_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    kind TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY(job_id, attempt, kind),
    FOREIGN KEY(job_id, attempt) REFERENCES job_attempts(job_id, attempt)
);
CREATE TABLE IF NOT EXISTS canvas_projections (
    canvas_id TEXT PRIMARY KEY,
    source_job_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS canvas_projection_nodes (
    canvas_id TEXT NOT NULL REFERENCES canvas_projections(canvas_id),
    node_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    x REAL NOT NULL DEFAULT 0,
    y REAL NOT NULL DEFAULT 0,
    width REAL NOT NULL DEFAULT 300,
    height REAL NOT NULL DEFAULT 200,
    PRIMARY KEY(canvas_id, node_id)
);
CREATE TABLE IF NOT EXISTS canvas_projection_edges (
    canvas_id TEXT NOT NULL REFERENCES canvas_projections(canvas_id),
    edge_id TEXT NOT NULL,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    color TEXT NOT NULL DEFAULT '#888',
    PRIMARY KEY(canvas_id, edge_id)
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
    if version < 4 {
        // EVENT-01: persist the canonical payload identity and the original
        // receipt alongside each dedup key so a replay can return exactly the
        // first outcome and a conflicting payload is rejected, not deduped.
        // A fresh database created by SCHEMA_SQL already has the columns, so
        // guard each ALTER on the live table shape.
        let has_payload: bool = tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM pragma_table_info('learning_event_keys') WHERE name='payload_hash')",
            [], |r| r.get(0),
        )?;
        if !has_payload {
            tx.execute_batch(
                "ALTER TABLE learning_event_keys ADD COLUMN payload_hash TEXT;
                 ALTER TABLE learning_event_keys ADD COLUMN event_id INTEGER;
                 ALTER TABLE learning_event_keys ADD COLUMN streak_after INTEGER;
                 ALTER TABLE learning_event_keys ADD COLUMN next_review_days INTEGER;",
            )?;
        }
    }
    if version < 6 {
        tx.execute_batch(
            "CREATE TABLE IF NOT EXISTS knowledge_v3_metadata (
                knowledge_id TEXT PRIMARY KEY REFERENCES knowledge(knowledge_id),
                source_type TEXT NOT NULL CHECK(source_type IN (
                    'personal_experience','personal_note','personal_definition',
                    'project_observation','external_document','authoritative_reference',
                    'derived_inference','machine_candidate','imported_legacy','research_result'
                )),
                owner TEXT NOT NULL CHECK(owner IN ('human','machine','system')),
                support_level TEXT NOT NULL CHECK(support_level IN ('none','weak','moderate','strong','authoritative')),
                confidence REAL CHECK(confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
                risk_level TEXT NOT NULL CHECK(risk_level IN ('low','medium','high','critical')),
                valid_from TEXT,
                valid_to TEXT,
                external_evidence TEXT NOT NULL DEFAULT '[]',
                requires_human_review INTEGER NOT NULL CHECK(requires_human_review IN (0,1)),
                CHECK(valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from)
            );"
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
