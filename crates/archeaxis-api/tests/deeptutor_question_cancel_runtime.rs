//! Explicit user cancellation: pinned donor/model transport workers, held synthetic loopback.
//! The fixture observes transport disconnect; it does not claim a real model provider stopped.
use archeaxis_application::executor::Executor;
use archeaxis_domain::document;
use axum::{
    Router,
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Read},
    net::TcpListener,
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    thread,
    time::{Duration, Instant},
};
use tower::ServiceExt;

struct HeldProvider {
    port: u16,
    entered: Arc<AtomicBool>,
    disconnected: Arc<AtomicBool>,
    stop: Arc<AtomicBool>,
    owner: Option<thread::JoinHandle<()>>,
}
impl HeldProvider {
    fn new() -> Self {
        let listener = TcpListener::bind(("127.0.0.1", 0)).unwrap();
        listener.set_nonblocking(true).unwrap();
        let port = listener.local_addr().unwrap().port();
        let entered = Arc::new(AtomicBool::new(false));
        let disconnected = Arc::new(AtomicBool::new(false));
        let stop = Arc::new(AtomicBool::new(false));
        let (seen, closed, ending) = (entered.clone(), disconnected.clone(), stop.clone());
        let owner = thread::spawn(move || {
            let until = Instant::now() + Duration::from_secs(30);
            let socket = loop {
                if ending.load(Ordering::SeqCst) || Instant::now() >= until {
                    return;
                }
                match listener.accept() {
                    Ok((socket, _)) => break socket,
                    Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                        thread::sleep(Duration::from_millis(5))
                    }
                    Err(error) => panic!("owned synthetic listener: {error}"),
                }
            };
            socket.set_nonblocking(false).unwrap();
            socket
                .set_read_timeout(Some(Duration::from_secs(5)))
                .unwrap();
            let mut reader = BufReader::new(socket.try_clone().unwrap());
            let mut length = 0usize;
            loop {
                let mut line = String::new();
                if reader.read_line(&mut line).unwrap_or(0) == 0 {
                    return;
                }
                if line.trim().is_empty() {
                    break;
                }
                if let Some(value) = line.to_ascii_lowercase().strip_prefix("content-length:") {
                    length = value.trim().parse::<usize>().unwrap().min(1 << 20);
                }
            }
            let mut body = vec![0u8; length];
            reader.read_exact(&mut body).unwrap();
            drop(reader);
            seen.store(true, Ordering::SeqCst);
            socket.set_nonblocking(true).unwrap();
            while !ending.load(Ordering::SeqCst) && Instant::now() < until {
                match socket.peek(&mut [0u8; 1]) {
                    Ok(0) => {
                        closed.store(true, Ordering::SeqCst);
                        break;
                    }
                    Err(error)
                        if matches!(
                            error.kind(),
                            std::io::ErrorKind::ConnectionReset
                                | std::io::ErrorKind::ConnectionAborted
                        ) =>
                    {
                        closed.store(true, Ordering::SeqCst);
                        break;
                    }
                    Err(error) if error.kind() != std::io::ErrorKind::WouldBlock => {
                        panic!("owned synthetic socket: {error}")
                    }
                    _ => thread::sleep(Duration::from_millis(5)),
                }
            }
            // The fixture stays alive after transport disconnect, like a shared provider.
            while !ending.load(Ordering::SeqCst) && Instant::now() < until {
                thread::sleep(Duration::from_millis(5));
            }
        });
        Self {
            port,
            entered,
            disconnected,
            stop,
            owner: Some(owner),
        }
    }
}
impl Drop for HeldProvider {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::SeqCst);
        if let Some(owner) = self.owner.take() {
            owner.join().unwrap();
        }
    }
}
async fn observed(flag: &AtomicBool, seconds: u64) {
    tokio::time::timeout(Duration::from_secs(seconds), async {
        while !flag.load(Ordering::SeqCst) {
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .expect("new owned transport observation was not established");
}
async fn call(router: Router, path: &str, body: Value) -> (StatusCode, Value) {
    call_as(router, path, body, "human").await
}
async fn call_as(router: Router, path: &str, body: Value, actor: &str) -> (StatusCode, Value) {
    let response = router
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(path)
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

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn explicit_cancel_runtime_closes_only_matching_request_without_stopping_provider() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_owned();
    let python = std::env::var_os("ARCHEAXIS_PYTHON")
        .map(PathBuf::from)
        .unwrap_or_else(|| root.join(".venv/Scripts/python.exe"));
    assert!(
        python.is_file(),
        "pinned existing Python required; absence is not a pass"
    );
    let provider = HeldProvider::new();
    // This binary's only model-invoking test uses an owned synthetic endpoint;
    // the other test configures no interpreter or worker. No shared service changes.
    unsafe {
        std::env::set_var(
            "ARCHEAXIS_MACHINE_ENDPOINT",
            format!("http://127.0.0.1:{}/v1", provider.port),
        );
        std::env::set_var("ARCHEAXIS_MACHINE_MODEL", "synthetic-cancel-model");
        std::env::set_var("ARCHEAXIS_MACHINE_PROTOCOL", "openai");
    }
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let material=document::create_optional(&mut conn,None,None,"Synthetic cancellation material",
        json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic arithmetic only"}]}]})).unwrap();
    let snapshot = json!({"document_id":material["document_id"],"version":material["version"],"content_sha256":material["content_sha256"]});
    document::create_optional(&mut conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snapshot,"authorization_basis":"Synthetic explicit choice","expires_at":null,"state":"granted"}}})).unwrap();
    drop(conn);
    let executor = Executor::open_routes(
        &db,
        &dir.path().join("staging"),
        &python,
        &root.join("services/python-workers/transport/text_ndjson.py"),
        &[
            (
                "deeptutor.practice.import",
                root.join("services/learning-providers/deeptutor/practice_host_worker.py"),
            ),
            (
                "course.openmaic.outline-model",
                root.join("services/python-workers/course/worker_outline_local_model.py"),
            ),
        ],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"create_request_id":"synthetic_explicit_cancel","material":snapshot,"requirement":"Synthetic arithmetic question","model":null});
    let running = tokio::spawn(call(
        router.clone(),
        "/api/v1/learning/deeptutor/question-turn",
        body.clone(),
    ));
    observed(&provider.entered, 25).await;
    let route = "/api/v1/learning/deeptutor/question-turn/cancel";
    let mut other = body.clone();
    other["create_request_id"] = json!("another_request");
    let absent = call(router.clone(), route, other).await;
    assert_eq!(absent.0, StatusCode::OK);
    assert_eq!(absent.1["state"], "NOT_FOUND");
    assert_eq!(absent.1["cancel_requested"], false);
    let mut conflict = body.clone();
    conflict["requirement"] = json!("changed request");
    let rejected = call(router.clone(), route, conflict).await;
    assert_eq!(rejected.0, StatusCode::CONFLICT);
    assert_eq!(rejected.1["reason"], "question_turn_request_id_conflict");
    assert!(!provider.disconnected.load(Ordering::SeqCst));
    assert!(!running.is_finished());
    let cancelled = tokio::time::timeout(
        Duration::from_secs(3),
        call(router.clone(), route, body.clone()),
    )
    .await
    .unwrap();
    assert_eq!(cancelled.0, StatusCode::OK);
    assert_eq!(cancelled.1["state"], "UNKNOWN");
    assert_eq!(cancelled.1["cancel_requested"], true);
    assert_eq!(cancelled.1["provider_stop_state"], "UNKNOWN");
    assert_eq!(cancelled.1.as_object().unwrap().len(), 9);
    observed(&provider.disconnected, 5).await;
    let original = tokio::time::timeout(Duration::from_secs(5), running)
        .await
        .unwrap()
        .unwrap();
    assert!(!original.0.is_success());
    assert_eq!(original.1["retryable"], false);
    assert!(
        !provider.owner.as_ref().unwrap().is_finished(),
        "cancellation must leave the provider fixture alive"
    );
    let (status, value) = call(
        router.clone(),
        "/api/v1/learning/deeptutor/question-turn/status",
        body.clone(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["state"], "UNKNOWN");
    assert!(value["result_document_id"].is_null());
    assert_eq!(
        value["current_invocation"],
        json!({"worker_invoked":false,"model_invoked":false})
    );
    let repeated_cancel = call(router.clone(), route, body.clone()).await;
    assert_eq!(repeated_cancel.0, StatusCode::OK);
    assert_eq!(repeated_cancel.1, cancelled.1);
    let repeated = call(router, "/api/v1/learning/deeptutor/question-turn", body).await;
    assert_eq!(repeated.0, StatusCode::CONFLICT);
    assert_eq!(repeated.1["retryable"], false);
    let id = archeaxis_domain::provider_question_turn::question_turn_document_id(
        "synthetic_explicit_cancel",
    );
    let saved = executor
        .store()
        .submit_wait(move |conn| document::read(conn, &id, None).is_ok())
        .await
        .unwrap();
    assert!(
        !saved,
        "cancelled inference must not publish a late candidate"
    );
}

