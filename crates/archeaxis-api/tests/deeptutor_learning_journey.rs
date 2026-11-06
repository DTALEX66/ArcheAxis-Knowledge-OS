//! One human learning journey over the formal router and the real Core writer:
//! synthetic material -> donor question candidate -> imported practice question
//! -> activity and attempt -> fixed DeepTutor 1.7.1 grading -> teaching feedback
//! candidate -> read-only grade disposition -> restart replay.
//!
//! The material and the provider are synthetic; the Core writer, the private
//! import/feedback workers and the fixed grader are real. The one model call
//! goes to a synthetic loopback lane, never a cloud provider. Without a usable
//! interpreter the test skips and says so: a skip is not evidence.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{
    document,
    provider_material_grant::Snapshot,
    source::{self, ImportOutcome},
};
use axum::{
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

const IMPORT_ROUTE: &str = "/api/v1/learning/deeptutor/practice-import";
const QUESTION_TURN_ROUTE: &str = "/api/v1/learning/deeptutor/question-turn";
const FEEDBACK_ROUTE: &str = "/api/v1/learning/deeptutor/teaching-feedback";
const GRADE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade";
const ACTIVITIES: &str = "/api/v1/learning/provider-activities";
const MODEL_CAPABILITY: &str = "course.openmaic.outline-model";
const SYNTHETIC_MODEL: &str = "synthetic-journey-model";

/// One synthetic loopback model lane. Every request is counted, so a retry that
/// silently re-ran the model is observable.
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
            let payload = json!({"model":SYNTHETIC_MODEL,
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

/// The donor question-turn reply shape the replay stage admits.
fn model_content() -> String {
    json!({"question_type":"choice","question":"What is the synthetic sum?",
        "options":{"A":"3","B":"4","C":"5","D":"6"},
        "correct_answer":"B","explanation":"Synthetic explanation."})
    .to_string()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Select an interpreter without any request input. A test that cannot find one
/// skips and says so; a skip is not evidence.
fn repository_python() -> Option<PathBuf> {
    [
        std::env::var_os("ARCHEAXIS_PYTHON").map(PathBuf::from),
        Some(repo().join(".venv/Scripts/python.exe")),
        Some(repo().join(".project-local/build/venv/Scripts/python.exe")),
    ]
    .into_iter()
    .flatten()
    .find(|path| path.is_file())
}

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn grant(conn: &mut rusqlite::Connection, material: &Value) -> Value {
    document::create_optional(conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
            "purpose":"practice","consumer":"deeptutor","operations":["practice"],
            "material":snap(material),"authorization_basis":"SYNTHETIC explicit human authorization",
            "expires_at":null,"state":"granted"}
    }})).unwrap()
}

async fn call(
    router: &axum::Router,
    method: &str,
    uri: &str,
    body: &Value,
    actor: &str,
) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
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

