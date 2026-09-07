//! C03 part3: revision supersedes chain from modified reviews.

use archeaxis_domain::knowledge::{self, knowledge_successors};
use archeaxis_store_sqlite::init_workspace;

#[test]
fn modified_creates_traceable_successor() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "v1", "candidate", None, None, "owner",
    )
    .unwrap();
    let kid2 = knowledge::review(&mut conn, &kid, "modified", "owner", Some("fix"), Some("v2")).unwrap();
    assert_ne!(kid, kid2);
    assert_eq!(knowledge_successors(&conn, &kid).unwrap(), vec![kid2.clone()]);
    // accept the successor so the chain becomes usable
    knowledge::review(&mut conn, &kid2, "accepted", "owner", Some("ok"), None).unwrap();
    assert!(knowledge::is_knowledge_active(&conn, &kid2).unwrap());
    // the old row is still active=false? old was candidate; keep as history with
    // a successor; deprecation of superseded old row is a consumer decision.
    assert_eq!(knowledge_successors(&conn, &kid2).unwrap().len(), 0);
}
