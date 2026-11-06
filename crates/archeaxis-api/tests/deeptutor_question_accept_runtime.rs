//! In-process Runtime router for human acceptance of a generated question. The
//! gated test runs the pinned Python question-turn worker and a synthetic
//! loopback lane, then proves the accepted Document is a graded question the
//! formal grading route accepts. No user material or real model is used.
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
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpListener,
    path::PathBuf,
    sync::{Arc, Mutex},
    thread,
};
use tower::ServiceExt;

const TURN_ROUTE: &str = "/api/v1/learning/deeptutor/question-turn";
const ACCEPT_ROUTE: &str = "/api/v1/learning/deeptutor/question-candidates/accept";
const GRADE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade";
const ACTIVITIES: &str = "/api/v1/learning/provider-activities";
const IMPORT_CAPABILITY: &str = "deeptutor.practice.import";
const MODEL_CAPABILITY: &str = "course.openmaic.outline-model";
const MODEL: &str = "synthetic-accept-model";

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

fn start_stub(content: String) -> (u16, Arc<Mutex<usize>>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let calls = Arc::new(Mutex::new(0_usize));
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
            let payload = json!({"model":MODEL,
                "choices":[{"index":0,"finish_reason":"stop",
                    "message":{"role":"assistant","content":content}}],
                "usage":{"prompt_tokens":5,"completion_tokens":7}})
            .to_string();
            let response = format!(
                "HTTP/1.1 200 synthetic\r\nContent-Type: application/json\r\n\
                 Content-Length: {}\r\nConnection: close\r\n\r\n{}",
                payload.len(),
                payload
            );
            let _ = stream.write_all(response.as_bytes());
            let _ = stream.flush();
        }
    });
    (port, calls)
}

fn model_content() -> String {
    json!({"question_type":"choice","question":"What is the synthetic sum?",
        "options":{"A":"3","B":"4","C":"5","D":"6"},
        "correct_answer":"D","explanation":"Synthetic explanation."})
    .to_string()
}

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

async fn call(router: &Router, uri: &str, actor: &str, body: &Value) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(uri)
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

fn grant(conn: &mut rusqlite::Connection, material: &Value) -> Value {
    document::create_optional(
        conn,
        None,
        None,
        "Synthetic grant",
        json!({"type":"doc","content":[],"attrs":{
            "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
                "purpose":"practice","consumer":"deeptutor","operations":["practice"],
                "material":snap(material),
                "authorization_basis":"SYNTHETIC explicit human authorization",
                "expires_at":null,"state":"granted"}
        }}),
    )
    .unwrap()
}

