//! In-process Runtime router for outline-driven OpenMAIC slide generation.
//! The gated test runs the pinned local Node slide adapters plus the fixed scene
//! builder and a synthetic loopback model stub; no real model, cloud provider or
//! user material is used.
use archeaxis_application::executor::{Executor, OpenMaicSlideStage};
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
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpListener,
    path::PathBuf,
    sync::{Arc, Mutex},
    thread,
};
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/courses/openmaic/scenes/generate";
const CAPABILITY: &str = "course.openmaic.outline-model";
const MODEL: &str = "synthetic-stub-model";

struct StubState {
    status: u16,
    content: String,
}

fn start_stub(content: String) -> (u16, Arc<Mutex<StubState>>, Arc<Mutex<usize>>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let state = Arc::new(Mutex::new(StubState {
        status: 200,
        content,
    }));
    let calls = Arc::new(Mutex::new(0_usize));
    let shared = state.clone();
    let counted = calls.clone();
    thread::spawn(move || {
        for stream in listener.incoming() {
            let Ok(mut stream) = stream else { break };
            let mut reader = BufReader::new(stream.try_clone().unwrap());
            let mut length = 0_usize;
            loop {
                let mut line = String::new();
                if !matches!(reader.read_line(&mut line), Ok(_)) || line.trim().is_empty() {
                    break;
                }
                if let Some(value) = line
                    .to_ascii_lowercase()
                    .strip_prefix("content-length:")
                    .map(str::trim)
                    .and_then(|value| value.parse::<usize>().ok())
                {
                    length = value.min(1 << 20);
                }
            }
            let mut body = vec![0_u8; length];
            let _ = reader.read_exact(&mut body);
            *counted.lock().unwrap() += 1;
            let state = shared.lock().unwrap();
            let payload = json!({"model": MODEL,
                "choices":[{"index":0,"finish_reason":"stop",
                    "message":{"role":"assistant","content":state.content}}],
                "usage":{"prompt_tokens":5,"completion_tokens":7}})
            .to_string();
            let response = format!(
                "HTTP/1.1 {} synthetic\r\nContent-Type: application/json\r\n\
                 Content-Length: {}\r\nConnection: close\r\n\r\n{}",
                state.status,
                payload.len(),
                payload
            );
            let _ = stream.write_all(response.as_bytes());
            let _ = stream.flush();
        }
    });
    (port, state, calls)
}

/// The exact donor reply shape: one text element and a solid background.
fn slide_reply_content() -> String {
    json!({"elements":[{"type":"text","left":60,"top":50,"width":880,"height":76,
            "rotate":0,"content":"SYNTHETIC_SLIDE_TEXT","defaultFontName":"",
            "defaultColor":""}],
        "background":{"type":"solid","color":"#ffffff"}})
    .to_string()
}

fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn outline_content() -> String {
    json!({"languageDirective":"Use Simplified Chinese.","courseTitle":"Synthetic course",
        "outlines":[
            {"id":"o1","type":"slide","title":"SYNTHETIC_SLIDE_TITLE",
             "description":"SYNTHETIC_SLIDE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
             "order":0},
            {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE","description":"",
             "keyPoints":[],"order":1}]})
    .to_string()
}

fn outline_request() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-generate/v1","create_request_id":"outline_1",
        "requirement":"Synthetic requirement","source_text":"SYNTHETIC source material",
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

