//! R05: the learning-events API reports which scheduling authority produced the
//! interval - the reused FSRS scheduler when the caller supplies card state, an
//! explicit "unavailable" (unscheduled review) when that scheduler cannot answer,
//! or the placeholder ladder when no card state is given.

use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn post(router: &axum::Router, body: &str) -> (StatusCode, Value) {
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/events")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

fn router() -> (tempfile::TempDir, axum::Router) {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    (dir, router)
}

const MATURE_STATE: &str = r#""schedule_state": {"state": "review", "stability": 42.0, "difficulty": 5.0,
     "due": "2026-09-01T00:00:00+00:00", "last_review": "2026-08-03T00:00:00+00:00", "step": 0}"#;

#[tokio::test]
async fn card_state_routes_the_review_through_the_reused_fsrs_scheduler() {
    let (_dir, router) = router();
    let body = format!(
        r#"{{"item_key":"api-card-1","correct":true,"client_event_id":"k-1",{MATURE_STATE},"now":"2026-09-02T00:00:00+00:00"}}"#
    );
    let (status, value) = post(&router, &body).await;
    assert_eq!(status, StatusCode::CREATED, "unexpected: {value}");
    assert_eq!(value["schedule_authority"], "fsrs");
    let days = value["next_review_days"].as_i64().unwrap();
    assert!(
        days > 14,
        "a mature card must exceed the placeholder ladder's 14-day ceiling, got {days}"
    );
}

#[tokio::test]
async fn no_card_state_is_reported_as_the_placeholder_ladder() {
    let (_dir, router) = router();
    let (status, value) = post(
        &router,
        r#"{"item_key":"api-card-2","correct":true,"client_event_id":"k-2"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(value["schedule_authority"], "placeholder_ladder");
    assert!(value["next_review_days"].as_i64().unwrap() > 0);
}

#[tokio::test]
async fn unusable_card_state_is_recorded_as_unscheduled() {
    let (_dir, router) = router();
    // An unknown card state makes the reusable scheduler reject the request; the
    // review must still be recorded, with no interval and an explicit authority.
    let (status, value) = post(
        &router,
        r#"{"item_key":"api-card-3","correct":true,"client_event_id":"k-3","schedule_state":{"state":"imaginary"}}"#,
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "unexpected: {value}");
    assert_eq!(value["schedule_authority"], "unavailable");
    assert_eq!(value["next_review_days"].as_i64().unwrap(), -2, "unscheduled sentinel");

    // History shows the event was kept with no due date, so nothing was invented.
    let resp = router
        .clone()
        .oneshot(Request::get("/api/v1/learning/events/api-card-3").body(Body::empty()).unwrap())
        .await
        .unwrap();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let history: Value = serde_json::from_slice(&bytes).unwrap();
    let items = history["events"].as_array().or_else(|| history.as_array()).expect("history list");
    assert_eq!(items.len(), 1);
    assert!(items[0]["next_review"].is_null(), "unscheduled review has no due date: {}", items[0]);
}
