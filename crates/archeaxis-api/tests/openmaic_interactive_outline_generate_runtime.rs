//! In-process Runtime router for interactive-outline generation and the
//! following interactive scene. The gated test runs the pinned local Node
//! adapters and a synthetic loopback model stub; no real model, cloud provider
//! or user material is used.
use archeaxis_application::executor::Executor;
use archeaxis_domain::document;
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

const OUTLINE_ROUTE: &str = "/api/v1/courses/openmaic/outlines/generate-interactive";
const SCENE_ROUTE: &str = "/api/v1/courses/openmaic/scenes/generate";
const CAPABILITY: &str = "course.openmaic.outline-model";
const MODEL: &str = "synthetic-stub-model";
const SCENE_HTML: &str =
    "<!DOCTYPE html><html><body><main>SYNTHETIC_INTERACTIVE_HTML</main></body></html>";

struct StubState {
    status: u16,
    queue: Vec<String>,
    cursor: usize,
    requests: Vec<Value>,
}

impl StubState {
    fn new(status: u16, content: impl Into<String>) -> Self {
        Self {
            status,
            queue: vec![content.into()],
            cursor: 0,
            requests: Vec::new(),
        }
    }

    fn then(mut self, content: impl Into<String>) -> Self {
        self.queue.push(content.into());
        self
    }

    fn next_content(&mut self) -> String {
        let index = self.cursor.min(self.queue.len().saturating_sub(1));
        self.cursor += 1;
        self.queue[index].clone()
    }
}

fn start_stub(state: StubState) -> (u16, Arc<Mutex<StubState>>, Arc<Mutex<usize>>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let state = Arc::new(Mutex::new(state));
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
            let (status, content) = {
                let mut state = shared.lock().unwrap();
                state.requests.push(serde_json::from_slice(&body).unwrap());
                (state.status, state.next_content())
            };
            let payload = json!({"model": MODEL,
                "choices":[{"index":0,"finish_reason":"stop",
                    "message":{"role":"assistant","content":content}}],
                "usage":{"prompt_tokens":5,"completion_tokens":7}})
            .to_string();
            let response = format!(
                "HTTP/1.1 {} synthetic\r\nContent-Type: application/json\r\n\
                 Content-Length: {}\r\nConnection: close\r\n\r\n{}",
                status,
                payload.len(),
                payload
            );
            let _ = stream.write_all(response.as_bytes());
            let _ = stream.flush();
        }
    });
    (port, state, calls)
}

fn outline_content() -> String {
    json!({"languageDirective":"使用简体中文","courseTitle":"交互课","outlines":[
        {"id":"interactive_1","type":"interactive","title":"SYNTHETIC_INTERACTIVE_TITLE",
         "description":"SYNTHETIC_INTERACTIVE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
         "order":1,"widgetType":"diagram",
         "widgetOutline":{"diagramType":"flowchart","nodeCount":4}},
        {"id":"game_1","type":"interactive","title":"SYNTHETIC_GAME_TITLE",
         "description":"SYNTHETIC_GAME_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
         "order":2,"widgetType":"game","widgetOutline":{"gameType":"action",
         "challenge":"SYNTHETIC_GAME_CHALLENGE","playerControls":["SYNTHETIC_THRUST"],
         "physicsConcept":"SYNTHETIC_PHYSICS"}},
        {"id":"code_1","type":"interactive","title":"SYNTHETIC_CODE_TITLE",
         "description":"SYNTHETIC_CODE_DESCRIPTION","keyPoints":["SYNTHETIC_KEY_POINT"],
         "order":3,"widgetType":"code","widgetOutline":{"language":"python",
         "challengeType":"SYNTHETIC_CODE_CHALLENGE"}},
        {"id":"slide_1","type":"slide","title":"SYNTHETIC_SLIDE_TITLE","description":"","keyPoints":[],
         "order":4}]})
    .to_string()
}

fn generate_body(create_request_id: &str) -> Value {
    json!({"create_request_id":create_request_id,
        "requirement":"Synthetic interactive outline requirement",
        "source_text":"SYNTHETIC_SOURCE_MATERIAL","model":null})
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

fn scene_body(outline_document_id: &str, source: &Value) -> Value {
    json!({"create_request_id":"interactive_scene_1",
        "outline_document_id":outline_document_id,"outline_index":0,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},"model":null})
}

