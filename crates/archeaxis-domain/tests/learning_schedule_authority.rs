//! R05: a keyed review records the interval the reusable scheduler produced, and
//! an unavailable scheduler yields an explicitly *unscheduled* review instead of
//! a placeholder-ladder interval. R2 EVENT-01 semantics (replay, conflict,
//! missing key) must hold unchanged.

use archeaxis_domain::learning::{self, SCHEDULE_DUPLICATE, SCHEDULE_UNAVAILABLE, ScheduleSource};
use archeaxis_store_sqlite::init_workspace;

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    (dir, conn)
}

#[test]
fn scheduler_interval_is_recorded_and_replayed_once() {
    let (_dir, mut conn) = workspace();
    let (event_id, streak, days, duplicate) =
        learning::record_review_scheduled(&mut conn, "card-1", "review", true, "key-1", Some(37))
            .unwrap();
    assert!(!duplicate);
    assert_eq!(
        days, 37,
        "the scheduler interval must be used, not the ladder"
    );
    assert_eq!(streak, 1);
    assert!(event_id > 0);

    let history = learning::events_for_item(&conn, "card-1").unwrap();
    assert_eq!(history.len(), 1);
    assert!(
        history[0].3.is_some(),
        "a scheduled review carries a due date"
    );

    // Same retry: original receipt, no second event.
    let (same_id, same_streak, same_days, duplicate) =
        learning::record_review_scheduled(&mut conn, "card-1", "review", true, "key-1", Some(37))
            .unwrap();
    assert!(duplicate);
    assert_eq!((same_id, same_streak, same_days), (event_id, streak, days));
    assert_eq!(learning::events_for_item(&conn, "card-1").unwrap().len(), 1);
}

#[test]
fn http_receipt_binds_request_and_rechecks_after_concurrent_scheduling() {
    let (_dir, mut conn) = workspace();
    let request = r#"{"item_key":"card-v2","now":"2026-09-02T00:00:00Z"}"#;
    assert!(
        learning::existing_http_learning_event(&conn, "card-v2", "review", true, "v2-key", request)
            .unwrap()
            .is_none()
    );
    let first = learning::record_http_learning_event(
        &mut conn,
        "card-v2",
        "review",
        true,
        "v2-key",
        request,
        ScheduleSource::Explicit(None),
    )
    .unwrap();
    assert!(!first.duplicate);
    assert_eq!(first.schedule_authority, "unavailable");
    assert_eq!(first.next_review_days, SCHEDULE_UNAVAILABLE);
    assert_eq!(first.idempotency_scope, "full_request");
    // Another request can have scheduled while the first one committed. Its
    // result must not replace the original outcome when the key is rechecked.
    let replay = learning::record_http_learning_event(
        &mut conn,
        "card-v2",
        "review",
        true,
        "v2-key",
        request,
        ScheduleSource::Explicit(Some(42)),
    )
    .unwrap();
    assert!(replay.duplicate);
    assert_eq!(replay.event_id, first.event_id);
    assert_eq!(replay.schedule_authority, "unavailable");
    assert_eq!(replay.next_review_days, SCHEDULE_UNAVAILABLE);
    let invalid_late_result = learning::record_http_learning_event(
        &mut conn,
        "card-v2",
        "review",
        true,
        "v2-key",
        request,
        ScheduleSource::Explicit(Some(-2)),
    )
    .unwrap();
    assert!(invalid_late_result.duplicate);
    assert_eq!(invalid_late_result.event_id, first.event_id);
    assert!(
        learning::record_http_learning_event(
            &mut conn,
            "card-v2",
            "review",
            true,
            "new-invalid-key",
            request,
            ScheduleSource::Explicit(Some(-2)),
        )
        .is_err()
    );
    let changed = r#"{"item_key":"card-v2","now":"2026-09-03T00:00:00Z"}"#;
    assert!(
        learning::record_http_learning_event(
            &mut conn,
            "card-v2",
            "review",
            true,
            "v2-key",
            changed,
            ScheduleSource::Explicit(Some(42))
        )
        .is_err()
    );
    assert_eq!(
        learning::events_for_item(&conn, "card-v2").unwrap().len(),
        1
    );
    // An older Core using the previous hash format cannot replay this newer
    // binding; it must fail closed rather than write a second event.
    assert!(
        learning::record_review_scheduled(&mut conn, "card-v2", "review", true, "v2-key", Some(42))
            .is_err()
    );
}

