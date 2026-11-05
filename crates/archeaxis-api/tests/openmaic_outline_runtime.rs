//! In-process Runtime router for OpenMAIC outline replay candidates.
//! The gated test runs the pinned local Node worker; it calls no model and no network.
use archeaxis_application::executor::Executor;
use archeaxis_store_sqlite::init_workspace;
use axum::{
    Router,
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/courses/openmaic/outlines";

fn outline_request(reply: Value) -> Value {
    json!({"schema":"archeaxis.openmaic-outline-replay/v1","request_id":"req_1",
        "requirement":"Synthetic outline requirement",
        "source_text":"SYNTHETIC_SOURCE_MATERIAL",
        "reply":reply})
}

fn candidate_reply() -> Value {
    let value = json!({"languageDirective":"Respond in Simplified Chinese.",
        "courseTitle":"Synthetic course",
        "outlines":[{"id":"outline_1","type":"slide","title":"Synthetic outline title",
            "description":"SYNTHETIC_OUTLINE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"]}]});
    json!({"kind":"synthetic_response","value":value.to_string()})
}

async fn call(router: &Router, actor: &str, body: &Value) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(ROUTE)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn document_count(executor: &Executor) -> i64 {
    executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT count(*) FROM documents", [], |row| {
                row.get::<_, i64>(0)
            })
        })
        .await
        .unwrap()
        .unwrap()
}

#[tokio::test]
async fn a_machine_actor_is_denied_and_an_unconfigured_provider_is_unavailable() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    init_workspace(path.to_str().unwrap()).unwrap();
    let executor = Executor::open(
        &path,
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"create_request_id":"machine_outline",
        "request":outline_request(candidate_reply())});
    let (status, denied) = call(&router, "machine", &body).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");
    assert!(!denied.to_string().contains("SYNTHETIC_OUTLINE_DESCRIPTION"));

    // A supported request reaches provider admission instead: with no Node
    // registration this is unavailability, not a refusal of the contract.
    let body = json!({"create_request_id":"unconfigured_outline",
        "request":outline_request(candidate_reply())});
    let (status, unavailable) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{unavailable}");
    assert!(
        !unavailable
            .to_string()
            .contains("SYNTHETIC_OUTLINE_DESCRIPTION")
    );
    assert_eq!(document_count(&executor).await, 0);
}

#[tokio::test]
async fn explicit_node_persists_an_outline_candidate_and_reopens_without_node() {
    let node = match std::env::var_os("ARCHEAXIS_TEST_NODE") {
        Some(value) => PathBuf::from(value),
        None => {
            eprintln!("skipping: ARCHEAXIS_TEST_NODE not set; this skip is not evidence");
            return;
        }
    };
    assert!(node.is_absolute());
    let expected_sha = match std::env::var("ARCHEAXIS_TEST_NODE_SHA256") {
        Ok(value) => value,
        Err(_) => {
            eprintln!("skipping: ARCHEAXIS_TEST_NODE_SHA256 not set; this skip is not evidence");
            return;
        }
    };
    assert_eq!(expected_sha.len(), 64);
    assert!(std::fs::metadata(&node).unwrap().is_file());
    assert_eq!(
        format!("{:x}", Sha256::digest(std::fs::read(&node).unwrap())),
        expected_sha
    );
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/learning-providers/openmaic/scene-build-worker.mjs")
        .canonicalize()
        .unwrap();
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    init_workspace(path.to_str().unwrap()).unwrap();
    let executor = Executor::open(
        &path,
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap()
    .with_openmaic_node(&node, &expected_sha, &worker)
    .unwrap();
    assert!(executor.openmaic_outline_script().is_some());
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"create_request_id":"node_outline_1",
        "request":outline_request(candidate_reply())});
    let (status, first) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{first}");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["outline_count"], 1);
    assert_eq!(first["rendering_authorized"], false);
    assert_eq!(first["active_content_executed"], false);
    assert_eq!(first["response_origin"], "client_declared_unverified");
    let stored = &first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_outline_candidate"];
    let frame = stored["request_frame"].as_str().unwrap();
    assert_eq!(
        serde_json::from_str::<Value>(frame).unwrap(),
        body["request"]
    );
    assert!(frame.contains("SYNTHETIC_SOURCE_MATERIAL"));
    assert_eq!(stored["model_call"], "NOT_INVOKED");
    assert_eq!(stored["human_review_required"], true);
    assert_eq!(stored["outlines"][0]["title"], "Synthetic outline title");
    assert_eq!(stored["outlines"][0]["key_points_count"], 1);
    let candidate_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();

    // The worker's own non-candidate outcome is preserved verbatim as a 422.
    let failing = json!({"create_request_id":"node_outline_error",
        "request":outline_request(json!({"kind":"synthetic_error"}))});
    let (status, failed) = call(&router, "human", &failing).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{failed}");
    assert_eq!(failed["code"], "AAK-VAL-001");
    assert_eq!(failed["retryable"], false);
    assert_eq!(failed["worker_outcome"]["status"], "UPSTREAM_FAILURE");
    assert_eq!(
        failed["worker_outcome"]["reason"],
        "upstream reported failure"
    );
    assert_eq!(failed["worker_outcome"]["exit_code"], 2);
    assert_eq!(document_count(&executor).await, 1);
    drop(router);
    drop(executor);

    // Reopen the same synthetic Core with no Node configured: a matching
    // request reads the persisted candidate rather than rerunning the worker.
    let reopened = Executor::open(
        &path,
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    assert_eq!(reopened.openmaic_outline_script(), None);
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, duplicate) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"], first["document"]);
    assert_eq!(duplicate["candidate_document_status"], "current");
    assert_eq!(duplicate["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&reopened).await, 1);
    assert_eq!(
        format!("{:x}", Sha256::digest(std::fs::read(&node).unwrap())),
        expected_sha
    );
}