#[tokio::test]
async fn a_generated_candidate_becomes_a_graded_question_only_by_human_acceptance() {
    let Some(python) = repository_python() else {
        eprintln!("skipping: no usable Python interpreter; this skip is not evidence");
        return;
    };
    let practice_worker =
        python_route("services/learning-providers/deeptutor/practice_host_worker.py");
    let model_worker =
        python_route("services/python-workers/openmaic/worker_outline_local_model.py");
    let text_worker = python_route("services/python-workers/transport/text_ndjson.py");
    let (port, calls) = start_stub(model_content());
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
    let (material, source_grant) = {
        let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
        let material = document::create_optional(
            &mut conn,
            None,
            None,
            "Synthetic material",
            json!({"type":"doc","content":[{"type":"paragraph",
                "content":[{"type":"text","text":"SYNTHETIC_MATERIAL_TEXT"}]}]}),
        )
        .unwrap();
        let source_grant = grant(&mut conn, &material);
        (material, source_grant)
    };
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[
            (IMPORT_CAPABILITY, practice_worker),
            (MODEL_CAPABILITY, model_worker),
        ],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());

    // 1. The donor question step produces a candidate whose own answer (D) is
    //    model opinion, not an accepted key.
    let (status, candidate) = call(
        &router,
        TURN_ROUTE,
        "human",
        &json!({"create_request_id":"accept_turn","material":snap(&material),
            "requirement":"One synthetic arithmetic question","model":null}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{candidate}");
    let staged = &candidate["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question_turn_candidate"];
    assert_eq!(staged["question"]["question"], "What is the synthetic sum?");
    assert_eq!(staged["question"]["question_type"], "choice");
    assert!(staged["question"]["options"].is_object());
    assert_eq!(*calls.lock().unwrap(), 1);

    // 2. A machine actor may not accept a candidate.
    let accept = json!({"create_request_id":"accept_1","candidate":snap(&candidate["document"]),
        "correct_answer":"B","question_text":null,"explanation":null});
    let (status, denied) = call(&router, ACCEPT_ROUTE, "machine", &accept).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");

    // 3. A key outside the candidate options is refused rather than accepted.
    let mut wrong_key = accept.clone();
    wrong_key["correct_answer"] = json!("Z");
    let (status, refused) = call(&router, ACCEPT_ROUTE, "human", &wrong_key).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{refused}");
    assert_eq!(refused["reason"], "question_candidate_not_acceptable");

    // 4. The human supplies key B; only now does a graded question exist.
    let (status, accepted) = call(&router, ACCEPT_ROUTE, "human", &accept).await;
    assert_eq!(status, StatusCode::CREATED, "{accepted}");
    assert_eq!(accepted["origin"], "user_import_unverified");
    assert_eq!(accepted["provider_identity"], "unverified");
    assert_eq!(accepted["independent_mastery"], "not_established");
    assert_eq!(
        accepted["question_view"]["question"]["question_id"]
            .as_str()
            .is_some(),
        true
    );
    assert_eq!(
        accepted["accepted_from"]["candidate"]["document_id"],
        candidate["document"]["document_id"]
    );
    let saved = &accepted["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question"];
    assert_eq!(saved["question"]["correct_answer"], "B");
    assert_eq!(
        saved["question"]["explanation"], "Synthetic explanation.",
        "the reviewed model draft supplies the explanation when the caller does not"
    );
    let acceptance =
        &accepted["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question_acceptance"];
    assert_eq!(acceptance["answer_key_source"], "human_declared");
    assert_eq!(acceptance["model_answer_used_as_key"], false);
    assert_eq!(acceptance["explanation_source"], "model_draft_reviewed");
    assert!(
        !accepted["question_view"]
            .to_string()
            .contains("Synthetic explanation"),
        "the practice view never carries the answer key or explanation"
    );
    let question = snap(&accepted["question_document"]);

    // 5. A repeated acceptance reads the same Document and does not create a
    //    second one.
    let (status, duplicate) = call(&router, ACCEPT_ROUTE, "human", &accept).await;
    assert_eq!(status, StatusCode::CREATED, "{duplicate}");
    assert_eq!(duplicate["duplicate"], true);
    assert_eq!(
        duplicate["question_document"]["document_id"],
        accepted["question_document"]["document_id"]
    );

    // 6. The accepted question is a real graded question: the formal grading
    //    route accepts it with a version-bound question grant.
    let question_grant = executor
        .store()
        .submit_wait({
            let question = question.clone();
            move |conn| Ok::<Value, rusqlite::Error>(grant(conn, &json!(question)))
        })
        .await
        .unwrap()
        .unwrap();
    let activity = json!({"activity_id":"accept_activity","material":snap(&material),
        "provider":{"id":"deeptutor","version":"1.7.1"},
        "question":{"question_id":accepted["question_view"]["question"]["question_id"],
            "question_version":accepted["question_view"]["question_version"]},
        "grant":snap(&source_grant)});
    let (status, created) = call(&router, ACTIVITIES, "human", &activity).await;
    assert_eq!(status, StatusCode::CREATED, "{created}");
    let (status, attempt) = call(
        &router,
        &format!("{ACTIVITIES}/accept_activity/attempts"),
        "human",
        &json!({"attempt_id":"accept_attempt"}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{attempt}");
    let (status, graded) = call(
        &router,
        GRADE_ROUTE,
        "human",
        &json!({"activity_id":"accept_activity","attempt_id":"accept_attempt","request":{
            "client_event_id":"accept_grade","question_document":question,
            "question_grant":snap(&question_grant),"answer":"B"}}),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{graded}");
    assert_eq!(graded["provider_correct"], json!(true));
    assert_eq!(graded["independent_mastery"], "not_established");
    assert_eq!(
        *calls.lock().unwrap(),
        1,
        "acceptance never calls the model again"
    );
}
