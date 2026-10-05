//! Evidence Center reads the anchors already persisted by the canonical Core.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_domain::{
    anchor,
    source::{self, ImportOutcome},
};
use archeaxis_store_sqlite::init_workspace;

#[tokio::test]
async fn evidence_anchor_list_projects_persisted_core_rows() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("evidence.sqlite");
    let source_id = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported =
            source::import_source(&mut conn, b"evidence body", "notes.md", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        anchor::add_anchor(
            &mut conn,
            &source_id,
            "rev-1",
            r#"{"paragraph":2,"offset":4}"#,
        )
        .unwrap();
        source_id
    };

    let response = app(db.to_str().unwrap())
        .unwrap()
        .oneshot(
            Request::get("/api/v1/evidence/anchors")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let payload: Value = serde_json::from_slice(&body).unwrap();

    assert_eq!(status, StatusCode::OK, "{payload}");
    assert_eq!(payload["items"][0]["source_id"], source_id);
    assert_eq!(payload["items"][0]["source_revision"], "rev-1");
    assert_eq!(
        payload["items"][0]["position"],
        r#"{"paragraph":2,"offset":4}"#
    );
    assert!(payload["items"][0]["raw_sha256"].as_str().unwrap().len() == 64);
    // The name the material was imported under, so a reader can name the thing cited
    // instead of only quoting an opaque source id back at them.
    assert_eq!(payload["items"][0]["source_name"], "notes.md");
    // A bare positional locator carries no selection, so the quote is explicitly null
    // rather than an empty string that would read as a quotation of nothing.
    assert!(payload["items"][0]["quote"].is_null());
    // Nothing cites this anchor yet, so the knowledge link is explicitly null too.
    assert!(payload["items"][0]["knowledge_id"].is_null());
    assert!(payload["items"][0]["knowledge_status"].is_null());
}

async fn anchors_payload(db: &std::path::Path) -> Value {
    let response = app(db.to_str().unwrap())
        .unwrap()
        .oneshot(
            Request::get("/api/v1/evidence/anchors")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body = response.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&body).unwrap()
}

#[tokio::test]
async fn evidence_anchor_list_surfaces_the_quoted_selection() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("evidence-quote.sqlite");
    {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported = source::import_source(&mut conn, b"quoted body", "quoted.md", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        anchor::add_anchor(
            &mut conn,
            &source_id,
            "rev-2",
            r#"{"quote":"the Earth radius is 6371 km","schema":"archeaxis.transform-text-selection/v1"}"#,
        )
        .unwrap();
    }

    let payload = anchors_payload(&db).await;
    assert_eq!(payload["items"][0]["source_name"], "quoted.md");
    assert_eq!(payload["items"][0]["quote"], "the Earth radius is 6371 km");
}

