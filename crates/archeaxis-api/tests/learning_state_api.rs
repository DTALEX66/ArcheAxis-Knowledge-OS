use archeaxis_api::app;
use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

async fn post(router: &axum::Router, value: Value, actor: &str) -> (StatusCode, Value) {
    let response = router.clone().oneshot(Request::post("/api/v1/learning/reviews")
        .header("content-type", "application/json").header("x-archeaxis-actor", actor)
        .body(Body::from(value.to_string())).unwrap()).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}

fn request(key: &str, instant: &str) -> Value {
    json!({"item_key":"restart-card", "client_event_id":key, "correct":true,
           "rating":3, "now":instant})
}

#[tokio::test]
async fn core_persists_real_worker_state_and_continues_after_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let first_request = request("first", "2026-09-02T00:00:00+00:00");
    let first = {
        let router = app(db.to_str().unwrap()).unwrap();
        let (status, value) = post(&router, first_request.clone(), "human").await;
        assert_eq!(status, StatusCode::CREATED, "{value}");
        assert_eq!(value["schedule_authority"], "fsrs");
        assert_eq!(value["schedule_state"]["step"], 1);
        assert_eq!(value["next_review"], "2026-09-02T00:10:00+00:00");
        value
    };
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, second) = post(&router, request("second", "2026-09-02T00:10:00+00:00"), "human").await;
    assert_eq!(status, StatusCode::CREATED, "{second}");
    assert_eq!(second["schedule_state"]["state"], "review");
    assert_eq!(second["next_review"], "2026-09-04T00:10:00+00:00");
    assert_eq!(second["streak_after"], 2);
    let (status, replay) = post(&router, first_request, "human").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(replay["event_id"], first["event_id"]);
    assert_eq!(replay["schedule_state"], first["schedule_state"]);
    assert_eq!(replay["next_review"], first["next_review"]);
    let (status, _) = post(&router, request("first", "2026-09-03T00:00:00+00:00"), "human").await;
    assert_eq!(status, StatusCode::CONFLICT);
    let conn = rusqlite::Connection::open(&db).unwrap();
    let count: i64 = conn.query_row("SELECT count(*) FROM learning_events", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 2);
}

#[tokio::test]
async fn machine_and_client_supplied_schedule_cannot_write_human_state() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let body = request("key", "2026-09-02T00:00:00+00:00");
    assert_eq!(post(&router, body.clone(), "machine").await.0, StatusCode::FORBIDDEN);
    let mut injected = body.clone();
    injected["schedule_state"] = json!({"stability":999});
    assert_eq!(post(&router, injected, "human").await.0, StatusCode::UNPROCESSABLE_ENTITY);
    let mut invalid = body;
    invalid["now"] = json!("12:00");
    assert_eq!(post(&router, invalid, "human").await.0, StatusCode::BAD_REQUEST);
    let conn = rusqlite::Connection::open(&db).unwrap();
    let count: i64 = conn.query_row("SELECT count(*) FROM learning_events", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
}
