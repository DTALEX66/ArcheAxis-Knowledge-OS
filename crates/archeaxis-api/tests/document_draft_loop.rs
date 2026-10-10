//! A saved draft and its block projection are one immutable, restartable version.
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

#[tokio::test]
async fn live_owned_writer_backups_are_human_only_pathless_and_independently_restorable() {
    let dir = tempfile::tempdir().unwrap();
    let mut parent = dir.path().to_path_buf();
    #[cfg(windows)]
    while parent.to_string_lossy().len() < 280 {
        parent.push("live-backup-component-0123456789");
    }
    std::fs::create_dir_all(&parent).unwrap();
    let database = parent.join("workspace.sqlite");
    let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let (_, source) = call(
        &router,
        "POST",
        "/api/v1/imports",
        json!({"name":"source.txt","content_base64":"b3JpZ2luYWw="}),
        "human",
    )
    .await;
    let (status,document)=call(&router,"POST","/api/v1/documents",json!({"source_id":source["source_id"],"source_revision":source["sha256"],"title":"live snapshot","editor_json":{"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"stable"},"content":[{"type":"text","text":"真实 live backup"}]}]}}),"human").await;
    assert_eq!(status, 201);
    let route = "/api/v1/workspace/backups";
    assert_eq!(
        call(&router, "POST", route, json!({}), "machine").await.0,
        403
    );
    assert!(!parent.join("backups").exists());
    assert_eq!(
        call(
            &router,
            "POST",
            route,
            json!({"path":"outside.sqlite"}),
            "human"
        )
        .await
        .0,
        422
    );
    let (status, receipt) = call(&router, "POST", route, json!({}), "human").await;
    assert_eq!(status, 201, "{receipt}");
    assert_eq!(receipt["verified"], true);
    assert_eq!(receipt["source_sha_list"], json!([source["sha256"]]));
    assert_eq!(
        receipt["filename"],
        format!("{}.sqlite", receipt["backup_id"].as_str().unwrap())
    );
    assert!(receipt.get("path").is_none());
    assert!(
        archeaxis_store_sqlite::writer::Store::open(&database).is_err(),
        "live backup must not relax sole writer ownership"
    );
    let artifact = parent
        .join("backups")
        .join(receipt["filename"].as_str().unwrap());
    assert!(artifact.is_file());
    let (status, listed) = call(&router, "GET", route, json!(null), "machine").await;
    assert_eq!(status, 200, "{listed}");
    assert_eq!(listed["backups"], json!([receipt.clone()]));
    assert_eq!(receipt["schema"], "archeaxis-core-backup-1");
    use sha2::{Digest, Sha256};
    assert_eq!(
        receipt["sha256"],
        format!("{:x}", Sha256::digest(std::fs::read(&artifact).unwrap()))
    );
    std::fs::write(parent.join("backups/unrelated.sqlite"), b"not a backup").unwrap();
    assert_eq!(
        call(&router, "GET", route, json!(null), "human").await.1,
        listed,
        "unrelated names must not be read/listed"
    );
    let snapshot = rusqlite::Connection::open_with_flags(
        artifact.canonicalize().unwrap(),
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .unwrap();
    let restored = dir.path().join("independent.sqlite");
    let mut destination =
        archeaxis_store_sqlite::init_workspace(restored.to_str().unwrap()).unwrap();
    archeaxis_domain::backup::restore(artifact.to_str().unwrap(), &mut destination).unwrap();
    assert!(archeaxis_domain::backup::verify_counts(&snapshot, &destination).unwrap());
    assert_eq!(
        archeaxis_domain::document::read(
            &destination,
            document["document_id"].as_str().unwrap(),
            None
        )
        .unwrap(),
        document
    );
    assert_eq!(
        archeaxis_store_sqlite::raw_objects::read(&destination, source["sha256"].as_str().unwrap())
            .unwrap(),
        b"original"
    );
    drop(destination);
    let restored_router = archeaxis_api::app(restored.to_str().unwrap()).unwrap();
    assert_eq!(
        call(
            &restored_router,
            "GET",
            &format!(
                "/api/v1/documents/{}",
                document["document_id"].as_str().unwrap()
            ),
            json!(null),
            "human"
        )
        .await
        .1,
        document
    );
}

#[tokio::test]
async fn large_document_library_lists_bounded_metadata_and_reads_one_full_snapshot() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("large-library.sqlite");
    let router = archeaxis_api::app(path.to_str().unwrap()).unwrap();
    let (_, imported) = call(
        &router,
        "POST",
        "/api/v1/imports",
        json!({"name":"source.txt","content_base64":"b3JpZ2luYWw="}),
        "human",
    )
    .await;
    let mut conn = rusqlite::Connection::open(&path).unwrap();
    let editor = json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"large-block"},"content":[{"type":"text","text":"x".repeat(1_000_000)}]}]});
    let mut last = Value::Null;
    for index in 0..25 {
        last = archeaxis_domain::document::create(
            &mut conn,
            imported["source_id"].as_str().unwrap(),
            imported["sha256"].as_str().unwrap(),
            &format!("large {index}"),
            editor.clone(),
        )
        .unwrap();
    }
    let (status, listed) = call(&router, "GET", "/api/v1/documents", json!(null), "human").await;
    assert_eq!(status, 200);
    let rows = listed["documents"].as_array().unwrap();
    assert_eq!(rows.len(), 25);
    assert!(
        listed.to_string().len() < 32 * 1024,
        "25 megabyte drafts must list only bounded metadata"
    );
    for row in rows {
        assert_eq!(row.as_object().unwrap().len(), 6);
        for field in [
            "document_id",
            "source_id",
            "source_revision",
            "title",
            "version",
            "content_sha256",
        ] {
            assert!(row.get(field).is_some(), "missing {field}");
        }
        assert!(row.get("editor_json").is_none());
        assert!(row.get("blocks").is_none());
        assert!(row.get("text_projection").is_none());
    }
    let (_, full) = call(
        &router,
        "GET",
        &format!(
            "/api/v1/documents/{}",
            last["document_id"].as_str().unwrap()
        ),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(
        full, last,
        "opening one document must return the complete saved snapshot"
    );
}

