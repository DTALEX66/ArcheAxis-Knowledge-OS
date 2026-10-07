//! F10: the diarization route is reachable from a Core job, and its refusal stays a refusal.
//!
//! The route was declared and Core-registered before this suite existed, which is exactly the
//! failure shape this file pins: a job kind that resolves, a capability that is claimed, and no
//! process able to answer it. The refusal scenario pins its own supply (a wrapper that clears the
//! model-library environment before exec'ing the real worker), so the honest outcome is a failed job
//! naming the artefacts on any host - never a succeeded job with no segments,
//! which downstream would read as "this recording had no speakers".

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

#[test]
fn the_diarization_route_is_declared_and_dispatchable() {
    assert_eq!(
        attempts::route_for_kind("diarize").map(|route| route.0),
        Some("media.diarize")
    );
    let manifest: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string(repo().join("services/python-workers/routes.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(
        manifest["routes"]["media.diarize"],
        serde_json::json!(["media/worker_diarize.py"])
    );
    let transport =
        std::fs::read_to_string(repo().join("services/python-workers/transport/text_ndjson.py"))
            .unwrap();
    assert!(
        transport.contains("\"media.diarize\": {"),
        "the Core can enqueue the kind, but only this table can answer it"
    );
}

#[tokio::test]
async fn a_diarize_job_without_its_models_fails_naming_the_exact_artefacts() {
    let dir = tempfile::tempdir().unwrap();
    // This scenario is about supply, so it pins supply instead of borrowing the host's. A machine
    // that has the declared diarization assets must not turn "absent models refuse" into a success,
    // and a machine without them must not be the only place the refusal is real.
    let worker = dir.path().join("diarize_worker_with_supply_pinned_absent.py");
    let real_worker = repo()
        .join("services/python-workers/media/worker_diarize.py")
        .display()
        .to_string();
    std::fs::write(
        &worker,
        format!(
            "import os, runpy\n\
             for _name in ('ARCHEAXIS_DIARIZATION_MODEL_DIR', 'ARCHEAXIS_MODEL_LIBRARY_DIR'):\n\
             \x20\x20\x20\x20os.environ[_name] = ''\n\
             runpy.run_path(r'{real_worker}', run_name='__main__')\n"
        ),
    )
    .unwrap();
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &repo().join("services/python-workers/transport/text_ndjson.py"),
        &[("media.diarize", worker.clone())],
    )
    .await
    .unwrap();

    // A real 16-bit mono WAV, so the refusal is about supply and not about the input.
    let payload =
        std::fs::read(repo().join("tests/fixtures/speech_16k_mono.wav")).unwrap_or_else(|_| {
            let mut wav = Vec::new();
            wav.extend_from_slice(b"RIFF\0\0\0\0WAVEfmt ");
            wav.extend_from_slice(&[0u8; 44]);
            wav
        });
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "room.wav", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-diarize", "diarize", &source_id).unwrap();
        })
        .await
        .unwrap();

    let outcome = executor
        .execute("job-diarize", "run-diarize", 300_000, &Cancellation::new())
        .await;
    let message = match outcome {
        // Reaching this branch is the assertion: an empty diarization and a missing model have to
        // be different answers, and only a failed job cannot be read as "no speakers".
        Ok(_) => panic!("a diarization with no models must not settle as success"),
        Err(error) => error.to_string(),
    };
    assert!(
        message.contains("segmentation-3.0.onnx") && message.contains("speaker-embedding.onnx"),
        "the refusal must name the artefacts it needs: {message}"
    );
}
