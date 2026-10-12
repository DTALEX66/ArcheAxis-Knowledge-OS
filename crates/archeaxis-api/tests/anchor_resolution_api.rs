//! Read-time qualification is independent of the historical create-time locator flag.
use archeaxis_api::app;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use tower::ServiceExt;

fn digest(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}

fn source(db: &str) -> (String, String) {
    let mut conn = init_workspace(db).unwrap();
    let raw = "星环 source paragraph";
    let source_id =
        match source::import_source(&mut conn, raw.as_bytes(), "note.txt", None).unwrap() {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
    (source_id, digest(raw))
}

async fn call(
    db: &str,
    method: &str,
    path: &str,
    actor: &str,
    payload: Value,
) -> (StatusCode, Value) {
    let response = app(db)
        .unwrap()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("x-archeaxis-actor", actor)
                .header("content-type", "application/json")
                .body(if method == "GET" {
                    Body::empty()
                } else {
                    Body::from(payload.to_string())
                })
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn create(
    db: &str,
    id: &str,
    revision: &str,
    locator: Value,
    checksum: Option<String>,
) -> String {
    let mut body = json!({"revision": revision, "position": locator.to_string()});
    if let Some(checksum) = checksum {
        body["checksum"] = json!(checksum);
    }
    let (status, result) = call(
        db,
        "POST",
        &format!("/api/v1/sources/{id}/anchors"),
        "human",
        body,
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{result}");
    result["anchor_id"].as_str().unwrap().to_owned()
}

async fn resolve(db: &str, source: &str, anchor: &str, actor: &str) -> (StatusCode, Value) {
    call(
        db,
        "GET",
        &format!("/api/v1/sources/{source}/anchors/{anchor}/resolve"),
        actor,
        Value::Null,
    )
    .await
}

fn stored(db: &str, anchor: &str) -> (String, String) {
    init_workspace(db)
        .unwrap()
        .query_row(
            "SELECT source_revision,position FROM anchors WHERE anchor_id=?1",
            [anchor],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap()
}

#[tokio::test]
async fn human_and_machine_revalidate_text_after_reopen_without_rewriting_history() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("workspace.sqlite")
        .to_str()
        .unwrap()
        .to_owned();
    let (id, revision) = source(&db);
    let anchor = create(
        &db,
        &id,
        &revision,
        json!({"type":"text", "start":0, "end":6}),
        Some(digest("星环")),
    )
    .await;
    let before = stored(&db, &anchor);
    for actor in ["human", "machine"] {
        let (status, body) = resolve(&db, &id, &anchor, actor).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["status"], "CURRENT");
        assert_eq!(body["reason"], "locator_revalidated");
        assert_eq!(body["scope"], "locator_provenance_only");
        assert_eq!(body["position"], before.1);
        assert_eq!(stored(&db, &anchor), before);
    }
}

#[tokio::test]
async fn checksum_tampering_is_rechecked_and_a_revision_change_is_stale() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("workspace.sqlite")
        .to_str()
        .unwrap()
        .to_owned();
    let (id, revision) = source(&db);
    let anchor = create(
        &db,
        &id,
        &revision,
        json!({"type":"text", "start":0, "end":6}),
        Some(digest("星环")),
    )
    .await;
    let conn = init_workspace(&db).unwrap();
    let mut position: Value = serde_json::from_str(&stored(&db, &anchor).1).unwrap();
    position["checksum"] = json!(digest("different"));
    conn.execute(
        "UPDATE anchors SET position=?1 WHERE anchor_id=?2",
        rusqlite::params![position.to_string(), anchor],
    )
    .unwrap();
    let before = stored(&db, &anchor);
    let (_, body) = resolve(&db, &id, &anchor, "human").await;
    assert_eq!(body["status"], "STALE");
    assert_eq!(stored(&db, &anchor), before);
    conn.execute(
        "UPDATE anchors SET source_revision='another-revision' WHERE anchor_id=?1",
        [&anchor],
    )
    .unwrap();
    let before = stored(&db, &anchor);
    let (_, body) = resolve(&db, &id, &anchor, "machine").await;
    assert_eq!(body["reason"], "source_revision_changed");
    assert_eq!(stored(&db, &anchor), before);
}

#[tokio::test]
async fn unverified_or_unknown_locators_do_not_gain_qualification_by_reading() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("workspace.sqlite")
        .to_str()
        .unwrap()
        .to_owned();
    let (id, revision) = source(&db);
    for locator in [
        json!({"type":"text","start":0,"end":6}),
        json!({"type":"future_visual"}),
    ] {
        let anchor = create(&db, &id, &revision, locator, None).await;
        let before = stored(&db, &anchor);
        let (status, body) = resolve(&db, &id, &anchor, "human").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["status"], "UNSUPPORTED");
        assert_eq!(stored(&db, &anchor), before);
    }
}

