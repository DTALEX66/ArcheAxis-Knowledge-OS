//! Real local model end to end for an OpenMAIC slide scene built from an outline.
//!
//! The outline candidate and the source document are synthetic; the Runtime
//! router, the pinned Node slide workers and the Python local-model worker are
//! the product's. Gated on explicit environment so CI never calls a model:
//!
//!   ARCHEAXIS_TEST_REAL_MODEL=1
//!   ARCHEAXIS_MACHINE_ENDPOINT / _MODEL / _PROTOCOL
//!   ARCHEAXIS_TEST_NODE / ARCHEAXIS_TEST_NODE_SHA256
//!   ARCHEAXIS_PYTHON
//!
//! A skip is not evidence, and the produced scene remains an unverified candidate.
//!
//! The lane must expose a context large enough for the donor slide prompt
//! (about 9,500 prompt tokens here). A lane loaded with the default 8,192-token
//! context answers 400 and Core names it `MODEL_REJECTED`, which is a capacity
//! decision for the operator, not a code defect: raise the loaded context and
//! rerun this test to obtain the success receipt.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{
    document,
    openmaic_outline::{
        self, OpenMaicLocalGeneration, OpenMaicOutlineGenerationPending,
        OpenMaicOutlineGenerationPreparation,
    },
};
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

const ROUTE: &str = "/api/v1/courses/openmaic/scenes/generate";
const CAPABILITY: &str = "course.openmaic.outline-model";

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
        .join("services/python-workers/openmaic/worker_outline_local_model.py")
        .canonicalize()
        .unwrap()
}

fn text_worker() -> PathBuf {
    repository().join("services/python-workers/transport/text_ndjson.py")
}

fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn outline_content() -> String {
    json!({"languageDirective":"用简体中文授课。","courseTitle":"合成课程",
        "outlines":[
            {"id":"o1","type":"slide","title":"间隔复习原理",
             "description":"讲解间隔复习的原理","keyPoints":["概念","科学依据"],
             "order":0}]})
    .to_string()
}

fn outline_request() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-generate/v1","create_request_id":"outline_1",
        "requirement":"生成一段间隔复习原理的讲解页","source_text":"间隔复习把复习分散到逐渐拉长的时间间隔中。",
        "model":null})
}

fn outline_binding() -> Value {
    let system = "SYNTHETIC_SYSTEM prompt";
    let user = "SYNTHETIC_USER prompt";
    json!({"schema":"archeaxis.openmaic-outline-prompt-binding/v1","request_id":"outline_1",
        "input_sha256":digest(b"unkeyed identity"),
        "upstream_manifest_sha256":digest(b"manifest"),
        "npm_members_sha256":digest(b"members"),
        "worker_sha256":digest(b"worker"),"guard_sha256":digest(b"guard"),
        "system":system,"user":user,
        "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())})
}

fn outline_worker_document() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-prompt-result/v1","status":"CANDIDATE",
        "reason":null,"request_id":"outline_1","stage":"replay",
        "response_origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
        "network_performed":false,"core_task":"NOT_CONNECTED",
        "core_authorization":"NOT_ESTABLISHED","canonical_bindings_verified":false,
        "identity_scope":"UNKEYED_COMPARISON_ONLY","binding_authentication":"NOT_PROVIDED",
        "source_snapshot_authority":"CALLER_DECLARED_ONLY","persisted":false,
        "active_content_executed":false,"human_review_required":true,
        "response_origin_verification":null,
        "data":{"languageDirective":"用简体中文授课。","courseTitle":"合成课程",
            "outlines":[
                {"id":"o1","type":"slide","title":"间隔复习原理",
                 "description":"讲解间隔复习的原理","keyPoints":["概念","科学依据"],
                 "order":0}]}})
}

