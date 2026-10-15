use archeaxis_application::executor::Executor;
use std::path::{Path, PathBuf};

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("run with the project wrapper and its declared Python")
        .into()
}

fn worker(relative: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers")
        .join(relative)
        .canonicalize()
        .unwrap()
}

#[tokio::test]
async fn real_video_health_hello_needs_no_job_or_media_engine() {
    let dir = tempfile::tempdir().unwrap();
    let staging = dir.path().join("staging");
    let video = worker("media/worker_video.py");
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &staging,
        &python(),
        &worker("transport/text_ndjson.py"),
    )
    .await
    .unwrap();
    let health = executor.provider_health("media.video", &video, false).await;
    assert_eq!(health["status"], "handshake_ready", "{health}");
    assert_eq!(health["worker_identity"], "python-worker-video-ndjson");
    assert_eq!(health["task_executed"], false);
    assert_eq!(health["protocol"], "NDJSON");
    assert_eq!(std::fs::read_dir(&staging).unwrap().count(), 0);
    let jobs: i64 = executor
        .store()
        .submit_wait(|conn| conn.query_row("SELECT COUNT(*) FROM jobs", [], |row| row.get(0)))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(jobs, 0, "a health hello must never enqueue a job");
}

#[tokio::test]
async fn health_keeps_non_artifact_workers_staging_only_and_input_free() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("strict_worker.py");
    let marker = dir.path().join("eof_without_request");
    std::fs::write(
        &script,
        r#"import argparse, json, pathlib, sys
parser = argparse.ArgumentParser()
parser.add_argument('--staging-root', required=True)
args = parser.parse_args()
print(json.dumps({'schema':'archeaxis.worker-hello/v1','type':'hello',
 'protocol':{'major':1,'min_minor':0,'max_minor':0},
 'worker':{'name':'python-worker-text-ndjson','version':'1'},
 'capabilities':['image.ocr'],
 'schemas':['archeaxis.text/v1','archeaxis.document-structure/v1','archeaxis.loss-receipt/v1']}), flush=True)
assert sys.stdin.buffer.read() == b''
pathlib.Path(__file__).with_name('eof_without_request').touch()
"#,
    )
    .unwrap();
    let staging = dir.path().join("staging");
    let executor = Executor::open(&dir.path().join("db"), &staging, &python(), &script)
        .await
        .unwrap();
    let health = executor.provider_health("image.ocr", &script, false).await;
    assert_eq!(health["status"], "handshake_ready", "{health}");
    assert_eq!(health["task_executed"], false);
    assert!(
        marker.is_file(),
        "worker must see EOF without request bytes"
    );
    assert_eq!(std::fs::read_dir(&staging).unwrap().count(), 0);
}

#[tokio::test]
async fn real_artifact_worker_health_hellos_remain_compatible() {
    let dir = tempfile::tempdir().unwrap();
    let staging = dir.path().join("staging");
    let text = worker("transport/text_ndjson.py");
    let executor = Executor::open(&dir.path().join("db"), &staging, &python(), &text)
        .await
        .unwrap();
    for (capability, relative) in [
        ("text.extract", "transport/text_ndjson.py"),
        ("pdf.extract", "document/worker_pdf.py"),
        ("archive.inventory", "document/worker_archive.py"),
        ("office.structure", "document/worker_office.py"),
    ] {
        let health = executor
            .provider_health(capability, &worker(relative), false)
            .await;
        assert_eq!(
            health["status"], "handshake_ready",
            "{capability}: {health}"
        );
        assert_eq!(health["task_executed"], false);
        assert_eq!(std::fs::read_dir(&staging).unwrap().count(), 0);
    }
}
