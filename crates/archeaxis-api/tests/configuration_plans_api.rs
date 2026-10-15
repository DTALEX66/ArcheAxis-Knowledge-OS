use archeaxis_application::executor::Executor;
use archeaxis_domain::model_configuration::{self, Profile};
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

async fn call(app: &axum::Router, method: &str) -> (u16, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri("/api/v1/configuration-plans")
                .body(Body::empty())
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
async fn real_store_read_is_repeatable_without_sql_writes_worker_launch_or_install_ports() {
    let dir = tempfile::tempdir().unwrap();
    let marker = dir.path().join("unexpected-worker-launch");
    let worker = dir.path().join("worker.py");
    std::fs::write(&worker, format!("from pathlib import Path\nPath({:?}).touch()\nraise RuntimeError('plan must never launch worker')\n", marker.to_string_lossy())).unwrap();
    let python =
        std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python"));
    let executor = Executor::open(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python,
        &worker,
    )
    .await
    .unwrap();
    let store = executor.store().clone();
    let before_first_read = store
        .submit_wait(|conn| {
            conn.query_row("SELECT total_changes()", [], |row| row.get::<_, i64>(0))
        })
        .await
        .unwrap()
        .unwrap();
    let app = archeaxis_api::runtime::router(executor);
    // An uninitialized workspace must be unavailable, not initialized by a plan read.
    let initial = call(&app, "GET").await;
    let after_first_read = store
        .submit_wait(|conn| {
            let changes =
                conn.query_row("SELECT total_changes()", [], |row| row.get::<_, i64>(0))?;
            let identities = conn.query_row(
                "SELECT count(*) FROM workspace_meta WHERE key='ui_workspace_identity_v1'",
                [],
                |row| row.get::<_, i64>(0),
            )?;
            Ok::<_, rusqlite::Error>((changes, identities))
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(after_first_read, (before_first_read, 0));
    assert_eq!(initial.0, 500);
    assert_eq!(initial.1["error"], "CONFIGURATION_PLANS_UNAVAILABLE");
    store
        .submit_wait(|conn| {
            let mut c = model_configuration::read(conn)?;
            c.profiles.insert(
                "local".into(),
                Profile {
                    endpoint: "http://127.0.0.1:1234/v1".into(),
                    protocol: "openai".into(),
                    model: "synthetic-model".into(),
                    credential_ref: None,
                    max_tokens: 2048,
                    timeout_s: 30,
                },
            );
            model_configuration::put(conn, 0, c)?;
            archeaxis_store_sqlite::capability_settings::set_enabled(conn, "text.extract", false)?;
            conn.query_row("SELECT total_changes()", [], |row| row.get::<_, i64>(0))
        })
        .await
        .unwrap()
        .unwrap();
    let before = store
        .submit_wait(|c| c.query_row("SELECT total_changes()", [], |r| r.get::<_, i64>(0)))
        .await
        .unwrap()
        .unwrap();
    let (status, first) = call(&app, "GET").await;
    assert_eq!(status, 200);
    assert_eq!(first["configuration_revision"], 1);
    assert_eq!(first["plans"].as_array().unwrap().len(), 2);
    assert!(!first["modules"].as_array().unwrap().is_empty());
    assert_eq!(
        first["modules"]
            .as_array()
            .unwrap()
            .iter()
            .find(|m| m["capability"] == "text.extract")
            .unwrap()["enabled"],
        false
    );
    assert_eq!(first["execution_grant"], Value::Null);
    assert_eq!(first["network_performed"], false);
    assert_eq!(first["storage_changed"], false);
    assert_eq!(first["worker_started"], false);
    assert_eq!(call(&app, "GET").await, (200, first));
    for method in ["POST", "PUT", "DELETE"] {
        assert_eq!(call(&app, method).await.0, 405);
    }
    let after = store
        .submit_wait(|c| c.query_row("SELECT total_changes()", [], |r| r.get::<_, i64>(0)))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(before, after);
    assert!(!marker.exists());
}