fn seed(workspace: &std::path::Path) -> (String, Value) {
    let mut conn = init_workspace(workspace.to_str().unwrap()).unwrap();
    let request = outline_request();
    let content = outline_content();
    let pending: OpenMaicOutlineGenerationPending =
        match openmaic_outline::prepare_openmaic_outline_generation(
            &mut conn,
            "outline_1",
            &request,
        )
        .unwrap()
        {
            OpenMaicOutlineGenerationPreparation::Pending(value) => value,
            OpenMaicOutlineGenerationPreparation::Existing(_) => panic!("expected a fresh outline"),
        };
    let reply = json!({"schema":"archeaxis.openmaic-outline-model-reply/v1","status":"REPLY",
        "content":content,"content_sha256":digest(content.as_bytes()),
        "content_bytes":content.as_bytes().len(),"model":"synthetic-local-model",
        "observed_model":"synthetic-local-model","finish_reason":"stop",
        "usage":{"input_tokens":7,"output_tokens":3},"model_call":"INVOKED",
        "network_performed":true,"network_scope":"LOOPBACK_LOCAL_MODEL_ONLY",
        "model_output_verification":"UNREVIEWED_LOCAL_MODEL_TEXT","persisted":false,
        "core_task":"NOT_CONNECTED","human_review_required":true});
    let generation = OpenMaicLocalGeneration {
        binding: outline_binding(),
        model_reply: reply,
        replay_document: outline_worker_document(),
    };
    let outline = openmaic_outline::commit_openmaic_outline_generation(
        &mut conn,
        "outline_1",
        &request,
        &pending,
        &generation,
    )
    .unwrap();
    let outline_id = outline["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let source = document::create_optional(
        &mut conn,
        None,
        None,
        "synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    (outline_id, source)
}

fn body(outline_document_id: &str, source: &Value) -> Value {
    json!({"create_request_id":"real_slide_1","outline_document_id":outline_document_id,
        "outline_index":0,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},
        "model":Value::Null})
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

#[tokio::test]
async fn a_declared_local_model_builds_a_slide_scene_from_the_outline() {
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
    let (outline_id, source) = seed(&path);
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
    let router = archeaxis_api::runtime::router(executor.clone());

    let request = body(&outline_id, &source);
    let (status, first) = call(&router, &request).await;
    assert_eq!(status, StatusCode::OK, "{first}");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(first["generation_route"], "outline_slide_local_model");
    assert_eq!(first["model_call"], "INVOKED");
    assert_eq!(first["model"], Value::String(model.clone()));
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(
        first["outline_document_id"],
        Value::String(outline_id.clone())
    );
    assert_eq!(first["outline_index"], 0);
    let scene = &first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"];
    assert_eq!(
        scene["derived_metadata"]["response_origin"],
        "LOCAL_MODEL_UNVERIFIED"
    );
    assert_eq!(scene["rendering_authorized"], false);
    let scene_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let documents_before = document_count(&executor).await;
    drop(router);
    drop(executor);

    // Reopen without Node or a model route: the scene candidate is durable and a
    // repeat never asks the model again.
    let reopened = Executor::open(&path, &dir.path().join("staging"), &python, &text_worker())
        .await
        .unwrap();
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, duplicate) = call(&router, &request).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"]["document_id"], scene_id);
    assert_eq!(document_count(&reopened).await, documents_before);

    println!(
        "{}",
        json!({"schema":"archeaxis.openmaic-slide-real-model-receipt/v1",
            "endpoint":endpoint,"model":model,"document_id":scene_id,
            "outline_document_id":outline_id,"model_reply_sha256":first["model_reply_sha256"],
            "prompt_binding":first["prompt_binding"]["system_sha256"],
            "generation_route":first["generation_route"],
            "response_origin":scene["derived_metadata"]["response_origin"],
            "restart_worker_invoked":duplicate["worker_invoked"],
            "rendering_authorized":scene["rendering_authorized"],
            "human_review_required":scene["human_review_required"]})
    );
}
