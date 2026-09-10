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

/// Provenance of one reported origin of a source. `received_at` is optional:
/// when the caller genuinely does not know it, it must stay `None` and the
/// stored cell stays NULL - a clock value is never fabricated.
#[derive(Debug, Clone, Copy)]
pub struct OriginInfo<'a> {
    pub kind: &'a str,
    pub origin_ref: &'a str,
    pub original_name: Option<&'a str>,
    pub received_at: Option<&'a str>,
}

/// The origin kinds the store's CHECK constraint accepts. Validated here because the
/// insert uses `INSERT OR IGNORE`: an out-of-vocabulary kind would be dropped in
/// silence, which looks like "the provenance was recorded" when it was not.
pub const ORIGIN_KINDS: &[&str] = &["path", "url", "import", "manual"];

fn record_origin(
    tx: &rusqlite::Transaction<'_>,
    source_id: &str,
    origin: OriginInfo<'_>,
) -> rusqlite::Result<()> {
    if !ORIGIN_KINDS.contains(&origin.kind) {
        return Err(rusqlite::Error::InvalidParameterName(format!(
            "origin kind {:?} is not one of {ORIGIN_KINDS:?}; the store would ignore the row in silence",
            origin.kind
        )));
    }
    tx.execute(
        "INSERT OR IGNORE INTO source_origins
            (source_id, origin_kind, origin_ref, original_name, received_at)
         VALUES(?1,?2,?3,?4,?5)",
        rusqlite::params![
            source_id,
            origin.kind,
            origin.origin_ref,
            origin.original_name,
            origin.received_at,
        ],
    )?;
    Ok(())
}

/// Import raw bytes with optional reported origin metadata; duplicate content
/// (same sha256) is idempotent for the content row and additionally keeps
/// every distinct reported origin (same bytes from different places must not
/// lose the later origin's semantics).
pub fn import_source(
    conn: &mut Connection,
    bytes: &[u8],
    original_name: &str,
    legacy_raw_path: Option<&str>,
) -> rusqlite::Result<ImportOutcome> {
    import_source_with_origin(conn, bytes, original_name, legacy_raw_path, None)
}

/// Like [`import_source`], but records the reported origin when provided.
pub fn import_source_with_origin(
    conn: &mut Connection,
    bytes: &[u8],
    original_name: &str,
    _legacy_raw_path: Option<&str>,
    origin: Option<OriginInfo<'_>>,
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
        if let Some(info) = origin {
            record_origin(&tx, &sid, info)?;
        }
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
    if let Some(info) = origin {
        record_origin(&tx, &source_id, info)?;
    }
    tx.commit()?;
    Ok(ImportOutcome::Imported {
        source_id,
        sha256: digest,
    })
}

/// Read the recorded origins for a source (empty when none were reported).
pub fn list_origins(
    conn: &Connection,
    source_id: &str,
) -> rusqlite::Result<Vec<(String, String, Option<String>, Option<String>)>> {
    let mut stmt = conn.prepare(
        "SELECT origin_kind, origin_ref, original_name, received_at
         FROM source_origins WHERE source_id=?1 ORDER BY imported_at, rowid",
    )?;
    let rows = stmt.query_map([source_id], |r| {
        Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?))
    })?;
    rows.collect()
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
