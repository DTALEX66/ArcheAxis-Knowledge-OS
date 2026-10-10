//! Canonical authored expression save/export/restart, distinct from derived canvas jobs.
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
async fn call(app: &Router, method: &str, path: &str, body: Value, actor: &str) -> (u16, Value) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}
fn editor() -> Value {
    json!({"type":"doc","attrs":{"archeaxis_expression":{"schema":"archeaxis.expression/v1","nodes":[{"id":"a","type":"text","x":-120,"y":30,"width":240,"height":100,"text":"中文表达\n原始文字"},{"id":"b","type":"text","x":200,"y":90,"width":180,"height":80,"text":"第二节点"}],"edges":[{"id":"edge","fromNode":"a","toNode":"b","label":"因果"}]}},"content":[]})
}
#[tokio::test]
async fn layout_restart_revision_and_reference_only_export_are_lossless() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("expression.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let body =
        json!({"create_request_id":"expression_attempt","title":"表达画布","editor_json":editor()});
    let (status, first) = call(&app, "POST", "/api/v1/documents", body.clone(), "human").await;
    assert_eq!(status, 201, "{first}");
    let (_, duplicate) = call(&app, "POST", "/api/v1/documents", body, "human").await;
    assert_eq!(duplicate, first);
    let path = format!(
        "/api/v1/documents/{}",
        first["document_id"].as_str().unwrap()
    );
    let mut next = first["editor_json"].clone();
    next["attrs"]["archeaxis_expression"]["nodes"][0]["text"] = json!("修订表达，知识正文保持原样");
    let (status, saved) = call(
        &app,
        "PUT",
        &format!("{path}/draft"),
        json!({"expected_version":1,"editor_json":next}),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{saved}");
    assert_eq!(saved["version"], 2);
    assert_eq!(
        call(
            &app,
            "PUT",
            &format!("{path}/draft"),
            json!({"expected_version":1,"editor_json":editor()}),
            "human"
        )
        .await
        .0,
        409
    );
    let (status, export) = call(
        &app,
        "GET",
        &format!("{path}/export?format=markdown"),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    let manifest: Value =
        serde_json::from_str(export["files"][1]["content"].as_str().unwrap()).unwrap();
    assert_eq!(manifest["document"], saved);
    assert_eq!(
        manifest["expression_export"]["content_sha256"],
        saved["content_sha256"]
    );
    assert_eq!(
        manifest["expression_export"]["media_packaging"],
        "reference_only"
    );
    assert_eq!(
        manifest["expression_export"]["engine_execution"],
        "NOT_EXECUTED"
    );
    assert!(
        manifest["loss"]
            .as_array()
            .unwrap()
            .iter()
            .any(|x| x["code"] == "expression_media_reference_only")
    );
    drop(app);
    let restarted = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(&restarted, "GET", &path, json!(null), "human").await.1,
        saved
    );
    assert_eq!(
        call(
            &restarted,
            "GET",
            &format!("{path}/versions/1"),
            json!(null),
            "human"
        )
        .await
        .1,
        first
    );
}
#[tokio::test]
async fn malformed_graph_and_missing_references_cannot_create_partial_documents() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("negative.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let mut cases = Vec::new();
    let mut e = editor();
    e["attrs"]["archeaxis_expression"]["edges"][0]["toNode"] = json!("missing");
    cases.push(e);
    let mut e = editor();
    e["attrs"]["archeaxis_expression"]["nodes"][1]["id"] = json!("a");
    cases.push(e);
    let mut e = editor();
    e["attrs"]["archeaxis_expression"]["nodes"][0]["x"] = json!(100001);
    cases.push(e);
    let mut e = editor();
    e["attrs"]["archeaxis_expression"]["context"] = json!({"knowledge_id":"missing"});
    cases.push(e);
    let mut e = editor();
    e["attrs"]["archeaxis_expression"]["schema"] = json!("archeaxis.expression/v99");
    cases.push(e);
    for (i, e) in cases.into_iter().enumerate() {
        let (status, value) = call(
            &app,
            "POST",
            "/api/v1/documents",
            json!({"create_request_id":format!("bad{i}"),"title":"bad","editor_json":e}),
            "human",
        )
        .await;
        assert_eq!(status, 400, "{value}");
    }
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/documents",
            json!({"title":"denied","editor_json":editor()}),
            "machine"
        )
        .await
        .0,
        403
    );
    let (_, list) = call(&app, "GET", "/api/v1/documents", json!(null), "human").await;
    assert_eq!(list["documents"], json!([]));
}
