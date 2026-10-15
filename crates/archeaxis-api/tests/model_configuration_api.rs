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
async fn finite_nonsecret_configuration_cas_authority_and_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("db");
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python"));
    let executor = Executor::open(&db, &dir.path().join("staging"), &python, &worker)
        .await
        .unwrap();
    let app = archeaxis_api::runtime::router(executor);
    let (status, c) = call(
        &app,
        "GET",
        "/api/v1/model-configuration",
        "human",
        json!({}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(c["revision"], 0);
    let identity = c.clone();
    let mut c = json!({"schema":"archeaxis.model-configuration/v1","revision":0,"profiles":{"local":{"endpoint":"http://127.0.0.1:1234/v1","protocol":"openai","model":"synthetic-model","credential_ref":null,"max_tokens":2048,"timeout_s":30}},"bindings":[{"purpose":"answer","lane":"deep","profile_id":"local"}]});
    c["workspace_id"] = identity["workspace_id"].clone();
    c["restore_epoch"] = identity["restore_epoch"].clone();
    let body = json!({"expected_revision":0,"configuration":c});
    assert_eq!(
        call(
            &app,
            "PUT",
            "/api/v1/model-configuration",
            "machine",
            body.clone()
        )
        .await
        .0,
        403
    );
    assert_eq!(
        call(
            &app,
            "PUT",
            "/api/v1/model-configuration",
            "human",
            body.clone()
        )
        .await
        .0,
        200
    );
    assert_eq!(
        call(&app, "PUT", "/api/v1/model-configuration", "human", body)
            .await
            .0,
        409
    );
    let (status, resolved) = call(
        &app,
        "POST",
        "/api/v1/model-configuration/resolve",
        "human",
        json!({"purpose":"answer","lane":"deep"}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(resolved["profile"]["model"], "synthetic-model");
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/model-configuration/resolve",
            "human",
            json!({"purpose":"answer","lane":"fast"})
        )
        .await
        .0,
        422
    );
    drop(app);
    let executor = Executor::open(&db, &dir.path().join("staging"), &python, &worker)
        .await
        .unwrap();
    let app = archeaxis_api::runtime::router(executor);
    let (status, c) = call(
        &app,
        "GET",
        "/api/v1/model-configuration",
        "human",
        json!({}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(c["revision"], 1);
}
