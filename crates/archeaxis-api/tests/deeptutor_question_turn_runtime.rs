//! In-process Runtime router for the DeepTutor single-question candidate route.
//! The gated test runs the pinned Python donor worker and a synthetic loopback
//! model stub; no real model, cloud provider or user material is used.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{document, provider_material_grant::Snapshot};
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

const ROUTE: &str = "/api/v1/learning/deeptutor/question-turn";
const IMPORT_CAPABILITY: &str = "deeptutor.practice.import";
const MODEL_CAPABILITY: &str = "course.openmaic.outline-model";
const MODEL: &str = "synthetic-stub-model";

struct StubState {
    status: u16,
    content: String,
}

/// One synthetic loopback model lane. Every request is counted, so a retry that
/// silently re-ran the model is observable.
fn start_stub(
    content: String,
) -> (
    u16,
    Arc<Mutex<StubState>>,
    Arc<Mutex<usize>>,
    Arc<Mutex<Vec<Value>>>,
) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let state = Arc::new(Mutex::new(StubState {
        status: 200,
        content,
    }));
    let calls = Arc::new(Mutex::new(0_usize));
    let shared = state.clone();
    let counted = calls.clone();
    let requests = Arc::new(Mutex::new(Vec::new()));
    let observed = requests.clone();
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
            observed
                .lock()
                .unwrap()
                .push(serde_json::from_slice(&body).unwrap());
            *counted.lock().unwrap() += 1;
            let state = shared.lock().unwrap();
            let payload = if state.status == 400 {
                state.content.clone()
            } else {
                json!({"model": MODEL,
                    "choices":[{"index":0,"finish_reason":"stop",
                        "message":{"role":"assistant","content":state.content}}],
                    "usage":{"prompt_tokens":5,"completion_tokens":7}})
                .to_string()
            };
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
    (port, state, calls, requests)
}

/// The model's final text, which the donor replay step validates strictly.
fn model_content() -> String {
    json!({"question_type":"choice","question":"What is the synthetic sum?",
        "options":{"A":"3","B":"4","C":"5","D":"6"},
        "correct_answer":"B","explanation":"Synthetic explanation."})
    .to_string()
}

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn repository() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

/// Select an interpreter without any request input. A test that cannot find one
/// skips and says so; a skip is not evidence.
fn repository_python() -> Option<PathBuf> {
    [
        std::env::var_os("ARCHEAXIS_PYTHON").map(PathBuf::from),
        Some(repository().join(".venv/Scripts/python.exe")),
        Some(repository().join(".project-local/build/venv/Scripts/python.exe")),
    ]
    .into_iter()
    .flatten()
    .find(|path| path.is_file())
}

