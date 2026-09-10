//! R15/F02-F03: a saved HTML snapshot reaches the store through its own route.
//!
//! The HTML worker existed since an earlier slice with no route pointing at it, so its
//! block structure and link list were unreachable. This suite covers the wiring, and it
//! pins what the route does NOT do: nothing fetches a URL, because the snapshot is the
//! input, so a page that was never saved cannot be read at all.

use archeaxis_application::{
    attempts,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

const SNAPSHOT: &str = "<!doctype html><html><head><title>Measured page</title></head><body>\
<h1>Heading one</h1><p>The measured value is 6371 km.</p>\
<p>Second paragraph with a <a href=\"https://example.invalid/source\">source link</a>.</p>\
<script>var ignored = 1;</script></body></html>";

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON").expect("run cargo via the project wrapper").into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap()
}

async fn open_executor(dir: &std::path::Path) -> Executor {
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[("html.structure", repo().join("services/python-workers/web/worker_html.py"))],
    )
    .await
    .unwrap()
}

#[test]
fn html_names_select_the_html_route_and_never_the_text_route() {
    assert_eq!(attempts::resolve_media_type("html", "snapshot.html").unwrap(), "text/html");
    assert_eq!(attempts::resolve_media_type("html", "page.htm").unwrap(), "text/html");
    assert_eq!(
        attempts::resolve_media_type("html", "page.xhtml").unwrap(),
        "application/xhtml+xml"
    );
    // a saved page must be read by the HTML worker, not decoded as plain text
    let error = attempts::resolve_media_type("text", "snapshot.html").unwrap_err().to_string();
    assert!(error.contains("cannot accept media type text/html"), "{error}");
    // and a URL is not a file name: there is no fetch route at all
    let error = attempts::resolve_media_type("html", "https://example.invalid/").unwrap_err().to_string();
    assert!(error.contains("cannot name a media type"), "{error}");
}

#[tokio::test]
async fn a_snapshot_job_stores_its_body_and_its_link_facts() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let payload = SNAPSHOT.as_bytes().to_vec();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "snapshot.html", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-html", "html", &source_id).unwrap();
        })
        .await
        .unwrap();
    executor.execute("job-html", "run-html", 120_000, &Cancellation::new()).await.unwrap();

    let (state, text, receipt) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-html").unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-html') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            let receipt: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id='job-html' AND kind='loss_report'",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text, receipt)
        })
        .await
        .unwrap();

    assert_eq!(state, "succeeded");
    assert!(text.contains("6371"), "the body must be projected: {text:?}");
    // script content is never projected: it is not executed and not read as text
    assert!(!text.contains("var ignored"), "{text:?}");
    assert!(receipt.contains("python-worker-html"), "{receipt}");
    // the worker's own block anchors and its link list are kept as facts
    assert!(receipt.contains("worker_structure"), "{receipt}");
    assert!(receipt.contains("block-1"), "{receipt}");
    assert!(receipt.contains("example.invalid/source"), "the link list must survive: {receipt}");
}

#[tokio::test]
async fn something_that_is_not_html_fails_the_job_instead_of_succeeding_empty() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    executor
        .store()
        .submit(|conn| {
            let source_id = match source::import_source(conn, b"PK\x03\x04 this is a zip, not a page", "page.html", None)
                .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-not-html", "html", &source_id).unwrap();
        })
        .await
        .unwrap();
    let outcome = executor.execute("job-not-html", "run", 60_000, &Cancellation::new()).await;
    let state = executor
        .store()
        .submit(|conn| jobs::job_state(conn, "job-not-html").unwrap().unwrap_or_default())
        .await
        .unwrap();
    // whatever the worker decides, the job must not report success with an empty body
    if outcome.is_err() {
        assert_eq!(state, "failed");
        let text_outputs: i64 = executor
            .store()
            .submit(|conn| {
                conn.query_row(
                    "SELECT count(*) FROM job_outputs WHERE job_id='job-not-html' AND kind='text'",
                    [],
                    |row| row.get(0),
                )
                .unwrap()
            })
            .await
            .unwrap();
        assert_eq!(text_outputs, 0, "no text artifact may exist for a page that failed");
    } else {
        let text: String = executor
            .store()
            .submit(|conn| {
                conn.query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-not-html') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default()
            })
            .await
            .unwrap();
        assert!(!text.trim().is_empty(), "a success must carry a real body, not nothing");
    }
}
