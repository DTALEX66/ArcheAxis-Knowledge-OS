use archeaxis_application::executor::Executor;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;
async fn call(
    app: &axum::Router,
    method: &str,
    path: &str,
    actor: &str,
    body: Value,
) -> (u16, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}
#[tokio::test]
async fn readiness_is_scoped_input_free_and_rechecked_before_execution() {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("db");
    let worker = d.path().join("fixture.py");
    std::fs::write(&worker,"from pathlib import Path\nPath(__file__).with_suffix('.spawned').write_text('unexpected')\n").unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python"));
    let e = Executor::open_routes(
        &db,
        &d.path().join("staging"),
        &python,
        &worker,
        &[("machine.answer", worker.clone())],
    )
    .await
    .unwrap();
    let app = archeaxis_api::runtime::router(e.clone());
    let (status, s) = call(
        &app,
        "POST",
        "/api/v1/operation-readiness",
        "human",
        json!({"scope":"view:CAP-0050","operations":["machine.answer"]}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(s["operations"].as_array().unwrap().len(), 1);
    assert_eq!(s["aggregate"], "UNVERIFIED");
    assert_eq!(s["network_performed"], false);
    assert_eq!(s["models_loaded"], false);
    assert!(!worker.with_extension("spawned").exists());
    let (status, enabled) = call(
        &app,
        "PUT",
        "/api/v1/capabilities/machine.answer/enabled",
        "human",
        json!({"enabled":true}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(enabled["capability"]["enabled"], true);
    assert_eq!(enabled["capability"]["health"], "declared");
    assert!(!worker.with_extension("spawned").exists());
    archeaxis_api::runtime::readiness::require_execution_dependencies(&e, "machine.answer")
        .await
        .unwrap();
    let _ = call(
        &app,
        "PUT",
        "/api/v1/capabilities/machine.answer/enabled",
        "human",
        json!({"enabled":false}),
    )
    .await;
    assert!(
        archeaxis_api::runtime::readiness::require_execution_dependencies(&e, "machine.answer")
            .await
            .is_err()
    );
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/operation-readiness",
            "human",
            json!({"scope":"view","operations":["machine.answer","machine.answer"]})
        )
        .await
        .0,
        422
    );
    assert!(!worker.with_extension("spawned").exists());
}

#[tokio::test]
async fn pdf_static_readiness_never_claims_engine_available_or_spawns_worker() {
    let d = tempfile::tempdir().unwrap();
    let worker = d.path().join("pdf.py");
    std::fs::write(
        &worker,
        "raise AssertionError('static readiness spawned PDF')",
    )
    .unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python"));
    let e = Executor::open_routes(
        &d.path().join("db"),
        &d.path().join("staging"),
        &python,
        &worker,
        &[("pdf.extract", worker.clone())],
    )
    .await
    .unwrap();
    let app = archeaxis_api::runtime::router(e);
    let (status, value) = call(
        &app,
        "POST",
        "/api/v1/operation-readiness",
        "human",
        json!({"scope":"pdf-test","operations":["pdf.extract"]}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(value["operations"][0]["dependencies"], "UNKNOWN");
    assert_eq!(value["aggregate"], "UNVERIFIED");
    assert!(
        value["operations"][0]["reasons"]
            .as_array()
            .unwrap()
            .contains(&json!("PDF_ENGINE_NOT_OBSERVED"))
    );
    assert_eq!(
        std::fs::read_dir(d.path().join("staging")).unwrap().count(),
        0
    );
}
