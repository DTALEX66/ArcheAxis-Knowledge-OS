use archeaxis_application::{executor::Executor, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::{path::PathBuf, time::Duration};
use tower::ServiceExt;

// Candidate adds no arbitrary runtime route. The test-only wrapper stalls one owned text job
// after real handshake; the other job delegates to the canonical text transport unchanged.
async fn setup_mixed_owned_worker(dir: &std::path::Path) -> Executor {
    let transport = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let script = dir.join("mixed_owned_worker.py");
    let path_literal = serde_json::to_string(&transport.to_string_lossy()).unwrap();
    std::fs::write(&script, format!("import importlib.util,time\np={path_literal}\ns=importlib.util.spec_from_file_location('canonical_text',p)\nm=importlib.util.module_from_spec(s)\ns.loader.exec_module(m)\noriginal=m.execute\ndef controlled(request,*args,**kwargs):\n if request.get('job_id')=='other': time.sleep(30)\n return original(request,*args,**kwargs)\nm.execute=controlled\nraise SystemExit(m.main())\n")).unwrap();
    let executor = Executor::open(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap()),
        &script,
    )
    .await
    .unwrap();
    executor
        .store()
        .submit(|conn| {
            let source = match source::import_source(
                conn,
                b"owned checkpoint synthetic input",
                "fixture.txt",
                None,
            )
            .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            for id in ["job", "other", "third"] {
                jobs::enqueue(conn, id, "text", &source).unwrap();
            }
        })
        .await
        .unwrap();
    executor
}

