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
    let markdown = export["files"][0]["content"].as_str().unwrap();
    assert!(markdown.contains(&format!(r#""reference":{target}"#)));
    assert!(!markdown.contains("<https://"));
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
async fn research_markdown_exports_registered_hit_and_pinned_materials() {
    use archeaxis_domain::public_research::{self, Request as ResearchRequest};
    use base64::{Engine as _, engine::general_purpose::STANDARD};
    use sha2::{Digest, Sha256};

    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("research.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let state = archeaxis_domain::ui_state::read(&mut conn).unwrap();
    let request = ResearchRequest {
        request_id: "export-test".into(),
        workspace_id: state["workspace_id"].as_str().unwrap().into(),
        restore_epoch: state["restore_epoch"].as_str().unwrap().into(),
        query: "spaced repetition".into(),
        families: vec!["community".into()],
        limit: 1,
        community_site: None,
    };
    public_research::begin(&mut conn, &request).unwrap();
    let url = "https://academia.stackexchange.com/questions/42/teaching";
    let quote = "Synthetic question about teaching.";
    let hit = "stackexchange:academia:question:42";
    let acquired = "2026-10-21T00:00:00Z";
    let result = json!({"schema":"public-research-worker/v1","query":request.query,"families":request.families,
        "channels":[{"family":"community","provider":"stackexchange","status":"complete","retrieved_at":acquired,
        "request_url":"https://api.stackexchange.com/2.3/search/advanced?q=spaced+repetition&site=academia&pagesize=1&sort=relevance&filter=withbody",
        "raw_response_base64":STANDARD.encode(br#"{"items":[]}"#),"retry_after_seconds":null,"error_code":null,
        "hits":[{"id":hit,"url":url,"family":"community","provider":"stackexchange","title":"Teaching",
        "retrieved_at":acquired,"content":"full_text","excerpt":quote,"locator":"question_id=42;body",
        "license":null,"free_access":"free","upstream_revision":null,"representation":"html_text","truncated":false}]}]});
    public_research::publish(&mut conn, &request, result).unwrap();
    let chosen =
        public_research::materialize(&mut conn, &request.request_id, "community", hit).unwrap();
    let source = &chosen["reference"];
    let hash = source["sha256"].as_str().unwrap();
    let raw = archeaxis_store_sqlite::raw_objects::read(&conn, hash).unwrap();
    let start = std::str::from_utf8(&raw).unwrap().find(quote).unwrap();
    drop(conn);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let checksum = format!("{:x}", Sha256::digest(quote.as_bytes()));
    let position = json!({"type":"text","start":start,"end":start+quote.len()});
    let (code, anchor) = call(
        &app,
        "POST",
        &format!(
            "/api/v1/sources/{}/anchors",
            source["source_id"].as_str().unwrap()
        ),
        json!({"revision":hash,"checksum":checksum,"position":position.to_string()}),
        "human",
    )
    .await;
    assert_eq!(code, 201, "{anchor}");
    let citation = json!({"schema":"archeaxis.research-citation/v1","anchor_id":anchor["anchor_id"],
        "source_sha256":hash,"read_snapshot_sha256":hash,"quote":quote,"quote_sha256":checksum,
        "anchor_position_sha256":format!("{:x}",Sha256::digest(anchor["position"].as_str().unwrap().as_bytes()))});
    let editor = json!({"type":"doc","content":[],"attrs":{"archeaxis_research":{
        "schema":"archeaxis.research/v1","question":"Teaching?","hypotheses":[],"methods":[],
        "experiments":[],"counterevidence":[],"conclusions":[],"unresolved":[],
        "materials":[{"id":"question","note":"Selected question","reference":source,"citation":citation},
        {"id":"response","note":"Original response","reference":chosen["raw_reference"]}]}}});
    let (code, doc) = call(
        &app,
        "POST",
        "/api/v1/documents",
        json!({"title":"Study","editor_json":editor}),
        "human",
    )
    .await;
    assert_eq!(code, 201, "{doc}");
    let (code, export) = call(
        &app,
        "GET",
        &format!(
            "/api/v1/documents/{}/export?format=markdown",
            doc["document_id"].as_str().unwrap()
        ),
        Value::Null,
        "human",
    )
    .await;
    assert_eq!(code, 200, "{export}");
    let md = export["files"][0]["content"].as_str().unwrap();
    assert_eq!(md.matches(&format!("<{url}>")).count(), 1);
    assert!(!md.contains("<https://api.stackexchange.com"));
    let records: Vec<Value> = md
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line.strip_prefix("    ")?).ok())
        .filter(|record| record.get("material_id").is_some())
        .collect();
    assert_eq!(records.len(), 2);
    assert_eq!(records[0]["reference"], *source);
    assert_eq!(records[0]["citation"], citation);
    assert_eq!(records[0]["position"]["start"], start);
    assert_eq!(records[0]["upstream_locator"], "question_id=42;body");
    assert_eq!(records[1]["reference"], chosen["raw_reference"]);
}
