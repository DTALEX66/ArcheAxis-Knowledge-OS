//! C06: knowledge qualification endpoint - consumers check active status
//! before reusing a unit as current context.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn get_qual(router: &axum::Router, id: &str) -> (StatusCode, Value) {
    let resp = router
        .clone()
        .oneshot(Request::get(format!("/api/v1/knowledge-items/{id}/qualification")).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

async fn post_knowledge(router: &axum::Router, body_text: &str, status: &str) -> String {
    let body = format!(r#"{{"knowledge_type":"FACTUAL_CLAIM","body":"{body_text}","status":"{status}","created_by":"owner"}}"#);
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/knowledge-items")
                .header("content-type", "application/json")
                .body(Body::from(body)).unwrap(),
        )
        .await
        .unwrap();
    let s = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let text = String::from_utf8_lossy(&bytes).to_string();
    assert!(s == StatusCode::CREATED, "create failed {s}: {text}");
    serde_json::from_str::<Value>(&text).unwrap()["knowledge_id"].as_str().expect(&format!("no id in {text}")).to_string()
}

async fn review(router: &axum::Router, id: &str, action: &str) {
    let body = format!(r#"{{"action":"{action}","reviewer":"owner"}}"#);
    let _ = router.clone().oneshot(
        Request::post(format!("/api/v1/knowledge-items/{id}/review-decisions"))
            .header("content-type", "application/json")
            .body(Body::from(body)).unwrap(),
    ).await.unwrap();
}

#[tokio::test]
async fn qualification_reflects_status_and_active_gate() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();

    // accepted row -> active true
    let id = post_knowledge(&router, "qual claim alpha", "candidate").await;
    review(&router, &id, "accepted").await;
    let (s, v) = get_qual(&router, &id).await;
    assert_eq!(s, StatusCode::OK);
    assert_eq!(v["active"], true);
    assert_eq!(v["exists"], true);

    // deprecated row -> active false even though status is persisted
    let id2 = post_knowledge(&router, "qual claim beta", "candidate").await;
    review(&router, &id2, "deprecated").await;
    let (_, v2) = get_qual(&router, &id2).await;
    assert_eq!(v2["active"], false);

    // missing -> 404
    let (s3, _) = get_qual(&router, "k_missing").await;
    assert_eq!(s3, StatusCode::NOT_FOUND);
}

async fn get_search(router: &axum::Router, q: &str) -> Value {
    let resp = router.clone().oneshot(
        Request::get(format!("/api/v1/search?q={q}")).body(Body::empty()).unwrap(),
    ).await.unwrap();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap_or(Value::Null)
}

#[tokio::test]
async fn search_results_carry_active_qualification() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let a = post_knowledge(&router, "alpha active marker zxq1", "candidate").await;
    review(&router, &a, "accepted").await;
    let b = post_knowledge(&router, "beta deprecated marker zxq1", "candidate").await;
    review(&router, &b, "deprecated").await;
    let v = get_search(&router, "zxq1").await;
    let items = v["items"].as_array().unwrap();
    assert_eq!(items.len(), 2, "both rows returned with status");
    let active = items.iter().filter(|it| it["active"] == true).count();
    let inactive = items.iter().filter(|it| it["active"] == false).count();
    assert_eq!(active, 1);
    assert_eq!(inactive, 1);
}

#[tokio::test]
async fn search_active_only_filters_out_inactive() {
    let dir = tempfile::tempdir().unwrap();
    let router = app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let a = post_knowledge(&router, "only alpha live zq", "candidate").await;
    review(&router, &a, "accepted").await;
    let b = post_knowledge(&router, "only beta dead zq", "candidate").await;
    review(&router, &b, "deprecated").await;
    let resp = router.clone().oneshot(
        Request::get("/api/v1/search?q=zq&active_only=true").body(Body::empty()).unwrap(),
    ).await.unwrap();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let v: Value = serde_json::from_slice(&bytes).unwrap();
    let items = v["items"].as_array().unwrap();
    assert_eq!(items.len(), 1);
    assert_eq!(items[0]["active"], true);
}