#[tokio::test]
async fn human_journey_imports_answers_grades_and_replays_after_restart() {
    let Some(python) = repository_python() else {
        eprintln!("skipping: no usable Python interpreter; this skip is not evidence");
        return;
    };
    // The Core refuses any `..` component in a worker path, so resolve it.
    let practice_worker = repo()
        .join("services/learning-providers/deeptutor/practice_host_worker.py")
        .canonicalize()
        .unwrap();
    assert!(practice_worker.is_file());
    let question_turn_worker = practice_worker
        .with_file_name("question_turn_worker.py")
        .canonicalize()
        .unwrap();
    let feedback_worker = practice_worker
        .with_file_name("teaching_feedback_worker.py")
        .canonicalize()
        .unwrap();
    let model_worker = repo()
        .join("services/python-workers/openmaic/worker_outline_local_model.py")
        .canonicalize()
        .unwrap();
    let (port, calls) = start_stub(model_content());
    // SAFETY: this binary runs one test; the variables are set once, before any
    // worker is spawned, so no concurrent reader can observe a partial update.
    unsafe {
        std::env::set_var(
            "ARCHEAXIS_MACHINE_ENDPOINT",
            format!("http://127.0.0.1:{port}/v1"),
        );
        std::env::set_var("ARCHEAXIS_MACHINE_MODEL", SYNTHETIC_MODEL);
        std::env::set_var("ARCHEAXIS_MACHINE_PROTOCOL", "openai");
    }

    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let staging = dir.path().join("staging");
    let default_worker = dir.path().join("unused-default");

    let (material, source_id, source_sha256) = {
        let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        let material = document::create_optional(
            &mut conn,
            None,
            None,
            "Synthetic journey material",
            json!({"type":"doc","content":[]}),
        )
        .unwrap();
        let raw = br#"[{"question":"Which option?","question_type":"single_choice","options":{"A":"first","B":"second"},"correct_answer":"B","explanation":"SYNTHETIC_PRIVATE_EXPLANATION"}]"#;
        let (source_id, source_sha256) =
            match source::import_source(&mut conn, raw, "synthetic.json", None).unwrap() {
                ImportOutcome::Imported { source_id, sha256 } => (source_id, sha256),
                ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
            };
        (material, source_id, source_sha256)
    };

    let executor = Executor::open_routes(
        &db,
        &staging,
        &python,
        &default_worker,
        &[
            ("deeptutor.practice.import", practice_worker.clone()),
            ("deeptutor.question.turn", question_turn_worker.clone()),
            ("deeptutor.teaching.feedback", feedback_worker.clone()),
            (MODEL_CAPABILITY, model_worker.clone()),
        ],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());

    // 1. Synthetic material -> imported practice question through the real
    //    private import worker. The limited view never carries the answer key.
    let import = json!({"request_id":"journey_import","source_id":source_id,
        "source_sha256":source_sha256,"source_duplicate":false,"source_format":"json",
        "source_row":1,"material_snapshot":snap(&material),
        "question_id":"synthetic_question","create_request_id":"journey_create",
        "title":"Journey practice"});
    let (status, imported) = call(&router, "POST", IMPORT_ROUTE, &import, "human").await;
    assert_eq!(status, StatusCode::OK, "{imported}");
    let question = imported["question_document"].clone();
    let view = imported["question_view"].clone();
    assert_eq!(view["question"]["question"], "Which option?");
    assert!(view["question"].get("correct_answer").is_none());
    assert!(!view.to_string().contains("SYNTHETIC_PRIVATE_EXPLANATION"));

    // 2. Version-bound grants for the material and the produced question are
    //    created through the same Core writer after the question exists.
    let source_grant = executor
        .store()
        .submit_wait({
            let material = material.clone();
            move |conn| Ok::<Value, rusqlite::Error>(grant(conn, &material))
        })
        .await
        .unwrap()
        .unwrap();
    let question_grant = executor
        .store()
        .submit_wait({
            let question = question.clone();
            move |conn| Ok::<Value, rusqlite::Error>(grant(conn, &question))
        })
        .await
        .unwrap()
        .unwrap();

    // 2b. The donor question step turns the same material into one candidate
    //     through the real prompt worker, the synthetic loopback lane and the
    //     real replay. It is a candidate for human review, not a graded item.
    let turn = json!({"create_request_id":"journey_turn","material":snap(&material),
        "requirement":"One synthetic arithmetic choice question","model":null});
    let (status, candidate) = call(&router, "POST", QUESTION_TURN_ROUTE, &turn, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{candidate}");
    assert_eq!(candidate["model_call"], "INVOKED");
    assert_eq!(candidate["response_origin"], "LOCAL_MODEL_UNVERIFIED");
    assert_eq!(candidate["answer_secrecy"], "not_established");
    assert_eq!(candidate["human_review_required"], true);
    assert_eq!(
        candidate["question"]["question"],
        "What is the synthetic sum?"
    );
    assert_eq!(candidate["model"], SYNTHETIC_MODEL);
    assert_eq!(*calls.lock().unwrap(), 1, "one model call");

    // 3. Human activity and attempt bound to that question version.
    let activity = json!({"activity_id":"journey_activity","material":snap(&material),
        "provider":{"id":"deeptutor","version":"1.7.1"},
        "question":{"question_id":"synthetic_question",
            "question_version":view["question_version"]},
        "grant":snap(&source_grant)});
    let (status, created) = call(&router, "POST", ACTIVITIES, &activity, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{created}");
    let (status, attempt) = call(
        &router,
        "POST",
        &format!("{ACTIVITIES}/journey_activity/attempts"),
        &json!({"attempt_id":"journey_attempt"}),
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{attempt}");

    // 4. The human answers and the formal grading route runs the fixed grader.
    let grade_body = json!({"activity_id":"journey_activity",
        "attempt_id":"journey_attempt","request":{
            "client_event_id":"journey_grade","question_document":snap(&question),
            "question_grant":snap(&question_grant),"answer":"B"}});
    let (status, graded) = call(&router, "POST", GRADE_ROUTE, &grade_body, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{graded}");
    assert_eq!(graded["provider_correct"], json!(true));
    assert_eq!(graded["independent_mastery"], "not_established");
    assert!(!graded.to_string().contains("SYNTHETIC_PRIVATE_EXPLANATION"));

    // 5. The activity read projects the durable grading disposition read-only.
    let (status, history) = call(
        &router,
        "GET",
        &format!("{ACTIVITIES}/journey_activity"),
        &Value::Null,
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{history}");
    assert_eq!(history["attempts"][0]["state"], "submitted");
    assert_eq!(
        history["attempts"][0]["grade_disposition"]["state"],
        "COMPLETED"
    );
    assert!(
        history["attempts"][0]["grade_disposition"]["dispatched_at_unix"]
            .as_u64()
            .unwrap()
            > 0
    );

    // 5b. The human reports how the answer went and the donor teaching rules
    //     persist one reviewable profile candidate. This calls no model and
    //     writes no review or mastery.
    let feedback = json!({"create_request_id":"journey_feedback",
        "session_id":"journey_session","turn_id":"journey_turn_1","profile":null,
        "current_message":"I prefer worked examples before theory, and short ones.",
        "objective_ids":["journey_objective"],"focus_objective_id":"journey_objective",
        "updates":[{"kind":"observation","op":"upsert","key":"journey_objective",
            "text":"Prefers worked examples","knowledge_point_id":"journey_objective",
            "basis":"learner_report","evidence":"worked examples"}],
        "include_history":false});
    let (status, taught) = call(&router, "POST", FEEDBACK_ROUTE, &feedback, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{taught}");
    assert_eq!(taught["model_call"], "NOT_INVOKED");
    assert_eq!(taught["response_origin"], "DONOR_RULES_UNVERIFIED");
    assert_eq!(taught["status"], "UPDATED");
    assert_eq!(taught["independent_mastery"], "not_established");
    assert_eq!(
        taught["result_profile"]["teaching_observations"]["journey_objective"]["text"],
        "Prefers worked examples"
    );
    assert_eq!(
        taught["guidance"]["teaching_observations"]["journey_objective"]["text"],
        "Prefers worked examples"
    );
    let taught_id = taught["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();

    // 6. Restart over the same database: the disposition and the receipt replay,
    //    and no second grader run happens.
    drop(router);
    drop(executor);
    let reopened = Executor::open_routes(
        &db,
        &staging,
        &python,
        &default_worker,
        &[("deeptutor.practice.import", practice_worker)],
    )
    .await
    .unwrap();
    let reopened_router = archeaxis_api::runtime::router(reopened);
    let (status, after_restart) = call(
        &reopened_router,
        "GET",
        &format!("{ACTIVITIES}/journey_activity"),
        &Value::Null,
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{after_restart}");
    assert_eq!(
        after_restart["attempts"][0]["grade_disposition"]["state"],
        "COMPLETED"
    );
    let (status, replay) = call(&reopened_router, "POST", GRADE_ROUTE, &grade_body, "human").await;
    assert_eq!(status, StatusCode::OK, "{replay}");
    assert_eq!(replay["duplicate"], true);
    assert_eq!(replay["provider_correct"], json!(true));

    // The question candidate and the teaching profile replay from storage too:
    // neither the model nor the donor rules run a second time.
    let (status, turn_replay) = call(
        &reopened_router,
        "POST",
        QUESTION_TURN_ROUTE,
        &turn,
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{turn_replay}");
    assert_eq!(turn_replay["worker_invoked"], false);
    assert_eq!(
        *calls.lock().unwrap(),
        1,
        "a restart never re-runs the model"
    );
    let (status, teach_replay) =
        call(&reopened_router, "POST", FEEDBACK_ROUTE, &feedback, "human").await;
    assert_eq!(status, StatusCode::OK, "{teach_replay}");
    assert_eq!(teach_replay["worker_invoked"], false);
    assert_eq!(teach_replay["document"]["document_id"], taught_id.as_str());
    assert_eq!(teach_replay["candidate_document_status"], "current");
}
