//! Real HTTP/CAS/Document consumer; no pre-inserted relationship fixtures.
use axum::{Router, body::Body, http::Request};
use base64::Engine;
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use tower::ServiceExt;

async fn call(app: &Router, method: &str, path: &str, body: Value) -> (u16, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes)
            .unwrap_or_else(|_| json!({"error":String::from_utf8_lossy(&bytes)})),
    )
}

#[tokio::test]
async fn imported_note_links_reach_the_existing_document_graph() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_, scope) = call(&app, "GET", "/api/v1/ingest-batches", Value::Null).await;
    let files = [
        ("notes/a.md", "See [[b]] and ![[image.svg]]."),
        ("notes/b.md", "Target note"),
        ("image.svg", "<svg/>"),
    ];
    let members: Vec<_> = files.iter().enumerate().map(|(i,(path, text))|
        json!({"ordinal":i,"relative_path":path,"byte_length":text.len(),"disposition":"pending"})).collect();
    let (status, manifest) = call(&app,"POST","/api/v1/ingest-batches",json!({
        "workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],
        "batch_id":"vault","folder_label":"selected-copy","expected_members":files.len(),"members":members})).await;
    assert_eq!(status, 200, "{manifest}");
    let mut imported = Vec::new();
    for (ordinal, (_, text)) in files.iter().enumerate() {
        let (status,source) = call(&app,"POST","/api/v1/ingest-batches/vault/imports",json!({
            "workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"ordinal":ordinal,
            "expected_sha256":format!("{:x}",Sha256::digest(text.as_bytes())),
            "content_base64":base64::engine::general_purpose::STANDARD.encode(text)})).await;
        assert_eq!(status, 202, "{source}");
        imported.push(source);
    }
    for source in &imported {
        let (status, actual) = call(
            &app,
            "GET",
            &format!("/api/v1/sources/{}", source["source_id"].as_str().unwrap()),
            Value::Null,
        )
        .await;
        assert_eq!(
            status, 200,
            "single-source identity must not require a capped listing: {actual}"
        );
        assert_eq!(actual["source_id"], source["source_id"]);
        assert_eq!(actual["source_revision"], source["sha256"]);
        assert_eq!(actual["sha256"], source["sha256"]);
        assert!(actual["imported_at"].is_string());
        assert!(actual["original_name"].is_string());
    }
    assert_eq!(
        call(&app, "GET", "/api/v1/sources/missing", Value::Null)
            .await
            .0,
        404
    );
    let mut docs = Vec::new();
    for ordinal in 0..2 {
        let (status,doc) = call(&app,"POST","/api/v1/documents",json!({
            "source_id":imported[ordinal]["source_id"],"source_revision":imported[ordinal]["sha256"],
            "title":files[ordinal].0,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":files[ordinal].1}]}]}})).await;
        assert_eq!(status, 201, "{doc}");
        docs.push(doc);
    }
    let path = format!(
        "/api/v1/documents/{}/relations",
        docs[0]["document_id"].as_str().unwrap()
    );
    let (_, before) = call(&app, "GET", &path, Value::Null).await;
    assert_eq!(
        before["edges"],
        json!([]),
        "import and ordinary document creation alone do not consume links"
    );
    let body = json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],
        "source_id":imported[0]["source_id"],"source_revision":imported[0]["sha256"],
        "document_id":docs[0]["document_id"],"expected_version":docs[0]["version"],"content_sha256":docs[0]["content_sha256"],
        "targets":[{"ordinal":1,"source_id":imported[1]["source_id"],"source_revision":imported[1]["sha256"],
            "document":{"document_id":docs[1]["document_id"],"version":1,"content_sha256":docs[1]["content_sha256"]}},
            {"ordinal":2,"source_id":imported[2]["source_id"],"source_revision":imported[2]["sha256"],"document":null}]});
    let mut stale_scope = body.clone();
    stale_scope["restore_epoch"] = json!("old-epoch");
    let (status, refused) = call(
        &app,
        "POST",
        "/api/v1/ingest-batches/vault/members/0/relations",
        stale_scope,
    )
    .await;
    assert_eq!(status, 409);
    assert_eq!(refused["code"], "AAK-INGEST-RELATION-001");
    assert!(
        refused.get("current_version").is_none(),
        "scope failure must not invent a zero Document version"
    );
    let (status, receipt) = call(
        &app,
        "POST",
        "/api/v1/ingest-batches/vault/members/0/relations",
        body.clone(),
    )
    .await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["added_relations"], 2);
    assert_eq!(receipt["input_kind"], "immutable_original_markdown");
    assert_eq!(
        receipt["document"]["editor_json"]["content"],
        docs[0]["editor_json"]["content"]
    );
    let (status, graph) = call(&app, "GET", &path, Value::Null).await;
    assert_eq!(status, 200, "{graph}");
    assert_eq!(
        graph["edges"].as_array().unwrap().len(),
        2,
        "real imported Markdown links are not consumed by the canonical graph: {graph}"
    );
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/ingest-batches/vault/members/0/relations",
            body.clone()
        )
        .await
        .0,
        409,
        "stale replay must not bypass expected version"
    );
    let mut fresh = body.clone();
    fresh["expected_version"] = receipt["document"]["version"].clone();
    fresh["content_sha256"] = receipt["document"]["content_sha256"].clone();
    let (status, repeat) = call(
        &app,
        "POST",
        "/api/v1/ingest-batches/vault/members/0/relations",
        fresh,
    )
    .await;
    assert_eq!(status, 200, "{repeat}");
    assert_eq!(repeat["added_relations"], 0);
    assert_eq!(repeat["document"], receipt["document"]);
    let mut unknown = body.clone();
    unknown["arbitrary_links"] = json!([]);
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/ingest-batches/vault/members/0/relations",
            unknown
        )
        .await
        .0,
        422
    );
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/ingest-batches/vault/members/0/relations")
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "machine")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status().as_u16(), 403);
    drop(app);
    let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status, after) = call(&reopened, "GET", &path, Value::Null).await;
    assert_eq!(status, 200);
    assert_eq!(after["edges"], graph["edges"]);
    assert_eq!(
        call(
            &reopened,
            "POST",
            "/api/v1/ingest-batches/vault/members/0/relations",
            body
        )
        .await
        .0,
        409
    );
}
