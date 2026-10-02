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
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/machine/worker_machine_answer.py");
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
        format!(r#"{{"knowledge_id":"{knowledge_id}","question":"{question}","timeout_s":600}}"#);
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
