//! One human learning journey over the formal router and the real Core writer:
//! synthetic material -> imported practice question -> activity and attempt ->
//! fixed DeepTutor 1.7.1 grading -> read-only grade disposition -> restart replay.
//!
//! The material and the provider are synthetic; the Core writer, the private
//! import worker and the fixed grader are real. No model or network provider is
//! involved. Without a usable interpreter the test skips and says so: a skip is
//! not evidence.
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
use std::path::PathBuf;
use tower::ServiceExt;

const IMPORT_ROUTE: &str = "/api/v1/learning/deeptutor/practice-import";
const GRADE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade";
const ACTIVITIES: &str = "/api/v1/learning/provider-activities";

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
        &[("deeptutor.practice.import", practice_worker.clone())],
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
}
