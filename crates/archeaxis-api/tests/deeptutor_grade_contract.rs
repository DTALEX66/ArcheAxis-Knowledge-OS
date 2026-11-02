//! Negative contract checks for the formal DeepTutor grading route and the
//! activity read that projects its disposition. Synthetic requests only: none of
//! these cases reaches a worker, and no model or provider service is involved.
use archeaxis_application::executor::Executor;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;

const GRADE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade";
const ACTIVITIES: &str = "/api/v1/learning/provider-activities";

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn snapshot(document_id: &str) -> Value {
    json!({"document_id":document_id,"version":1,
        "content_sha256":"a".repeat(64)})
}

fn grade_request() -> Value {
    json!({"activity_id":"missing_activity","attempt_id":"missing_attempt",
        "request":{"client_event_id":"missing_event",
            "question_document":snapshot("missing_question"),
            "question_grant":snapshot("missing_grant"),"answer":"A"}})
}

async fn call(
    router: &axum::Router,
    method: &str,
    uri: &str,
    body: &Value,
    actor: Option<&str>,
) -> (StatusCode, Value) {
    let mut builder = Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json");
    if let Some(actor) = actor {
        builder = builder.header("x-archeaxis-actor", actor);
    }
    let response = router
        .clone()
        .oneshot(builder.body(Body::from(body.to_string())).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn router() -> (tempfile::TempDir, axum::Router) {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let staging = dir.path().join("staging");
    // The interpreter and default worker are never invoked by these cases; a
    // missing practice worker keeps the route fail-closed behind its guards.
    let python = std::env::current_exe().unwrap();
    let worker = repo().join("services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open_routes(&db, &staging, &python, &worker, &[])
        .await
        .unwrap();
    (dir, archeaxis_api::runtime::router(executor))
}

#[tokio::test]
async fn grade_route_rejects_a_machine_actor_before_any_reservation() {
    let (_dir, router) = router().await;
    let (status, body) = call(
        &router,
        "POST",
        GRADE_ROUTE,
        &grade_request(),
        Some("machine"),
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    assert_eq!(body["code"], "DEEPTUTOR_PRACTICE_GRADE");
    assert_eq!(body["reason"], "human_actor_required");
}

#[tokio::test]
async fn grade_route_rejects_malformed_or_unknown_request_shapes() {
    let (_dir, router) = router().await;
    // Missing required member.
    let missing = json!({"activity_id":"a","attempt_id":"b"});
    assert_eq!(
        call(&router, "POST", GRADE_ROUTE, &missing, Some("human"))
            .await
            .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    // Undeclared member.
    let mut extra = grade_request();
    extra["unexpected"] = json!(true);
    assert_eq!(
        call(&router, "POST", GRADE_ROUTE, &extra, Some("human"))
            .await
            .0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    // Invalid snapshot shape inside the request (not a 64-hex digest) is refused
    // as an invalid grade request rather than being looked up.
    let mut bad_snapshot = grade_request();
    bad_snapshot["request"]["question_document"] =
        json!({"document_id":"d","version":1,"content_sha256":"short"});
    let (status, body) = call(&router, "POST", GRADE_ROUTE, &bad_snapshot, Some("human")).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{body}");
    assert_eq!(body["reason"], "invalid_grade_request");
}

#[tokio::test]
async fn grade_route_enforces_its_32768_byte_body_limit() {
    let (_dir, router) = router().await;
    let mut oversized = grade_request();
    oversized["request"]["answer"] = json!("x".repeat(40_000));
    let (status, _body) = call(&router, "POST", GRADE_ROUTE, &oversized, Some("human")).await;
    assert_eq!(status, StatusCode::PAYLOAD_TOO_LARGE);
}

#[tokio::test]
async fn grade_route_reports_a_missing_activity_as_not_found() {
    let (_dir, router) = router().await;
    let (status, body) = call(
        &router,
        "POST",
        GRADE_ROUTE,
        &grade_request(),
        Some("human"),
    )
    .await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{body}");
    assert_eq!(body["code"], "DEEPTUTOR_PRACTICE_GRADE");
    assert_eq!(body["reason"], "practice_object_not_found");
}

#[tokio::test]
async fn activity_read_requires_a_human_and_reports_missing_records() {
    let (_dir, router) = router().await;
    let uri = format!("{ACTIVITIES}/missing_activity");
    let (status, body) = call(&router, "GET", &uri, &Value::Null, Some("machine")).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    assert_eq!(body["reason"], "human_actor_required");
    let (status, body) = call(&router, "GET", &uri, &Value::Null, Some("human")).await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{body}");
    assert_eq!(body["reason"], "practice_object_not_found");
}
