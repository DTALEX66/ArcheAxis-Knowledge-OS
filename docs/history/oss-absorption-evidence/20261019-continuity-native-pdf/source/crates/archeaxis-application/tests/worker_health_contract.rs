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
            .provider_health(capability, &worker(relative), capability == "pdf.extract")
            .await;
        assert_eq!(
            health["status"], "handshake_ready",
            "{capability}: {health}"
        );
        assert_eq!(health["task_executed"], false);
        assert_eq!(std::fs::read_dir(&staging).unwrap().count(), 0);
    }
}

#[tokio::test]
async fn pdf_health_observes_actual_dependency_without_a_document() {
    let dir = tempfile::tempdir().unwrap();
    let executor = Executor::open(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python(),
        &worker("transport/text_ndjson.py"),
    )
    .await
    .unwrap();
    let pdf = worker("document/worker_pdf.py");
    let missing = executor.provider_health("pdf.extract", &pdf, false).await;
    assert_eq!(missing["status"], "dependency_missing", "{missing}");
    assert_eq!(missing["reason"], "PDF_DEPENDENCY_MISSING");
    let observed = executor.provider_health("pdf.extract", &pdf, true).await;
    assert_eq!(observed["status"], "handshake_ready", "{observed}");
    assert_eq!(observed["runtime_dependency"]["status"], "AVAILABLE");
    assert_ne!(observed["runtime_dependency"]["version"], "pymupdf");
    assert_eq!(observed["task_executed"], false);
    assert_eq!(
        std::fs::read_dir(dir.path().join("staging"))
            .unwrap()
            .count(),
        0
    );
    let jobs: i64 = executor
        .store()
        .submit_wait(|c| c.query_row("SELECT COUNT(*) FROM jobs", [], |r| r.get(0)))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(jobs, 0);
}

#[tokio::test]
async fn pdf_dependency_rejection_sends_no_request_and_persists_failed_attempt() {
    use archeaxis_application::{executor::Cancellation, jobs};
    use archeaxis_domain::source::{self, ImportOutcome};
    for status in ["MISSING", "VERSION_UNKNOWN", "IMPORT_FAILED", "UNOBSERVED"] {
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("pdf.py");
        let observation = if status == "UNOBSERVED" {
            String::new()
        } else {
            format!(",'runtime_dependency':{{'name':'pymupdf','status':'{status}','version':None}}")
        };
        std::fs::write(&script, format!(r#"import json,pathlib,sys
print(json.dumps({{'schema':'archeaxis.worker-hello/v1','type':'hello',
'protocol':{{'major':1,'min_minor':0,'max_minor':0}},'worker':{{'name':'python-worker-pdf-ndjson','version':'1'}},
'capabilities':['pdf.extract'],'schemas':['archeaxis.text/v1','archeaxis.document-structure/v1','archeaxis.loss-receipt/v1']{observation}}}),flush=True)
if sys.stdin.buffer.read(): pathlib.Path(__file__).with_suffix('.leaked').touch()
"#)).unwrap();
        let executor = Executor::open_routes(
            &dir.path().join("db"),
            &dir.path().join("staging"),
            &python(),
            &script,
            &[("pdf.extract", script.clone())],
        )
        .await
        .unwrap();
        executor
            .store()
            .submit_wait(|c| {
                let source =
                    match source::import_source(c, b"%PDF-controlled", "controlled.pdf", None)
                        .unwrap()
                    {
                        ImportOutcome::Imported { source_id, .. }
                        | ImportOutcome::Duplicate { source_id, .. } => source_id,
                    };
                jobs::enqueue(c, "pdf-job", "pdf", &source).unwrap();
            })
            .await
            .unwrap();
        let error = executor
            .execute("pdf-job", "run", 5000, &Cancellation::new())
            .await
            .unwrap_err();
        assert!(
            error.contains(&format!("PDF_DEPENDENCY_{status}")),
            "{error}"
        );
        assert!(
            !script.with_extension("leaked").exists(),
            "Core must reject before writing request contents"
        );
        executor
            .store()
            .submit_wait(|c| {
                assert_eq!(
                    jobs::job_state(c, "pdf-job").unwrap().as_deref(),
                    Some("failed")
                );
                let outputs: i64 = c
                    .query_row("SELECT COUNT(*) FROM job_outputs", [], |r| r.get(0))
                    .unwrap();
                assert_eq!(outputs, 0);
                let attempts: i64 = c
                    .query_row(
                        "SELECT COUNT(*) FROM job_attempts WHERE state='failed'",
                        [],
                        |r| r.get(0),
                    )
                    .unwrap();
                assert_eq!(attempts, 1);
            })
            .await
            .unwrap();
    }
}

#[tokio::test]
async fn pdf_file_receipt_must_match_the_same_process_hello_version() {
    use archeaxis_application::{executor::Cancellation, jobs};
    use archeaxis_domain::source::{self, ImportOutcome};
    let d = tempfile::tempdir().unwrap();
    let pdf = std::process::Command::new(python()).args(["-B","-c","import pymupdf,sys;d=pymupdf.open();d.new_page().insert_text((72,100),'runtime version identity');sys.stdout.buffer.write(d.tobytes())"]).output().unwrap();
    assert!(pdf.status.success());
    let script = d.path().join("mismatch.py");
    std::fs::write(
        &script,
        format!(
            r#"import importlib.util,sys
spec=importlib.util.spec_from_file_location('pdf_wrapper',{})
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
real=m._runtime_dependency
def wrong_hello():
    engine,observed=real()
    return engine,{{**observed,'version':'9.99.99'}}
m._runtime_dependency=wrong_hello
sys.exit(m.main())
"#,
            serde_json::to_string(&worker("document/worker_pdf.py").to_str().unwrap()).unwrap()
        ),
    )
    .unwrap();
    let e = Executor::open_routes(
        &d.path().join("db"),
        &d.path().join("staging"),
        &python(),
        &script,
        &[("pdf.extract", script.clone())],
    )
    .await
    .unwrap();
    e.store()
        .submit_wait(move |c| {
            let source =
                match source::import_source(c, &pdf.stdout, "controlled.pdf", None).unwrap() {
                    ImportOutcome::Imported { source_id, .. }
                    | ImportOutcome::Duplicate { source_id, .. } => source_id,
                };
            jobs::enqueue(c, "job", "pdf", &source).unwrap();
        })
        .await
        .unwrap();
    let error = e
        .execute("job", "mismatch", 10000, &Cancellation::new())
        .await
        .unwrap_err();
    assert!(
        error.contains("PDF_RUNTIME_RECEIPT_IDENTITY_MISMATCH"),
        "{error}"
    );
    let outputs: i64 = e
        .store()
        .submit_wait(|c| c.query_row("SELECT COUNT(*) FROM job_outputs", [], |r| r.get(0)))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(outputs, 0);
}