async fn call(router: &Router, method: &str, path: &str, body: Value, actor: &str) -> (u16, Value) {
    let request = Request::builder()
        .method(method)
        .uri(path)
        .header("content-type", "application/json")
        .header("x-archeaxis-actor", actor)
        .body(Body::from(body.to_string()))
        .unwrap();
    let response = router.clone().oneshot(request).await.unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}

#[tokio::test]
async fn document_draft_is_atomic_versioned_conflict_checked_and_restorable_after_restart() {
    let directory = tempfile::tempdir().unwrap();
    let db = directory.path().join("documents.sqlite");
    let router = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (_, imported) = call(
        &router,
        "POST",
        "/api/v1/imports",
        json!({"name":"original.txt","content_base64":"b3JpZ2luYWw="}),
        "human",
    )
    .await;
    let editor = json!({"type":"doc","content":[
        {"type":"paragraph","attrs":{"block_id":"first"},"content":[{"type":"text","text":"中文 first"}]},
        {"type":"futureNode","attrs":{"block_id":"unknown","future":{"opaque":true}},"payload":{"kept":[1,2]}}
    ]});
    let body = json!({"source_id":imported["source_id"],"source_revision":imported["sha256"],"title":"Working note","editor_json":editor});
    let (status, original) =
        call(&router, "POST", "/api/v1/documents", body.clone(), "human").await;
    assert_eq!(status, 201, "{original}");
    assert_eq!(original["version"], 1);
    assert_eq!(original["source_revision"], imported["sha256"]);
    assert_eq!(original["editor_json"], editor);
    assert_eq!(original["text_projection"], "中文 first");
    assert_eq!(original["blocks"][1]["codec_status"], "preserved_unknown");
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/documents",
            body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    let mut invalid = body.clone();
    invalid["source_revision"] = json!("0".repeat(64));
    assert_eq!(
        call(&router, "POST", "/api/v1/documents", invalid, "human")
            .await
            .0,
        400
    );
    let document_id = original["document_id"].as_str().unwrap();
    let route = format!("/api/v1/documents/{document_id}");
    let mut updated = editor.clone();
    updated["content"][0]["content"][0]["text"] = json!("中文 second");
    let save = json!({"expected_version":1,"editor_json":updated});
    let (status, second) = call(
        &router,
        "PUT",
        &format!("{route}/draft"),
        save.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{second}");
    assert_eq!(second["version"], 2);
    assert_eq!(second["blocks"][0]["block_id"], "first");
    assert_eq!(
        call(&router, "PUT", &format!("{route}/draft"), save, "human")
            .await
            .0,
        409
    );
    assert_eq!(
        call(&router, "GET", &route, json!(null), "human").await.1,
        second
    );
    let duplicated =
        json!({"type":"doc","content":[editor["content"][0].clone(),editor["content"][0].clone()]});
    assert_eq!(
        call(
            &router,
            "PUT",
            &format!("{route}/draft"),
            json!({"expected_version":2,"editor_json":duplicated}),
            "human"
        )
        .await
        .0,
        400
    );
    assert_eq!(
        call(&router, "GET", &route, json!(null), "human").await.1,
        second,
        "rejected save must leave every projection unchanged"
    );
    let anchor_path = format!(
        "/api/v1/sources/{}/anchors",
        imported["source_id"].as_str().unwrap()
    );
    let anchor_body = json!({"revision":imported["sha256"],"position":"{\"kind\":\"text\",\"start\":0,\"end\":8}"});
    assert_eq!(
        call(&router, "POST", &anchor_path, anchor_body.clone(), "human")
            .await
            .0,
        201
    );
    assert_eq!(
        call(
            &router,
            "POST",
            &anchor_path,
            anchor_body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    assert_eq!(
        call(
            &router,
            "POST",
            &anchor_path,
            json!({"revision":"fictional","position":"{}"}),
            "human"
        )
        .await
        .0,
        400
    );
    let anchors = call(&router, "GET", &anchor_path, json!(null), "human")
        .await
        .1;
    assert_eq!(anchors["anchors"][0]["source_revision"], imported["sha256"]);
    assert_eq!(anchors["anchors"][0]["location_status"], "unverified");
    let located = json!({"revision":imported["sha256"],"position":"{\"type\":\"text\",\"start\":0,\"end\":8}","checksum":imported["sha256"]});
    let (status, result) = call(&router, "POST", &anchor_path, located.clone(), "human").await;
    assert_eq!(status, 201, "{result}");
    assert_eq!(result["location_status"], "located");
    assert_eq!(result["source_id"], imported["source_id"]);
    assert_eq!(result["source_revision"], imported["sha256"]);
    assert_eq!(result["checksum"], imported["sha256"]);
    assert!(result["position"].is_string());
    let (_, listed) = call(&router, "GET", &anchor_path, json!(null), "human").await;
    assert!(
        listed["anchors"].as_array().unwrap().contains(&result),
        "create and list must return identical DTOs"
    );
    let mut wrong = located;
    wrong["checksum"] = json!("0".repeat(64));
    assert_eq!(
        call(&router, "POST", &anchor_path, wrong, "human").await.0,
        400
    );
    let old = call(
        &router,
        "GET",
        &format!("{route}/versions/1"),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(old.0, 200);
    assert_eq!(old.1, original);
    for format in ["markdown", "obsidian"] {
        let (status, package) = call(
            &router,
            "GET",
            &format!("{route}/export?format={format}"),
            json!(null),
            "human",
        )
        .await;
        assert_eq!(status, 200, "{package}");
        assert_eq!(package["version"], 2);
        assert_eq!(package["files"][0]["path"], "document.md");
        assert_eq!(package["files"][1]["path"], "manifest.json");
        let manifest: Value =
            serde_json::from_str(package["files"][1]["content"].as_str().unwrap()).unwrap();
        assert_eq!(manifest["document"], second);
        assert_eq!(
            manifest["document"]["editor_json"]["content"][1],
            editor["content"][1]
        );
        assert!(manifest["anchors"].as_array().unwrap().len() >= 2);
        assert!(!manifest["loss"].as_array().unwrap().is_empty());
        let markdown = package["files"][0]["content"].as_str().unwrap();
        assert!(markdown.contains(second["text_projection"].as_str().unwrap()));
        assert!(!markdown.contains("[Immutable source](archeaxis://"));
        assert!(!markdown.contains("[Evidence anchor](archeaxis://"));
        let records: Vec<Value> = markdown
            .lines()
            .filter_map(|line| line.strip_prefix("    "))
            .map(|record| serde_json::from_str(record).unwrap())
            .collect();
        assert_eq!(
            records[0],
            json!({"source_id":second["source_id"],"source_revision":second["source_revision"]})
        );
        assert_eq!(&records[1..], manifest["anchors"].as_array().unwrap());
        assert!(
            manifest["loss"]
                .as_array()
                .unwrap()
                .iter()
                .any(|item| item["code"] == "external_navigation_unavailable")
        );
    }
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("{route}/export?format=../../outside"),
            json!(null),
            "human"
        )
        .await
        .0,
        400
    );
    let (status, restored) = call(
        &router,
        "POST",
        &format!("{route}/restore"),
        json!({"expected_version":2,"restore_version":1}),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{restored}");
    assert_eq!(restored["version"], 3);
    assert_eq!(restored["editor_json"], editor);
    drop(router);
    let restarted = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(&restarted, "GET", &route, json!(null), "human")
            .await
            .1,
        restored
    );
    let response = restarted
        .clone()
        .oneshot(
            Request::builder()
                .uri(format!(
                    "/api/v1/sources/{}/original",
                    imported["source_id"].as_str().unwrap()
                ))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), 200);
    let original: Value =
        serde_json::from_slice(&response.into_body().collect().await.unwrap().to_bytes()).unwrap();
    assert_eq!(original["sha256"], imported["sha256"]);
    assert_eq!(original["content_base64"], "b3JpZ2luYWw=");
    let corrupt =
        archeaxis_store_sqlite::raw_objects::root(&rusqlite::Connection::open(&db).unwrap())
            .unwrap()
            .join(imported["sha256"].as_str().unwrap());
    std::fs::write(corrupt, b"tampered").unwrap();
    assert_eq!(
        call(
            &restarted,
            "GET",
            &format!(
                "/api/v1/sources/{}/original",
                imported["source_id"].as_str().unwrap()
            ),
            json!(null),
            "human"
        )
        .await
        .0,
        500,
        "CAS tampering must not return corrupt original bytes"
    );
}

#[tokio::test]
async fn versioned_human_review_refuses_machine_and_stale_versions_without_partial_writes() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("review.sqlite");
    let router = archeaxis_api::app(path.to_str().unwrap()).unwrap();
    let mut conn = rusqlite::Connection::open(&path).unwrap();
    let actual: String = conn
        .query_row("SELECT sqlite_version()", [], |r| r.get(0))
        .unwrap();
    let (_, runtime) = call(
        &router,
        "GET",
        "/api/v1/system/version",
        json!(null),
        "human",
    )
    .await;
    assert_eq!(runtime["sqlite_version"], actual);
    println!("actual Store SQLite runtime: {actual}");
    let numbers: Vec<u32> = actual
        .split('.')
        .map(|value| value.parse().unwrap())
        .collect();
    assert!(
        numbers.as_slice() >= [3, 51, 3].as_slice(),
        "SQLite WAL-reset fix requires >=3.51.3, actual {actual}"
    );
    let id = archeaxis_domain::knowledge::create_knowledge(
        &mut conn,
        "OBSERVATION",
        "same immutable body",
        "candidate",
        None,
        None,
        "machine",
    )
    .unwrap();
    let get = format!("/api/v1/knowledge-items/{id}/v3");
    let route = format!("/api/v1/knowledge/{id}/review/versioned");
    let (_, before) = call(&router, "GET", &get, json!(null), "human").await;
    let body = json!({"action":"accepted","reviewer":"owner","expected_version":before["version"]});
    assert_eq!(
        call(&router, "POST", &route, body.clone(), "machine")
            .await
            .0,
        403
    );
    assert_eq!(
        call(&router, "GET", &get, json!(null), "human").await.1,
        before
    );
    let (status, accepted) = call(&router, "POST", &route, body.clone(), "human").await;
    assert_eq!(status, 200, "{accepted}");
    assert_ne!(accepted["version"], before["version"]);
    let (status, conflict) = call(&router, "POST", &route, body, "human").await;
    assert_eq!(status, 409, "{conflict}");
    assert_eq!(conflict["current_version"], accepted["version"]);
    let (_, after) = call(&router, "GET", &get, json!(null), "human").await;
    assert_eq!(after["body"], before["body"]);
    assert_eq!(after["status"], "accepted");
    let events: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM review_events WHERE knowledge_id=?1",
            [&id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        events, 1,
        "machine and stale requests must write no review events"
    );
    archeaxis_domain::learning::record_card_reference(&mut conn, "fresh-card", &id, None).unwrap();
    archeaxis_domain::learning::create_assessment(&mut conn, "fresh-card", &id).unwrap();
    let (_, queue) = call(
        &router,
        "GET",
        "/api/v1/learning/items",
        json!(null),
        "human",
    )
    .await;
    assert!(
        queue["items"]
            .as_array()
            .unwrap()
            .contains(&json!({"item_key":"fresh-card","next_review":null})),
        "unreviewed referenced assessment must be visible: {queue}"
    );
    let count: i64 = conn
        .query_row("SELECT COUNT(*) FROM learning_events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(
        count, 0,
        "reading queue must not fabricate review or mastery"
    );
}

