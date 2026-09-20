//! A04: the Rust/SQLite knowledge writer exposes an explicit V3 projection.

use axum::body::Body;
use axum::http::Request;
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn json(router: &axum::Router, method: &str, path: &str, body: &str) -> (u16, Value) {
    let request = if method == "POST" {
        Request::post(path)
            .header("content-type", "application/json")
            .body(Body::from(body.to_owned()))
            .unwrap()
    } else {
        Request::get(path).body(Body::empty()).unwrap()
    };
    let response = router.clone().oneshot(request).await.unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let value = serde_json::from_slice(&bytes).unwrap_or_else(|_| serde_json::json!({}));
    (status, value)
}

#[tokio::test]
async fn v3_projection_preserves_personal_source_without_external_admission_gate() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("knowledge.sqlite").to_str().unwrap()).unwrap();
    let (status, created) = json(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"my local definition","status":"accepted","created_by":"owner"}"#,
    )
    .await;
    assert_eq!(status, 201);
    let created_id = created["knowledge_id"].as_str().unwrap();

    let (status, projected) = json(
        &router,
        "GET",
        &format!("/api/v1/knowledge-items/{created_id}/v3"),
        "",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(projected["schema_version"], "3.0.0");
    assert_eq!(projected["source_type"], "personal_definition");
    assert_eq!(projected["owner"], "human");
    assert_eq!(projected["status"], "accepted");
    assert_eq!(projected["support_level"], "none");
    assert_eq!(projected["confidence"], serde_json::Value::Null);
    assert_eq!(projected["external_evidence"], serde_json::json!([]));
    assert_eq!(projected["requires_human_review"], false);
}

#[tokio::test]
async fn v3_projection_keeps_machine_candidates_and_revision_links_explicit() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("knowledge.sqlite").to_str().unwrap()).unwrap();
    let (_, first) = json(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"machine v1","status":"candidate","created_by":"python-worker"}"#,
    )
    .await;
    let first_id = first["knowledge_id"].as_str().unwrap();
    let (_, revised) = json(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{first_id}/review-decisions"),
        r#"{"action":"modified","reviewer":"owner","new_body":"machine v2"}"#,
    )
    .await;
    let revised_id = revised["knowledge_id"].as_str().unwrap();

    let (status, projected) = json(
        &router,
        "GET",
        &format!("/api/v1/knowledge-items/{revised_id}/v3"),
        "",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(projected["source_type"], "machine_candidate");
    assert_eq!(projected["owner"], "machine");
    assert_eq!(projected["status"], "candidate");
    assert_eq!(projected["requires_human_review"], true);
    assert_eq!(projected["supersedes"], serde_json::json!([first_id]));

    let (status, old_projected) = json(
        &router,
        "GET",
        &format!("/api/v1/knowledge-items/{first_id}/v3"),
        "",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(old_projected["superseded_by"], serde_json::json!([revised_id]));
}

#[tokio::test]
async fn v3_projection_returns_not_found_without_touching_the_writer() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("knowledge.sqlite").to_str().unwrap()).unwrap();
    let (status, payload) = json(
        &router,
        "GET",
        "/api/v1/knowledge-items/missing/v3",
        "",
    )
    .await;
    assert_eq!(status, 404);
    assert!(payload.is_object());
}

#[tokio::test]
async fn v3_write_persists_governance_metadata_and_carries_it_across_revision() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("knowledge.sqlite").to_str().unwrap()).unwrap();
    let (status, created) = json(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"temporal personal fact","status":"accepted","created_by":"owner","v3":{"source_type":"personal_experience","owner":"human","support_level":"moderate","confidence":0.75,"risk_level":"medium","valid_from":"2026-09-01T00:00:00+00:00","valid_to":"2026-09-30T00:00:00+00:00","external_evidence":[],"requires_human_review":true}}"#,
    )
    .await;
    assert_eq!(status, 201);
    let id = created["knowledge_id"].as_str().unwrap();

    let (status, projected) = json(
        &router,
        "GET",
        &format!("/api/v1/knowledge-items/{id}/v3"),
        "",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(projected["support_level"], "moderate");
    assert_eq!(projected["confidence"], 0.75);
    assert_eq!(projected["risk_level"], "medium");
    assert_eq!(projected["valid_from"], "2026-09-01T00:00:00+00:00");
    assert_eq!(projected["valid_to"], "2026-09-30T00:00:00+00:00");

    let (status, revised) = json(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{id}/review-decisions"),
        r#"{"action":"modified","reviewer":"owner","new_body":"corrected temporal personal fact"}"#,
    )
    .await;
    assert_eq!(status, 200);
    let revised_id = revised["knowledge_id"].as_str().unwrap();
    let (status, revised_projection) = json(
        &router,
        "GET",
        &format!("/api/v1/knowledge-items/{revised_id}/v3"),
        "",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(revised_projection["confidence"], 0.75);
    assert_eq!(revised_projection["risk_level"], "medium");
    assert_eq!(revised_projection["supersedes"], serde_json::json!([id]));
}

#[tokio::test]
async fn v3_write_rejects_invalid_temporal_and_machine_governance() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("knowledge.sqlite").to_str().unwrap()).unwrap();
    let (status, _) = json(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"bad dates","status":"accepted","created_by":"owner","v3":{"source_type":"personal_definition","owner":"human","valid_from":"2026-09-30T00:00:00+00:00","valid_to":"2026-09-01T00:00:00+00:00"}}"#,
    )
    .await;
    assert_eq!(status, 400);

    let (status, _) = json(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"machine accepted","status":"accepted","created_by":"python-worker","v3":{"source_type":"machine_candidate","owner":"machine"}}"#,
    )
    .await;
    assert_eq!(status, 400);
}
