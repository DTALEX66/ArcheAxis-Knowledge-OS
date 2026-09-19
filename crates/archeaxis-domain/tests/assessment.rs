use archeaxis_domain::{learning, knowledge};
use archeaxis_store_sqlite::init_workspace;

fn fsrs_schedule() -> learning::ReviewSchedule {
    learning::ReviewSchedule {
        schedule_json: r#"{"authority":"fsrs","state":{"state":"review","step":null,"stability":30.0,"difficulty":3.0,"last_review":"2026-09-02T00:00:00+00:00","due":"2026-10-02T00:00:00+00:00"}}"#.into(),
        next_review: Some("2026-10-02T00:00:00+00:00".into()),
        next_review_days: 30,
    }
}

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

#[test]
fn answered_assessment_persists_fsrs_and_explicitly_open_mastery_projection() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assessment.sqlite");
    let (assessment_id, event_id) = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let knowledge_id = knowledge::create_knowledge(
            &mut conn, "FACTUAL_CLAIM", "FSRS schedules review.", "accepted", None, None, "owner",
        ).unwrap();
        learning::record_card_reference(&mut conn, "card-projection", &knowledge_id, None).unwrap();
        let assessment = learning::create_assessment(&mut conn, "card-projection", &knowledge_id).unwrap();
        let receipt = learning::record_review_with_state_and_answer(
            &mut conn, "card-projection", "review", true, "review-1", "canonical-1",
            Some("learner observation"), Some(&assessment.assessment_id), |_| Ok(fsrs_schedule()),
        ).unwrap();
        (assessment.assessment_id, receipt.event_id)
    };
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    let (_, _, outcome, _) = learning::events_for_item(&conn, "card-projection").unwrap().pop().unwrap();
    let value: serde_json::Value = serde_json::from_str(&outcome).unwrap();
    assert_eq!(value["assessment_id"], assessment_id);
    assert_eq!(value["answer"], "learner observation");
    assert_eq!(value["schedule"]["authority"], "fsrs");
    assert_eq!(value["mastery_projection"]["status"], "projection");
    assert_eq!(value["mastery_projection"]["closed"], false);
    let fsrs_state = learning::latest_fsrs_state_json(&conn, "card-projection").unwrap().unwrap();
    assert!(fsrs_state.contains("\"state\":\"review\""));
    assert!(fsrs_state.contains("\"stability\":30.0"));
    assert_eq!(event_id, 1);
}