#[test]
fn historical_http_receipts_replay_with_honest_limited_identity() {
    let (_dir, mut conn) = workspace();
    let (event, streak, days, _) = learning::record_review_scheduled(
        &mut conn,
        "historical",
        "review",
        true,
        "historical-key",
        Some(37),
    )
    .unwrap();
    let original: (String, String) = conn.query_row(
        "SELECT k.payload_hash,e.outcome FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id WHERE k.event_key='historical-key'",
        [], |row| Ok((row.get(0)?, row.get(1)?)),
    ).unwrap();
    let replay = learning::existing_http_learning_event(
        &conn,
        "historical",
        "review",
        true,
        "historical-key",
        "newly supplied request cannot be verified",
    )
    .unwrap()
    .unwrap();
    assert_eq!(
        (
            replay.event_id,
            replay.streak_after,
            replay.next_review_days
        ),
        (event, streak, days)
    );
    assert_eq!(replay.idempotency_scope, "legacy_item_kind_outcome");
    assert_eq!(replay.schedule_authority, "legacy_unverified");
    assert!(
        learning::existing_http_learning_event(
            &conn,
            "historical",
            "review",
            false,
            "historical-key",
            "request",
        )
        .is_err()
    );
    let unchanged: (String, String) = conn.query_row(
        "SELECT k.payload_hash,e.outcome FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id WHERE k.event_key='historical-key'",
        [], |row| Ok((row.get(0)?, row.get(1)?)),
    ).unwrap();
    assert_eq!(unchanged, original);

    learning::record_review_scheduled(
        &mut conn,
        "historical-offline",
        "review",
        true,
        "offline-key",
        None,
    )
    .unwrap();
    let unavailable = learning::existing_http_learning_event(
        &conn,
        "historical-offline",
        "review",
        true,
        "offline-key",
        "request",
    )
    .unwrap()
    .unwrap();
    assert_eq!(unavailable.schedule_authority, "unavailable");
    assert_eq!(unavailable.next_review_days, SCHEDULE_UNAVAILABLE);
    assert_eq!(unavailable.idempotency_scope, "legacy_item_kind_outcome");
}

#[test]
fn unavailable_scheduler_records_an_unscheduled_review_not_a_ladder_interval() {
    let (_dir, mut conn) = workspace();
    let (event_id, _streak, days, duplicate) =
        learning::record_review_scheduled(&mut conn, "card-2", "review", true, "key-2", None)
            .unwrap();
    assert!(!duplicate);
    assert_eq!(days, SCHEDULE_UNAVAILABLE);
    assert!(
        event_id > 0,
        "the review is still recorded when the scheduler is unavailable"
    );

    let history = learning::events_for_item(&conn, "card-2").unwrap();
    assert_eq!(history.len(), 1);
    assert_eq!(history[0].3, None, "an unscheduled review has no due date");
    let outcome = &history[0].2;
    assert!(
        outcome.contains("unavailable"),
        "the payload must mark the missing schedule: {outcome}"
    );
    // The ladder would have produced a concrete interval for a correct review.
    assert_ne!(days, learning::suggest_next_interval(1));
}

#[test]
fn ladder_path_is_unchanged_and_still_separate_from_the_scheduler_path() {
    let (_dir, mut conn) = workspace();
    let (_id, _streak, ladder_days, _dup) =
        learning::record_review_keyed(&mut conn, "card-3", "review", true, "key-3").unwrap();
    assert_eq!(ladder_days, learning::suggest_next_interval(1));

    let (_id2, _streak2, scheduled_days, _dup2) =
        learning::record_review_scheduled(&mut conn, "card-3", "review", true, "key-4", Some(99))
            .unwrap();
    assert_eq!(scheduled_days, 99, "the explicit scheduler value wins");
}

#[test]
fn schedule_survives_a_workspace_reopen() {
    // R05 acceptance: restart must not change what was recorded - a scheduled
    // review keeps its due date and an unscheduled one stays unscheduled.
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("reopen.sqlite");
    {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        learning::record_review_scheduled(&mut conn, "card-r1", "review", true, "key-r1", Some(21))
            .unwrap();
        learning::record_review_scheduled(&mut conn, "card-r2", "review", true, "key-r2", None)
            .unwrap();
    }
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let scheduled = learning::events_for_item(&conn, "card-r1").unwrap();
    assert_eq!(scheduled.len(), 1);
    assert!(
        scheduled[0].3.is_some(),
        "the scheduled due date must survive a reopen"
    );
    let unscheduled = learning::events_for_item(&conn, "card-r2").unwrap();
    assert_eq!(unscheduled.len(), 1);
    assert_eq!(
        unscheduled[0].3, None,
        "an unscheduled review stays unscheduled after reopen"
    );
    // The keyed receipt also survives, so a post-restart retry still replays it.
    let (_id, _streak, days, duplicate) =
        learning::record_review_scheduled(&mut conn, "card-r1", "review", true, "key-r1", Some(21))
            .unwrap();
    assert!(
        duplicate,
        "post-restart retry must be recognised as a replay"
    );
    assert_eq!(days, 21);
}

#[test]
fn event_key_contract_still_holds_for_scheduled_reviews() {
    let (_dir, mut conn) = workspace();
    learning::record_review_scheduled(&mut conn, "card-4", "review", true, "key-a", Some(5))
        .unwrap();

    // Missing key rejected.
    assert!(
        learning::record_review_scheduled(&mut conn, "card-4", "review", true, "", Some(5))
            .is_err()
    );

    // Same key, different item -> conflict.
    let conflict = learning::record_review_scheduled(
        &mut conn,
        "card-other",
        "review",
        true,
        "key-a",
        Some(5),
    );
    assert!(conflict.is_err(), "key bound to another item must conflict");

    // Same key, different payload -> conflict.
    let conflict_payload =
        learning::record_review_scheduled(&mut conn, "card-4", "review", false, "key-a", Some(5));
    assert!(
        conflict_payload.is_err(),
        "key bound to another payload must conflict"
    );

    // Sources are explicit so callers cannot accidentally mix them.
    assert_ne!(ScheduleSource::Ladder, ScheduleSource::Explicit(Some(5)));
    assert_eq!(SCHEDULE_DUPLICATE, -1);
}
