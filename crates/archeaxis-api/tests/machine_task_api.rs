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
        "method_version": "method-1",
        "tool_version": "tool-1",
        "model_version": "qwen3:8b",
        "scope": "one observable extraction task",
        "outcome": outcome,
        "retest_of": null
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
    // Every field the write accepted must come back: a readback that drops the
    // conditions or the knowledge/method/tool versions cannot re-check the claim.
    assert_eq!(readback["task_id"], "task-1");
    assert_eq!(readback["conditions"], "offline; fixed sample");
    assert!(readback["knowledge_version"].is_null());
    assert_eq!(readback["method_version"], "method-1");
    assert_eq!(readback["tool_version"], "tool-1");
    assert_eq!(readback["model_version"], "qwen3:8b");
    assert_eq!(readback["scope"], "one observable extraction task");
    assert_eq!(readback["outcome"], "succeeded");
    assert!(readback["retest_of"].is_null());
    assert!(readback["failure"].is_null());
    assert!(
        readback["note"].as_str().unwrap_or("").contains("weights were trained"),
        "the readback must separate a task receipt from weight training: {readback}"
    );

    let (status, _) = call(&router, "GET", "/api/v1/machine/tasks/unknown", None, "").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn machine_task_binds_knowledge_and_retest_to_canonical_records() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let db_str = db.to_str().unwrap().to_string();
    let router = app(&db_str).unwrap();

    let (status, accepted) = call(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        None,
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"bound fact","status":"accepted","created_by":"owner"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{accepted}");
    let knowledge_id = accepted["knowledge_id"].as_str().unwrap().to_string();

    let failed = serde_json::json!({
        "task_id": "failed-task",
        "conditions": "fixed sample",
        "knowledge_version": &knowledge_id,
        "method_version": "method-1",
        "tool_version": "tool-1",
        "model_version": "model-1",
        "scope": "one task",
        "outcome": "failed",
        "failure": "provider error"
    });
    let (status, _) = call(&router, "POST", "/api/v1/machine/tasks", Some("machine"), &failed.to_string()).await;
    assert_eq!(status, StatusCode::CREATED);

    let (status, corrected) = call(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{knowledge_id}/review-decisions"),
        None,
        r#"{"action":"modified","reviewer":"owner","new_body":"bound fact corrected by owner"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{corrected}");
    let successor_id = corrected["knowledge_id"].as_str().unwrap().to_string();
    let (status, _) = call(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{successor_id}/review-decisions"),
        None,
        r#"{"action":"accepted","reviewer":"owner"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::OK);

    let retest = serde_json::json!({
        "task_id": "retest-task",
        "conditions": "fixed sample after human correction",
        "knowledge_version": &successor_id,
        "method_version": "method-1",
        "tool_version": "tool-1",
        "model_version": "model-1",
        "scope": "one task",
        "outcome": "succeeded",
        "retest_of": "failed-task"
    });
    let (status, _) = call(&router, "POST", "/api/v1/machine/tasks", Some("machine"), &retest.to_string()).await;
    assert_eq!(status, StatusCode::CREATED);

    let missing_knowledge = serde_json::json!({
        "task_id": "missing-knowledge",
        "conditions": "fixed sample",
        "knowledge_version": "k_missing",
        "model_version": "model-1",
        "scope": "one task",
        "outcome": "succeeded"
    });
    let (status, _) = call(&router, "POST", "/api/v1/machine/tasks", Some("machine"), &missing_knowledge.to_string()).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let (status, _) = call(
        &router,
        "POST",
        "/api/v1/machine/tasks",
        Some("machine"),
        &serde_json::json!({
            "task_id": "unknown-retest",
            "conditions": "fixed sample",
            "knowledge_version": &successor_id,
            "model_version": "model-1",
            "scope": "one task",
            "outcome": "succeeded",
            "retest_of": "missing-task"
        }).to_string(),
    ).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    drop(router);
    let router2 = app(&db_str).unwrap();
    let (status, readback) = call(&router2, "GET", "/api/v1/machine/tasks/retest-task", None, "").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(readback["knowledge_version"], successor_id);
    assert_eq!(readback["retest_of"], "failed-task");
    assert_eq!(readback["outcome"], "succeeded");
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
