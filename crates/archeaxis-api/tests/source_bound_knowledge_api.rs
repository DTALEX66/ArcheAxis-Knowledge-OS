use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;

async fn post(router: &axum::Router, uri: &str, payload: Value) -> (StatusCode, Value) {
    let response = router.clone().oneshot(
        Request::post(uri).header("content-type", "application/json")
            .body(Body::from(payload.to_string())).unwrap(),
    ).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let payload = serde_json::from_slice(&bytes).unwrap_or_else(|_| json!({"raw": String::from_utf8_lossy(&bytes).to_string()}));
    (status, payload)
}

async fn get(router: &axum::Router, uri: &str) -> (StatusCode, Value) {
    let response = router.clone().oneshot(Request::get(uri).body(Body::empty()).unwrap()).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let payload = serde_json::from_slice(&bytes).unwrap_or_else(|_| json!({"raw": String::from_utf8_lossy(&bytes).to_string()}));
    (status, payload)
}

#[tokio::test]
async fn source_bound_candidate_checks_unicode_selection_and_commits_anchor_atomically() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source-bound.sqlite");
    let transform_text = "A😀B is a verified selection.";
    let (source_id, transform_id, raw_sha256) = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported = source::import_source(&mut conn, b"raw source bytes", "note.txt", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, sha256 } | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
        };
        let transform_id = source::record_transform(&mut conn, &source_id.0, "text", transform_text, None).unwrap();
        conn.execute(
            "INSERT INTO jobs(job_id,kind,state,input_ref,engine,transform_id) VALUES('job-1','text','succeeded',?1,'fixture',?2)",
            rusqlite::params![source_id.0, transform_id],
        ).unwrap();
        (source_id.0, transform_id, source_id.1)
    };
    let router = app(db.to_str().unwrap()).unwrap();

    let (read_status, transform) = get(&router, &format!("/api/v1/sources/{source_id}/jobs/job-1/transform")).await;
    assert_eq!(read_status, StatusCode::OK, "{transform}");
    assert_eq!(transform["source_id"], source_id);
    assert_eq!(transform["job_id"], "job-1");
    assert_eq!(transform["transform_id"], transform_id);
    assert_eq!(transform["raw_sha256"], raw_sha256);
    assert_eq!(transform["content"], transform_text);

    let base = json!({
        "knowledge_type": "PERSONAL_DEFINITION",
        "body": "B is the selected definition.",
        "source_id": source_id,
        "job_id": "job-1",
        "transform_id": transform_id,
        "selection_start_utf16": 3,
        "selection_end_utf16": 4,
        "quote": "B"
    });
    let (bad_status, _) = post(&router, "/api/v1/knowledge-items/from-transform", {
        let mut invalid = base.clone();
        invalid["quote"] = json!("not B");
        invalid
    }).await;
    assert_eq!(bad_status, StatusCode::BAD_REQUEST);

    let (created_status, created) = post(&router, "/api/v1/knowledge-items/from-transform", base).await;
    assert_eq!(created_status, StatusCode::CREATED, "{created}");
    assert_eq!(created["status"], "candidate");
    assert_eq!(created["source_id"], source_id);
    assert_eq!(created["job_id"], "job-1");
    assert_eq!(created["transform_id"], transform_id);
    assert_eq!(created["raw_sha256"], raw_sha256);
    let knowledge_id = created["knowledge_id"].as_str().unwrap();
    let (v3_status, v3) = get(&router, &format!("/api/v1/knowledge-items/{knowledge_id}/v3")).await;
    assert_eq!(v3_status, StatusCode::OK, "{v3}");
    assert_eq!(v3["source_id"], source_id);
    assert_eq!(v3["anchor_id"], created["anchor_id"]);
    assert_eq!(v3["status"], "candidate");
    assert_eq!(v3["owner"], "human");
    assert_eq!(v3["requires_human_review"], true);

    let response = router.oneshot(Request::get("/api/v1/evidence/anchors").body(Body::empty()).unwrap()).await.unwrap();
    let anchors: Value = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(anchors["items"].as_array().unwrap().len(), 1);
    assert!(anchors["items"][0]["position"].as_str().unwrap().contains("\"selection_start_utf16\":3"));
}

#[tokio::test]
async fn source_bound_candidate_rejects_mismatched_job_and_transform_without_orphan_anchor() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source-bound-mismatch.sqlite");
    let (source_id, transform_id) = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported = source::import_source(&mut conn, b"raw", "note.txt", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        let transform_id = source::record_transform(&mut conn, &source_id, "text", "quote", None).unwrap();
        conn.execute(
            "INSERT INTO jobs(job_id,kind,state,input_ref,engine,transform_id) VALUES('job-2','text','failed',?1,'fixture',?2)",
            rusqlite::params![source_id, transform_id],
        ).unwrap();
        (source_id, transform_id)
    };
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, _) = post(&router, "/api/v1/knowledge-items/from-transform", json!({
        "knowledge_type":"PERSONAL_DEFINITION", "body":"candidate", "source_id":source_id,
        "job_id":"job-2", "transform_id":transform_id, "selection_start_utf16":0,
        "selection_end_utf16":5, "quote":"quote"
    })).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let response = router.oneshot(Request::get("/api/v1/evidence/anchors").body(Body::empty()).unwrap()).await.unwrap();
    let anchors: Value = serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(anchors["items"].as_array().unwrap().len(), 0);
}
