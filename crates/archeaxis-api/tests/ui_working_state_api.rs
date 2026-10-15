use archeaxis_api::router;
use archeaxis_store_sqlite::writer::Store;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
const ROUTE: &str = "/api/v1/workspace/ui-state";
#[tokio::test]
async fn human_release_preserves_frozen_body_and_retires_late_create_through_existing_write_route()
{
    let dir = tempfile::tempdir().unwrap();
    let app = router(Store::open(&dir.path().join("release.sqlite")).unwrap());
    let (_, initial) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    let record = json!({"schema":"archeaxis.teaching-record/v2","record_id":"frozen_refused","kind":"observation","knowledge_id":"synthetic","knowledge_version":"synthetic","course_id":null,"parent_id":null,"purpose":"purpose","scope":"personal","privacy":"local_only","content":"preserved body","feedback_class":null,"assessment_id":null,"rubric_version":null,"assisted":false,"producer_kind":"human_authored"});
    let entry = json!({"page_id":"08","context_item_key":null,"form":{"kind":"observation","purpose":"purpose","content":"preserved body","scope":"personal","privacy":"local_only","assisted":false,"feedback_class":null,"rubric_version":"","producer_kind":"human_authored"},"knowledge_id":"synthetic","course_id":null,"item_key":null,"assessment_id":null,"parent":null,"preparation":null,"saved_preparation":"","pending_record":record});
    let mut write = json!({"workspace_id":initial["workspace_id"],"restore_epoch":initial["restore_epoch"],"state_revision":0,"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"08","teaching_drafts":{"08:":entry}}});
    let (status, staged) = call(&app, "PUT", ROUTE, write.clone(), "human").await;
    assert_eq!(status, 200, "{staged}");
    write["state_revision"] = staged["state_revision"].clone();
    write["state"]["teaching_drafts"]["08:"]["pending_record"] = Value::Null;
    assert_eq!(
        call(&app, "PUT", ROUTE, write.clone(), "human").await.0,
        422,
        "normal write cannot silently unfreeze"
    );
    write["release_teaching"] = json!({"draft_key":"08:","record_id":"frozen_refused"});
    assert_eq!(
        call(&app, "PUT", ROUTE, write.clone(), "machine").await.0,
        403
    );
    let (status, released) = call(&app, "PUT", ROUTE, write, "human").await;
    assert_eq!(status, 200, "{released}");
    assert_eq!(
        released["state"]["teaching_drafts"]["08:"]["form"],
        entry["form"]
    );
    assert!(released["state"]["teaching_drafts"]["08:"]["pending_record"].is_null());
    let (status, late) = call(&app, "POST", "/api/v2/teaching/records", record, "human").await;
    assert_eq!(status, 409, "{late}");
    assert!(late.to_string().contains("retired"));
}
#[tokio::test]
async fn frozen_preparation_survives_reopen_and_requires_exact_current_document_before_clear() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("preparation.sqlite");
    let app = router(Store::open(&path).unwrap());
    let (_, initial) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    let editor = json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"frozen"},"content":[{"type":"text","text":"original"}]}]});
    let attempt = json!({"operation":"document_create","payload":{"body":{"create_request_id":"stable_preparation","title":"purpose","editor_json":editor}},"snapshot":"{\"purpose\":\"purpose\",\"content\":\"original\"}","persistedPurpose":"purpose","expectedTitle":"purpose"});
    let entry = json!({"page_id":"12","context_item_key":null,"form":{"kind":"feedback","purpose":"purpose","content":"original","scope":"personal","privacy":"local_only","assisted":false,"feedback_class":null,"rubric_version":"","producer_kind":"human_authored"},"knowledge_id":null,"course_id":null,"item_key":null,"assessment_id":null,"parent":null,"preparation":null,"saved_preparation":"","pending_record":null,"preparation_attempt":attempt});
    let mut write = json!({"workspace_id":initial["workspace_id"],"restore_epoch":initial["restore_epoch"],"state_revision":0,"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"12","teaching_drafts":{"12:":entry}}});
    let (status, saved) = call(&app, "PUT", ROUTE, write.clone(), "human").await;
    assert_eq!(status, 200, "{saved}");
    drop(app);
    let app = router(Store::open(&path).unwrap());
    assert_eq!(
        call(&app, "GET", ROUTE, Value::Null, "human").await.1,
        saved
    );
    write["state_revision"] = saved["state_revision"].clone();
    let mut clear = write.clone();
    clear["state"]
        .as_object_mut()
        .unwrap()
        .remove("teaching_drafts");
    assert_ne!(
        call(&app, "PUT", ROUTE, clear.clone(), "human").await.0,
        200,
        "no forged clearance before document save"
    );
    let mut replace = write.clone();
    replace["state"]["teaching_drafts"]["12:"]["preparation_attempt"]["payload"]["body"]["create_request_id"] =
        json!("replacement");
    assert_ne!(call(&app, "PUT", ROUTE, replace, "human").await.0, 200);
    let (_, doc) = call(
        &app,
        "POST",
        "/api/v1/documents",
        attempt["payload"]["body"].clone(),
        "human",
    )
    .await;
    let (status, duplicate) = call(
        &app,
        "POST",
        "/api/v1/documents",
        attempt["payload"]["body"].clone(),
        "human",
    )
    .await;
    assert!(status == 200 || status == 201, "{duplicate}");
    assert_eq!(duplicate["document_id"], doc["document_id"]);
    // A newer form is independent of the frozen dispatched body.
    write["state"]["teaching_drafts"]["12:"]["form"]["content"] = json!("later input");
    let (status, newer) = call(&app, "PUT", ROUTE, write.clone(), "human").await;
    assert_eq!(status, 200, "{newer}");
    write["state_revision"] = newer["state_revision"].clone();
    write["state"]["teaching_drafts"]["12:"]
        .as_object_mut()
        .unwrap()
        .remove("preparation_attempt");
    write["state"]["teaching_drafts"]["12:"]["preparation"] =
        json!({"document_id":doc["document_id"],"version":1,"title":"purpose"});
    write["state"]["teaching_drafts"]["12:"]["saved_preparation"] = attempt["snapshot"].clone();
    let conn = rusqlite::Connection::open(&path).unwrap();
    conn.execute("UPDATE document_versions SET content_sha256='wrong'", [])
        .unwrap();
    assert_ne!(
        call(&app, "PUT", ROUTE, write.clone(), "human").await.0,
        200,
        "actual stored integrity is checked"
    );
    conn.execute(
        "UPDATE document_versions SET content_sha256=?1",
        [doc["content_sha256"].as_str().unwrap()],
    )
    .unwrap();
    let (status, finished) = call(&app, "PUT", ROUTE, write, "human").await;
    assert_eq!(status, 200, "{finished}");
    assert_eq!(
        finished["state"]["teaching_drafts"]["12:"]["form"]["content"],
        "later input"
    );
    assert!(
        finished["state"]["teaching_drafts"]["12:"]
            .get("preparation_attempt")
            .is_none()
    );
    assert_eq!(
        conn.query_row("SELECT count(*) FROM documents", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        1
    );
}
#[tokio::test]
async fn unbound_teaching_text_survives_core_store_reopen_without_publishing_a_record() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("teaching-drafts.sqlite");
    let store = Store::open(&path).unwrap();
    let app = router(store.clone());
    let (_, initial) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    let draft = json!({"page_id":"12","context_item_key":null,"form":{"kind":"feedback","purpose":"未提交总结","content":"  反馈正文\n保持原文  ","scope":"personal","privacy":"local_only","assisted":false,"feedback_class":"mastery","rubric_version":"","producer_kind":"human_authored"},"knowledge_id":null,"course_id":null,"item_key":null,"assessment_id":null,"parent":null,"preparation":null,"saved_preparation":"","pending_record":null});
    let body = json!({"workspace_id":initial["workspace_id"],"restore_epoch":initial["restore_epoch"],"state_revision":initial["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"12","teaching_drafts":{"12:":draft}}});
    assert_eq!(
        call(&app, "PUT", ROUTE, body.clone(), "machine").await.0,
        403
    );
    let (status, saved) = call(&app, "PUT", ROUTE, body, "human").await;
    assert_eq!(status, 200, "{saved}");
    drop(app);
    drop(store);
    let app = router(Store::open(&path).unwrap());
    assert_eq!(
        call(&app, "GET", ROUTE, Value::Null, "human").await.1,
        saved
    );
    let conn = rusqlite::Connection::open(&path).unwrap();
    assert_eq!(
        conn.query_row("SELECT count(*) FROM teaching_records", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
}
async fn call(
    router: &Router,
    method: &str,
    route: &str,
    body: Value,
    actor: &str,
) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(route)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
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
async fn human_ui_state_survives_reopen_but_machine_cannot_read_or_replace_it() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("db.sqlite");
    let store = Store::open(&db).unwrap();
    let app = router(store.clone());
    let (status,doc)=call(&app,"POST","/api/v1/documents",json!({"title":"owned note","editor_json":{"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"stable"},"content":[{"type":"text","text":"committed"}]}]}}),"human").await;
    assert_eq!(status, 201, "{doc}");
    let id = doc["document_id"].as_str().unwrap();
    let (status, initial) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    assert_eq!(status, 200, "{initial}");
    let state = json!({"drafts":{(id):{"base_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"private 中文 draft"}]}]}}},"opened_documents":[id],"active_document":id,"page_id":"03"});
    let body = json!({"workspace_id":initial["workspace_id"],"restore_epoch":initial["restore_epoch"],"state_revision":initial["state_revision"],"state":state});
    assert_eq!(
        call(&app, "GET", ROUTE, Value::Null, "machine").await.0,
        403
    );
    assert_eq!(
        call(&app, "PUT", ROUTE, body.clone(), "machine").await.0,
        403
    );
    let (status, saved) = call(&app, "PUT", ROUTE, body.clone(), "human").await;
    assert_eq!(status, 200, "{saved}");
    let (status, conflict) = call(&app, "PUT", ROUTE, body, "human").await;
    assert_eq!(status, 409, "{conflict}");
    assert!(conflict.get("state").is_none());
    assert!(conflict.get("drafts").is_none());
    assert_eq!(conflict["state_revision"], saved["state_revision"]);
    let (status, read) = call(
        &app,
        "GET",
        &format!("/api/v1/documents/{id}"),
        Value::Null,
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(
        read["version"], 1,
        "UI draft does not commit Document content"
    );
    drop(app);
    drop(store);
    let store = Store::open(&db).unwrap();
    let app = router(store);
    let (status, reopened) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    assert_eq!(status, 200);
    assert_eq!(reopened, saved);
}
#[tokio::test]
async fn extra_fields_and_machine_recovery_are_rejected() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("db.sqlite")).unwrap();
    let app = router(store);
    let (_, initial) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    let mut body = json!({"workspace_id":initial["workspace_id"],"restore_epoch":initial["restore_epoch"],"state_revision":0,"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":null}});
    body["endpoint"] = json!("https://example.com");
    assert_eq!(call(&app, "PUT", ROUTE, body, "human").await.0, 422);
    let recovery = json!({"workspace_id":initial["workspace_id"],"restore_epoch":initial["restore_epoch"],"state_revision":0,"action":"discard"});
    assert_eq!(
        call(
            &app,
            "POST",
            &format!("{ROUTE}/recover"),
            recovery,
            "machine"
        )
        .await
        .0,
        403
    );
}

#[tokio::test]
async fn clear_saved_verifies_the_committed_document_before_removing_only_that_draft() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("db.sqlite")).unwrap();
    let app = router(store);
    let content = json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"stable"},"content":[{"type":"text","text":"pending"}]}]});
    let (_, doc) = call(
        &app,
        "POST",
        "/api/v1/documents",
        json!({"title":"test","editor_json":content}),
        "human",
    )
    .await;
    let id = doc["document_id"].as_str().unwrap();
    let (_, initial) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    let (_,saved)=call(&app,"PUT",ROUTE,json!({"workspace_id":initial["workspace_id"],"restore_epoch":initial["restore_epoch"],"state_revision":0,"state":{"drafts":{(id):{"base_version":1,"editor_json":content}},"opened_documents":[id],"active_document":id,"page_id":"03"}}),"human").await;
    let clear = json!({"workspace_id":saved["workspace_id"],"restore_epoch":saved["restore_epoch"],"state_revision":saved["state_revision"],"document_id":id,"base_version":1,"content_sha256":saved["draft_digests"][id],"saved_version":2});
    let route = format!("{ROUTE}/clear-saved");
    assert_eq!(
        call(&app, "POST", &route, clear.clone(), "human").await.0,
        409,
        "UI cannot forge a Document ACK"
    );
    let (status, version) = call(
        &app,
        "PUT",
        &format!("/api/v1/documents/{id}/draft"),
        json!({"expected_version":1,"editor_json":content}),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{version}");
    assert_eq!(
        call(&app, "POST", &route, clear.clone(), "machine").await.0,
        403
    );
    let (status, cleared) = call(&app, "POST", &route, clear, "human").await;
    assert_eq!(status, 200, "{cleared}");
    assert_eq!(cleared["state"]["drafts"], json!({}));
    assert_eq!(cleared["state"]["opened_documents"], json!([id]));
}
