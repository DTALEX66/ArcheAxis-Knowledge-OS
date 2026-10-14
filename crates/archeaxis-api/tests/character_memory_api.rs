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
async fn only_human_admits_memory_and_enabled_context_is_finite() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("db");
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python"));
    let executor = Executor::open(&db, &dir.path().join("staging"), &python, &worker)
        .await
        .unwrap();
    let app = archeaxis_api::runtime::router(executor);
    assert_eq!(
        call(
            &app,
            "GET",
            "/api/v1/character-memory",
            "machine",
            json!({})
        )
        .await
        .0,
        403
    );
    let (status, p) = call(&app, "GET", "/api/v1/character-memory", "human", json!({})).await;
    assert_eq!(status, 200);
    let write = json!({"workspace_id":p["workspace_id"],"restore_epoch":p["restore_epoch"],"expected_revision":0,"command":{"operation":"remember","memory":{"id":"m1","text":"synthetic preference","provenance":"explicit human fixture"}}});
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/character-memory",
            "machine",
            write.clone()
        )
        .await
        .0,
        403
    );
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/character-memory",
            "human",
            write.clone()
        )
        .await
        .0,
        200
    );
    assert_eq!(
        call(&app, "POST", "/api/v1/character-memory", "human", write)
            .await
            .0,
        409
    );
    let (status, context) = call(
        &app,
        "GET",
        "/api/v1/character-memory/context",
        "machine",
        json!({}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(context["approved_memories"], json!([]));
    let enable = json!({"workspace_id":p["workspace_id"],"restore_epoch":p["restore_epoch"],"expected_revision":1,"command":{"operation":"enable"}});
    assert_eq!(
        call(&app, "POST", "/api/v1/character-memory", "human", enable)
            .await
            .0,
        200
    );
    let (_, context) = call(
        &app,
        "GET",
        "/api/v1/character-memory/context",
        "machine",
        json!({}),
    )
    .await;
    assert_eq!(context["approved_memories"][0]["id"], "m1");
    assert_eq!(context["grants"], json!([]));
    assert_eq!(context["knowledge_admitted"], false);
    assert_eq!(
        call(
            &app,
            "GET",
            "/api/v1/character-memory/export",
            "machine",
            json!({})
        )
        .await
        .0,
        403
    );
    let (_, export) = call(
        &app,
        "GET",
        "/api/v1/character-memory/export",
        "human",
        json!({}),
    )
    .await;
    assert_eq!(export["network_performed"], false);
    assert_eq!(export["profile"]["memories"][0]["id"], "m1");
}
