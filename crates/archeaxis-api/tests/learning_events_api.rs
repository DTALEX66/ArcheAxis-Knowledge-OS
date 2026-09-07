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
    let body = format!(
        r#"{{"item_key":"{item}","kind":"review","correct":{correct}}}"#
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
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
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
