//! Real local model end to end for the interactive outline and scene chain: the
//! same Runtime router, the pinned Node interactive adapters and the Python
//! local-model worker the product uses, with the operator's declared loopback
//! model answering instead of a stub. Gated so CI never reaches a model:
//!
//!   ARCHEAXIS_TEST_REAL_MODEL=1
//!   ARCHEAXIS_MACHINE_ENDPOINT / _MODEL / _PROTOCOL   (declare the local lane)
//!   ARCHEAXIS_TEST_NODE / ARCHEAXIS_TEST_NODE_SHA256   (pinned Node)
//!   ARCHEAXIS_PYTHON                                   (worker interpreter)
//!
//! A real model is not a fixture, so this asserts the engineering contract for
//! outcomes instead of demanding one reply. An admitted reply must stay inside
//! the bounded slice and be durable across a reopen; a refused or unavailable
//! stage must arrive named and must leave no partial document behind. A valid
//! outline without an interactive entry is recorded separately. Whether the course
//! is any good is a separate judgement: quality needs human truth/prediction pairs.
use archeaxis_api::runtime;
use archeaxis_application::executor::Executor;
use archeaxis_domain::document;
use archeaxis_store_sqlite::init_workspace;
use axum::{Router, body::Body, http::Request, http::StatusCode};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use tower::ServiceExt;

const OUTLINE_ROUTE: &str = "/api/v1/courses/openmaic/outlines/generate-interactive";
const SCENE_ROUTE: &str = "/api/v1/courses/openmaic/scenes/generate";
const CAPABILITY: &str = "course.openmaic.outline-model";
const WIDGET_TYPES: [&str; 5] = ["simulation", "diagram", "code", "game", "visualization3d"];

fn repository() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

fn scene_script() -> PathBuf {
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

async fn call(router: &Router, route: &str, actor: &str, body: &Value) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(route)
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

fn outline_body(create_request_id: &str) -> Value {
    json!({"create_request_id":create_request_id,
        "requirement":"用一张流程图讲解间隔复习的复习点如何逐步拉长，再配一节讲解页。",
        "source_text":"间隔复习把复习分散到逐渐拉长的时间间隔中，以改善长期记忆保持。",
        "model":Value::Null})
}

fn scene_body(
    create_request_id: &str,
    outline_document_id: &str,
    index: usize,
    source: &Value,
) -> Value {
    json!({"create_request_id":create_request_id,
        "outline_document_id":outline_document_id,"outline_index":index,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},"model":Value::Null})
}

/// A worker-backed refusal has to say which bounded rule it hit. Scene failures
/// that come from document or snapshot state carry no worker outcome at all, so
/// the shape is checked only where a worker actually answered.
fn named_refusal(response: &Value) {
    if response["worker_outcome"].is_null() {
        return;
    }
    let outcome = &response["worker_outcome"];
    assert!(
        outcome["status"]
            .as_str()
            .is_some_and(|name| !name.is_empty()),
        "{response}"
    );
    assert!(
        outcome["differences"].is_array() && outcome["transformations"].is_array(),
        "a worker refusal must carry its bounded rule names: {response}"
    );
}

