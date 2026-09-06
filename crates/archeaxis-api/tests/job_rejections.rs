use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

async fn post(app: &axum::Router, path: &str, body: Value) -> (StatusCode, String) {
    let response = app.clone().oneshot(Request::post(path)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8(bytes.to_vec()).unwrap())
}

#[tokio::test]
async fn job_responses_reflect_persisted_state_and_classify_conflicts() {
    let dir = tempfile::tempdir().unwrap();
    let app = archeaxis_api::app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (_, text) = post(&app, "/api/v1/imports", json!({"name":"x.txt","content_base64":"eA=="})).await;
    let source: Value = serde_json::from_str(&text).unwrap();
    let enqueue = json!({"job_id":"j","kind":"text","input_ref":source["source_id"]});
    assert_eq!(post(&app, "/api/v1/jobs", enqueue.clone()).await.0, StatusCode::ACCEPTED);
    let path = "/api/v1/jobs/j/receipts";
    assert_eq!(post(&app, path, json!({"state":"anything"})).await.0, StatusCode::BAD_REQUEST);
    assert_eq!(post(&app, path, json!({"state":"succeeded"})).await.0, StatusCode::BAD_REQUEST);
    let receipt = json!({"state":"succeeded","engine":"worker","text":"x"});
    assert_eq!(post(&app, path, receipt.clone()).await.0, StatusCode::OK);
    assert_eq!(post(&app, path, receipt).await.0, StatusCode::OK);
    let (_, readback) = post(&app, "/api/v1/jobs", enqueue).await;
    assert_eq!(serde_json::from_str::<Value>(&readback).unwrap()["state"], "succeeded");
    assert_eq!(post(&app, path, json!({"state":"failed","error":"late"})).await.0, StatusCode::CONFLICT);
    assert_eq!(post(&app, path, json!({"state":"succeeded","engine":"worker","text":"changed"})).await.0, StatusCode::CONFLICT);
    assert_eq!(post(&app, "/api/v1/jobs/missing/receipts", json!({"state":"failed"})).await.0, StatusCode::NOT_FOUND);
}