fn outline_worker() -> Value {
    json!({"schema":"archeaxis.openmaic-outline-prompt-result/v1","status":"CANDIDATE",
        "reason":null,"request_id":"outline_1","stage":"replay",
        "response_origin":"CALLER_SUPPLIED_UNVERIFIED","model_call":"NOT_INVOKED",
        "network_performed":false,"core_task":"NOT_CONNECTED",
        "core_authorization":"NOT_ESTABLISHED","canonical_bindings_verified":false,
        "identity_scope":"UNKEYED_COMPARISON_ONLY","binding_authentication":"NOT_PROVIDED",
        "source_snapshot_authority":"CALLER_DECLARED_ONLY","persisted":false,
        "active_content_executed":false,"human_review_required":true,
        "response_origin_verification":null,
        "data":{"languageDirective":"Use Simplified Chinese.","courseTitle":"Synthetic course",
            "outlines":[
                {"id":"o1","type":"slide","title":"SYNTHETIC_SLIDE_TITLE",
                 "description":"SYNTHETIC_SLIDE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
                 "order":0},
                {"id":"o2","type":"quiz","title":"SYNTHETIC_QUIZ_TITLE","description":"",
                 "keyPoints":[],"order":1}]}})
}

/// Seed one committed outline candidate and one source document before the
/// executor opens the workspace, so this test qualifies the slide chain only.
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
        replay_document: outline_worker(),
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

fn request(outline_document_id: &str, index: i64, source: &Value) -> Value {
    json!({"create_request_id":"slide_1","outline_document_id":outline_document_id,
        "outline_index":index,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},
        "model":Value::Null})
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

