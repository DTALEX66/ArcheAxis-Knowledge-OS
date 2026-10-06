//! Synthetic binary HTTP transfer budget regression, not media decoding evidence.
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use base64::Engine;
use http_body_util::BodyExt;
use tower::ServiceExt;
#[tokio::test]
async fn known_six_and_twenty_six_mib_originals_import_and_read_back_exactly() {
    let dir = tempfile::tempdir().unwrap();
    let router = archeaxis_api::app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    for size in [6 * 1024 * 1024, 26 * 1024 * 1024] {
        let raw = vec![37u8; size];
        let encoded = base64::engine::general_purpose::STANDARD.encode(&raw);
        let body = serde_json::json!({"name":"fixture.mp3","content_base64":encoded});
        let response = router
            .clone()
            .oneshot(
                Request::post("/api/v1/imports")
                    .header("content-type", "application/json")
                    .body(Body::from(body.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::ACCEPTED);
        let imported: serde_json::Value =
            serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes())
                .unwrap();
        let response = router
            .clone()
            .oneshot(
                Request::get(format!(
                    "/api/v1/sources/{}/original",
                    imported["source_id"].as_str().unwrap()
                ))
                .body(Body::empty())
                .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        let original: serde_json::Value =
            serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes())
                .unwrap();
        assert_eq!(original["sha256"], imported["sha256"]);
        assert_eq!(
            base64::engine::general_purpose::STANDARD
                .decode(original["content_base64"].as_str().unwrap())
                .unwrap(),
            raw
        );
    }
}
