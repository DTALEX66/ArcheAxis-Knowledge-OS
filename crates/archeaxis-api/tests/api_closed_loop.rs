//! API slice test: thin HTTP loop over version/import/anchor/knowledge/review/search.
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use base64::Engine;
use http_body_util::BodyExt;
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_store_sqlite::init_workspace;

#[tokio::test]
async fn api_closed_loop() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();

    // version
    let resp = router
        .clone()
        .oneshot(
            Request::get("/api/v1/system/version")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    // import (base64 of a short text)
    let bytes = "memory palace: spatial encoding improves recall".as_bytes();
    let b64 = base64::engine::general_purpose::STANDARD.encode(bytes);
    let import_body = format!(r#"{{"name":"palace.txt","content_base64":"{b64}"}}"#);
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/imports")
                .header("content-type", "application/json")
                .body(Body::from(import_body))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::ACCEPTED);
    let body = resp.into_body().collect().await.unwrap().to_bytes();
    let v: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let source_id = v["source_id"].as_str().unwrap().to_string();
    assert_eq!(v["duplicate"], false);

    // create knowledge (personal definition)
    let kbody = r#"{"knowledge_type":"PERSONAL_DEFINITION","body":"进步本：记录错误与突破","status":"accepted","created_by":"owner"}"#;
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/knowledge-items")
                .header("content-type", "application/json")
                .body(Body::from(kbody))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);
    let body = resp.into_body().collect().await.unwrap().to_bytes();
    let v: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let kid = v["knowledge_id"].as_str().unwrap().to_string();

    // anchor on the source
    let abody = format!(r#"{{"revision":"rev-1","position":"{{\"start\":0,\"end\":10}}"}}"#);
    let resp = router
        .clone()
        .oneshot(
            Request::post(&format!("/api/v1/sources/{source_id}/anchors"))
                .header("content-type", "application/json")
                .body(Body::from(abody))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);

    // review decision (accept)
    let rbody = r#"{"action":"accepted","reviewer":"owner","note":"ok"}"#;
    let resp = router
        .clone()
        .oneshot(
            Request::post(&format!("/api/v1/knowledge-items/{kid}/review-decisions"))
                .header("content-type", "application/json")
                .body(Body::from(rbody))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    // search (FTS5)
    let resp = router
        .clone()
        .oneshot(
            Request::get("/api/v1/search?q=%E8%BF%9B%E6%AD%A5%E6%9C%AC")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = resp.into_body().collect().await.unwrap().to_bytes();
    let v: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert!(v["count"].as_i64().unwrap() >= 1, "search should hit: {v}");

    // workspace info
    let resp = router
        .oneshot(
            Request::get("/api/v1/workspaces/info")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn worker_job_flow_via_api() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("jobs.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();

    // import source
    let b64 = base64::engine::general_purpose::STANDARD.encode(b"note body text here");
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/imports")
                .header("content-type", "application/json")
                .body(Body::from(format!(
                    r#"{{"name":"n.txt","content_base64":"{b64}"}}"#
                )))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::ACCEPTED);
    let v: serde_json::Value =
        serde_json::from_slice(&resp.into_body().collect().await.unwrap().to_bytes()).unwrap();
    let sid = v["source_id"].as_str().unwrap().to_string();

    // enqueue a worker job
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/jobs")
                .header("content-type", "application/json")
                .body(Body::from(format!(
                    r#"{{"job_id":"job-9","kind":"transform","input_ref":"{sid}"}}"#
                )))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::ACCEPTED);

    // worker posts a completed receipt with text + loss receipt
    let receipt = r#"{"state":"succeeded","engine":"python-worker","text":"note body text here (clean)","loss_receipt":{"engine":"python-worker","engine_version":"0.1.0","params":{},"loss_note":"bom stripped"}}"#;
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/jobs/job-9/receipts")
                .header("content-type", "application/json")
                .body(Body::from(receipt))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    // failed path records an explicit failure
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/jobs")
                .header("content-type", "application/json")
                .body(Body::from(format!(
                    r#"{{"job_id":"job-10","kind":"ocr","input_ref":"{sid}"}}"#
                )))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::ACCEPTED);
    let resp = router
        .oneshot(
            Request::post("/api/v1/jobs/job-10/receipts")
                .header("content-type", "application/json")
                .body(Body::from(
                    r#"{"state":"failed","error":"ocr engine unavailable"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    // verify persisted state + transform text through a fresh connection
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    let state: String = conn
        .query_row("SELECT state FROM jobs WHERE job_id='job-9'", [], |r| {
            r.get(0)
        })
        .unwrap();
    assert_eq!(state, "succeeded");
    let fstate: String = conn
        .query_row("SELECT state FROM jobs WHERE job_id='job-10'", [], |r| {
            r.get(0)
        })
        .unwrap();
    assert_eq!(fstate, "failed");
    let text: String = conn
        .query_row(
            "SELECT text FROM transforms WHERE source_id=?1",
            [&sid],
            |r| r.get(0),
        )
        .unwrap();
    assert!(text.contains("clean"));
}
