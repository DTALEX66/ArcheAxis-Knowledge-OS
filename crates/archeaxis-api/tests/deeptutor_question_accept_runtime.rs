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
        "correct_answer":"D","explanation":"D is the synthetic model's answer."})
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
    let model_worker = python_route("services/python-workers/course/worker_outline_local_model.py");
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
        saved["question"]["explanation"], "",
        "a model explanation for D cannot silently accompany the human key B"
    );
    let acceptance =
        &accepted["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question_acceptance"];
    assert_eq!(acceptance["answer_key_source"], "human_declared");
    assert_eq!(acceptance["model_answer_used_as_key"], false);
    assert_eq!(acceptance["explanation_source"], "model_draft_not_adopted");
    assert!(
        !accepted["question_view"]
            .to_string()
            .contains("D is the synthetic model's answer"),
        "the practice view never carries the answer key or explanation"
    );
    let question = snap(&accepted["question_document"]);

    // A matching draft may be carried as unverified; a changed question or a
    // human-supplied explanation must retain its own honest source.
    let mut matching = accept.clone();
    matching["create_request_id"] = json!("accept_matching");
    matching["correct_answer"] = json!("D");
    let (status, matched) = call(&router, ACCEPT_ROUTE, "human", &matching).await;
    assert_eq!(status, StatusCode::CREATED, "{matched}");
    let matched_attrs = &matched["document"]["editor_json"]["attrs"];
    assert_eq!(
        matched_attrs["archeaxis_deeptutor_question"]["question"]["explanation"],
        "D is the synthetic model's answer."
    );
    assert_eq!(
        matched_attrs["archeaxis_deeptutor_question_acceptance"]["explanation_source"],
        "model_draft_matching_unverified"
    );
    let mut changed_question = matching.clone();
    changed_question["create_request_id"] = json!("accept_changed_question");
    changed_question["question_text"] = json!("A changed synthetic question");
    let (status, changed_question) = call(&router, ACCEPT_ROUTE, "human", &changed_question).await;
    assert_eq!(status, StatusCode::CREATED, "{changed_question}");
    let changed_attrs = &changed_question["document"]["editor_json"]["attrs"];
    assert_eq!(
        changed_attrs["archeaxis_deeptutor_question"]["question"]["explanation"],
        ""
    );
    assert_eq!(
        changed_attrs["archeaxis_deeptutor_question_acceptance"]["explanation_source"],
        "model_draft_not_adopted"
    );
    let mut supplied = accept.clone();
    supplied["create_request_id"] = json!("accept_supplied_explanation");
    supplied["explanation"] = json!("B is the human-supplied synthetic explanation.");
    let (status, supplied) = call(&router, ACCEPT_ROUTE, "human", &supplied).await;
    assert_eq!(status, StatusCode::CREATED, "{supplied}");
    let supplied_attrs = &supplied["document"]["editor_json"]["attrs"];
    assert_eq!(
        supplied_attrs["archeaxis_deeptutor_question"]["question"]["explanation"],
        "B is the human-supplied synthetic explanation."
    );
    assert_eq!(
        supplied_attrs["archeaxis_deeptutor_question_acceptance"]["explanation_source"],
        "human_supplied"
    );

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

    // A later edit makes the original snapshot historical. A fresh acceptance
    // must not silently create a graded question from that outdated version.
    let candidate_id = candidate["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let mut edited = candidate["document"]["editor_json"].clone();
    edited["content"][0]["content"][0]["text"] = json!("Edited synthetic question");
    let revision = executor
        .store()
        .submit_wait(move |conn| document::save(conn, &candidate_id, 1, edited))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(revision["version"], 2);
    let count_before = executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT count(*) FROM documents", [], |row| {
                row.get::<_, i64>(0)
            })
        })
        .await
        .unwrap()
        .unwrap();
    let mut stale = accept.clone();
    stale["create_request_id"] = json!("accept_stale");
    let (status, _) = call(&router, ACCEPT_ROUTE, "human", &stale).await;
    assert_eq!(
        status,
        StatusCode::CONFLICT,
        "stale candidate was not refused"
    );
    let count_after = executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT count(*) FROM documents", [], |row| {
                row.get::<_, i64>(0)
            })
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        count_after, count_before,
        "a stale candidate writes nothing"
    );

    // The current version with a false digest is also a conflict.
    let mut wrong_digest = accept.clone();
    wrong_digest["create_request_id"] = json!("accept_wrong_digest");
    wrong_digest["candidate"] = json!(snap(&revision));
    wrong_digest["candidate"]["content_sha256"] = json!("0".repeat(64));
    let (status, _) = call(&router, ACCEPT_ROUTE, "human", &wrong_digest).await;
    assert_eq!(status, StatusCode::CONFLICT, "candidate digest must match");
    let count_after_digest = executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT count(*) FROM documents", [], |row| {
                row.get::<_, i64>(0)
            })
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(count_after_digest, count_before);

    // A current snapshot is not sufficient if its visible blocks and the
    // hidden question fields disagree: the accepted question must be the one
    // the human can see.
    let mut inconsistent_body = matching.clone();
    inconsistent_body["create_request_id"] = json!("accept_inconsistent_body");
    inconsistent_body["candidate"] = json!(snap(&revision));
    let (status, _) = call(&router, ACCEPT_ROUTE, "human", &inconsistent_body).await;
    assert_eq!(
        status,
        StatusCode::UNPROCESSABLE_ENTITY,
        "visible body differs"
    );

    let revision_id = revision["document_id"].as_str().unwrap().to_owned();
    let mut option_edit = revision["editor_json"].clone();
    option_edit["attrs"]["archeaxis_deeptutor_question_turn_candidate"]["question"]["question"] =
        json!("Edited synthetic question");
    option_edit["attrs"]["archeaxis_deeptutor_question_turn_candidate"]["question"]["options"]["B"] =
        json!("Edited option");
    let mismatched_options = executor
        .store()
        .submit_wait(move |conn| document::save(conn, &revision_id, 2, option_edit))
        .await
        .unwrap()
        .unwrap();
    let mut inconsistent_options = matching.clone();
    inconsistent_options["create_request_id"] = json!("accept_inconsistent_options");
    inconsistent_options["candidate"] = json!(snap(&mismatched_options));
    let (status, _) = call(&router, ACCEPT_ROUTE, "human", &inconsistent_options).await;
    assert_eq!(
        status,
        StatusCode::UNPROCESSABLE_ENTITY,
        "visible options differ"
    );
    let count_after_inconsistent = executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT count(*) FROM documents", [], |row| {
                row.get::<_, i64>(0)
            })
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(count_after_inconsistent, count_before);

    // Once the visible question and its metadata agree, the edited version is
    // usable. Its old model explanation is not silently carried forward.
    let revision_id = mismatched_options["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let mut consistent = mismatched_options["editor_json"].clone();
    consistent["content"][2]["content"][0]["text"] = json!("B. Edited option");
    let consistent = executor
        .store()
        .submit_wait(move |conn| document::save(conn, &revision_id, 3, consistent))
        .await
        .unwrap()
        .unwrap();
    let mut changed_options = matching;
    changed_options["create_request_id"] = json!("accept_changed_options");
    changed_options["candidate"] = json!(snap(&consistent));
    let (status, changed_options) = call(&router, ACCEPT_ROUTE, "human", &changed_options).await;
    assert_eq!(status, StatusCode::CREATED, "{changed_options}");
    assert_eq!(
        changed_options["question_view"]["question"]["question"],
        "Edited synthetic question"
    );
    assert_eq!(
        changed_options["question_view"]["question"]["options"]["B"],
        "Edited option"
    );
    let option_attrs = &changed_options["document"]["editor_json"]["attrs"];
    assert_eq!(
        option_attrs["archeaxis_deeptutor_question"]["question"]["explanation"],
        ""
    );
    assert_eq!(
        option_attrs["archeaxis_deeptutor_question_acceptance"]["explanation_source"],
        "model_draft_not_adopted"
    );

    // An already completed acceptance remains idempotent after that edit.
    let (status, replay) = call(&router, ACCEPT_ROUTE, "human", &accept).await;
    assert_eq!(status, StatusCode::CREATED, "{replay}");
    assert_eq!(replay["duplicate"], true);
    assert_eq!(replay["question_document"], accepted["question_document"]);

    // The same create ID with a different answer is a conflict, not a shape
    // refusal; the contract distinguishes these cases.
    let mut changed = accept.clone();
    changed["correct_answer"] = json!("C");
    let (status, _) = call(&router, ACCEPT_ROUTE, "human", &changed).await;
    assert_eq!(
        status,
        StatusCode::CONFLICT,
        "changed acceptance ID must conflict"
    );

    // The old accepted snapshot remains readable after restarting without a
    // model or donor route, even though its source candidate was edited.
    drop(router);
    drop(executor);
    let reopened = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[],
    )
    .await
    .unwrap();
    let reopened_router = archeaxis_api::runtime::router(reopened);
    let (status, replayed) = call(&reopened_router, ACCEPT_ROUTE, "human", &accept).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(replayed["duplicate"], true);
    assert_eq!(replayed["question_document"], accepted["question_document"]);
    assert_eq!(
        replayed["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_question_acceptance"]["explanation_source"],
        "model_draft_not_adopted"
    );
    assert_eq!(*calls.lock().unwrap(), 1);
}