#[tokio::test]
async fn original_notes_and_version_bound_checks_remain_independent_and_restorable() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("original.sqlite");
    let router = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let editor = json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"original-block"},"content":[{"type":"text","text":"原创，无来源，无认可仍保存"}]}]});
    let body = json!({"title":"original","editor_json":editor});
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/documents",
            body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    assert_eq!(
        call(
            &router,
            "POST",
            "/api/v1/documents",
            json!({"source_id":"absent","title":"invalid","editor_json":editor}),
            "human"
        )
        .await
        .0,
        400
    );
    let (status, original) = call(&router, "POST", "/api/v1/documents", body, "human").await;
    assert_eq!(status, 201, "{original}");
    assert_eq!(
        call(
            &router,
            "GET",
            "/api/v1/search?q=%E5%8E%9F%E5%88%9B",
            json!(null),
            "machine"
        )
        .await
        .1["documents"][0]["document_id"],
        original["document_id"]
    );
    assert!(original["source_id"].is_null() && original["source_revision"].is_null());
    let id = original["document_id"].as_str().unwrap();
    let check_route = format!("/api/v1/documents/{id}/checks");
    let initial = call(&router, "GET", &check_route, json!(null), "machine")
        .await
        .1;
    assert_eq!(initial["checks"], json!([]));
    assert_eq!(initial["default_status"], "unverified");
    let request = json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud"});
    let (status, pending) = call(&router, "POST", &check_route, request, "machine").await;
    assert_eq!(status, 201, "{pending}");
    assert_eq!(pending["status"], "pending");
    assert_eq!(pending["reason"], "worker_not_configured");
    assert_eq!(pending["execution_verified"], false);
    for fake in ["passed", "supported", "failed"] {
        assert_eq!(call(&router,"POST",&check_route,json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","status":fake}),"human").await.0,400);
    }
    let manual = json!({"version":1,"dimension":"professional_basis","provider_mode":"manual","status":"supported","basis":"人工核对实验记录，非云执行","position":{"block_id":"original-block"}});
    assert_eq!(
        call(&router, "POST", &check_route, manual.clone(), "machine")
            .await
            .0,
        403
    );
    let (status, support) = call(&router, "POST", &check_route, manual, "human").await;
    assert_eq!(status, 201, "{support}");
    assert_eq!(support["execution_state"], "reported_manual");
    for status in ["uncertain", "original_unclear", "conflicting"] {
        assert_eq!(call(&router,"POST",&check_route,json!({"version":1,"dimension":"recognition_fidelity","provider_mode":"manual","status":status}),"human").await.0,201);
    }
    assert_eq!(call(&router,"POST",&check_route,json!({"version":1,"dimension":"recognition_fidelity","provider_mode":"manual","status":"supported"}),"human").await.0,400);
    assert_eq!(call(&router,"POST",&check_route,json!({"version":1,"dimension":"recognition_fidelity","provider_mode":"manual","status":"faithful","basis":"未经核实","position":{"type":"text","start":0,"end":1},"recognition_job_id":"unknown","recognition_result_sha256":"bad"}),"human").await.0,400);
    let draft = format!("/api/v1/documents/{id}/draft");
    assert_eq!(call(&router,"PUT",&draft,json!({"expected_version":1,"editor_json":editor,"revision_basis":{"rationale":"edit","human_approved":true}}),"human").await.0,400);
    assert_eq!(call(&router,"PUT",&draft,json!({"expected_version":1,"editor_json":editor,"revision_basis":{"reference_version":9,"rationale":"edit"}}),"human").await.0,400);
    let basis = json!({"reference_version":1,"check_id":support["check_id"],"position":{"block_id":"original-block"},"rationale":"保留旧版专业依据，非认可"});
    let mut invalid_basis = basis.clone();
    invalid_basis["position"] = json!({"block_id":"unknown-block"});
    assert_eq!(
        call(
            &router,
            "PUT",
            &draft,
            json!({"expected_version":1,"editor_json":editor,"revision_basis":invalid_basis}),
            "human"
        )
        .await
        .0,
        400
    );
    let (status, saved) = call(
        &router,
        "PUT",
        &draft,
        json!({"expected_version":1,"editor_json":editor,"revision_basis":basis}),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{saved}");
    assert_eq!(saved["revision_basis"], basis);
    assert_eq!(
        call(&router, "GET", &check_route, json!(null), "human")
            .await
            .1["checks"],
        json!([])
    );
    let historical = call(
        &router,
        "GET",
        &format!("{check_route}?version=1"),
        json!(null),
        "human",
    )
    .await
    .1;
    assert_eq!(historical["historical"], true);
    assert_eq!(historical["checks"].as_array().unwrap().len(), 5);
    let (status, export) = call(
        &router,
        "GET",
        &format!("/api/v1/documents/{id}/export?format=markdown"),
        json!(null),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{export}");
    let (status, backup) = call(
        &router,
        "POST",
        "/api/v1/workspace/backups",
        json!({}),
        "human",
    )
    .await;
    assert_eq!(status, 201, "{backup}");
    let artifact = dir
        .path()
        .join("backups")
        .join(backup["filename"].as_str().unwrap());
    let restored_path = dir.path().join("restored.sqlite");
    let mut destination =
        archeaxis_store_sqlite::init_workspace(restored_path.to_str().unwrap()).unwrap();
    archeaxis_domain::backup::restore(artifact.to_str().unwrap(), &mut destination).unwrap();
    assert_eq!(
        archeaxis_domain::document::read(&destination, id, None).unwrap(),
        saved
    );
    assert_eq!(
        archeaxis_domain::document::checks(&destination, id, Some(1)).unwrap(),
        historical
    );
    drop(destination);
    drop(router);
    let restarted = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        call(
            &restarted,
            "GET",
            &format!("/api/v1/documents/{id}"),
            json!(null),
            "human"
        )
        .await
        .1,
        saved
    );
    assert_eq!(
        call(
            &restarted,
            "GET",
            &format!("{check_route}?version=1"),
            json!(null),
            "human"
        )
        .await
        .1,
        historical
    );
    // Save remains independent even after failed/pending checks and without a revision basis.
    let updated = json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"updated_search_only"}]}]});
    assert_eq!(
        call(
            &restarted,
            "PUT",
            &draft,
            json!({"expected_version":2,"editor_json":updated}),
            "human"
        )
        .await
        .0,
        200
    );
    assert_eq!(
        call(
            &restarted,
            "GET",
            "/api/v1/search?q=updated_search_only",
            json!(null),
            "machine"
        )
        .await
        .1["documents"][0]["version"],
        3
    );
    assert_eq!(
        call(
            &restarted,
            "GET",
            "/api/v1/search?q=%E5%8E%9F%E5%88%9B",
            json!(null),
            "machine"
        )
        .await
        .1["documents"],
        json!([])
    );
    assert_eq!(
        call(
            &restarted,
            "GET",
            "/api/v1/search?q=%25",
            json!(null),
            "machine"
        )
        .await
        .1["documents"],
        json!([])
    );
}

