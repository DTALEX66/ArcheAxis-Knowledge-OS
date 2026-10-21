//! INTEGRATED HTTP/SQLite batch identity and restart, no worker or model.
use axum::{Router, body::Body, http::Request};
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
                .body(Body::from(body.to_string()))
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
async fn batch_registration_is_durable_paged_and_exactly_idempotent() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("batch.sqlite");
    let app = archeaxis_api::app(path.to_str().unwrap()).unwrap();
    let (_, basis) = call(&app, "GET", "/api/v1/workspace/ui-state", Value::Null).await;
    let body = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "batch_id":"batch-one","folder_label":"资料","expected_members":2,
        "members":[{"ordinal":0,"relative_path":"甲/a.md","byte_length":1,"disposition":"pending"}]});
    let (status, first) = call(&app, "POST", "/api/v1/ingest-batches", body.clone()).await;
    assert_eq!(status, 200, "{first}");
    assert_eq!(first["registered_members"], 1);
    assert_eq!(first["complete"], false);
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", body.clone())
            .await
            .0,
        200
    );
    let mut changed = body.clone();
    changed["members"][0]["relative_path"] = json!("changed.md");
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", changed)
            .await
            .0,
        409
    );
    let mut second = body.clone();
    second["members"][0]["ordinal"] = json!(1);
    second["members"][0]["relative_path"] = json!("乙/a.md");
    let (status, complete) = call(&app, "POST", "/api/v1/ingest-batches", second).await;
    assert_eq!(status, 200, "{complete}");
    assert_eq!(complete["complete"], true);
    drop(app);
    let reopened = archeaxis_api::app(path.to_str().unwrap()).unwrap();
    let (status, page) = call(
        &reopened,
        "GET",
        "/api/v1/ingest-batches/batch-one?limit=1",
        Value::Null,
    )
    .await;
    assert_eq!(status, 200, "{page}");
    assert_eq!(page["members"].as_array().unwrap().len(), 1);
    assert_eq!(page["next_ordinal"], 0);
    assert_eq!(page["members"][0]["relative_path"], "甲/a.md");
    let (_, tail) = call(
        &reopened,
        "GET",
        "/api/v1/ingest-batches/batch-one?after_ordinal=0&limit=1",
        Value::Null,
    )
    .await;
    assert_eq!(tail["members"][0]["relative_path"], "乙/a.md");
    assert_eq!(tail["next_ordinal"], Value::Null);
}

#[tokio::test]
async fn imported_members_share_cas_and_jobs_but_keep_identity_across_backup_restore() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_, basis) = call(&app, "GET", "/api/v1/workspace/ui-state", Value::Null).await;
    let mut manifest = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "batch_id":"batch-two","folder_label":"资料","expected_members":2,
        "members":[{"ordinal":0,"relative_path":"甲/a.md","byte_length":1,"disposition":"pending"}]});
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", manifest.clone())
            .await
            .0,
        200
    );
    let digest = "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881";
    let mut upload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "ordinal":0,"expected_sha256":digest,"content_base64":"eA=="});
    let import_path = "/api/v1/ingest-batches/batch-two/imports";
    assert_eq!(
        call(&app, "POST", import_path, upload.clone()).await.0,
        409,
        "incomplete manifest must not import"
    );
    manifest["members"][0]["ordinal"] = json!(1);
    manifest["members"][0]["relative_path"] = json!("乙/a.md");
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", manifest.clone())
            .await
            .0,
        200
    );
    let mut tampered = upload.clone();
    tampered["expected_sha256"] = json!("0".repeat(64));
    assert_eq!(call(&app, "POST", import_path, tampered).await.0, 400);
    let (status, first) = call(&app, "POST", import_path, upload.clone()).await;
    assert_eq!(status, 202, "{first}");
    assert_eq!(first["sha256"], digest);
    assert_eq!(
        call(&app, "POST", import_path, upload.clone()).await.1["source_id"],
        first["source_id"]
    );
    upload["ordinal"] = json!(1);
    let (status, second) = call(&app, "POST", import_path, upload.clone()).await;
    assert_eq!(status, 202, "{second}");
    assert_eq!(first["source_id"], second["source_id"]);
    let enqueue = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "ordinal":0,"source_id":first["source_id"],"source_revision":digest,"kind":"text"});
    let enqueue_path = "/api/v1/ingest-batches/batch-two/jobs";
    let (status, job) = call(&app, "POST", enqueue_path, enqueue.clone()).await;
    assert_eq!(status, 202, "{job}");
    assert_eq!(
        call(&app, "POST", enqueue_path, enqueue.clone()).await.1["job_id"],
        job["job_id"]
    );
    let mut sibling = enqueue.clone();
    sibling["ordinal"] = json!(1);
    assert_eq!(
        call(&app, "POST", enqueue_path, sibling).await.1["job_id"],
        job["job_id"]
    );
    let mut wrong = enqueue.clone();
    wrong["source_id"] = json!("src_other");
    assert_eq!(call(&app, "POST", enqueue_path, wrong).await.0, 409);
    drop(app);
    let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        conn.query_row::<i64, _, _>("SELECT count(*) FROM sources", [], |r| r.get(0))
            .unwrap(),
        1
    );
    assert_eq!(
        conn.query_row::<i64, _, _>("SELECT count(*) FROM source_origins", [], |r| r.get(0))
            .unwrap(),
        2
    );
    assert_eq!(
        conn.query_row::<i64, _, _>("SELECT count(*) FROM jobs", [], |r| r.get(0))
            .unwrap(),
        1
    );
    let backup = dir.path().join("backup.sqlite");
    archeaxis_domain::backup::backup(&conn, backup.to_str().unwrap()).unwrap();
    let restored = dir.path().join("restored.sqlite");
    let mut target = archeaxis_store_sqlite::init_workspace(restored.to_str().unwrap()).unwrap();
    archeaxis_domain::backup::restore(backup.to_str().unwrap(), &mut target).unwrap();
    assert!(archeaxis_domain::backup::finalize_restore_authorization(&conn, &mut target).unwrap());
    drop(target);
    drop(conn);
    let app = archeaxis_api::app(restored.to_str().unwrap()).unwrap();
    let (_, readback) = call(&app, "GET", "/api/v1/ingest-batches/batch-two", Value::Null).await;
    assert_ne!(readback["restore_epoch"], basis["restore_epoch"]);
    assert_eq!(readback["members"].as_array().unwrap().len(), 2);
    assert_eq!(readback["members"][0]["job_id"], job["job_id"]);
    for (path, body) in [
        ("/api/v1/ingest-batches", manifest),
        (import_path, upload),
        (enqueue_path, enqueue),
    ] {
        assert_eq!(
            call(&app, "POST", path, body).await.0,
            409,
            "stale restore intent: {path}"
        );
    }
}

