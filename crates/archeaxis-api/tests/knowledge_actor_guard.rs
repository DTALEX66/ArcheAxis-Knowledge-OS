//! C02: actor is a server-side principal (launch-session claim or, in-process,
//! the x-archeaxis-actor header), never a body field. Machine content must
//! start as candidate; machines cannot self-accept, review, or record human
//! learning outcomes; humans may accept personal definitions without external
//! evidence.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use tower::ServiceExt;

use archeaxis_api::app;

async fn call(router: &axum::Router, method: &str, path: &str, actor: Option<&str>, body: &str) -> (StatusCode, String) {
    let mut req = Request::builder().method(method).uri(path)
        .header("content-type", "application/json");
    if let Some(a) = actor {
        req = req.header("x-archeaxis-actor", a);
    }
    let resp = router.clone().oneshot(req.body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8_lossy(&bytes).to_string())
}

#[tokio::test]
async fn machine_cannot_self_accept_or_act_without_identity() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let kbody = |s: &str, cb: &str| format!(r#"{{"knowledge_type":"FACTUAL_CLAIM","body":"x","status":"{s}","created_by":"{cb}"}}"#);

    // machine + candidate -> 201
    let (s, _) = call(&router, "POST", "/api/v1/knowledge-items", Some("machine"), &kbody("candidate", "python-worker")).await;
    assert_eq!(s, StatusCode::CREATED);

    // machine + accepted -> 400 (cannot self-accept)
    let (s, msg) = call(&router, "POST", "/api/v1/knowledge-items", Some("machine"), &kbody("accepted", "python-worker")).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
    assert!(msg.contains("cannot self-accept"));

    // machine with body actor=human + header machine must NOT escalate
    let body = r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"forged","status":"accepted","actor":"human","created_by":"machine"}"#;
    let (s, _) = call(&router, "POST", "/api/v1/knowledge-items", Some("machine"), body).await;
    assert_eq!(s, StatusCode::BAD_REQUEST, "body actor must be ignored");

    // unknown actor header -> 400
    let (s, _) = call(&router, "POST", "/api/v1/knowledge-items", Some("alien"), &kbody("candidate", "x")).await;
    assert_eq!(s, StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn human_personal_definition_may_start_accepted_without_evidence() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (s, body) = call(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        Some("human"),
        r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"个人定义，无需外部证据","status":"accepted","created_by":"owner"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::CREATED, "unexpected: {body}");
}

#[tokio::test]
async fn machine_cannot_review_or_record_human_learning() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (s, body) = call(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        Some("machine"),
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"proposal","status":"candidate","created_by":"python-worker"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::CREATED);
    let id = serde_json::from_str::<serde_json::Value>(&body).unwrap()["knowledge_id"].as_str().unwrap().to_string();

    // machine review of its own candidate -> 403
    let (s, _) = call(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{id}/review-decisions"),
        Some("machine"),
        r#"{"action":"accepted","reviewer":"python-worker"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::FORBIDDEN);

    // machine recording a human learning outcome -> 403
    let (s, _) = call(
        &router,
        "POST",
        "/api/v1/learning/events",
        Some("machine"),
        r#"{"item_key":"card-a","kind":"review","correct":true}"#,
    )
    .await;
    assert_eq!(s, StatusCode::FORBIDDEN);
}
