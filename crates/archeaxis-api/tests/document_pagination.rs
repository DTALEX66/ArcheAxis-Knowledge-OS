use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
async fn get(router: &Router, path: &str) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(Request::builder().uri(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}
#[tokio::test]
async fn fixed_membership_pagination_survives_same_second_insertion_and_restart() {
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(database.to_str().unwrap()).unwrap();
    for index in 0..501 {
        archeaxis_domain::document::create_optional(
            &mut conn,
            None,
            None,
            &format!("document {index}"),
            json!({"type":"doc","content":[]}),
        )
        .unwrap();
    }
    conn.execute("UPDATE documents SET created_at='2026-10-09 00:00:00'", [])
        .unwrap();
    drop(conn);
    let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let (status, first) = get(&router, "/api/v1/documents").await;
    assert_eq!(status, 200);
    assert_eq!(first["snapshot_count"], 501);
    assert_eq!(first["documents"].as_array().unwrap().len(), 500);
    let cursor = first["next_cursor"].as_str().unwrap().to_owned();
    drop(router);
    let mut conn = archeaxis_store_sqlite::init_workspace(database.to_str().unwrap()).unwrap();
    let inserted = archeaxis_domain::document::create_optional(
        &mut conn,
        None,
        None,
        "new document",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    conn.execute("UPDATE documents SET created_at='2026-10-09 00:00:00'", [])
        .unwrap();
    let old_id = first["documents"][0]["document_id"].as_str().unwrap();
    archeaxis_domain::document::save(&mut conn,old_id,1,json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"changed"}]}]})).unwrap();
    drop(conn);
    let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let (status, second) = get(&router, &format!("/api/v1/documents?cursor={cursor}")).await;
    assert_eq!(status, 200);
    assert_eq!(second["snapshot_count"], 501);
    assert_eq!(second["next_cursor"], Value::Null);
    assert_eq!(second["documents"].as_array().unwrap().len(), 1);
    let ids: first_set::Ids = first["documents"]
        .as_array()
        .unwrap()
        .iter()
        .chain(second["documents"].as_array().unwrap())
        .map(|v| v["document_id"].as_str().unwrap().to_owned())
        .collect();
    assert_eq!(ids.len(), 501);
    assert!(!ids.contains(inserted["document_id"].as_str().unwrap()));
    let (status, historical) =
        get(&router, &format!("/api/v1/documents/{old_id}/versions/1")).await;
    assert_eq!(status, 200);
    assert_eq!(
        historical["content_sha256"],
        first["documents"][0]["content_sha256"]
    );
    assert_eq!(
        get(&router, "/api/v1/documents").await.1["snapshot_count"],
        502
    );
    assert_eq!(get(&router, "/api/v1/documents?cursor=bad").await.0, 400);
}
mod first_set {
    pub type Ids = std::collections::HashSet<String>;
}

#[tokio::test]
async fn legacy_ids_at_page_boundary_and_invalid_cursors() {
    use base64::Engine;
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(database.to_str().unwrap()).unwrap();
    for index in 0..501 {
        let created = archeaxis_domain::document::create_optional(
            &mut conn,
            None,
            None,
            "legacy",
            json!({"type":"doc","content":[]}),
        )
        .unwrap();
        let tx = conn.transaction().unwrap();
        tx.execute_batch("PRAGMA defer_foreign_keys=ON;").unwrap();
        let id = format!("legacy_{index:04}");
        let old = created["document_id"].as_str().unwrap();
        tx.execute(
            "UPDATE document_versions SET document_id=?1 WHERE document_id=?2",
            [&id, old],
        )
        .unwrap();
        tx.execute("UPDATE documents SET document_id=?1,created_at='2020-01-01T00:00:00Z' WHERE document_id=?2",[&id,old]).unwrap();
        tx.commit().unwrap();
    }
    drop(conn);
    let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let (_, first) = get(&router, "/api/v1/documents").await;
    let encoded = first["next_cursor"].as_str().unwrap();
    let mut cursor: Value = serde_json::from_slice(
        &base64::engine::general_purpose::URL_SAFE_NO_PAD
            .decode(encoded)
            .unwrap(),
    )
    .unwrap();
    assert_eq!(cursor["after_document_id"], "legacy_0499");
    assert_eq!(
        get(&router, &format!("/api/v1/documents?cursor={encoded}"))
            .await
            .1["documents"][0]["document_id"],
        "legacy_0500"
    );
    for (field, value) in [
        ("v", json!(2)),
        ("extra", json!(true)),
        ("after_document_id", json!("missing")),
        ("snapshot_count", json!(999)),
    ] {
        let mut invalid = cursor.clone();
        invalid[field] = value;
        let encoded = base64::engine::general_purpose::URL_SAFE_NO_PAD
            .encode(serde_json::to_vec(&invalid).unwrap());
        assert_eq!(
            get(&router, &format!("/api/v1/documents?cursor={encoded}"))
                .await
                .0,
            400
        );
    }
    cursor["after_created_at"] = json!("x".repeat(65));
    let encoded = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .encode(serde_json::to_vec(&cursor).unwrap());
    assert_eq!(
        get(&router, &format!("/api/v1/documents?cursor={encoded}"))
            .await
            .0,
        400
    );
}

#[tokio::test]
async fn exact_page_boundary_has_no_spurious_next_page() {
    for count in [0, 101, 500] {
        let dir = tempfile::tempdir().unwrap();
        let database = dir.path().join("workspace.sqlite");
        let mut conn = archeaxis_store_sqlite::init_workspace(database.to_str().unwrap()).unwrap();
        for index in 0..count {
            archeaxis_domain::document::create_optional(
                &mut conn,
                None,
                None,
                &format!("d{index}"),
                json!({"type":"doc","content":[]}),
            )
            .unwrap();
        }
        drop(conn);
        let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
        let (status, page) = get(&router, "/api/v1/documents").await;
        assert_eq!(status, 200);
        assert_eq!(page["snapshot_count"], count);
        assert_eq!(page["documents"].as_array().unwrap().len(), count as usize);
        assert_eq!(page["next_cursor"], Value::Null);
    }
}
