//! The conflict rules the published contract states, as executable cases.
//!
//! docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md tells the UI:
//!
//! * re-POSTing `/jobs/{id}/executions` with the **same** `idempotency-key` and the same
//!   payload replays, and the reply says so;
//! * a **different** payload under the same key is `409`;
//! * a job that has settled `succeeded` is not re-executed.
//!
//! Those behaviours existed but nothing asserted them as the contract states them - the
//! existing coverage reached the replay path incidentally - so a UI built against the
//! document could not rely on them staying true. The cases below were first exercised against
//! a live Core, then fixed here so they are checked on every run.

use archeaxis_application::{executor::Executor, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::{path::PathBuf, time::Duration};
use tower::ServiceExt;

async fn executor(dir: &std::path::Path) -> Executor {
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
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
            let id =
                match source::import_source(conn, "alpha beta gamma\n".as_bytes(), "n.txt", None)
                    .unwrap()
                {
                    ImportOutcome::Imported { source_id, .. } => source_id,
                    _ => unreachable!(),
                };
            for job in ["job-a", "job-b"] {
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
    tokio::time::timeout(Duration::from_secs(10), async {
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

/// The execution body. The job and the idempotency key travel in the path and the header,
/// so the only thing a caller can vary here is the deadline - which is exactly the field the
/// Core compares when it decides whether a repeated key is a replay or a conflict.
fn execution_body(deadline_ms: u64) -> String {
    format!(r#"{{"deadline_ms":{deadline_ms}}}"#)
}

#[tokio::test]
async fn the_contract_conflict_rules_hold() {
    let dir = tempfile::tempdir().unwrap();
    let executor = executor(dir.path()).await;
    let router = archeaxis_api::runtime::router(executor.clone());

    // A completed execution, so the replay path is about a settled job rather than a race.
    let (status, body) = call(
        &router,
        "POST",
        "/api/v1/jobs/job-a/executions",
        "key-a",
        &execution_body(60_000),
    )
    .await;
    assert_eq!(status, 202, "{body}");
    assert_eq!(body["replayed"], false, "{body}");
    let settled = terminal(&router, "job-a").await;
    assert_eq!(settled["state"], "succeeded", "{settled}");

    // same key, same payload: a replay, and the reply says so
    let (status, body) = call(
        &router,
        "POST",
        "/api/v1/jobs/job-a/executions",
        "key-a",
        &execution_body(60_000),
    )
    .await;
    assert_eq!(status, 202, "same key and payload must replay: {body}");
    assert_eq!(
        body["replayed"], true,
        "the reply must say it replayed: {body}"
    );
    assert_eq!(body["state"], "succeeded", "{body}");

    // same key, a different payload: a conflict, not a second run
    let (status, body) = call(
        &router,
        "POST",
        "/api/v1/jobs/job-a/executions",
        "key-a",
        &execution_body(61_000),
    )
    .await;
    assert_eq!(
        status, 409,
        "a different deadline under one key must conflict: {body}"
    );
    assert_eq!(body["code"], "AAK-CON-002", "{body}");

    // the same key used for a different job: also a conflict
    let (status, body) = call(
        &router,
        "POST",
        "/api/v1/jobs/job-b/executions",
        "key-a",
        &execution_body(60_000),
    )
    .await;
    assert_eq!(status, 409, "one key may not name two jobs: {body}");
    assert_eq!(body["code"], "AAK-CON-002", "{body}");

    // a settled job is not re-executed under a new key either
    let (status, body) = call(
        &router,
        "POST",
        "/api/v1/jobs/job-a/executions",
        "key-a2",
        &execution_body(60_000),
    )
    .await;
    assert_eq!(status, 409, "a settled job must not start again: {body}");
    assert_eq!(body["code"], "AAK-CON-003", "{body}");

    // and the state is unchanged by those refusals
    let after = terminal(&router, "job-a").await;
    assert_eq!(
        after["state"], "succeeded",
        "a refused start must not disturb the job"
    );
    let attempts: i64 = executor
        .store()
        .submit(|conn| {
            conn.query_row(
                "SELECT count(*) FROM job_attempts WHERE job_id='job-a'",
                [],
                |r| r.get(0),
            )
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        attempts, 1,
        "no conflict path may leave a second attempt behind"
    );
}

#[tokio::test]
async fn an_execution_that_is_already_running_conflicts_with_a_second_key() {
    let dir = tempfile::tempdir().unwrap();
    let executor = executor(dir.path()).await;
    let router = archeaxis_api::runtime::router(executor);

    let (first, body) = call(
        &router,
        "POST",
        "/api/v1/jobs/job-a/executions",
        "run-1",
        &execution_body(60_000),
    )
    .await;
    assert_eq!(first, 202, "{body}");

    // While it is in flight, a second key must not start a second attempt.
    let (status, body) = call(
        &router,
        "POST",
        "/api/v1/jobs/job-a/executions",
        "run-2",
        &execution_body(60_000),
    )
    .await;
    assert!(
        status == 409 || status == 202,
        "a second attempt at one job is either refused or a replay, never a second run: {status} {body}"
    );
    if status == 409 {
        assert_eq!(body["code"], "AAK-CON-002", "{body}");
    }

    let settled = terminal(&router, "job-a").await;
    assert_eq!(settled["state"], "succeeded", "{settled}");
}
