//! R08 step (d) part 2: the executor dispatches by the claimed request's
//! capability through a route registry, and a job whose capability has no
//! registered worker fails explicitly instead of being sent to the wrong process.
//!
//! Receipt fidelity is tested here too, because the Core rejects a receipt rather than
//! accepting a half-true one. The Core addresses an anchor by its span and by the **final**
//! path segment, taking any leading segment as a qualifier, so the final segment has to be
//! the line's global position. The PDF worker used a page-local counter there, which is
//! identical to the global one on a single-page document - so a single-page fixture passed
//! while a real multi-page PDF failed with
//! `invalid receipt: structure or coverage does not match projected text` even though every
//! span was correct. `a_multi_page_pdf_number_anchors_globally_not_per_page` pins that.

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

/// A two-page PDF whose pages have different line counts, so a page-local line counter
/// and a global one diverge from the second page onward.
fn multi_page_pdf_bytes() -> Vec<u8> {
    let script = "\
import fitz, sys
doc = fitz.open()
first = doc.new_page()
for index in range(6):
    first.insert_text((72, 100 + index * 18), f'page one line {index + 1}')
second = doc.new_page()
for index in range(3):
    second.insert_text((72, 100 + index * 18), f'page two line {index + 1}')
sys.stdout.buffer.write(doc.tobytes())
";
    match std::process::Command::new(python())
        .arg("-c")
        .arg(script)
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
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "sample.pdf", None).unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job", "pdf", &source_id).unwrap();
        })
        .await
        .unwrap();

    executor
        .execute("job", "run-pdf", 120_000, &Cancellation::new())
        .await
        .unwrap();

    executor
        .store()
        .submit(|conn| {
            assert_eq!(
                jobs::job_state(conn, "job").unwrap().as_deref(),
                Some("succeeded")
            );
            assert_eq!(
                conn.query_row("SELECT count(*) FROM job_attempts", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                1
            );
            assert_eq!(
                conn.query_row("SELECT count(*) FROM job_outputs", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                3
            );
            let text: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE kind='text'",
                    [],
                    |r| r.get(0),
                )
                .unwrap();
            assert!(
                text.contains("6371"),
                "the PDF text must be stored verbatim: {text}"
            );
            let request_json: String = conn
                .query_row(
                    "SELECT request_json FROM job_attempts WHERE job_id='job'",
                    [],
                    |r| r.get(0),
                )
                .unwrap();
            assert!(
                request_json.contains("\"capability\":\"pdf.extract\""),
                "{request_json}"
            );
            assert!(request_json.contains("application/pdf"), "{request_json}");
            let engine: String = conn
                .query_row("SELECT engine FROM jobs WHERE job_id='job'", [], |r| {
                    r.get(0)
                })
                .unwrap();
            assert_eq!(
                engine, "pymupdf-native-pdf",
                "the route engine must be recorded, not the text engine"
            );
        })
        .await
        .unwrap();
}

#[tokio::test]
async fn a_job_without_a_registered_route_worker_fails_explicitly() {
    let dir = tempfile::tempdir().unwrap();
    let text_worker = repo().join("services/python-workers/transport/text_ndjson.py");
    // The pdf route is claimable (attempts::ROUTES) but no worker is registered
    // for it here, so dispatch must refuse rather than send it to the text worker.
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &text_worker,
    )
    .await
    .unwrap();
    executor
        .store()
        .submit(|conn| {
            let source_id =
                match source::import_source(conn, b"%PDF-1.4 placeholder", "sample.pdf", None)
                    .unwrap()
                {
                    ImportOutcome::Imported { source_id, .. } => source_id,
                    ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
            jobs::enqueue(conn, "job", "pdf", &source_id).unwrap();
        })
        .await
        .unwrap();

    let error = executor
        .execute("job", "run-unrouted", 30_000, &Cancellation::new())
        .await
        .unwrap_err();
    assert!(
        error.contains("no worker registered for capability pdf.extract"),
        "{error}"
    );
}

#[tokio::test]
async fn registering_a_route_makes_its_capability_dispatchable() {
    // The registry is what changes behaviour: with the pdf route registered, the
    // same job is no longer refused for lacking a worker. (It then reaches the
    // worker, whose receipt fidelity is covered by the multi-page test below.)
    let dir = tempfile::tempdir().unwrap();
    let text_worker = repo().join("services/python-workers/transport/text_ndjson.py");
    let pdf_worker = repo().join("services/python-workers/document/worker_pdf.py");
    let _executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &text_worker,
        &[("pdf.extract", pdf_worker.clone())],
    )
    .await
    .unwrap();
    assert!(pdf_worker.is_file());
    assert!(
        Executor::open(
            &dir.path().join("other.sqlite"),
            &dir.path().join("staging"),
            &python(),
            &text_worker
        )
        .await
        .is_ok()
    );
}

/// The anchor's final path segment must be the line's global position.
///
/// A page-local counter in that position makes the second page onwards fail the Core's
/// span check even when every `char_start`/`char_end` is correct, because the Core
/// compares the final segment against the projected line number. A single-page PDF has
/// page-local == global, which is why the single-page fixtures never caught this.
#[tokio::test]
async fn a_multi_page_pdf_number_anchors_globally_not_per_page() {
    let pdf = multi_page_pdf_bytes();
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
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "multi.pdf", None).unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "multi", "pdf", &source_id).unwrap();
        })
        .await
        .unwrap();

    executor
        .execute("multi", "run-multi", 120_000, &Cancellation::new())
        .await
        .unwrap();

    executor
        .store()
        .submit(|conn| {
            assert_eq!(
                jobs::job_state(conn, "multi").unwrap().as_deref(),
                Some("succeeded"),
                "a multi-page receipt must satisfy the Core's span check"
            );
            let structure: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE kind='document_structure'",
                    [],
                    |r| r.get(0),
                )
                .unwrap();
            let lines: Vec<serde_json::Value> = serde_json::from_str(&structure).unwrap();
            assert!(
                !lines.is_empty(),
                "the receipt must carry anchors: {structure}"
            );
            for (index, line) in lines.iter().enumerate() {
                let path = line.get("path").and_then(|p| p.as_array()).unwrap();
                let last = path.last().and_then(|s| s.as_str()).unwrap();
                assert_eq!(
                    last,
                    format!("line-{}", index + 1),
                    "anchor {index} must name its global line, got {path:?}"
                );
                assert!(
                    path.first()
                        .and_then(|s| s.as_str())
                        .unwrap()
                        .starts_with("page-"),
                    "the page must stay a qualifier: {path:?}"
                );
            }
        })
        .await
        .unwrap();
}