#[tokio::test]
async fn explicit_cancel_runtime_is_bounded_human_only_and_closes_registration_gap() {
    use archeaxis_domain::provider_question_turn::{
        self as turn, QuestionTurnPreparation, QuestionTurnRequest,
    };
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("gap.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let material=document::create_optional(&mut conn,None,None,"Synthetic gap material",
        json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic arithmetic only"}]}]})).unwrap();
    let snapshot = json!({"document_id":material["document_id"],"version":material["version"],"content_sha256":material["content_sha256"]});
    document::create_optional(&mut conn,None,None,"Synthetic gap grant",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snapshot,"authorization_basis":"Synthetic explicit choice","expires_at":null,"state":"granted"}}})).unwrap();
    drop(conn);
    let executor = Executor::open_routes(
        &db,
        &dir.path().join("staging"),
        &dir.path().join("no-python"),
        &dir.path().join("no-worker"),
        &[],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"create_request_id":"synthetic_gap_cancel","material":snapshot,"requirement":"Synthetic gap question","model":null});
    let route = "/api/v1/learning/deeptutor/question-turn/cancel";
    assert_eq!(
        call_as(router.clone(), route, body.clone(), "machine")
            .await
            .0,
        StatusCode::FORBIDDEN
    );
    let missing = call(router.clone(), route, body.clone()).await;
    assert_eq!(missing.0, StatusCode::OK);
    assert_eq!(missing.1["state"], "NOT_FOUND");
    assert_eq!(missing.1["cancel_requested"], false);
    let mut large = body.clone();
    large["requirement"] = json!("x".repeat(65_536));
    assert_eq!(
        call(router.clone(), route, large).await.0,
        StatusCode::PAYLOAD_TOO_LARGE
    );
    // Prepare through the real writer, but deliberately leave the ephemeral
    // registry empty, modelling the handoff gap or a restarted process.
    let parsed: QuestionTurnRequest = serde_json::from_value(body.clone()).unwrap();
    let prepared = executor
        .store()
        .submit_wait(move |conn| turn::prepare_question_turn(conn, &parsed))
        .await
        .unwrap()
        .unwrap();
    let QuestionTurnPreparation::Pending(pending) = prepared else {
        panic!("fresh claim expected")
    };
    let cancelled = call(router.clone(), route, body.clone()).await;
    assert_eq!(cancelled.0, StatusCode::OK);
    assert_eq!(cancelled.1["state"], "UNKNOWN");
    assert_eq!(cancelled.1["cancel_requested"], true);
    assert_eq!(
        cancelled.1["current_invocation"],
        json!({"worker_invoked":false,"model_invoked":false})
    );
    assert!(
        executor
            .store()
            .submit_wait(move |conn| turn::assert_question_turn_dispatch(conn, &pending))
            .await
            .unwrap()
            .is_err()
    );
    let retry = call(
        router.clone(),
        "/api/v1/learning/deeptutor/question-turn",
        body.clone(),
    )
    .await;
    assert_eq!(retry.0, StatusCode::CONFLICT);
    assert_eq!(retry.1["retryable"], false);
    executor.store().submit_wait(|conn|conn.execute("UPDATE workspace_meta SET value='bad-json' WHERE key LIKE 'deeptutor_question_turn_claim_%'",[])).await.unwrap().unwrap();
    let corrupt = call(router, route, body).await;
    assert_eq!(corrupt.0, StatusCode::CONFLICT);
    assert_eq!(
        corrupt.1["reason"],
        "question_turn_execution_outcome_unresolved"
    );
}
