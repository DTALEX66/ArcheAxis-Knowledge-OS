//! R10: the learner side and the machine side of an item's state are reported
//! separately, and learner progress is never presented as machine competence.

use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn call(router: &axum::Router, method: &str, path: &str, body: &str) -> (StatusCode, Value) {
    let req = Request::builder().method(method).uri(path).header("content-type", "application/json");
    let resp = router
        .clone()
        .oneshot(req.body(Body::from(body.to_string())).unwrap())
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

#[tokio::test]
async fn learner_and_machine_state_are_reported_separately() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    // A fact, and a card built from it.
    let (status, created) = call(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"radius 6371 km","status":"accepted","created_by":"owner"}"#,
    )
    .await;
    assert!(status.is_success(), "{created}");
    let knowledge_id = created["knowledge_id"].as_str().unwrap().to_string();
    let (status, _) = call(
        &router,
        "POST",
        "/api/v1/learning/items/card-s/references",
        &serde_json::json!({"knowledge_id": knowledge_id}).to_string(),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);

    // An empty state: both sides present, the machine side explicitly not recorded.
    let (status, state) = call(&router, "GET", "/api/v1/learning/items/card-s/state", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(state["learner"]["event_count"], 0);
    assert_eq!(state["machine"]["status"], "not_recorded", "{state}");
    assert!(
        state["machine"]["note"].as_str().unwrap_or("").contains("machine loop"),
        "the machine side must say where receipts come from: {state}"
    );

    // A learner outcome with no card state takes the placeholder ladder path, so
    // it does carry an interval (and the events endpoint reports that authority).
    let (status, _) = call(
        &router,
        "POST",
        "/api/v1/learning/events",
        r#"{"item_key":"card-s","correct":true,"client_event_id":"evt-s"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);

    // A learner outcome whose scheduler cannot answer is stored as unscheduled -
    // the interval is never invented, which is what lets a human record an
    // activity result that could not flow back automatically.
    let (status, _) = call(
        &router,
        "POST",
        "/api/v1/learning/events",
        r#"{"item_key":"card-s","correct":true,"client_event_id":"evt-s2","schedule_state":{"state":"imaginary"}}"#,
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);

    let (status, state) = call(&router, "GET", "/api/v1/learning/items/card-s/state", "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(state["learner"]["event_count"], 2, "{state}");
    assert_eq!(state["learner"]["correct_streak"], 2);
    assert_eq!(state["learner"]["scheduled_events"], 1, "{state}");
    assert_eq!(
        state["learner"]["unscheduled_events"], 1,
        "the event whose scheduler was unavailable must be stored unscheduled: {state}"
    );
    let references = state["learner"]["references"].as_array().unwrap();
    assert_eq!(references.len(), 1);
    assert_eq!(references[0]["active"], true);
    // Recording a human outcome must not fabricate machine competence.
    assert_eq!(state["machine"]["status"], "not_recorded", "{state}");
}
