//! In-process Runtime router for OpenMAIC local-model outline generation.
//! The gated test runs the pinned local Node outline worker and a synthetic
//! loopback model stub; no real model, cloud provider or user material is used.
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
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpListener,
    path::PathBuf,
    sync::{Arc, Mutex},
    thread,
};
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/courses/openmaic/outlines/generate";
const CAPABILITY: &str = "course.openmaic.outline-model";
const MODEL: &str = "synthetic-stub-model";

struct StubState {
    status: u16,
    content: String,
    truncated_chunk: bool,
    finish_reason: &'static str,
}

/// One synthetic loopback model lane. Every request is counted, so a retry that
/// silently re-ran the model is observable.
fn start_stub(content: String) -> (u16, Arc<Mutex<StubState>>, Arc<Mutex<usize>>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let state = Arc::new(Mutex::new(StubState {
        status: 200,
        content,
        truncated_chunk: false,
        finish_reason: "stop",
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
            if state.truncated_chunk {
                let response = format!(
                    "HTTP/1.1 {} synthetic\r\nTransfer-Encoding: chunked\r\n\
                     Connection: close\r\n\r\n20\r\n{{\"private\":\"SYNTHETIC_PRIVATE\"",
                    state.status
                );
                let _ = stream.write_all(response.as_bytes());
                let _ = stream.flush();
                continue;
            }
            let payload = if state.status == 400 {
                state.content.clone()
            } else {
                json!({"model": MODEL,
                    "choices":[{"index":0,"finish_reason":state.finish_reason,
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
    (port, state, calls)
}

fn model_content(title: &str) -> String {
    json!({"languageDirective":"Respond in Simplified Chinese.",
        "courseTitle":"Synthetic course",
        "outlines":[{"id":"synthetic_outline_1","type":"slide","title":title,
            "description":"SYNTHETIC_GENERATED_DESCRIPTION",
            "keyPoints":["SYNTHETIC_KEY_POINT"],"order":1}]})
    .to_string()
}

fn generate_body(create_request_id: &str) -> Value {
    json!({"create_request_id":create_request_id,
        "requirement":"Synthetic outline requirement",
        "source_text":"SYNTHETIC_SOURCE_MATERIAL","model":null})
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

#[tokio::test]
async fn a_local_model_generates_a_candidate_and_every_failure_stays_named() {
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
    let (port, stub, calls) = start_stub(model_content("SYNTHETIC_GENERATED_TITLE"));
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

    // A machine actor may not ask for material-bearing generation.
    let (status, denied) = call(&router, "machine", &generate_body("generate_denied")).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");
    assert_eq!(document_count(&executor).await, 0);

    let body = generate_body("generate_1");
    let (status, first) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{first}");
    let content = model_content("SYNTHETIC_GENERATED_TITLE");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(first["generation_route"], "local_model");
    assert_eq!(first["model_call"], "INVOKED");
    assert_eq!(first["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(first["rendering_authorized"], false);
    assert_eq!(first["active_content_executed"], false);
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["outline_count"], 1);
    assert_eq!(first["outlines"][0]["title"], "SYNTHETIC_GENERATED_TITLE");
    assert_eq!(first["model"], MODEL);
    assert_eq!(
        first["model_reply_sha256"],
        format!("{:x}", Sha256::digest(content.as_bytes()))
    );
    assert_eq!(first["prompt_binding"]["request_id"], "generate_1");
    assert!(first["prompt_binding"]["system_sha256"].as_str().is_some());
    assert!(first["prompt_binding"]["input_sha256"].as_str().is_some());
    let stored =
        &first["document"]["editor_json"]["attrs"]["archeaxis_openmaic_outline_generate_candidate"];
    assert_eq!(stored["generation_route"], "local_model");
    assert_eq!(stored["model_call"], "INVOKED");
    assert_eq!(stored["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(stored["human_review_required"], true);
    assert_eq!(stored["active_content_executed"], false);
    assert_eq!(stored["rendering_authorized"], false);
    assert_eq!(stored["prompt_binding"], first["prompt_binding"]);
    // The exact replay frame carries the model text and the captured binding.
    let replay = stored["replay_frame"].as_str().unwrap();
    assert!(replay.contains("SYNTHETIC_SOURCE_MATERIAL"));
    assert!(replay.contains("SYNTHETIC_GENERATED_TITLE"));
    let candidate_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    assert_eq!(*calls.lock().unwrap(), 1, "one model call");

    // A repeated request reads the candidate back without rerunning anything.
    let (status, duplicate) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"], first["document"]);
    assert_eq!(duplicate["document"]["document_id"], candidate_id);
    assert_eq!(*calls.lock().unwrap(), 1, "a retry never re-runs the model");
    assert_eq!(document_count(&executor).await, 1);

    // An empty model body is a named no-final-answer, never fabricated text.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: "   ".into(),
        truncated_chunk: false,
        finish_reason: "stop",
    };
    let (status, empty) = call(&router, "human", &generate_body("generate_empty")).await;
    assert_eq!(status, StatusCode::GATEWAY_TIMEOUT, "{empty}");
    assert_eq!(empty["stage"], "local_model");
    assert_eq!(empty["worker_outcome"]["status"], "NO_FINAL_ANSWER");
    assert_eq!(empty["worker_outcome"]["reason"], "EMPTY_CONTENT");
    assert_eq!(document_count(&executor).await, 1, "no partial candidate");

    // An unreachable/unhealthy lane is a named unavailability.
    *stub.lock().unwrap() = StubState {
        status: 500,
        content: String::new(),
        truncated_chunk: false,
        finish_reason: "stop",
    };
    let (status, unavailable) =
        call(&router, "human", &generate_body("generate_unavailable")).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{unavailable}");
    assert_eq!(unavailable["stage"], "local_model");
    assert_eq!(unavailable["worker_outcome"]["status"], "MODEL_UNAVAILABLE");
    assert_eq!(
        unavailable["worker_outcome"]["model_observation"]["http_status"],
        500
    );
    assert_eq!(document_count(&executor).await, 1);

    *stub.lock().unwrap() = StubState {
        status: 400,
        content: json!({"error":{"message":"SYNTHETIC_PRIVATE_BODY",
            "n_prompt_tokens":9496,"n_ctx":8192}})
        .to_string(),
        truncated_chunk: false,
        finish_reason: "stop",
    };
    let (status, capacity) = call(&router, "human", &generate_body("generate_capacity")).await;
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
    assert_eq!(document_count(&executor).await, 1);

    // Even syntactically valid outline JSON is not a complete model reply
    // when the provider says it stopped at its output limit.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: model_content("SYNTHETIC_UNFINISHED_TITLE"),
        truncated_chunk: false,
        finish_reason: "length",
    };
    let before = *calls.lock().unwrap();
    let (status, unfinished) = call(&router, "human", &generate_body("generate_unfinished")).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{unfinished}");
    assert_eq!(unfinished["stage"], "local_model");
    assert_eq!(
        unfinished["worker_outcome"]["status"],
        "INVALID_MODEL_OUTPUT"
    );
    assert_eq!(unfinished["worker_outcome"]["reason"], "MODEL_NONSTOP");
    assert!(
        !unfinished
            .to_string()
            .contains("SYNTHETIC_UNFINISHED_TITLE")
    );
    assert_eq!(*calls.lock().unwrap(), before + 1, "no model retry");
    assert_eq!(document_count(&executor).await, 1, "no partial candidate");

    // An interrupted HTTP body is named at the real Core/worker boundary;
    // neither its private fragment nor a partial candidate may be exposed.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: String::new(),
        truncated_chunk: true,
        finish_reason: "stop",
    };
    let before = *calls.lock().unwrap();
    let (status, truncated) = call(&router, "human", &generate_body("generate_truncated")).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{truncated}");
    assert_eq!(truncated["stage"], "local_model");
    assert_eq!(
        truncated["worker_outcome"]["status"],
        "INVALID_MODEL_OUTPUT"
    );
    assert_eq!(
        truncated["worker_outcome"]["reason"],
        "MODEL_RESPONSE_INVALID"
    );
    assert!(!truncated.to_string().contains("SYNTHETIC_PRIVATE"));
    assert_eq!(*calls.lock().unwrap(), before + 1, "no model retry");
    assert_eq!(document_count(&executor).await, 1, "no partial candidate");

    // The same interruption on a 4xx response retains the known rejection.
    stub.lock().unwrap().status = 400;
    let before = *calls.lock().unwrap();
    let (status, truncated_rejection) = call(
        &router,
        "human",
        &generate_body("generate_truncated_rejection"),
    )
    .await;
    assert_eq!(
        status,
        StatusCode::UNPROCESSABLE_ENTITY,
        "{truncated_rejection}"
    );
    assert_eq!(truncated_rejection["stage"], "local_model");
    assert_eq!(
        truncated_rejection["worker_outcome"]["status"],
        "MODEL_REJECTED"
    );
    assert_eq!(
        truncated_rejection["worker_outcome"]["reason"],
        "MODEL_HTTP_REJECTED"
    );
    assert!(
        !truncated_rejection
            .to_string()
            .contains("SYNTHETIC_PRIVATE")
    );
    assert_eq!(*calls.lock().unwrap(), before + 1, "no model retry");
    assert_eq!(document_count(&executor).await, 1, "no partial candidate");

    // A reply the replay stage cannot admit keeps the worker's own status.
    *stub.lock().unwrap() = StubState {
        status: 200,
        content: "not an outline document".into(),
        truncated_chunk: false,
        finish_reason: "stop",
    };
    let (status, rejected) = call(&router, "human", &generate_body("generate_non_candidate")).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{rejected}");
    assert_eq!(rejected["stage"], "replay");
    assert!(
        [
            "UPSTREAM_FAILURE",
            "UPSTREAM_RECOVERY_NOT_ADMITTED",
            "UPSTREAM_RESULT_NOT_ADMITTED"
        ]
        .contains(&rejected["worker_outcome"]["status"].as_str().unwrap_or("")),
        "{rejected}"
    );
    assert_eq!(document_count(&executor).await, 1);
    drop(router);
    drop(executor);

    // A runtime that configured Node but not the local-model route refuses with
    // a reason that names the missing capability.
    let unregistered = Executor::open(&path, &dir.path().join("staging"), &python, &text_worker())
        .await
        .unwrap()
        .with_openmaic_node(&node, &expected_sha, &outline_script())
        .unwrap();
    let router = archeaxis_api::runtime::router(unregistered.clone());
    let (status, missing) = call(&router, "human", &generate_body("generate_no_model_route")).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{missing}");
    assert_eq!(missing["stage"], "local_model");
    assert!(
        missing["message"]
            .as_str()
            .unwrap()
            .contains("derived worker is not registered"),
        "{missing}"
    );
    assert_eq!(document_count(&unregistered).await, 1);
    drop(router);
    drop(unregistered);

    // Reopening with no Node still reads the stored candidate, no rerun.
    let reopened = Executor::open(&path, &dir.path().join("staging"), &python, &text_worker())
        .await
        .unwrap();
    assert_eq!(reopened.openmaic_outline_script(), None);
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, read_back) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{read_back}");
    assert_eq!(read_back["worker_invoked"], false);
    assert_eq!(read_back["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&reopened).await, 1);
}
