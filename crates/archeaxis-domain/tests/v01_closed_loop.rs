//! v0.1 closed-loop integration test (data layer, Rust sole writer).
//!
//! Mirrors the twelve-step vNext loop at the Core level: init -> import
//! (sha256 idempotent) -> transform -> anchor -> personal definition +
//! machine candidate -> accept -> FTS5 retrieval -> learning event ->
//! restart read-back (fresh connection) -> online backup -> restore into a
//! fresh workspace with identical counts.

use archeaxis_domain::{ImportOutcome, anchor, backup, knowledge, learning, search, source};
use archeaxis_store_sqlite::{init_workspace, workspace_info_json};
use rusqlite::Connection;

#[test]
fn v01_closed_loop_restart_and_restore() {
    let dir = tempfile::tempdir().unwrap();
    let db_a = dir.path().join("workspace_a.sqlite");
    let db_b = dir.path().join("workspace_b.sqlite");
    let snapshot = dir.path().join("snapshot.sqlite");

    // 1) workspace init (schema + WAL)
    let mut conn = init_workspace(db_a.to_str().unwrap()).unwrap();

    // 2) import two sources; repeat import is idempotent (same sha256)
    let bytes1 = b"progress notebook: record errors and wins daily".to_vec();
    let bytes2 = b"memory palace: spatial encoding improves recall".to_vec();
    let o1 = source::import_source(&mut conn, &bytes1, "progress.txt", None).unwrap();
    let src1 = match &o1 {
        ImportOutcome::Imported { source_id, .. } => source_id.clone(),
        ImportOutcome::Duplicate { .. } => panic!("first import must import"),
    };
    let dup = source::import_source(&mut conn, &bytes1, "progress-again.txt", None).unwrap();
    assert!(
        matches!(dup, ImportOutcome::Duplicate { .. }),
        "repeat import must be idempotent"
    );
    let src2 = match source::import_source(&mut conn, &bytes2, "palace.txt", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } => source_id,
        ImportOutcome::Duplicate { .. } => panic!("second import must import"),
    };
    assert_eq!(source::count_sources(&conn).unwrap(), 2);

    // 3) transform receipts (worker extracts; Rust persists)
    source::record_transform(
        &mut conn,
        &src1,
        "python-worker",
        "progress notebook: record errors and wins daily",
        None,
    )
    .unwrap();
    source::record_transform(
        &mut conn,
        &src2,
        "python-worker",
        "memory palace: spatial encoding improves recall",
        None,
    )
    .unwrap();

    // 4) anchor a sentence in source 1
    let anchor_id =
        anchor::add_anchor(&mut conn, &src1, "rev-1", r#"{"start":10,"end":34}"#).unwrap();
    let got = anchor::get_anchor(&conn, &anchor_id).unwrap().unwrap();
    assert_eq!(got.0, src1);

    // 5) personal definition (no external evidence required) + machine candidate
    let personal = knowledge::create_knowledge(
        &mut conn,
        "PERSONAL_DEFINITION",
        "进步本：每天记录错误与突破，作为刻意练习的反馈回路。",
        "accepted",
        None,
        Some(&anchor_id),
        "owner",
    )
    .unwrap();
    let candidate = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "记忆宫殿是空间记忆法的统称（机器候选，未经人工复核）。",
        "candidate",
        Some("UNSOURCED"),
        None,
        "python-worker",
    )
    .unwrap();

    // 6) accept the candidate -> immutable receipt; reject path is exercised too
    let accepted = knowledge::review(
        &mut conn,
        &candidate,
        "accepted",
        "owner",
        Some("核实来源"),
        None,
    )
    .unwrap();
    let reject_me = knowledge::create_knowledge(
        &mut conn,
        "OPINION",
        "随机观点：不参与验收",
        "candidate",
        None,
        None,
        "python-worker",
    )
    .unwrap();
    knowledge::review(
        &mut conn,
        &reject_me,
        "rejected",
        "owner",
        Some("无关"),
        None,
    )
    .unwrap();
    assert_eq!(accepted, candidate, "accept returns same knowledge id");
    let counts = knowledge::status_counts(&conn).unwrap();
    assert!(
        counts.contains("\"accepted\":2"),
        "expected 2 accepted, got {counts}"
    );

    // 7) FTS5 retrieval finds accepted + candidate rows
    search::reindex(&conn).unwrap();
    let hits = search::search(&conn, "记忆宫殿 OR 进步本", 10).unwrap();
    assert!(!hits.is_empty(), "FTS5 should hit at least one row");

    // 8) learning event + next review hint
    let ev = learning::record_learning_event(
        &mut conn,
        &personal,
        "quiz",
        r#"{"correct":true,"score":1.0}"#,
        2,
    )
    .unwrap();
    assert!(ev > 0);
    assert_eq!(learning::suggest_next_interval(3), 7);

    // 9) restart read-back: fresh connection to the SAME file
    drop(conn);
    let conn = init_workspace(db_a.to_str().unwrap()).unwrap();
    let info = workspace_info_json(&conn).unwrap();
    assert!(info.contains("\"sources\":2"));
    assert!(
        info.contains("\"knowledge\":3"),
        "personal + accepted-candidate + rejected-opinion rows: {info}"
    );
    assert!(info.contains("\"learning_events\":1"));
    let text = source::source_text(&conn, &src1).unwrap().unwrap();
    assert!(text.contains("progress notebook"));

    // 10) online backup (consistent snapshot)
    backup::backup(&conn, snapshot.to_str().unwrap()).unwrap();
    let snap = Connection::open(snapshot.to_str().unwrap()).unwrap();
    assert!(backup::verify_counts(&conn, &snap).unwrap());

    // 11) restore into a fresh workspace -> identical counts
    let mut conn_b = init_workspace(db_b.to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut conn_b).unwrap();
    let snap2 = Connection::open(snapshot.to_str().unwrap()).unwrap();
    assert!(backup::verify_counts(&conn_b, &snap2).unwrap());
    assert_eq!(source::count_sources(&conn_b).unwrap(), 2);
}
