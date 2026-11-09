use archeaxis_store_sqlite::{SCHEMA_VERSION, init_workspace};
use rusqlite::Connection;

fn history(conn: &Connection) -> Vec<(i64, String, String, String, Option<String>, String)> {
    let mut stmt = conn.prepare(
        "SELECT event_id,item_key,kind,outcome,next_review,created_at FROM learning_events ORDER BY event_id",
    ).unwrap();
    stmt.query_map([], |row| {
        Ok((
            row.get(0)?,
            row.get(1)?,
            row.get(2)?,
            row.get(3)?,
            row.get(4)?,
            row.get(5)?,
        ))
    })
    .unwrap()
    .collect::<rusqlite::Result<_>>()
    .unwrap()
}

#[test]
fn existing_workspace_gains_learning_event_index_without_rewriting_history() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("existing.sqlite");
    let conn = init_workspace(path.to_str().unwrap()).unwrap();
    for (item, next_review) in [
        ("alpha", Some("2026-09-10T00:00:00Z")),
        ("beta", None),
        ("alpha", None),
    ] {
        conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,?3)",
                     rusqlite::params![item, "{\"fixture\":true}", next_review]).unwrap();
    }
    let before = history(&conn);
    conn.execute_batch("DROP INDEX IF EXISTS learning_events_item_event_idx;")
        .unwrap();
    drop(conn);
    let reopened = init_workspace(path.to_str().unwrap()).unwrap();
    let version: String = reopened
        .query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(version, SCHEMA_VERSION.to_string());
    assert_eq!(history(&reopened), before);
    let columns = reopened
        .prepare(
            "SELECT name FROM pragma_index_info('learning_events_item_event_idx') ORDER BY seqno",
        )
        .unwrap()
        .query_map([], |row| row.get::<_, String>(0))
        .unwrap()
        .collect::<rusqlite::Result<Vec<_>>>()
        .unwrap();
    assert_eq!(columns, ["item_key", "event_id"]);
    let plan: String = reopened.query_row(
        "EXPLAIN QUERY PLAN SELECT event_id FROM learning_events WHERE item_key=?1 ORDER BY event_id", ["alpha"], |r| r.get(3),
    ).unwrap();
    assert!(plan.contains("learning_events_item_event_idx"), "{plan}");
    assert_eq!(
        reopened
            .query_row("SELECT count(*) FROM pragma_foreign_key_check", [], |r| r
                .get::<_, i64>(
                0
            ))
            .unwrap(),
        0
    );
    drop(reopened);
    let again = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(history(&again), before);
    assert_eq!(again.query_row("SELECT count(*) FROM sqlite_master WHERE type='index' AND name='learning_events_item_event_idx'", [], |r| r.get::<_, i64>(0)).unwrap(), 1);
}