async fn terminal_execution_status(router: &Router, job: &str, request: &str) -> serde_json::Value {
    tokio::time::timeout(Duration::from_secs(6), async {
        loop {
            let (code, value) = call(
                router,
                "GET",
                &format!("/api/v1/jobs/{job}/execution-status"),
                "",
                "",
            )
            .await;
            assert_eq!(code, 200);
            assert_eq!(value["job_id"], job);
            assert_eq!(value["request_id"], request);
            if ["succeeded", "failed", "cancelled", "rejected"]
                .contains(&value["state"].as_str().unwrap())
            {
                return value;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap()
}

#[tokio::test]
async fn bounded_status_reads_durable_budget_steps_commits_and_exact_replay() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup_mixed_owned_worker(dir.path()).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "explicit-1",
            r#"{"deadline_ms":5000,"split":false,"words":false}"#
        )
        .await
        .0,
        202
    );
    let status = terminal_execution_status(&router, "job", "explicit-1").await;
    assert_eq!(status["state"], "succeeded");
    let a = &status["attempts"][0];
    assert_eq!(a["budget"]["deadline_ms"], 5000);
    assert_eq!(a["steps"]["durable_claim"], "RECORDED");
    assert_eq!(a["steps"]["worker_response_commit"], "RECORDED");
    assert_eq!(a["checkpoint"]["status"], "CORE_COMMITTED");
    assert!(
        a["checkpoint"]["outputs"]
            .as_array()
            .unwrap()
            .iter()
            .any(|o| o["kind"] == "text")
    );
    assert_eq!(a["checkpoint"]["worker_cache_readback"], "NOT_OBSERVED");
    assert_eq!(a["continuation"]["resume_status"], "NOT_SUPPORTED");
    assert!(
        !status
            .to_string()
            .contains(&dir.path().to_string_lossy().to_string())
    );
    let replay = call(
        &router,
        "POST",
        "/api/v1/jobs/job/executions",
        "explicit-1",
        r#"{"deadline_ms":5000}"#,
    )
    .await;
    assert_eq!(replay.0, 202);
    assert_eq!(replay.1["replayed"], true);
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "explicit-1",
            r#"{"deadline_ms":5001}"#
        )
        .await
        .0,
        409
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions",
            "explicit-1",
            r#"{"deadline_ms":5000}"#
        )
        .await
        .0,
        409
    );
    let (old_code, legacy) = call(&router, "GET", "/api/v1/jobs/job", "", "").await;
    assert_eq!(old_code, 200);
    for key in [
        "job_id",
        "state",
        "attempt",
        "request_id",
        "input_ref",
        "error",
    ] {
        assert_eq!(legacy[key], status[key]);
    }
    executor
        .store()
        .submit(|conn| {
            assert_eq!(
                conn.query_row(
                    "SELECT count(*) FROM job_attempts WHERE job_id='job'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap(),
                1
            );
            assert_eq!(
                conn.query_row("SELECT count(*) FROM transforms", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                1
            );
        })
        .await
        .unwrap();
}

#[tokio::test]
async fn bounded_cancel_confirms_terminal_and_preserves_other_committed_outputs_and_history() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup_mixed_owned_worker(dir.path()).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "committed",
            r#"{"deadline_ms":5000}"#
        )
        .await
        .0,
        202
    );
    let before = terminal_execution_status(&router, "job", "committed").await;
    let (_, before_text) = call(&router, "GET", "/api/v1/jobs/job/outputs/text", "", "").await;
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions",
            "cancel-me",
            r#"{"deadline_ms":300000}"#
        )
        .await
        .0,
        202
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions/wrong/cancel",
            "",
            ""
        )
        .await
        .0,
        409
    );
    let cancel = call(
        &router,
        "POST",
        "/api/v1/jobs/other/executions/cancel-me/cancel",
        "",
        "",
    )
    .await;
    assert_eq!(cancel.0, 202);
    assert_eq!(cancel.1["cancel_requested"], true);
    assert!(
        cancel.1.get("state").is_none(),
        "202 must not masquerade as a terminal result"
    );
    let cancelled = terminal_execution_status(&router, "other", "cancel-me").await;
    assert_eq!(cancelled["state"], "cancelled");
    assert_eq!(
        cancelled["attempts"][0]["checkpoint"]["status"],
        "NOT_OBSERVED"
    );
    assert_eq!(
        cancelled["attempts"][0]["continuation"]["resume_status"],
        "NOT_SUPPORTED"
    );
    assert_eq!(
        cancelled["attempts"][0]["continuation"]["new_attempt_eligible_state"],
        true
    );
    assert_eq!(
        terminal_execution_status(&router, "job", "committed").await,
        before
    );
    assert_eq!(
        call(&router, "GET", "/api/v1/jobs/job/outputs/text", "", "")
            .await
            .1,
        before_text
    );
    let terminal_cancel = call(
        &router,
        "POST",
        "/api/v1/jobs/other/executions/cancel-me/cancel",
        "",
        "",
    )
    .await;
    assert_eq!(terminal_cancel.0, 200);
    assert_eq!(terminal_cancel.1["state"], "cancelled");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions",
            "cancel-me",
            r#"{"deadline_ms":300000}"#
        )
        .await
        .1["state"],
        "cancelled"
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions",
            "fresh-retry",
            r#"{"deadline_ms":100}"#
        )
        .await
        .0,
        202
    );
    let failed = terminal_execution_status(&router, "other", "fresh-retry").await;
    assert_eq!(failed["state"], "failed");
    assert_eq!(failed["attempts"][0]["attempt"], 2);
    assert_eq!(failed["attempts"][1]["request_id"], "cancel-me");
    assert_eq!(failed["attempts"][1]["state"], "cancelled");
    assert_eq!(failed["attempts"][0]["budget"]["deadline_ms"], 100);
}

