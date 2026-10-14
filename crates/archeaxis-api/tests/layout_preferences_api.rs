use archeaxis_api::router;
use archeaxis_store_sqlite::writer::Store;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;
const ROUTE: &str = "/api/v1/workspace/layout?device_id=desktop";
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
async fn layout_commands_are_human_only_cas_bound_and_device_local() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let store = Store::open(&db).unwrap();
    let app = router(store.clone());
    let (status, first) = call(&app, "GET", ROUTE, Value::Null, "human").await;
    assert_eq!(status, 200, "{first}");
    let body = json!({"workspace_id":first["workspace_id"],"device_id":first["device_id"],"restore_epoch":first["restore_epoch"],"expected_revision":first["revision"],"layout":first["layout"]});
    assert_eq!(
        call(&app, "GET", ROUTE, Value::Null, "machine").await.0,
        403
    );
    assert_eq!(
        call(
            &app,
            "PUT",
            "/api/v1/workspace/layout",
            body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    let (status, saved) = call(
        &app,
        "PUT",
        "/api/v1/workspace/layout",
        body.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{saved}");
    assert_eq!(saved["revision"], 1);
    let (status, conflict) = call(&app, "PUT", "/api/v1/workspace/layout", body, "human").await;
    assert_eq!(status, 409);
    assert!(conflict.get("layout").is_none());
    let (_, other) = call(
        &app,
        "GET",
        "/api/v1/workspace/layout?device_id=other",
        Value::Null,
        "human",
    )
    .await;
    assert_eq!(other["revision"], 0);
    assert_eq!(
        call(
            &app,
            "GET",
            "/api/v1/workspace/layout?device_id=desktop&extra=1",
            Value::Null,
            "human"
        )
        .await
        .0,
        400
    );
    drop(app);
    drop(store);
    let app = router(Store::open(&db).unwrap());
    assert_eq!(
        call(&app, "GET", ROUTE, Value::Null, "human").await.1,
        saved
    );
}
