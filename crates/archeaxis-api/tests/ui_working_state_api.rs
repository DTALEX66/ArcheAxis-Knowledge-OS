use archeaxis_api::router;
use archeaxis_store_sqlite::writer::Store;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
const ROUTE: &str = "/api/v1/workspace/ui-state";
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