#[tokio::test]
async fn bounded_job_scope_and_parameters_fail_before_any_claim() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup(dir.path(), true).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    for body in [
        r#"{"deadline_ms":0}"#,
        r#"{"deadline_ms":300001}"#,
        r#"{"deadline_ms":1.5}"#,
        r#"{"deadline_ms":1,"url":"http://invalid"}"#,
        r#"{"deadline_ms":1,"script":"unowned"}"#,
    ] {
        assert_eq!(
            call(
                &router,
                "POST",
                "/api/v1/jobs/job/executions",
                "bounded-negative",
                body
            )
            .await
            .0,
            422
        );
    }
    assert_eq!(
        call(
            &router,
            "GET",
            "/api/v1/jobs/missing/execution-status",
            "",
            ""
        )
        .await
        .0,
        404
    );
    let (_, status) = call(&router, "GET", "/api/v1/jobs/job/execution-status", "", "").await;
    let (_, listing) = call(
        &router,
        "GET",
        &format!(
            "/api/v1/sources/{}/jobs",
            status["input_ref"].as_str().unwrap()
        ),
        "",
        "",
    )
    .await;
    assert_eq!(listing["source_id"], status["input_ref"]);
    assert!(
        listing["jobs"]
            .as_array()
            .unwrap()
            .iter()
            .any(|row| row["job_id"] == "job" && row["input_ref"] == status["input_ref"])
    );
    executor
        .store()
        .submit(|conn| {
            assert_eq!(
                conn.query_row("SELECT count(*) FROM job_attempts", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                0
            );
            assert_eq!(
                conn.query_row("SELECT count(*) FROM transforms", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                0
            );
        })
        .await
        .unwrap();
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "minimum-budget",
            r#"{"deadline_ms":1}"#
        )
        .await
        .0,
        202
    );
    assert_eq!(
        terminal_execution_status(&router, "job", "minimum-budget").await["state"],
        "failed"
    );
}

async fn setup(dir: &std::path::Path, stalled: bool) -> Executor {
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = if stalled {
        let p = dir.join("stalled.py");
        std::fs::write(&p, "import time\ntime.sleep(30)\n").unwrap();
        p
    } else {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/python-workers/transport/text_ndjson.py")
    };
    let executor = Executor::open(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python,
        &script,
    )
    .await
    .unwrap();
    executor
        .store()
        .submit(|conn| {
            let id = match source::import_source(conn, "中😀\r\n".as_bytes(), "test.txt", None)
                .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            for job in ["job", "other", "third"] {
                jobs::enqueue(conn, job, "text", &id).unwrap();
            }
        })
        .await
        .unwrap();
    executor
}
async fn call(
    router: &Router,
    method: &str,
    path: &str,
    key: &str,
    body: &str,
) -> (u16, serde_json::Value) {
    let mut req = Request::builder()
        .method(method)
        .uri(path)
        .header("content-type", "application/json");
    if !key.is_empty() {
        req = req.header("idempotency-key", key);
    }
    let resp = router
        .clone()
        .oneshot(req.body(Body::from(body.to_owned())).unwrap())
        .await
        .unwrap();
    let status = resp.status().as_u16();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}