#[tokio::test]
async fn completed_real_recognition_is_not_a_fidelity_basis_or_human_approval_by_itself() {
    use archeaxis_application::{executor::Executor, jobs};
    use archeaxis_domain::source::{self, ImportOutcome};
    let dir = tempfile::tempdir().unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
    )
    .await
    .unwrap();
    let source = executor
        .store()
        .submit(|conn| {
            let id = match source::import_source(conn, "original text".as_bytes(), "test.txt", None)
                .unwrap()
            {
                ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            jobs::enqueue(conn, "recognition-job", "text", &id).unwrap();
            let revision: String = conn
                .query_row(
                    "SELECT sha256 FROM sources WHERE source_id=?1",
                    [&id],
                    |r| r.get(0),
                )
                .unwrap();
            (id, revision)
        })
        .await
        .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/jobs/recognition-job/executions")
                .header("content-type", "application/json")
                .header("idempotency-key", "real-recognition-check")
                .body(Body::from("{\"deadline_ms\":5000}"))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), 202);
    tokio::time::timeout(std::time::Duration::from_secs(6), async {
        loop {
            let state = call(
                &router,
                "GET",
                "/api/v1/jobs/recognition-job",
                json!(null),
                "human",
            )
            .await
            .1;
            if state["state"] == "succeeded" {
                break;
            }
            assert!(
                state["state"] == "running" || state["state"] == "queued",
                "{state}"
            );
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    let editor = json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"original text"}]}]});
    let (status,doc)=call(&router,"POST","/api/v1/documents",json!({"source_id":source.0,"source_revision":source.1,"title":"recognition","editor_json":editor}),"human").await;
    assert_eq!(status, 201, "{doc}");
    let route = format!(
        "/api/v1/documents/{}/checks",
        doc["document_id"].as_str().unwrap()
    );
    assert_eq!(
        call(&router, "GET", &route, json!(null), "human").await.1["checks"],
        json!([]),
        "recognition processing success must not create fidelity/basis/approval"
    );
    let output = call(
        &router,
        "GET",
        "/api/v1/jobs/recognition-job/outputs/text",
        json!(null),
        "human",
    )
    .await
    .1;
    assert_eq!(output["content"], "original text");
    use sha2::{Digest, Sha256};
    let digest = format!(
        "{:x}",
        Sha256::digest(output["content"].as_str().unwrap().as_bytes())
    );
    let mut record = json!({"version":1,"dimension":"recognition_fidelity","provider_mode":"manual","status":"faithful","source_id":source.0,"source_revision":source.1,"recognition_job_id":"recognition-job","recognition_result_sha256":digest,"position":{"type":"text","start":0,"end":13},"basis":"Human compared actual original bytes and worker text"});
    let mut wrong_position = record.clone();
    wrong_position["position"]["end"] = json!(99999);
    assert_eq!(
        call(&router, "POST", &route, wrong_position, "human")
            .await
            .0,
        400
    );
    let (status, receipt) = call(&router, "POST", &route, record.clone(), "human").await;
    assert_eq!(status, 201, "{receipt}");
    assert_eq!(receipt["execution_verified"], false);
    assert_eq!(receipt["recognition_result_sha256"], digest);
    record["recognition_result_sha256"] =
        json!("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff");
    assert_eq!(call(&router, "POST", &route, record, "human").await.0, 400);
    assert_eq!(
        call(&router, "GET", &route, json!(null), "human").await.1["checks"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
}

#[tokio::test]
async fn check_history_pagination_exposes_every_record_without_inheriting_new_version() {
    let dir = tempfile::tempdir().unwrap();
    let router = archeaxis_api::app(dir.path().join("history.sqlite").to_str().unwrap()).unwrap();
    let doc = call(
        &router,
        "POST",
        "/api/v1/documents",
        json!({"title":"history","editor_json":{"type":"doc","content":[]}}),
        "human",
    )
    .await
    .1;
    let route = format!(
        "/api/v1/documents/{}/checks",
        doc["document_id"].as_str().unwrap()
    );
    let body = json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud"});
    let mut last = Value::Null;
    for _ in 0..1001 {
        let (status, receipt) = call(&router, "POST", &route, body.clone(), "machine").await;
        assert_eq!(status, 201, "{receipt}");
        last = receipt;
    }
    let first = call(&router, "GET", &route, json!(null), "human").await.1;
    assert_eq!(first["checks"].as_array().unwrap().len(), 1000);
    assert_eq!(first["checks_capped"], true);
    assert_eq!(first["next_offset"], 1000);
    let second = call(
        &router,
        "GET",
        &format!("{route}?offset=1000"),
        json!(null),
        "human",
    )
    .await
    .1;
    assert_eq!(second["checks"], json!([last]));
    assert_eq!(second["checks_capped"], false);
    assert!(second["next_offset"].is_null());
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("{route}?offset=-1"),
            json!(null),
            "human"
        )
        .await
        .0,
        400
    );
}