#[tokio::test]
async fn batch_rejects_unbounded_or_ambiguous_members_and_unknown_fields() {
    let dir = tempfile::tempdir().unwrap();
    let app = archeaxis_api::app(dir.path().join("negative.sqlite").to_str().unwrap()).unwrap();
    let (_, basis) = call(&app, "GET", "/api/v1/workspace/ui-state", Value::Null).await;
    let body = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "batch_id":"negative","folder_label":"资料","expected_members":1,
        "members":[{"ordinal":0,"relative_path":"a.md","byte_length":1,"disposition":"pending"}]});
    for path in [
        "../a.md",
        "/a.md",
        "a//b.md",
        "a/./b.md",
        "C:/a.md",
        "a\\b.md",
        ".codex/private",
    ] {
        let mut bad = body.clone();
        bad["members"][0]["relative_path"] = json!(path);
        assert_eq!(
            call(&app, "POST", "/api/v1/ingest-batches", bad).await.0,
            400,
            "{path}"
        );
    }
    let mut bad = body.clone();
    bad["expected_members"] = json!(10001);
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", bad).await.0,
        400
    );
    let mut bad = body.clone();
    bad["members"] = json!(vec![body["members"][0].clone(); 201]);
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", bad).await.0,
        400
    );
    let mut bad = body.clone();
    bad["extra"] = json!(true);
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", bad).await.0,
        422
    );
    let mut bad = body.clone();
    bad["members"][0]["extra"] = json!(true);
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", bad).await.0,
        422
    );
    let (_, listing) = call(&app, "GET", "/api/v1/ingest-batches", Value::Null).await;
    assert_eq!(
        listing["batches"],
        json!([]),
        "refusals leave no partial batch"
    );
}

#[tokio::test]
async fn restored_fence_rejects_all_old_mutations_and_cross_member_uploads() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("fenced.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_, basis) = call(&app, "GET", "/api/v1/workspace/ui-state", Value::Null).await;
    let manifest = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "batch_id":"fenced","folder_label":"folder","expected_members":1,
        "members":[{"ordinal":0,"relative_path":"a.md","byte_length":1,"disposition":"pending"}]});
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches", manifest.clone())
            .await
            .0,
        200
    );
    let upload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "ordinal":0,"expected_sha256":"2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881","content_base64":"eA=="});
    let mut wrong = upload.clone();
    wrong["ordinal"] = json!(1);
    assert_eq!(
        call(&app, "POST", "/api/v1/ingest-batches/fenced/imports", wrong)
            .await
            .0,
        404
    );
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/ingest-batches/another/imports",
            upload.clone()
        )
        .await
        .0,
        404
    );
    let (status, source) = call(
        &app,
        "POST",
        "/api/v1/ingest-batches/fenced/imports",
        upload.clone(),
    )
    .await;
    assert_eq!(status, 202);
    let job = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],
        "ordinal":0,"source_id":source["source_id"],"source_revision":upload["expected_sha256"],"kind":"text"});
    assert_eq!(
        call(
            &app,
            "POST",
            "/api/v1/ingest-batches/fenced/jobs",
            job.clone()
        )
        .await
        .0,
        202
    );
    // Exercise the exact post-restore authorization transition independently of
    // snapshot publication. The separate backup test retains the full real path.
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    for (path, body) in [
        ("/api/v1/ingest-batches", manifest),
        ("/api/v1/ingest-batches/fenced/imports", upload),
        ("/api/v1/ingest-batches/fenced/jobs", job),
    ] {
        assert_eq!(call(&app, "POST", path, body).await.0, 409);
    }
    let (_, readback) = call(&app, "GET", "/api/v1/ingest-batches/fenced", Value::Null).await;
    assert_eq!(readback["members"][0]["job_state"], "queued");
    assert_eq!(
        conn.query_row::<i64, _, _>("SELECT count(*) FROM jobs", [], |r| r.get(0))
            .unwrap(),
        1
    );
}
