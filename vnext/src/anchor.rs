//! Anchors: jump-back locators into a specific source revision.
use rusqlite::{Connection, OptionalExtension};
use sha2::{Digest, Sha256};

fn id(seed: &str) -> String {
    let mut h = Sha256::new();
    h.update(seed.as_bytes());
    format!("anc_{}", &hex::encode(h.finalize())[..24])
}

/// Save an anchor (source + revision + position). Returns its id.
pub fn add_anchor(
    conn: &mut Connection,
    source_id: &str,
    source_revision: &str,
    position_json: &str,
) -> rusqlite::Result<String> {
    let seed = format!("{source_id}|{source_revision}|{position_json}");
    let anchor_id = id(&seed);
    conn.execute(
        "INSERT OR IGNORE INTO anchors(anchor_id, source_id, source_revision, position) VALUES(?1,?2,?3,?4)",
        rusqlite::params![anchor_id, source_id, source_revision, position_json],
    )?;
    Ok(anchor_id)
}

/// Fetch (source_id, source_revision, position) for an anchor.
pub fn get_anchor(conn: &Connection, anchor_id: &str) -> rusqlite::Result<Option<(String, String, String)>> {
    conn.query_row(
        "SELECT source_id, source_revision, position FROM anchors WHERE anchor_id=?1",
        [anchor_id], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?))).optional()
}