#[tokio::test]
async fn unconfigured_document_check_is_human_only_version_bound_retryable_after_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("checks.sqlite");
    let router = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status,doc)=call(&router,"POST","/api/v1/documents",json!({"title":"ordinary","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"original ordinary text"}]}]}}),"human").await;
    assert_eq!(status, 201, "{doc}");
    assert!(doc["source_id"].is_null());
    let path = format!("/api/v1/documents/{}", doc["document_id"].as_str().unwrap());
    let checks = format!("{path}/checks");
    let execute = format!("{checks}/execute");
    let (status, pending) = call(
        &router,
        "POST",
        &checks,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud"}),
        "human",
    )
    .await;
    assert_eq!(status, 201, "{pending}");
    assert_ne!(call(&router,"POST",&checks,json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud","status":"supported"}),"human").await.0,201);
    let body =
        json!({"check_id":pending["check_id"],"expected_content_sha256":doc["content_sha256"]});
    assert_eq!(
        call(&router, "POST", &execute, body.clone(), "machine")
            .await
            .0,
        403
    );
    let mut unknown = body.clone();
    unknown["model"] = json!("forbidden");
    assert_eq!(
        call(&router, "POST", &execute, unknown, "human").await.0,
        422
    );
    let mut wrong = body.clone();
    wrong["expected_content_sha256"] = json!("wrong");
    assert_ne!(call(&router, "POST", &execute, wrong, "human").await.0, 201);
    let (status, a) = call(&router, "POST", &execute, body.clone(), "human").await;
    assert_eq!(status, 201, "{a}");
    assert_eq!(a["reason"], "not_configured");
    assert_eq!(a["execution_verified"], false);
    assert_ne!(
        call(&router, "POST", &execute, body.clone(), "human")
            .await
            .0,
        201
    );
    let (status,saved)=call(&router,"PUT",&format!("{path}/draft"),json!({"expected_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"still saveable"}]}]}}),"human").await;
    assert_eq!(status, 200, "{saved}");
    assert_eq!(saved["version"], 2);
    drop(router);
    let restarted = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let mut retry = body;
    retry["retry_of_task_id"] = a["attempt_id"].clone();
    let (status, b) = call(&restarted, "POST", &execute, retry, "human").await;
    assert_eq!(status, 201, "{b}");
    assert_ne!(a["attempt_id"], b["attempt_id"]);
    assert_eq!(b["version"], 1);
    let history = call(
        &restarted,
        "GET",
        &format!("{checks}?version=1"),
        json!(null),
        "human",
    )
    .await
    .1;
    assert_eq!(history["historical"], true);
    assert_eq!(history["checks"].as_array().unwrap().len(), 3);
    assert_eq!(
        call(&restarted, "GET", &path, json!(null), "human").await.1["text_projection"],
        saved["text_projection"]
    );
}

#[tokio::test]
async fn recovery_preview_is_read_only_bound_to_identity_and_rejects_bad_cas_schema_and_machine() {
    use sha2::{Digest, Sha256};
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("workspace.sqlite");
    let router = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let (_, source) = call(
        &router,
        "POST",
        "/api/v1/imports",
        json!({"name":"original.txt","content_base64":"b3JpZ2luYWw="}),
        "human",
    )
    .await;
    let (_, receipt) = call(
        &router,
        "POST",
        "/api/v1/workspace/backups",
        json!({}),
        "human",
    )
    .await;
    let selection = json!({"backup_id":receipt["backup_id"],"expected_sha256":receipt["sha256"]});
    let route = "/api/v2/workspace/restore/preview";
    assert_eq!(
        call(&router, "POST", route, selection.clone(), "machine")
            .await
            .0,
        403
    );
    let before = call(&router, "GET", "/api/v1/sources", json!(null), "human")
        .await
        .1;
    let (status, preview) = call(&router, "POST", route, selection.clone(), "human").await;
    assert_eq!(status, 200, "{preview}");
    assert_eq!(preview["source_count"], 1);
    assert_eq!(preview["verified"], true);
    assert_eq!(
        call(
            &router,
            "POST",
            route,
            json!({"backup_id":"../outside","expected_sha256":receipt["sha256"]}),
            "human"
        )
        .await
        .0,
        400
    );
    assert_eq!(
        call(
            &router,
            "POST",
            route,
            json!({"backup_id":receipt["backup_id"],"expected_sha256":"a".repeat(64)}),
            "human"
        )
        .await
        .0,
        409
    );
    assert_eq!(call(&router,"POST",route,json!({"backup_id":receipt["backup_id"],"expected_sha256":receipt["sha256"],"path":"outside"}),"human").await.0,422);
    let backup = dir
        .path()
        .join("backups")
        .join(receipt["filename"].as_str().unwrap());
    let objects = std::path::PathBuf::from(format!("{}.objects", backup.display()));
    let object = objects.join(source["sha256"].as_str().unwrap());
    std::fs::write(&object, b"tampered").unwrap();
    assert_eq!(
        call(&router, "POST", route, selection.clone(), "human")
            .await
            .0,
        409
    );
    std::fs::write(&object, b"original").unwrap();
    let conn = rusqlite::Connection::open(&backup).unwrap();
    conn.execute(
        "UPDATE workspace_meta SET value='99999' WHERE key='schema_version'",
        [],
    )
    .unwrap();
    drop(conn);
    let sha = format!("{:x}", Sha256::digest(std::fs::read(&backup).unwrap()));
    let manifest = std::path::PathBuf::from(format!("{}.manifest.json", backup.display()));
    let mut value: Value = serde_json::from_slice(&std::fs::read(&manifest).unwrap()).unwrap();
    value["sha256"] = json!(sha);
    value["schema_version"] = json!("99999");
    std::fs::write(&manifest, serde_json::to_vec(&value).unwrap()).unwrap();
    assert_eq!(
        call(
            &router,
            "POST",
            route,
            json!({"backup_id":receipt["backup_id"],"expected_sha256":sha}),
            "human"
        )
        .await
        .0,
        409
    );
    assert_eq!(
        call(&router, "GET", "/api/v1/sources", json!(null), "human")
            .await
            .1,
        before,
        "rejected preview must preserve the live workspace"
    );
    assert_eq!(
        call(
            &router,
            "GET",
            &format!(
                "/api/v1/sources/{}/original",
                source["source_id"].as_str().unwrap()
            ),
            json!(null),
            "human"
        )
        .await
        .1["content_base64"],
        "b3JpZ2luYWw="
    );
}
