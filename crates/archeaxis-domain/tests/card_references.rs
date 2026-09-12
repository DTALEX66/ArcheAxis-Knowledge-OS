//! R09: a learning item records the knowledge revision it was created from, and
//! after that revision is superseded the read-side annotation reports it as no
//! longer current - while the historical reference is preserved, never rewritten.

use archeaxis_domain::learning;
use archeaxis_domain::knowledge;
use archeaxis_store_sqlite::init_workspace;

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    (dir, conn)
}

#[test]
fn a_card_keeps_its_revision_and_is_annotated_after_supersede() {
    let (_dir, mut conn) = workspace();
    let original = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "the radius is 6371 km",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    knowledge::review(&mut conn, &original, "accepted", "owner", None, None).unwrap();
    learning::record_card_reference(&mut conn, "card-1", &original, Some(1)).unwrap();

    // While the referenced revision is current, the annotation says so.
    assert_eq!(
        learning::references_for_card(&conn, "card-1").unwrap(),
        vec![(original.clone(), true)]
    );

    // A later revision supersedes it; the card reference is NOT rewritten.
    let successor = knowledge::review(
        &mut conn,
        &original,
        "modified",
        "owner",
        Some("correction"),
        Some("the radius is 6371.0088 km"),
    )
    .unwrap();
    knowledge::review(&mut conn, &successor, "accepted", "owner", None, None).unwrap();

    let references = learning::references_for_card(&conn, "card-1").unwrap();
    assert_eq!(references.len(), 1, "the historical reference must be preserved");
    assert_eq!(references[0].0, original, "it still names the revision the card was built from");
    assert!(
        !references[0].1,
        "after supersede the referenced revision must be reported as not current"
    );
    assert!(knowledge::is_knowledge_active(&conn, &successor).unwrap());

    // Recording the same reference again stays idempotent (retries cannot grow it).
    learning::record_card_reference(&mut conn, "card-1", &original, Some(2)).unwrap();
    assert_eq!(learning::references_for_card(&conn, "card-1").unwrap().len(), 1);

    // A reference to a revision that does not exist is refused.
    assert!(learning::record_card_reference(&mut conn, "card-2", "k_missing", None).is_err());
    // Empty keys are refused rather than recorded as an anonymous link.
    assert!(learning::record_card_reference(&mut conn, "  ", &original, None).is_err());
}

#[test]
fn the_annotation_survives_a_workspace_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("reopen.sqlite");
    let original;
    {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        original = knowledge::create_knowledge(
            &mut conn,
            "PERSONAL_DEFINITION",
            "my own note",
            "accepted",
            None,
            None,
            "owner",
        )
        .unwrap();
        learning::record_card_reference(&mut conn, "card-r", &original, None).unwrap();
    }
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        learning::references_for_card(&conn, "card-r").unwrap(),
        vec![(original, true)],
        "restart must not lose the reference or change its validity"
    );
}
