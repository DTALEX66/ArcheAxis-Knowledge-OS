//! R08 step (d): an image/screenshot job is a first-class job too - its kind
//! selects the image.ocr route, the executor dispatches it to the OCR worker, and
//! the recognised text lands in the Core's job outputs like text and PDF jobs.

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
async fn ocr_job_is_dispatched_to_the_ocr_worker_and_its_text_is_stored() {
    // The sample is rendered by the same interpreter the worker uses.
    let sample_dir = tempfile::tempdir().unwrap();
    let sample = sample_dir.path().join("shot.png");
    let render = std::process::Command::new(python())
        .arg("-c")
        .arg("import sys;from PIL import Image,ImageDraw;i=Image.new('RGB',(460,110),'white');ImageDraw.Draw(i).text((20,40),'ocr job 6371',fill='black');i.save(sys.argv[1])")
        .arg(&sample)
        .output();
    match render {
        Ok(out) if out.status.success() => {}
        _ => {
            eprintln!("skipping: PIL unavailable for building a sample");
            return;
        }
    }
    let png = std::fs::read(&sample).unwrap();
    assert!(!png.is_empty());

    let dir = tempfile::tempdir().unwrap();
    let text_worker = repo().join("services/python-workers/transport/text_ndjson.py");
    let ocr_worker = repo().join("services/python-workers/vision/worker_ocr.py");
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python(),
        &text_worker,
        &[("image.ocr", ocr_worker)],
    )
    .await
    .unwrap();

    let payload = png.clone();
    executor.store().submit(move |conn| {
        let source_id = match source::import_source(conn, &payload, "shot.png", None).unwrap() {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        jobs::enqueue(conn, "job", "image", &source_id).unwrap();
    }).await.unwrap();

    executor.execute("job", "run-ocr", 180_000, &Cancellation::new()).await.unwrap();

    executor.store().submit(|conn| {
        assert_eq!(jobs::job_state(conn, "job").unwrap().as_deref(), Some("succeeded"));
        assert_eq!(conn.query_row("SELECT count(*) FROM job_outputs", [], |r| r.get::<_, i64>(0)).unwrap(), 3);
        let text: String = conn
            .query_row("SELECT content FROM job_outputs WHERE kind='text'", [], |r| r.get(0))
            .unwrap();
        assert!(!text.trim().is_empty(), "recognised text must be stored");
        let request_json: String = conn
            .query_row("SELECT request_json FROM job_attempts WHERE job_id='job'", [], |r| r.get(0))
            .unwrap();
        assert!(request_json.contains("\"capability\":\"image.ocr\""), "{request_json}");
        assert!(request_json.contains("image/png"), "{request_json}");
        let engine: String = conn
            .query_row("SELECT engine FROM jobs WHERE job_id='job'", [], |r| r.get(0))
            .unwrap();
        assert_eq!(engine, "python-worker-ocr", "the OCR route engine must be recorded");
        let structure: String = conn
            .query_row("SELECT content FROM job_outputs WHERE kind='document_structure'", [], |r| r.get(0))
            .unwrap();
        assert!(structure.contains("\"line-1\""), "structure must be canonical line anchors: {structure}");
    }).await.unwrap();
}
