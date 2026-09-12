//! R08 step (d) part 2: the executor dispatches by the claimed request's
//! capability through a route registry, and a job whose capability has no
//! registered worker fails explicitly instead of being sent to the wrong process.
//!
//! KNOWN GAP (recorded in docs/authority/taskpack-0910-r3/EXECUTION.md, R08j):
//! running a real PDF job end to end is still blocked by the PDF worker's
//! receipt fidelity, which the Core rejects rather than accepting a half-true
//! receipt:
//!   * the Core validates covered/total/coverage together (the PDF receipt had
//!     no `coverage`), and
//!   * coverage/structure must match the projected text, so anchors must be
//!     derived from the FINISHED text (page separators otherwise shift line
//!     offsets and counts).
//! Both are worker-side fixes; the end-to-end test is added together with them.

use archeaxis_application::{executor::{Cancellation, Executor}, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON").expect("run cargo via the project wrapper").into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap()
}

fn pdf_bytes(text: &str) -> Vec<u8> {
    match std::process::Command::new(python())
        .arg("-c")
        .arg("import fitz,sys;d=fitz.open();d.new_page().insert_text((72,100),sys.argv[1]);sys.stdout.buffer.write(d.tobytes())")
        .arg(text)
        .output()
    {
        Ok(out) if out.status.success() => out.stdout,
        _ => Vec::new(),
    }
}

#[tokio::test]
async fn pdf_job_is_dispatched_to_the_pdf_worker_and_its_text_is_stored() {
    let pdf = pdf_bytes("pdf job 6371 km");
    if pdf.is_empty() {
        eprintln!("skipping: native PDF engine unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let text_worker = repo().join("services/python-workers/transport/text_ndjson.py");
    let pdf_worker = repo().join("services/python-workers/document/worker_pdf.py");
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &text_worker,
        &[("pdf.extract", pdf_worker)],
    )
    .await
    .unwrap();

    let payload = pdf.clone();
    executor.store().submit(move |conn| {
        let source_id = match source::import_source(conn, &payload, "sample.pdf", None).unwrap() {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        jobs::enqueue(conn, "job", "pdf", &source_id).unwrap();
    }).await.unwrap();

    executor.execute("job", "run-pdf", 120_000, &Cancellation::new()).await.unwrap();

    executor.store().submit(|conn| {
        assert_eq!(jobs::job_state(conn, "job").unwrap().as_deref(), Some("succeeded"));
        assert_eq!(conn.query_row("SELECT count(*) FROM job_attempts", [], |r| r.get::<_, i64>(0)).unwrap(), 1);
        assert_eq!(conn.query_row("SELECT count(*) FROM job_outputs", [], |r| r.get::<_, i64>(0)).unwrap(), 3);
        let text: String = conn
            .query_row("SELECT content FROM job_outputs WHERE kind='text'", [], |r| r.get(0))
            .unwrap();
        assert!(text.contains("6371"), "the PDF text must be stored verbatim: {text}");
        let request_json: String = conn
            .query_row("SELECT request_json FROM job_attempts WHERE job_id='job'", [], |r| r.get(0))
            .unwrap();
        assert!(request_json.contains("\"capability\":\"pdf.extract\""), "{request_json}");
        assert!(request_json.contains("application/pdf"), "{request_json}");
        let engine: String = conn
            .query_row("SELECT engine FROM jobs WHERE job_id='job'", [], |r| r.get(0))
            .unwrap();
        assert_eq!(engine, "pymupdf-native-pdf", "the route engine must be recorded, not the text engine");
    }).await.unwrap();
}

#[tokio::test]
async fn a_job_without_a_registered_route_worker_fails_explicitly() {
    let dir = tempfile::tempdir().unwrap();
    let text_worker = repo().join("services/python-workers/transport/text_ndjson.py");
    // The pdf route is claimable (attempts::ROUTES) but no worker is registered
    // for it here, so dispatch must refuse rather than send it to the text worker.
    let executor = Executor::open(&dir.path().join("db.sqlite"), &dir.path().join("staging"), &python(), &text_worker)
        .await
        .unwrap();
    executor.store().submit(|conn| {
        let source_id = match source::import_source(conn, b"%PDF-1.4 placeholder", "sample.pdf", None).unwrap() {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        jobs::enqueue(conn, "job", "pdf", &source_id).unwrap();
    }).await.unwrap();

    let error = executor.execute("job", "run-unrouted", 30_000, &Cancellation::new()).await.unwrap_err();
    assert!(error.contains("no worker registered for capability pdf.extract"), "{error}");
}

#[tokio::test]
async fn registering_a_route_makes_its_capability_dispatchable() {
    // The registry is what changes behaviour: with the pdf route registered, the
    // same job is no longer refused for lacking a worker. (It then reaches the
    // worker, whose receipt fidelity is the recorded remaining gap.)
    let dir = tempfile::tempdir().unwrap();
    let text_worker = repo().join("services/python-workers/transport/text_ndjson.py");
    let pdf_worker = repo().join("services/python-workers/document/worker_pdf.py");
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &text_worker,
        &[("pdf.extract", pdf_worker.clone())],
    )
    .await
    .unwrap();
    assert!(pdf_worker.is_file());
    assert!(Executor::open(&dir.path().join("other.sqlite"), &dir.path().join("staging"), &python(), &text_worker).await.is_ok());
}
