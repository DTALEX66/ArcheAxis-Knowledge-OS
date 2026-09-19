use archeaxis_domain::{learning, knowledge};
use archeaxis_store_sqlite::init_workspace;

#[test]
fn assessment_is_append_only_stable_and_survives_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assessment.sqlite");
    let assessment = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let knowledge_id = knowledge::create_knowledge(
            &mut conn,
            "FACTUAL_CLAIM",
            "FSRS uses review history to schedule a next review.",
            "accepted",
            None,
            None,
            "owner",
        )
        .unwrap();
        learning::record_card_reference(&mut conn, "card-fsrs", &knowledge_id, None).unwrap();
        let first = learning::create_assessment(&mut conn, "card-fsrs", &knowledge_id).unwrap();
        let retry = learning::create_assessment(&mut conn, "card-fsrs", &knowledge_id).unwrap();
        assert_eq!(first.assessment_id, retry.assessment_id);
        assert_eq!(first.knowledge_id, knowledge_id);
        assert!(first.question.contains("请回答"));
        assert_eq!(first.content, "FSRS uses review history to schedule a next review.");
        assert!(first.source_id.is_none());
        assert!(first.anchor_id.is_none());
        first
    };
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    let readback = learning::assessment_by_id(&conn, &assessment.assessment_id)
        .unwrap()
        .unwrap();
    assert_eq!(readback, assessment);
}

#[test]
fn assessment_rejects_non_current_or_unaccepted_knowledge() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("assessment.sqlite").to_str().unwrap()).unwrap();
    let candidate = knowledge::create_knowledge(
        &mut conn, "FACTUAL_CLAIM", "candidate", "candidate", None, None, "worker",
    )
    .unwrap();
    learning::record_card_reference(&mut conn, "candidate-card", &candidate, None).unwrap();
    assert!(learning::create_assessment(&mut conn, "candidate-card", &candidate).is_err());
}
