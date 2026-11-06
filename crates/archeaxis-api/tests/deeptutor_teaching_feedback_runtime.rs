//! In-process Runtime router for the DeepTutor teaching-feedback route. The
//! gated test runs the pinned Python donor worker and its byte-preserved
//! upstream modules; no model, cloud provider or user material is used.
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
use std::path::PathBuf;
use tower::ServiceExt;

const ROUTE: &str = "/api/v1/learning/deeptutor/teaching-feedback";
const IMPORT_CAPABILITY: &str = "deeptutor.practice.import";

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

/// One preference upsert whose evidence quote is a literal substring of the
/// learner message, as the donor rule requires.
fn request_body(create_request_id: &str, profile: Value) -> Value {
    json!({"create_request_id":create_request_id,
        "session_id":"session_1","turn_id":format!("{create_request_id}_turn"),
        "profile":profile,
        "current_message":"Please keep the examples short and concrete.",
        "objective_ids":["objective_basics"],
        "focus_objective_id":"objective_basics",
        "updates":[{"kind":"preference","op":"upsert","key":"examples",
            "text":"Keep examples short","basis":"learner_report",
            "evidence":"examples short"}],
        "include_history":false})
}

#[tokio::test]
async fn a_caller_declared_profile_becomes_one_reviewable_candidate() {
    let Some(python) = repository_python() else {
        eprintln!("skipping: no usable Python interpreter; this skip is not evidence");
        return;
    };
    let practice_worker =
        python_route("services/learning-providers/deeptutor/practice_host_worker.py");
    let text_worker = python_route("services/python-workers/transport/text_ndjson.py");
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    {
        let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
        document::create_optional(
            &mut conn,
            None,
            None,
            "Synthetic anchor",
            json!({"type":"doc","content":[{"type":"paragraph",
                "content":[{"type":"text","text":"SYNTHETIC_ANCHOR_TEXT"}]}]}),
        )
        .unwrap();
    }
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[(IMPORT_CAPABILITY, practice_worker.clone())],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());

    // A machine actor may not write a learner profile.
    let body = request_body("feedback_1", json!(null));
    let (status, denied) = call(&router, "machine", &body).await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{denied}");
    assert_eq!(document_count(&executor).await, 1);

    let (status, first) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::CREATED, "{first}");
    assert_eq!(first["worker_invoked"], true);
    assert_eq!(
        first["generation_route"],
        "deeptutor_teaching_feedback_donor_rules"
    );
    assert_eq!(first["model_call"], "NOT_INVOKED");
    assert_eq!(first["response_origin"], "DONOR_RULES_UNVERIFIED");
    assert_eq!(first["status"], "UPDATED");
    assert_eq!(first["changed_fields"], json!(["teaching_preferences"]));
    assert_eq!(first["human_review_required"], true);
    assert_eq!(first["active_content_executed"], false);
    assert_eq!(first["rendering_authorized"], false);
    assert_eq!(first["independent_mastery"], "not_established");
    assert_eq!(first["candidate_document_status"], "current");
    assert_eq!(first["profile_source"], Value::Null);
    assert_eq!(
        first["update_evidence_verification"],
        "nonempty_literal_match_only"
    );
    assert_eq!(
        first["existing_profile_evidence_verification"],
        "NOT_VERIFIED"
    );
    let preference = &first["result_profile"]["teaching_preferences"]["examples"];
    assert_eq!(preference["text"], "Keep examples short");
    assert_eq!(preference["evidence"], "examples short");
    let guidance = &first["guidance"]["teaching_preferences"]["examples"];
    assert_eq!(guidance["text"], "Keep examples short");
    let stored = &first["document"]["editor_json"]["attrs"]["archeaxis_deeptutor_teaching_feedback_candidate"];
    assert_eq!(
        stored["schema"],
        "archeaxis.deeptutor-teaching-feedback-document/v1"
    );
    assert_eq!(stored["update_status"], "UPDATED");
    assert_eq!(stored["persistence"], Value::Null);
    assert_eq!(
        stored["worker_document"]["persistence"], "NOT_PERFORMED",
        "the worker's own claim is stored verbatim"
    );
    assert_eq!(stored["input_profile"], json!({}));
    assert!(
        stored["request_frame"]
            .as_str()
            .unwrap()
            .contains("Please keep the examples short")
    );
    let candidate_id = first["document"]["document_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let candidate_version = first["document"]["version"].as_i64().unwrap();
    let candidate_sha = first["document"]["content_sha256"]
        .as_str()
        .unwrap()
        .to_owned();
    assert_eq!(document_count(&executor).await, 2);

    // A repeated request reads the stored candidate; the rules never run twice.
    let (status, duplicate) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{duplicate}");
    assert_eq!(duplicate["worker_invoked"], false);
    assert_eq!(duplicate["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&executor).await, 2);

    // The same create ID cannot describe different content.
    let mut other = body.clone();
    other["current_message"] = json!("A different synthetic message.");
    let (status, conflict) = call(&router, "human", &other).await;
    assert_eq!(status, StatusCode::CONFLICT, "{conflict}");
    assert_eq!(document_count(&executor).await, 2);

    // The next turn starts from the stored profile snapshot and keeps it.
    let base = json!({"document_id":candidate_id,"version":candidate_version,
        "content_sha256":candidate_sha});
    let mut next = request_body("feedback_2", base.clone());
    next["updates"] = json!([{"kind":"observation","op":"upsert","key":"objective_basics",
        "text":"Prefers worked examples before theory","knowledge_point_id":"objective_basics",
        "basis":"learner_report","evidence":"examples"}]);
    let (status, second) = call(&router, "human", &next).await;
    assert_eq!(status, StatusCode::CREATED, "{second}");
    assert_eq!(second["profile_source"], base);
    assert_eq!(
        second["result_profile"]["teaching_preferences"]["examples"]["text"], "Keep examples short",
        "the base snapshot is carried forward, not dropped"
    );
    assert_eq!(document_count(&executor).await, 3);

    // A stale snapshot is a conflict, never a silently substituted profile.
    let mut stale = request_body(
        "feedback_3",
        json!({"document_id":candidate_id,"version":candidate_version,
            "content_sha256":"0".repeat(64)}),
    );
    stale["focus_objective_id"] = json!("objective_basics");
    let (status, stale_result) = call(&router, "human", &stale).await;
    assert_eq!(status, StatusCode::CONFLICT, "{stale_result}");
    assert_eq!(document_count(&executor).await, 3);

    // A structurally invalid request is refused before any worker runs.
    let mut invalid = request_body("feedback_4", json!(null));
    invalid["objective_ids"] = json!(["objective_other"]);
    let (status, refused) = call(&router, "human", &invalid).await;
    assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{refused}");
    assert_eq!(refused["reason"], "invalid_teaching_feedback_request");
    assert_eq!(document_count(&executor).await, 3);
    drop(router);
    drop(executor);

    // Reopening without the private worker still reads the stored candidate.
    let reopened = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &text_worker,
        &[],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(reopened.clone());
    let (status, read_back) = call(&router, "human", &body).await;
    assert_eq!(status, StatusCode::OK, "{read_back}");
    assert_eq!(read_back["worker_invoked"], false);
    assert_eq!(read_back["document"]["document_id"], candidate_id);
    assert_eq!(document_count(&reopened).await, 3);

    // A runtime without the private DeepTutor worker refuses with a name and
    // writes nothing.
    let (status, missing) = call(&router, "human", &request_body("feedback_5", json!(null))).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE, "{missing}");
    assert_eq!(missing["reason"], "teaching_feedback_worker_unavailable");
    assert_eq!(document_count(&reopened).await, 3);
}
