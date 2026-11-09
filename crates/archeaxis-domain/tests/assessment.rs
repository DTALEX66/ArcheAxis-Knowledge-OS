use archeaxis_domain::{knowledge, learning};
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
        assert!(!first.question.trim().is_empty());
        assert_ne!(first.question, first.content);
        assert!(!first.question.contains(&first.content));
        assert_eq!(first.question, retry.question);
        assert_eq!(
            first.content,
            "FSRS uses review history to schedule a next review."
        );
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
        &mut conn,
        "FACTUAL_CLAIM",
        "candidate",
        "candidate",
        None,
        None,
        "worker",
    )
    .unwrap();
    learning::record_card_reference(&mut conn, "candidate-card", &candidate, None).unwrap();
    assert!(learning::create_assessment(&mut conn, "candidate-card", &candidate).is_err());
}

#[test]
fn unbound_legacy_review_remains_history_but_is_not_assigned_to_new_assessment() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(
        dir.path()
            .join("legacy-assessment.sqlite")
            .to_str()
            .unwrap(),
    )
    .unwrap();
    let item = "legacy-before-assessment";
    learning::record_review_with_state_and_answer(
        &mut conn,
        item,
        "review",
        true,
        "legacy-event",
        "legacy",
        None,
        None,
        None,
        |_| Ok(fsrs_schedule()),
    )
    .unwrap();
    // A caller may snapshot the unbound card before an assessment is created
    // while its scheduler is running outside the writer transaction.
    let prior_card = learning::latest_fsrs_state_for_assessment(&conn, item, None).unwrap();
    assert_eq!(
        learning::item_keys_with_latest_review(&conn).unwrap(),
        vec![(item.to_string(), Some("2026-10-02T00:00:00+00:00".into()))]
    );
    let knowledge_id = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "Synthetic new assessment",
        "accepted",
        None,
        None,
        "fixture",
    )
    .unwrap();
    learning::record_card_reference(&mut conn, item, &knowledge_id, None).unwrap();
    let assessment = learning::create_assessment(&mut conn, item, &knowledge_id).unwrap();
    let replay = learning::record_review_with_state_and_answer(
        &mut conn,
        item,
        "review",
        true,
        "legacy-event",
        "legacy",
        None,
        None,
        None,
        |_| panic!("a committed legacy receipt must replay without rescheduling"),
    )
    .unwrap();
    assert!(replay.duplicate);
    let stale_unbound = learning::record_review_with_state_and_answer(
        &mut conn,
        item,
        "review",
        true,
        "new-unbound-event",
        "new legacy request",
        None,
        None,
        Some(prior_card),
        |_| panic!("an unbound review must not be scheduled after assessment creation"),
    )
    .unwrap_err();
    assert!(
        stale_unbound
            .to_string()
            .contains("assessment binding conflict")
    );
    assert_eq!(
        learning::item_keys_with_latest_review(&conn).unwrap(),
        vec![(item.to_string(), None)]
    );
    assert!(
        learning::latest_fsrs_state_for_assessment(&conn, item, None)
            .unwrap()
            .is_some()
    );
    assert_eq!(
        learning::latest_fsrs_state_for_assessment(&conn, item, Some(&assessment.assessment_id))
            .unwrap(),
        None
    );
    assert_eq!(
        learning::correct_streak_for_assessment(&conn, item, None).unwrap(),
        1
    );
    assert_eq!(
        learning::correct_streak_for_assessment(&conn, item, Some(&assessment.assessment_id))
            .unwrap(),
        0
    );
    assert_eq!(learning::events_for_item(&conn, item).unwrap().len(), 1);
    assert!(
        learning::events_for_assessment(&conn, item, &assessment.assessment_id)
            .unwrap()
            .is_empty()
    );
}