#[tokio::test]
async fn interactive_outlines_and_scenes_run_from_one_local_model_lane() {
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
    let (port, stub, calls) = start_stub(
        StubState::new(200, outline_content())
            .then(SCENE_HTML)
            .then(SCENE_HTML)
            .then(SCENE_HTML),
    );
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
    let router = archeaxis_api::runtime::router(executor.clone());

    // A machine actor may not ask for material-bearing generation.
    let (status, denied) = call(
        &router,
        OUTLINE_ROUTE,
        "machine",
        &generate_body("interactive_denied"),
    )
    .await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");
    assert_eq!(*calls.lock().unwrap(), 0);

    let body = generate_body("interactive_outline_1");
    let (status, first) = call(&router, OUTLINE_ROUTE, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{first}");
    {
        let state = stub.lock().unwrap();
        let messages = state.requests[0]["messages"].as_array().unwrap();
        let system = messages[0]["content"].as_str().unwrap();
        let user = messages[1]["content"].as_str().unwrap();
        assert!(system.contains("AAOS output compatibility contract"));
        assert!(system.contains("Never put the widget name in the scene type"));
        assert!(user.contains("Synthetic interactive outline requirement"));
    }
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(first["generation_route"], "local_model_interactive_outline");
    assert_eq!(first["model_call"], "INVOKED");
    assert_eq!(first["outline_count"], 4);
    assert_eq!(first["outlines"][0]["type"], "interactive");
    assert_eq!(first["rendering_authorized"], false);
    assert_eq!(first["active_content_executed"], false);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["model"], MODEL);
    assert_eq!(
        first["model_reply_sha256"],
        format!("{:x}", Sha256::digest(outline_content().as_bytes()))
    );
    assert_eq!(
        first["prompt_binding"]["request_id"],
        "interactive_outline_1"
    );
    let stored = &first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_interactive_outline_generate_candidate"];
    assert_eq!(
        stored["generation_route"],
        "local_model_interactive_outline"
    );
    assert!(
        stored["capture_frame"]
            .as_str()
            .unwrap()
            .contains("SYNTHETIC_SOURCE_MATERIAL")
    );
    assert!(
        stored["replay_frame"]
            .as_str()
            .unwrap()
            .contains("SYNTHETIC_INTERACTIVE_TITLE")
    );
    let outline_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    assert_eq!(*calls.lock().unwrap(), 1);

    // A repeated outline request reads the candidate back without rerunning.
    let (status, duplicate) = call(&router, OUTLINE_ROUTE, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"]["document_id"], outline_id);
    assert_eq!(*calls.lock().unwrap(), 1);

    // The persisted interactive outline drives the existing interactive scene
    // route: widget prompt, model HTML, normalize, scene candidate.
    let scene = scene_body(&outline_id, &source);
    let (status, scene_first) = call(&router, SCENE_ROUTE, "human", &scene).await;
    assert_eq!(status, StatusCode::OK, "{scene_first}");
    assert_eq!(scene_first["scene_route"], "interactive");
    assert_eq!(
        scene_first["generation_route"],
        "outline_interactive_local_model"
    );
    assert_eq!(scene_first["widget_type"], "diagram");
    assert_eq!(scene_first["html_execution"], "NOT_PERFORMED");
    assert_eq!(scene_first["rendering_authorized"], false);
    assert_eq!(scene_first["render"]["report"]["playable"], false);
    let built = &scene_first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_scene_candidate"]
        ["worker_document"]["scene"];
    assert_eq!(built["type"], "interactive");
    assert_eq!(built["content"]["widgetType"], "diagram");
    assert!(
        built["content"]["html"]
            .as_str()
            .unwrap()
            .contains("SYNTHETIC_INTERACTIVE_HTML")
    );
    let scene_id = scene_first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    assert_eq!(
        *calls.lock().unwrap(),
        2,
        "one outline and one scene model call"
    );

    // Exercise the fields that the outline admitted all the way through the
    // real prompt adapter and into the stub model's request, not just the frame.
    let mut extra_scenes = Vec::new();
    for (index, widget, request_id) in [
        (1, "game", "interactive_game_1"),
        (2, "code", "interactive_code_1"),
    ] {
        let mut body = scene_body(&outline_id, &source);
        body["create_request_id"] = json!(request_id);
        body["outline_index"] = json!(index);
        let (status, result) = call(&router, SCENE_ROUTE, "human", &body).await;
        assert_eq!(status, StatusCode::OK, "{result}");
        assert_eq!(result["widget_type"], widget);
        assert_eq!(result["html_execution"], "NOT_PERFORMED");
        assert_eq!(result["rendering_authorized"], false);
        assert_eq!(result["render"]["report"]["playable"], false);
        let scene_id = result["document"]["document_id"]
            .as_str()
            .unwrap()
            .to_owned();
        extra_scenes.push((body, scene_id));
    }
    {
        let state = stub.lock().unwrap();
        let game_prompt = state.requests[2].to_string();
        for detail in [
            "SYNTHETIC_GAME_CHALLENGE",
            "SYNTHETIC_THRUST",
            "SYNTHETIC_PHYSICS",
        ] {
            assert!(game_prompt.contains(detail));
        }
        assert!(
            state.requests[3]
                .to_string()
                .contains("SYNTHETIC_CODE_CHALLENGE")
        );
    }

    // Both retries read the same candidates and rerun nothing.
    let (status, scene_duplicate) = call(&router, SCENE_ROUTE, "human", &scene).await;
    assert_eq!(status, StatusCode::OK, "{scene_duplicate}");
    assert_eq!(scene_duplicate["worker_invoked"], false);
    assert_eq!(scene_duplicate["document"]["document_id"], scene_id);
    assert_eq!(*calls.lock().unwrap(), 4);
    assert_eq!(
        document_count(&executor).await,
        5,
        "outline, source and three scenes"
    );

    // A reply the interactive-outline adapter cannot admit keeps its own status.
    *stub.lock().unwrap() = StubState::new(200, "not an outline document");
    let (status, rejected) = call(
        &router,
        OUTLINE_ROUTE,
        "human",
        &generate_body("interactive_rejected"),
    )
    .await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{rejected}");
    assert_eq!(rejected["stage"], "interactive_outline");
    assert_eq!(rejected["worker_outcome"]["status"], "UNSUPPORTED_OUTPUT");
    // The refusal names the bounded rule it hit, so an operator can act on it
    // without the route ever echoing the model's bytes.
    assert_eq!(
        rejected["worker_outcome"]["differences"][0]["kind"],
        "UPSTREAM_RESULT_SHAPE_UNSUPPORTED"
    );
    assert_eq!(
        rejected["worker_outcome"]["differences"][0]["fields"],
        json!([])
    );
    assert!(
        rejected["worker_outcome"]["transformations"]
            .as_array()
            .is_some(),
        "{rejected}"
    );
    assert_eq!(document_count(&executor).await, 5);

    // Model-generated object keys are content too, even when they look like
    // diagnostic field names. Known contract labels may still be named.
    let mut unusual: Value = serde_json::from_str(&outline_content()).unwrap();
    unusual["outlines"][0]["SYNTHETIC_PRIVATE_FIELD_NAME"] = json!(true);
    unusual["outlines"][3]["widgetType"] = json!("diagram");
    *stub.lock().unwrap() = StubState::new(200, unusual.to_string());
    let (status, rejected_fields) = call(
        &router,
        OUTLINE_ROUTE,
        "human",
        &generate_body("interactive_unrecognized_field"),
    )
    .await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    assert!(
        !rejected_fields
            .to_string()
            .contains("SYNTHETIC_PRIVATE_FIELD_NAME")
    );
    let differences = rejected_fields["worker_outcome"]["differences"]
        .as_array()
        .unwrap();
    assert_eq!(differences[0]["kind"], "UNKNOWN_OUTLINE_FIELDS");
    assert_eq!(differences[0]["fields"], json!(["UNRECOGNIZED_FIELD"]));
    assert_eq!(differences[1]["fields"], json!(["widgetType"]));
    assert_eq!(document_count(&executor).await, 5);

    // An unavailable model lane is a named service error, never fabricating text.
    *stub.lock().unwrap() = StubState::new(500, String::new());
    let (status, unavailable) = call(
        &router,
        OUTLINE_ROUTE,
        "human",
        &generate_body("interactive_unavailable"),
    )
    .await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{unavailable}");
    assert_eq!(unavailable["stage"], "local_model");

    drop(router);
    drop(executor);
    // Reopening with no Node still reads both candidates, no rerun.
    let reopened = Executor::open(&path, &dir.path().join("staging"), &python, &text_worker())
        .await
        .unwrap();
    assert_eq!(reopened.openmaic_interactive_outline_script(), None);
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, read_back) = call(&router, OUTLINE_ROUTE, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{read_back}");
    assert_eq!(read_back["worker_invoked"], false);
    assert_eq!(read_back["document"]["document_id"], outline_id);
    let (status, scene_read_back) = call(&router, SCENE_ROUTE, "human", &scene).await;
    assert_eq!(status, StatusCode::OK, "{scene_read_back}");
    assert_eq!(scene_read_back["worker_invoked"], false);
    assert_eq!(scene_read_back["document"]["document_id"], scene_id);
    for (body, scene_id) in extra_scenes {
        let (status, read_back) = call(&router, SCENE_ROUTE, "human", &body).await;
        assert_eq!(status, StatusCode::OK, "{read_back}");
        assert_eq!(read_back["worker_invoked"], false);
        assert_eq!(read_back["document"]["document_id"], scene_id);
    }
    assert_eq!(
        *calls.lock().unwrap(),
        7,
        "one outline, three scenes, two rejected and one failed probe"
    );
}