async fn terminal(router: &Router, job: &str) -> serde_json::Value {
    tokio::time::timeout(Duration::from_secs(6), async {
        loop {
            let (status, value) = call(router, "GET", &format!("/api/v1/jobs/{job}"), "", "").await;
            assert_eq!(status, 200);
            if value["state"] != "running" && value["state"] != "queued" {
                return value;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap()
}
#[tokio::test]
async fn http_runs_real_worker_and_replays_without_a_second_transform() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup(dir.path(), false).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/receipts",
            "",
            r#"{"state":"failed","error":"forged receipt"}"#
        )
        .await
        .0,
        404,
        "runtime exposed legacy receipt injection"
    );
    let (_, job_status) = call(&router, "GET", "/api/v1/jobs/job", "", "").await;
    let source_id = executor
        .store()
        .submit(|conn| {
            conn.query_row("SELECT input_ref FROM jobs WHERE job_id='job'", [], |r| {
                r.get::<_, String>(0)
            })
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        job_status["input_ref"], source_id,
        "job status must project the persisted source binding for Reader identity checks"
    );
    let (_, other_status) = call(&router, "GET", "/api/v1/jobs/other", "", "").await;
    assert_eq!(
        other_status["input_ref"], source_id,
        "each job status must expose its own persisted source binding"
    );
    let path = "/api/v1/jobs/job/executions";
    let (status, _) = call(&router, "POST", path, "run-1", r#"{"deadline_ms":5000}"#).await;
    assert_eq!(status, 202, "HTTP execution entry missing");
    assert_eq!(terminal(&router, "job").await["state"], "succeeded");
    let (status, output) = call(&router, "GET", "/api/v1/jobs/job/outputs/text", "", "").await;
    assert_eq!(status, 200);
    assert_eq!(output["content"], "中😀\r\n");
    assert_eq!(
        call(&router, "POST", path, "run-1", r#"{"deadline_ms":5000}"#)
            .await
            .0,
        202
    );
    assert_eq!(
        call(&router, "POST", path, "run-1", r#"{"deadline_ms":6000}"#)
            .await
            .0,
        409
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions",
            "run-1",
            r#"{"deadline_ms":5000}"#
        )
        .await
        .0,
        409
    );
    executor
        .store()
        .submit(|conn| {
            assert_eq!(
                conn.query_row("SELECT count(*) FROM transforms", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                1
            )
        })
        .await
        .unwrap();
    drop(router);
    drop(executor);
    tokio::task::yield_now().await;
    let restored = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap()),
        &PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/python-workers/transport/text_ndjson.py"),
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(restored);
    let replay = call(&router, "POST", path, "run-1", r#"{"deadline_ms":5000}"#).await;
    assert_eq!(replay.0, 202);
    assert_eq!(replay.1["state"], "succeeded");
    assert_eq!(replay.1["replayed"], true);
}

#[tokio::test]
async fn durable_ack_cancel_retry_and_parallel_budget_are_not_client_lifetime() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup(dir.path(), true).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    let (a, b) = tokio::join!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "same",
            r#"{"deadline_ms":5000}"#
        ),
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "same",
            r#"{"deadline_ms":5000}"#
        )
    );
    assert_eq!((a.0, b.0), (202, 202));
    executor
        .store()
        .submit(|conn| {
            assert_eq!(
                conn.query_row("SELECT count(*) FROM job_attempts", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                1
            );
            assert_eq!(
                jobs::job_state(conn, "job").unwrap().as_deref(),
                Some("running")
            );
        })
        .await
        .unwrap();
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions",
            "other",
            r#"{"deadline_ms":5000}"#
        )
        .await
        .0,
        202
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/third/executions",
            "third",
            r#"{"deadline_ms":5000}"#
        )
        .await
        .0,
        503
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions/stale/cancel",
            "",
            ""
        )
        .await
        .0,
        409
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions/same/cancel",
            "",
            ""
        )
        .await
        .0,
        202
    );
    assert_eq!(terminal(&router, "job").await["state"], "cancelled");
    assert_eq!(
        call(&router, "GET", "/api/v1/jobs/job/outputs/text", "", "")
            .await
            .0,
        404
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "same",
            r#"{"deadline_ms":5000}"#
        )
        .await
        .1["state"],
        "cancelled"
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "retry",
            r#"{"deadline_ms":100}"#
        )
        .await
        .0,
        202
    );
    assert_eq!(terminal(&router, "job").await["state"], "failed");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions/other/cancel",
            "",
            ""
        )
        .await
        .0,
        202
    );
    terminal(&router, "other").await;
    for (key, body) in [
        ("", r#"{"deadline_ms":100}"#),
        ("valid", r#"{"deadline_ms":0}"#),
        ("valid", r#"{"deadline_ms":10,"script":"elsewhere"}"#),
    ] {
        let invalid = call(&router, "POST", "/api/v1/jobs/third/executions", key, body).await;
        assert_eq!(invalid.0, 422);
        assert_eq!(invalid.1["code"], "AAK-VAL-001");
    }
}

#[tokio::test]
async fn disconnected_submitter_does_not_abandon_claimed_http_operation() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup(dir.path(), true).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    let client = router.clone();
    let submitted = tokio::spawn(async move {
        call(
            &client,
            "POST",
            "/api/v1/jobs/job/executions",
            "disconnected",
            r#"{"deadline_ms":150}"#,
        )
        .await
    });
    tokio::time::timeout(Duration::from_secs(2), async {
        loop {
            if executor
                .store()
                .submit(|c| jobs::job_state(c, "job").unwrap())
                .await
                .unwrap()
                .as_deref()
                == Some("running")
            {
                break;
            }
            tokio::task::yield_now().await;
        }
    })
    .await
    .unwrap();
    submitted.abort();
    assert_eq!(terminal(&router, "job").await["state"], "failed");
}

#[tokio::test]
async fn unrecoverable_terminal_write_is_reported_unavailable_not_reaccepted_running() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup(dir.path(), true).await;
    executor.store().submit(|conn|conn.execute_batch("CREATE TRIGGER reject_terminal BEFORE UPDATE OF state ON job_attempts WHEN new.state <> 'running' BEGIN SELECT RAISE(ABORT,'injected terminal write failure'); END;").unwrap()).await.unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let path = "/api/v1/jobs/job/executions";
    assert_eq!(
        call(
            &router,
            "POST",
            path,
            "disk-fault",
            r#"{"deadline_ms":100}"#
        )
        .await
        .0,
        202
    );
    tokio::time::timeout(Duration::from_secs(3), async {
        loop {
            if call(&router, "GET", "/api/v1/jobs/job", "", "").await.0 == 503 {
                break;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    assert_eq!(
        call(
            &router,
            "POST",
            path,
            "disk-fault",
            r#"{"deadline_ms":100}"#
        )
        .await
        .0,
        503,
        "faulted execution pretended to accept replay"
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions/disk-fault/cancel",
            "",
            ""
        )
        .await
        .0,
        503
    );
}

#[tokio::test]
async fn waiting_admission_does_not_block_cancellation_of_an_owned_worker() {
    use std::{
        future::Future,
        sync::mpsc,
        task::{Context, Waker},
    };
    let dir = tempfile::tempdir().unwrap();
    let executor = setup(dir.path(), true).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "owned",
            r#"{"deadline_ms":5000}"#
        )
        .await
        .0,
        202
    );
    executor.store().submit(|_| ()).await.unwrap();
    let (started, ready) = mpsc::channel();
    let (release, wait) = mpsc::channel();
    let mut blocker = Box::pin(executor.store().submit(move |_| {
        started.send(()).unwrap();
        wait.recv_timeout(Duration::from_secs(3)).unwrap();
    }));
    assert!(
        blocker
            .as_mut()
            .poll(&mut Context::from_waker(Waker::noop()))
            .is_pending()
    );
    ready.recv_timeout(Duration::from_secs(1)).unwrap();
    let mut pending = Box::pin(call(
        &router,
        "POST",
        "/api/v1/jobs/other/executions",
        "waiting",
        r#"{"deadline_ms":100}"#,
    ));
    assert!(
        pending
            .as_mut()
            .poll(&mut Context::from_waker(Waker::noop()))
            .is_pending()
    );
    tokio::time::sleep(Duration::from_millis(20)).await;
    let cancelled = tokio::time::timeout(
        Duration::from_millis(100),
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions/owned/cancel",
            "",
            "",
        ),
    )
    .await;
    release.send(()).unwrap();
    blocker.await.unwrap();
    let _ = pending.await;
    assert_eq!(
        cancelled.expect("admission blocked owner cancellation").0,
        202
    );
    assert_eq!(terminal(&router, "job").await["state"], "cancelled");
    terminal(&router, "other").await;
}

