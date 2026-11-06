//! Real local model end to end for OpenMAIC outline generation.
//!
//! This is the same Runtime router, pinned Node outline worker and Python
//! local-model worker the product uses; the only difference from the synthetic
//! suite is that the operator's declared loopback model answers instead of a
//! stub. It is gated on explicit environment so CI never reaches a model:
//!
//!   ARCHEAXIS_TEST_REAL_MODEL=1
//!   ARCHEAXIS_MACHINE_ENDPOINT / _MODEL / _PROTOCOL   (declare the local lane)
//!   ARCHEAXIS_TEST_NODE / ARCHEAXIS_TEST_NODE_SHA256   (pinned Node)
//!   ARCHEAXIS_PYTHON                                   (worker interpreter)
//!
//! A skip is not evidence, and a model reply remains an unverified candidate.
use archeaxis_application::executor::Executor;
use archeaxis_store_sqlite::init_workspace;
use axum::{Router, body::Body, http::Request, http::StatusCode};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/courses/openmaic/outlines/generate";
const CAPABILITY: &str = "course.openmaic.outline-model";

fn repository() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

fn outline_script() -> PathBuf {
    repository()
        .join("services/learning-providers/openmaic/scene-build-worker.mjs")
        .canonicalize()
        .unwrap()
}

fn model_worker() -> PathBuf {
    repository()
        .join("services/python-workers/course/worker_outline_local_model.py")
        .canonicalize()
        .unwrap()
}

fn text_worker() -> PathBuf {
    repository().join("services/python-workers/transport/text_ndjson.py")
}

async fn call(router: &Router, body: &Value) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(ROUTE)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
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

fn body(create_request_id: &str) -> Value {
    json!({"create_request_id":create_request_id,
        "requirement":"为“间隔复习”生成一份两场景的入门课程大纲：先讲原理，再给出一道单选题。",
        "source_text":"间隔复习把复习分散到逐渐拉长的时间间隔中，以改善长期记忆保持。",
        "model":Value::Null})
}

#[tokio::test]
async fn a_declared_local_model_generates_a_persisted_outline_candidate() {
    if std::env::var("ARCHEAXIS_TEST_REAL_MODEL").as_deref() != Ok("1") {
        eprintln!("skipping: ARCHEAXIS_TEST_REAL_MODEL is not 1; this skip is not evidence");
        return;
    }
    let endpoint = std::env::var("ARCHEAXIS_MACHINE_ENDPOINT").expect("declared local endpoint");
    let model = std::env::var("ARCHEAXIS_MACHINE_MODEL").expect("declared local model");
    let node = PathBuf::from(std::env::var_os("ARCHEAXIS_TEST_NODE").expect("pinned Node path"));
    let expected_sha = std::env::var("ARCHEAXIS_TEST_NODE_SHA256").expect("pinned Node hash");
    assert!(node.is_absolute());
    assert_eq!(
        format!("{:x}", Sha256::digest(std::fs::read(&node).unwrap())),
        expected_sha
    );
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("the canonical isolated interpreter is required")
        .into();
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    init_workspace(path.to_str().unwrap()).unwrap();
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker(),
        &[(CAPABILITY, model_worker())],
    )
    .await
    .unwrap()
    .with_openmaic_node(&node, &expected_sha, &outline_script())
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());

    let request = body("real_model_outline_1");
    let (status, first) = call(&router, &request).await;
    assert_eq!(status, StatusCode::OK, "{first}");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(first["generation_route"], "local_model");
    assert_eq!(first["model_call"], "INVOKED");
    assert_eq!(first["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(first["rendering_authorized"], false);
    assert_eq!(first["active_content_executed"], false);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["model"], Value::String(model.clone()));
    let count = first["outline_count"].as_u64().unwrap_or(0);
    assert!((1..=30).contains(&count), "{first}");
    for outline in first["outlines"].as_array().unwrap() {
        assert!(!outline["id"].as_str().unwrap_or("").is_empty());
        assert!(["slide", "quiz"].contains(&outline["type"].as_str().unwrap_or("")));
        assert!(!outline["title"].as_str().unwrap_or("").trim().is_empty());
    }
    let candidate_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    assert_eq!(document_count(&executor).await, 1);
    drop(router);
    drop(executor);

    // Reopen without Node or a registered model route: the candidate is durable,
    // and a repeat never asks the model again.
    let reopened = Executor::open(&path, &dir.path().join("staging"), &python, &text_worker())
        .await
        .unwrap();
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, duplicate) = call(&router, &request).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&reopened).await, 1);

    println!(
        "{}",
        json!({"schema":"archeaxis.openmaic-outline-real-model-receipt/v1",
            "endpoint":endpoint,"model":model,"document_id":candidate_id,
            "outline_count":count,"outlines":first["outlines"],
            "model_reply_sha256":first["model_reply_sha256"],
            "prompt_binding":first["prompt_binding"],
            "response_origin":first["response_origin"],
            "restart_worker_invoked":duplicate["worker_invoked"],
            "candidate_document_status":first["candidate_document_status"],
            "rendering_authorized":false,"human_review_required":true})
    );
}
