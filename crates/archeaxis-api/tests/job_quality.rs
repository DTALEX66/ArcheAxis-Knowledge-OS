//! R08: the quality view reports facts about a job's extraction - engine,
//! coverage, loss and region counts - and never an accuracy figure.

use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn get(router: &axum::Router, path: &str) -> (StatusCode, String) {
    let resp = router
        .clone()
        .oneshot(Request::get(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8_lossy(&bytes).to_string())
}

async fn post(router: &axum::Router, path: &str, body: &str) -> (StatusCode, Value) {
    let resp = router
        .clone()
        .oneshot(
            Request::post(path)
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

#[tokio::test]
async fn unknown_job_has_no_quality_view() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (status, _) = get(&router, "/api/v1/jobs/no-such-job/quality").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn a_queued_job_reports_facts_without_an_accuracy_claim() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    let (status, created) = post(
        &router,
        "/api/v1/imports",
        r#"{"name":"note.md","content_base64":"aGVsbG8gNjM3MQ=="}"#,
    )
    .await;
    assert!(status.is_success(), "unexpected import response: {created}");
    let source_id = created["source_id"].as_str().expect("source_id").to_string();

    let (status, queued) = post(
        &router,
        "/api/v1/jobs",
        &serde_json::json!({"job_id":"job-q","kind":"text","input_ref":source_id}).to_string(),
    )
    .await;
    assert!(matches!(status, StatusCode::ACCEPTED), "unexpected enqueue response: {queued}");

    let (status, body) = get(&router, "/api/v1/jobs/job-q/quality").await;
    assert_eq!(status, StatusCode::OK);
    let value: Value = serde_json::from_str(&body).unwrap();
    assert_eq!(value["job_id"], "job-q");
    assert_eq!(value["state"], "queued");
    assert_eq!(value["loss_count"], 0);
    assert_eq!(value["region_count"], 0);
    assert!(value["coverage"].is_null(), "no receipt yet means no coverage claim: {value}");
    assert!(value.get("accuracy").is_none(), "an accuracy figure must never be reported");
    assert!(
        value["note"].as_str().unwrap_or("").contains("not accuracy"),
        "the view must state that confidence is not accuracy: {value}"
    );
}
