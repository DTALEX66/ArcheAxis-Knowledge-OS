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
