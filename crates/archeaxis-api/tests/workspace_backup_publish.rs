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

#[tokio::test]
async fn large_v1_backup_lists_previews_and_restores_while_bad_neighbors_stay_isolated() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("large.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let transaction = conn.transaction().unwrap();
    for index in 0..15_000 {
        archeaxis_domain::source::import_source_tx(
            &transaction,
            format!("SYNTHETIC distinct original {index}").as_bytes(),
            &format!("{index}.txt"),
            None,
        )
        .unwrap();
    }
    transaction.commit().unwrap();
    drop(conn);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let route = "/api/v1/workspace/backups";
    let (status, receipt) = call(&app, "POST", route, json!({}), "human").await;
    assert_eq!(status, 201, "{receipt}");
    assert_eq!(receipt["source_sha_list"].as_array().unwrap().len(), 15_000);
    let root = dir.path().join("backups");
    let artifact = root.join(receipt["filename"].as_str().unwrap());
    let manifest = artifact.with_extension("sqlite.manifest.json");
    assert!(std::fs::metadata(&manifest).unwrap().len() > 1024 * 1024);
    let original_manifest = std::fs::read(&manifest).unwrap();

    // Keep valid large v1, malformed JSON, oversized forged inventory, missing
    // manifest and bad database together. None may hide the usable snapshot.
    for (id, body) in [('1', "{".to_owned()), ('2', " ".repeat(3 * 1024 * 1024))] {
        let filename = format!("{}.sqlite", id.to_string().repeat(32));
        std::fs::copy(&artifact, root.join(&filename)).unwrap();
        std::fs::write(root.join(format!("{filename}.manifest.json")), body).unwrap();
    }
    let missing = root.join(format!("{}.sqlite", "3".repeat(32)));
    std::fs::copy(&artifact, missing).unwrap();
    let bad = root.join(format!("{}.sqlite", "4".repeat(32)));
    std::fs::write(&bad, b"not SQLite").unwrap();
    std::fs::write(bad.with_extension("sqlite.manifest.json"), b"{}").unwrap();
    let forged = root.join(format!("{}.sqlite", "5".repeat(32)));
    let forged_db = rusqlite::Connection::open(&forged).unwrap();
    forged_db.execute_batch("CREATE VIEW sources AS WITH RECURSIVE entries(sha256) AS (SELECT 'x' UNION ALL SELECT sha256 FROM entries) SELECT sha256 FROM entries;").unwrap();
    drop(forged_db);
    std::fs::write(forged.with_extension("sqlite.manifest.json"), b"{}").unwrap();
    let listed = call(&app, "GET", route, Value::Null, "human").await;
    assert_eq!(listed.0, 200, "{}", listed.1);
    assert_eq!(listed.1["backups"], json!([receipt]));
    assert_eq!(listed.1["unavailable_backups"].as_array().unwrap().len(), 5);
    assert!(
        listed.1["unavailable_backups"]
            .as_array()
            .unwrap()
            .iter()
            .all(|v| v["code"] == "AAK-BACKUP-INVALID")
    );
    let preview = call(
        &app,
        "POST",
        "/api/v2/workspace/restore/preview",
        json!({"backup_id":receipt["backup_id"],"expected_sha256":receipt["sha256"]}),
        "human",
    )
    .await;
    assert_eq!(preview.0, 200, "{}", preview.1);
    assert_eq!(preview.1["source_count"], 15_000);
    let invalid = call(
        &app,
        "POST",
        "/api/v2/workspace/restore/preview",
        json!({"backup_id":"2".repeat(32),"expected_sha256":receipt["sha256"]}),
        "human",
    )
    .await;
    assert_eq!(invalid.0, 409);
    assert_eq!(std::fs::read(&manifest).unwrap(), original_manifest);
    drop(app);

    // Use the actual maintenance entry, including authorization staging, on a
    // new isolated destination. This is not a legacy database or a mock restore.
    let restored = dir.path().join("restored.sqlite");
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_archeaxis-api"))
        .arg("--maintenance-restore")
        .arg(&restored)
        .arg(&artifact)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stdout)
    );
    let result: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(result["authorization_requires_new_grants"], true);
    let reopened = archeaxis_store_sqlite::init_workspace(restored.to_str().unwrap()).unwrap();
    assert_eq!(
        reopened
            .query_row("SELECT count(*) FROM sources", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        15_000
    );
    let source = rusqlite::Connection::open_with_flags(
        &artifact,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .unwrap();
    assert!(archeaxis_domain::backup::verify_restored_authorization(&source, &reopened).unwrap());
    assert_eq!(std::fs::read(&manifest).unwrap(), original_manifest);
}
