//! New request-scoped transport checks with synthetic private Python workers only.
//! No model endpoint, provider service, user material or older experiment is invoked.
use archeaxis_application::executor::{Cancellation, Executor};
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::{Duration, Instant},
};

struct Fixture {
    dir: tempfile::TempDir,
    staging: PathBuf,
    executor: Executor,
}

impl Fixture {
    async fn new() -> Self {
        let dir = tempfile::tempdir().unwrap();
        let staging = dir.path().join("staging");
        let python = std::env::var_os("ARCHEAXIS_PYTHON")
            .map(PathBuf::from)
            .expect(
                "new process tests require the dev.py-owned interpreter; absence is not a pass",
            );
        assert!(python.is_file());
        let worker = dir.path().join("synthetic_local_model.py");
        std::fs::write(&worker, "import json, pathlib, sys, time\nr=json.load(sys.stdin)\nif r.get('ready'): pathlib.Path(r['ready']).write_text('ready')\ntime.sleep(r.get('pause',0))\nif r.get('finished'): pathlib.Path(r['finished']).write_text('finished')\nprint(json.dumps({'status':'SYNTHETIC_REPLY'}),flush=True)\n").unwrap();
        let executor = Executor::open_routes(
            &dir.path().join("workspace.sqlite"),
            &staging,
            &python,
            &dir.path().join("unused-default-worker"),
            &[("course.openmaic.outline-model", worker)],
        )
        .await
        .unwrap();
        Self {
            dir,
            staging,
            executor,
        }
    }
    fn request(&self, name: &str, pause: f64) -> Value {
        json!({"ready":self.dir.path().join(format!("{name}-ready")),
            "finished":self.dir.path().join(format!("{name}-finished")),"pause":pause})
    }
    async fn entered(&self, name: &str) {
        wait_for(|| self.dir.path().join(format!("{name}-ready")).is_file()).await;
    }
    async fn cleaned(&self) {
        wait_for(|| empty(&self.staging)).await;
    }
}

fn empty(path: &Path) -> bool {
    std::fs::read_dir(path).unwrap().next().is_none()
}

