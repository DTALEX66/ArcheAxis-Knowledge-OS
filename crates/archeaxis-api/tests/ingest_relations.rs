//! Real HTTP/CAS/Document consumer; no pre-inserted relationship fixtures.
use axum::{Router, body::Body, http::Request};
use base64::Engine;
use http_body_util::BodyExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use tower::ServiceExt;

#[tokio::test]
async fn fragment_review_invalid_targets_leave_the_same_store_writer_usable() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("parser-review.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_, scope) = call(&app, "GET", "/api/v1/ingest-batches", Value::Null).await;
    for (case, (text, fragment, block)) in [
        ("`a\n中`# Heading", "Heading", false),
        ("text ^named\n`abc` ^named", "named", true),
        ("text ^named `abc`", "named", true),
        ("<!--\n# Heading\n-->", "Heading", false),
        ("<!--\ntext ^named\n-->", "named", true),
        ("> ~~~\n> text ^named\n> ~~~", "named", true),
    ]
    .into_iter()
    .enumerate()
    {
        let batch = format!("parser-review-{case}");
        let link = format!("[[peer#{}{fragment}]]", if block { "^" } else { "" });
        let files = [("index.md", link.as_str()), ("peer.md", text)];
        let members: Vec<_> = files.iter().enumerate().map(|(i, (path, text))|json!({"ordinal":i,"relative_path":path,"byte_length":text.len(),"disposition":"pending"})).collect();
        assert_eq!(call(&app,"POST","/api/v1/ingest-batches",json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"batch_id":batch,"folder_label":"parser-review","expected_members":2,"members":members})).await.0, 200);
        let mut sources = Vec::new();
        let mut docs = Vec::new();
        for (ordinal, (path, content)) in files.iter().enumerate() {
            let (status, source) = call(&app,"POST",&format!("/api/v1/ingest-batches/{batch}/imports"),json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"ordinal":ordinal,"expected_sha256":format!("{:x}",Sha256::digest(content.as_bytes())),"content_base64":base64::engine::general_purpose::STANDARD.encode(content)})).await;
            assert_eq!(status, 202, "{source}");
            let (status, doc) = call(&app,"POST","/api/v1/documents",json!({"source_id":source["source_id"],"source_revision":source["sha256"],"title":path,"editor_json":{"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"selected_block"},"content":[{"type":"text","text":content}]}]}})).await;
            assert_eq!(status, 201, "{doc}");
            sources.push(source);
            docs.push(doc);
        }
        let request = json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"source_id":sources[0]["source_id"],"source_revision":sources[0]["sha256"],"document_id":docs[0]["document_id"],"expected_version":1,"content_sha256":docs[0]["content_sha256"],"targets":[{"ordinal":1,"source_id":sources[1]["source_id"],"source_revision":sources[1]["sha256"],"document":{"document_id":docs[1]["document_id"],"version":1,"content_sha256":docs[1]["content_sha256"]}}],"fragment_bindings":[{"link_ordinal":0,"target_ordinal":1,"fragment":fragment,"fragment_is_block":block,"block_id":"selected_block"}]});
        let (status, refused) = call(
            &app,
            "POST",
            &format!("/api/v1/ingest-batches/{batch}/members/0/relations"),
            request,
        )
        .await;
        // Exercise the same Store after the potentially hostile parser input, before asserting
        // rejection, so a writer-thread panic is visible as a second failed operation.
        let (save_status, saved) = call(&app,"POST","/api/v1/documents",json!({"title":"After rejected fragment","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Writer remains usable"}]}]}})).await;
        assert_eq!(
            save_status, 201,
            "case {case}: rejected={status} {refused}; save={saved}"
        );
        assert_eq!(status, 400, "case {case}: {refused}");
        let document_path = format!(
            "/api/v1/documents/{}",
            docs[0]["document_id"].as_str().unwrap()
        );
        assert_eq!(
            call(&app, "GET", &document_path, Value::Null).await.1,
            docs[0]
        );
        let graph_path = format!("{document_path}/relations");
        assert_eq!(
            call(&app, "GET", &graph_path, Value::Null).await.1["edges"],
            json!([])
        );
    }
}

