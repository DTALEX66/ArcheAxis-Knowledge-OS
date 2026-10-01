//! The boundaries of `GET /jobs/{job_id}/outputs/{kind}`, pinned.
//!
//! The UI reads three outputs from a conversion job, and this route had no test of its own - so
//! nothing recorded what a client should expect when it asks for an output that is not there.
//! Driven against a live Core first, the answers are:
//!
//! * the three kinds a text job writes answer `200` with `{content, metadata}`, and `metadata`
//!   carries the `kind`, `schema`, `sha256`, `byte_length` and `authority_effect`;
//! * **everything else is `404 AAK-VAL-004` "output not found"** - a kind the job will never
//!   write, a kind no route writes, a job that does not exist, and a job that has not finished.
//!
//! That last group is the important one, because the reasons are different and the answer is the
//! same. A UI cannot tell "not yet" from "never" by the status code, so the resolution rule has to
//! come from the job's own state, which is what `the_job_state_resolves_the_ambiguity` checks:
//! while a job is `running` a missing output means retry, and once it is `succeeded` a missing
//! output means it will never appear. The contract documents this.

use archeaxis_application::{executor::Executor, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::{path::PathBuf, time::Duration};
use tower::ServiceExt;

const KINDS: [&str; 3] = ["text", "document_structure", "loss_report"];

async fn setup() -> (tempfile::TempDir, Router, Executor) {
    let dir = tempfile::tempdir().unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
    )
    .await
    .unwrap();
    executor
        .store()
        .submit(|conn| {
            let id = match source::import_source(
                conn,
                b"alpha beta gamma\nsecond line\n",
                "n.txt",
                None,
            )
            .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            jobs::enqueue(conn, "job", "text", &id).unwrap();
        })
        .await
        .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    (dir, router, executor)
}

async fn get(router: &Router, path: &str) -> (u16, serde_json::Value) {
    let resp = router
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(path)
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let status = resp.status().as_u16();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}

async fn start(router: &Router, job: &str) {
    let resp = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/api/v1/jobs/{job}/executions"))
                .header("content-type", "application/json")
                .header("idempotency-key", format!("key-{job}"))
                .body(Body::from(r#"{"deadline_ms":60000}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status().as_u16(), 202);
}

async fn settle(router: &Router, job: &str) -> String {
    tokio::time::timeout(Duration::from_secs(10), async {
        loop {
            let (_, value) = get(router, &format!("/api/v1/jobs/{job}")).await;
            let state = value["state"].as_str().unwrap_or_default().to_owned();
            if state != "running" && state != "queued" && !state.is_empty() {
                return state;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap()
}

#[tokio::test]
async fn the_three_kinds_a_text_job_writes_are_readable_with_their_envelope() {
    let (_dir, router, _executor) = setup().await;
    start(&router, "job").await;
    assert_eq!(settle(&router, "job").await, "succeeded");

    let mut seen = Vec::new();
    for kind in KINDS {
        let (status, body) = get(&router, &format!("/api/v1/jobs/job/outputs/{kind}")).await;
        assert_eq!(status, 200, "{kind}: {body}");
        assert!(
            body["content"].is_string(),
            "{kind} must carry content: {body}"
        );
        assert!(
            !body["content"].as_str().unwrap().is_empty(),
            "{kind} is empty"
        );
        let metadata = &body["metadata"];
        assert_eq!(
            metadata["kind"], kind,
            "{kind} metadata must name its own kind"
        );
        assert!(
            metadata["schema"].is_string(),
            "{kind} must name its schema: {body}"
        );
        assert!(
            metadata["sha256"].is_string(),
            "{kind} must carry a digest: {body}"
        );
        assert!(
            metadata["byte_length"].is_number(),
            "{kind} must carry a byte length: {body}"
        );
        assert_eq!(
            metadata["authority_effect"], "candidate_or_measurement_only",
            "{kind} must not claim authority: {body}"
        );
        seen.push(kind);
    }
    assert_eq!(seen.len(), 3);
}

#[tokio::test]
async fn everything_that_is_not_there_answers_the_same_404() {
    let (_dir, router, _executor) = setup().await;
    start(&router, "job").await;
    assert_eq!(settle(&router, "job").await, "succeeded");

    let cases = [
        (
            "a kind this job never writes",
            "/api/v1/jobs/job/outputs/ocr_words",
        ),
        (
            "a kind no route writes",
            "/api/v1/jobs/job/outputs/definitely_not_a_kind",
        ),
        (
            "a job that does not exist",
            "/api/v1/jobs/no-such-job/outputs/text",
        ),
    ];
    for (label, path) in cases {
        let (status, body) = get(&router, path).await;
        assert_eq!(status, 404, "{label}: {body}");
        assert_eq!(body["code"], "AAK-VAL-004", "{label}: {body}");
        assert_eq!(body["message"], "output not found", "{label}: {body}");
    }
}

#[tokio::test]
async fn the_job_state_resolves_the_ambiguity() {
    // This is the rule the UI needs, and it is why the contract calls it out: the same 404 means
    // "retry" while the job is running and "never" once it has succeeded.
    let (_dir, router, _executor) = setup().await;

    let (_, before) = get(&router, "/api/v1/jobs/job").await;
    assert_eq!(before["state"], "queued", "{before}");
    let (status, body) = get(&router, "/api/v1/jobs/job/outputs/text").await;
    assert_eq!(status, 404, "a queued job has written nothing: {body}");
    assert_eq!(body["code"], "AAK-VAL-004");

    start(&router, "job").await;
    assert_eq!(settle(&router, "job").await, "succeeded");

    let (status, body) = get(&router, "/api/v1/jobs/job/outputs/text").await;
    assert_eq!(
        status, 200,
        "after success the output is there, so a 404 at this point would mean never: {body}"
    );
    // and the absent-kind 404 now means "never", because the job cannot write it
    let (status, body) = get(&router, "/api/v1/jobs/job/outputs/definitely_not_a_kind").await;
    assert_eq!(status, 404);
    assert_eq!(body["code"], "AAK-VAL-004");
}

#[tokio::test]
async fn a_replay_does_not_remove_the_outputs() {
    let (_dir, router, _executor) = setup().await;
    start(&router, "job").await;
    assert_eq!(settle(&router, "job").await, "succeeded");
    let (first, _) = get(&router, "/api/v1/jobs/job/outputs/text").await;
    assert_eq!(first, 200);

    // the same idempotency key replays rather than starting a second attempt
    let resp = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/jobs/job/executions")
                .header("content-type", "application/json")
                .header("idempotency-key", "key-job")
                .body(Body::from(r#"{"deadline_ms":60000}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status().as_u16(), 202);

    // The route reads the latest attempt's rows, so a replay that added an attempt without
    // outputs would blank them. Re-reading is therefore the check, not the replay itself.
    let (again, body) = get(&router, "/api/v1/jobs/job/outputs/text").await;
    assert_eq!(again, 200, "outputs must survive a replay: {body}");
    assert!(
        body["content"]
            .as_str()
            .is_some_and(|c| c.contains("alpha"))
    );
}
