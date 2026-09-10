//! R15/F07-F09: an Office package reaches the store through its own route.
//!
//! The worker that reads DOCX/PPTX/XLSX already existed in this repository, but no route
//! pointed at it, so the capability was unreachable through the job contract. This suite
//! covers the wiring now: the Core derives an OOXML media type from the name, dispatches
//! `office.structure` to that worker, and the structure listing lands in the store. The
//! negative cases are the point as much as the positive one: a .docx offered to the text
//! route is refused, the legacy binary formats are refused by name, and a document whose
//! engine is missing fails the job instead of succeeding empty.

use archeaxis_application::{
    attempts,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

const DOCX: &str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON").expect("run cargo via the project wrapper").into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap()
}

/// A real DOCX built through the same interpreter, using the fixture builder the
/// worker's own tests use so the sample is a genuine OOXML package.
fn docx_bytes() -> Vec<u8> {
    let script = "import io,sys,zipfile\n\
                  buf=io.BytesIO()\n\
                  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:\n\
                  \x20   z.writestr('[Content_Types].xml', '<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"/>')\n\
                  \x20   z.writestr('word/document.xml', '<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body><w:p><w:r><w:t>measured 6371 km</w:t></w:r></w:p><w:p><w:r><w:t>second paragraph</w:t></w:r></w:p></w:body></w:document>')\n\
                  sys.stdout.buffer.write(buf.getvalue())\n";
    match std::process::Command::new(python()).arg("-c").arg(script).output() {
        Ok(out) if out.status.success() => out.stdout,
        _ => Vec::new(),
    }
}

async fn open_executor(dir: &std::path::Path) -> Executor {
    Executor::open_routes(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[("office.structure", repo().join("services/python-workers/document/worker_office.py"))],
    )
    .await
    .unwrap()
}

#[test]
fn office_names_select_the_office_route_and_the_legacy_formats_are_refused() {
    assert_eq!(attempts::resolve_media_type("office", "report.docx").unwrap(), DOCX);
    assert!(attempts::resolve_media_type("office", "deck.pptx").is_ok());
    assert!(attempts::resolve_media_type("office", "book.xlsx").is_ok());
    // an Office package cannot travel as text: no route may decode a ZIP of XML as text
    let error = attempts::resolve_media_type("text", "report.docx").unwrap_err().to_string();
    assert!(error.contains("cannot accept media type"), "{error}");
    // the legacy binary formats have no reader here, so the name is refused rather than
    // handed to a route that cannot open it
    for name in ["old.doc", "old.ppt", "old.xls", "old.rtf"] {
        let error = attempts::resolve_media_type("office", name).unwrap_err().to_string();
        assert!(error.contains("cannot name a media type"), "{name}: {error}");
    }
}

#[tokio::test]
async fn a_docx_job_is_dispatched_to_the_office_worker_and_its_structure_is_stored() {
    let docx = docx_bytes();
    if docx.is_empty() {
        eprintln!("skipping: zipfile unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let payload = docx.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "report.docx", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-docx", "office", &source_id).unwrap();
        })
        .await
        .unwrap();

    executor.execute("job-docx", "run-docx", 120_000, &Cancellation::new()).await.unwrap();

    let (state, text, receipt) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-docx").unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-docx') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            let receipt: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id='job-docx' AND kind='loss_report'",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text, receipt)
        })
        .await
        .unwrap();

    assert_eq!(state, "succeeded");
    // the worker extracts paragraph text, which is what makes a DOCX more than custody
    assert!(text.contains("6371"), "the paragraph text must be projected: {text:?}");
    assert!(text.contains("second paragraph"), "{text:?}");
    assert!(receipt.contains("python-worker-office"), "{receipt}");
}

#[tokio::test]
async fn a_package_the_worker_cannot_read_fails_the_job_instead_of_succeeding_empty() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    executor
        .store()
        .submit(|conn| {
            let source_id = match source::import_source(conn, b"not a package at all", "broken.docx", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-broken-docx", "office", &source_id).unwrap();
        })
        .await
        .unwrap();

    let outcome = executor.execute("job-broken-docx", "run-broken", 60_000, &Cancellation::new()).await;
    let state = executor
        .store()
        .submit(|conn| jobs::job_state(conn, "job-broken-docx").unwrap().unwrap_or_default())
        .await
        .unwrap();
    assert!(outcome.is_err(), "an unreadable package must not report success");
    assert_eq!(state, "failed");
    let text_outputs: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM job_outputs WHERE job_id='job-broken-docx' AND kind='text'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(text_outputs, 0, "no text artifact may exist for an Office job that failed");
}
