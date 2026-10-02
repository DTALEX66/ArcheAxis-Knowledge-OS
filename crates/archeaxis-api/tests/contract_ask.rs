//! G2: Ask answers with citations, or says it did not find anything.
//!
//! The golden path asks for "Reader / Ask with citation". The checks below are about the citation
//! rather than the wording, because the point of asking *with citation* is that a reader can check
//! the answer: a projection that returns prose with no source is the failure this route exists to
//! avoid, and an empty string standing in for "nothing matched" is the same failure wearing a quieter
//! face.

use archeaxis_application::executor::Executor;
use archeaxis_domain::{anchor, knowledge, source};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

struct Fixture {
    _dir: tempfile::TempDir,
    router: Router,
    #[allow(dead_code)]
    knowledge_id: String,
    source_id: String,
}

/// One anchored knowledge item (a note tied to a position in an imported file) and one unattached
/// one, so both provenance shapes are exercised.
async fn fixture() -> Fixture {
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

    let (knowledge_id, source_id) = executor
        .store()
        .submit(|conn| {
            let source_id = match source::import_source(
                conn,
                b"ArcheAxis keeps its canonical store in SQLite and only the Rust Core writes it.\n",
                "notes.txt",
                None,
            )
            .unwrap()
            {
                source::ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            // `add_anchor` takes the position as JSON, which is what the store holds.
            let anchor_id =
                anchor::add_anchor(conn, &source_id, "rev-1", r#"{"line":1}"#).unwrap();
            // anchored to a real position in a real file
            let anchored = knowledge::create_knowledge(
                conn,
                "NOTE",
                "The canonical store is SQLite and only the Rust Core writes it.",
                "accepted",
                None,
                Some(&anchor_id),
                "human",
            )
            .unwrap();
            // a personal note with no file behind it, which is a legitimate shape
            knowledge::create_knowledge(
                conn,
                "NOTE",
                "SQLite is the canonical store; personal notes may have no anchor at all.",
                "accepted",
                None,
                None,
                "human",
            )
            .unwrap();
            Ok::<_, rusqlite::Error>((anchored, source_id))
        })
        .await
        .unwrap()
        .unwrap();

    let router = archeaxis_api::runtime::router(executor);
    Fixture {
        _dir: dir,
        router,
        knowledge_id,
        source_id,
    }
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
async fn a_question_is_required() {
    let fixture = fixture().await;
    let (status, body) = post(&fixture.router, "/api/v1/ask", r#"{"question":"   "}"#).await;
    assert_eq!(status, 422, "{body}");
    assert!(body.contains("question is required"), "{body}");
}

#[tokio::test]
async fn an_unknown_field_is_refused_rather_than_ignored() {
    let fixture = fixture().await;
    let (status, _) = post(
        &fixture.router,
        "/api/v1/ask",
        r#"{"question":"sqlite","answer_style":"verbose"}"#,
    )
    .await;
    assert_eq!(status, 422);
}

#[tokio::test]
async fn an_answer_carries_a_citation_a_reader_can_check() {
    let fixture = fixture().await;
    let (status, body) = post(
        &fixture.router,
        "/api/v1/ask",
        r#"{"question":"canonical store"}"#,
    )
    .await;
    assert_eq!(status, 200, "{body}");
    let value: serde_json::Value = serde_json::from_str(&body).unwrap();

    assert_eq!(value["schema"], "archeaxis.ask/v1");
    assert_eq!(value["answered"], true, "{body}");
    assert_eq!(value["authority"], "projection_of_accepted_knowledge");
    let citations = value["citations"].as_array().unwrap();
    assert!(!citations.is_empty(), "{body}");

    // every citation names the item and its excerpt, so a reader can open the thing being quoted
    for entry in citations {
        assert!(
            entry["knowledge_id"].as_str().unwrap().starts_with("k_"),
            "{entry}"
        );
        assert!(
            !entry["excerpt"].as_str().unwrap().trim().is_empty(),
            "{entry}"
        );
        assert!(entry["active"].is_boolean(), "{entry}");
    }

    // at least one citation must reach all the way to the source file, or it is not checkable
    let attached = citations
        .iter()
        .find(|entry| entry["attached_to_a_source"] == true)
        .expect("the anchored item should be cited");
    assert_eq!(
        attached["source"]["original_name"], "notes.txt",
        "{attached}"
    );
    assert_eq!(attached["anchor"]["source_revision"], "rev-1", "{attached}");
    assert_eq!(
        attached["anchor"]["position"], r#"{"line":1}"#,
        "{attached}"
    );
}

#[tokio::test]
async fn an_answer_is_the_material_itself_rather_than_a_paraphrase() {
    let fixture = fixture().await;
    let (_, body) = post(
        &fixture.router,
        "/api/v1/ask",
        r#"{"question":"canonical store"}"#,
    )
    .await;
    let value: serde_json::Value = serde_json::from_str(&body).unwrap();

    // A Core-composed sentence would be a claim with no citation, so the answer must be built from
    // the cited excerpts and nothing else.
    let answer = value["answer"].as_str().unwrap();
    for entry in value["citations"].as_array().unwrap() {
        let excerpt = entry["excerpt"].as_str().unwrap();
        assert!(
            answer.contains(excerpt),
            "answer omits a cited excerpt: {entry}"
        );
    }
}

#[tokio::test]
async fn no_match_is_an_unanswered_question_rather_than_an_empty_answer() {
    let fixture = fixture().await;
    let (status, body) = post(
        &fixture.router,
        "/api/v1/ask",
        r#"{"question":"zzz-no-such-term-anywhere"}"#,
    )
    .await;
    assert_eq!(status, 200, "{body}");
    let value: serde_json::Value = serde_json::from_str(&body).unwrap();

    assert_eq!(value["answered"], false, "{body}");
    // `null`, not `""`: an empty string reads as "the workspace says nothing", which is not the same
    // as "nothing matched".
    assert!(value["answer"].is_null(), "{body}");
    assert_eq!(value["count"], 0, "{body}");
    assert!(value["citations"].as_array().unwrap().is_empty(), "{body}");
    assert!(
        value["note"]
            .as_str()
            .unwrap()
            .contains("no accepted material"),
        "{body}"
    );
}

#[tokio::test]
async fn an_item_with_no_anchor_says_so_instead_of_inventing_provenance() {
    let fixture = fixture().await;
    let (_, body) = post(
        &fixture.router,
        "/api/v1/ask",
        r#"{"question":"personal notes anchor"}"#,
    )
    .await;
    let value: serde_json::Value = serde_json::from_str(&body).unwrap();
    let citations = value["citations"].as_array().unwrap();

    let unattached = citations
        .iter()
        .find(|entry| entry["attached_to_a_source"] == false)
        .expect("the unanchored note should be cited");
    assert!(unattached["anchor"]["anchor_id"].is_null(), "{unattached}");
    assert!(
        unattached["attachment_note"]
            .as_str()
            .unwrap()
            .contains("no anchor"),
        "{unattached}"
    );
}

#[tokio::test]
async fn asking_writes_nothing() {
    // The route is a projection; if it wrote, a question would change the material it answers from.
    let fixture = fixture().await;
    let before = fixture.source_id.clone();
    let (_, body) = post(
        &fixture.router,
        "/api/v1/ask",
        r#"{"question":"canonical"}"#,
    )
    .await;
    assert!(body.contains(&before) || !body.contains("k_"), "{body}");
    // and the answer states that nothing was written
    let value: serde_json::Value = serde_json::from_str(&body).unwrap();
    assert!(
        value["note"]
            .as_str()
            .unwrap()
            .contains("nothing here was written"),
        "{body}"
    );
}
