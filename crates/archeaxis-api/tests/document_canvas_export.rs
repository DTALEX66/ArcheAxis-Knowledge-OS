//! Authored Canvas editing/export through Core APIs; no UI or external file access.
use axum::{Router, body::Body, http::Request};
use base64::Engine;
use http_body_util::BodyExt;
use serde_json::{Value, json};
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
            .unwrap_or_else(|_| json!({"raw":String::from_utf8_lossy(&bytes)})),
    )
}

fn canvas() -> Value {
    json!({"plugin:root":{"opaque":[true,"中文"]},"nodes":[
    {"id":"first","type":"text","x":-10,"y":15,"width":200,"height":100,"text":"原第一段🙂","plugin:node":{"preserve":true}},
    {"id":"group","type":"group","x":0,"y":0,"width":800,"height":600,"label":"组","background":"private/unused.png","backgroundStyle":"cover"},
    {"id":"second","type":"text","x":300,"y":0,"width":200,"height":100,"text":"原第二段"},
    {"id":"file","type":"file","x":0,"y":200,"width":200,"height":100,"file":"../未读取.pdf","subpath":"#^block"},
    {"id":"link","type":"link","x":0,"y":350,"width":200,"height":100,"url":"plugin://unopened","plugin:unknown":"kept"}],
    "edges":[{"id":"edge","fromNode":"first","toNode":"file","fromSide":"right","toSide":"left","toEnd":"arrow","label":"证据","plugin:edge":[1,2]}]})
}

fn editor(first: &str, second: &str) -> Value {
    json!({"type":"doc","content":[
    {"type":"paragraph","attrs":{"canvas_node_id":"first"},"content":[{"type":"text","text":first}]},
    {"type":"paragraph","attrs":{"canvas_node_id":"second"},"content":[{"type":"text","text":second}]}]})
}

fn exported_canvas(value: &Value) -> Value {
    assert_eq!(value["format"], "canvas");
    assert_eq!(value["files"][0]["path"], "document.canvas");
    serde_json::from_str(value["files"][0]["content"].as_str().unwrap()).unwrap()
}