#[tokio::test]
async fn explicit_fragment_mapping_pins_a_real_block_at_the_existing_http_boundary() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("fragments.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_, scope) = call(&app, "GET", "/api/v1/ingest-batches", Value::Null).await;
    let files = [
        (
            "index.md",
            "[[peer#Heading]] [[peer#^named]] [[peer#unmapped]]",
        ),
        ("peer.md", "# Heading\nContent ^named"),
    ];
    let members:Vec<_> = files.iter().enumerate().map(|(i,(path,text))|json!({"ordinal":i,"relative_path":path,"byte_length":text.len(),"disposition":"pending"})).collect();
    let (status, _) = call(&app,"POST","/api/v1/ingest-batches",json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"batch_id":"fragments","folder_label":"selected-copy","expected_members":2,"members":members})).await;
    assert_eq!(status, 200);
    let mut sources = Vec::new();
    let mut docs = Vec::new();
    for (ordinal, (path, text)) in files.iter().enumerate() {
        let (status,source)=call(&app,"POST","/api/v1/ingest-batches/fragments/imports",json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"ordinal":ordinal,"expected_sha256":format!("{:x}",Sha256::digest(text.as_bytes())),"content_base64":base64::engine::general_purpose::STANDARD.encode(text)})).await;
        assert_eq!(status, 202, "{source}");
        let (status,doc)=call(&app,"POST","/api/v1/documents",json!({"source_id":source["source_id"],"source_revision":source["sha256"],"title":path,"editor_json":{"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"selected_block"},"content":[{"type":"text","text":text}]}]}})).await;
        assert_eq!(status, 201, "{doc}");
        sources.push(source);
        docs.push(doc);
    }
    let mut request = json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"source_id":sources[0]["source_id"],"source_revision":sources[0]["sha256"],"document_id":docs[0]["document_id"],"expected_version":1,"content_sha256":docs[0]["content_sha256"],"targets":[{"ordinal":1,"source_id":sources[1]["source_id"],"source_revision":sources[1]["sha256"],"document":{"document_id":docs[1]["document_id"],"version":1,"content_sha256":docs[1]["content_sha256"]}}],"fragment_bindings":[{"link_ordinal":0,"target_ordinal":1,"fragment":"Heading","fragment_is_block":false,"block_id":"selected_block"},{"link_ordinal":1,"target_ordinal":1,"fragment":"named","fragment_is_block":true,"block_id":"selected_block"}]});
    let path = "/api/v1/ingest-batches/fragments/members/0/relations";
    let (status, receipt) = call(&app, "POST", path, request.clone()).await;
    assert_eq!(
        status, 200,
        "explicit mapping must reach the existing writer: {receipt}"
    );
    assert_eq!(receipt["added_relations"], 2, "{receipt}");
    assert_eq!(
        receipt["links"][2]["reason"],
        "fragment_resolution_not_supported"
    );
    let reference = json!({"kind":"document","document_id":docs[1]["document_id"],"version":1,"block_id":"selected_block"});
    assert_eq!(
        receipt["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"][0]["target"],
        reference
    );
    assert_eq!(call(&app, "POST", path, request.clone()).await.0, 409);
    request["expected_version"] = receipt["document"]["version"].clone();
    request["content_sha256"] = receipt["document"]["content_sha256"].clone();
    let (status, repeated) = call(&app, "POST", path, request).await;
    assert_eq!(status, 200);
    assert_eq!(repeated["added_relations"], 0);
    let graph_path = format!(
        "/api/v1/documents/{}/relations",
        docs[0]["document_id"].as_str().unwrap()
    );
    let graph = call(&app, "GET", &graph_path, Value::Null).await.1;
    assert_eq!(graph["edges"].as_array().unwrap().len(), 2);
    drop(app);
    let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(&reopened, "GET", &graph_path, Value::Null).await.1["edges"],
        graph["edges"]
    );
    let fixed_path = format!(
        "/api/v1/documents/{}/versions/1",
        docs[1]["document_id"].as_str().unwrap()
    );
    let (status, pinned) = call(&reopened, "GET", &fixed_path, Value::Null).await;
    assert_eq!(status, 200, "{pinned}");
    assert_eq!(pinned["blocks"][0]["block_id"], "selected_block");
}

