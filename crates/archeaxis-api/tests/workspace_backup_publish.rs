//! Complete, collision-safe backup publication through the canonical live writer.
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
                .body(Body::from(serde_json::to_vec(&body).unwrap()))
                .unwrap(),
        )
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
async fn live_backup_publishes_synced_manifest_and_restorable_objects_without_clobber() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let route = "/api/v1/workspace/backups";
    assert_eq!(call(&app, "POST", route, json!({}), "machine").await.0, 403);
    assert!(!dir.path().join("backups").exists());
    assert_eq!(
        call(&app, "POST", route, json!({"path":"outside"}), "human")
            .await
            .0,
        422
    );
    let (status, source) = call(
        &app,
        "POST",
        "/api/v1/imports",
        json!({"name":"backup.txt", "content_base64":"b3JpZ2luYWw="}),
        "human",
    )
    .await;
    assert_eq!(status, 202, "{source}");
    let (status, first) = call(&app, "POST", route, json!({}), "human").await;
    assert_eq!(status, 201, "{first}");
    assert_eq!(first["verified"], true);
    assert_eq!(first["source_sha_list"], json!([source["sha256"]]));
    let artifact = dir
        .path()
        .join("backups")
        .join(first["filename"].as_str().unwrap());
    let manifest = artifact.with_extension("sqlite.manifest.json");
    let first_bytes = std::fs::read(&artifact).unwrap();
    let first_manifest = std::fs::read(&manifest).unwrap();
    assert_eq!(
        serde_json::from_slice::<Value>(&first_manifest).unwrap(),
        first
    );
    let (status, second) = call(&app, "POST", route, json!({}), "human").await;
    assert_eq!(status, 201, "{second}");
    assert_ne!(first["backup_id"], second["backup_id"]);
    assert_eq!(std::fs::read(&artifact).unwrap(), first_bytes);
    assert_eq!(std::fs::read(&manifest).unwrap(), first_manifest);
    assert!(
        std::fs::read_dir(dir.path().join("backups"))
            .unwrap()
            .all(|entry| !entry
                .unwrap()
                .file_name()
                .to_string_lossy()
                .ends_with(".tmp"))
    );
    let listed = call(&app, "GET", route, Value::Null, "human").await;
    assert_eq!(listed.0, 200, "{}", listed.1);
    assert_eq!(listed.1["backups"].as_array().unwrap().len(), 2);
    let preview = call(
        &app,
        "POST",
        "/api/v2/workspace/restore/preview",
        json!({"backup_id":first["backup_id"], "expected_sha256":first["sha256"]}),
        "human",
    )
    .await;
    assert_eq!(preview.0, 200, "{}", preview.1);
    assert_eq!(preview.1["verified"], true);
    let bad = call(
        &app,
        "POST",
        "/api/v2/workspace/restore/preview",
        json!({"backup_id":first["backup_id"], "expected_sha256":"0".repeat(64)}),
        "human",
    )
    .await;
    assert_eq!(bad.0, 409);
    drop(app);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(call(&app, "GET", route, Value::Null, "human").await, listed);
    drop(app);
    let original = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let restored = dir.path().join("restored.sqlite");
    let mut restored = archeaxis_store_sqlite::init_workspace(restored.to_str().unwrap()).unwrap();
    archeaxis_domain::backup::restore(artifact.to_str().unwrap(), &mut restored).unwrap();
    assert!(archeaxis_domain::backup::verify_counts(&original, &restored).unwrap());
    assert_eq!(
        archeaxis_store_sqlite::raw_objects::read(&restored, source["sha256"].as_str().unwrap())
            .unwrap(),
        b"original"
    );
}
