use archeaxis_domain::{
    anchor, knowledge,
    source::{self, ImportOutcome},
    teaching::*,
};
use archeaxis_store_sqlite::{init_workspace, writer::Store};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

// Public, synthetic fixture credentials. Never reads a real launch/session secret.
const HUMAN_TOKEN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const MACHINE_TOKEN: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
fn fixture() -> (tempfile::TempDir, std::path::PathBuf, String) {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("teaching.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let sid = match source::import_source(
        &mut conn,
        b"Evidence remains immutable.",
        "evidence.md",
        None,
    )
    .unwrap()
    {
        ImportOutcome::Imported { source_id, .. } => source_id,
        _ => unreachable!(),
    };
    let hash: String = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&sid],
            |r| r.get(0),
        )
        .unwrap();
    let aid = anchor::add_anchor(&mut conn, &sid, &hash, r#"{"line":1}"#).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "Evidence remains immutable.",
        "accepted",
        None,
        Some(&aid),
        "human",
    )
    .unwrap();
    drop(conn);
    (dir, db, kid)
}
fn row(kind: RecordKind, id: &str, parent: Option<&str>, kid: &str) -> TeachingRecord {
    TeachingRecord {
        schema: RECORD_SCHEMA.into(),
        record_id: id.into(),
        kind,
        knowledge_id: kid.into(),
        knowledge_version: kid.into(),
        course_id: None,
        parent_id: parent.map(str::to_owned),
        purpose: "人工需求、教学交换与复述".into(),
        scope: RecordScope::ManualExchange,
        privacy: RecordPrivacy::AuthorizedExport,
        content: "中文原文 <script>inert</script>：不是执行指令。".into(),
        feedback_class: None,
        assessment_id: None,
        rubric_version: None,
        assisted: false,
        producer_kind: ProducerKind::HumanAuthored,
    }
}
fn chain(kid: &str) -> Vec<TeachingRecord> {
    let mut rows = vec![
        row(RecordKind::Observation, "obs", None, kid),
        row(RecordKind::Requirement, "req", Some("obs"), kid),
        row(RecordKind::Proposal, "proposal", Some("req"), kid),
        row(RecordKind::Delivery, "delivery", Some("proposal"), kid),
        row(RecordKind::Feedback, "feedback", Some("delivery"), kid),
        row(RecordKind::Revision, "revision", Some("feedback"), kid),
        row(RecordKind::Delivery, "delivery2", Some("revision"), kid),
        row(RecordKind::TeachBack, "teachback", Some("delivery2"), kid),
    ];
    rows[4].feedback_class = Some(FeedbackClass::EvidenceFidelity);
    rows
}
async fn call(
    app: &Router,
    method: &str,
    path: &str,
    body: Value,
    actor: Option<&str>,
    token: Option<&str>,
) -> (u16, Value) {
    let mut req = Request::builder()
        .method(method)
        .uri(path)
        .header("content-type", "application/json");
    if let Some(actor) = actor {
        req = req.header("x-archeaxis-actor", actor);
    }
    if let Some(token) = token {
        req = req.header("x-archeaxis-launch-token", token);
    }
    let response = app
        .clone()
        .oneshot(req.body(Body::from(body.to_string())).unwrap())
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
async fn human(app: &Router, method: &str, path: &str, body: Value) -> (u16, Value) {
    call(app, method, path, body, Some("human"), None).await
}

#[tokio::test]
async fn incomplete_preparation_initial_creation_retries_the_same_document_after_reopen() {
    let (_dir, db, _) = fixture();
    let request = json!({"create_request_id":"preparation_stable_attempt","title":"不完整准备","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"尚无正式知识或需求绑定"}]}]}});
    let app = archeaxis_api::router(Store::open(&db).unwrap());
    let (status, first) = human(&app, "POST", "/api/v1/documents", request.clone()).await;
    assert_eq!(status, 201, "{first}");
    drop(app);
    let app = archeaxis_api::router(Store::open(&db).unwrap());
    let (status, retry) = human(&app, "POST", "/api/v1/documents", request.clone()).await;
    assert_eq!(status, 201, "{retry}");
    assert_eq!(retry, first);
    let mut conflicting = request;
    conflicting["title"] = json!("不同内容");
    assert_eq!(
        human(&app, "POST", "/api/v1/documents", conflicting)
            .await
            .0,
        409
    );
    drop(app);
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        conn.query_row("SELECT COUNT(*) FROM documents", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        1
    );
}
async fn count(app: &Router) -> usize {
    let (status, page) = human(app, "GET", "/api/v2/teaching/records", json!({})).await;
    assert_eq!(status, 200, "{page}");
    page["items"].as_array().unwrap().len()
}
async fn put_chain(app: &Router, rows: &[TeachingRecord]) {
    for row in rows {
        let (status, value) = human(
            app,
            "POST",
            "/api/v2/teaching/records",
            serde_json::to_value(row).unwrap(),
        )
        .await;
        assert_eq!(status, 201, "{value}");
        assert_eq!(value["item"]["scoring_status"], "not_scored");
        assert_eq!(value["duplicate"], false);
    }
}

#[tokio::test]
async fn trusted_launch_principal_overrides_spoofed_actor_and_missing_actor_is_never_human() {
    let (_dir, db, kid) = fixture();
    let store = Store::open(&db).unwrap();
    let launch=serde_json::from_value(json!({"launch_token":HUMAN_TOKEN,"machine_token":MACHINE_TOKEN,"session_id":"cccccccccccccccccccccccccccccccc","actor":"human","protocol":"archeaxis.desktop-launch/v2"})).unwrap();
    let protected =
        archeaxis_api::launch::protect(archeaxis_api::router(store.clone()), &store, launch)
            .await
            .unwrap();
    let body = serde_json::to_value(row(RecordKind::Requirement, "req", None, &kid)).unwrap();
    assert_eq!(
        call(
            &protected,
            "POST",
            "/api/v2/teaching/records",
            body.clone(),
            Some("human"),
            None
        )
        .await
        .0,
        401
    );
    assert_eq!(
        call(
            &protected,
            "POST",
            "/api/v2/teaching/records",
            body.clone(),
            Some("human"),
            Some(MACHINE_TOKEN)
        )
        .await
        .0,
        403
    );
    assert_eq!(
        call(
            &protected,
            "POST",
            "/api/v2/teaching/records",
            body.clone(),
            Some("machine"),
            Some(HUMAN_TOKEN)
        )
        .await
        .0,
        201
    );
    // Thin in-process routes also refuse absent/misspelled principals; production is always protected.
    let unprotected = archeaxis_api::router(store.clone());
    for actor in [None, Some("machine"), Some("Human")] {
        assert_eq!(
            call(
                &unprotected,
                "POST",
                "/api/v2/teaching/records",
                body.clone(),
                actor,
                None
            )
            .await
            .0,
            403
        );
    }
    assert_eq!(
        call(
            &protected,
            "GET",
            "/api/v2/teaching/records",
            json!({}),
            Some("human"),
            None
        )
        .await
        .0,
        401
    );
    for path in [
        "/api/v2/teaching/records/req/export",
        "/api/v2/teaching/imports/preview",
        "/api/v2/teaching/imports",
        "/api/v2/teaching/withdrawals",
    ] {
        let (method, payload) = if path.ends_with("export") {
            ("GET", json!({}))
        } else if path.ends_with("withdrawals") {
            (
                "POST",
                json!({"schema":WITHDRAWAL_SCHEMA,"withdrawal_id":"withdraw-req","record_id":"req","reason":"人工撤回"}),
            )
        } else {
            let r = row(RecordKind::Requirement, "new", None, &kid);
            (
                "POST",
                json!({"schema":EXCHANGE_SCHEMA,"records":[r.clone()],"package_sha256":package_hash(&[r]).unwrap()}),
            )
        };
        assert_eq!(
            call(
                &protected,
                method,
                path,
                payload,
                Some("human"),
                Some(MACHINE_TOKEN)
            )
            .await
            .0,
            403
        );
    }
    assert_eq!(count(&unprotected).await, 1);
}

#[tokio::test]
async fn strict_fields_and_missing_references_fail_without_writes() {
    let (_dir, db, kid) = fixture();
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let good = serde_json::to_value(row(RecordKind::Requirement, "req", None, &kid)).unwrap();
    for field in ["actor", "provider", "verified", "status", "truth", "score"] {
        let mut bad = good.clone();
        bad[field] = json!("human");
        assert_eq!(
            human(&app, "POST", "/api/v2/teaching/records", bad).await.0,
            422
        );
    }
    for (field, value, expected) in [
        ("knowledge_id", json!("missing"), 422),
        ("knowledge_version", json!("missing"), 422),
        ("course_id", json!("missing"), 404),
        ("assessment_id", json!("missing"), 404),
        ("record_id", json!("../escape"), 422),
        ("purpose", json!(" "), 422),
    ] {
        let mut bad = good.clone();
        bad[field] = value;
        assert_eq!(
            human(&app, "POST", "/api/v2/teaching/records", bad).await.0,
            expected
        );
    }
    let mut missing = good.clone();
    missing["knowledge_id"] = json!("missing");
    missing["knowledge_version"] = json!("missing");
    assert_eq!(
        human(&app, "POST", "/api/v2/teaching/records", missing)
            .await
            .0,
        404
    );
    let mut orphan = row(RecordKind::Proposal, "orphan", Some("missing"), &kid);
    assert_eq!(
        human(
            &app,
            "POST",
            "/api/v2/teaching/records",
            serde_json::to_value(&orphan).unwrap()
        )
        .await
        .0,
        404
    );
    orphan.parent_id = None;
    assert_eq!(
        human(
            &app,
            "POST",
            "/api/v2/teaching/records",
            serde_json::to_value(orphan).unwrap()
        )
        .await
        .0,
        422
    );
    assert_eq!(
        human(
            &app,
            "GET",
            "/api/v2/teaching/records?actor=human",
            json!({})
        )
        .await
        .0,
        400
    );
    assert_eq!(count(&app).await, 0);
}

#[tokio::test]
async fn complete_formal_chain_replays_conflicts_and_reopens_exact_content() {
    let (_dir, db, kid) = fixture();
    let rows = chain(&kid);
    let first;
    {
        let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
        put_chain(&app, &rows).await;
        let (status, value) =
            human(&app, "GET", "/api/v2/teaching/records/teachback", json!({})).await;
        assert_eq!(status, 200);
        first = value;
        assert_eq!(first["record"], serde_json::to_value(&rows[7]).unwrap());
        let (status, replay) = human(
            &app,
            "POST",
            "/api/v2/teaching/records",
            serde_json::to_value(&rows[7]).unwrap(),
        )
        .await;
        assert_eq!(status, 200);
        assert_eq!(replay["duplicate"], true);
        assert_eq!(replay["item"], first);
        let mut changed = rows[7].clone();
        changed.content.push('!');
        assert_eq!(
            human(
                &app,
                "POST",
                "/api/v2/teaching/records",
                serde_json::to_value(changed).unwrap()
            )
            .await
            .0,
            409
        );
        assert_eq!(count(&app).await, 8);
    }
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(
        human(&app, "GET", "/api/v2/teaching/records/teachback", json!({})).await,
        (200, first)
    );
    let conn = rusqlite::Connection::open(&db).unwrap();
    let knowledge: String = conn
        .query_row(
            "SELECT body FROM knowledge WHERE knowledge_id=?1",
            [&kid],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(knowledge, "Evidence remains immutable.");
    let events: i64 = conn
        .query_row("SELECT COUNT(*) FROM learning_events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(
        events, 0,
        "Unscored teaching is not an FSRS review or qualification event"
    );
}

#[tokio::test]
async fn export_preview_import_validate_all_and_replay_without_resurrection() {
    let (_dir, db, kid) = fixture();
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let rows = chain(&kid);
    put_chain(&app, &rows).await;
    let (status, export) = human(
        &app,
        "GET",
        "/api/v2/teaching/records/teachback/export",
        json!({}),
    )
    .await;
    assert_eq!(status, 200, "{export}");
    let bundle: ExchangeBundle = serde_json::from_value(export).unwrap();
    assert_eq!(bundle.records, rows);
    assert_eq!(bundle.package_sha256, package_hash(&rows).unwrap());
    let mut fresh = bundle.clone();
    for r in &mut fresh.records {
        r.record_id = format!("copy-{}", r.record_id);
        r.parent_id = r.parent_id.as_ref().map(|id| format!("copy-{id}"));
    }
    fresh.records.reverse();
    fresh.package_sha256 = package_hash(&fresh.records).unwrap();
    let payload = serde_json::to_value(&fresh).unwrap();
    let (status, preview) = human(
        &app,
        "POST",
        "/api/v2/teaching/imports/preview",
        payload.clone(),
    )
    .await;
    assert_eq!(status, 200, "{preview}");
    assert_eq!(preview["valid"], true);
    assert_eq!(preview["record_count"], 8);
    assert_eq!(preview["duplicate_count"], 0);
    assert_eq!(count(&app).await, 8, "Preview must not insert");
    let mut tampered = payload.clone();
    tampered["records"][0]["content"] = json!("tampered");
    assert_eq!(
        human(&app, "POST", "/api/v2/teaching/imports", tampered)
            .await
            .0,
        422
    );
    assert_eq!(count(&app).await, 8);
    let mut malformed = payload.clone();
    malformed["records"][0]["actor"] = json!("human");
    assert_eq!(
        human(&app, "POST", "/api/v2/teaching/imports/preview", malformed)
            .await
            .0,
        422
    );
    let (status, receipt) = human(&app, "POST", "/api/v2/teaching/imports", payload.clone()).await;
    assert_eq!(status, 201, "{receipt}");
    assert_eq!(receipt["items"].as_array().unwrap().len(), 8);
    assert_eq!(receipt["duplicate_count"], 0);
    assert_eq!(receipt["package_sha256"], fresh.package_sha256);
    assert_eq!(count(&app).await, 16);
    let (status, duplicate) =
        human(&app, "POST", "/api/v2/teaching/imports", payload.clone()).await;
    assert_eq!(status, 200);
    assert_eq!(duplicate["duplicate_count"], 8);
    let withdrawal = json!({"schema":WITHDRAWAL_SCHEMA,"withdrawal_id":"withdraw-copy","record_id":"copy-req","reason":"人工撤回"});
    assert_eq!(
        human(&app, "POST", "/api/v2/teaching/withdrawals", withdrawal)
            .await
            .0,
        201
    );
    let (status, replay) = human(&app, "POST", "/api/v2/teaching/imports", payload).await;
    assert_eq!(status, 200, "{replay}");
    assert_eq!(replay["duplicate_count"], 8);
    assert!(
        replay["items"]
            .as_array()
            .unwrap()
            .iter()
            .find(|v| v["record"]["record_id"] == "copy-teachback")
            .unwrap()["withdrawn"]
            .as_bool()
            .unwrap()
    );
    assert_eq!(count(&app).await, 16);
}

#[tokio::test]
async fn withdrawal_projects_descendants_preserves_history_and_blocks_children_export() {
    let (_dir, db, kid) = fixture();
    let rows = chain(&kid);
    let before;
    {
        let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
        put_chain(&app, &rows).await;
        before = human(&app, "GET", "/api/v2/teaching/records/teachback", json!({}))
            .await
            .1;
        let mut local = row(RecordKind::Requirement, "private", None, &kid);
        local.privacy = RecordPrivacy::LocalOnly;
        put_chain(&app, &[local]).await;
        assert_eq!(
            human(
                &app,
                "GET",
                "/api/v2/teaching/records/private/export",
                json!({})
            )
            .await
            .0,
            409
        );
        let w = json!({"schema":WITHDRAWAL_SCHEMA,"withdrawal_id":"withdraw-req","record_id":"req","reason":"保留历史，撤回后续授权"});
        let (status, receipt) =
            human(&app, "POST", "/api/v2/teaching/withdrawals", w.clone()).await;
        assert_eq!(status, 201, "{receipt}");
        assert_eq!(receipt["affected_record_ids"].as_array().unwrap().len(), 7);
        let (status, replay) = human(&app, "POST", "/api/v2/teaching/withdrawals", w.clone()).await;
        assert_eq!(status, 200);
        assert_eq!(replay["duplicate"], true);
        let mut changed = w;
        changed["reason"] = json!("different");
        assert_eq!(
            human(&app, "POST", "/api/v2/teaching/withdrawals", changed)
                .await
                .0,
            409
        );
        assert_eq!(
            human(
                &app,
                "GET",
                "/api/v2/teaching/records/teachback/export",
                json!({})
            )
            .await
            .0,
            409
        );
        let child = row(RecordKind::Feedback, "late", Some("delivery2"), &kid);
        assert_eq!(
            human(
                &app,
                "POST",
                "/api/v2/teaching/records",
                serde_json::to_value(child).unwrap()
            )
            .await
            .0,
            409
        );
    }
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    let (status, after) = human(&app, "GET", "/api/v2/teaching/records/teachback", json!({})).await;
    assert_eq!(status, 200);
    assert_eq!(after["record"], before["record"]);
    assert_eq!(after["content_sha256"], before["content_sha256"]);
    assert_eq!(after["withdrawn"], true);
    assert_eq!(
        human(&app, "GET", "/api/v2/teaching/records/obs", json!({}))
            .await
            .1["withdrawn"],
        false
    );
}

#[tokio::test]
async fn pagination_and_invalid_complete_bundle_are_bounded_and_atomic() {
    let (_dir, db, kid) = fixture();
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    for i in 0..23 {
        put_chain(
            &app,
            &[row(
                RecordKind::Requirement,
                &format!("req-{i:02}"),
                None,
                &kid,
            )],
        )
        .await;
    }
    let (status, page) = human(&app, "GET", "/api/v2/teaching/records", json!({})).await;
    assert_eq!(status, 200);
    assert_eq!(page["items"].as_array().unwrap().len(), 20);
    let cursor = page["next_cursor"].as_str().unwrap();
    let (status, next) = human(
        &app,
        "GET",
        &format!("/api/v2/teaching/records?cursor={cursor}"),
        json!({}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(next["items"].as_array().unwrap().len(), 3);
    assert!(next["next_cursor"].is_null());
    let ids: std::collections::HashSet<_> = page["items"]
        .as_array()
        .unwrap()
        .iter()
        .chain(next["items"].as_array().unwrap())
        .map(|v| v["record"]["record_id"].as_str().unwrap())
        .collect();
    assert_eq!(ids.len(), 23);
    let records = vec![
        row(RecordKind::Requirement, "new-valid", None, &kid),
        row(
            RecordKind::Proposal,
            "new-orphan",
            Some("missing-parent"),
            &kid,
        ),
    ];
    let bundle = json!({"schema":EXCHANGE_SCHEMA,"package_sha256":package_hash(&records).unwrap(),"records":records});
    for path in [
        "/api/v2/teaching/imports/preview",
        "/api/v2/teaching/imports",
    ] {
        assert_eq!(human(&app, "POST", path, bundle.clone()).await.0, 404);
        assert_eq!(
            human(&app, "GET", "/api/v2/teaching/records/new-valid", json!({}))
                .await
                .0,
            404,
            "A valid prefix may not be inserted before a later invalid member"
        );
    }
    let conn = rusqlite::Connection::open(&db).unwrap();
    let total: i64 = conn
        .query_row("SELECT count(*) FROM teaching_records", [], |r| r.get(0))
        .unwrap();
    assert_eq!(total, 23);
}
