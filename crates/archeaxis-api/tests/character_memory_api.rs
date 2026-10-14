use archeaxis_application::executor::Executor;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::PathBuf;
use tower::ServiceExt;

#[tokio::test]
async fn human_profile_correction_export_and_forgetting_match_the_current_store() {
    let dir = tempfile::tempdir().unwrap();
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python"));
    let executor = Executor::open(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python,
        &worker,
    )
    .await
    .unwrap();
    let app = archeaxis_api::runtime::router(executor.clone());
    let (_, mut profile) = call(&app, "GET", "/api/v1/character-memory", "human", json!({})).await;
    for command in [
        json!({"operation":"profile","preferences":"synthetic calm style","learning_goals":"synthetic goal"}),
        json!({"operation":"remember","memory":{"id":"first","text":"synthetic first","provenance":"explicit human fixture"}}),
        json!({"operation":"remember","memory":{"id":"second","text":"synthetic second","provenance":"explicit human fixture"}}),
        json!({"operation":"correct","memory":{"id":"first","text":"synthetic corrected","provenance":"human correction fixture"}}),
        json!({"operation":"enable"}),
    ] {
        let body = json!({"workspace_id":profile["workspace_id"],"restore_epoch":profile["restore_epoch"],"expected_revision":profile["revision"],"command":command});
        let (status, receipt) = call(&app, "POST", "/api/v1/character-memory", "human", body).await;
        assert_eq!(status, 200);
        assert_eq!(receipt["schema"], "archeaxis.memory-write/v1");
        assert_eq!(receipt["forgotten_ids"], json!([]));
        assert_eq!(receipt["secure_erasure"], false);
        profile = receipt["profile"].clone();
        let (status, readback) =
            call(&app, "GET", "/api/v1/character-memory", "human", json!({})).await;
        assert_eq!(status, 200);
        assert_eq!(readback, profile);
    }
    assert_eq!(profile["revision"], 5);
    assert_eq!(profile["memories"][0]["text"], "synthetic corrected");
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
    let (status, export) = call(
        &app,
        "GET",
        "/api/v1/character-memory/export",
        "human",
        json!({}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(
        export,
        json!({"schema":"archeaxis.memory-export/v1","profile":profile,"contains_personal_memory":true,"network_performed":false})
    );
    for (command, forgotten) in [
        (json!({"operation":"forget","id":"first"}), json!(["first"])),
        (json!({"operation":"forget_all"}), json!(["second"])),
    ] {
        let body = json!({"workspace_id":profile["workspace_id"],"restore_epoch":profile["restore_epoch"],"expected_revision":profile["revision"],"command":command});
        let (status, receipt) = call(&app, "POST", "/api/v1/character-memory", "human", body).await;
        assert_eq!(status, 200);
        assert_eq!(receipt["forgotten_ids"], forgotten);
        assert_eq!(receipt["live_store_deleted"], true);
        assert_eq!(receipt["historical_chat_modified"], false);
        assert_eq!(receipt["backups_modified"], false);
        assert_eq!(receipt["secure_erasure"], false);
        profile = receipt["profile"].clone();
    }
    assert_eq!(profile["memories"], json!([]));
    assert_eq!(profile["preferences"], "synthetic calm style");
    let persisted = executor
        .store()
        .submit_wait(|connection| archeaxis_domain::character_memory::read(connection))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(serde_json::to_value(persisted).unwrap(), profile);
    let (_, context) = call(
        &app,
        "GET",
        "/api/v1/character-memory/context",
        "machine",
        json!({}),
    )
    .await;
    assert_eq!(context["approved_memories"], json!([]));
    assert_eq!(context["authority"], "human_preferences_only");
    assert_eq!(context["grants"], json!([]));
    assert_eq!(context["knowledge_admitted"], false);
}
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
