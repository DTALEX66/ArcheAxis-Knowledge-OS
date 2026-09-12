//! C03: review is a single transaction - status + event commit together and a
//! modified review creates a new candidate AND records an event on the old row.

use archeaxis_domain::knowledge::{self, is_knowledge_active};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;

fn events_for(conn: &Connection, kid: &str) -> Vec<(String, String)> {
    let mut stmt = conn
        .prepare("SELECT action, reviewer FROM review_events WHERE knowledge_id=?1 ORDER BY event_id")
        .unwrap();
    stmt.query_map([kid], |r| Ok((r.get(0)?, r.get(1)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

#[test]
fn accept_commits_status_and_one_event_atomically() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("k.sqlite").to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "claim", "candidate", None, None, "owner",
    )
    .unwrap();
    let ret = knowledge::review(&mut conn, &kid, "accepted", "owner", Some("checked"), None).unwrap();
    assert_eq!(ret, kid);
    let status: String = conn
        .query_row("SELECT status FROM knowledge WHERE knowledge_id=?1", [&kid], |r| r.get(0))
        .unwrap();
    assert_eq!(status, "accepted");
    assert!(is_knowledge_active(&conn, &kid).unwrap());
    assert_eq!(events_for(&conn, &kid).len(), 1);
}

#[test]
fn modified_creates_candidate_and_records_event_on_original() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("k.sqlite").to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "old text", "candidate", None, None, "owner",
    )
    .unwrap();
    let new_kid = knowledge::review(
        &mut conn,
        &kid,
        "modified",
        "owner",
        Some("corrected"),
        Some("new text"),
    )
    .unwrap();
    assert_ne!(new_kid, kid);
    let events = events_for(&conn, &kid);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].0, "modified");
    // original stays candidate but now HAS a successor: no longer current;
    // the new row is a fresh active candidate.
    assert!(!is_knowledge_active(&conn, &kid).unwrap());
    assert!(is_knowledge_active(&conn, &new_kid).unwrap());
}

#[test]
fn failed_review_leaves_no_partial_state() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("k.sqlite").to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "claim", "candidate", None, None, "owner",
    )
    .unwrap();
    let err = knowledge::review(&mut conn, &kid, "nonsense", "owner", None, None);
    assert!(err.is_err());
    let status: String = conn
        .query_row("SELECT status FROM knowledge WHERE knowledge_id=?1", [&kid], |r| r.get(0))
        .unwrap();
    assert_eq!(status, "candidate", "no partial status change on failed review");
    assert_eq!(events_for(&conn, &kid).len(), 0, "no event on failed review");
}

// REVISION-01: accept/reject/deprecate never overwrite the reviewed body; a
// corrected body must create a new revision via the modified action.
#[test]
fn accept_with_new_body_is_rejected_and_body_stays_immutable() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("k.sqlite").to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "original bytes", "candidate", None, None, "owner",
    )
    .unwrap();
    let err = knowledge::review(
        &mut conn, &kid, "accepted", "owner", Some("try to sneak a body change"), Some("rewritten body"),
    );
    assert!(err.is_err(), "accept must not carry a body change");
    let (status, body): (String, String) = conn
        .query_row(
            "SELECT status, body FROM knowledge WHERE knowledge_id=?1",
            [&kid],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(status, "candidate", "failed mixed review changes nothing");
    assert_eq!(body, "original bytes", "reviewed bytes are immutable");
    assert_eq!(events_for(&conn, &kid).len(), 0);

    // The pure accept path still works and leaves body untouched.
    let ret = knowledge::review(&mut conn, &kid, "accepted", "owner", Some("clean accept"), None).unwrap();
    assert_eq!(ret, kid);
    let body: String = conn
        .query_row("SELECT body FROM knowledge WHERE knowledge_id=?1", [&kid], |r| r.get(0))
        .unwrap();
    assert_eq!(body, "original bytes");
}
