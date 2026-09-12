//! X09 minimal real side: qualification check before reusing a knowledge unit
//! as current context (deprecated/rejected must not stay "active").

use archeaxis_domain::knowledge::{self, is_knowledge_active};
use archeaxis_store_sqlite::init_workspace;

#[test]
fn only_candidate_or_accepted_rows_are_active() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("k.sqlite").to_str().unwrap()).unwrap();

    let active = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "active claim", "candidate", None, None, "owner",
    )
    .unwrap();
    assert!(is_knowledge_active(&conn, &active).unwrap());

    let accepted = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "accepted claim", "candidate", None, None, "owner",
    )
    .unwrap();
    knowledge::review(&mut conn, &accepted, "accepted", "owner", Some("checked"), None)
        .unwrap();
    assert!(is_knowledge_active(&conn, &accepted).unwrap());

    let deprecated = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "old claim", "candidate", None, None, "owner",
    )
    .unwrap();
    knowledge::review(&mut conn, &deprecated, "deprecated", "owner", Some("superseded"), None)
        .unwrap();
    assert!(!is_knowledge_active(&conn, &deprecated).unwrap());

    let rejected = knowledge::create_knowledge(
        &mut conn, "OPINION", "wrong opinion", "candidate", None, None, "owner",
    )
    .unwrap();
    knowledge::review(&mut conn, &rejected, "rejected", "owner", Some("not usable"), None)
        .unwrap();
    assert!(!is_knowledge_active(&conn, &rejected).unwrap());

    assert!(!is_knowledge_active(&conn, "k_missing").unwrap());
}
