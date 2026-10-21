use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
async fn raw_call(app: &Router, method: &str, path: &str, body: Vec<u8>) -> (u16, Vec<u8>) {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(body))
                .unwrap(),
        )
        .await
        .unwrap();
    (
        response.status().as_u16(),
        response
            .into_body()
            .collect()
            .await
            .unwrap()
            .to_bytes()
            .to_vec(),
    )
}

#[tokio::test]
async fn media_package_api_roundtrips_scan_sized_bytes_and_rejects_oversize_explicitly() {
    use archeaxis_domain::{ImportOutcome, document, portable_document::Package, source};
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("media.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let mut ids = Vec::new();
    for size in [4_564_915, 8 * 1024 * 1024 + 1] {
        let (id, sha) =
            match source::import_source(&mut conn, &vec![255; size], "authored-scan.pdf", None)
                .unwrap()
            {
                ImportOutcome::Imported { source_id, sha256 }
                | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
            };
        let doc = document::create_optional(
            &mut conn,
            Some(&id),
            Some(&sha),
            "Scan",
            json!({"type":"doc","content":[]}),
        )
        .unwrap();
        ids.push(doc["document_id"].as_str().unwrap().to_owned());
    }
    drop(conn);
    let app = archeaxis_api::app(path.to_str().unwrap()).unwrap();
    let (status, package_bytes) = raw_call(
        &app,
        "GET",
        &format!("/api/v1/documents/{}/package", ids[0]),
        vec![],
    )
    .await;
    assert_eq!(status, 200, "{}", String::from_utf8_lossy(&package_bytes));
    assert!(package_bytes.len() > 16 * 1024 * 1024);
    let package: Package = serde_json::from_slice(&package_bytes).unwrap();
    assert_eq!(package.objects[0].bytes, vec![255; 4_564_915]);
    let mut request = br#"{"request_id":"media-roundtrip","package":"#.to_vec();
    request.extend(package_bytes);
    request.push(b'}');
    let (status, bytes) = raw_call(
        &app,
        "POST",
        "/api/v1/document-packages/import",
        request.clone(),
    )
    .await;
    assert_eq!(status, 201, "{}", String::from_utf8_lossy(&bytes));
    let imported: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(
        raw_call(&app, "POST", "/api/v1/document-packages/import", request)
            .await
            .1,
        bytes
    );
    let (status, restored) = raw_call(
        &app,
        "GET",
        &format!(
            "/api/v1/documents/{}/package",
            imported["document"]["document_id"].as_str().unwrap()
        ),
        vec![],
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(
        serde_json::from_slice::<Package>(&restored)
            .unwrap()
            .objects[0]
            .bytes,
        package.objects[0].bytes
    );
    let (status, error) = raw_call(
        &app,
        "GET",
        &format!("/api/v1/documents/{}/package", ids[1]),
        vec![],
    )
    .await;
    assert_eq!(status, 400, "{}", String::from_utf8_lossy(&error));
    assert!(String::from_utf8(error).unwrap().contains("byte budget"));
    let (status, _) = raw_call(
        &app,
        "POST",
        "/api/v1/document-packages/import",
        vec![b' '; archeaxis_domain::portable_document::MAX_IMPORT_JSON_BYTES + 1],
    )
    .await;
    assert_eq!(status, 413, "package transport remains bounded");
}
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
async fn ordinary_document_package_requires_human_and_imports_once() {
    let dir = tempfile::tempdir().unwrap();
    let app = archeaxis_api::app(dir.path().join("package.sqlite").to_str().unwrap()).unwrap();
    let (_,document)=call(&app,"POST","/api/v1/documents",json!({"title":"synthetic","editor_json":{"type":"doc","content":[{"type":"future_node","attrs":{"preserved":true}}]}}),"human").await;
    let (status, package) = call(
        &app,
        "GET",
        &format!(
            "/api/v1/documents/{}/package",
            document["document_id"].as_str().unwrap()
        ),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    let body = json!({"request_id":"package_repeat","package":package});
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/document-packages/import",
            body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    let (status, receipt) = call(
        &app,
        "POST",
        "/api/v1/document-packages/import",
        body.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 201, "{receipt}");
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/document-packages/import",
            body,
            "human"
        )
        .await
        .1,
        receipt
    );
    assert_eq!(receipt["document"]["editor_json"], document["editor_json"]);
    assert_eq!(receipt["knowledge_admission"], "NOT_EXECUTED");
}
