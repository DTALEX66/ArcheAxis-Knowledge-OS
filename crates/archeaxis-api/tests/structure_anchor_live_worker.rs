//! R15/F07: a location reported by a real worker run becomes a verified anchor.
//!
//! `structure_anchor_api` pins the locator contract against rows written by hand. This closes the
//! remaining gap: the structure here is whatever the actual DOCX worker chose to report for an
//! actual package, read back from the store after a real job, and the anchor is created through the
//! HTTP surface. If a worker ever changes its span conventions without the anchor contract moving
//! with it, this is the suite that says so.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use sha2::{Digest, Sha256};
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_application::{
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("run cargo via the project wrapper")
        .into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap()
}

async fn open_executor(dir: &std::path::Path) -> Executor {
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[(
            "office.structure",
            repo().join("services/python-workers/document/worker_office.py"),
        )],
    )
    .await
    .unwrap()
}

/// What one real run actually reported: the latest attempt's own words.
struct Reported {
    source_id: String,
    revision: String,
    job_id: String,
    attempt: u64,
    kind: String,
    path: Vec<String>,
    excerpt: String,
}

#[tokio::test]
async fn a_location_a_real_docx_run_reported_is_addressable_through_the_api() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("db.sqlite");
    let executor = open_executor(dir.path()).await;
    let bytes =
        std::fs::read(repo().join("tests/fixtures/golden/golden-docx-anchor.docx")).unwrap();
    let reported = {
        let copy = bytes.clone();
        let source_id = executor
            .store()
            .submit(move |conn| {
                let source_id = match source::import_source(conn, &copy, "report.docx", None)
                    .expect("import the committed package")
                {
                    ImportOutcome::Imported { source_id, .. }
                    | ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
                jobs::enqueue(conn, "office-live", "office", &source_id).expect("enqueue");
                source_id
            })
            .await
            .unwrap();
        executor
            .execute(
                "office-live",
                "run-office-live",
                120_000,
                &Cancellation::new(),
            )
            .await
            .unwrap();

        let (revision, attempt, loss, text) = executor
            .store()
            .submit({
                let source_id = source_id.clone();
                move |conn| {
                    let revision: String = conn
                        .query_row(
                            "SELECT sha256 FROM sources WHERE source_id=?1",
                            [&source_id],
                            |row| row.get(0),
                        )
                        .unwrap();
                    let attempt: i64 = conn
                        .query_row(
                            "SELECT MAX(a.attempt) FROM job_attempts a JOIN jobs j ON j.job_id=a.job_id
                             WHERE j.job_id='office-live' AND a.state='succeeded' AND j.state='succeeded'",
                            [],
                            |row| row.get(0),
                        )
                        .unwrap();
                    let loss: String = conn
                        .query_row(
                            "SELECT content FROM job_outputs WHERE job_id='office-live' AND attempt=?1 AND kind='loss_report'",
                            [attempt],
                            |row| row.get(0),
                        )
                        .unwrap();
                    let text: String = conn
                        .query_row(
                            "SELECT content FROM job_outputs WHERE job_id='office-live' AND attempt=?1 AND kind='text'",
                            [attempt],
                            |row| row.get(0),
                        )
                        .unwrap();
                    (revision, attempt, loss, text)
                }
            })
            .await
            .unwrap();
        assert!(attempt >= 1, "a real attempt ran: {attempt}");
        let receipt: Value = serde_json::from_str(&loss).unwrap();
        let entries = receipt["params"]["worker_structure"]
            .as_array()
            .unwrap_or_else(|| panic!("the run reported its own structure: {receipt}"));
        assert!(!entries.is_empty(), "the worker reported nothing");
        // take the first location it named, exactly as it named it
        let entry = &entries[0];
        let kind = entry["kind"].as_str().expect("a kind").to_string();
        let path: Vec<String> = entry["path"]
            .as_array()
            .expect("a path")
            .iter()
            .map(|value| value.as_str().expect("string segment").to_string())
            .collect();
        let start = entry["char_start"].as_u64().expect("char_start") as usize;
        let end = entry["char_end"].as_u64().expect("char_end") as usize;
        assert!(end > start, "{kind} {path:?} spans nothing");
        let excerpt: String = text.chars().skip(start).take(end - start).collect();
        assert!(
            !excerpt.trim().is_empty(),
            "{path:?} addresses only whitespace"
        );
        // the projection is the committed package's own text, not something this test supplied
        assert!(
            text.contains("Document evidence anchor"),
            "unexpected projection from the real worker: {text:?}"
        );
        drop(executor);
        Reported {
            source_id,
            revision,
            job_id: "office-live".to_string(),
            attempt: attempt as u64,
            kind,
            path,
            excerpt,
        }
    };

    // the location the worker named first is addressable through the HTTP surface
    let file = db.to_str().unwrap().to_string();
    let position = serde_json::json!({
        "type": "worker_structure",
        "job_id": reported.job_id,
        "attempt": reported.attempt,
        "kind": reported.kind,
        "path": reported.path,
    })
    .to_string();
    let checksum = format!("{:x}", Sha256::digest(reported.excerpt.as_bytes()));
    let body = serde_json::json!({
        "revision": reported.revision,
        "position": position,
        "checksum": checksum,
    });
    let response = app(&file)
        .unwrap()
        .oneshot(
            Request::post(format!("/api/v1/sources/{}/anchors", reported.source_id))
                .header("x-archeaxis-actor", "human")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let payload: Value = serde_json::from_slice(&bytes).unwrap_or(Value::Null);
    assert_eq!(status, StatusCode::CREATED, "{payload}");
    assert_eq!(payload["location_status"], "located", "{payload}");

    // the same location with a digest of text the run never produced is refused
    let forged = serde_json::json!({
        "revision": reported.revision,
        "position": position,
        "checksum": format!("{:x}", Sha256::digest(b"text from somewhere else")),
    });
    let response = app(&file)
        .unwrap()
        .oneshot(
            Request::post(format!("/api/v1/sources/{}/anchors", reported.source_id))
                .header("x-archeaxis-actor", "human")
                .header("content-type", "application/json")
                .body(Body::from(forged.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}
