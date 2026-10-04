use archeaxis_application::executor::Executor;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;

#[tokio::test]
async fn unavailable_donor_is_an_explicit_worker_outcome_without_a_course_write() {
    let dir = tempfile::tempdir().unwrap();
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();
    let script = dir.path().join("course.py");
    std::fs::copy(
        root.join("services/python-workers/course/worker_general_course.py"),
        &script,
    )
    .unwrap();
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python,
        &script,
        &[("course.general", script.clone())],
    )
    .await
    .unwrap();
    let app = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"manifest":{},"bindings":[{"component_id":"x","knowledge_id":"x","knowledge_version":"x","source_id":"x","source_revision":"x"}]});
    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/courses")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status().as_u16(), 503);
    let value: Value =
        serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(value["worker_outcome"]["exit_code"], 2);
    assert_eq!(
        value["worker_outcome"]["document"]["status"], "UNAVAILABLE",
        "{value}"
    );
    assert_eq!(
        executor
            .store()
            .submit_wait(|conn| conn
                .query_row("SELECT count(*) FROM general_courses", [], |r| r
                    .get::<_, i64>(0))
                .unwrap())
            .await
            .unwrap(),
        0
    );
}
