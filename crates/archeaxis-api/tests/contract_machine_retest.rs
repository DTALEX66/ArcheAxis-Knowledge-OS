//! G4: a retest asks the same question again and records itself against the task it retests.
//!
//! The checks are about the link and the boundary. A retest that does not name what it retests is
//! just another task; a retest that scores itself would be the Core marking its own work; and a
//! retest recorded when the model could not run would look like a measurement.

use archeaxis_application::executor::Executor;
use archeaxis_domain::{knowledge, machine};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

struct Fixture {
    _dir: tempfile::TempDir,
    router: Router,
    knowledge_id: String,
    prior_task_id: String,
}

async fn fixture() -> Fixture {
    let dir = tempfile::tempdir().unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    // Synthetic worker: deterministic contract evidence, never real-model evidence.
    let worker = dir.path().join("answer.py");
    std::fs::write(&worker, r#"import json
from pathlib import Path
p = Path(__file__).with_suffix('.count')
p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')
print(json.dumps({'answer': 'Synthetic answer', 'model': 'some-model', 'loss_receipt': {'params': {'authority': 'candidate'}}}))
"#).unwrap();
    let transport = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &transport,
        &[("machine.answer", worker)],
    )
    .await
    .unwrap();

    let (knowledge_id, prior_task_id) = executor
        .store()
        .submit(|conn| {
            let knowledge_id = knowledge::create_knowledge(
                conn,
                "NOTE",
                "ArcheAxis keeps its canonical store in SQLite and only the Rust Core writes it.",
                "accepted",
                None,
                None,
                "human",
            )?;
            // The task being retested. Recorded through the domain, so the retest's claim about it
            // is a claim about a real receipt.
            machine::record_machine_task(
                conn,
                &machine::MachineTask {
                    task_id: "task_baseline",
                    principal: "machine",
                    conditions: &serde_json::json!({"knowledge_id": knowledge_id, "question": "what writes the store?", "answer": {"answer":"incorrect baseline", "model":"some-model"}, "correction": {"correction_candidate_id":"candidate_fixture"}}).to_string(),
                    knowledge_version: Some(&format!("{knowledge_id}@v1")),
                    method_version: None,
                    tool_version: None,
                    model_version: "some-model",
                    scope: "runtime.evaluation.failed",
                    // The domain only accepts a retest of a **failed** task, because that is the
                    // only case where "did the correction help" has a meaning. The fixture
                    // therefore records a failure, with the reason the domain requires.
                    outcome: "failed",
                    failure: Some("named a database this workspace does not use"),
                    retest_of: None,
                },
            )?;
            Ok::<_, rusqlite::Error>((knowledge_id, "task_baseline".to_string()))
        })
        .await
        .unwrap()
        .unwrap();

    let router = archeaxis_api::runtime::router(executor);
    Fixture {
        _dir: dir,
        router,
        knowledge_id,
        prior_task_id,
    }
}

fn body(knowledge_id: &str, retest_of: &str, question: &str) -> String {
    format!(
        r#"{{"knowledge_id":"{knowledge_id}","retest_of":"{retest_of}","question":"{question}","timeout_s":600}}"#
    )
}

async fn post(router: &Router, path: &str, body: &str) -> (u16, String) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(path)
                .header("content-type", "application/json")
                .body(Body::from(body.to_owned()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8_lossy(&bytes).to_string())
}

#[tokio::test]
async fn a_retest_must_name_what_it_retests() {
    let fixture = fixture().await;
    let (status, text) = post(
        &fixture.router,
        "/api/v1/machine/retests",
        &body(&fixture.knowledge_id, "   ", "what writes the store?"),
    )
    .await;
    assert_eq!(status, 422, "{text}");
    assert!(text.contains("retest_of is required"), "{text}");
}

#[tokio::test]
async fn a_retest_needs_a_question() {
    let fixture = fixture().await;
    let (status, text) = post(
        &fixture.router,
        "/api/v1/machine/retests",
        &body(&fixture.knowledge_id, &fixture.prior_task_id, "  "),
    )
    .await;
    assert_eq!(status, 422, "{text}");
    assert!(text.contains("question is required"), "{text}");
}

#[tokio::test]
async fn retesting_a_task_that_does_not_exist_is_a_not_found_before_any_model_call() {
    // Checked before the model runs, so a typo in the task id cannot spend a model call or produce
    // an answer that is then thrown away.
    let fixture = fixture().await;
    let (status, text) = post(
        &fixture.router,
        "/api/v1/machine/retests",
        &body(
            &fixture.knowledge_id,
            "task_does_not_exist",
            "what writes the store?",
        ),
    )
    .await;
    assert_eq!(status, 404, "{text}");
    assert!(text.contains("no machine task"), "{text}");
}

#[tokio::test]
async fn an_unknown_knowledge_item_is_a_not_found() {
    let fixture = fixture().await;
    let (status, text) = post(
        &fixture.router,
        "/api/v1/machine/retests",
        &body(
            "k_does_not_exist",
            &fixture.prior_task_id,
            "what writes the store?",
        ),
    )
    .await;
    assert_eq!(status, 404, "{text}");
    assert!(text.contains("no knowledge item"), "{text}");
}

