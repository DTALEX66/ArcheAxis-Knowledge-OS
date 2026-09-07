//! X04 slice: actor guard on knowledge creation at the API boundary.
//! machine content must start as candidate (no self-accept/verify); human may
//! create personal definitions directly as accepted when no external evidence
//! applies; unknown actor rejected.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use tower::ServiceExt;

use archeaxis_api::app;

async fn post_knowledge(router: &axum::Router, body: &str) -> (StatusCode, String) {
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/knowledge-items")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8_lossy(&bytes).to_string())
}

#[tokio::test]
async fn machine_cannot_self_accept_or_use_empty_identity() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    // machine + candidate + created_by -> allowed (201)
    let (s, _) = post_knowledge(
        &router,
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"machine candidate ok","status":"candidate","actor":"machine","created_by":"python-worker"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::CREATED);

    // machine + accepted -> rejected
    let (s, msg) = post_knowledge(
        &router,
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"machine self-accept attempt","status":"accepted","actor":"machine","created_by":"python-worker"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
    assert!(msg.contains("cannot self-accept"));

    // machine without identity -> rejected
    let (s, _) = post_knowledge(
        &router,
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"anon machine","status":"candidate","actor":"machine"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::BAD_REQUEST);

    // unknown actor -> rejected
    let (s, _) = post_knowledge(
        &router,
        r#"{"knowledge_type":"OPINION","body":"x","status":"candidate","actor":"alien"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn human_personal_definition_may_start_accepted_without_evidence() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (s, body) = post_knowledge(
        &router,
        r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"个人定义，无需外部证据","status":"accepted","actor":"human","created_by":"owner"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::CREATED, "unexpected: {body}");
}
