//! X09 minimal real side: qualification check before reusing a knowledge unit
//! as current context (deprecated/rejected must not stay "active").

use archeaxis_domain::knowledge::{self, is_knowledge_active};
use archeaxis_store_sqlite::init_workspace;

#[test]
fn only_candidate_or_accepted_rows_are_active() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("k.sqlite").to_str().unwrap()).unwrap();

    let active = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "active claim",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    assert!(is_knowledge_active(&conn, &active).unwrap());

    let accepted = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "accepted claim",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    knowledge::review(
        &mut conn,
        &accepted,
        "accepted",
        "owner",
        Some("checked"),
        None,
    )
    .unwrap();
    assert!(is_knowledge_active(&conn, &accepted).unwrap());

    let deprecated = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "old claim",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    knowledge::review(
        &mut conn,
        &deprecated,
        "deprecated",
        "owner",
        Some("superseded"),
        None,
    )
    .unwrap();
    assert!(!is_knowledge_active(&conn, &deprecated).unwrap());

    let rejected = knowledge::create_knowledge(
        &mut conn,
        "OPINION",
        "wrong opinion",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    knowledge::review(
        &mut conn,
        &rejected,
        "rejected",
        "owner",
        Some("not usable"),
        None,
    )
    .unwrap();
    assert!(!is_knowledge_active(&conn, &rejected).unwrap());

    assert!(!is_knowledge_active(&conn, "k_missing").unwrap());
}

#[test]
fn currentness_separates_the_identity_from_its_use_state() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("c.sqlite").to_str().unwrap()).unwrap();

    let candidate = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "current claim",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    let view = knowledge::currentness(&conn, &candidate)
        .unwrap()
        .expect("row exists");
    assert_eq!(view.status, "candidate");
    assert_eq!(view.currentness, "current");
    assert!(view.active);
    assert_eq!(view.superseded_by, None);
    assert_eq!(view.successor_count, 0);
    assert_eq!(view.valid_to, None);

    let successor = knowledge::review(
        &mut conn,
        &candidate,
        "modified",
        "owner",
        Some("fix"),
        Some("corrected claim"),
    )
    .unwrap();
    knowledge::review(&mut conn, &successor, "accepted", "owner", None, None).unwrap();
    let historical = knowledge::currentness(&conn, &candidate)
        .unwrap()
        .expect("the historical row still exists");
    assert_eq!(historical.currentness, "superseded");
    assert!(!historical.active, "a row with a successor is not current");
    assert_eq!(
        historical.superseded_by.as_deref(),
        Some(successor.as_str())
    );
    assert_eq!(historical.successor_count, 1);
    let current = knowledge::currentness(&conn, &successor).unwrap().unwrap();
    assert_eq!(current.currentness, "current");
    assert_eq!(current.status, "accepted");

    let rejected = knowledge::create_knowledge(
        &mut conn,
        "OPINION",
        "wrong opinion",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    knowledge::review(&mut conn, &rejected, "rejected", "owner", None, None).unwrap();
    let refused = knowledge::currentness(&conn, &rejected).unwrap().unwrap();
    assert_eq!(refused.currentness, "not_current");
    assert_eq!(refused.status, "rejected");

    // Missing is `None`, which is different from an existing but non-current row.
    assert_eq!(knowledge::currentness(&conn, "k_missing").unwrap(), None);
}
