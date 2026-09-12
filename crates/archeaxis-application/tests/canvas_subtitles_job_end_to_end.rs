//! R15/F12: the canvas and subtitle workers reach the store through their own routes.
//!
//! Both workers existed in this repository since the 2026-09-05 slice with no route
//! pointing at them, so their real structure (node anchors carrying ids; cue anchors
//! carrying timings) was unreachable through the job contract. This suite covers the
//! wiring, and it pins the duplication being resolved: a `.srt` now declares its own
//! media type, so it can no longer reach the text route and the dedicated worker is the
//! one answer for a subtitle file.

use archeaxis_application::{
    attempts,
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::source::{self, ImportOutcome};
use std::path::PathBuf;

const CANVAS: &str = r#"{"nodes":[{"id":"n-1","type":"text","text":"measured 6371 km"},{"id":"n-2","type":"file","file":"notes/atomic.md"}],"edges":[{"id":"e-1","fromNode":"n-1","toNode":"n-2"}]}"#;
const SRT: &str = "1\n00:00:01,000 --> 00:00:04,000\nThe measured value is 6371 km.\n\n2\n00:00:05,500 --> 00:00:07,000\nSecond cue.\n";

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
        &[
            ("canvas.structure", repo().join("services/python-workers/document/worker_canvas.py")),
            ("subtitles.structure", repo().join("services/python-workers/document/worker_subtitles.py")),
        ],
    )
    .await
    .unwrap()
}

async fn run_job(executor: &Executor, job_id: &str, kind: &str, name: &str, payload: Vec<u8>) {
    let owned_job = job_id.to_string();
    let owned_name = name.to_string();
    let owned_kind = kind.to_string();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, &owned_name, None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, &owned_job, &owned_kind, &source_id).unwrap();
        })
        .await
        .unwrap();
    executor.execute(job_id, "run", 120_000, &Cancellation::new()).await.unwrap();
}

async fn stored_text(executor: &Executor, job_id: &str) -> (String, String, String) {
    let owned = job_id.to_string();
    executor
        .store()
        .submit(move |conn| {
            let state = jobs::job_state(conn, &owned).unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id=?1) ORDER BY transform_id DESC LIMIT 1",
                    [&owned],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            let receipt: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id=?1 AND kind='loss_report'",
                    [&owned],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text, receipt)
        })
        .await
        .unwrap()
}

#[test]
fn canvas_and_subtitle_names_select_their_own_routes() {
    assert_eq!(attempts::resolve_media_type("canvas", "board.canvas").unwrap(), "application/json");
    assert_eq!(attempts::resolve_media_type("subtitles", "talk.srt").unwrap(), "application/x-subrip");
    assert_eq!(attempts::resolve_media_type("subtitles", "talk.vtt").unwrap(), "text/vtt");
    // a subtitle is no longer declared as plain text, so the text route cannot take it
    let error = attempts::resolve_media_type("text", "talk.srt").unwrap_err().to_string();
    assert!(error.contains("cannot accept media type application/x-subrip"), "{error}");
    // and the subtitle route will not take a plain text file
    let error = attempts::resolve_media_type("subtitles", "notes.txt").unwrap_err().to_string();
    assert!(error.contains("application/x-subrip"), "{error}");
}

#[tokio::test]
async fn a_canvas_job_stores_its_node_structure_and_its_edges() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    run_job(&executor, "job-canvas", "canvas", "board.canvas", CANVAS.as_bytes().to_vec()).await;
    let (state, text, receipt) = stored_text(&executor, "job-canvas").await;

    assert_eq!(state, "succeeded");
    // the worker projects the text nodes, so a canvas is no longer custody-only
    assert!(text.contains("measured 6371 km"), "{text:?}");
    assert!(receipt.contains("python-worker-canvas"), "{receipt}");
    // the worker's own node anchors are kept as a fact, with the node ids in them
    assert!(receipt.contains("worker_structure"), "{receipt}");
    assert!(receipt.contains("n-1"), "the node anchor must carry its id: {receipt}");
    assert!(receipt.contains("text_node"), "{receipt}");
    // and the edges the worker preserved are in the receipt too
    assert!(receipt.contains("e-1"), "{receipt}");
}

#[tokio::test]
async fn a_subtitle_job_stores_its_cue_structure_with_timings() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    run_job(&executor, "job-srt", "subtitles", "talk.srt", SRT.as_bytes().to_vec()).await;
    let (state, text, receipt) = stored_text(&executor, "job-srt").await;

    assert_eq!(state, "succeeded");
    assert!(text.contains("The measured value is 6371 km."), "{text:?}");
    assert!(text.contains("Second cue."), "{text:?}");
    assert!(receipt.contains("python-worker-subtitles"), "{receipt}");
    // the cue anchors carry real timings, which is what makes this more than a text read
    assert!(receipt.contains("cue-"), "{receipt}");
    assert!(receipt.contains("offset_ms"), "{receipt}");
    assert!(receipt.contains("duration_ms"), "{receipt}");
}

#[tokio::test]
async fn a_subtitle_file_the_worker_cannot_parse_fails_the_job() {
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let broken = b"not a subtitle file at all\n".to_vec();
    let owned_job = "job-bad-srt".to_string();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &broken, "broken.srt", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, &owned_job, "subtitles", &source_id).unwrap();
        })
        .await
        .unwrap();
    let outcome = executor.execute("job-bad-srt", "run", 60_000, &Cancellation::new()).await;
    let (state, _, _) = stored_text(&executor, "job-bad-srt").await;
    assert!(outcome.is_err(), "a malformed subtitle file must not report success");
    assert_eq!(state, "failed");
}
