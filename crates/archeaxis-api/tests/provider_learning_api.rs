//! In-process HTTP over the real Core writer with synthetic data only.
use archeaxis_api::app;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

async fn call(
    router: &axum::Router,
    method: &str,
    path: &str,
    body: Value,
    actor: &str,
) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
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

#[tokio::test]
async fn local_attempt_is_real_core_persistence_with_conflicts_and_cancellation() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let doc = archeaxis_domain::document::create_optional(
        &mut c,
        None,
        None,
        "SYNTHETIC",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    drop(c);
    let router = app(path.to_str().unwrap()).unwrap();
    let activity = json!({"activity_id":"activity", "material":{"document_id":doc["document_id"],"version":doc["version"],"content_sha256":doc["content_sha256"]},"provider":{"id":"openmaic","version":"1.3.0"},"question":{"question_id":"q1","question_version":"caller_v1"},"grant":null});
    let base = "/api/v1/learning/provider-activities";
    assert_eq!(
        call(&router, "POST", base, activity.clone(), "machine")
            .await
            .0,
        StatusCode::FORBIDDEN
    );
    assert_eq!(
        call(&router, "POST", base, activity.clone(), "human")
            .await
            .0,
        StatusCode::CREATED
    );
    assert_eq!(
        call(&router, "POST", base, activity.clone(), "human")
            .await
            .0,
        StatusCode::OK
    );
    let mut no_grant = activity.clone();
    no_grant["activity_id"] = json!("deeptutor");
    no_grant["provider"] = json!({"id":"deeptutor","version":"1.7.1"});
    assert_eq!(
        call(&router, "POST", base, no_grant, "human").await.0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let attempts = "/api/v1/learning/provider-activities/activity/attempts";
    assert_eq!(
        call(
            &router,
            "POST",
            attempts,
            json!({"attempt_id":"try1"}),
            "human"
        )
        .await
        .0,
        StatusCode::CREATED
    );
    let submit = "/api/v1/learning/provider-activities/activity/attempts/try1/submit";
    let observation = json!({"client_event_id":"event1","answer":"SYNTHETIC", "provider_correct":null,"self_report":true,"rating":null});
    let (status, first) = call(&router, "POST", submit, observation.clone(), "human").await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(first["independent_mastery"], "not_established");
    assert_eq!(
        call(&router, "POST", submit, observation.clone(), "human")
            .await
            .0,
        StatusCode::OK
    );
    let mut changed = observation.clone();
    changed["answer"] = json!("changed");
    assert_eq!(
        call(&router, "POST", submit, changed, "human").await.0,
        StatusCode::CONFLICT
    );
    assert_eq!(
        call(
            &router,
            "POST",
            attempts,
            json!({"attempt_id":"try2"}),
            "human"
        )
        .await
        .0,
        StatusCode::CREATED
    );
    let cancel = "/api/v1/learning/provider-activities/activity/attempts/try2/cancel";
    assert_eq!(
        call(
            &router,
            "POST",
            cancel,
            json!({"client_cancel_id":"cancel1"}),
            "human"
        )
        .await
        .0,
        StatusCode::CREATED
    );
    let late = "/api/v1/learning/provider-activities/activity/attempts/try2/submit";
    let mut late_body = observation;
    late_body["client_event_id"] = json!("late");
    assert_eq!(
        call(&router, "POST", late, late_body, "human").await.0,
        StatusCode::CONFLICT
    );
    let (status, history) = call(
        &router,
        "GET",
        "/api/v1/learning/provider-activities/activity",
        Value::Null,
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(history["attempts"].as_array().unwrap().len(), 2);
    assert_eq!(
        history["provider_result_verification"],
        "unverified_client_report"
    );
}

#[tokio::test]
async fn human_question_view_is_redacted_read_only_and_does_not_authorize_a_provider() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("question.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let source = archeaxis_domain::document::create_optional(
        &mut conn,
        None,
        None,
        "source",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let material = json!({"document_id":source["document_id"],"version":source["version"],"content_sha256":source["content_sha256"]});
    let question=archeaxis_domain::document::create_optional(&mut conn,None,None,"question",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_deeptutor_question":{"schema":"archeaxis.deeptutor-question/v1","source_material":material,
            "origin":"user_import_unverified","upstream_entry_id":"SENTINEL_ENTRY",
            "question":{"question_id":"q1","question":"Which option?","question_type":"choice",
                "options":{"A":"first","B":"second"},"correct_answer":"SENTINEL_KEY","explanation":"SENTINEL_EXPLANATION"}}
    }})).unwrap();
    drop(conn);
    let store = archeaxis_store_sqlite::writer::Store::open(&path).unwrap();
    let router = archeaxis_api::router(store.clone());
    let before = store
        .submit_wait(|conn| conn.total_changes())
        .await
        .unwrap();
    let body = json!({"question_document":{"document_id":question["document_id"],"version":question["version"],"content_sha256":question["content_sha256"]}});
    let route = "/api/v1/learning/deeptutor/question-view";
    assert_eq!(
        call(&router, "POST", route, body.clone(), "machine")
            .await
            .0,
        StatusCode::FORBIDDEN
    );
    let (status, view) = call(&router, "POST", route, body.clone(), "human").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(view["source_reference"], "declared_unverified");
    assert_eq!(view["origin"], "user_import_unverified");
    assert_eq!(view["authorization_effect"], "none");
    assert_eq!(view["provider_executed"], false);
    assert!(!view.to_string().contains("SENTINEL_"));
    let mut invalid = body.clone();
    invalid["question_document"]["content_sha256"] = json!("0".repeat(64));
    assert_eq!(
        call(&router, "POST", route, invalid, "human").await.0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let mut injected = body;
    injected["correct_answer"] = json!("injected");
    assert_eq!(
        call(&router, "POST", route, injected, "human").await.0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let after = store
        .submit_wait(|conn| conn.total_changes())
        .await
        .unwrap();
    assert_eq!(
        after, before,
        "question view must not write through its Core Store connection"
    );
    let conn = rusqlite::Connection::open(&path).unwrap();
    assert_eq!(
        conn.query_row(
            "SELECT count(*) FROM learning_provider_activities",
            [],
            |r| r.get::<_, i64>(0)
        )
        .unwrap(),
        0
    );
    assert_eq!(
        conn.query_row("SELECT count(*) FROM learning_provider_attempts", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
}
