//! Configuration plans only enumerate an explicit Node registration; they run no task.
use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use tower::ServiceExt;

const NODE_CAPABILITY: &str = "course.openmaic.scene-build";

fn worker() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/learning-providers/openmaic/scene-build-worker.mjs")
        .canonicalize()
        .unwrap()
}

async fn catalog(router: &Router) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
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

fn node_module(body: &Value) -> Option<&Value> {
    body["modules"]
        .as_array()
        .unwrap()
        .iter()
        .find(|item| item["capability"] == NODE_CAPABILITY)
}

#[tokio::test]
async fn configured_node_is_listed_read_only_as_unverified_and_obeys_settings() {
    let dir = tempfile::tempdir().unwrap();
    let node = dir
        .path()
        .join(if cfg!(windows) { "node.exe" } else { "node" });
    let fake = b"synthetic non-executable";
    std::fs::write(&node, fake).unwrap();
    let digest = format!("{:x}", Sha256::digest(fake));
    let ex = Executor::open(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    // Establish an owned workspace identity; the subsequent plan reads must not write.
    ex.store()
        .submit_wait(|conn| archeaxis_domain::model_configuration::read(conn))
        .await
        .unwrap()
        .unwrap();
    let absent = archeaxis_api::runtime::router(ex.clone());
    let (status, body) = catalog(&absent).await;
    assert_eq!(status, 200, "{body}");
    assert!(node_module(&body).is_none());
    assert!(
        ex.clone()
            .with_openmaic_node(&node, &"0".repeat(64), &worker())
            .is_err()
    );
    assert!(node_module(&catalog(&absent).await.1).is_none());

    let ex = ex.with_openmaic_node(&node, &digest, &worker()).unwrap();
    let configured = archeaxis_api::runtime::router(ex.clone());
    let before = ex
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT total_changes()", [], |row| row.get::<_, i64>(0))
        })
        .await
        .unwrap()
        .unwrap();
    let (status, first) = catalog(&configured).await;
    assert_eq!(status, 200, "{first}");
    let module = node_module(&first).unwrap();
    assert_eq!(module["enabled"], true);
    assert_eq!(module["runtime_qualification"], "UNVERIFIED");
    assert_eq!(module.as_object().unwrap().len(), 3);
    assert_eq!(first["worker_started"], false);
    assert_eq!(first["network_performed"], false);
    assert_eq!(first["storage_changed"], false);
    assert!(first["execution_grant"].is_null());
    assert_eq!(catalog(&configured).await, (200, first));
    let after = ex
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT total_changes()", [], |row| row.get::<_, i64>(0))
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(before, after);

    ex.set_openmaic_enabled(false).await.unwrap();
    let before = ex
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT total_changes()", [], |row| row.get::<_, i64>(0))
        })
        .await
        .unwrap()
        .unwrap();
    // A changed binary is still only a registered, unverified plan entry. Its
    // identity and execution are checked separately by health/derived admission.
    std::fs::write(&node, b"changed after registration").unwrap();
    let (status, disabled) = catalog(&configured).await;
    assert_eq!(status, 200, "{disabled}");
    let module = node_module(&disabled).unwrap();
    assert_eq!(module["enabled"], false);
    assert_eq!(module["runtime_qualification"], "UNVERIFIED");
    assert_eq!(disabled["worker_started"], false);
    let after = ex
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT total_changes()", [], |row| row.get::<_, i64>(0))
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(before, after);
}