#[tokio::test]
async fn the_declared_local_model_either_generates_or_refuses_without_a_partial_write() {
    if std::env::var("ARCHEAXIS_TEST_REAL_MODEL").as_deref() != Ok("1") {
        eprintln!("skipping: ARCHEAXIS_TEST_REAL_MODEL is not 1; this skip is not evidence");
        return;
    }
    let model = std::env::var("ARCHEAXIS_MACHINE_MODEL").expect("declared local model");
    let endpoint = std::env::var("ARCHEAXIS_MACHINE_ENDPOINT").expect("declared local endpoint");
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
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let source = document::create_optional(
        &mut conn,
        None,
        None,
        "synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    drop(conn);
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker(),
        &[(CAPABILITY, model_worker())],
    )
    .await
    .unwrap()
    .with_openmaic_node(&node, &expected_sha, &scene_script())
    .unwrap();
    let router = runtime::router(executor.clone());

    // A machine actor may not ask for material-bearing generation.
    let (status, denied) = call(&router, OUTLINE_ROUTE, "machine", &outline_body("rm_io_no")).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");
    let stored = document_count(&executor).await;

    let request = outline_body("rm_io_outline");
    let (status, outline) = call(&router, OUTLINE_ROUTE, "human", &request).await;
    if status != StatusCode::OK {
        // A replay refusal is 422; model failure or an unavailable adapter is
        // a distinct outcome, not a successful outline or a shape refusal.
        let outcome = match outline["stage"].as_str() {
            Some("interactive_outline") if status == StatusCode::UNPROCESSABLE_ENTITY => {
                assert!(!outline["worker_outcome"].is_null(), "{outline}");
                "OUTLINE_REFUSED"
            }
            Some("interactive_outline")
                if status == StatusCode::SERVICE_UNAVAILABLE
                    || status == StatusCode::BAD_GATEWAY =>
            {
                "OUTLINE_PROVIDER_UNAVAILABLE"
            }
            Some("local_model")
                if status == StatusCode::UNPROCESSABLE_ENTITY
                    || status == StatusCode::SERVICE_UNAVAILABLE
                    || status == StatusCode::GATEWAY_TIMEOUT =>
            {
                "OUTLINE_MODEL_FAILURE"
            }
            _ => panic!("unexpected outline failure: {status} {outline}"),
        };
        named_refusal(&outline);
        assert_eq!(document_count(&executor).await, stored, "{outline}");
        println!(
            "{}",
            json!({"schema":"archeaxis.openmaic-interactive-real-model-receipt/v1",
                "outcome":outcome,"endpoint":endpoint,"model":model,
                "status":status.as_u16(),"stage":outline["stage"],
                "detail":outline["worker_outcome"],"documents":stored,
                "quality":"NOT_ASSESSED"})
        );
        return;
    }
    assert_eq!(outline["worker_invoked"], true);
    assert_eq!(
        outline["generation_route"],
        "local_model_interactive_outline"
    );
    assert_eq!(outline["model_call"], "INVOKED");
    assert_eq!(outline["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(outline["model"], Value::String(model.clone()));
    assert_eq!(outline["rendering_authorized"], false);
    assert_eq!(outline["active_content_executed"], false);
    assert_eq!(outline["candidate_document_status"], "current");
    let outlines = outline["outlines"].as_array().unwrap().clone();
    assert_eq!(
        outlines.len() as u64,
        outline["outline_count"].as_u64().unwrap(),
        "{outline}"
    );
    // Whatever the model wrote, only slide or ordinary interactive entries may
    // persist, and each interactive entry names one admitted widget.
    for entry in outlines.iter() {
        assert!(
            ["slide", "interactive"].contains(&entry["type"].as_str().unwrap_or("")),
            "{entry}"
        );
        if entry["type"] == "interactive" {
            assert!(
                WIDGET_TYPES.contains(&entry["widgetType"].as_str().unwrap_or("")),
                "{entry}"
            );
        }
    }
    let outline_id = outline["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let after_outline = document_count(&executor).await;
    assert!(after_outline > stored, "the candidate is not persisted");

    // A repeat under the same request ID reads the stored candidate back, asks
    // nothing of the lane and adds no document.
    let (status, repeat) = call(&router, OUTLINE_ROUTE, "human", &request).await;
    assert_eq!(status, StatusCode::OK, "{repeat}");
    assert_eq!(repeat["worker_invoked"], false);
    assert_eq!(repeat["document"]["document_id"], outline_id);
    assert_eq!(document_count(&executor).await, after_outline);

    let Some(selected) = outlines
        .iter()
        .position(|entry| entry["type"] == "interactive")
    else {
        println!(
            "{}",
            json!({"schema":"archeaxis.openmaic-interactive-real-model-receipt/v1",
                "outcome":"NO_INTERACTIVE_SCENE","endpoint":endpoint,"model":model,
                "outline_document_id":outline_id,"documents":after_outline,
                "quality":"NOT_ASSESSED"})
        );
        return;
    };
    let body = scene_body("rm_io_scene", &outline_id, selected, &source);
    let (scene_status, built) = call(&router, SCENE_ROUTE, "human", &body).await;
    if scene_status != StatusCode::OK {
        named_refusal(&built);
        assert_eq!(
            document_count(&executor).await,
            after_outline,
            "a refused scene wrote a document: {built}"
        );
        println!(
            "{}",
            json!({"schema":"archeaxis.openmaic-interactive-real-model-receipt/v1",
                "outcome":"SCENE_REFUSED","endpoint":endpoint,"model":model,
                "status":scene_status.as_u16(),"stage":built["stage"],
                "detail":built["worker_outcome"],"refusal":built["refusal"],
                "outline_document_id":outline_id,"selected_index":selected,
                "widget_type":outlines[selected]["widgetType"],
                "documents":after_outline,"quality":"NOT_ASSESSED"})
        );
        return;
    }
    assert_eq!(built["scene_route"], "interactive");
    assert_eq!(built["generation_route"], "outline_interactive_local_model");
    assert_eq!(built["html_execution"], "NOT_PERFORMED");
    assert_eq!(built["rendering_authorized"], false);
    assert_eq!(built["render"]["report"]["playable"], false);
    let scene_id = built["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let after_scene = document_count(&executor).await;
    assert!(
        after_scene > after_outline,
        "the scene candidate is missing"
    );

    // Reopen without Node or a registered model route: both candidates stay
    // readable and neither repeat runs a worker, so the durable state is the
    // whole story rather than a result that only exists in this process.
    drop(router);
    drop(executor);
    let reopened = Executor::open(&path, &dir.path().join("staging"), &python, &text_worker())
        .await
        .unwrap();
    let router = runtime::router(reopened.clone());
    let (status, reread) = call(&router, OUTLINE_ROUTE, "human", &request).await;
    assert_eq!(status, StatusCode::OK, "{reread}");
    assert_eq!(reread["worker_invoked"], false);
    assert_eq!(reread["document"]["document_id"], outline_id);
    let (status, scene_reread) = call(&router, SCENE_ROUTE, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{scene_reread}");
    assert_eq!(scene_reread["worker_invoked"], false);
    assert_eq!(scene_reread["document"]["document_id"], scene_id);
    assert_eq!(document_count(&reopened).await, after_scene);

    println!(
        "{}",
        json!({"schema":"archeaxis.openmaic-interactive-real-model-receipt/v1",
            "outcome":"GENERATED","endpoint":endpoint,"model":model,
            "outline_document_id":outline_id,"scene_document_id":scene_id,
            "selected_index":selected,"widget_type":outlines[selected]["widgetType"],
            "model_reply_sha256":outline["model_reply_sha256"],
            "restart_worker_invoked":[reread["worker_invoked"],scene_reread["worker_invoked"]],
            "documents":after_scene,"quality":"NOT_ASSESSED"})
    );
}