fn python_route(relative: &str) -> PathBuf {
    repository().join(relative).canonicalize().unwrap()
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

fn request_body(material: &Value, create_request_id: &str) -> Value {
    json!({"create_request_id":create_request_id,"material":snap(material),
        "requirement":"Synthetic arithmetic requirement","model":null})
}

#[tokio::test]
async fn a_local_model_produces_one_candidate_and_every_failure_stays_named() {
    let Some(python) = repository_python() else {
        eprintln!("skipping: no usable Python interpreter; this skip is not evidence");
        return;
    };
    let practice_worker =
        python_route("services/learning-providers/deeptutor/practice_host_worker.py");
    let model_worker = python_route("services/python-workers/course/worker_outline_local_model.py");
    let text_worker = python_route("services/python-workers/transport/text_ndjson.py");
    let (port, stub, calls, requests) = start_stub(model_content());
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
    let (material, _) = {
        let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
        let material = document::create_optional(
            &mut conn,
            None,
            None,
            "Synthetic material",
            json!({"type":"doc","content":[{"type":"paragraph",
                "content":[{"type":"text","text":"SYNTHETIC_MATERIAL_TEXT about arithmetic"}]}]}),
        )
        .unwrap();
        document::create_optional(&mut conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{
            "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
                "purpose":"practice","consumer":"deeptutor","operations":["practice"],
                "material":snap(&material),
                "authorization_basis":"SYNTHETIC explicit human authorization",
                "expires_at":null,"state":"granted"}
        }})).unwrap();
        (material, ())
    };
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[
            (IMPORT_CAPABILITY, practice_worker.clone()),
            (MODEL_CAPABILITY, model_worker.clone()),
        ],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());

    // A machine actor may not ask for material-bearing generation.
    let (status, denied) = call(&router, "machine", &request_body(&material, "turn_denied")).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");
    assert_eq!(document_count(&executor).await, 2);

    let body = request_body(&material, "turn_1");
    let (status, first) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::CREATED, "{first}");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(
        first["generation_route"],
        "deeptutor_question_turn_local_model"
    );
    assert_eq!(first["model_call"], "INVOKED");
    assert_eq!(first["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(first["rendering_authorized"], false);
    assert_eq!(first["active_content_executed"], false);
    assert_eq!(first["answer_secrecy"], "not_established");
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["question"]["question"], "What is the synthetic sum?");
    assert_eq!(
        first["question"]["options"],
        json!({"A":"3","B":"4","C":"5","D":"6"})
    );
    assert_eq!(first["model"], MODEL);
    assert!(first["capture_binding"]["prompt_sha256"].as_str().is_some());
    assert_eq!(first["capture_binding"]["request_id"], "turn_1");
    let sent = requests.lock().unwrap()[0].clone();
    let system = sent["messages"][0]["content"].as_str().unwrap();
    assert_eq!(system, first["model_prompt_binding"]["system"]);
    assert_eq!(
        format!("{:x}", Sha256::digest(system.as_bytes())),
        first["model_prompt_binding"]["system_sha256"]
    );
    assert!(
        first["capture_binding"]["system"]
            .as_str()
            .unwrap()
            .contains("# Output protocol (mandatory")
    );
    assert!(!system.contains("# Output protocol (mandatory"));
    assert!(system.contains("# FINISH JSON schema (strict)"));
    assert_eq!(
        sent["messages"][1]["content"],
        first["capture_binding"]["user"]
    );
    assert_eq!(first["material"], json!(snap(&material)));
    let stored =
        &first["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question_turn_candidate"];
    assert_eq!(
        stored["generation_route"],
        "deeptutor_question_turn_local_model"
    );
    assert_eq!(stored["model_call"], "INVOKED");
    assert_eq!(stored["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(stored["human_review_required"], true);
    assert_eq!(stored["active_content_executed"], false);
    assert_eq!(stored["rendering_authorized"], false);
    assert_eq!(stored["answer_secrecy"], "not_established");
    assert_eq!(stored["material"], json!(snap(&material)));
    let replay = stored["replay_frame"].as_str().unwrap();
    assert!(replay.contains("SYNTHETIC_MATERIAL_TEXT"));
    assert!(replay.contains("What is the synthetic sum?"));
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
    assert_eq!(duplicate["document"], first["document"]);
    assert_eq!(duplicate["document"]["document_id"], candidate_id);
    assert_eq!(*calls.lock().unwrap(), 1, "a retry never re-runs the model");
    assert_eq!(document_count(&executor).await, 3);

    // The same create ID cannot describe different content.
    let mut other = body.clone();
    other["requirement"] = json!("A different synthetic requirement");
    let (status, conflict) = call(&router, "human", &other).await;
    assert_eq!(status, StatusCode::CONFLICT, "{conflict}");
    assert_eq!(document_count(&executor).await, 3);

    // An unreachable/unhealthy lane is a named unavailability.
    *stub.lock().unwrap() = StubState {
        status: 500,
        content: String::new(),
    };
    let (status, unavailable) = call(
        &router,
        "human",
        &request_body(&material, "turn_unavailable"),
    )
    .await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{unavailable}");
    assert_eq!(unavailable["stage"], "local_model");
    assert_eq!(unavailable["worker_outcome"]["status"], "MODEL_UNAVAILABLE");
    assert_eq!(
        unavailable["worker_outcome"]["reason"],
        "MODEL_ENDPOINT_UNHEALTHY"
    );
    assert_eq!(
        unavailable["worker_outcome"]["model_observation"]["http_status"],
        500
    );
    assert_eq!(
        unavailable["worker_outcome"]["model_observation"]["network_performed"],
        true
    );
    assert_eq!(document_count(&executor).await, 3);

    // An empty model body is a named no-final-answer.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: "   ".into(),
    };
    let (status, empty) = call(&router, "human", &request_body(&material, "turn_empty")).await;
    assert_eq!(status, StatusCode::GATEWAY_TIMEOUT, "{empty}");
    assert_eq!(empty["stage"], "local_model");
    assert_eq!(empty["worker_outcome"]["status"], "NO_FINAL_ANSWER");
    assert_eq!(empty["worker_outcome"]["reason"], "EMPTY_CONTENT");
    assert_eq!(document_count(&executor).await, 3);

    // Capacity details are numbers supplied by the provider. Its body may
    // quote private prompt text, which must never appear in the route reply.
    *stub.lock().unwrap() = StubState {
        status: 400,
        content: json!({"error":{"message":"SYNTHETIC_PRIVATE_BODY",
            "n_prompt_tokens":9496,"n_ctx":8192}})
        .to_string(),
    };
    let (status, capacity) =
        call(&router, "human", &request_body(&material, "turn_capacity")).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{capacity}");
    assert_eq!(capacity["worker_outcome"]["reason"], "MODEL_HTTP_REJECTED");
    assert_eq!(
        capacity["worker_outcome"]["model_observation"]["http_status"],
        400
    );
    assert_eq!(
        capacity["worker_outcome"]["model_observation"]["provider_prompt_tokens"],
        9496
    );
    assert_eq!(
        capacity["worker_outcome"]["model_observation"]["provider_context_tokens"],
        8192
    );
    assert!(!capacity.to_string().contains("SYNTHETIC_PRIVATE_BODY"));
    assert_eq!(document_count(&executor).await, 3);

    // A reply the replay stage cannot admit keeps the worker's own status.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: "not a question document".into(),
    };
    let (status, rejected) =
        call(&router, "human", &request_body(&material, "turn_rejected")).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{rejected}");
    assert_eq!(rejected["stage"], "replay");
    assert_eq!(rejected["worker_outcome"]["status"], "REJECTED");
    assert_eq!(rejected["worker_outcome"]["reason"], "INVALID_RESPONSE");
    assert_eq!(
        rejected["worker_outcome"]["response_format"],
        "PLAIN_JSON_PARSE_FAILED"
    );
    assert!(!rejected.to_string().contains("not a question document"));
    assert_eq!(document_count(&executor).await, 3);
    drop(router);
    drop(executor);

    // Reopening with no model route still reads the stored candidate.
    let reopened = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[(IMPORT_CAPABILITY, practice_worker.clone())],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, read_back) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{read_back}");
    assert_eq!(read_back["worker_invoked"], false);
    assert_eq!(read_back["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&reopened).await, 3);
    drop(router);
    drop(reopened);

    // A runtime without the private DeepTutor worker refuses with a reason that
    // names the missing capability, and writes nothing.
    let unregistered = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[(MODEL_CAPABILITY, model_worker)],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(unregistered.clone());
    let (status, missing) =
        call(&router, "human", &request_body(&material, "turn_no_worker")).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{missing}");
    assert_eq!(missing["reason"], "question_turn_worker_unavailable");
    assert_eq!(document_count(&unregistered).await, 3);
}
