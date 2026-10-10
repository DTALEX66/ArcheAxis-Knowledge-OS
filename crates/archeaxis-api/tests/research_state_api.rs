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