/// Asking to split is the only extra input an execution body may carry, and it does not widen any
/// other route: a text job has no bounded unit of work, so the claim refuses it and no attempt row
/// is created. A body that carries a window plan instead is refused outright, because the plan is
/// derived from the file rather than accepted from the caller.
#[tokio::test]
async fn the_split_choice_does_not_widen_other_routes() {
    let dir = tempfile::tempdir().unwrap();
    let executor = setup(dir.path(), false).await;
    let router = archeaxis_api::runtime::router(executor);

    for body in [
        r#"{"deadline_ms":100,"split":"yes"}"#,
        r#"{"deadline_ms":100,"window":{"index":0,"start_ms":0,"end_ms":10}}"#,
        r#"{"deadline_ms":100,"split":true,"staging":"elsewhere"}"#,
    ] {
        let (status, value) = call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "bad-split",
            body,
        )
        .await;
        assert_eq!(status, 422, "{body}");
        assert_eq!(value["code"], "AAK-VAL-001", "{body}");
    }

    // The job is a text job: it has no bounded unit of work, so a split cannot be honoured.
    let (status, _) = call(
        &router,
        "POST",
        "/api/v1/jobs/job/executions",
        "text-split",
        r#"{"deadline_ms":100,"split":true}"#,
    )
    .await;
    assert_eq!(status, 409);
    // No attempt row means no staging copy and no partial output was left behind either.
    let (status, value) = call(&router, "GET", "/api/v1/jobs/job", "", "").await;
    assert_eq!(status, 200);
    assert!(value["attempt"].is_null(), "{value}");
}

