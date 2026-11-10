//! P05 / A07: the schedule may be computed outside the writer, so recording a
//! review carries the card snapshot it was computed from. If that snapshot is no
//! longer current, the write must be rejected rather than silently overwriting a
//! newer schedule with a stale one.

use archeaxis_domain::learning::{self, ReviewSchedule, SCHEDULE_UNAVAILABLE};
use archeaxis_store_sqlite::init_workspace;

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("basis.sqlite").to_str().unwrap()).unwrap();
    (dir, conn)
}

// An explicitly unscheduled (unavailable-scheduler) result is always valid to record, so the
// assertions below are about the basis guard, not about scheduling arithmetic.
fn unscheduled() -> ReviewSchedule {
    ReviewSchedule {
        schedule_json: serde_json::json!({ "authority": "unavailable" }).to_string(),
        next_review: None,
        next_review_days: SCHEDULE_UNAVAILABLE,
    }
}

#[test]
fn matching_basis_records_and_mismatched_basis_is_rejected() {
    let (_dir, mut conn) = workspace();
    // The item has no prior FSRS card, so the correct basis is "no state".
    assert_eq!(
        learning::latest_fsrs_state_json(&conn, "card").unwrap(),
        None
    );

    let ok = learning::record_review_with_state_and_answer(
        &mut conn,
        "card",
        "review",
        true,
        "key-match",
        "canonical-match",
        None,
        None,
        Some(None),
        |_| Ok(unscheduled()),
    )
    .expect("a schedule computed from the current (absent) basis records normally");
    assert!(!ok.duplicate);

    // A stale, non-null basis must be refused: it never reaches the insert.
    let stale = learning::record_review_with_state_and_answer(
        &mut conn,
        "card",
        "review",
        true,
        "key-stale",
        "canonical-stale",
        None,
        None,
        Some(Some("{}".to_string())),
        |_| panic!("a rejected basis must not resolve a schedule"),
    );
    match stale {
        Err(rusqlite::Error::InvalidParameterName(message)) => {
            assert!(message.starts_with("schedule basis conflict"), "{message}");
        }
        other => panic!("expected a schedule basis conflict, got {other:?}"),
    }
    // The refused review left no second event behind.
    assert_eq!(learning::events_for_item(&conn, "card").unwrap().len(), 1);
}

#[test]
fn unguarded_callers_keep_their_previous_behaviour() {
    let (_dir, mut conn) = workspace();
    // Passing no expectation never checks the basis, matching the legacy wrapper path.
    let result = learning::record_review_with_state_and_answer(
        &mut conn,
        "card",
        "review",
        true,
        "key-unguarded",
        "canonical-unguarded",
        None,
        None,
        None,
        |_| Ok(unscheduled()),
    )
    .expect("unguarded callers are unaffected by the new basis parameter");
    assert_eq!(result.next_review_days, SCHEDULE_UNAVAILABLE);
}

#[test]
fn assessment_scoped_basis_ignores_other_versions_but_rejects_its_own_stale_state() {
    let (_dir, mut conn) = workspace();
    let fsrs = || {
        ReviewSchedule {
        schedule_json: r#"{"authority":"fsrs","state":{"state":"review","step":null,"stability":30.0,"difficulty":3.0,"last_review":"2026-09-02T00:00:00+00:00","due":"2026-10-02T00:00:00+00:00"}}"#.into(),
        next_review: Some("2026-10-02T00:00:00+00:00".into()),
        next_review_days: 30,
    }
    };
    learning::record_review_with_state_and_answer(
        &mut conn,
        "card",
        "review",
        true,
        "old-version",
        "old",
        Some("old"),
        Some("assessment-old"),
        Some(None),
        |_| Ok(fsrs()),
    )
    .unwrap();
    assert!(
        learning::latest_fsrs_state_for_assessment(&conn, "card", Some("assessment-old"))
            .unwrap()
            .is_some()
    );
    assert_eq!(
        learning::latest_fsrs_state_for_assessment(&conn, "card", Some("assessment-new")).unwrap(),
        None
    );
    let new = learning::record_review_with_state_and_answer(
        &mut conn,
        "card",
        "review",
        true,
        "new-version",
        "new",
        Some("new"),
        Some("assessment-new"),
        Some(None),
        |_| Ok(fsrs()),
    )
    .unwrap();
    assert_eq!(new.streak_after, 1);
    let projection: serde_json::Value = serde_json::from_str(&new.outcome_json).unwrap();
    assert_eq!(projection["mastery_projection"]["attempts"], 1);
    assert_eq!(learning::correct_streak(&conn, "card").unwrap(), 2); // legacy item history
    assert_eq!(
        learning::correct_streak_for_assessment(&conn, "card", Some("assessment-new")).unwrap(),
        1
    );
    let stale = learning::record_review_with_state_and_answer(
        &mut conn,
        "card",
        "review",
        true,
        "new-stale",
        "new-stale",
        None,
        Some("assessment-new"),
        Some(None),
        |_| panic!("stale assessment basis must not schedule"),
    );
    assert!(
        matches!(stale, Err(rusqlite::Error::InvalidParameterName(message)) if message.starts_with("schedule basis conflict"))
    );
    assert_eq!(learning::events_for_item(&conn, "card").unwrap().len(), 2);
}
