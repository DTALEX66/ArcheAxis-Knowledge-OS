//! The source-scoped transform route must not be text-only.
//!
//! `GET /api/v1/sources/{source_id}/jobs/{job_id}/transform` joined `jobs`, `sources` and
//! `transforms` and then filtered `j.kind='text'`, so a PDF, OCR, Office, HTML, canvas,
//! subtitle, archive, media or ASR job that had succeeded with a stored projection was
//! reported as `404 succeeded source-bound text transform not found`. The projection is what
//! every route stores in `transforms.text` - the PDF worker's extracted text, the OCR
//! worker's reading, the subtitle worker's cue text - so the filter excluded real, readable
//! content on the basis of the job's kind rather than of whether content exists.
//!
//! Nothing asserted the refusal: the existing coverage for this route only exercised
//! `kind='text'`, which is how a text-only filter survived.

use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::Path;
use tower::ServiceExt;

fn load(relative: &str) -> impl std::future::Future<Output = Router> {
    async move { archeaxis_api::app(relative).unwrap() }
}

async fn get(router: &Router, path: &str) -> (u16, serde_json::Value) {
    let resp = router
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(path)
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let status = resp.status().as_u16();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}

/// A workspace with one source and one succeeded job of `kind`, carrying a stored projection.
fn workspace_with(db: &Path, kind: &str, projection: &str) -> (String, i64) {
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let imported =
        source::import_source(&mut conn, b"raw source bytes", "material.bin", None).unwrap();
    let source_id = match imported {
        ImportOutcome::Imported { source_id, .. } | ImportOutcome::Duplicate { source_id, .. } => {
            source_id
        }
    };
    let transform_id = source::record_transform(
        &mut conn,
        &source_id,
        "pymupdf-native-pdf",
        projection,
        None,
    )
    .unwrap();
    conn.execute(
        "INSERT INTO jobs(job_id,kind,state,input_ref,engine,transform_id) \
         VALUES(?1,?2,'succeeded',?3,'pymupdf-native-pdf',?4)",
        rusqlite::params![format!("job-{kind}"), kind, source_id, transform_id],
    )
    .unwrap();
    (source_id, transform_id)
}

#[tokio::test]
async fn a_pdf_transform_is_readable_through_the_source_scoped_route() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("pdf-transform.sqlite");
    let projection = "the extracted radius is 6371 km";
    let (source_id, transform_id) = workspace_with(&db, "pdf", projection);
    let router = load(db.to_str().unwrap()).await;

    let (status, body) = get(
        &router,
        &format!("/api/v1/sources/{source_id}/jobs/job-pdf/transform"),
    )
    .await;
    assert_eq!(
        status, 200,
        "a succeeded PDF job's stored projection must be readable: {body}"
    );
    assert_eq!(body["transform_id"], transform_id);
    assert_eq!(body["content"], projection);
    assert_eq!(body["source_id"], source_id);
}

#[tokio::test]
async fn every_extraction_kind_that_stores_a_projection_is_readable() {
    let dir = tempfile::tempdir().unwrap();
    let kinds = [
        "text",
        "pdf",
        "image",
        "office",
        "html",
        "canvas",
        "subtitles",
        "archive",
        "media",
        "transcribe",
    ];
    for kind in kinds {
        let db = dir.path().join(format!("k-{kind}.sqlite"));
        let projection = format!("projection produced by the {kind} route");
        let (source_id, _) = workspace_with(&db, kind, &projection);
        let router = load(db.to_str().unwrap()).await;
        let (status, body) = get(
            &router,
            &format!("/api/v1/sources/{source_id}/jobs/job-{kind}/transform"),
        )
        .await;
        assert_eq!(status, 200, "kind {kind} must be readable: {body}");
        assert_eq!(body["content"], projection, "kind {kind}");
    }
}

#[tokio::test]
async fn a_job_that_did_not_succeed_is_still_not_readable() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("failed.sqlite");
    let (source_id, transform_id) = workspace_with(&db, "pdf", "unused");
    {
        let conn = rusqlite::Connection::open(&db).unwrap();
        conn.execute(
            "UPDATE jobs SET state='failed', transform_id=NULL WHERE job_id='job-pdf'",
            [],
        )
        .unwrap();
    }
    let _ = transform_id;
    let router = load(db.to_str().unwrap()).await;
    let (status, _) = get(
        &router,
        &format!("/api/v1/sources/{source_id}/jobs/job-pdf/transform"),
    )
    .await;
    assert_eq!(
        status, 404,
        "a job without a stored projection has nothing to read"
    );
}

#[tokio::test]
async fn a_source_that_does_not_own_the_job_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("binding.sqlite");
    let (source_id, _) = workspace_with(&db, "pdf", "the real projection");
    let router = load(db.to_str().unwrap()).await;
    let (status, _) = get(
        &router,
        &format!("/api/v1/sources/src_not_the_owner/jobs/job-pdf/transform"),
    )
    .await;
    assert_eq!(
        status, 404,
        "the source binding must still be enforced, not just the job id"
    );
    // and the real owner still reads it
    let (ok, _) = get(
        &router,
        &format!("/api/v1/sources/{source_id}/jobs/job-pdf/transform"),
    )
    .await;
    assert_eq!(ok, 200);
}
