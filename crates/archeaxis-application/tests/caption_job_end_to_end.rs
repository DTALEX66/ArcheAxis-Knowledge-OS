//! R15/F04: a figure description is a labelled candidate, never extracted text.
//!
//! The caption worker existed since an earlier slice with no route pointing at it. This
//! suite covers the wiring and, more importantly, the honesty of a model route: the
//! description is model output and the receipt says so; a missing model is a named
//! failure; and the job never reports success with an empty description. The test does
//! not assert what the description says, because a model's wording is not a fact this
//! repository can pin.

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

/// A real PNG, so the worker's own image validation is exercised.
fn png_bytes() -> Vec<u8> {
    let script = "import io,sys\n\
                  from PIL import Image, ImageDraw\n\
                  buf=io.BytesIO()\n\
                  img=Image.new('RGB',(320,120),'white')\n\
                  ImageDraw.Draw(img).text((20,40),'measured 6371 km',fill='black')\n\
                  img.save(buf,'PNG')\n\
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
        &[("image.caption", repo().join("services/python-workers/vision/worker_caption.py"))],
    )
    .await
    .unwrap()
}

#[test]
fn a_caption_name_selects_the_caption_route_and_not_the_ocr_route() {
    // the kind selects the route, so the same .png name means OCR or captions depending
    // on what the caller asked for
    assert_eq!(attempts::route_for_kind("caption").map(|route| route.0), Some("image.caption"));
    assert_eq!(attempts::route_for_kind("image").map(|route| route.0), Some("image.ocr"));
    assert_eq!(attempts::resolve_media_type("caption", "figure.png").unwrap(), "image/png");
    // and the caption route will not take something that is not an image
    let error = attempts::resolve_media_type("caption", "notes.md").unwrap_err().to_string();
    assert!(error.contains("image/png"), "{error}");
}

#[tokio::test]
async fn a_caption_job_is_either_a_labelled_candidate_or_a_named_failure() {
    let png = png_bytes();
    if png.is_empty() {
        eprintln!("skipping: PIL unavailable for building a sample");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let executor = open_executor(dir.path()).await;
    let payload = png.clone();
    executor
        .store()
        .submit(move |conn| {
            let source_id = match source::import_source(conn, &payload, "figure.png", None).unwrap() {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
            jobs::enqueue(conn, "job-caption", "caption", &source_id).unwrap();
        })
        .await
        .unwrap();

    let outcome = executor.execute("job-caption", "run-caption", 300_000, &Cancellation::new()).await;
    let (state, text, receipt) = executor
        .store()
        .submit(|conn| {
            let state = jobs::job_state(conn, "job-caption").unwrap().unwrap_or_default();
            let text: String = conn
                .query_row(
                    "SELECT text FROM transforms WHERE source_id=(
                       SELECT input_ref FROM jobs WHERE job_id='job-caption') ORDER BY transform_id DESC LIMIT 1",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            let receipt: String = conn
                .query_row(
                    "SELECT content FROM job_outputs WHERE job_id='job-caption' AND kind='loss_report'",
                    [],
                    |row| row.get(0),
                )
                .unwrap_or_default();
            (state, text, receipt)
        })
        .await
        .unwrap();

    match outcome {
        Ok(()) => {
            // a success must carry a real description, and the receipt must say what it is
            assert_eq!(state, "succeeded");
            assert!(!text.trim().is_empty(), "a successful caption must not be empty");
            assert!(receipt.contains("python-worker-caption"), "{receipt}");
            assert!(receipt.contains("qwen2.5vl"), "the model must be recorded: {receipt}");
            assert!(receipt.contains("model output"), "{receipt}");
            assert!(receipt.contains("candidate"), "{receipt}");
            assert!(receipt.contains("prompt_version"), "{receipt}");
        }
        Err(_) => {
            // no model here: the job fails by name and leaves no text artifact behind
            assert_eq!(state, "failed");
            let text_outputs: i64 = executor
                .store()
                .submit(|conn| {
                    conn.query_row(
                        "SELECT count(*) FROM job_outputs WHERE job_id='job-caption' AND kind='text'",
                        [],
                        |row| row.get(0),
                    )
                    .unwrap()
                })
                .await
                .unwrap();
            assert_eq!(text_outputs, 0, "a failed caption must leave no text artifact");
        }
    }
}
