use archeaxis_domain::learning::{self, ReviewSchedule};
use archeaxis_store_sqlite::init_workspace;

fn schedule() -> ReviewSchedule {
    ReviewSchedule {
        schedule_json: r#"{"authority":"fsrs","state":{"state":"learning","step":1,"stability":2.3065,"difficulty":2.118103970459016,"last_review":"2026-09-02T00:00:00+00:00","due":"2026-09-02T00:10:00+00:00"}}"#.into(),
        next_review: Some("2026-09-02T00:10:00+00:00".into()),
        next_review_days: 0,
    }
}

#[test]
fn complete_state_and_minute_due_survive_reopen_and_retry_skips_scheduler() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let first = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        learning::record_review_with_state(&mut conn, "card", "review", true, "key-1", "request-1",
            |_| Ok(schedule())).unwrap()
    };
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let state = learning::latest_fsrs_state_json(&conn, "card").unwrap().unwrap();
    assert!(state.contains("\"step\":1"));
    assert!(state.contains("2.118103970459016"));
    assert!(state.contains("last_review"));
    assert_eq!(first.next_review.as_deref(), Some("2026-09-02T00:10:00+00:00"));
    assert_eq!(first.next_review_days, 0);
    let replay = learning::record_review_with_state(&mut conn, "card", "review", true, "key-1", "request-1",
        |_| panic!("retry must not invoke the scheduler")).unwrap();
    assert!(replay.duplicate);
    assert_eq!(replay.event_id, first.event_id);
    assert_eq!(replay.outcome_json, first.outcome_json);
    assert_eq!(replay.next_review, first.next_review);
    assert_eq!(learning::count_learning(&conn).unwrap(), 1);
    assert_eq!(learning::correct_streak(&conn, "card").unwrap(), 1);
    let conflict = learning::record_review_with_state(&mut conn, "card", "review", true, "key-1", "different-state-or-time",
        |_| panic!("conflict must not invoke the scheduler"));
    assert!(conflict.is_err());
    assert_eq!(learning::count_learning(&conn).unwrap(), 1);
}

#[test]
fn failed_transaction_leaves_no_state_event_or_key() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("learning.sqlite").to_str().unwrap()).unwrap();
    conn.execute_batch("CREATE TRIGGER reject_receipt BEFORE INSERT ON learning_event_keys BEGIN SELECT RAISE(ABORT, 'fixture'); END;").unwrap();
    assert!(learning::record_review_with_state(&mut conn, "card", "review", true, "key-1", "request-1",
        |_| Ok(schedule())).is_err());
    assert_eq!(learning::count_learning(&conn).unwrap(), 0);
    assert!(learning::latest_fsrs_state_json(&conn, "card").unwrap().is_none());
    let keys: i64 = conn.query_row("SELECT count(*) FROM learning_event_keys", [], |r| r.get(0)).unwrap();
    assert_eq!(keys, 0);
}

#[test]
fn unscheduled_review_preserves_prior_state_and_replays_as_unscheduled() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("learning.sqlite").to_str().unwrap()).unwrap();
    learning::record_review_with_state(&mut conn, "card", "review", true, "key-1", "request-1",
        |_| Ok(schedule())).unwrap();
    let before = learning::latest_fsrs_state_json(&conn, "card").unwrap();
    let unavailable = learning::record_review_with_state(&mut conn, "card", "review", false, "key-2", "request-2",
        |_| Ok(ReviewSchedule { schedule_json: r#"{"authority":"unavailable"}"#.into(),
            next_review: None, next_review_days: learning::SCHEDULE_UNAVAILABLE })).unwrap();
    assert_eq!(learning::latest_fsrs_state_json(&conn, "card").unwrap(), before);
    let retry = learning::record_review_with_state(&mut conn, "card", "review", false, "key-2", "request-2",
        |_| panic!("retry must preserve the original unavailable receipt")).unwrap();
    assert_eq!(retry.next_review_days, learning::SCHEDULE_UNAVAILABLE);
    assert_eq!(retry.outcome_json, unavailable.outcome_json);
    assert!(retry.next_review.is_none());
    assert_eq!(learning::correct_streak(&conn, "card").unwrap(), 0);
}

#[test]
fn corrupt_schedule_is_rejected_without_events_keys_or_state() {
    for broken in ["time-only", "infinity", "invalid-day", "missing-step", "wrong-due"] {
        let dir = tempfile::tempdir().unwrap();
        let mut conn = init_workspace(dir.path().join("learning.sqlite").to_str().unwrap()).unwrap();
        let mut value = schedule();
        match broken {
            "time-only" => {
                value.schedule_json = value.schedule_json.replace("2026-09-02T00:10:00+00:00", "12:00")
                    .replace("2026-09-02T00:00:00+00:00", "11:00");
                value.next_review = Some("12:00".into());
            }
            "infinity" => value.schedule_json = value.schedule_json.replace("2.3065", "1e999"),
            "invalid-day" => {
                value.schedule_json = value.schedule_json.replace("2026-09-02", "2026-02-30");
                value.next_review = Some("2026-02-30T00:10:00+00:00".into());
            }
            "missing-step" => value.schedule_json = value.schedule_json.replace("\"step\":1,", ""),
            "wrong-due" => value.next_review = Some("2026-09-03T00:10:00+00:00".into()),
            _ => unreachable!(),
        }
        assert!(learning::record_review_with_state(&mut conn, "card", "review", true, "key", "request",
            |_| Ok(value)).is_err(), "accepted {broken}");
        assert_eq!(learning::count_learning(&conn).unwrap(), 0);
        assert!(learning::latest_fsrs_state_json(&conn, "card").unwrap().is_none());
        let keys: i64 = conn.query_row("SELECT count(*) FROM learning_event_keys", [], |r| r.get(0)).unwrap();
        assert_eq!(keys, 0);
    }
}

#[test]
fn key_binds_item_kind_and_correct_even_if_caller_reuses_request_string() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("learning.sqlite").to_str().unwrap()).unwrap();
    learning::record_review_with_state(&mut conn, "card", "review", true, "key", "request", |_| Ok(schedule())).unwrap();
    for (item, kind, correct) in [("other", "review", true), ("card", "quiz", true), ("card", "review", false)] {
        assert!(learning::record_review_with_state(&mut conn, item, kind, correct, "key", "request",
            |_| panic!("conflict called scheduler")).is_err());
    }
    assert_eq!(learning::count_learning(&conn).unwrap(), 1);
}

#[test]
fn streak_parses_legacy_and_compact_outcomes_without_matching_embedded_text() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("learning.sqlite").to_str().unwrap()).unwrap();
    for outcome in [r#"{"outcome": "correct"}"#, r#"{"correct":true}"#, r#"{"outcome":"correct"}"#] {
        learning::record_learning_event(&mut conn, "card", "review", outcome, 1).unwrap();
    }
    assert_eq!(learning::correct_streak(&conn, "card").unwrap(), 3);
    for outcome in ["not-json", r#"{"note":{"correct": true}}"#, r#"{"outcome":"incorrect","correct":true}"#,
                    r#"{"correct":1}"#, r#"{"correct":"true"}"#] {
        learning::record_learning_event(&mut conn, "card", "review", outcome, 1).unwrap();
        assert_eq!(learning::correct_streak(&conn, "card").unwrap(), 0);
    }
}
