//! In-process Runtime router with synthetic documents; no Node or model call.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{course::{self, OpenMaicPreparation}, document};
use archeaxis_store_sqlite::init_workspace;
use axum::{Router, body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/courses/openmaic/scenes";

fn request(source: &Value) -> Value {
    json!({"schema":"archeaxis.openmaic-scene-build/v1", "request_id":"req_1", "attempt":1,
        "source":{"document_id":source["document_id"],"version":source["version"],"content_sha256":source["content_sha256"]},
        "stage_id":"stage_1","scene_id":"scene_1", "outline":{"id":"outline_1","type":"quiz",
        "title":"Synthetic title","description":"Synthetic description","keyPoints":[],"order":0},
        "content":{"questions":[{"id":"q1","question":"Synthetic?","answer":"SYNTHETIC_PRIVATE_ANSWER"}]}, "actions":[]})
}

fn synthetic_worker(request: &Value) -> Value {
    let mut frame = serde_json::to_vec(request).unwrap();
    frame.push(b'\n');
    json!({"schema":"archeaxis.openmaic-scene-build-result/v1", "status":"CANDIDATE",
        "request_id":request["request_id"],"attempt":request["attempt"],"input_sha256":format!("{:x}", Sha256::digest(&frame)),
        "source":request["source"],"source_binding":"client_declared_unverified","provider":"openmaic",
        "provider_version":"1.3.0","generation_version":"0.3.28","authority_effect":"candidate_only",
        "model_call":"NOT_INVOKED","canonical_bindings_verified":false,"human_review_required":true,
        "active_content_executed":false,"rendering_authorized":false,"retry_bytes_stable":false,
        "scene":{"id":request["scene_id"],"stageId":request["stage_id"],"outlineId":request["outline"]["id"],
            "type":"quiz","title":request["outline"]["title"],"order":request["outline"]["order"],
            "content":{"type":"quiz","questions":request["content"]["questions"]},"actions":request["actions"]}})
}

async fn call(router: &Router, actor: &str, body: &Value) -> (StatusCode, Value) {
    let response = router.clone().oneshot(Request::builder().method("POST").uri(ROUTE)
        .header("content-type", "application/json").header("x-archeaxis-actor", actor)
        .body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

#[tokio::test]
async fn human_can_retrieve_prior_candidate_without_node_and_machine_cannot() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let source = document::create_optional(&mut conn, None, None, "synthetic material",
        json!({"type":"doc","content":[]})).unwrap();
    let request = request(&source);
    let pending = match course::prepare_openmaic_scene(&mut conn, "client_1", &request).unwrap() {
        OpenMaicPreparation::Pending(value) => value,
        _ => panic!("a fresh request must not exist"),
    };
    let seeded = course::commit_openmaic_scene(&mut conn, "client_1", &request, &pending, &synthetic_worker(&request)).unwrap();
    drop(conn);
    let ex = Executor::open(&path, &dir.path().join("staging"),
        &dir.path().join("unused-python"), &dir.path().join("unused-worker")).await.unwrap();
    let router = archeaxis_api::runtime::router(ex.clone());
    let body = json!({"create_request_id":"client_1","request":request});
    let (status, denied) = call(&router, "machine", &body).await;
    assert_eq!(status, StatusCode::FORBIDDEN);
    assert!(!denied.to_string().contains("SYNTHETIC_PRIVATE_ANSWER"));
    let (status, existing) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{existing}");
    assert_eq!(existing["worker_invoked"], false);
    assert_eq!(existing["document"], seeded["document"]);
    assert_eq!(existing["candidate_document_status"], "current");
    assert_eq!(existing["source_snapshot_status"], "current");
    assert_eq!(existing["rendering_authorized"], false);
    assert_eq!(existing["answer_secrecy"], "not_established");

    let mut fresh = body.clone();
    fresh["create_request_id"] = json!("client_2");
    let (status, unavailable) = call(&router, "human", &fresh).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{unavailable}");
    assert!(!unavailable.to_string().contains("SYNTHETIC_PRIVATE_ANSWER"));
    let count = ex.store().submit_wait(|conn|
        conn.query_row("SELECT count(*) FROM documents", [], |row| row.get::<_, i64>(0)))
        .await.unwrap().unwrap();
    assert_eq!(count, 2); // the source and previously seeded candidate only
}

#[tokio::test]
#[ignore = "requires explicit ARCHEAXIS_TEST_NODE and ARCHEAXIS_TEST_NODE_SHA256; runs real local Node and the pinned worker"]
async fn explicit_node_builds_and_persists_an_inert_scene_then_reopens_without_node() {
    use std::path::PathBuf;
    let node = PathBuf::from(std::env::var_os("ARCHEAXIS_TEST_NODE").expect("explicit Node path required"));
    assert!(node.is_absolute());
    let expected_sha = std::env::var("ARCHEAXIS_TEST_NODE_SHA256").expect("explicit Node SHA required");
    assert_eq!(expected_sha.len(), 64);
    let node_bytes = std::fs::metadata(&node).unwrap().len();
    assert!(node_bytes > 0 && node_bytes <= 512 * 1024 * 1024);
    assert_eq!(format!("{:x}", Sha256::digest(std::fs::read(&node).unwrap())), expected_sha);
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/learning-providers/openmaic/scene-build-worker.mjs")
        .canonicalize().unwrap();
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let source = document::create_optional(&mut conn, None, None, "synthetic material",
        json!({"type":"doc","content":[]})).unwrap();
    drop(conn);
    let mut request = request(&source);
    request["outline"]["type"] = json!("slide");
    request["outline"]["description"] = json!("SYNTHETIC_OUTLINE_DESCRIPTION");
    request["outline"]["keyPoints"] = json!(["SYNTHETIC_KEY_POINT"]);
    request["content"] = json!({"elements":[{"id":"text1","type":"text","content":"<p>synthetic</p>"}],
        "background":{"type":"solid","color":"#ffffff"},"remark":"SYNTHETIC_SLIDE_REMARK"});
    let body = json!({"create_request_id":"node_scene_1","request":request});
    let ex = Executor::open(&path, &dir.path().join("staging"),
        &dir.path().join("unused-python"), &dir.path().join("unused-worker")).await.unwrap()
        .with_openmaic_node(&node, &expected_sha, &worker).unwrap();
    let router = archeaxis_api::runtime::router(ex.clone());
    let (status, first) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{first}");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["source_snapshot_status"], "current");
    let stored = &first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"];
    let frame = stored["request_frame"].as_str().unwrap();
    assert_eq!(serde_json::from_str::<Value>(frame).unwrap(), body["request"]);
    assert!(frame.contains("SYNTHETIC_SLIDE_REMARK"));
    assert!(frame.contains("SYNTHETIC_OUTLINE_DESCRIPTION"));
    assert!(frame.contains("SYNTHETIC_KEY_POINT"));
    assert_eq!(stored["worker_document"]["scene"]["content"]["canvas"]["elements"], body["request"]["content"]["elements"]);
    assert_eq!(stored["worker_document"]["scene"]["content"]["canvas"]["background"], body["request"]["content"]["background"]);
    let candidate_id = first["document"]["document_id"].as_str().unwrap().to_owned();
    let source_id = source["document_id"].as_str().unwrap().to_owned();
    drop(router);
    drop(ex);

    // Reopen the same synthetic Core with no Node configured: a matching
    // request must read the already persisted version rather than rerun it.
    let reopened = Executor::open(&path, &dir.path().join("staging"),
        &dir.path().join("unused-python"), &dir.path().join("unused-worker")).await.unwrap();
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, duplicate) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"], first["document"]);

    reopened.store().submit_wait(move |conn| {
        document::save(conn, &candidate_id, 1, json!({"type":"doc","content":[]}))?;
        document::save(conn, &source_id, 1, json!({"type":"doc","content":[]}))?;
        Ok::<_, document::Error>(())
    }).await.unwrap().unwrap();
    let (status, historical) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{historical}");
    assert_eq!(historical["worker_invoked"], false);
    assert_eq!(historical["candidate_document_status"], "historical");
    assert_eq!(historical["source_snapshot_status"], "historical");
    assert_eq!(historical["document"], first["document"]);
    assert_eq!(format!("{:x}", Sha256::digest(std::fs::read(&node).unwrap())), expected_sha);
}
