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
#[tokio::test]
async fn relation_query_and_authored_research_use_one_writer_and_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status,material)=call(&app,"POST","/api/v1/documents",json!({"title":"依据原文","create_request_id":"material","editor_json":{"type":"doc","content":[]}}),"human").await;
    assert_eq!(status, 201);
    let target = json!({"kind":"document","document_id":material["document_id"],"version":1,"block_id":null});
    let mut editor = json!({"type":"doc","content":[],"attrs":{"archeaxis_relations":{"schema":"archeaxis.relations/v1","relations":[{"id":"related","kind":"supports","label":"依据","target":target}]},"archeaxis_research":{"schema":"archeaxis.research/v1","question":"问题","materials":[{"id":"material","note":"原文","reference":target}],"hypotheses":[],"methods":[],"experiments":[],"counterevidence":[],"conclusions":[{"id":"conclusion","text":"待核结论","sources":[target],"basis":[]}],"unresolved":[]},"future_payload":{"preserve":"exact"}}});
    let create = json!({"title":"研究","create_request_id":"research","editor_json":editor});
    assert_eq!(
        call(&app, "POST", "/api/v1/documents", create.clone(), "machine")
            .await
            .0,
        403
    );
    let (status, first) = call(&app, "POST", "/api/v1/documents", create.clone(), "human").await;
    assert_eq!(status, 201, "{first}");
    assert_eq!(
        call(&app, "POST", "/api/v1/documents", create, "human")
            .await
            .1,
        first
    );
    let path = format!(
        "/api/v1/documents/{}",
        first["document_id"].as_str().unwrap()
    );
    let material_graph = format!(
        "/api/v1/documents/{}/relations?version=1",
        material["document_id"].as_str().unwrap()
    );
    let (status, graph) = call(&app, "GET", &material_graph, json!(null), "human").await;
    assert_eq!(status, 200);
    assert_eq!(graph["edges"][0]["direction"], "backlink");
    assert_eq!(
        graph["edges"][0]["source_snapshot"]["content_sha256"],
        first["content_sha256"]
    );
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{path}/relations?version=0"),
            json!(null),
            "human"
        )
        .await
        .0,
        400
    );
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{path}/relations?cursor=../escape"),
            json!(null),
            "human"
        )
        .await
        .0,
        400
    );
    editor["attrs"]["archeaxis_relations"]["relations"] = json!([]);
    editor["attrs"]["archeaxis_research"]["conclusions"][0]["basis"] = json!([target]);
    let (_, saved) = call(
        &app,
        "PUT",
        &format!("{path}/draft"),
        json!({"expected_version":1,"editor_json":editor}),
        "human",
    )
    .await;
    assert_eq!(saved["version"], 2);
    let (_, export) = call(
        &app,
        "GET",
        &format!("{path}/export?format=markdown"),
        json!(null),
        "human",
    )
    .await;
    let manifest: Value =
        serde_json::from_str(export["files"][1]["content"].as_str().unwrap()).unwrap();
    assert_eq!(manifest["document"], saved);
    drop(app);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(&app, "GET", &path, json!(null), "human").await.1,
        saved
    );
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{path}/versions/1"),
            json!(null),
            "human"
        )
        .await
        .1,
        first
    );
    assert!(
        call(&app, "GET", &material_graph, json!(null), "human")
            .await
            .1["edges"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    let (_, material_read) = call(
        &app,
        "GET",
        &format!(
            "/api/v1/documents/{}",
            material["document_id"].as_str().unwrap()
        ),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(material_read, material);
}

#[tokio::test]
async fn pinned_document_relation_reports_history_after_update_and_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("versioned-relations.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status, material) = call(
        &app,
        "POST",
        "/api/v1/documents",
        json!({
            "title":"synthetic material", "editor_json":{"type":"doc","content":[
                {"type":"paragraph","content":[{"type":"text","text":"first version"}]}]}
        }),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    let material_id = material["document_id"].as_str().unwrap();
    let reference =
        json!({"kind":"document","document_id":material_id,"version":1,"block_id":null});
    let (status, research) = call(
        &app,
        "POST",
        "/api/v1/documents",
        json!({
            "title":"synthetic research", "editor_json":{"type":"doc","content":[],"attrs":{
                "archeaxis_relations":{"schema":"archeaxis.relations/v1","relations":[
                    {"id":"source","kind":"supports","label":"source","target":reference}]}}}
        }),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    let path = format!(
        "/api/v1/documents/{}/relations?version=1",
        research["document_id"].as_str().unwrap()
    );
    let (status, before) = call(&app, "GET", &path, json!(null), "human").await;
    assert_eq!(status, 200);
    let find_target = |graph: &Value| {
        graph["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .find(|node| node["reference"] == reference)
            .unwrap()
            .clone()
    };
    assert_eq!(find_target(&before)["version_relation"], "current");
    let (status, updated) = call(
        &app,
        "PUT",
        &format!("/api/v1/documents/{material_id}/draft"),
        json!({
            "expected_version":1,"editor_json":{"type":"doc","content":[
                {"type":"paragraph","content":[{"type":"text","text":"second version"}]}]}
        }),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(updated["version"], 2);
    let (status, after) = call(&app, "GET", &path, json!(null), "human").await;
    assert_eq!(status, 200);
    let node = find_target(&after);
    assert_eq!(node["status"], "resolved");
    assert_eq!(node["version_relation"], "historical");
    assert_eq!(node["object"]["current_version"], 2);
    assert_eq!(node["object"]["content_sha256"], material["content_sha256"]);
    assert_eq!(after["edges"][0]["relation"]["target"], reference);
    drop(app);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status, reopened) = call(&app, "GET", &path, json!(null), "human").await;
    assert_eq!(status, 200);
    assert_eq!(find_target(&reopened), node);
    assert_eq!(reopened["edges"][0]["relation"]["target"], reference);
}

#[tokio::test]
async fn research_references_report_versions_without_rewriting_the_snapshot() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("research-references.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status, material) = call(
        &app,
        "POST",
        "/api/v1/documents",
        json!({
            "title":"synthetic material", "editor_json":{"type":"doc","content":[]}
        }),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    let material_id = material["document_id"].as_str().unwrap();
    let document_ref =
        json!({"kind":"document","document_id":material_id,"version":1,"block_id":null});
    let (status, knowledge) = call(&app, "POST", "/api/v1/knowledge-items", json!({
        "knowledge_type":"FACTUAL_CLAIM", "body":"synthetic fact", "status":"accepted", "created_by":"human"
    }), "human").await;
    assert_eq!(status, 201);
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap();
    let knowledge_ref = json!({"kind":"knowledge","knowledge_id":knowledge_id});
    let (status, research) = call(&app, "POST", "/api/v1/documents", json!({
        "title":"synthetic research", "editor_json":{"type":"doc","content":[],"attrs":{
            "archeaxis_research":{"schema":"archeaxis.research/v1","question":"synthetic question",
                "materials":[{"id":"material","note":"basis","reference":document_ref}],
                "hypotheses":[{"id":"hypothesis","text":"hypothesis","references":[knowledge_ref]}],
                "methods":[{"id":"method","text":"method","references":[document_ref]}],
                "experiments":[{"id":"experiment","text":"experiment","references":[document_ref]}],
                "counterevidence":[{"id":"counterevidence","text":"counterevidence","references":[knowledge_ref]}],
                "conclusions":[{"id":"conclusion","text":"conclusion","sources":[document_ref],"basis":[knowledge_ref]}],
                "unresolved":[{"id":"unresolved","text":"unresolved","references":[knowledge_ref]}]}}}
    }), "human").await;
    assert_eq!(status, 201);
    let path = format!(
        "/api/v1/documents/{}/research-references?version=1",
        research["document_id"].as_str().unwrap()
    );
    let (status, before) = call(&app, "GET", &path, json!(null), "human").await;
    assert_eq!(status, 200, "{before}");
    assert_eq!(before["metadata_status"], "supported");
    assert_eq!(
        before["document"]["content_sha256"],
        research["content_sha256"]
    );
    let refs = before["references"].as_array().unwrap();
    assert_eq!(refs.len(), 8);
    assert_eq!(
        (refs[0]["entry_kind"].as_str(), refs[0]["field"].as_str()),
        (Some("material"), Some("reference"))
    );
    assert_eq!(refs[0]["reference"], document_ref);
    assert_eq!(refs[0]["object"]["version_relation"], "current");
    assert_eq!(refs[0]["version_relation"], "current");
    assert_eq!(refs[0]["current_version"], 1);
    assert_eq!(refs[1]["reference"], knowledge_ref);
    assert_eq!(refs[1]["object"]["currentness"], "current");
    assert_eq!(refs[1]["currentness"], "current");
    assert_eq!(
        refs.iter()
            .map(|item| item["entry_kind"].as_str().unwrap())
            .collect::<Vec<_>>(),
        [
            "material",
            "hypothesis",
            "method",
            "experiment",
            "counterevidence",
            "unresolved",
            "conclusion",
            "conclusion"
        ]
    );
    assert_eq!(refs[6]["field"], "sources");
    assert_eq!(refs[7]["field"], "basis");
    assert_eq!(
        call(
            &app,
            "GET",
            &path.replace("version=1", "version=0"),
            json!(null),
            "human"
        )
        .await
        .0,
        400
    );
    assert_eq!(
        call(
            &app,
            "GET",
            &format!("{path}&unknown=1"),
            json!(null),
            "human"
        )
        .await
        .0,
        400
    );
    assert_eq!(
        call(
            &app,
            "GET",
            "/api/v1/documents/missing/research-references",
            json!(null),
            "human"
        )
        .await
        .0,
        404
    );

    let (status, _) = call(&app, "PUT", &format!("/api/v1/documents/{material_id}/draft"), json!({
        "expected_version":1, "editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"revision"}]}]}
    }), "human").await;
    assert_eq!(status, 200);
    let (status, successor) = call(
        &app,
        "POST",
        &format!("/api/v1/knowledge-items/{knowledge_id}/review-decisions"),
        json!({
            "action":"modified","reviewer":"human","new_body":"corrected synthetic fact"
        }),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    let (status, after) = call(&app, "GET", &path, json!(null), "human").await;
    assert_eq!(status, 200);
    assert_eq!(after["document"], before["document"]);
    assert_eq!(after["references"][0]["reference"], document_ref);
    assert_eq!(
        after["references"][0]["object"]["version_relation"],
        "historical"
    );
    assert_eq!(after["references"][0]["version_relation"], "historical");
    assert_eq!(after["references"][0]["current_version"], 2);
    assert_eq!(after["references"][1]["reference"], knowledge_ref);
    assert_eq!(
        after["references"][1]["object"]["currentness"],
        "superseded"
    );
    assert_eq!(after["references"][1]["currentness"], "superseded");
    assert_eq!(
        after["references"][1]["object"]["superseded_by"],
        successor["knowledge_id"]
    );
    drop(app);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status, reopened) = call(&app, "GET", &path, json!(null), "human").await;
    assert_eq!(status, 200);
    assert_eq!(reopened, after);
}
