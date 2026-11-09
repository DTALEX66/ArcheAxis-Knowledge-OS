//! Recovery selects only recorded, assessment-scoped observations with usable evidence.
use archeaxis_domain::learning;
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::json;

fn insert(conn: &Connection, item: &str, outcome: serde_json::Value) -> i64 {
    conn.execute(
        "INSERT INTO learning_events(item_key,kind,outcome) VALUES(?1,'review',?2)",
        rusqlite::params![item, outcome.to_string()],
    )
    .unwrap();
    conn.last_insert_rowid()
}

fn unavailable(assessment: Option<&str>, rating: u8, now: Option<&str>) -> serde_json::Value {
    json!({"assessment_id":assessment,"outcome":if rating==1 {"incorrect"} else {"correct"},
        "schedule":{"authority":"unavailable"},"review_evidence":{"rating":rating,"now":now}})
}

#[test]
fn pending_reviews_follow_the_last_card_and_the_selected_assessment() {
    let temp = tempfile::tempdir().unwrap();
    let conn = init_workspace(temp.path().join("recovery.sqlite").to_str().unwrap()).unwrap();
    insert(
        &conn,
        "item",
        unavailable(Some("a"), 1, Some("2026-09-01T00:00:00Z")),
    );
    let card = json!({"state":"review","last_review":"2026-09-02T00:00:00Z"});
    insert(
        &conn,
        "item",
        json!({"assessment_id":"a","schedule":{"authority":"fsrs","state":card}}),
    );
    let first = insert(
        &conn,
        "item",
        unavailable(Some("a"), 1, Some("2026-09-03T00:00:00Z")),
    );
    insert(
        &conn,
        "item",
        unavailable(Some("b"), 1, Some("2026-09-04T00:00:00Z")),
    );
    let second = insert(
        &conn,
        "item",
        unavailable(Some("a"), 3, Some("2026-09-05T00:00:00Z")),
    );
    let basis = learning::review_schedule_basis(&conn, "item", Some("a")).unwrap();
    assert_eq!(basis.previous_state.unwrap(), card.to_string());
    assert_eq!(basis.latest_event_id, Some(second));
    assert!(basis.recovery_issue.is_none());
    assert_eq!(
        basis
            .pending
            .iter()
            .map(|e| (e.event_id, e.rating))
            .collect::<Vec<_>>(),
        [(first, 1), (second, 3)]
    );
    assert_eq!(basis.pending[0].reviewed_at, "2026-09-03T00:00:00Z");
}

#[test]
fn missing_or_inconsistent_evidence_fails_closed_without_inventing_time() {
    let temp = tempfile::tempdir().unwrap();
    let conn = init_workspace(temp.path().join("recovery.sqlite").to_str().unwrap()).unwrap();
    insert(&conn, "missing", unavailable(None, 1, None));
    let basis = learning::review_schedule_basis(&conn, "missing", None).unwrap();
    assert_eq!(
        basis.recovery_issue,
        Some("unscheduled_review_evidence_missing_or_invalid")
    );
    assert!(basis.pending.is_empty());
    let mut effective = unavailable(None, 1, None);
    effective["schedule"]["reviewed_at"] = json!("2026-09-03T00:00:00Z");
    insert(&conn, "effective", effective);
    assert_eq!(
        learning::review_schedule_basis(&conn, "effective", None)
            .unwrap()
            .pending[0]
            .reviewed_at,
        "2026-09-03T00:00:00Z"
    );
    let mut conflicting = unavailable(None, 1, Some("2026-09-03T00:00:00Z"));
    conflicting["outcome"] = json!("correct");
    insert(&conn, "conflicting", conflicting);
    assert_eq!(
        learning::review_schedule_basis(&conn, "conflicting", None)
            .unwrap()
            .recovery_issue,
        Some("unscheduled_review_evidence_missing_or_invalid")
    );
}

