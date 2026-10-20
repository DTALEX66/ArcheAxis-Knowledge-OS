use archeaxis_application::executor::Executor;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::{Duration, Instant},
};

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("canonical Python required")
        .into()
}
fn hello() -> Value {
    json!({"schema":"archeaxis.public-research-worker-hello/v1","version":1,
    "worker":"python-worker-machine-answer-ndjson","capability":"research.public",
    "protocol":"public-research-worker/v1","task_executed":false,"network_performed":false,"model_executed":false})
}
async fn fixture(script: &str) -> (tempfile::TempDir, Executor, PathBuf) {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("health.py");
    std::fs::write(&worker, script).unwrap();
    let ex = Executor::open(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &python(),
        &worker,
    )
    .await
    .unwrap();
    (dir, ex, worker)
}
fn script(value: &Value) -> String {
    format!(
        "import sys,os\nassert sys.argv[1:]==['--public-research-hello']\nassert sys.stdin.buffer.read()==b''\nassert 'ARCHEAXIS_PUBLIC_RESEARCH_PROXY' not in os.environ\nprint({:?})\n",
        value.to_string()
    )
}

#[tokio::test]
async fn real_public_research_health_is_input_free_without_a_job_or_provider_claim() {
    let worker = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/machine/worker_machine_answer.py")
        .canonicalize()
        .unwrap();
    let (dir, ex, _) = fixture("raise AssertionError('unused text route')").await;
    let health = ex.provider_health("research.public", &worker, true).await;
    assert_eq!(health["status"], "handshake_ready", "{health}");
    assert_eq!(
        health["worker_identity"],
        "python-worker-machine-answer-ndjson"
    );
    assert_eq!(
        health["protocol"],
        "archeaxis.public-research-worker-hello/v1"
    );
    assert_eq!(health["task_executed"], false);
    assert!(health["runtime_dependency"].is_null());
    assert_eq!(
        std::fs::read_dir(dir.path().join("staging"))
            .unwrap()
            .count(),
        0
    );
    let jobs: i64 = ex
        .store()
        .submit_wait(|conn| conn.query_row("SELECT count(*) FROM jobs", [], |r| r.get(0)))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(jobs, 0);
}

#[tokio::test]
async fn strict_public_hello_accepts_only_the_fixed_identity_and_inactive_flags() {
    let (dir, ex, worker) = fixture(&script(&hello())).await;
    let health = ex.provider_health("research.public", &worker, false).await;
    assert_eq!(health["status"], "handshake_ready", "{health}");
    for (field, value) in [
        ("schema", json!("other")),
        ("worker", json!("unknown-worker")),
        ("capability", json!("machine.answer")),
        ("version", json!(2)),
        ("protocol", json!("NDJSON")),
        ("task_executed", json!(true)),
        ("network_performed", json!(true)),
        ("model_executed", json!(true)),
        ("version", json!("1")),
        ("unknown", json!("extra")),
    ] {
        let mut bad = hello();
        bad[field] = value;
        std::fs::write(&worker, script(&bad)).unwrap();
        let health = ex.provider_health("research.public", &worker, false).await;
        assert_eq!(health["status"], "handshake_failed", "{field}: {health}");
        assert_eq!(
            health["reason"], "public_research_invalid_hello",
            "{field}: {health}"
        );
    }
    assert_eq!(
        std::fs::read_dir(dir.path().join("staging"))
            .unwrap()
            .count(),
        0
    );
}

#[tokio::test]
async fn hello_rejects_nonzero_exit_invalid_json_and_missing_modules() {
    let (_dir, ex, worker) = fixture(&(script(&hello()) + "raise SystemExit(2)\n")).await;
    let health = ex.provider_health("research.public", &worker, false).await;
    assert_eq!(health["status"], "handshake_failed");
    assert_eq!(health["reason"], "public_research_worker_exit_failed");
    std::fs::write(&worker, "print('invalid synthetic JSON')\n").unwrap();
    assert_eq!(
        ex.provider_health("research.public", &worker, false).await["reason"],
        "public_research_invalid_json"
    );
    let real = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/machine/worker_machine_answer.py");
    std::fs::copy(real, &worker).unwrap();
    let health = ex.provider_health("research.public", &worker, true).await;
    assert_eq!(
        health["status"], "handshake_failed",
        "missing public_research.py must not advertise readiness: {health}"
    );
    assert_eq!(health["reason"], "public_research_worker_exit_failed");
}

#[tokio::test]
async fn hello_bounds_output_and_reaps_hung_owned_worker() {
    let (dir, ex, worker) =
        fixture("import sys,time\nsys.stdout.write('x'*4097)\nsys.stdout.flush()\ntime.sleep(5)\n")
            .await;
    let start = Instant::now();
    assert_eq!(
        ex.provider_health("research.public", &worker, false).await["reason"],
        "public_research_output_exceeds_bound"
    );
    assert!(start.elapsed() < Duration::from_secs(3));
    std::fs::write(&worker, "import time\ntime.sleep(5)\nprint('{}')\n").unwrap();
    let start = Instant::now();
    assert_eq!(
        ex.provider_health("research.public", &worker, false).await["reason"],
        "public_research_timeout"
    );
    assert!(start.elapsed() < Duration::from_secs(4));
    assert_eq!(
        std::fs::read_dir(dir.path().join("staging"))
            .unwrap()
            .count(),
        0
    );
}
