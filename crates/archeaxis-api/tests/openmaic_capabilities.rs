//! Node registration and settings are separate from Python routes; no model is involved.
use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    path::{Path, PathBuf},
    time::Duration,
};
use tower::ServiceExt;

const NAME: &str = "course.openmaic.scene-build";
const DETAIL: &str = "/api/v1/capabilities/course.openmaic.scene-build";
const ENABLED: &str = "/api/v1/capabilities/course.openmaic.scene-build/enabled";

fn worker() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/learning-providers/openmaic/scene-build-worker.mjs")
        .canonicalize()
        .unwrap()
}

fn sha(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

async fn executor(dir: &Path) -> Executor {
    Executor::open(
        &dir.join("workspace.sqlite"),
        &dir.join("staging"),
        &dir.join("unused-python"),
        &dir.join("unused-python-worker"),
    )
    .await
    .unwrap()
}

async fn request(router: &Router, method: &str, path: &str, body: &str) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .body(Body::from(body.to_owned()))
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
async fn absent_node_cannot_be_reported_or_enabled() {
    let dir = tempfile::tempdir().unwrap();
    let ex = executor(dir.path()).await;
    let router = archeaxis_api::runtime::router(ex.clone());
    assert_eq!(request(&router, "GET", DETAIL, "").await.0, 404);
    assert_eq!(
        request(&router, "PUT", ENABLED, r#"{"enabled":true}"#)
            .await
            .0,
        404
    );
    let count = ex
        .store()
        .submit_wait(|conn| {
            conn.query_row(
                "SELECT count(*) FROM capability_settings WHERE capability=?1",
                [NAME],
                |row| row.get::<_, i64>(0),
            )
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(count, 0);
    assert_eq!(
        ex.derived_json(NAME, json!({}), Duration::from_secs(1))
            .await
            .unwrap_err(),
        "OpenMAIC Node worker not configured"
    );
}

#[tokio::test]
async fn fake_node_is_typed_but_not_healthy_and_changes_fail_closed() {
    let dir = tempfile::tempdir().unwrap();
    let node = dir
        .path()
        .join(if cfg!(windows) { "node.exe" } else { "node" });
    let original = b"synthetic non-executable, not Node";
    std::fs::write(&node, original).unwrap();
    let ex = executor(dir.path()).await;
    assert!(
        ex.clone()
            .with_openmaic_node(&node, &"0".repeat(64), &worker())
            .is_err()
    );
    assert!(
        ex.clone()
            .with_openmaic_node(&node, "bad-sha", &worker())
            .is_err()
    );
    let ex = ex
        .with_openmaic_node(&node, &sha(original), &worker())
        .unwrap();
    let router = archeaxis_api::runtime::router(ex.clone());

    let (status, listing) = request(&router, "GET", "/api/v1/capabilities", "").await;
    assert_eq!(status, 200, "{listing}");
    let record = listing["capabilities"]
        .as_array()
        .unwrap()
        .iter()
        .find(|entry| entry["capability"] == NAME)
        .unwrap();
    assert_eq!(record["provider"]["kind"], "node-worker");
    assert_eq!(record["provider"]["uses_site_packages"], false);
    assert_eq!(
        record["provider"]["version_qualification"],
        "not_established"
    );
    // The declared scene contract tells a consumer which candidates exist; it does
    // not claim a job ran, and the render contract is not declared execution-ready.
    assert_eq!(
        record["provider"]["scene_contract"]["request_schema"],
        "archeaxis.openmaic-scene-build/v1"
    );
    assert_eq!(
        record["provider"]["scene_contract"]["scene_types"],
        json!(["slide", "quiz"])
    );
    assert_eq!(
        record["provider"]["scene_contract"]["candidate_contract_versions"],
        json!([
            "archeaxis.openmaic-scene-document/v1",
            "archeaxis.openmaic-scene-document/v2"
        ])
    );
    assert_eq!(
        record["provider"]["scene_contract"]["execution_verified"],
        false
    );
    assert_eq!(record["health"], "handshake_failed");
    assert_eq!(record["health_details"]["task_executed"], false);
    assert_eq!(record["health_details"]["hello_timeout_ms"], 2000);
    assert!(record["health_details"]["timeout_ms"].is_null());
    assert_eq!(listing["execution_verified"], false);

    let (status, disabled) = request(&router, "PUT", ENABLED, r#"{"enabled":false}"#).await;
    assert_eq!(status, 200, "{disabled}");
    assert_eq!(disabled["capability"]["enabled"], false);
    assert_eq!(
        ex.derived_json(NAME, json!({}), Duration::from_secs(1))
            .await
            .unwrap_err(),
        "derived capability is disabled"
    );
    let stored = ex
        .store()
        .submit_wait(|conn| archeaxis_store_sqlite::capability_settings::is_enabled(conn, NAME))
        .await
        .unwrap()
        .unwrap();
    assert!(!stored);
    let (status, enabled) = request(&router, "PUT", ENABLED, r#"{"enabled":true}"#).await;
    assert_eq!(status, 200, "{enabled}");
    assert_eq!(enabled["capability"]["enabled"], true);

    std::fs::write(&node, b"changed after the trusted profile was accepted").unwrap();
    let (_, changed) = request(&router, "GET", DETAIL, "").await;
    assert_eq!(changed["capability"]["health"], "handshake_failed");
    assert!(
        changed["capability"]["health_details"]["reason"]
            .as_str()
            .unwrap()
            .contains("identity mismatch")
    );
    assert_eq!(
        ex.derived_json(NAME, json!({}), Duration::from_secs(2))
            .await
            .unwrap_err(),
        "OpenMAIC Node worker unavailable or identity mismatch"
    );
}

#[tokio::test]
#[ignore = "requires explicit ARCHEAXIS_TEST_NODE; no PATH discovery or installed-runtime claim"]
async fn explicit_node_hello_is_observed_without_running_a_task() {
    let dir = tempfile::tempdir().unwrap();
    let node = PathBuf::from(
        std::env::var_os("ARCHEAXIS_TEST_NODE").expect("explicit Node path required"),
    )
    .canonicalize()
    .unwrap();
    let node_sha = sha(&std::fs::read(&node).unwrap());
    let ex = executor(dir.path())
        .await
        .with_openmaic_node(&node, &node_sha, &worker())
        .unwrap();
    let router = archeaxis_api::runtime::router(ex);
    let (status, body) = request(&router, "GET", DETAIL, "").await;
    assert_eq!(status, 200, "{body}");
    assert_eq!(body["capability"]["provider"]["kind"], "node-worker");
    assert_eq!(body["capability"]["health"], "handshake_ready", "{body}");
    assert_eq!(body["capability"]["health_details"]["task_executed"], false);
    assert_eq!(
        body["capability"]["provider"]["version_qualification"],
        "not_established"
    );
}