#[test]
fn recovery_has_a_named_bound_instead_of_truncating_history() {
    let temp = tempfile::tempdir().unwrap();
    let conn = init_workspace(temp.path().join("recovery.sqlite").to_str().unwrap()).unwrap();
    conn.execute_batch("BEGIN").unwrap();
    for _ in 0..4097 {
        insert(
            &conn,
            "many",
            unavailable(None, 1, Some("2026-09-03T00:00:00Z")),
        );
    }
    conn.execute_batch("COMMIT").unwrap();
    let basis = learning::review_schedule_basis(&conn, "many", None).unwrap();
    assert_eq!(basis.pending.len(), 4096);
    assert_eq!(basis.recovery_issue, Some("too_many_unscheduled_reviews"));
}

#[test]
fn review_times_compare_exact_microseconds_and_offsets() {
    let temp = tempfile::tempdir().unwrap();
    let conn = init_workspace(temp.path().join("recovery.sqlite").to_str().unwrap()).unwrap();
    let time = |s| {
        learning::review_timestamp_micros(&conn, s)
            .unwrap()
            .unwrap()
    };
    assert_eq!(
        time("2026-09-03T08:00:00.000002+08:00"),
        time("2026-09-03T00:00:00.000002Z")
    );
    assert_eq!(
        time("2026-09-03T08:00:00.000002+08:00") - time("2026-09-03T00:00:00.000001Z"),
        1
    );
    assert_eq!(
        time("2026-09-02T19:00:00-05:00"),
        time("2026-09-03T00:00:00Z")
    );
    assert_eq!(
        time("2024-02-29T00:00:00.1Z") - time("2024-02-29T00:00:00Z"),
        100_000
    );
    assert!(
        learning::review_timestamp_micros(&conn, "2025-02-29T00:00:00Z")
            .unwrap()
            .is_none()
    );
}

#[test]
fn inverted_historical_events_are_not_reordered_or_replayed() {
    let temp = tempfile::tempdir().unwrap();
    let conn = init_workspace(temp.path().join("recovery.sqlite").to_str().unwrap()).unwrap();
    insert(
        &conn,
        "item",
        unavailable(None, 1, Some("2026-09-03T08:00:00.000002+08:00")),
    );
    insert(
        &conn,
        "item",
        unavailable(None, 3, Some("2026-09-03T00:00:00.000001Z")),
    );
    let basis = learning::review_schedule_basis(&conn, "item", None).unwrap();
    assert_eq!(
        basis.recovery_issue,
        Some("unscheduled_review_time_order_invalid")
    );
    assert_eq!(basis.pending.len(), 1);
}

#[test]
fn due_and_reported_interval_must_match_the_review_instant() {
    let temp = tempfile::tempdir().unwrap();
    let conn = init_workspace(temp.path().join("recovery.sqlite").to_str().unwrap()).unwrap();
    let make = |last: &str, due: &str, days: i64| learning::ReviewSchedule {
        schedule_json: json!({"authority":"fsrs","state":{"state":"review","step":null,
            "stability":3.0,"difficulty":5.0,"last_review":last,"due":due}})
        .to_string(),
        next_review: Some(due.to_owned()),
        next_review_days: days,
    };
    let last = "2026-09-02T08:00:00.000002+08:00";
    assert!(
        learning::review_schedule_is_valid(&conn, &make(last, "2026-09-02T00:00:00.000002Z", 0))
            .unwrap()
    );
    assert!(
        learning::review_schedule_is_valid(&conn, &make(last, "2026-09-03T00:00:00.000001Z", 0))
            .unwrap()
    );
    assert!(
        learning::review_schedule_is_valid(&conn, &make(last, "2026-09-03T00:00:00.000002Z", 1))
            .unwrap()
    );
    assert!(
        !learning::review_schedule_is_valid(&conn, &make(last, "2026-09-02T00:00:00.000001Z", 0))
            .unwrap()
    );
    assert!(
        !learning::review_schedule_is_valid(&conn, &make(last, "2026-09-03T00:00:00.000002Z", 2))
            .unwrap()
    );
}
