//! Evidence Center reads the anchors already persisted by the canonical Core.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_domain::{
    anchor,
    source::{self, ImportOutcome},
};
use archeaxis_store_sqlite::init_workspace;

#[tokio::test]
async fn evidence_anchor_list_projects_persisted_core_rows() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("evidence.sqlite");
    let source_id = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported =
            source::import_source(&mut conn, b"evidence body", "notes.md", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        anchor::add_anchor(
            &mut conn,
            &source_id,
            "rev-1",
            r#"{"paragraph":2,"offset":4}"#,
        )
        .unwrap();
        source_id
    };

    let response = app(db.to_str().unwrap())
        .unwrap()
        .oneshot(
            Request::get("/api/v1/evidence/anchors")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let payload: Value = serde_json::from_slice(&body).unwrap();

    assert_eq!(status, StatusCode::OK, "{payload}");
    assert_eq!(payload["items"][0]["source_id"], source_id);
    assert_eq!(payload["items"][0]["source_revision"], "rev-1");
    assert_eq!(
        payload["items"][0]["position"],
        r#"{"paragraph":2,"offset":4}"#
    );
    assert!(payload["items"][0]["raw_sha256"].as_str().unwrap().len() == 64);
    // The name the material was imported under, so a reader can name the thing cited
    // instead of only quoting an opaque source id back at them.
    assert_eq!(payload["items"][0]["source_name"], "notes.md");
    // A bare positional locator carries no selection, so the quote is explicitly null
    // rather than an empty string that would read as a quotation of nothing.
    assert!(payload["items"][0]["quote"].is_null());
    // Nothing cites this anchor yet, so the knowledge link is explicitly null too.
    assert!(payload["items"][0]["knowledge_id"].is_null());
    assert!(payload["items"][0]["knowledge_status"].is_null());
}

async fn anchors_payload(db: &std::path::Path) -> Value {
    let response = app(db.to_str().unwrap())
        .unwrap()
        .oneshot(
            Request::get("/api/v1/evidence/anchors")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body = response.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&body).unwrap()
}

#[tokio::test]
async fn evidence_anchor_list_surfaces_the_quoted_selection() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("evidence-quote.sqlite");
    {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let imported = source::import_source(&mut conn, b"quoted body", "quoted.md", None).unwrap();
        let source_id = match imported {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        anchor::add_anchor(
            &mut conn,
            &source_id,
            "rev-2",
            r#"{"quote":"the Earth radius is 6371 km","schema":"archeaxis.transform-text-selection/v1"}"#,
        )
        .unwrap();
    }

    let payload = anchors_payload(&db).await;
    assert_eq!(payload["items"][0]["source_name"], "quoted.md");
    assert_eq!(payload["items"][0]["quote"], "the Earth radius is 6371 km");
}
