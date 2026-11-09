//! X08 minimal real side: human review events through the Core API with
//! deterministic next-review hints (single scheduler authority until the FSRS
//! adapter wiring lands).

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn post_event(router: &axum::Router, item: &str, correct: bool) -> (StatusCode, Value) {
    static CALL: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let counter = CALL.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    let body = format!(
        r#"{{"item_key":"{item}","kind":"review","correct":{correct},"client_event_id":"auto-{item}-{counter}"}}"#
    );
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/events")
                .header("content-type", "application/json")
                .body(Body::from(body))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

#[tokio::test]
async fn correct_streak_grows_and_interval_scales_then_resets() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    let (s, v) = post_event(&router, "card-a", true).await;
    assert_eq!(s, StatusCode::CREATED);
    assert_eq!(v["streak_after"], 1);
    assert_eq!(v["next_review_days"], 2);

    let (_, v) = post_event(&router, "card-a", true).await;
    assert_eq!(v["streak_after"], 2);
    assert_eq!(v["next_review_days"], 4);

    let (_, v) = post_event(&router, "card-a", true).await;
    assert_eq!(v["streak_after"], 3);
    assert_eq!(v["next_review_days"], 7);

    // incorrect resets the streak and schedules a 1-day review
    let (_, v) = post_event(&router, "card-a", false).await;
    assert_eq!(v["streak_after"], 0);
    assert_eq!(v["next_review_days"], 1);

    // independent item is not affected
    let (_, v) = post_event(&router, "card-b", true).await;
    assert_eq!(v["streak_after"], 1);
    assert_eq!(v["next_review_days"], 2);
}

#[tokio::test]
async fn empty_item_key_is_rejected() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (s, _) = post_event(&router, "", true).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
}

