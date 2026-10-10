//! G2: the vault member classification route, and the reason it exists.
//!
//! The assertion that matters most is the one about `.obsidian/workspace.json`. That file records
//! which notes a person had open, with absolute paths on their disk. Before this route nothing
//! distinguished it from a note, so a walk had no way to keep it out of the canonical store. The tests
//! below pin that, and pin that an unsafe path is refused rather than classified.

use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

async fn router() -> (tempfile::TempDir, Router) {
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
    (dir, archeaxis_api::runtime::router(executor))
}

async fn post(router: &Router, body: &str) -> (u16, serde_json::Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/vault/members")
                .header("content-type", "application/json")
                .body(Body::from(body.to_owned()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let value = serde_json::from_slice(&bytes).unwrap_or(serde_json::Value::Null);
    (status, value)
}

#[tokio::test]
async fn an_empty_member_list_is_refused() {
    let (_dir, router) = router().await;
    let (status, _) = post(&router, r#"{"members":[]}"#).await;
    assert_eq!(status, 422);
}

#[tokio::test]
async fn an_unknown_field_is_refused() {
    let (_dir, router) = router().await;
    // `vault_root` would be the Core starting to read a directory, which it does not do.
    let (status, _) = post(&router, r#"{"members":["a.md"],"vault_root":"/somewhere"}"#).await;
    assert_eq!(status, 422);
}

#[tokio::test]
async fn the_obsidian_workspace_file_is_application_state_not_knowledge() {
    // The finding this route exists for: workspace.json holds a person's open panes with absolute
    // paths, and importing it would file a private path as a claim about the world.
    let (_dir, router) = router().await;
    let body = serde_json::json!({
        "members": [".obsidian/workspace.json", ".obsidian/app.json", "notes/atomic.md"]
    })
    .to_string();
    let (status, value) = post(&router, &body).await;
    assert_eq!(status, 200, "{value}");
    assert_eq!(value["schema"], "archeaxis.vault-members/v1");

    let workspace = value["members"]
        .as_array()
        .unwrap()
        .iter()
        .find(|entry| entry["member"] == ".obsidian/workspace.json")
        .unwrap();
    assert_eq!(workspace["role"], "app_config", "{workspace}");
    assert_eq!(
        workspace["disposition"], "exclude_application_state",
        "{workspace}"
    );
    assert!(
        workspace["reason"]
            .as_str()
            .unwrap()
            .contains("application's own configuration")
    );

    assert_eq!(value["importable"], 1, "only the note is importable");
    assert_eq!(value["excluded_as_application_state"], 2, "{value}");
}

#[tokio::test]
async fn an_unsafe_path_is_refused_and_not_classified() {
    let (_dir, router) = router().await;
    let body = serde_json::json!({
        "members": ["C:/Users/somebody/notes.md", "notes/../../outside.md", "fine.md"]
    })
    .to_string();
    let (status, value) = post(&router, &body).await;
    assert_eq!(status, 200, "{value}");

    // Every member is reported, including the two refused ones: a caller has to see what it offered.
    assert_eq!(value["count"], 3, "{value}");
    assert_eq!(value["unsafe"].as_array().unwrap().len(), 2, "{value}");
    for entry in value["members"].as_array().unwrap() {
        if entry["member"] != "fine.md" {
            assert_eq!(entry["disposition"], "refuse", "{entry}");
            assert_eq!(
                entry["problems"].as_array().unwrap().is_empty(),
                false,
                "{entry}"
            );
        }
    }
    assert_eq!(value["importable"], 1, "{value}");
}

#[tokio::test]
async fn an_unrecognised_member_asks_for_a_human_rather_than_guessing() {
    let (_dir, router) = router().await;
    let body = serde_json::json!({"members": ["notes/thing.frobnicate"]}).to_string();
    let (status, value) = post(&router, &body).await;
    assert_eq!(status, 200, "{value}");
    assert_eq!(value["members"][0]["role"], "unknown", "{value}");
    assert_eq!(
        value["members"][0]["disposition"], "needs_a_human_decision",
        "{value}"
    );
    assert_eq!(value["needing_a_human_decision"], 1, "{value}");
}

#[tokio::test]
async fn the_response_states_that_it_reads_no_configuration() {
    // Classification is about names. The route must not be read as having interpreted anyone's
    // settings, and it must not be read as having walked anything.
    let (_dir, router) = router().await;
    let body = serde_json::json!({"members": [".obsidian/app.json"]}).to_string();
    let (_, value) = post(&router, &body).await;
    let gaps = value["not_done_here"].as_array().unwrap();
    assert!(
        gaps.iter()
            .any(|g| g.as_str().unwrap().contains("reading .obsidian/app.json"))
    );
    assert!(
        gaps.iter()
            .any(|g| g.as_str().unwrap().contains("walking a directory"))
    );
}

#[tokio::test]
async fn a_real_vault_shape_is_classified_as_expected() {
    // The shape of the fixture vault in the archive crate, plus the config directory such a vault
    // carries in practice.
    let (_dir, router) = router().await;
    let body = serde_json::json!({"members": [
        "notes/index.md",
        "notes/atomic.md",
        "attachments/diagram.png",
        "vault.canvas",
        ".obsidian/app.json",
        ".obsidian/workspace.json",
        ".obsidian/plugins/dataview/main.js",
        ".obsidian/themes/Minimal/theme.css",
        ".trash/old-note.md"
    ]})
    .to_string();
    let (status, value) = post(&router, &body).await;
    assert_eq!(status, 200, "{value}");
    assert_eq!(value["count"], 9, "{value}");
    assert_eq!(
        value["importable"], 4,
        "2 notes + 1 attachment + 1 canvas: {value}"
    );
    assert_eq!(value["excluded_as_application_state"], 5, "{value}");
    assert_eq!(value["counts"]["note"], 2, "{value}");
    assert_eq!(value["counts"]["app_config"], 5, "{value}");
}
