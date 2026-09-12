//! R15/F15: a container reaches the store through its own route.
//!
//! A ZIP is binary, so this test also pins the honesty of the routing: the Core
//! derives `application/zip` from the name, dispatches the archive capability to its
//! own worker, and the inventory listing lands in the store with line anchors. The
//! negative cases matter as much: a `.zip` offered to the text route is refused, and a
//! corrupt container fails the job instead of succeeding with an empty inventory.

use archeaxis_application::{
    attempts,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON").expect("run cargo via the project wrapper").into()
}

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap()
}

/// Build a real ZIP through the same interpreter the worker uses.
fn zip_bytes() -> Vec<u8> {
    let script = "import io,sys,zipfile\n\
                  buf=io.BytesIO()\n\
                  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as c:\n\
                  \x20   c.writestr('notes/index.md','# Index\\nThe value is 6371 km.\\n')\n\
                  \x20   c.writestr('assets/',b'')\n\
                  \x20   c.writestr('data.csv','name,qty\\nbolt,4\\n')\n\
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
        &[("archive.inventory", repo().join("services/python-workers/document/worker_archive.py"))],
    )
    .await
    .unwrap()
}

#[test]
fn a_zip_name_selects_the_archive_route_and_never_the_text_route() {
    assert_eq!(attempts::resolve_media_type("archive", "bundle.zip").unwrap(), "application/zip");
    assert!(attempts::route_for_kind("archive").is_some());
    // a .zip cannot travel as text: no route may decode a container into text
    let error = attempts::resolve_media_type("text", "bundle.zip").unwrap_err().to_string();
    assert!(error.contains("cannot accept media type application/zip"), "{error}");
    // and the archive route will not take something that is not a container
    let error = attempts::resolve_media_type("archive", "notes.md").unwrap_err().to_string();
    assert!(error.contains("application/zip"), "{error}");
}

#[tokio::test]
async fn a_zip_job_is_dispatched_to_the_archive_worker_and_its_inventory_is_stored() {
    let container = zip_bytes();
    if container.is_empty() {
        eprintln!("skipping: zipfile unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let payload = container.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "bundle.zip", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-zip", "archive", &source_id).unwrap();
        })
        .await
        .unwrap();

    executor.execute("job-zip", "run-zip", 120_000, &Cancellation::new()).await.unwrap();

    let (state, text, receipt) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-zip").unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-zip') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            let receipt: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id='job-zip' AND kind='loss_report'",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text, receipt)
        })
        .await
        .unwrap();

    assert_eq!(state, "succeeded");
    assert!(text.contains("notes/index.md"), "the inventory must name the members: {text:?}");
    assert!(text.contains("data.csv"), "{text:?}");
    // the projection is the inventory, so the members' contents are NOT in the store text
    assert!(!text.contains("6371"), "a container projection must not contain member contents: {text:?}");
    assert!(receipt.contains("container inventory"), "{receipt}");
    assert!(receipt.contains("NOT the members' contents"), "{receipt}");
    // and the receipt carries the engine the route is allowed to report
    assert!(receipt.contains("python-worker-archive"), "{receipt}");
}

#[tokio::test]
async fn a_corrupt_container_fails_the_job_instead_of_succeeding_empty() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    executor
        .store()
        .submit(|conn| {
            let source_id = match source::import_source(conn, b"PK\x03\x04 not a container", "broken.zip", None).unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-broken", "archive", &source_id).unwrap();
        })
        .await
        .unwrap();

    let outcome = executor.execute("job-broken", "run-broken", 60_000, &Cancellation::new()).await;
    let state = executor
        .store()
        .submit(|conn| jobs::job_state(conn, "job-broken").unwrap().unwrap_or_default())
        .await
        .unwrap();
    assert!(outcome.is_err(), "a corrupt container must not report success");
    assert_eq!(state, "failed");
    let text_outputs: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM job_outputs WHERE job_id='job-broken' AND kind='text'",
                [],
                |row| row.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(text_outputs, 0, "no text artifact may exist for a container that failed");
}