#[tokio::test]
async fn a_disabled_capability_refuses_before_the_model_runs() {
    let fixture = fixture().await;
    let response = fixture
        .router
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri("/api/v1/capabilities/machine.answer/enabled")
                .header("content-type", "application/json")
                .body(Body::from(r#"{"enabled":false}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status().as_u16(), 200);

    let (status, text) = post(
        &fixture.router,
        "/api/v1/machine/retests",
        &body(
            &fixture.knowledge_id,
            &fixture.prior_task_id,
            "what writes the store?",
        ),
    )
    .await;
    assert_eq!(status, 409, "{text}");
}

#[tokio::test]
async fn a_recorded_retest_links_to_the_task_it_retests() {
    // The assertion is which of the two honest outcomes happens. With a model the retest is recorded
    // and linked; without one the route fails by name and records nothing, because a task that could
    // not run is not a measurement.
    let fixture = fixture().await;
    let question = "what writes the store?";
    let (status, text) = post(
        &fixture.router,
        "/api/v1/machine/retests",
        &body(&fixture.knowledge_id, &fixture.prior_task_id, question),
    )
    .await;

    match status {
        200 => {
            let value: serde_json::Value = serde_json::from_str(&text).unwrap();
            assert_eq!(value["schema"], "archeaxis.machine-retest/v1");
            assert_eq!(value["retest_of"], fixture.prior_task_id, "{text}");
            assert_eq!(value["authority"], "candidate", "{text}");
            // the prior receipt travels with it, so a person can compare the two
            assert_eq!(value["prior"]["outcome"], "failed", "{text}");
            assert_eq!(value["prior"]["model_version"], "some-model", "{text}");
            // the Core does not score its own retest
            assert!(
                value["note"].as_str().unwrap().contains("does not decide"),
                "{text}"
            );
            let retest_id = value["retest_task_id"].as_str().unwrap().to_string();
            assert!(retest_id.starts_with("retest_"), "{text}");
        }
        503 => {
            assert!(!text.trim().is_empty(), "a failure must name a reason");
        }
        other => panic!("unexpected status {other}: {text}"),
    }
}

#[tokio::test]
async fn different_question_and_unrelated_knowledge_are_rejected_before_inference() {
    let f = fixture().await;
    assert_eq!(
        post(
            &f.router,
            "/api/v1/machine/retests",
            &body(&f.knowledge_id, &f.prior_task_id, "a different question")
        )
        .await
        .0,
        409
    );
    let mut conn = rusqlite::Connection::open(f._dir.path().join("db.sqlite")).unwrap();
    let other = knowledge::create_knowledge(
        &mut conn,
        "NOTE",
        "unrelated",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    assert_eq!(
        post(
            &f.router,
            "/api/v1/machine/retests",
            &body(&other, &f.prior_task_id, "what writes the store?")
        )
        .await
        .0,
        409
    );
    assert!(!f._dir.path().join("answer.count").exists());
}

#[tokio::test]
async fn concurrent_retests_and_restart_replay_one_persisted_answer() {
    let f = fixture().await;
    let request = body(&f.knowledge_id, &f.prior_task_id, "what writes the store?");
    let (a, b) = tokio::join!(
        post(&f.router, "/api/v1/machine/retests", &request),
        post(&f.router, "/api/v1/machine/retests", &request)
    );
    assert_eq!(a.0, 200, "{}", a.1);
    assert_eq!(a, b);
    assert_eq!(
        std::fs::read_to_string(f._dir.path().join("answer.count")).unwrap(),
        "1"
    );
    drop(f.router);
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let transport = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open_routes(
        &f._dir.path().join("db.sqlite"),
        &f._dir.path().join("staging"),
        &python,
        &transport,
        &[("machine.answer", f._dir.path().join("answer.py"))],
    )
    .await
    .unwrap();
    let restarted = archeaxis_api::runtime::router(executor);
    assert_eq!(
        a,
        post(&restarted, "/api/v1/machine/retests", &request).await
    );
    assert_eq!(
        std::fs::read_to_string(f._dir.path().join("answer.count")).unwrap(),
        "1"
    );
}

#[tokio::test]
async fn a_reviewed_successor_remains_comparable_to_the_original() {
    let f = fixture().await;
    let mut conn = rusqlite::Connection::open(f._dir.path().join("db.sqlite")).unwrap();
    let successor = knowledge::create_knowledge(
        &mut conn,
        "NOTE",
        "corrected successor",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    conn.execute(
        "INSERT INTO knowledge_supersedes(old_knowledge_id,new_knowledge_id) VALUES(?1,?2)",
        [&f.knowledge_id, &successor],
    )
    .unwrap();
    let request = body(&successor, &f.prior_task_id, "what writes the store?");
    let first = post(&f.router, "/api/v1/machine/retests", &request).await;
    assert_eq!(first.0, 200, "{}", first.1);
    conn.execute(
        "UPDATE knowledge SET status='deprecated' WHERE knowledge_id=?1",
        [successor],
    )
    .unwrap();
    // Replaying the immutable historical result does not infer from deprecated knowledge.
    assert_eq!(
        first,
        post(&f.router, "/api/v1/machine/retests", &request).await
    );
    assert_eq!(
        std::fs::read_to_string(f._dir.path().join("answer.count")).unwrap(),
        "1"
    );
}
