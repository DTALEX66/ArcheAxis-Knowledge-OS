//! X05 slice B: HTTP import accepts optional origin metadata and retains it.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use base64::Engine;
use http_body_util::BodyExt;
use tower::ServiceExt;

use archeaxis_api::app;

async fn post_import(router: &axum::Router, body: &str) -> (StatusCode, serde_json::Value) {
    let resp = router
        .clone()
        .oneshot(
            Request::post("/api/v1/imports")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let value = serde_json::from_slice(&bytes).unwrap_or(serde_json::Value::Null);
    (status, value)
}

fn origins_for(conn: &rusqlite::Connection, source_id: &str) -> Vec<(String, String, Option<String>)> {
    let mut stmt = conn
        .prepare(
            "SELECT origin_kind, origin_ref, received_at FROM source_origins
             WHERE source_id=?1 ORDER BY origin_kind",
        )
        .unwrap();
    stmt.query_map([source_id], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .unwrap()
        .map(|r| r.unwrap())
        .collect()
}

#[tokio::test]
async fn import_with_origin_retains_url_and_path_origins() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();

    let bytes = b"provenance test bytes";
    let b64 = base64::engine::general_purpose::STANDARD.encode(bytes);

    // First import: url origin, received_at unknown -> NULL.
    let body1 = format!(
        r#"{{"name":"a.txt","content_base64":"{b64}","origin_kind":"url","origin_ref":"https://example.invalid/a.txt"}}"#
    );
    let (status, out1) = post_import(&router, &body1).await;
    assert!(
        status == StatusCode::ACCEPTED,
        "first import failed: status={status:?} body={out1} sent={body1}"
    );
    assert_eq!(out1["duplicate"], false);
    let sid = out1["source_id"].as_str().unwrap().to_string();

    // Second import: same bytes, path origin with explicit received_at.
    let body2 = format!(
        r#"{{"name":"a.txt","content_base64":"{b64}","origin_kind":"path","origin_ref":"D:\\notes\\a.txt","received_at":"2026-09-07T00:00:00Z"}}"#
    );
    let (status, out2) = post_import(&router, &body2).await;
    assert_eq!(status, StatusCode::ACCEPTED);
    assert_eq!(out2["duplicate"], true);
    assert_eq!(out2["source_id"].as_str(), Some(sid.as_str()));

    let conn = rusqlite::Connection::open(db.to_str().unwrap()).unwrap();
    let origins = origins_for(&conn, &sid);
    assert_eq!(origins.len(), 2);

    let url = origins.iter().find(|o| o.0 == "url").unwrap();
    assert_eq!(url.1, "https://example.invalid/a.txt");
    assert_eq!(url.2, None, "unknown received_at must stay NULL");

    let path = origins.iter().find(|o| o.0 == "path").unwrap();
    assert_eq!(path.2.as_deref(), Some("2026-09-07T00:00:00Z"));
}

#[tokio::test]
async fn import_rejects_invalid_or_partial_origin_fields() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let b64 = base64::engine::general_purpose::STANDARD.encode(b"x");

    let bad_kind = format!(r#"{{"name":"a","content_base64":"{b64}","origin_kind":"cloud","origin_ref":"r"}}"#);
    let (status, _) = post_import(&router, &bad_kind).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);

    let partial = format!(r#"{{"name":"a","content_base64":"{b64}","origin_kind":"url"}}"#);
    let (status, _) = post_import(&router, &partial).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
}
