//! R05: a keyed review records the interval the reusable scheduler produced, and
//! an unavailable scheduler yields an explicitly *unscheduled* review instead of
//! a placeholder-ladder interval. R2 EVENT-01 semantics (replay, conflict,
//! missing key) must hold unchanged.

use archeaxis_domain::learning::{self, ScheduleSource, SCHEDULE_DUPLICATE, SCHEDULE_UNAVAILABLE};
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
    assert_eq!(days, 37, "the scheduler interval must be used, not the ladder");
    assert_eq!(streak, 1);
    assert!(event_id > 0);

    let history = learning::events_for_item(&conn, "card-1").unwrap();
    assert_eq!(history.len(), 1);
    assert!(history[0].3.is_some(), "a scheduled review carries a due date");

    // Same retry: original receipt, no second event.
    let (same_id, same_streak, same_days, duplicate) =
        learning::record_review_scheduled(&mut conn, "card-1", "review", true, "key-1", Some(37))
            .unwrap();
    assert!(duplicate);
    assert_eq!((same_id, same_streak, same_days), (event_id, streak, days));
    assert_eq!(learning::events_for_item(&conn, "card-1").unwrap().len(), 1);
}

#[test]
fn unavailable_scheduler_records_an_unscheduled_review_not_a_ladder_interval() {
    let (_dir, mut conn) = workspace();
    let (event_id, _streak, days, duplicate) =
        learning::record_review_scheduled(&mut conn, "card-2", "review", true, "key-2", None)
            .unwrap();
    assert!(!duplicate);
    assert_eq!(days, SCHEDULE_UNAVAILABLE);
    assert!(event_id > 0, "the review is still recorded when the scheduler is unavailable");

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
fn event_key_contract_still_holds_for_scheduled_reviews() {
    let (_dir, mut conn) = workspace();
    learning::record_review_scheduled(&mut conn, "card-4", "review", true, "key-a", Some(5)).unwrap();

    // Missing key rejected.
    assert!(learning::record_review_scheduled(&mut conn, "card-4", "review", true, "", Some(5)).is_err());

    // Same key, different item -> conflict.
    let conflict = learning::record_review_scheduled(&mut conn, "card-other", "review", true, "key-a", Some(5));
    assert!(conflict.is_err(), "key bound to another item must conflict");

    // Same key, different payload -> conflict.
    let conflict_payload =
        learning::record_review_scheduled(&mut conn, "card-4", "review", false, "key-a", Some(5));
    assert!(conflict_payload.is_err(), "key bound to another payload must conflict");

    // Sources are explicit so callers cannot accidentally mix them.
    assert_ne!(ScheduleSource::Ladder, ScheduleSource::Explicit(Some(5)));
    assert_eq!(SCHEDULE_DUPLICATE, -1);
}
