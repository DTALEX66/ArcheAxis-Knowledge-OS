//! R11 over the Core API: a machine principal records task receipts, a human
//! principal cannot write them, learners cannot be credited with machine
//! competence, and an unverified task stays visible as unmeasured.

use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn call(router: &axum::Router, method: &str, path: &str, actor: Option<&str>, body: &str) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(path).header("content-type", "application/json");
    if let Some(actor) = actor {
        req = req.header("x-archeaxis-actor", actor);
    }
    let resp = router
        .clone()
        .oneshot(req.body(Body::from(body.to_string())).unwrap())
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

fn receipt(task_id: &str, outcome: &str) -> String {
    serde_json::json!({
        "task_id": task_id,
        "conditions": "offline; fixed sample",
        "model_version": "qwen3:8b",
        "scope": "one observable extraction task",
        "outcome": outcome
    })
    .to_string()
}

#[tokio::test]
async fn a_machine_records_a_receipt_and_anyone_can_read_it_back() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    let (status, body) = call(&router, "POST", "/api/v1/machine/tasks", Some("machine"), &receipt("task-1", "succeeded")).await;
    assert_eq!(status, StatusCode::CREATED, "{body}");

    let (status, readback) = call(&router, "GET", "/api/v1/machine/tasks/task-1", None, "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(readback["outcome"], "succeeded");
    assert_eq!(readback["model_version"], "qwen3:8b");
    assert_eq!(readback["scope"], "one observable extraction task");
    assert!(readback["failure"].is_null());
    assert!(
        readback["note"].as_str().unwrap_or("").contains("weights were trained"),
        "the readback must separate a task receipt from weight training: {readback}"
    );

    let (status, _) = call(&router, "GET", "/api/v1/machine/tasks/unknown", None, "").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn a_human_cannot_write_a_machine_receipt() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (status, _) = call(&router, "POST", "/api/v1/machine/tasks", Some("human"), &receipt("task-h", "succeeded")).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "the two sides must stay distinguishable");
    let (status, _) = call(&router, "GET", "/api/v1/machine/tasks/task-h", None, "").await;
    assert_eq!(status, StatusCode::NOT_FOUND, "a refused receipt must not land");
}

#[tokio::test]
async fn an_unmeasured_task_stays_unmeasured_and_cannot_be_rewritten() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    let (status, _) = call(&router, "POST", "/api/v1/machine/tasks", Some("machine"), &receipt("task-u", "unmeasured")).await;
    assert_eq!(status, StatusCode::CREATED);

    // A rollup that ignores unmeasured results would be misleading: the state is
    // preserved verbatim and re-reading reports it as such.
    let (_, readback) = call(&router, "GET", "/api/v1/machine/tasks/task-u", None, "").await;
    assert_eq!(readback["outcome"], "unmeasured");

    // A failure without a reason is refused, and a receipt cannot be rewritten.
    let (status, _) = call(
        &router,
        "POST",
        "/api/v1/machine/tasks",
        Some("machine"),
        &serde_json::json!({"task_id":"task-f","conditions":"c","model_version":"m","scope":"s","outcome":"failed"}).to_string(),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let (status, _) = call(&router, "POST", "/api/v1/machine/tasks", Some("machine"), &receipt("task-u", "succeeded")).await;
    assert_eq!(status, StatusCode::BAD_REQUEST, "an existing receipt must not be rewritten");
}