#[tokio::test]
async fn missing_and_cross_source_anchor_ids_are_not_resolved() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("workspace.sqlite")
        .to_str()
        .unwrap()
        .to_owned();
    let (id, revision) = source(&db);
    let anchor = create(
        &db,
        &id,
        &revision,
        json!({"type":"text", "start":0, "end":6}),
        Some(digest("星环")),
    )
    .await;
    for (source, anchor) in [("missing", anchor.as_str()), (id.as_str(), "missing")] {
        let (status, body) = resolve(&db, source, anchor, "human").await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        assert_eq!(body["status"], "MISSING");
    }
    let mut conn = init_workspace(&db).unwrap();
    let other = match source::import_source(&mut conn, b"another", "other.txt", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let (status, body) = resolve(&db, &other, &anchor, "machine").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["reason"], "anchor_not_found_for_source");
    assert_eq!(
        resolve(&db, &id, &anchor, "invalid").await.0,
        StatusCode::BAD_REQUEST
    );
}

#[tokio::test]
async fn worker_locator_is_current_then_stale_on_reparse_and_missing_if_attempt_disappears() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir
        .path()
        .join("workspace.sqlite")
        .to_str()
        .unwrap()
        .to_owned();
    let (id, revision) = source(&db);
    let mut conn = init_workspace(&db).unwrap();
    archeaxis_application::jobs::enqueue(&mut conn, "job", "office", &id).unwrap();
    let wire = json!({"job_id":"job", "attempt":1, "capability":"office.structure", "inputs":[{"sha256":revision}]}).to_string();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('job',1,'request',?1,'succeeded')", [&wire]).unwrap();
    conn.execute("UPDATE jobs SET state='succeeded' WHERE job_id='job'", [])
        .unwrap();
    let text = "paragraph";
    let loss = json!({"params":{"worker_structure":[{"kind":"paragraph","path":["paragraph-1"],"char_start":0,"char_end":9}]}}).to_string();
    for (kind, content) in [
        ("text", text),
        ("document_structure", "[]"),
        ("loss_report", loss.as_str()),
    ] {
        conn.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('job',1,?1,'{}',?2)", rusqlite::params![kind, content]).unwrap();
    }
    let anchor = create(&db, &id, &revision, json!({"type":"worker_structure","job_id":"job","attempt":1,"kind":"paragraph","path":["paragraph-1"]}), Some(digest(text))).await;
    let before = stored(&db, &anchor);
    assert_eq!(
        resolve(&db, &id, &anchor, "machine").await.1["status"],
        "CURRENT"
    );
    let next_wire = json!({"job_id":"job", "attempt":2, "capability":"office.structure", "inputs":[{"sha256":revision}]}).to_string();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('job',2,'request-2',?1,'running')", [&next_wire]).unwrap();
    let (_, body) = resolve(&db, &id, &anchor, "human").await;
    assert_eq!(body["status"], "STALE");
    assert_eq!(body["reason"], "job_attempt_superseded");
    conn.execute("DELETE FROM job_outputs WHERE job_id='job'", [])
        .unwrap();
    conn.execute("DELETE FROM job_attempts WHERE job_id='job'", [])
        .unwrap();
    assert_eq!(
        resolve(&db, &id, &anchor, "human").await.1["status"],
        "MISSING"
    );
    assert_eq!(stored(&db, &anchor), before);
}