async fn wait_for(condition: impl Fn() -> bool) {
    tokio::time::timeout(Duration::from_secs(5), async {
        while !condition() {
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .expect("owned worker condition must become observable within its bound");
}

#[tokio::test]
async fn local_model_cancel_pre_cancelled_request_never_spawns() {
    let fixture = Fixture::new().await;
    let cancel = Cancellation::new();
    cancel.cancel();
    let result = fixture
        .executor
        .local_model_json_cancellable(
            fixture.request("pre", 60.0),
            Duration::from_secs(30),
            cancel,
        )
        .await;
    assert_eq!(result.unwrap_err(), "local model request cancelled");
    assert!(!fixture.dir.path().join("pre-ready").exists());
    assert!(empty(&fixture.staging));
}

#[tokio::test]
async fn local_model_cancel_normal_completion_preserves_the_request_token() {
    let fixture = Fixture::new().await;
    let cancel = Cancellation::new();
    let result = fixture
        .executor
        .local_model_json_cancellable(
            fixture.request("normal", 0.0),
            Duration::from_secs(10),
            cancel.clone(),
        )
        .await
        .unwrap();
    assert_eq!(result["exit_code"], 0);
    assert_eq!(result["document"]["status"], "SYNTHETIC_REPLY");
    assert!(
        !cancel.is_cancelled(),
        "normal model completion must not cancel the later replay stage"
    );
    assert!(empty(&fixture.staging));
}

#[tokio::test]
async fn local_model_cancel_stops_only_its_owned_worker_and_keeps_other_request_running() {
    let fixture = Fixture::new().await;
    let cancel = Cancellation::new();
    let survivor = Cancellation::new();
    let first = {
        let executor = fixture.executor.clone();
        let token = cancel.clone();
        let request = fixture.request("cancel", 60.0);
        tokio::spawn(async move {
            executor
                .local_model_json_cancellable(request, Duration::from_secs(30), token)
                .await
        })
    };
    let other = {
        let executor = fixture.executor.clone();
        let token = survivor.clone();
        let request = fixture.request("survivor", 0.8);
        tokio::spawn(async move {
            executor
                .local_model_json_cancellable(request, Duration::from_secs(10), token)
                .await
        })
    };
    fixture.entered("cancel").await;
    fixture.entered("survivor").await;
    let started = Instant::now();
    cancel.cancel();
    assert_eq!(
        tokio::time::timeout(Duration::from_secs(4), first)
            .await
            .unwrap()
            .unwrap()
            .unwrap_err(),
        "local model request cancelled"
    );
    assert!(started.elapsed() < Duration::from_secs(4));
    assert_eq!(
        other.await.unwrap().unwrap()["document"]["status"],
        "SYNTHETIC_REPLY"
    );
    assert!(!survivor.is_cancelled());
    assert!(!fixture.dir.path().join("cancel-finished").exists());
    assert!(fixture.dir.path().join("survivor-finished").exists());
    fixture.cleaned().await;
}

#[tokio::test]
async fn local_model_cancel_deadline_bounds_the_owned_worker_cleanup() {
    let fixture = Fixture::new().await;
    let started = Instant::now();
    let result = fixture
        .executor
        .local_model_json_cancellable(
            fixture.request("deadline", 60.0),
            Duration::from_millis(500),
            Cancellation::new(),
        )
        .await;
    assert!(result.unwrap_err().contains("timed out"));
    assert!(started.elapsed() < Duration::from_secs(4));
    assert!(!fixture.dir.path().join("deadline-finished").exists());
    fixture.cleaned().await;
}

#[tokio::test]
async fn local_model_cancel_dropping_future_cancels_transport_and_prevents_late_completion() {
    let fixture = Fixture::new().await;
    let cancel = Cancellation::new();
    let running = {
        let executor = fixture.executor.clone();
        let token = cancel.clone();
        let request = fixture.request("drop", 60.0);
        tokio::spawn(async move {
            executor
                .local_model_json_cancellable(request, Duration::from_secs(30), token)
                .await
        })
    };
    fixture.entered("drop").await;
    running.abort();
    assert!(running.await.unwrap_err().is_cancelled());
    assert!(cancel.is_cancelled());
    fixture.cleaned().await;
    assert!(!fixture.dir.path().join("drop-finished").exists());
}

#[tokio::test]
async fn local_model_cancel_while_all_process_slots_are_busy_never_dispatches_queued_request() {
    let fixture = Fixture::new().await;
    let mut owners = Vec::new();
    for index in 0..4 {
        let name = format!("slot_{index}");
        let cancel = Cancellation::new();
        let executor = fixture.executor.clone();
        let token = cancel.clone();
        let request = fixture.request(&name, 60.0);
        let task = tokio::spawn(async move {
            executor
                .local_model_json_cancellable(request, Duration::from_secs(30), token)
                .await
        });
        owners.push((cancel, task));
        fixture.entered(&name).await;
    }
    let cancel = Cancellation::new();
    let executor = fixture.executor.clone();
    let token = cancel.clone();
    let request = fixture.request("queued", 60.0);
    let queued = tokio::spawn(async move {
        executor
            .local_model_json_cancellable(request, Duration::from_secs(30), token)
            .await
    });
    tokio::time::sleep(Duration::from_millis(50)).await;
    cancel.cancel();
    let result = tokio::time::timeout(Duration::from_secs(1), queued)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(result.unwrap_err(), "local model request cancelled");
    assert!(!fixture.dir.path().join("queued-ready").exists());
    for (cancel, _) in &owners {
        cancel.cancel();
    }
    for (_, task) in owners {
        assert_eq!(
            task.await.unwrap().unwrap_err(),
            "local model request cancelled"
        );
    }
    fixture.cleaned().await;
}

#[test]
fn local_model_cancel_while_blocking_pool_is_occupied_aborts_queued_work() {
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .max_blocking_threads(1)
        .build()
        .unwrap();
    runtime.block_on(async {
        let fixture = Fixture::new().await;
        let (release, held) = std::sync::mpsc::channel();
        struct Release(Option<std::sync::mpsc::Sender<()>>);
        impl Drop for Release {
            fn drop(&mut self) {
                if let Some(sender) = self.0.take() {
                    let _ = sender.send(());
                }
            }
        }
        let release = Release(Some(release));
        let (started, entered) = tokio::sync::oneshot::channel();
        let blocker = tokio::task::spawn_blocking(move || {
            let _ = started.send(());
            let _ = held.recv_timeout(Duration::from_secs(10));
        });
        entered.await.unwrap();
        let cancel = Cancellation::new();
        let executor = fixture.executor.clone();
        let token = cancel.clone();
        let request = fixture.request("pool", 60.0);
        let queued = tokio::spawn(async move {
            executor
                .local_model_json_cancellable(request, Duration::from_secs(30), token)
                .await
        });
        tokio::time::sleep(Duration::from_millis(50)).await;
        let cancelled_at = Instant::now();
        cancel.cancel();
        // Admission may still be awaiting its readonly Store check. In that
        // case cancellation is observed before a blocking job exists. If the
        // job is already queued, Tokio cannot finish its JoinHandle until the
        // pool dequeues it, so the three-second observation returns UNKNOWN.
        // This integration test makes no claim about which admission stage won.
        let outcome = tokio::time::timeout(Duration::from_secs(4), queued)
            .await
            .unwrap()
            .unwrap()
            .unwrap_err();
        assert!(matches!(
            outcome.as_str(),
            "local model request cancelled" | "local model worker cleanup unknown"
        ));
        assert!(cancelled_at.elapsed() < Duration::from_secs(4));
        assert!(!blocker.is_finished(), "the queue must still be occupied");
        assert!(!fixture.dir.path().join("pool-ready").exists());
        assert!(empty(&fixture.staging));
        drop(release);
        blocker.await.unwrap();
        // A FIFO pool fence observes the cancelled queued job after capacity
        // returns. It must never start a private worker or publish late output.
        tokio::task::spawn_blocking(|| ()).await.unwrap();
        assert!(!fixture.dir.path().join("pool-ready").exists());
        assert!(!fixture.dir.path().join("pool-finished").exists());
        fixture.cleaned().await;
    });
}
