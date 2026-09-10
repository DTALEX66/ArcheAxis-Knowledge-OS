//! R09 at the consumption entry: re-reading a learning item reports the revision
//! it was built from and whether that revision is still current, so a consumer
//! cannot silently keep using a superseded revision - while the history itself is
//! never rewritten.

use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn request(router: &axum::Router, method: &str, path: &str, body: &str) -> (StatusCode, Value) {
    let mut req = Request::builder().method(method).uri(path).header("content-type", "application/json");
    let resp = router
        .clone()
        .oneshot(req.body(Body::from(body.to_string())).unwrap())
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

async fn post(router: &axum::Router, path: &str, body: &str) -> (StatusCode, Value) {
    request(router, "POST", path, body).await
}

async fn get(router: &axum::Router, path: &str) -> (StatusCode, Value) {
    request(router, "GET", path, "").await
}

#[tokio::test]
async fn re_reading_an_item_reports_its_revision_and_validity() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    // A current, accepted fact.
    let (status, created) = post(
        &router,
        "/api/v1/knowledge-items",
        r#"{"knowledge_type":"FACTUAL_CLAIM","body":"radius 6371 km","status":"accepted","created_by":"owner"}"#,
    )
    .await;
    assert!(status.is_success(), "{created}");
    let original = created["knowledge_id"].as_str().unwrap().to_string();

    // The learning item records the revision it was built from.
    let (status, _) = post(
        &router,
        "/api/v1/learning/items/card-9/references",
        &serde_json::json!({"knowledge_id": original}).to_string(),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);

    let (status, history) = get(&router, "/api/v1/learning/events/card-9").await;
    assert_eq!(status, StatusCode::OK);
    let references = history["references"].as_array().expect("references array");
    assert_eq!(references.len(), 1, "{history}");
    assert_eq!(references[0]["knowledge_id"], original.as_str());
    assert_eq!(references[0]["active"], true, "the revision is current: {history}");

    // A correction supersedes it and the successor is accepted.
    let (status, superseded) = post(
        &router,
        &format!("/api/v1/knowledge-items/{original}/review-decisions"),
        r#"{"action":"modified","reviewer":"owner","new_body":"radius 6371.0088 km"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{superseded}");
    let successor = superseded["knowledge_id"].as_str().unwrap().to_string();
    assert_ne!(successor, original);
    let (status, _) = post(
        &router,
        &format!("/api/v1/knowledge-items/{successor}/review-decisions"),
        r#"{"action":"accepted","reviewer":"owner"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::OK);

    // Re-reading the same item reports the same historical revision, now clearly
    // not current - the reference was not rewritten and nothing was recalled.
    let (status, history) = get(&router, "/api/v1/learning/events/card-9").await;
    assert_eq!(status, StatusCode::OK);
    let references = history["references"].as_array().expect("references array");
    assert_eq!(references.len(), 1, "{history}");
    assert_eq!(
        references[0]["knowledge_id"],
        original.as_str(),
        "the item must still name the revision it was built from: {history}"
    );
    assert_eq!(references[0]["active"], false, "the referenced revision is no longer current: {history}");

    // A reference to an unknown revision is refused rather than silently ignored.
    let (status, _) = post(
        &router,
        "/api/v1/learning/items/card-9/references",
        r#"{"knowledge_id":"k_missing"}"#,
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}