#[tokio::test]
async fn edited_canvas_preserves_structure_source_and_current_text_across_restart_and_package_restore()
 {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("canvas.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let original = canvas();
    let raw = serde_json::to_vec(&original).unwrap();
    let (status,source)=call(&app,"POST","/api/v1/imports",json!({"name":"authored.canvas","content_base64":base64::engine::general_purpose::STANDARD.encode(&raw)})).await;
    assert_eq!(status, 202, "{source}");
    let (status,created)=call(&app,"POST","/api/v1/documents",json!({"title":"Canvas","source_id":source["source_id"],"source_revision":source["sha256"],"editor_json":editor("原第一段🙂","原第二段")})).await;
    assert_eq!(status, 201, "{created}");
    let route = format!(
        "/api/v1/documents/{}",
        created["document_id"].as_str().unwrap()
    );
    let mut edited = editor("已编辑中文🙂\n新行", "第二段也已编辑");
    edited["content"][0]["content"][0]["marks"] = json!([
        {"type":"link","attrs":{"href":"https://example.invalid/not-followed"}},
        {"type":"bold"}]);
    edited["content"][1]["type"] = json!("codeBlock");
    edited["content"][1]["attrs"]["language"] = json!("rust");
    let (status, saved) = call(
        &app,
        "PUT",
        &format!("{route}/draft"),
        json!({"expected_version":1,"editor_json":edited}),
    )
    .await;
    assert_eq!(status, 200, "{saved}");
    assert_eq!(saved["version"], 2);
    let export_path = format!("{route}/export?format=canvas");
    let (status, export) = call(&app, "GET", &export_path, Value::Null).await;
    assert_eq!(status, 200, "{export}");
    let mut expected = original.clone();
    expected["nodes"][0]["text"] = json!("已编辑中文🙂\n新行");
    expected["nodes"][2]["text"] = json!("第二段也已编辑");
    assert_eq!(exported_canvas(&export), expected);
    let manifest: Value =
        serde_json::from_str(export["files"][1]["content"].as_str().unwrap()).unwrap();
    assert_eq!(manifest["document"], saved);
    assert_eq!(
        manifest["reconstruction_scope"],
        "TEXT_NODE_PLAIN_TEXT_ONLY"
    );
    assert_eq!(
        manifest["document"]["editor_json"]["content"][0]["content"][0]["marks"],
        edited["content"][0]["content"][0]["marks"]
    );
    assert_eq!(
        manifest["document"]["editor_json"]["content"][1]["attrs"]["language"],
        "rust"
    );
    let text_loss = manifest["loss"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["code"] == "text_node_plain_projection")
        .unwrap()["message"]
        .as_str()
        .unwrap();
    assert!(text_loss.contains("link hrefs") && text_loss.contains("code-block language"));
    assert!(
        manifest["loss"]
            .as_array()
            .unwrap()
            .iter()
            .any(|v| v["code"] == "references_only")
    );
    let original_path = format!(
        "/api/v1/sources/{}/original",
        source["source_id"].as_str().unwrap()
    );
    let (status, original_read) = call(&app, "GET", &original_path, Value::Null).await;
    assert_eq!(status, 200);
    assert_eq!(
        base64::engine::general_purpose::STANDARD
            .decode(original_read["content_base64"].as_str().unwrap())
            .unwrap(),
        raw
    );
    assert_eq!(
        call(
            &app,
            "PUT",
            &format!("{route}/draft"),
            json!({"expected_version":1,"editor_json":editor("stale","stale")})
        )
        .await
        .0,
        409
    );
    let (status, package) = call(&app, "GET", &format!("{route}/package"), Value::Null).await;
    assert_eq!(status, 200, "{package}");
    drop(app);
    let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(&reopened, "GET", &export_path, Value::Null).await,
        (200, export)
    );
    let target = dir.path().join("independent.sqlite");
    let restored = archeaxis_api::app(target.to_str().unwrap()).unwrap();
    let (status, imported) = call(
        &restored,
        "POST",
        "/api/v1/document-packages/import",
        json!({"request_id":"canvas-independent-restore","package":package}),
    )
    .await;
    assert_eq!(status, 201, "{imported}");
    let restored_path = format!(
        "/api/v1/documents/{}/export?format=canvas",
        imported["document"]["document_id"].as_str().unwrap()
    );
    let (status, reexport) = call(&restored, "GET", &restored_path, Value::Null).await;
    assert_eq!(status, 200, "{reexport}");
    assert_eq!(exported_canvas(&reexport), expected);
}

#[tokio::test]
async fn canvas_export_refuses_ambiguous_editor_without_blocking_ordinary_save_or_markdown() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("bad-mapping.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_,source)=call(&app,"POST","/api/v1/imports",json!({"name":"authored.canvas","content_base64":base64::engine::general_purpose::STANDARD.encode(canvas().to_string())})).await;
    let (_,created)=call(&app,"POST","/api/v1/documents",json!({"title":"Ordinary document","source_id":source["source_id"],"source_revision":source["sha256"],"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"未映射仍可普通保存"}]}]}})).await;
    let route = format!(
        "/api/v1/documents/{}",
        created["document_id"].as_str().unwrap()
    );
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{route}/export?format=canvas"),
            Value::Null
        )
        .await
        .0,
        400
    );
    for format in ["markdown", "obsidian"] {
        assert_eq!(
            call(
                &app,
                "GET",
                &format!("{route}/export?format={format}"),
                Value::Null
            )
            .await
            .0,
            200
        );
    }
    assert_eq!(call(&app, "GET", &route, Value::Null).await, (200, created));
    let (_, manual) = call(
        &app,
        "POST",
        "/api/v1/documents",
        json!({"title":"No source","editor_json":editor("a","b")}),
    )
    .await;
    assert_eq!(
        call(
            &app,
            "GET",
            &format!(
                "/api/v1/documents/{}/export?format=canvas",
                manual["document_id"].as_str().unwrap()
            ),
            Value::Null
        )
        .await
        .0,
        400
    );
}
