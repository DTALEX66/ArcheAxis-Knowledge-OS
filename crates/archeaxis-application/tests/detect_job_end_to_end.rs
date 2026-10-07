//! F04: a source whose extension names nothing still gets an answer, from bytes not from a guess.
//!
//! The repository already carried the vendored Magika ONNX with its own committed tests, yet the
//! product path never consulted it: a file named `field_notes` was refused, and the absorbed donor
//! stayed a catalogue entry. This suite runs the real executor against the real worker, so what is
//! asserted is that the capability is reachable from a Core job - not merely declared.

use archeaxis_application::{
    attempts,
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
            "document.detect",
            repo().join("services/python-workers/document/worker_detect.py"),
        )],
    )
    .await
    .unwrap()
}

#[test]
fn the_detection_route_is_the_route_for_an_unnameable_name() {
    assert_eq!(
        attempts::route_for_kind("detect").map(|route| route.0),
        Some("document.detect")
    );
    // and it is the ONLY route that takes such a name: projection routes still refuse.
    assert!(attempts::resolve_media_type("text", "field_notes").is_err());
    assert_eq!(
        attempts::resolve_media_type("detect", "field_notes").unwrap(),
        "application/octet-stream"
    );
}

#[tokio::test]
async fn a_detect_job_answers_with_the_models_own_judgement_of_the_bytes() {
    // A real XLSX fixture handed over under a name that declares nothing.
    let payload = std::fs::read(repo().join("tests/fixtures/sample.xlsx")).expect("fixture");
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    executor
        .store()
        .submit(move |conn| {
            let source_id =
                match source::import_source(conn, &payload, "field_notes", None).unwrap() {
                    ImportOutcome::Imported { source_id, .. } => source_id,
                    ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
            jobs::enqueue(conn, "job-detect", "detect", &source_id).unwrap();
        })
        .await
        .unwrap();

    let outcome = executor
        .execute("job-detect", "run-detect", 300_000, &Cancellation::new())
        .await;
    assert!(outcome.is_ok(), "detection job failed: {outcome:?}");

    let (state, text) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-detect")
                .unwrap()
                .unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT t.text FROM transforms t
                     JOIN jobs j ON j.transform_id=t.transform_id
                     WHERE j.job_id='job-detect'",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text)
        })
        .await
        .unwrap();

    assert_eq!(state, "succeeded", "{state}");
    // The label is the model's, the bytes are the fixture's, and the name never entered the answer.
    assert!(
        text.starts_with("xlsx\toffice\t"),
        "the judgement should name the bytes it read: {text:?}"
    );
    assert!(
        !text.contains("field_notes"),
        "a detection must not smuggle the unusable name back in as a type: {text:?}"
    );
}
