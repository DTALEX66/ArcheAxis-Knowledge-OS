//! G2: the vault link route reports what a note declares, and does not pretend to store it.
//!
//! The interesting assertion is the negative one. `obsidian_vault_roundtrip.rs` says no table stores a
//! link or embed relationship, and a route that returned a tidy graph could easily be read as "the
//! graph is now in the database". So the response has to say what it did not do, and that has to be
//! checked rather than hoped for.

use archeaxis_application::executor::Executor;
use archeaxis_domain::knowledge;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

const NOTE: &str = "---\ntitle: Canonical writer\ntags: [aaos]\n---\n\n# Canonical writer\n\n\
Only the Rust Core writes the store. See [[Knowledge Version]], [[Evidence Anchor|the anchor]] \
and [[Note#Heading|see here]]. A tag appears as #aaos.\n\n![[diagram.png]]\n\n\
See also [the note](notes/atomic.md) and [docs](https://example.com).\n";

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
            knowledge::create_knowledge(conn, "NOTE", NOTE, "accepted", None, None, "human")
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
async fn neither_a_note_nor_an_id_is_refused_rather_than_answered_with_an_empty_graph() {
    let (_dir, router, _) = fixture().await;
    let (status, text) = post(&router, "/api/v1/vault/links", "{}").await;
    assert_eq!(status, 422, "{text}");
    assert!(text.contains("either markdown or knowledge_id"), "{text}");
}

#[tokio::test]
async fn a_raw_note_is_parsed_without_touching_the_store() {
    let (_dir, router, _) = fixture().await;
    let body = serde_json::json!({"markdown": "[[One]] and ![[Two]]"}).to_string();
    let (status, text) = post(&router, "/api/v1/vault/links", &body).await;
    assert_eq!(status, 200, "{text}");
    let value: serde_json::Value = serde_json::from_str(&text).unwrap();
    assert_eq!(value["schema"], "archeaxis.vault-links/v1");
    assert_eq!(value["count"], 2, "{text}");
    assert_eq!(value["embeds"], 1, "{text}");
    // no knowledge item was named, so none is claimed
    assert!(value["knowledge_id"].is_null(), "{text}");
}

#[tokio::test]
async fn a_knowledge_items_own_body_can_be_parsed() {
    let (_dir, router, knowledge_id) = fixture().await;
    let body = serde_json::json!({"knowledge_id": knowledge_id}).to_string();
    let (status, text) = post(&router, "/api/v1/vault/links", &body).await;
    assert_eq!(status, 200, "{text}");
    let value: serde_json::Value = serde_json::from_str(&text).unwrap();
    assert_eq!(value["knowledge_id"], knowledge_id, "{text}");

    let targets: Vec<String> = value["links"]
        .as_array()
        .unwrap()
        .iter()
        .map(|link| link["target"].as_str().unwrap().to_string())
        .collect();
    // the three wiki-links, the one embed and the one internal markdown link; the external URL is not
    // a vault relationship and must not appear
    assert!(
        targets.contains(&"Knowledge Version".to_string()),
        "{targets:?}"
    );
    assert!(
        targets.contains(&"Evidence Anchor".to_string()),
        "{targets:?}"
    );
    assert!(targets.contains(&"Note".to_string()), "{targets:?}");
    assert!(targets.contains(&"diagram.png".to_string()), "{targets:?}");
    assert!(
        targets.contains(&"notes/atomic.md".to_string()),
        "{targets:?}"
    );
    assert!(
        !targets.iter().any(|t| t.contains("example.com")),
        "{targets:?}"
    );
}

#[tokio::test]
async fn an_unknown_knowledge_item_is_a_not_found() {
    let (_dir, router, _) = fixture().await;
    let body = serde_json::json!({"knowledge_id": "k_does_not_exist"}).to_string();
    let (status, text) = post(&router, "/api/v1/vault/links", &body).await;
    assert_eq!(status, 404, "{text}");
    assert!(text.contains("no knowledge item"), "{text}");
}

#[tokio::test]
async fn a_url_is_not_reported_as_a_vault_relationship() {
    let (_dir, router, _) = fixture().await;
    let body = serde_json::json!({"markdown": "[docs](https://example.com) [mail](mailto:a@b.c)"})
        .to_string();
    let (status, text) = post(&router, "/api/v1/vault/links", &body).await;
    assert_eq!(status, 200, "{text}");
    let value: serde_json::Value = serde_json::from_str(&text).unwrap();
    assert_eq!(value["count"], 0, "{text}");
}

#[tokio::test]
async fn the_response_states_that_the_graph_is_not_stored() {
    // This is the assertion that matters. The vault round-trip test names the gap; a route returning a
    // clean graph must not close the gap by implication.
    let (_dir, router, knowledge_id) = fixture().await;
    let body = serde_json::json!({"knowledge_id": knowledge_id}).to_string();
    let (_, text) = post(&router, "/api/v1/vault/links", &body).await;
    let value: serde_json::Value = serde_json::from_str(&text).unwrap();

    let gaps = value["not_done_here"].as_array().unwrap();
    assert!(
        gaps.iter()
            .any(|gap| gap.as_str().unwrap().contains("persisting the graph")),
        "{text}"
    );
    // and every link says it was not resolved, so a reader cannot think the target was checked
    for link in value["links"].as_array().unwrap() {
        assert_eq!(link["resolved"], false, "{link}");
    }
}

#[tokio::test]
async fn an_unknown_field_is_refused() {
    let (_dir, router, _) = fixture().await;
    let body = serde_json::json!({"markdown": "[[a]]", "vault_root": "/somewhere"}).to_string();
    let (status, _) = post(&router, "/api/v1/vault/links", &body).await;
    // a `vault_root` would be the Core starting to read a directory, which it does not do
    assert_eq!(status, 422);
}
