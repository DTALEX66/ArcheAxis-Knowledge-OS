//! Synthetic practice input through the actual Core writer and private worker.
use archeaxis_application::executor::{Executor, PracticeImportCancellation};
use archeaxis_domain::{
    document,
    provider_learning::{self, Activity, Provider, Question, Start},
    provider_material_grant::Snapshot,
    provider_question,
    source::{self, ImportOutcome},
};
use axum::{
    Router,
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/learning/deeptutor/practice-import";

fn seed(path: &Path) -> Value {
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let material = document::create_optional(
        &mut conn,
        None,
        None,
        "Synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let raw = br#"[{"question":"Which option?","question_type":"single_choice","options":{"A":"first","B":"second"},"correct_answer":"B","explanation":"SYNTHETIC_PRIVATE_EXPLANATION"}]"#;
    let (source_id, source_sha256, source_duplicate) =
        match source::import_source(&mut conn, raw, "synthetic.json", None).unwrap() {
            ImportOutcome::Imported { source_id, sha256 } => (source_id, sha256, false),
            ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256, true),
        };
    json!({"request_id":"synthetic_request", "source_id":source_id,
        "source_sha256":source_sha256, "source_duplicate":source_duplicate,
        "source_format":"json", "source_row":1,
        "material_snapshot":{"document_id":material["document_id"],"version":material["version"],
            "content_sha256":material["content_sha256"]},
        "question_id":"synthetic_question", "create_request_id":"synthetic_create", "title":"Synthetic practice"})
}

async fn post(router: &Router, body: &Value, actor: &str) -> (StatusCode, Value) {
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

#[tokio::test]
async fn missing_private_worker_does_not_write_a_question() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let request = seed(&db);
    let executor = Executor::open(
        &db,
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        post(&router, &request, "machine").await.0,
        StatusCode::FORBIDDEN
    );
    let (status, unavailable) = post(&router, &request, "human").await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(unavailable["reason"], "practice_worker_unavailable");
    let count = executor
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
        count, 1,
        "missing worker must not create a question document"
    );
}

