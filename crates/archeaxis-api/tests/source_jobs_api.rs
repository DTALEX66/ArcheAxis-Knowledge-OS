use archeaxis_api::app;
use archeaxis_application::jobs;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use tower::ServiceExt;

async fn get(router: &axum::Router, path: &str) -> (u16, serde_json::Value) {
    let response = router
        .clone()
        .oneshot(Request::builder().uri(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}

#[tokio::test]
async fn source_jobs_are_read_from_persisted_core_state_and_unknown_sources_are_not_found() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let source_id = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let source_id = match source::import_source(&mut conn, b"reader payload", "reader.txt", None).unwrap() {
            ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        jobs::enqueue(&mut conn, "job-running", "text", &source_id).unwrap();
        jobs::enqueue(&mut conn, "job-succeeded", "text", &source_id).unwrap();
        jobs::enqueue(&mut conn, "job-succeeded-older", "text", &source_id).unwrap();
        jobs::enqueue(&mut conn, "job-failed", "ocr", &source_id).unwrap();
        conn.execute("UPDATE jobs SET state='succeeded',completed_at='2026-09-24T00:00:02Z' WHERE job_id='job-succeeded'", []).unwrap();
        conn.execute("UPDATE jobs SET state='succeeded',completed_at='2026-09-24T00:00:00Z' WHERE job_id='job-succeeded-older'", []).unwrap();
        conn.execute("UPDATE jobs SET state='failed',completed_at='2026-09-24T00:00:03Z' WHERE job_id='job-failed'", []).unwrap();
        conn.execute(
            "INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state,completed_at) VALUES('job-succeeded',1,'attempt-success','{}','succeeded','2026-09-24T00:00:02Z')",
            [],
        ).unwrap();
        conn.execute(
            "INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state,completed_at) VALUES('job-succeeded-older',1,'attempt-success-older','{}','succeeded','2026-09-24T00:00:00Z')",
            [],
        ).unwrap();
        conn.execute(
            "INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state,error,completed_at) VALUES('job-failed',1,'attempt-failed','{}','failed','worker unavailable','2026-09-24T00:00:03Z')",
            [],
        ).unwrap();
        source_id
    };

    // Opening the API after closing the initializer proves the projection is read from
    // the durable workspace, not an in-memory import/session cache.
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, payload) = get(&router, &format!("/api/v1/sources/{source_id}/jobs")).await;
    assert_eq!(status, 200, "{payload}");
    assert_eq!(payload["source_id"], source_id);
    let jobs = payload["jobs"].as_array().unwrap();
    assert_eq!(jobs.len(), 4, "{payload}");
    assert_eq!(jobs[0]["job_id"], "job-failed");
    assert_eq!(jobs[0]["kind"], "ocr");
    assert_eq!(jobs[0]["state"], "failed");
    assert_eq!(jobs[0]["input_ref"], source_id);
    assert_eq!(jobs[0]["attempt"], 1);
    assert_eq!(jobs[0]["error"], "worker unavailable");
    assert_eq!(jobs[1]["job_id"], "job-succeeded");
    assert_eq!(jobs[1]["state"], "succeeded");
    assert_eq!(jobs[2]["job_id"], "job-succeeded-older");
    assert_eq!(jobs[2]["state"], "succeeded");
    assert_eq!(jobs[3]["job_id"], "job-running");
    assert_eq!(jobs[3]["state"], "queued");
    assert!(jobs[3]["attempt"].is_null());

    let empty_id = {
        let mut conn = init_workspace(dir.path().join("empty.sqlite").to_str().unwrap()).unwrap();
        match source::import_source(&mut conn, b"no jobs", "empty.txt", None).unwrap() {
            ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => source_id,
        }
    };
    let empty_router = app(dir.path().join("empty.sqlite").to_str().unwrap()).unwrap();
    let (status, payload) = get(&empty_router, &format!("/api/v1/sources/{empty_id}/jobs")).await;
    assert_eq!(status, 200, "{payload}");
    assert_eq!(payload["jobs"], serde_json::json!([]));

    let (status, _) = get(&router, "/api/v1/sources/src_does_not_exist/jobs").await;
    assert_eq!(status, 404);
}