#[tokio::test]
async fn contained_parent_links_reach_existing_api_graph_without_rewriting_original_targets() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_, scope) = call(&app, "GET", "/api/v1/ingest-batches", Value::Null).await;
    let files = [
        (
            "notes/index.md",
            "[[target]] and ![[../assets/evidence.svg]]\n`[[ghost]]`\n```md\n[[ghost]]\n```",
        ),
        ("notes/target.md", "Target note"),
        ("notes/assets-only.md", "[Evidence](../assets/evidence.svg)"),
        ("assets/evidence.svg", "<svg/>"),
    ];
    let members: Vec<_> = files.iter().enumerate().map(|(i,(path,text))|
        json!({"ordinal":i,"relative_path":path,"byte_length":text.len(),"disposition":"pending"})).collect();
    let (status, manifest) = call(&app,"POST","/api/v1/ingest-batches",json!({
        "workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],
        "batch_id":"contained","folder_label":"selected-copy","expected_members":4,"members":members})).await;
    assert_eq!(status, 200, "{manifest}");
    let mut sources = Vec::new();
    for (ordinal, (_, text)) in files.iter().enumerate() {
        let (status, source) = call(&app,"POST","/api/v1/ingest-batches/contained/imports",json!({
            "workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],"ordinal":ordinal,
            "expected_sha256":format!("{:x}",Sha256::digest(text.as_bytes())),
            "content_base64":base64::engine::general_purpose::STANDARD.encode(text)})).await;
        assert_eq!(status, 202, "{source}");
        sources.push(source);
    }
    let mut docs = Vec::new();
    for ordinal in 0..3 {
        let (status, doc) = call(&app,"POST","/api/v1/documents",json!({
            "source_id":sources[ordinal]["source_id"],"source_revision":sources[ordinal]["sha256"],
            "title":files[ordinal].0,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Edited body [[body-ghost]]"}]}]}})).await;
        assert_eq!(status, 201, "{doc}");
        docs.push(doc);
    }
    let targets: Vec<_> = (1..4).map(|i|json!({"ordinal":i,"source_id":sources[i]["source_id"],"source_revision":sources[i]["sha256"],
        "document":docs.get(i).map(|d|json!({"document_id":d["document_id"],"version":d["version"],"content_sha256":d["content_sha256"]}))})).collect();
    let mut request = json!({"workspace_id":scope["workspace_id"],"restore_epoch":scope["restore_epoch"],
        "source_id":sources[0]["source_id"],"source_revision":sources[0]["sha256"],
        "document_id":docs[0]["document_id"],"expected_version":docs[0]["version"],"content_sha256":docs[0]["content_sha256"],"targets":targets});
    let path = "/api/v1/ingest-batches/contained/members/0/relations";
    let (status, receipt) = call(&app, "POST", path, request.clone()).await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(
        receipt["added_relations"], 2,
        "same-batch parent embed lost at real API boundary: {receipt}"
    );
    assert_eq!(receipt["links"].as_array().unwrap().len(), 2);
    assert_eq!(receipt["links"][1]["target"], "../assets/evidence.svg");
    assert_eq!(receipt["links"][1]["status"], "resolved_reference");
    assert_eq!(
        receipt["links"][1]["reason"],
        "embed_rendering_not_supported"
    );
    let asset =
        json!({"kind":"source","source_id":sources[3]["source_id"],"sha256":sources[3]["sha256"]});
    assert_eq!(
        receipt["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"][1]["target"],
        asset
    );
    assert_eq!(
        receipt["document"]["editor_json"]["content"],
        docs[0]["editor_json"]["content"]
    );
    let graph_path = format!(
        "/api/v1/documents/{}/relations",
        docs[0]["document_id"].as_str().unwrap()
    );
    let (status, graph) = call(&app, "GET", &graph_path, Value::Null).await;
    assert_eq!(status, 200);
    assert_eq!(graph["edges"].as_array().unwrap().len(), 2);
    let mut markdown = request.clone();
    markdown["source_id"] = sources[2]["source_id"].clone();
    markdown["source_revision"] = sources[2]["sha256"].clone();
    markdown["document_id"] = docs[2]["document_id"].clone();
    markdown["expected_version"] = docs[2]["version"].clone();
    markdown["content_sha256"] = docs[2]["content_sha256"].clone();
    let (status, other) = call(
        &app,
        "POST",
        "/api/v1/ingest-batches/contained/members/2/relations",
        markdown,
    )
    .await;
    assert_eq!(status, 200, "{other}");
    assert_eq!(other["added_relations"], 1);
    assert_eq!(
        other["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"][0]["target"],
        asset
    );
    assert_eq!(call(&app, "POST", path, request.clone()).await.0, 409);
    request["expected_version"] = receipt["document"]["version"].clone();
    request["content_sha256"] = receipt["document"]["content_sha256"].clone();
    let (status, repeated) = call(&app, "POST", path, request).await;
    assert_eq!(status, 200, "{repeated}");
    assert_eq!(repeated["added_relations"], 0);
    assert_eq!(repeated["document"], receipt["document"]);
    drop(app);
    let reopened = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(&reopened, "GET", &graph_path, Value::Null).await.1["edges"],
        graph["edges"]
    );
}

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
