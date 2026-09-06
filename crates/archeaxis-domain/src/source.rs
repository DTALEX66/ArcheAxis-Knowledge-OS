//! Source import: sha256 content addressing + idempotency.
use rusqlite::{Connection, OptionalExtension};
use sha2::{Digest, Sha256};

pub enum ImportOutcome {
    Imported { source_id: String, sha256: String },
    Duplicate { source_id: String, sha256: String },
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(bytes);
    hex::encode(h.finalize())
}

fn stable_id(prefix: &str, seed: &str) -> String {
    let mut h = Sha256::new();
    h.update(seed.as_bytes());
    format!("{}_{}", prefix, &hex::encode(h.finalize())[..24])
}

/// Import raw bytes; duplicate content (same sha256) is idempotent and
/// returns the existing source_id without inserting a second row.
pub fn import_source(
    conn: &mut Connection,
    bytes: &[u8],
    original_name: &str,
    _legacy_raw_path: Option<&str>,
) -> rusqlite::Result<ImportOutcome> {
    let digest = sha256_hex(bytes);
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let raw_ref = archeaxis_store_sqlite::raw_objects::persist(&tx, bytes)?;
    let existing: Option<String> = tx
        .query_row(
            "SELECT source_id FROM sources WHERE sha256=?1",
            [&digest],
            |r| r.get(0),
        )
        .optional()?;
    if let Some(sid) = existing {
        tx.execute("UPDATE sources SET raw_path=?1 WHERE source_id=?2", [&raw_ref, &sid])?;
        tx.commit()?;
        return Ok(ImportOutcome::Duplicate {
            source_id: sid,
            sha256: digest,
        });
    }
    let source_id = stable_id("src", &digest);
    tx.execute(
        "INSERT INTO sources(source_id, sha256, original_name, raw_path) VALUES(?1,?2,?3,?4)",
        rusqlite::params![source_id, digest, original_name, raw_ref],
    )?;
    tx.commit()?;
    Ok(ImportOutcome::Imported {
        source_id,
        sha256: digest,
    })
}

/// Store extracted text as a transform receipt (Python worker extracts;
/// Rust persists the receipt — worker never holds a DB handle).
pub fn record_transform(
    conn: &mut Connection,
    source_id: &str,
    engine: &str,
    text: &str,
    loss_note: Option<&str>,
) -> rusqlite::Result<i64> {
    conn.execute(
        "INSERT INTO transforms(source_id, engine, text, loss_note) VALUES(?1,?2,?3,?4)",
        rusqlite::params![source_id, engine, text, loss_note],
    )?;
    Ok(conn.last_insert_rowid())
}

/// Read the latest non-empty extracted text for a source.
pub fn source_text(conn: &Connection, source_id: &str) -> rusqlite::Result<Option<String>> {
    conn.query_row(
        "SELECT text FROM transforms WHERE source_id=?1 AND length(text)>0 ORDER BY transform_id DESC LIMIT 1",
        [source_id], |r| r.get(0)).optional()
}

pub fn count_sources(conn: &Connection) -> rusqlite::Result<i64> {
    conn.query_row("SELECT count(*) FROM sources", [], |r| r.get(0))
}
