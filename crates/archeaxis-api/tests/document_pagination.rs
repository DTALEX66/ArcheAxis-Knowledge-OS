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
    assert!(
        first["documents"]
            .as_array()
            .unwrap()
            .iter()
            .all(|d| d["has_collection"] == false)
    );
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
    assert_eq!(second["documents"][0]["has_collection"], false);
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
async fn collection_presence_is_derived_from_the_current_saved_version_without_body_payloads_or_writes()
 {
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(database.to_str().unwrap()).unwrap();
    let definition = json!({"schema":"archeaxis.collection/v1","properties":[],"records":[],"views":[{"view_id":"table","name":"Table","kind":"table"}]});
    let plain = json!({"type":"doc","attrs":{"foreign":{"archeaxis_collection":definition.clone()}},"content":[]});
    let with_collection = json!({"type":"doc","attrs":{"foreign":{"keep":true},"archeaxis_collection":definition},"content":[]});
    let removed = archeaxis_domain::document::create_optional(
        &mut conn,
        None,
        None,
        "Removed",
        with_collection.clone(),
    )
    .unwrap();
    let added =
        archeaxis_domain::document::create_optional(&mut conn, None, None, "Added", plain.clone())
            .unwrap();
    let ordinary = archeaxis_domain::document::create_optional(
        &mut conn,
        None,
        None,
        "Ordinary",
        plain.clone(),
    )
    .unwrap();
    let removed = archeaxis_domain::document::save(
        &mut conn,
        removed["document_id"].as_str().unwrap(),
        1,
        plain,
    )
    .unwrap();
    let added = archeaxis_domain::document::save(
        &mut conn,
        added["document_id"].as_str().unwrap(),
        1,
        with_collection,
    )
    .unwrap();
    let original_counts: (i64, i64) = (
        conn.query_row("SELECT count(*) FROM documents", [], |r| r.get(0))
            .unwrap(),
        conn.query_row("SELECT count(*) FROM document_versions", [], |r| r.get(0))
            .unwrap(),
    );
    let summaries = archeaxis_domain::document::list(&conn).unwrap();
    assert_eq!(
        summaries
            .iter()
            .find(|r| r["document_id"] == added["document_id"])
            .unwrap()["has_collection"],
        true
    );
    drop(conn);
    for _ in 0..2 {
        let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
        let (status, page) = get(&router, "/api/v1/documents").await;
        assert_eq!(status, 200);
        assert_eq!(page["snapshot_count"], 3);
        for (document, has_collection) in [(&removed, false), (&added, true), (&ordinary, false)] {
            let summary = page["documents"]
                .as_array()
                .unwrap()
                .iter()
                .find(|r| r["document_id"] == document["document_id"])
                .unwrap();
            assert_eq!(summary["has_collection"], has_collection);
            assert_eq!(summary["version"], document["version"]);
            assert_eq!(summary["content_sha256"], document["content_sha256"]);
            assert!(
                summary.get("editor_json").is_none() && summary.get("text_projection").is_none()
            );
            let (status, readback) = get(
                &router,
                &format!(
                    "/api/v1/documents/{}",
                    document["document_id"].as_str().unwrap()
                ),
            )
            .await;
            assert_eq!(status, 200);
            assert_eq!(readback, *document);
        }
        drop(router);
    }
    let conn = archeaxis_store_sqlite::init_workspace(database.to_str().unwrap()).unwrap();
    let after: (i64, i64) = (
        conn.query_row("SELECT count(*) FROM documents", [], |r| r.get(0))
            .unwrap(),
        conn.query_row("SELECT count(*) FROM document_versions", [], |r| r.get(0))
            .unwrap(),
    );
    assert_eq!(after, original_counts);
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