// Seeded protocol receipts test API validation; these are not ASR execution evidence.
async fn time_anchor_post(
    db: &std::path::Path,
    source: &str,
    revision: &str,
    position: Value,
    checksum: Option<&str>,
) -> (StatusCode, Value) {
    let response = app(db.to_str().unwrap())
        .unwrap()
        .oneshot(
            Request::post(format!("/api/v1/sources/{source}/anchors"))
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(
                    serde_json::json!({
        "revision":revision,"position":position.to_string(),"checksum":checksum})
                    .to_string(),
                ))
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

#[tokio::test]
async fn time_anchor_binds_actual_receipt_and_preserves_old_attempt() {
    use sha2::{Digest, Sha256};
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("time.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let import = |conn: &mut rusqlite::Connection, bytes: &[u8]| match source::import_source(
        conn,
        bytes,
        "speech.wav",
        None,
    )
    .unwrap()
    {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let source = import(&mut conn, b"synthetic audio");
    let other = import(&mut conn, b"other audio");
    let revision = format!("{:x}", Sha256::digest(b"synthetic audio"));
    archeaxis_application::jobs::enqueue(&mut conn, "time-job", "transcribe", &source).unwrap();
    let loss=serde_json::json!({"params":{"worker_output":{"duration_ms":2000,"cues":[{"start_ms":100,"end_ms":1000,"text":"value 37"}]}}}).to_string();
    let result_sha = format!("{:x}", Sha256::digest(loss.as_bytes()));
    let checksum = format!("{:x}", Sha256::digest(b"value 37"));
    let request=serde_json::json!({"job_id":"time-job","attempt":1,"capability":"media.transcribe","inputs":[{"sha256":revision}]}).to_string();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('time-job',1,'time-request',?1,'succeeded')",[request]).unwrap();
    conn.execute(
        "UPDATE jobs SET state='succeeded' WHERE job_id='time-job'",
        [],
    )
    .unwrap();
    let metadata =
        serde_json::json!({"kind":"loss_report","sha256":result_sha,"byte_length":loss.len()})
            .to_string();
    conn.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('time-job',1,'loss_report',?1,?2)",rusqlite::params![metadata,loss]).unwrap();
    let locator = serde_json::json!({"type":"time","job_id":"time-job","attempt":1,"cue_index":0,"start_ms":100,"end_ms":1000,"result_sha256":result_sha});
    for (field, value) in [
        ("result_sha256", serde_json::json!("wrong")),
        ("start_ms", serde_json::json!(101)),
        ("attempt", serde_json::json!(2)),
        ("cue_index", serde_json::json!(1)),
    ] {
        let mut bad = locator.clone();
        bad[field] = value;
        assert_eq!(
            time_anchor_post(&db, &source, &revision, bad, Some(&checksum))
                .await
                .0,
            StatusCode::BAD_REQUEST
        );
    }
    let other_revision = format!("{:x}", Sha256::digest(b"other audio"));
    assert_eq!(
        time_anchor_post(
            &db,
            &other,
            &other_revision,
            locator.clone(),
            Some(&checksum)
        )
        .await
        .0,
        StatusCode::BAD_REQUEST
    );
    assert_eq!(
        time_anchor_post(&db, &source, &revision, locator.clone(), Some("wrong"))
            .await
            .0,
        StatusCode::BAD_REQUEST
    );
    let (_, unverified) = time_anchor_post(&db, &source, &revision, locator.clone(), None).await;
    assert_eq!(unverified["location_status"], "unverified");
    let (status, accepted) =
        time_anchor_post(&db, &source, &revision, locator.clone(), Some(&checksum)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(accepted["location_status"], "located");
    let anchor_id = accepted["anchor_id"].as_str().unwrap();
    let saved: String = conn
        .query_row(
            "SELECT position FROM anchors WHERE anchor_id=?1",
            [anchor_id],
            |r| r.get(0),
        )
        .unwrap();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('time-job',2,'next-request','{}','failed')",[]).unwrap();
    assert_eq!(
        time_anchor_post(&db, &source, &revision, locator, Some(&checksum))
            .await
            .0,
        StatusCode::BAD_REQUEST
    );
    assert_eq!(
        conn.query_row(
            "SELECT position FROM anchors WHERE anchor_id=?1",
            [anchor_id],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        saved
    );
    // Empty cues cannot authenticate even a formerly valid cue/checksum.
    conn.execute(
        "DELETE FROM job_attempts WHERE job_id='time-job' AND attempt=2",
        [],
    )
    .unwrap();
    conn.execute(
        "UPDATE job_outputs SET content=?1 WHERE job_id='time-job'",
        [r#"{"params":{"worker_output":{"duration_ms":2000,"cues":[]}}}"#],
    )
    .unwrap();
    let empty: String = conn
        .query_row(
            "SELECT content FROM job_outputs WHERE job_id='time-job'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let empty_hash = format!("{:x}", Sha256::digest(empty.as_bytes()));
    let empty_meta =
        serde_json::json!({"kind":"loss_report","sha256":empty_hash,"byte_length":empty.len()})
            .to_string();
    conn.execute(
        "UPDATE job_outputs SET metadata_json=?1 WHERE job_id='time-job'",
        [empty_meta],
    )
    .unwrap();
    let mut bad = serde_json::from_str::<Value>(&saved).unwrap();
    bad["result_sha256"] = serde_json::json!(empty_hash);
    assert_eq!(
        time_anchor_post(&db, &source, &revision, bad, Some(&checksum))
            .await
            .0,
        StatusCode::BAD_REQUEST
    );
}

// SIMULATED protocol receipts test the API guard; not EPUB worker execution evidence.
#[tokio::test]
async fn epub_locator_requires_exact_receipt_identity_and_retains_old_anchor() {
    use sha2::{Digest, Sha256};
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("epub.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let bytes = b"SIMULATED EPUB custody bytes";
    let source = match source::import_source(&mut conn, bytes, "book.epub", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let revision = format!("{:x}", Sha256::digest(bytes));
    archeaxis_application::jobs::enqueue(&mut conn, "epub-job", "text", &source).unwrap();
    let loss = serde_json::json!({"params":{"format":{"format":"epub","parsed":true,"locations":[{"kind":"epub_chapter_paragraph","path":"book/ch.xhtml","chapter":1,"paragraph":1,"value":"Known paragraph 37"}]}}}).to_string();
    let result_sha = format!("{:x}", Sha256::digest(loss.as_bytes()));
    let checksum = format!("{:x}", Sha256::digest(b"Known paragraph 37"));
    let request = serde_json::json!({"job_id":"epub-job","attempt":1,"capability":"text.extract","inputs":[{"sha256":revision,"media_type":"application/epub+zip"}]}).to_string();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('epub-job',1,'epub-request',?1,'succeeded')",[request]).unwrap();
    conn.execute(
        "UPDATE jobs SET state='succeeded' WHERE job_id='epub-job'",
        [],
    )
    .unwrap();
    let metadata =
        serde_json::json!({"kind":"loss_report","sha256":result_sha,"byte_length":loss.len()})
            .to_string();
    conn.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('epub-job',1,'loss_report',?1,?2)",rusqlite::params![metadata,loss]).unwrap();
    let locator = serde_json::json!({"type":"epub","job_id":"epub-job","attempt":1,"chapter":1,"paragraph":1,"path":"book/ch.xhtml","result_sha256":result_sha});
    for (field, value) in [
        ("chapter", serde_json::json!(2)),
        ("paragraph", serde_json::json!(99)),
        ("path", serde_json::json!("book/other.xhtml")),
        ("attempt", serde_json::json!(2)),
        ("result_sha256", serde_json::json!("0".repeat(64))),
    ] {
        let mut wrong = locator.clone();
        wrong[field] = value;
        assert_eq!(
            time_anchor_post(&db, &source, &revision, wrong, Some(&checksum))
                .await
                .0,
            StatusCode::BAD_REQUEST
        );
    }
    assert_eq!(
        time_anchor_post(&db, &source, &revision, locator.clone(), Some("wrong"))
            .await
            .0,
        StatusCode::BAD_REQUEST
    );
    let (_, unverified) = time_anchor_post(&db, &source, &revision, locator.clone(), None).await;
    assert_eq!(unverified["location_status"], "unverified");
    let (status, located) =
        time_anchor_post(&db, &source, &revision, locator.clone(), Some(&checksum)).await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(located["location_status"], "located");
    let id = located["anchor_id"].as_str().unwrap();
    let original = anchor::get_anchor(&conn, id).unwrap().unwrap();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('epub-job',2,'next-epub','{}','failed')",[]).unwrap();
    assert_eq!(
        time_anchor_post(&db, &source, &revision, locator, Some(&checksum))
            .await
            .0,
        StatusCode::BAD_REQUEST
    );
    drop(conn);
    let reopened = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        anchor::get_anchor(&reopened, id).unwrap().unwrap(),
        original
    );
}