#[tokio::test]
async fn one_slide_outline_becomes_a_scene_candidate_and_every_failure_stays_named() {
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
    assert_eq!(
        format!("{:x}", Sha256::digest(std::fs::read(&node).unwrap())),
        expected_sha
    );
    let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("the canonical isolated Python is required")
        .into();
    let (port, stub, calls) = start_stub(slide_reply_content());
    // SAFETY: this binary runs one test; the variables are set once, before any
    // worker is spawned, so no concurrent reader can observe a partial update.
    unsafe {
        std::env::set_var(
            "ARCHEAXIS_MACHINE_ENDPOINT",
            format!("http://127.0.0.1:{port}/v1"),
        );
        std::env::set_var("ARCHEAXIS_MACHINE_MODEL", MODEL);
        std::env::set_var("ARCHEAXIS_MACHINE_PROTOCOL", "openai");
    }
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
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
    let body = request(&outline_id, 0, &source);

    // A machine actor may not ask for material-bearing generation.
    let (status, denied) = call(&router, "machine", &body).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");
    assert_eq!(
        *calls.lock().unwrap(),
        0,
        "no model call for a refused actor"
    );
    assert_eq!(document_count(&executor).await, 2);

    let (status, first) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{first}");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(first["generation_route"], "outline_slide_local_model");
    assert_eq!(first["model_call"], "INVOKED");
    assert_eq!(first["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(first["rendering_authorized"], false);
    assert_eq!(first["active_content_executed"], false);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["source_snapshot_status"], "current");
    assert_eq!(
        first["contract_version"],
        "archeaxis.openmaic-scene-document/v2"
    );
    assert_eq!(first["projection"]["status"], "RECORDED");
    assert_eq!(first["render"]["status"], "RECORDED");
    assert_eq!(first["model"], MODEL);
    assert_eq!(first["outline_document_id"], outline_id.as_str());
    assert_eq!(first["outline_index"], 0);
    assert_eq!(first["outline_id"], "o1");
    assert_eq!(
        first["model_reply_sha256"],
        digest(slide_reply_content().as_bytes())
    );
    assert!(first["prompt_binding"]["system_sha256"].as_str().is_some());
    assert!(first["prompt_binding"]["user_sha256"].as_str().is_some());
    assert!(
        first["prompt_binding"].get("system").is_none(),
        "the stored prompt binding keeps digests only"
    );
    assert_eq!(first["reply"]["status"], "CANDIDATE");
    assert_eq!(first["normalize"]["status"], "CANDIDATE");
    let stored = &first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"]["derived_metadata"];
    assert_eq!(stored["schema"], "archeaxis.openmaic-slide-candidate/v1");
    assert_eq!(stored["generation_route"], "outline_slide_local_model");
    assert_eq!(stored["model_call"], "INVOKED");
    assert_eq!(stored["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(stored["human_review_required"], true);
    assert_eq!(stored["active_content_executed"], false);
    assert_eq!(stored["rendering_authorized"], false);
    // The persisted scene is the donor builder's own output for Core's request.
    let scene = &first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"]["worker_document"]
        ["scene"];
    assert_eq!(scene["type"], "slide");
    assert_eq!(scene["outlineId"], "o1");
    assert_eq!(scene["content"]["canvas"]["elements"][0]["type"], "text");
    let candidate_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    assert_eq!(*calls.lock().unwrap(), 1, "one model call");
    assert_eq!(document_count(&executor).await, 3);

    // A repeated request reads the candidate back without rerunning anything.
    let (status, duplicate) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"]["document_id"], candidate_id);
    assert_eq!(*calls.lock().unwrap(), 1, "a retry never re-runs the model");
    assert_eq!(document_count(&executor).await, 3);

    // A model lane that is unavailable is a named service error.
    *stub.lock().unwrap() = StubState {
        status: 500,
        content: String::new(),
    };
    let mut unavailable_body = body.clone();
    unavailable_body["create_request_id"] = json!("slide_unavailable");
    let (status, unavailable) = call(&router, "human", &unavailable_body).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{unavailable}");
    assert_eq!(unavailable["stage"], "local_model");
    assert_eq!(unavailable["worker_outcome"]["status"], "MODEL_UNAVAILABLE");
    assert_eq!(document_count(&executor).await, 3);

    // A lane with no final answer is a named timeout, never fabricated text.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: "   ".into(),
    };
    let mut timeout_body = body.clone();
    timeout_body["create_request_id"] = json!("slide_timeout");
    let (status, timeout) = call(&router, "human", &timeout_body).await;
    assert_eq!(status, StatusCode::GATEWAY_TIMEOUT, "{timeout}");
    assert_eq!(timeout["stage"], "local_model");
    assert_eq!(timeout["worker_outcome"]["status"], "NO_FINAL_ANSWER");
    assert_eq!(document_count(&executor).await, 3);

    // A reply the donor adapter cannot admit is refused with its own status and
    // reason; nothing is repaired and nothing is written.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: "not a slide reply".into(),
    };
    let mut reply_body = body.clone();
    reply_body["create_request_id"] = json!("slide_non_candidate");
    let (status, rejected) = call(&router, "human", &reply_body).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{rejected}");
    assert_eq!(rejected["stage"], "slide_reply");
    assert_eq!(rejected["worker_outcome"]["status"], "QUARANTINED");
    assert!(
        rejected["worker_outcome"]["reason"].as_str().is_some(),
        "{rejected}"
    );
    assert_eq!(document_count(&executor).await, 3);

    // Same create ID with different content conflicts before any stage.
    let mut conflict = body.clone();
    conflict["model"] = json!("another-model");
    let (status, conflict) = call(&router, "human", &conflict).await;
    assert_eq!(status, StatusCode::CONFLICT, "{conflict}");

    // A quiz outline is refused by type; it is not rewritten into a slide.
    let calls_before_quiz = *calls.lock().unwrap();
    let quiz_body = request(&outline_id, 1, &source);
    let (status, quiz) = call(&router, "human", &quiz_body).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{quiz}");
    assert_eq!(quiz["refusal"]["reason"], "UNSUPPORTED_OUTLINE_TYPE");
    assert_eq!(quiz["refusal"]["declared"], "quiz");
    assert_eq!(
        *calls.lock().unwrap(),
        calls_before_quiz,
        "no stage runs for a quiz outline"
    );
    assert_eq!(document_count(&executor).await, 3);
    drop(router);
    drop(executor);

    // Reopening without Node or a registered model route reads the candidate.
    let reopened = Executor::open(&path, &dir.path().join("staging"), &python, &text_worker())
        .await
        .unwrap();
    assert!(
        reopened
            .openmaic_slide_script(OpenMaicSlideStage::Prompt)
            .is_none()
    );
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, read_back) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{read_back}");
    assert_eq!(read_back["worker_invoked"], false);
    assert_eq!(read_back["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&reopened).await, 3);
}
