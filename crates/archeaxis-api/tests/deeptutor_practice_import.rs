//! Synthetic practice input through the actual Core writer and private worker.
use archeaxis_application::executor::{Executor, PracticeImportCancellation};
use archeaxis_domain::{document, source::{self, ImportOutcome}};
use axum::{body::Body, http::{Request, StatusCode}, Router};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/learning/deeptutor/practice-import";

fn seed(path: &Path) -> Value {
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let material = document::create_optional(&mut conn, None, None, "Synthetic material",
        json!({"type":"doc","content":[]})).unwrap();
    let raw = br#"[{"question":"Which option?","question_type":"single_choice","options":{"A":"first","B":"second"},"correct_answer":"B","explanation":"SYNTHETIC_PRIVATE_EXPLANATION"}]"#;
    let (source_id, source_sha256, source_duplicate) = match source::import_source(
        &mut conn, raw, "synthetic.json", None,
    ).unwrap() {
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
    let response = router.clone().oneshot(Request::builder().method("POST").uri(ROUTE)
        .header("content-type", "application/json").header("x-archeaxis-actor", actor)
        .body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

#[tokio::test]
async fn missing_private_worker_does_not_write_a_question() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let request = seed(&db);
    let executor = Executor::open(&db, &dir.path().join("staging"),
        &dir.path().join("unused-python"), &dir.path().join("unused-worker")).await.unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(post(&router, &request, "machine").await.0, StatusCode::FORBIDDEN);
    let (status, unavailable) = post(&router, &request, "human").await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(unavailable["reason"], "practice_worker_unavailable");
    let count = executor.store().submit_wait(|conn| conn.query_row(
        "SELECT count(*) FROM documents", [], |row| row.get::<_, i64>(0))).await.unwrap().unwrap();
    assert_eq!(count, 1, "missing worker must not create a question document");
}

#[tokio::test]
#[ignore = "requires explicit ARCHEAXIS_PYTHON and launches the fixed local DeepTutor worker"]
async fn explicit_worker_import_persists_once_and_returns_only_the_question_view() {
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("explicit Python required"));
    assert!(python.is_absolute());
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/learning-providers/deeptutor/practice_host_worker.py")
        .canonicalize().unwrap();
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let request = seed(&db);
    let executor = Executor::open_routes(&db, &dir.path().join("staging"), &python,
        &dir.path().join("unused-worker"), &[("deeptutor.practice.import", worker.clone())])
        .await.unwrap();
    // Exercise the same private worker before the HTTP call. Only the finite
    // error category is reported; the answer-bearing response is never printed.
    let probe_request = serde_json::from_value(request.clone()).unwrap();
    let probe = executor.store().submit_wait(move |conn|
        archeaxis_domain::provider_question::prepare_practice_import(conn, &probe_request))
        .await.unwrap().unwrap();
    let probe_result = executor.run_deeptutor_practice_import(
        probe.worker_frame().to_vec(), std::time::Duration::from_secs(60),
        PracticeImportCancellation::new()).await;
    assert!(probe_result.is_ok(), "private worker category: {:?}", probe_result.err());
    assert!(executor.registered_routes().iter().all(|(name, _, _)| *name != "deeptutor.practice.import"),
        "private answer-bearing protocol must not be exposed as a generic job");
    let router = archeaxis_api::runtime::router(executor.clone());
    let (status, first) = post(&router, &request, "human").await;
    assert_eq!(status, StatusCode::OK, "{first}");
    assert_eq!(first["question_view"]["question"]["question"], "Which option?");
    assert_eq!(first["duplicate"], false);
    assert!(!first.to_string().contains("SYNTHETIC_PRIVATE_EXPLANATION"));
    assert!(first["question_view"]["question"].get("correct_answer").is_none());
    let (status, again) = post(&router, &request, "human").await;
    assert_eq!(status, StatusCode::OK, "{again}");
    assert_eq!(again["duplicate"], true);
    assert_eq!(again["question_document"], first["question_document"]);
    let mut changed = request.clone();
    changed["title"] = json!("Conflicting title");
    assert_eq!(post(&router, &changed, "human").await.0, StatusCode::CONFLICT);
    let count = executor.store().submit_wait(|conn| conn.query_row(
        "SELECT count(*) FROM documents", [], |row| row.get::<_, i64>(0))).await.unwrap().unwrap();
    assert_eq!(count, 2, "retries must not create extra documents");
    drop(router);
    drop(executor);
    let reopened = Executor::open_routes(&db, &dir.path().join("staging"), &python,
        &dir.path().join("unused-worker"), &[("deeptutor.practice.import", worker)])
        .await.unwrap();
    let reopened_router = archeaxis_api::runtime::router(reopened);
    let (status, after_restart) = post(&reopened_router, &request, "human").await;
    assert_eq!(status, StatusCode::OK, "{after_restart}");
    assert_eq!(after_restart["duplicate"], true);
    assert_eq!(after_restart["question_document"], first["question_document"]);
}
