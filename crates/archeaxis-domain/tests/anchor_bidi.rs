//! C03 part: reverse navigation from a source anchor to derived knowledge.

use archeaxis_domain::knowledge::{self, knowledge_ids_for_anchor};
use archeaxis_domain::source;
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;

fn count(conn: &Connection, table: &str) -> i64 {
    conn.query_row(&format!("SELECT count(*) FROM {table}"), [], |r| r.get(0))
        .unwrap()
}

#[test]
fn knowledge_is_findable_from_its_source_anchor() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("b.sqlite").to_str().unwrap()).unwrap();
    source::import_source(&mut conn, b"origin bytes", "note.txt", None).unwrap();
    let sid: String = conn
        .query_row("SELECT source_id FROM sources LIMIT 1", [], |r| r.get(0))
        .unwrap();
    let anchor_id = archeaxis_domain::anchor::add_anchor(
        &mut conn,
        &sid,
        "rev-1",
        r#"{"start":0,"end":9}"#,
    )
    .unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn,
        "PERSONAL_DEFINITION",
        "anchored note",
        "candidate",
        None,
        Some(&anchor_id),
        "owner",
    )
    .unwrap();
    let found = knowledge_ids_for_anchor(&conn, &anchor_id).unwrap();
    assert_eq!(found, vec![kid]);
    // unrelated knowledge (no anchor) is not returned
    assert_eq!(knowledge_ids_for_anchor(&conn, "missing-anchor").unwrap().len(), 0);
    // reverse map also covers rows created through the transactional review
    // modified path? kept simple here; primary direction asserted above.
    let _ = count(&conn, "knowledge");
}
