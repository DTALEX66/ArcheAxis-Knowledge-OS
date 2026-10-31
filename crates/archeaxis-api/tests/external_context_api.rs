//! SYNTHETIC material via real Router/Store. No external transport is deployed.
use archeaxis_store_sqlite::writer::Store;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
async fn call(r: &Router, method: &str, path: &str, actor: &str, body: Value) -> (u16, Value) {
    let response = r
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(if body.is_null() {
                    String::new()
                } else {
                    body.to_string()
                }))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}
fn packet() -> Value {
    json!({"candidate":{"schema_version":1,"candidate_id":"case-1","knowledge_kind":"root_cause",
        "title":"API fixture","summary":"Minimal public knowledge","problem":"fixture","root_cause":"UNKNOWN",
        "failed_attempts":[],"resolution":"UNRESOLVED","applicability":"synthetic only","contraindications":"unmeasured",
        "evidence_refs":[],"verification":{"status":"UNKNOWN","command":null,"exit_code":null,"artifact_hash":null,"diff_ref":null},
        "source":{"provider_id":"fixture","project_id":"arbitrary-future-project","source_app":"test-agent",
        "source_ref":"opaque:fixture","auth_scope":"knowledge_candidate:import","fetch_status":"AVAILABLE",
        "provenance":[],"updated_at":"2026-10-23T00:00:00Z"}},"material_authorized":true,"redaction_confirmed":true})
}
#[tokio::test]
async fn offline_status_explicit_authorization_and_canonical_idempotent_import() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("workspace.sqlite")).unwrap();
    let r = archeaxis_api::router(store);
    let status = call(
        &r,
        "GET",
        "/api/v1/machine/external-context/status",
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(status.0, 200);
    assert_eq!(status.1["fetch_status"], "NOT_CONNECTED");
    assert_eq!(status.1["network_fetch"], false);
    let path = "/api/v1/machine/external-context/candidates";
    assert_eq!(call(&r, "POST", path, "machine", packet()).await.0, 403);
    let mut denied = packet();
    denied["material_authorized"] = json!(false);
    assert!(call(&r, "POST", path, "human", denied).await.0 >= 400);
    let mut raw = packet();
    raw["candidate"]["messages"] = json!(["private raw context"]);
    assert_eq!(call(&r, "POST", path, "human", raw).await.0, 422);
    let first = call(&r, "POST", path, "human", packet()).await;
    assert_eq!(first.0, 201, "{}", first.1);
    assert_eq!(call(&r, "POST", path, "human", packet()).await.1, first.1);
    assert_eq!(
        first.1["editor_json"]["attrs"]["archeaxis_ai_asset"]["state"],
        "candidate"
    );
    let read = call(
        &r,
        "GET",
        &format!(
            "/api/v1/documents/{}",
            first.1["document_id"].as_str().unwrap()
        ),
        "human",
        Value::Null,
    )
    .await;
    assert_eq!(read.0, 200);
    assert_eq!(read.1["document_id"], first.1["document_id"]);
}
