//! G4: a machine answer over an accepted knowledge item, and the limits it must keep.
//!
//! This is the machine half of the co-learning loop. The checks below are about grounding and
//! labelling rather than about what the model says, because a model's wording is not a fact this
//! repository can fix: the answer must be grounded in the workspace's own accepted body, must be
//! labelled a candidate, and must never be promoted.

use archeaxis_application::executor::Executor;
use archeaxis_domain::knowledge;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

/// An executor with the machine answer route declared, plus one accepted knowledge item to answer
/// from.
async fn fixture() -> (tempfile::TempDir, Router, String) {
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

    let knowledge_id = executor
        .store()
        .submit(|conn| {
            // `create_knowledge` rather than the v3 form: the v3 form requires governance metadata and
            // rejects its absence, which is a fact about governance rather than about this route.
            knowledge::create_knowledge(
                conn,
                "NOTE",
                "ArcheAxis Knowledge keeps its canonical store in SQLite, and only the Rust Core \
                 writes it. The release is currently FROZEN.",
                "accepted",
                None,
                None,
                "human",
            )
        })
        .await
        .unwrap()
        .unwrap();

    let router = archeaxis_api::runtime::router(executor);
    (dir, router, knowledge_id)
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
async fn a_question_is_required_rather_than_answering_nothing() {
    let (_dir, router, knowledge_id) = fixture().await;
    let (status, body) = post(
        &router,
        "/api/v1/machine/answers",
        &format!(r#"{{"knowledge_id":"{knowledge_id}","question":"   "}}"#),
    )
    .await;

    assert_eq!(status, 422, "{body}");
    assert!(body.contains("question is required"), "{body}");
}

#[tokio::test]
async fn an_unknown_knowledge_item_is_a_not_found_rather_than_a_free_answer() {
    // Without this, a typo in the id would silently answer from nothing and look like a capability.
    let (_dir, router, _) = fixture().await;
    let (status, body) = post(
        &router,
        "/api/v1/machine/answers",
        r#"{"knowledge_id":"k_does_not_exist","question":"what?"}"#,
    )
    .await;

    assert_eq!(status, 404, "{body}");
    assert!(body.contains("no knowledge item"), "{body}");
}

#[tokio::test]
async fn candidate_and_deprecated_knowledge_are_refused_before_inference() {
    for status in ["candidate", "deprecated", "rejected"] {
        let (dir, router, knowledge_id) = fixture().await;
        let conn = rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
        conn.execute(
            "UPDATE knowledge SET status=?1 WHERE knowledge_id=?2",
            [status, &knowledge_id],
        )
        .unwrap();
        let (status, body) = post(
            &router,
            "/api/v1/machine/answers",
            &serde_json::json!({"knowledge_id": knowledge_id, "question": "what?", "timeout_s": 1})
                .to_string(),
        )
        .await;
        assert_eq!(status, 404, "{body}");
    }
}

#[tokio::test]
async fn active_personal_knowledge_is_allowed_but_superseded_knowledge_is_not() {
    let (dir, router, id) = fixture().await;
    let mut conn = rusqlite::Connection::open(dir.path().join("db.sqlite")).unwrap();
    let personal = knowledge::create_knowledge(
        &mut conn,
        "PERSONAL_DEFINITION",
        "my experience",
        "candidate",
        None,
        None,
        "human",
    )
    .unwrap();
    let request = serde_json::json!({"knowledge_id":personal,"question":"what?"});
    assert_eq!(
        post(&router, "/api/v1/machine/answers", &request.to_string())
            .await
            .0,
        200
    );
    conn.execute(
        "INSERT INTO knowledge_supersedes(old_knowledge_id,new_knowledge_id) VALUES(?1,?2)",
        [&id, &personal],
    )
    .unwrap();
    let request = serde_json::json!({"knowledge_id":id,"question":"what?"});
    assert_eq!(
        post(&router, "/api/v1/machine/answers", &request.to_string())
            .await
            .0,
        404
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "1"
    );
}

#[tokio::test]
async fn a_free_text_context_is_refused_because_grounding_is_the_point() {
    let (_dir, router, _) = fixture().await;
    // `context` is not a field of this route; a caller must name accepted material instead.
    let (status, _) = post(
        &router,
        "/api/v1/machine/answers",
        r#"{"knowledge_id":"k_x","question":"what?","context":"whatever I like"}"#,
    )
    .await;

    assert_eq!(
        status, 422,
        "an unknown field must be refused rather than ignored"
    );
}

#[tokio::test]
async fn a_disabled_capability_refuses_before_the_model_runs() {
    let (_dir, router, knowledge_id) = fixture().await;
    let response = router
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

    let (status, body) = post(
        &router,
        "/api/v1/machine/answers",
        &format!(r#"{{"knowledge_id":"{knowledge_id}","question":"what writes the store?"}}"#),
    )
    .await;

    assert_eq!(status, 409, "{body}");
    assert!(body.contains("machine.answer"), "{body}");
}

#[tokio::test]
async fn an_answer_is_either_a_labelled_candidate_or_a_named_failure() {
    // The assertion is deliberately about which of the two honest outcomes happens, not about the
    // model's wording. A machine with no model must fail by name; a machine with one must answer and
    // label the answer a candidate. Either way nothing is invented and nothing is promoted.
    let (_dir, router, knowledge_id) = fixture().await;
    // One line, so no backslash-newline can end up inside the JSON string: that is an invalid escape
    // and a defect in the test rather than in the route.
    let question = "What writes the canonical store, and is the release frozen?";
    let body =
        format!(r#"{{"knowledge_id":"{knowledge_id}","question":"{question}","timeout_s":120}}"#);
    let (status, body) = post(&router, "/api/v1/machine/answers", &body).await;

    match status {
        200 => {
            let value: serde_json::Value = serde_json::from_str(&body).unwrap();
            assert_eq!(value["schema"], "archeaxis.machine-answer/v1");
            assert_eq!(value["authority"], "candidate", "{body}");
            assert!(
                value["note"]
                    .as_str()
                    .unwrap()
                    .contains("not accepted knowledge"),
                "{body}"
            );
            let answer = value["answer"]["answer"].as_str().unwrap();
            assert!(
                !answer.trim().is_empty(),
                "an empty answer must never be a success"
            );
            // the receipt that travels with it must also say candidate
            assert_eq!(
                value["answer"]["loss_receipt"]["params"]["authority"],
                "candidate"
            );
            // and nothing may claim knowledge changed or a model was trained
            let lowered = body.to_lowercase();
            for forbidden in ["\"promoted\":true", "trained", "accuracy"] {
                assert!(
                    !lowered.contains(forbidden),
                    "{forbidden} appears in {body}"
                );
            }
        }
        503 => {
            // No model on this host is a real state, and the reason must be the worker's own.
            assert!(!body.trim().is_empty(), "a failure must name a reason");
        }
        other => panic!("unexpected status {other}: {body}"),
    }
}

#[tokio::test]
async fn persisted_answer_correction_review_and_retest_form_one_chain() {
    let (dir, router, id) = fixture().await;
    let request = serde_json::json!({"knowledge_id":id,"question":"what writes the store?"});
    let (status, answer) = post(&router, "/api/v1/machine/answers", &request.to_string()).await;
    assert_eq!(status, 200, "{answer}");
    let answer: serde_json::Value = serde_json::from_str(&answer).unwrap();
    let correction = serde_json::json!({"answer_id":answer["answer_id"],
        "knowledge_id":id,"question":request["question"],"machine_answer":answer["answer"]["answer"],
        "corrected_answer":"The Rust Core writes the SQLite store.", "error_note":"synthetic worker did not identify the writer"});
    let (status, correction) = post(
        &router,
        "/api/v1/machine/corrections",
        &correction.to_string(),
    )
    .await;
    assert_eq!(status, 200, "{correction}");
    let correction: serde_json::Value = serde_json::from_str(&correction).unwrap();
    let candidate = correction["correction_candidate_id"].as_str().unwrap();
    let retest = serde_json::json!({"retest_of":correction["failed_task_id"],
        "knowledge_id":candidate,"question":request["question"]});
    assert_eq!(
        post(&router, "/api/v1/machine/retests", &retest.to_string())
            .await
            .0,
        404
    );
    assert_eq!(
        post(
            &router,
            &format!("/api/v1/knowledge-items/{candidate}/review-decisions"),
            r#"{"action":"accepted","reviewer":"synthetic-human"}"#
        )
        .await
        .0,
        200
    );
    let (status, result) = post(&router, "/api/v1/machine/retests", &retest.to_string()).await;
    assert_eq!(status, 200, "{result}");
    let result: serde_json::Value = serde_json::from_str(&result).unwrap();
    assert_eq!(
        result["prior"]["conditions"]["answer_id"],
        answer["answer_id"]
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),
        "2"
    );
    // A wrong retest is another persisted answer; the same correction text must work again.
    let second = serde_json::json!({
        "answer_id": result["retest_task_id"], "knowledge_id": candidate,
        "question": request["question"], "machine_answer": result["answer"]["answer"],
        "corrected_answer": "The Rust Core writes the SQLite store.",
        "error_note": "synthetic retest still omitted the writer"
    });
    let (status, second) = post(&router, "/api/v1/machine/corrections", &second.to_string()).await;
    assert_eq!(status, 200, "{second}");
    let second: serde_json::Value = serde_json::from_str(&second).unwrap();
    assert_eq!(second["answer_id"], result["retest_task_id"]);
    assert_ne!(
        second["correction_candidate_id"],
        correction["correction_candidate_id"]
    );
    let second_id = second["correction_candidate_id"].as_str().unwrap();
    assert_eq!(
        post(
            &router,
            &format!("/api/v1/knowledge-items/{second_id}/review-decisions"),
            r#"{"action":"accepted","reviewer":"synthetic-human"}"#
        )
        .await
        .0,
        200
    );
    let second_retest = serde_json::json!({
        "retest_of": second["failed_task_id"], "knowledge_id": second_id,
        "question": request["question"]
    });
    let (status, response) = post(
        &router,
        "/api/v1/machine/retests",
        &second_retest.to_string(),
    )
    .await;
    assert_eq!(status, 200, "{response}");
}