#[tokio::test]
#[ignore = "requires explicit ARCHEAXIS_PYTHON and launches the fixed local DeepTutor worker"]
async fn explicit_worker_import_persists_once_and_returns_only_the_question_view() {
    let python =
        PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("explicit Python required"));
    assert!(python.is_absolute());
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/learning-providers/deeptutor/practice_host_worker.py")
        .canonicalize()
        .unwrap();
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let request = seed(&db);
    let executor = Executor::open_routes(
        &db,
        &dir.path().join("staging"),
        &python,
        &dir.path().join("unused-worker"),
        &[("deeptutor.practice.import", worker.clone())],
    )
    .await
    .unwrap();
    // Exercise the same private worker before the HTTP call. Only the finite
    // error category is reported; the answer-bearing response is never printed.
    let probe_request = serde_json::from_value(request.clone()).unwrap();
    let probe = executor
        .store()
        .submit_wait(move |conn| {
            archeaxis_domain::provider_question::prepare_practice_import(conn, &probe_request)
        })
        .await
        .unwrap()
        .unwrap();
    let probe_result = executor
        .run_deeptutor_practice_import(
            probe.worker_frame().to_vec(),
            std::time::Duration::from_secs(60),
            PracticeImportCancellation::new(),
        )
        .await;
    assert!(
        probe_result.is_ok(),
        "private worker category: {:?}",
        probe_result.err()
    );
    assert!(
        executor
            .registered_routes()
            .iter()
            .all(|(name, _, _)| *name != "deeptutor.practice.import"),
        "private answer-bearing protocol must not be exposed as a generic job"
    );
    let router = archeaxis_api::runtime::router(executor.clone());
    let (status, first) = post(&router, &request, "human").await;
    assert_eq!(status, StatusCode::OK, "{first}");
    assert_eq!(
        first["question_view"]["question"]["question"],
        "Which option?"
    );
    assert_eq!(first["duplicate"], false);
    assert!(!first.to_string().contains("SYNTHETIC_PRIVATE_EXPLANATION"));
    assert!(
        first["question_view"]["question"]
            .get("correct_answer")
            .is_none()
    );
    let (status, again) = post(&router, &request, "human").await;
    assert_eq!(status, StatusCode::OK, "{again}");
    assert_eq!(again["duplicate"], true);
    assert_eq!(again["question_document"], first["question_document"]);
    let mut changed = request.clone();
    changed["title"] = json!("Conflicting title");
    assert_eq!(
        post(&router, &changed, "human").await.0,
        StatusCode::CONFLICT
    );
    let count = executor
        .store()
        .submit_wait(|conn| {
            conn.query_row("SELECT count(*) FROM documents", [], |row| {
                row.get::<_, i64>(0)
            })
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(count, 2, "retries must not create extra documents");
    drop(router);
    drop(executor);
    let reopened = Executor::open_routes(
        &db,
        &dir.path().join("staging"),
        &python,
        &dir.path().join("unused-worker"),
        &[("deeptutor.practice.import", worker)],
    )
    .await
    .unwrap();
    let reopened_router = archeaxis_api::runtime::router(reopened);
    let (status, after_restart) = post(&reopened_router, &request, "human").await;
    assert_eq!(status, StatusCode::OK, "{after_restart}");
    assert_eq!(after_restart["duplicate"], true);
    assert_eq!(
        after_restart["question_document"],
        first["question_document"]
    );
}

// ---------------------------------------------------------------------------
// DeepTutor practice grading: the formal Core-persisted chain on the real
// runtime router. Synthetic material only; no model or provider service.
// ---------------------------------------------------------------------------

const GRADE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade";

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

fn grade_snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn grade_grant(conn: &mut rusqlite::Connection, material: &Value) -> Value {
    document::create_optional(conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
            "purpose":"practice","consumer":"deeptutor","operations":["practice"],
            "material":grade_snap(material),"authorization_basis":"SYNTHETIC explicit human authorization",
            "expires_at":null,"state":"granted"}
    }})).unwrap()
}

/// A synthetic question Document, both version-bound grants, one DeepTutor
/// 1.7.1 activity and one pending attempt. Nothing here comes from a human.
fn grade_seed(path: &Path) -> Value {
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let source = document::create_optional(
        &mut conn,
        None,
        None,
        "Synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let question = document::create_optional(&mut conn,None,None,"Synthetic question",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_deeptutor_question":{"schema":"archeaxis.deeptutor-question/v1","source_material":grade_snap(&source),
            "origin":"user_import_unverified","question":{"question_id":"synthetic_question","question":"Which option?",
            "question_type":"choice","options":{"A":"first","B":"second"},"correct_answer":"A",
            "explanation":"SYNTHETIC_PRIVATE_EXPLANATION"}}
    }})).unwrap();
    let source_grant = grade_grant(&mut conn, &source);
    let question_grant = grade_grant(&mut conn, &question);
    let view = provider_question::read_view(&conn, &grade_snap(&question)).unwrap();
    let activity = Activity {
        activity_id: "activity".into(),
        material: grade_snap(&source),
        provider: Provider {
            id: "deeptutor".into(),
            version: "1.7.1".into(),
        },
        question: Question {
            question_id: "synthetic_question".into(),
            question_version: view["question_version"].as_str().unwrap().into(),
        },
        grant: Some(grade_snap(&source_grant)),
    };
    provider_learning::create(&mut conn, &activity).unwrap();
    provider_learning::start(
        &mut conn,
        "activity",
        &Start {
            attempt_id: "attempt".into(),
        },
    )
    .unwrap();
    json!({"activity_id":"activity","attempt_id":"attempt","request":{
        "client_event_id":"event","question_document":grade_snap(&question),
        "question_grant":grade_snap(&question_grant),"answer":"A"}})
}

