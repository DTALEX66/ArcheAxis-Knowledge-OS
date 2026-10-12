use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;

async fn post(router: &axum::Router, uri: &str, payload: Value) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::post(uri)
                .header("content-type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let payload = serde_json::from_slice(&bytes)
        .unwrap_or_else(|_| json!({"raw": String::from_utf8_lossy(&bytes).to_string()}));
    (status, payload)
}

async fn get(router: &axum::Router, uri: &str) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(Request::get(uri).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let payload = serde_json::from_slice(&bytes)
        .unwrap_or_else(|_| json!({"raw": String::from_utf8_lossy(&bytes).to_string()}));
    (status, payload)
}

#[tokio::test]
async fn source_bound_candidate_checks_unicode_selection_and_commits_anchor_atomically() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source-bound.sqlite");
    let transform_text = "A😀B is a verified selection.";
    let (source_id, transform_id, raw_sha256) = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported =
            source::import_source(&mut conn, b"raw source bytes", "note.txt", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, sha256 }
            | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
        };
        let transform_id =
            source::record_transform(&mut conn, &source_id.0, "text", transform_text, None)
                .unwrap();
        conn.execute(
            "INSERT INTO jobs(job_id,kind,state,input_ref,engine,transform_id) VALUES('job-1','text','succeeded',?1,'fixture',?2)",
            rusqlite::params![source_id.0, transform_id],
        ).unwrap();
        (source_id.0, transform_id, source_id.1)
    };
    let router = app(db.to_str().unwrap()).unwrap();

    let (read_status, transform) = get(
        &router,
        &format!("/api/v1/sources/{source_id}/jobs/job-1/transform"),
    )
    .await;
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
    })
    .await;
    assert_eq!(bad_status, StatusCode::BAD_REQUEST);

    let (created_status, created) =
        post(&router, "/api/v1/knowledge-items/from-transform", base).await;
    assert_eq!(created_status, StatusCode::CREATED, "{created}");
    assert_eq!(created["status"], "candidate");
    assert_eq!(created["source_id"], source_id);
    assert_eq!(created["job_id"], "job-1");
    assert_eq!(created["transform_id"], transform_id);
    assert_eq!(created["raw_sha256"], raw_sha256);
    let knowledge_id = created["knowledge_id"].as_str().unwrap();
    let (v3_status, v3) = get(
        &router,
        &format!("/api/v1/knowledge-items/{knowledge_id}/v3"),
    )
    .await;
    assert_eq!(v3_status, StatusCode::OK, "{v3}");
    assert_eq!(v3["source_id"], source_id);
    assert_eq!(v3["anchor_id"], created["anchor_id"]);
    assert_eq!(v3["status"], "candidate");
    assert_eq!(v3["owner"], "human");
    assert_eq!(v3["requires_human_review"], true);

    let anchor_id = created["anchor_id"].as_str().unwrap();
    let resolve_path = format!("/api/v1/sources/{source_id}/anchors/{anchor_id}/resolve");
    let stored_position: String = init_workspace(db.to_str().unwrap())
        .unwrap()
        .query_row(
            "SELECT position FROM anchors WHERE anchor_id=?1",
            [anchor_id],
            |row| row.get(0),
        )
        .unwrap();
    // Reopening the actual Core route must qualify transform UTF-16 offsets,
    // even though the raw source is different and has no such selected quote.
    drop(router);
    let router = app(db.to_str().unwrap()).unwrap();
    let reopened = router.clone();
    let (resolved_status, resolved) = get(&reopened, &resolve_path).await;
    assert_eq!(resolved_status, StatusCode::OK, "{resolved}");
    assert_eq!(resolved["status"], "CURRENT");
    assert_eq!(resolved["reason"], "transform_selection_revalidated");
    assert_eq!(resolved["scope"], "locator_provenance_only");
    assert_eq!(resolved["position"], stored_position);

    let baseline: Value = serde_json::from_str(&stored_position).unwrap();
    for (field, value) in [
        ("quote", json!("not B")),
        ("selection_start_utf16", json!(2)),
        ("selection_end_utf16", json!(1000)),
        ("transform_id", json!(transform_id + 1)),
        ("job_id", json!("different-job")),
    ] {
        let mut invalid = baseline.clone();
        invalid[field] = value;
        let position = invalid.to_string();
        init_workspace(db.to_str().unwrap())
            .unwrap()
            .execute(
                "UPDATE anchors SET position=?1 WHERE anchor_id=?2",
                rusqlite::params![position, anchor_id],
            )
            .unwrap();
        let (status, result) = get(&reopened, &resolve_path).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(result["status"], "STALE", "{field}: {result}");
        assert_eq!(result["position"], position);
    }
    init_workspace(db.to_str().unwrap())
        .unwrap()
        .execute(
            "UPDATE anchors SET position=?1 WHERE anchor_id=?2",
            rusqlite::params![stored_position, anchor_id],
        )
        .unwrap();
    assert_eq!(get(&reopened, &resolve_path).await.1["status"], "CURRENT");
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    conn.execute("UPDATE jobs SET state='failed' WHERE job_id='job-1'", [])
        .unwrap();
    assert_eq!(get(&reopened, &resolve_path).await.1["status"], "STALE");
    conn.execute("UPDATE jobs SET state='succeeded' WHERE job_id='job-1'", [])
        .unwrap();
    conn.execute(
        "UPDATE sources SET sha256='changed-revision' WHERE source_id=?1",
        [&source_id],
    )
    .unwrap();
    let (_, changed_revision) = get(&reopened, &resolve_path).await;
    assert_eq!(changed_revision["status"], "STALE");
    assert_eq!(changed_revision["reason"], "source_revision_changed");
    conn.execute(
        "UPDATE sources SET sha256=?1 WHERE source_id=?2",
        rusqlite::params![raw_sha256, source_id],
    )
    .unwrap();
    assert_eq!(get(&reopened, &resolve_path).await.1["status"], "CURRENT");

    let response = router
        .oneshot(
            Request::get("/api/v1/evidence/anchors")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let anchors: Value =
        serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(anchors["items"].as_array().unwrap().len(), 1);
    assert!(
        anchors["items"][0]["position"]
            .as_str()
            .unwrap()
            .contains("\"selection_start_utf16\":3")
    );
}

#[tokio::test]
async fn source_bound_candidate_rejects_mismatched_job_and_transform_without_orphan_anchor() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source-bound-mismatch.sqlite");
    let (source_id, transform_id) = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported = source::import_source(&mut conn, b"raw", "note.txt", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        let transform_id =
            source::record_transform(&mut conn, &source_id, "text", "quote", None).unwrap();
        conn.execute(
            "INSERT INTO jobs(job_id,kind,state,input_ref,engine,transform_id) VALUES('job-2','text','failed',?1,'fixture',?2)",
            rusqlite::params![source_id, transform_id],
        ).unwrap();
        (source_id, transform_id)
    };
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, _) = post(
        &router,
        "/api/v1/knowledge-items/from-transform",
        json!({
            "knowledge_type":"PERSONAL_DEFINITION", "body":"candidate", "source_id":source_id,
            "job_id":"job-2", "transform_id":transform_id, "selection_start_utf16":0,
            "selection_end_utf16":5, "quote":"quote"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    let response = router
        .oneshot(
            Request::get("/api/v1/evidence/anchors")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let anchors: Value =
        serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(anchors["items"].as_array().unwrap().len(), 0);
}