#[tokio::test]
async fn folder_mixed_success_failure_cancel_keeps_originals_only_failed_fresh_request_and_restarts()
 {
    // Candidate test only. All data/processes owned by this tempfile; canonical
    // runtime route and text transport perform real execution when root runs it.
    let dir = tempfile::tempdir().unwrap();
    let transport = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let script = dir.path().join("folder_mixed_owned.py");
    let literal = serde_json::to_string(&transport.to_string_lossy()).unwrap();
    std::fs::write(&script,format!("import importlib.util,time\np={literal}\ns=importlib.util.spec_from_file_location('owned_canonical_text',p)\nm=importlib.util.module_from_spec(s)\ns.loader.exec_module(m)\noriginal=m.execute\ndef controlled(request,*args,**kwargs):\n if request.get('job_id')=='other' or (request.get('job_id')=='third' and request.get('request_id')=='folder-failure'): time.sleep(30)\n return original(request,*args,**kwargs)\nm.execute=controlled\nraise SystemExit(m.main())\n")).unwrap();
    let db = dir.path().join("db.sqlite");
    let executor = Executor::open(
        &db,
        &dir.path().join("staging"),
        &PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap()),
        &script,
    )
    .await
    .unwrap();
    let source_id = executor
        .store()
        .submit(|conn| {
            let source = match source::import_source(
                conn,
                "owned 中😀\r\n".as_bytes(),
                "owned-folder.txt",
                None,
            )
            .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            for id in ["job", "other", "third"] {
                jobs::enqueue(conn, id, "text", &source).unwrap();
            }
            source
        })
        .await
        .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let (code, original) = call(
        &router,
        "GET",
        &format!("/api/v1/sources/{source_id}/original"),
        "",
        "",
    )
    .await;
    assert_eq!(code, 200);
    let body = r#"{"deadline_ms":5000,"split":false,"words":false}"#;
    let (code, ack) = call(
        &router,
        "POST",
        "/api/v1/jobs/job/executions",
        "folder-success",
        body,
    )
    .await;
    assert_eq!(code, 202);
    assert_eq!(
        ack,
        serde_json::json!({"job_id":"job","request_id":"folder-success","state":"running","replayed":false})
    );
    let succeeded = terminal_execution_status(&router, "job", "folder-success").await;
    assert_eq!(succeeded["input_ref"], source_id);
    assert_eq!(succeeded["state"], "succeeded");
    let (code, transform) = call(
        &router,
        "GET",
        &format!("/api/v1/sources/{source_id}/jobs/job/transform"),
        "",
        "",
    )
    .await;
    assert_eq!(code, 200);
    assert_eq!(transform["source_id"], source_id);
    assert_eq!(transform["job_id"], "job");
    assert_eq!(transform["raw_sha256"], original["sha256"]);
    assert_eq!(transform["content"], "owned 中😀\r\n");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/third/executions",
            "folder-failure",
            r#"{"deadline_ms":100}"#
        )
        .await
        .0,
        202
    );
    let failed = terminal_execution_status(&router, "third", "folder-failure").await;
    assert_eq!(failed["state"], "failed");
    assert_eq!(failed["input_ref"], source_id);
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/other/executions",
            "folder-cancel",
            r#"{"deadline_ms":300000}"#
        )
        .await
        .0,
        202
    );
    let pending = call(
        &router,
        "POST",
        "/api/v1/jobs/other/executions/folder-cancel/cancel",
        "",
        "",
    )
    .await;
    assert_eq!(pending.0, 202);
    assert_eq!(
        pending.1,
        serde_json::json!({"job_id":"other","request_id":"folder-cancel","cancel_requested":true})
    );
    let cancelled = terminal_execution_status(&router, "other", "folder-cancel").await;
    assert_eq!(cancelled["state"], "cancelled");
    assert_eq!(cancelled["input_ref"], source_id);
    // Lost ACK -> same request read/replay, not a fresh worker invocation.
    let replay = call(
        &router,
        "POST",
        "/api/v1/jobs/third/executions",
        "folder-failure",
        r#"{"deadline_ms":100}"#,
    )
    .await;
    assert_eq!(replay.0, 202);
    assert_eq!(
        replay.1,
        serde_json::json!({"job_id":"third","request_id":"folder-failure","state":"failed","replayed":true})
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/job/executions",
            "folder-failure",
            r#"{"deadline_ms":100}"#
        )
        .await
        .0,
        409
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/third/executions",
            "folder-failure",
            r#"{"deadline_ms":101}"#
        )
        .await
        .0,
        409
    );
    // Only the failed row is re-executed using a genuinely new frozen request.
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/jobs/third/executions",
            "folder-failed-fresh",
            body
        )
        .await
        .0,
        202
    );
    let retried = terminal_execution_status(&router, "third", "folder-failed-fresh").await;
    assert_eq!(retried["state"], "succeeded");
    assert_eq!(retried["attempt"], 2);
    assert_eq!(retried["attempts"][1]["request_id"], "folder-failure");
    assert_eq!(retried["attempts"][1]["state"], "failed");
    assert_eq!(
        terminal_execution_status(&router, "job", "folder-success").await,
        succeeded
    );
    assert_eq!(
        terminal_execution_status(&router, "other", "folder-cancel").await,
        cancelled
    );
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("/api/v1/sources/{source_id}/original"),
            "",
            ""
        )
        .await
        .1,
        original
    );
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("/api/v1/sources/{source_id}/jobs/job/transform"),
            "",
            ""
        )
        .await
        .1,
        transform
    );
    executor
        .store()
        .submit(|conn| {
            assert_eq!(
                conn.query_row(
                    "SELECT count(*) FROM job_attempts WHERE job_id='job'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap(),
                1
            );
            assert_eq!(
                conn.query_row(
                    "SELECT count(*) FROM job_attempts WHERE job_id='other'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap(),
                1
            );
            assert_eq!(
                conn.query_row(
                    "SELECT count(*) FROM job_attempts WHERE job_id='third'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap(),
                2
            );
            assert_eq!(
                conn.query_row("SELECT count(*) FROM transforms", [], |r| r
                    .get::<_, i64>(0))
                    .unwrap(),
                2
            );
        })
        .await
        .unwrap();
    drop(router);
    drop(executor);
    // Real durable reopen using projections only: no fresh worker or forged rows.
    let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(
            &reopened,
            "GET",
            &format!("/api/v1/sources/{source_id}/original"),
            "",
            ""
        )
        .await
        .1,
        original
    );
    assert_eq!(
        call(
            &reopened,
            "GET",
            &format!("/api/v1/sources/{source_id}/jobs/job/transform"),
            "",
            ""
        )
        .await
        .1,
        transform
    );
    let (code, listing) = call(
        &reopened,
        "GET",
        &format!("/api/v1/sources/{source_id}/jobs"),
        "",
        "",
    )
    .await;
    assert_eq!(code, 200);
    assert_eq!(listing["source_id"], source_id);
    let rows = listing["jobs"].as_array().unwrap();
    assert_eq!(rows.len(), 3);
    assert_eq!(listing["jobs_capped"], false);
    for (job, state, attempt) in [
        ("job", "succeeded", 1),
        ("other", "cancelled", 1),
        ("third", "succeeded", 2),
    ] {
        let row = rows.iter().find(|row| row["job_id"] == job).unwrap();
        assert_eq!(row["input_ref"], source_id);
        assert_eq!(row["state"], state);
        assert_eq!(row["attempt"], attempt);
    }
}
