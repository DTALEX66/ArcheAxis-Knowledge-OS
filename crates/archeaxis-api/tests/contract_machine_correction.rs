//! G4's human half: a person finds a real error in a machine answer and records the correction.
//!
//! The checks are about what the loop must not allow. A correction that a machine can write, that
//! omits what was wrong, or that arrives already accepted would remove the human step the gate
//! exists for - so each of those is refused explicitly rather than left to convention.

use archeaxis_application::executor::Executor;
use archeaxis_domain::knowledge;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

async fn fixture() -> (tempfile::TempDir, Router, String) {
    let dir = tempfile::tempdir().unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let transport = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &transport,
    )
    .await
    .unwrap();

    let knowledge_id = executor
        .store()
        .submit(|conn| {
            knowledge::create_knowledge(
                conn,
                "NOTE",
                "The canonical store is SQLite and only the Rust Core writes it.",
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

fn body(knowledge_id: &str, overrides: &[(&str, &str)]) -> String {
    let mut fields = vec![
        ("knowledge_id".to_string(), knowledge_id.to_string()),
        ("question".to_string(), "What writes the store?".to_string()),
        (
            "machine_answer".to_string(),
            "Postgres writes the canonical store.".to_string(),
        ),
        (
            "corrected_answer".to_string(),
            "The Rust Core writes the SQLite canonical store.".to_string(),
        ),
        (
            "error_note".to_string(),
            "the model named a database that is not used here".to_string(),
        ),
    ];
    for (key, value) in overrides {
        if let Some(slot) = fields.iter_mut().find(|(name, _)| name == key) {
            slot.1 = (*value).to_string();
        }
    }
    let inner: Vec<String> = fields
        .iter()
        .map(|(key, value)| format!("{key:?}: {value:?}"))
        .collect();
    format!("{{{}}}", inner.join(","))
}

async fn post(router: &Router, path: &str, body: &str, actor: Option<&str>) -> (u16, String) {
    let mut builder = Request::builder()
        .method("POST")
        .uri(path)
        .header("content-type", "application/json");
    if let Some(actor) = actor {
        builder = builder.header("x-archeaxis-actor", actor);
    }
    let response = router
        .clone()
        .oneshot(builder.body(Body::from(body.to_owned())).unwrap())
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8_lossy(&bytes).to_string())
}

#[tokio::test]
async fn a_correction_records_the_pair_and_stays_a_candidate() {
    let (_dir, router, knowledge_id) = fixture().await;
    let (status, text) = post(
        &router,
        "/api/v1/machine/corrections",
        &body(&knowledge_id, &[]),
        None,
    )
    .await;
    assert_eq!(status, 200, "{text}");
    let value: serde_json::Value = serde_json::from_str(&text).unwrap();

    assert_eq!(value["schema"], "archeaxis.machine-correction/v1");
    // the model's own words travel with the correction, so a reviewer reads what was said
    assert_eq!(
        value["machine_answer"],
        "Postgres writes the canonical store."
    );
    assert_eq!(
        value["error_note"],
        "the model named a database that is not used here"
    );
    assert_eq!(value["corrects_knowledge_id"], knowledge_id);

    // and it is a candidate, with the promotion path named
    assert_eq!(value["status"], "candidate", "{text}");
    assert_eq!(value["authority"], "candidate", "{text}");
    assert!(
        value["promotion"]
            .as_str()
            .unwrap()
            .contains("not knowledge until a human accepts"),
        "{text}"
    );
    assert!(
        value["correction_candidate_id"]
            .as_str()
            .unwrap()
            .starts_with("k_")
    );
}

#[tokio::test]
async fn a_machine_principal_cannot_correct_itself() {
    // A machine that could record a correction would close the loop without a person, which is the
    // step the gate exists for.
    let (_dir, router, knowledge_id) = fixture().await;
    let (status, text) = post(
        &router,
        "/api/v1/machine/corrections",
        &body(&knowledge_id, &[]),
        Some("machine"),
    )
    .await;
    assert_eq!(status, 403, "{text}");
    assert!(text.contains("a correction is a human act"), "{text}");
}

#[tokio::test]
async fn a_correction_without_the_specific_error_is_refused() {
    // "it was wrong" is not a reviewable finding: a later reviewer would have to guess.
    let (_dir, router, knowledge_id) = fixture().await;
    let (status, text) = post(
        &router,
        "/api/v1/machine/corrections",
        &body(&knowledge_id, &[("error_note", "   ")]),
        None,
    )
    .await;
    assert_eq!(status, 422, "{text}");
    assert!(text.contains("error_note is required"), "{text}");
}

#[tokio::test]
async fn a_correction_without_the_machine_answer_is_refused() {
    // Without the model's answer the pair cannot be reviewed as a pair, and the record would be a
    // claim about a statement nobody can read.
    let (_dir, router, knowledge_id) = fixture().await;
    let (status, text) = post(
        &router,
        "/api/v1/machine/corrections",
        &body(&knowledge_id, &[("machine_answer", "")]),
        None,
    )
    .await;
    assert_eq!(status, 422, "{text}");
    assert!(text.contains("machine_answer is required"), "{text}");
}

#[tokio::test]
async fn a_correction_about_nothing_is_a_not_found() {
    let (_dir, router, _) = fixture().await;
    let (status, text) = post(
        &router,
        "/api/v1/machine/corrections",
        &body("k_does_not_exist", &[]),
        None,
    )
    .await;
    assert_eq!(status, 404, "{text}");
    assert!(text.contains("no knowledge item"), "{text}");
}

#[tokio::test]
async fn the_correction_can_be_promoted_only_by_human_review() {
    // The whole point of writing it as a candidate is that something else has to accept it. This
    // pins the second half: the promotion route exists and refuses a machine principal.
    let (_dir, router, knowledge_id) = fixture().await;
    let (_, text) = post(
        &router,
        "/api/v1/machine/corrections",
        &body(&knowledge_id, &[]),
        None,
    )
    .await;
    let candidate =
        serde_json::from_str::<serde_json::Value>(&text).unwrap()["correction_candidate_id"]
            .as_str()
            .unwrap()
            .to_string();

    // a machine may not accept it
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!(
                    "/api/v1/knowledge-items/{candidate}/review-decisions"
                ))
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "machine")
                .body(Body::from(r#"{"action":"accepted","reviewer":"machine"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(
        response.status().as_u16(),
        403,
        "a machine principal must not accept its own correction"
    );

    // a human may
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!(
                    "/api/v1/knowledge-items/{candidate}/review-decisions"
                ))
                .header("content-type", "application/json")
                .body(Body::from(r#"{"action":"accepted","reviewer":"owner"}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(
        response.status().as_u16(),
        200,
        "a human review must be able to promote it"
    );
}