async fn post_event_keyed(
    router: &axum::Router,
    item: &str,
    correct: bool,
    key: Option<&str>,
) -> (StatusCode, Value) {
    let body = match key {
        Some(k) => format!(
            r#"{{"item_key":"{item}","kind":"review","correct":{correct},"client_event_id":"{k}"}}"#
        ),
        None => format!(
            r#"{{"item_key":"{item}","kind":"review","correct":{correct},"client_event_id":""}}"#
        ),
    };
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/events")
                .header("content-type", "application/json")
                .body(Body::from(body))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

#[tokio::test]
async fn legacy_review_replays_but_new_legacy_review_requires_assessment_route() {
    use archeaxis_domain::{knowledge, learning};
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy-event-assessment.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, first) = post_event_keyed(&router, "card-x", true, Some("old-event")).await;
    assert_eq!(status, StatusCode::CREATED);
    drop(router);
    {
        let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        let id = knowledge::create_knowledge(
            &mut conn,
            "FACTUAL_CLAIM",
            "Synthetic fact",
            "accepted",
            None,
            None,
            "fixture",
        )
        .unwrap();
        learning::record_card_reference(&mut conn, "card-x", &id, None).unwrap();
        learning::create_assessment(&mut conn, "card-x", &id).unwrap();
    }
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, replay) = post_event_keyed(&router, "card-x", true, Some("old-event")).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(replay["event_id"], first["event_id"]);
    assert_eq!(replay["duplicate"], true);
    let (status, refused) = post_event_keyed(&router, "card-x", true, Some("new-event")).await;
    assert_eq!(status, StatusCode::CONFLICT, "{refused}");
    let conn = rusqlite::Connection::open(db).unwrap();
    let count: i64 = conn
        .query_row("SELECT count(*) FROM learning_events", [], |row| row.get(0))
        .unwrap();
    assert_eq!(count, 1);
    drop(conn);
    // A non-review activity remains available as item history; it must not
    // change the current assessment's queue or progress.
    let response = router.clone().oneshot(
        Request::post("/api/v1/learning/events")
            .header("content-type", "application/json")
            .body(Body::from(r#"{"item_key":"card-x","kind":"teach_back","correct":true,"client_event_id":"activity"}"#))
            .unwrap(),
    ).await.unwrap();
    assert_eq!(response.status(), StatusCode::CREATED);
    let response = router
        .oneshot(
            Request::get("/api/v1/learning/items/card-x/state")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let state: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(state["learner"]["event_count"], 2);
    assert_eq!(state["learner"]["assessment_progress"]["event_count"], 0);
    assert!(state["learner"]["next_review"].is_null());
}

#[tokio::test]
async fn same_client_event_id_is_recorded_only_once() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let (s1, v1) = post_event_keyed(&router, "card-x", true, Some("evt-1")).await;
    assert_eq!(s1, StatusCode::CREATED);
    assert_eq!(v1["duplicate"], false);
    assert_eq!(v1["streak_after"], 1);
    // replay with same key -> no new event; the ORIGINAL receipt is returned
    let (s2, v2) = post_event_keyed(&router, "card-x", true, Some("evt-1")).await;
    assert_eq!(s2, StatusCode::OK);
    assert_eq!(v2["duplicate"], true);
    assert_eq!(v2["event_id"], v1["event_id"]);
    assert_eq!(v2["streak_after"], 1);
    assert_eq!(v2["next_review_days"], 2);
    // different key -> new event, streak continues
    let (s3, v3) = post_event_keyed(&router, "card-x", true, Some("evt-2")).await;
    assert_eq!(s3, StatusCode::CREATED);
    assert_eq!(v3["duplicate"], false);
    assert_eq!(v3["streak_after"], 2);
    // exactly two events persisted
    let conn = rusqlite::Connection::open(db.to_str().unwrap()).unwrap();
    let n: i64 = conn
        .query_row(
            "SELECT count(*) FROM learning_events WHERE item_key='card-x'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(n, 2);
}

#[tokio::test]
async fn historical_receipts_remain_readable_without_inventing_original_authority() {
    use archeaxis_domain::learning;
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("historical-event-key.sqlite");
    let original = {
        let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        learning::record_review_scheduled(
            &mut conn,
            "old-success",
            "review",
            true,
            "old-success-key",
            Some(37),
        )
        .unwrap();
        learning::record_review_scheduled(
            &mut conn,
            "old-unavailable",
            "review",
            true,
            "old-unavailable-key",
            None,
        )
        .unwrap();
        conn.query_row("SELECT k.payload_hash,e.outcome FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id WHERE k.event_key='old-success-key'",
            [], |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))).unwrap()
    };
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, success) =
        post_event_keyed(&router, "old-success", true, Some("old-success-key")).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(success["next_review_days"], 37);
    assert_eq!(success["schedule_authority"], "legacy_unverified");
    assert_eq!(success["idempotency_scope"], "legacy_item_kind_outcome");
    let (status, unavailable) = post_event_keyed(
        &router,
        "old-unavailable",
        true,
        Some("old-unavailable-key"),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(unavailable["next_review_days"], -2);
    assert_eq!(unavailable["schedule_authority"], "unavailable");
    assert_eq!(unavailable["idempotency_scope"], "legacy_item_kind_outcome");
    assert_eq!(
        post_event_keyed(&router, "old-success", false, Some("old-success-key"))
            .await
            .0,
        StatusCode::CONFLICT
    );
    let conn = rusqlite::Connection::open(db).unwrap();
    let unchanged: (String, String) = conn.query_row(
        "SELECT k.payload_hash,e.outcome FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id WHERE k.event_key='old-success-key'",
        [], |row| Ok((row.get(0)?, row.get(1)?)),
    ).unwrap();
    assert_eq!(unchanged, original);
}

#[tokio::test]
async fn history_lists_recorded_events_for_item() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let _ = post_event(&router, "card-h", true).await;
    let _ = post_event(&router, "card-h", false).await;
    let resp = router
        .clone()
        .oneshot(
            Request::get("/api/v1/learning/events/card-h")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let v: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(v["count"], 2);
    assert_eq!(v["events"][1]["outcome"], r#"{"outcome": "incorrect"}"#);
}

// EVENT-01: a key bound to a different payload is a conflict, not a dedup;
// unkeyed submissions are rejected.
#[tokio::test]
async fn same_key_different_payload_conflicts_and_missing_key_rejected() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (s1, _) = post_event_keyed(&router, "card-c", true, Some("evt-c1")).await;
    assert_eq!(s1, StatusCode::CREATED);
    // same key, different outcome payload -> conflict
    let (s2, _) = post_event_keyed(&router, "card-c", false, Some("evt-c1")).await;
    assert_eq!(s2, StatusCode::CONFLICT);
    // same key, different item -> conflict
    let (s3, _) = post_event_keyed(&router, "card-d", true, Some("evt-c1")).await;
    assert_eq!(s3, StatusCode::CONFLICT);
    // missing/empty key -> rejected, nothing accumulates
    let (s4, _) = post_event_keyed(&router, "card-c", true, None).await;
    assert_eq!(s4, StatusCode::BAD_REQUEST);
}