#[test]
fn newest_assessment_wins_same_second_without_reassigning_the_old_review() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assessment-order.sqlite");
    let (old, revised) = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let old_id = knowledge::create_knowledge(
            &mut conn,
            "FACTUAL_CLAIM",
            "Synthetic original fact",
            "accepted",
            None,
            None,
            "fixture",
        )
        .unwrap();
        let item = "assessment-tie-1";
        learning::record_card_reference(&mut conn, item, &old_id, None).unwrap();
        let mut old = learning::create_assessment(&mut conn, item, &old_id).unwrap();
        learning::record_review_with_state_and_answer(
            &mut conn,
            item,
            "review",
            true,
            "assessment-old-review",
            "synthetic-old-review",
            Some("synthetic old answer"),
            Some(&old.assessment_id),
            None,
            |_| Ok(fsrs_schedule()),
        )
        .unwrap();
        let new_id = knowledge::review(
            &mut conn,
            &old_id,
            "modified",
            "fixture",
            None,
            Some("Synthetic revised fact"),
        )
        .unwrap();
        knowledge::review(&mut conn, &new_id, "accepted", "fixture", None, None).unwrap();
        learning::record_card_reference(&mut conn, item, &new_id, None).unwrap();
        let mut revised = learning::create_assessment(&mut conn, item, &new_id).unwrap();
        // Both ordinary SQLite defaults can have exactly the same second. The
        // fixed IDs make the older digest sort after the newer one, so a digest
        // tie-breaker deterministically exposes the wrong "latest" result.
        assert!(old.assessment_id > revised.assessment_id);
        conn.execute(
            "UPDATE learning_assessments SET created_at='2026-11-09 00:00:00' WHERE item_key=?1",
            [item],
        )
        .unwrap();
        old.created_at = "2026-11-09 00:00:00".into();
        revised.created_at = old.created_at.clone();
        assert_eq!(
            learning::assessment_for_item_key(&conn, item).unwrap(),
            Some(revised.clone())
        );
        assert_eq!(
            learning::assessment_by_id(&conn, &old.assessment_id).unwrap(),
            Some(old.clone())
        );
        let events = learning::events_for_item(&conn, item).unwrap();
        assert_eq!(events.len(), 1);
        let outcome: serde_json::Value = serde_json::from_str(&events[0].2).unwrap();
        assert_eq!(outcome["assessment_id"], old.assessment_id);
        assert_ne!(outcome["assessment_id"], revised.assessment_id);
        assert_eq!(
            learning::create_assessment(&mut conn, item, &new_id).unwrap(),
            revised
        );
        (old, revised)
    };
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        learning::assessment_for_item_key(&conn, "assessment-tie-1").unwrap(),
        Some(revised.clone())
    );
    assert_eq!(
        learning::assessment_by_id(&conn, &old.assessment_id).unwrap(),
        Some(old.clone())
    );
    let snapshot = dir.path().join("assessment-backup.sqlite");
    archeaxis_domain::backup::backup(&conn, snapshot.to_str().unwrap()).unwrap();
    let mut restored =
        init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    assert!(
        archeaxis_domain::backup::restore_authorized(snapshot.to_str().unwrap(), &mut restored)
            .unwrap()
    );
    assert_eq!(
        learning::assessment_for_item_key(&restored, "assessment-tie-1").unwrap(),
        Some(revised)
    );
    assert_eq!(
        learning::assessment_by_id(&restored, &old.assessment_id).unwrap(),
        Some(old.clone())
    );
    let events = learning::events_for_item(&restored, "assessment-tie-1").unwrap();
    assert_eq!(events.len(), 1);
    let outcome: serde_json::Value = serde_json::from_str(&events[0].2).unwrap();
    assert_eq!(outcome["assessment_id"], old.assessment_id);
}

#[test]
fn answered_assessment_persists_fsrs_and_explicitly_open_mastery_projection() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assessment.sqlite");
    let (assessment_id, event_id) = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let knowledge_id = knowledge::create_knowledge(
            &mut conn,
            "FACTUAL_CLAIM",
            "FSRS schedules review.",
            "accepted",
            None,
            None,
            "owner",
        )
        .unwrap();
        learning::record_card_reference(&mut conn, "card-projection", &knowledge_id, None).unwrap();
        let assessment =
            learning::create_assessment(&mut conn, "card-projection", &knowledge_id).unwrap();
        let receipt = learning::record_review_with_state_and_answer(
            &mut conn,
            "card-projection",
            "review",
            true,
            "review-1",
            "canonical-1",
            Some("learner observation"),
            Some(&assessment.assessment_id),
            None,
            |_| Ok(fsrs_schedule()),
        )
        .unwrap();
        (assessment.assessment_id, receipt.event_id)
    };
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    let (_, _, outcome, _) = learning::events_for_item(&conn, "card-projection")
        .unwrap()
        .pop()
        .unwrap();
    let value: serde_json::Value = serde_json::from_str(&outcome).unwrap();
    assert_eq!(value["assessment_id"], assessment_id);
    assert_eq!(value["answer"], "learner observation");
    assert_eq!(value["schedule"]["authority"], "fsrs");
    assert_eq!(value["mastery_projection"]["status"], "projection");
    assert_eq!(value["mastery_projection"]["closed"], false);
    let fsrs_state = learning::latest_fsrs_state_json(&conn, "card-projection")
        .unwrap()
        .unwrap();
    assert!(fsrs_state.contains("\"state\":\"review\""));
    assert!(fsrs_state.contains("\"stability\":30.0"));
    assert_eq!(event_id, 1);
}