async fn call(
    router: &Router,
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

async fn grade(router: &Router, body: &Value, actor: &str) -> (StatusCode, Value) {
    call(router, "POST", GRADE_ROUTE, body, actor).await
}

async fn attempt_states(executor: &Executor) -> Vec<String> {
    executor
        .store()
        .submit_wait(|conn| {
            let mut statement = conn
                .prepare("SELECT state FROM learning_provider_attempts ORDER BY attempt_id")
                .unwrap();
            statement
                .query_map([], |row| row.get::<_, String>(0))
                .unwrap()
                .collect::<rusqlite::Result<Vec<_>>>()
                .unwrap()
        })
        .await
        .unwrap()
}

#[tokio::test]
async fn grading_without_a_fixed_worker_fails_closed_and_writes_no_result() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let body = grade_seed(&db);
    let executor = Executor::open(
        &db,
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        grade(&router, &body, "machine").await.0,
        StatusCode::FORBIDDEN
    );
    let (status, refused) = grade(&router, &body, "human").await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(refused["code"], "DEEPTUTOR_PRACTICE_GRADE");
    assert_eq!(refused["reason"], "practice_grade_worker_unavailable");
    assert_eq!(attempt_states(&executor).await, vec!["pending".to_string()]);
}

#[tokio::test]
async fn a_cancelled_attempt_cannot_be_graded() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let body = grade_seed(&db);
    let executor = Executor::open(
        &db,
        &dir.path().join("staging"),
        &dir.path().join("unused-python"),
        &dir.path().join("unused-worker"),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let (status, cancelled) = call(
        &router,
        "POST",
        "/api/v1/learning/provider-activities/activity/attempts/attempt/cancel",
        &json!({"client_cancel_id":"cancel"}),
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{cancelled}");
    assert_eq!(cancelled["state"], "cancelled");
    let (status, refused) = grade(&router, &body, "human").await;
    assert_eq!(status, StatusCode::CONFLICT, "{refused}");
    assert_eq!(refused["reason"], "practice_grade_conflict");
    assert_eq!(
        attempt_states(&executor).await,
        vec!["cancelled".to_string()]
    );
}

#[tokio::test]
async fn grading_persists_an_observed_result_once_and_reads_it_back_after_restart() {
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
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let body = grade_seed(&db);
    let staging = dir.path().join("staging");
    let default_worker = dir.path().join("unused-default");
    let executor = Executor::open_routes(
        &db,
        &staging,
        &python,
        &default_worker,
        &[("deeptutor.practice.import", practice_worker.clone())],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let (status, first) = grade(&router, &body, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{first}");
    assert_eq!(first["provider_correct"], json!(true));
    assert_eq!(first["duplicate"], false);
    assert_eq!(
        first["provider_result_verification"],
        "local_upstream_worker_observation"
    );
    assert_eq!(first["independent_mastery"], "not_established");
    assert!(!first.to_string().contains("SYNTHETIC_PRIVATE_EXPLANATION"));
    assert!(first.get("correct_answer").is_none());
    // The same event is a history read, not a second worker run.
    let (status, again) = grade(&router, &body, "human").await;
    assert_eq!(status, StatusCode::OK, "{again}");
    assert_eq!(again["duplicate"], true);
    // A different answer under the same event identity conflicts.
    let mut changed = body.clone();
    changed["request"]["answer"] = json!("B");
    assert_eq!(
        grade(&router, &changed, "human").await.0,
        StatusCode::CONFLICT
    );
    // The history route verifies the stored evidence and reports the observation.
    let (status, history) = call(
        &router,
        "GET",
        "/api/v1/learning/provider-activities/activity",
        &Value::Null,
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{history}");
    assert_eq!(history["attempts"][0]["state"], "submitted");
    assert_eq!(history["provider_result_verification"], "per_attempt");
    assert_eq!(history["independent_mastery"], "not_established");
    // Restart: a fresh Core process state over the same database replays it.
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
    let (status, after_restart) = grade(&reopened_router, &body, "human").await;
    assert_eq!(status, StatusCode::OK, "{after_restart}");
    assert_eq!(after_restart["duplicate"], true);
    assert_eq!(after_restart["provider_correct"], json!(true));
}
