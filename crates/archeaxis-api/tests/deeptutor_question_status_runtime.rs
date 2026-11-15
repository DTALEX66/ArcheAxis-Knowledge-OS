//! New read-only status route checks; synthetic SQLite, no worker or model executable.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{
    document,
    provider_question_turn::{self as turn, QuestionTurnPreparation, QuestionTurnRequest},
};
use axum::{
    Router,
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

async fn fixture() -> (tempfile::TempDir, Executor, Router, Value) {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("status.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let material = document::create_optional(&mut conn, None, None, "Synthetic status material",
        json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic status-only material"}]}]})).unwrap();
    let snapshot = json!({"document_id":material["document_id"],"version":material["version"],"content_sha256":material["content_sha256"]});
    document::create_optional(&mut conn,None,None,"Synthetic status grant",json!({"type":"doc","content":[],"attrs":{
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
    let request = json!({"create_request_id":"status_runtime","material":snapshot,"requirement":"Synthetic requirement","model":null});
    (dir, executor, router, request)
}

async fn call(router: &Router, actor: &str, request: Value) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/learning/deeptutor/question-turn/status")
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(request.to_string()))
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
async fn question_status_runtime_is_bounded_human_only_and_does_not_launch() {
    let (_dir, executor, router, request) = fixture().await;
    assert_eq!(
        call(&router, "machine", request.clone()).await.0,
        StatusCode::FORBIDDEN
    );
    let (status, value) = call(&router, "human", request.clone()).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["state"], "NOT_FOUND");
    assert_eq!(
        value["current_invocation"],
        json!({"worker_invoked":false,"model_invoked":false})
    );
    let claims: i64 = executor.store().submit_wait(|conn|conn.query_row("SELECT count(*) FROM workspace_meta WHERE key LIKE 'deeptutor_question_turn_claim_%'",[],|r|r.get(0))).await.unwrap().unwrap();
    assert_eq!(claims, 0);
    let mut too_large = request;
    too_large["requirement"] = json!("x".repeat(65_536));
    assert_eq!(
        call(&router, "human", too_large).await.0,
        StatusCode::PAYLOAD_TOO_LARGE
    );
}

#[tokio::test]
async fn question_status_runtime_distinguishes_unresolved_and_conflicting_identity() {
    let (_dir, executor, router, request) = fixture().await;
    let parsed: QuestionTurnRequest = serde_json::from_value(request.clone()).unwrap();
    let pending = executor
        .store()
        .submit_wait(move |conn| turn::prepare_question_turn(conn, &parsed))
        .await
        .unwrap()
        .unwrap();
    let QuestionTurnPreparation::Pending(pending) = pending else {
        panic!("expected a fresh dispatch intent")
    };
    let (status, value) = call(&router, "human", request.clone()).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["state"], "DISPATCHED");
    executor
        .store()
        .submit_wait(move |conn| {
            turn::finish_question_turn_failure(conn, &pending, turn::QuestionTurnFailure::Unknown)
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        call(&router, "human", request.clone()).await.1["state"],
        "UNKNOWN"
    );
    let mut changed = request.clone();
    changed["requirement"] = json!("changed request");
    let (status, conflict) = call(&router, "human", changed).await;
    assert_eq!(status, StatusCode::CONFLICT);
    assert_eq!(conflict["reason"], "question_turn_request_id_conflict");
    executor.store().submit_wait(|conn|conn.execute("UPDATE workspace_meta SET value='not-json' WHERE key LIKE 'deeptutor_question_turn_claim_%'",[])).await.unwrap().unwrap();
    let (status, unresolved) = call(&router, "human", request).await;
    assert_eq!(status, StatusCode::CONFLICT);
    assert_eq!(
        unresolved["reason"],
        "question_turn_execution_outcome_unresolved"
    );
}
