use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
async fn call(app: &Router, method: &str, path: &str, body: Value, actor: &str) -> (u16, Value) {
    let response = app
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
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}
#[tokio::test]
async fn ordinary_document_package_requires_human_and_imports_once() {
    let dir = tempfile::tempdir().unwrap();
    let app = archeaxis_api::app(dir.path().join("package.sqlite").to_str().unwrap()).unwrap();
    let (_,document)=call(&app,"POST","/api/v1/documents",json!({"title":"synthetic","editor_json":{"type":"doc","content":[{"type":"future_node","attrs":{"preserved":true}}]}}),"human").await;
    let (status, package) = call(
        &app,
        "GET",
        &format!(
            "/api/v1/documents/{}/package",
            document["document_id"].as_str().unwrap()
        ),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    let body = json!({"request_id":"package_repeat","package":package});
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/document-packages/import",
            body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    let (status, receipt) = call(
        &app,
        "POST",
        "/api/v1/document-packages/import",
        body.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 201, "{receipt}");
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/document-packages/import",
            body,
            "human"
        )
        .await
        .1,
        receipt
    );
    assert_eq!(receipt["document"]["editor_json"], document["editor_json"]);
    assert_eq!(receipt["knowledge_admission"], "NOT_EXECUTED");
}
