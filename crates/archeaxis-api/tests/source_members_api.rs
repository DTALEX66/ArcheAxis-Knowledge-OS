//! R15/F15: the container-to-member relation is visible through the API.
//!
//! A container's members are sources recorded with an `import` origin whose reference
//! names the container. `GET /api/v1/sources/:id/members` answers what is inside a
//! container and which parts could be read, so a reader sees both the members that were
//! read and the ones that were kept but not readable. The surface is tested here; the
//! pipeline that produces the relation is exercised end to end in the application
//! crate's `container_members` suite.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;
use archeaxis_domain::source::{self, ImportOutcome, OriginInfo};
use archeaxis_store_sqlite::init_workspace;

async fn get(router: &axum::Router, path: &str) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(Request::builder().uri(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

fn member_of(conn: &mut rusqlite::Connection, container: &str, name: &str, body: &[u8]) -> String {
    let outcome = source::import_source_with_origin(
        conn,
        body,
        name,
        None,
        Some(OriginInfo {
            kind: "import",
            origin_ref: &format!("{container}#{name}"),
            original_name: Some(name),
            received_at: None,
        }),
    )
    .unwrap();
    match outcome {
        ImportOutcome::Imported { source_id, .. } => source_id,
        ImportOutcome::Duplicate { source_id, .. } => source_id,
    }
}

#[tokio::test]
async fn a_containers_members_are_listed_with_their_readability() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let container_id = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let container = source::import_source(&mut conn, b"PK\x03\x04 container bytes", "bundle.zip", None).unwrap();
        let container_id = match container {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        let readable = member_of(&mut conn, &container_id, "notes/index.md", b"# Index\n6371 km\n");
        member_of(&mut conn, &container_id, "opaque/blob.bin", b"raw bytes\n");
        // the readable member really was read: a transform exists for it
        source::record_transform(
            &mut conn,
            &readable,
            "python-worker-text",
            "# Index\n6371 km\n",
            Some("none"),
        )
        .unwrap();
        container_id
    };

    let router = app(db.to_str().unwrap()).unwrap();
    let (status, payload) = get(&router, &format!("/api/v1/sources/{container_id}/members")).await;
    assert_eq!(status, StatusCode::OK, "{payload}");
    assert_eq!(payload["container_source_id"], container_id);
    assert_eq!(payload["member_count"], 2);
    assert_eq!(payload["readable_count"], 1);
    assert_eq!(payload["custody_only_count"], 1);

    let members = payload["members"].as_array().unwrap();
    let by_name: std::collections::BTreeMap<&str, &Value> = members
        .iter()
        .map(|member| (member["member"].as_str().unwrap(), member))
        .collect();
    assert!(by_name.contains_key("notes/index.md"), "{payload}");
    assert!(by_name.contains_key("opaque/blob.bin"), "{payload}");
    assert_eq!(by_name["notes/index.md"]["readable"], true);
    assert_eq!(by_name["opaque/blob.bin"]["readable"], false);
    assert_eq!(by_name["opaque/blob.bin"]["job_id"], Value::Null);
    assert_eq!(by_name["notes/index.md"]["sha256"].as_str().unwrap().len(), 64);

    // the note says what the list is and what "readable" means, so nobody reads it as
    // the container's whole inventory
    let note = payload["note"].as_str().unwrap();
    assert!(note.contains("not its whole inventory"), "{note}");
    assert!(note.contains("a transform exists"), "{note}");
}

#[tokio::test]
async fn an_unknown_source_is_a_named_not_found_and_an_unexpanded_container_is_empty() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let container_id = {
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        match source::import_source(&mut conn, b"PK\x03\x04 no members", "empty.zip", None).unwrap() {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        }
    };

    let router = app(db.to_str().unwrap()).unwrap();
    let (status, body) = get(&router, "/api/v1/sources/src_does_not_exist/members").await;
    assert_eq!(status, StatusCode::NOT_FOUND, "{body}");

    let (status, payload) = get(&router, &format!("/api/v1/sources/{container_id}/members")).await;
    assert_eq!(status, StatusCode::OK, "{payload}");
    assert_eq!(payload["member_count"], 0);
    assert_eq!(payload["readable_count"], 0);
    assert_eq!(payload["custody_only_count"], 0);
    assert!(payload["members"].as_array().unwrap().is_empty());
}
