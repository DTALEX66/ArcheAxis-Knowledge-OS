//! Real Store/SQLite/HTTP contracts; synthetic metadata, no model or desktop Host.
use archeaxis_api::router;
use archeaxis_domain::{failure_log, ui_state};
use archeaxis_store_sqlite::{authorization_fence, writer::Store};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
const ROOT: &str = "/api/v1/workspace/operation-failures/";
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
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or_else(|_| json!({"rejected":true})),
    )
}
async fn log(app: &Router, action: &str, body: Value) -> (u16, Value) {
    call(app, "POST", &format!("{ROOT}{action}"), body, "human").await
}
fn scope(state: &Value) -> Value {
    json!({"workspace_id":state["workspace_id"],"restore_epoch":state["restore_epoch"]})
}
fn event(state: &Value) -> Value {
    json!({"workspace_id":state["workspace_id"],"restore_epoch":state["restore_epoch"],"log_generation":state["log_generation"],"operation":"document_get","status":404,"code":"unavailable","reason":"missing"})
}
async fn initial(app: &Router) -> Value {
    let (s, v) = call(
        app,
        "GET",
        "/api/v1/workspace/ui-state",
        Value::Null,
        "human",
    )
    .await;
    assert_eq!(s, 200, "{v}");
    v
}
#[tokio::test]
async fn real_store_reopen_preserves_only_bounded_metadata_without_touching_near_budget_drafts() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let store = Store::open(&path).unwrap();
    let app = router(store.clone());
    let state = initial(&app).await;
    let mut drafts = serde_json::Map::new();
    for i in 0..4 {
        let (created,document)=call(&app,"POST","/api/v1/documents",json!({"title":format!("Synthetic draft {i}"),"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Small owned baseline"}]}]}}),"human").await;
        assert!((200..300).contains(&created), "{document}");
        let editor = json!({"type":"doc","content":[{"type":"text","text":"PRIVATE_DRAFT_SENTINEL".repeat(11_000)}]});
        assert!(serde_json::to_vec(&editor).unwrap().len() <= 262_144);
        drafts.insert(
            document["document_id"].as_str().unwrap().into(),
            json!({"base_version":document["version"],"editor_json":editor}),
        );
    }
    let body = json!({"workspace_id":state["workspace_id"],"restore_epoch":state["restore_epoch"],"state_revision":state["state_revision"],"state":{"drafts":drafts,"opened_documents":[],"active_document":null,"page_id":"02"}});
    let draft_bytes = serde_json::to_vec(&body["state"]).unwrap().len();
    assert!((900_000..=1_048_576).contains(&draft_bytes));
    let (status, saved) = call(&app, "PUT", "/api/v1/workspace/ui-state", body, "human").await;
    assert_eq!(status, 200, "{saved}");
    let (_, history) = log(&app, "read", scope(&state)).await;
    for status in 1..=55 {
        let mut request = event(&history);
        request["status"] = json!(status);
        assert_eq!(log(&app, "append", request).await.0, 200);
    }
    let (_, history) = log(&app, "read", scope(&state)).await;
    assert_eq!(history["entries"].as_array().unwrap().len(), 50);
    assert!(!history.to_string().contains("PRIVATE_DRAFT_SENTINEL"));
    assert_eq!(
        initial(&app).await,
        saved,
        "logging must not consume draft CAS revision, bytes or recovery candidates"
    );
    drop(app);
    store.close().await.unwrap();
    let store = Store::open(&path).unwrap();
    let app = router(store.clone());
    assert_eq!(log(&app, "read", scope(&state)).await.1, history);
    assert_eq!(initial(&app).await, saved);
    drop(app);
    store.close().await.unwrap();
}
#[tokio::test]
async fn queued_old_scope_and_clear_generation_requests_are_rejected_without_any_log_write() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("workspace.sqlite")).unwrap();
    let app = router(store.clone());
    let state = initial(&app).await;
    let (_, history) = log(&app, "read", scope(&state)).await;
    let old = event(&history);
    assert_eq!(log(&app, "append", old.clone()).await.0, 200);
    let mut wrong = old.clone();
    wrong["workspace_id"] = json!("b".repeat(32));
    assert_eq!(log(&app, "append", wrong).await.0, 409);
    let clear = json!({"workspace_id":state["workspace_id"],"restore_epoch":state["restore_epoch"],"log_generation":history["log_generation"]});
    let (status, cleared) = log(&app, "clear", clear.clone()).await;
    assert_eq!(status, 200);
    assert_ne!(cleared["log_generation"], history["log_generation"]);
    assert_eq!(
        log(&app, "append", old.clone()).await.0,
        409,
        "append sent before clear cannot repopulate it"
    );
    assert_eq!(
        log(&app, "clear", clear).await.0,
        409,
        "late old clear cannot wipe the new generation"
    );
    assert_eq!(log(&app, "read", scope(&state)).await.1, cleared);
    let before = store
        .submit(|conn| {
            conn.query_row(
                "SELECT value FROM workspace_meta WHERE key=?1",
                [failure_log::KEY],
                |r| r.get::<_, String>(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    store
        .submit(|conn| {
            let tx = conn.transaction().unwrap();
            authorization_fence::install_after_restore(&tx).unwrap();
            tx.commit().unwrap();
        })
        .await
        .unwrap();
    assert_eq!(
        log(&app, "append", event(&cleared)).await.0,
        409,
        "server, not just UI, checks the restored epoch"
    );
    assert_eq!(log(&app,"clear",json!({"workspace_id":state["workspace_id"],"restore_epoch":"initial","log_generation":cleared["log_generation"]})).await.0,409);
    let after = store
        .submit(|conn| {
            conn.query_row(
                "SELECT value FROM workspace_meta WHERE key=?1",
                [failure_log::KEY],
                |r| r.get::<_, String>(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    assert_eq!(before, after);
    drop(app);
    store.close().await.unwrap();
}
#[tokio::test]
async fn strict_enums_unknown_field_refusal_corruption_repair_and_human_boundary() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("workspace.sqlite")).unwrap();
    let app = router(store.clone());
    let state = initial(&app).await;
    let (_, history) = log(&app, "read", scope(&state)).await;
    for field in [
        "summary", "message", "stack", "body", "endpoint", "token", "at", "count",
    ] {
        let mut body = event(&history);
        body[field] = json!("PRIVATE_SENTINEL https://secret.invalid/?token=secret");
        assert_eq!(log(&app, "append", body).await.0, 422);
    }
    for (field, value) in [
        ("operation", json!("private_document_title")),
        ("code", json!("private_error")),
        ("reason", json!("PRIVATE_SENTINEL")),
        ("status", json!(600)),
    ] {
        let mut body = event(&history);
        body[field] = value;
        assert_eq!(log(&app, "append", body).await.0, 422);
    }
    assert_eq!(
        call(
            &app,
            "POST",
            &format!("{ROOT}append"),
            event(&history),
            "machine"
        )
        .await
        .0,
        403
    );
    let (_, one) = log(&app, "append", event(&history)).await;
    let (_, two) = log(&app, "append", event(&history)).await;
    assert_eq!(one["entries"][0]["entry_id"], two["entries"][0]["entry_id"]);
    assert_eq!(two["entries"][0]["count"], 2);
    let original: String = store
        .submit(|conn| {
            conn.query_row(
                "SELECT value FROM workspace_meta WHERE key=?1",
                [failure_log::KEY],
                |r| r.get(0),
            )
            .unwrap()
        })
        .await
        .unwrap();
    // Valid JSON with unchanged log semantics, but beyond the persisted byte budget.
    let oversized = format!("{original}{}", " ".repeat(65_537));
    assert!(serde_json::from_str::<Value>(&oversized).is_ok());
    for invalid in ["PRIVATE_CORRUPT_SENTINEL".to_owned(), oversized] {
        store
            .submit(move |conn| {
                conn.execute(
                    "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                    rusqlite::params![invalid, failure_log::KEY],
                )
                .unwrap()
            })
            .await
            .unwrap();
        let (status, corrupt) = log(&app, "read", scope(&state)).await;
        assert_eq!(status, 200);
        assert_eq!(corrupt["corrupt"], true);
        assert!(!corrupt.to_string().contains("PRIVATE_"));
        assert_eq!(initial(&app).await, state);
        let (_,repaired)=log(&app,"clear",json!({"workspace_id":state["workspace_id"],"restore_epoch":state["restore_epoch"],"log_generation":null})).await;
        assert_eq!(repaired["corrupt"], false);
        assert_eq!(repaired["entries"], json!([]));
    }
    let identity = store
        .submit(|conn| ui_state::read(conn).unwrap())
        .await
        .unwrap();
    assert_eq!(identity, state);
    drop(app);
    store.close().await.unwrap();
}
