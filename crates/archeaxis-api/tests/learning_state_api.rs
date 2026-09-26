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

async fn get_items(router: &axum::Router) -> (StatusCode, Value) {
    let response = router.clone().oneshot(Request::get("/api/v1/learning/items")
        .body(Body::empty()).unwrap()).await.unwrap();
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

#[tokio::test]
async fn learning_items_returns_one_latest_deadline_per_item() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    assert_eq!(get_items(&router).await.0, StatusCode::OK);
    assert_eq!(post(&router, request("first", "2026-09-02T00:00:00+00:00"), "human").await.0,
               StatusCode::CREATED);
    let (status, value) = get_items(&router).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["count"], 1);
    assert_eq!(value["items"][0]["item_key"], "restart-card");
    assert_eq!(value["items"][0]["next_review"], "2026-09-02T00:10:00+00:00");
}

#[tokio::test]
async fn learning_items_includes_referenced_cards_before_the_first_review() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let initial = get_items(&router).await;
    assert_eq!(initial.0, StatusCode::OK);
    assert_eq!(initial.1["count"], 0);

    let response = router.clone().oneshot(
        Request::post("/api/v1/knowledge-items")
            .header("content-type", "application/json")
            .body(Body::from(json!({
                "knowledge_type": "PERSONAL_DEFINITION",
                "body": "A first-use personal learning item.",
                "status": "candidate",
                "created_by": "human"
            }).to_string())).unwrap(),
    ).await.unwrap();
    assert_eq!(response.status(), StatusCode::CREATED);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let knowledge: Value = serde_json::from_slice(&bytes).unwrap();
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap();

    let reference = router.clone().oneshot(
        Request::post("/api/v1/learning/items/first-use-card/references")
            .header("content-type", "application/json")
            .body(Body::from(json!({"knowledge_id": knowledge_id}).to_string())).unwrap(),
    ).await.unwrap();
    assert_eq!(reference.status(), StatusCode::CREATED);

    let assessment = router.clone().oneshot(
        Request::post("/api/v1/learning/items/first-use-card/assessment")
            .header("content-type", "application/json")
            .body(Body::from(json!({"knowledge_id": knowledge_id}).to_string())).unwrap(),
    ).await.unwrap();
    assert_eq!(assessment.status(), StatusCode::CREATED);

    let (status, queue) = get_items(&router).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(queue["count"], 1);
    assert_eq!(queue["items"][0]["item_key"], "first-use-card");
    assert!(queue["items"][0]["next_review"].is_null());
}

#[tokio::test]
async fn submitted_answer_is_readable_after_core_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let knowledge_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/knowledge-items")
                .header("content-type", "application/json")
                .body(Body::from(
                    r#"{"knowledge_type":"FACTUAL_CLAIM","body":"FSRS schedules a next review from review history.","status":"accepted","created_by":"owner"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(knowledge_response.status(), StatusCode::CREATED);
    let bytes = knowledge_response.into_body().collect().await.unwrap().to_bytes();
    let knowledge: Value = serde_json::from_slice(&bytes).unwrap();
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap();

    let reference_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/restart-card/references")
                .header("content-type", "application/json")
                .body(Body::from(json!({"knowledge_id": knowledge_id}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(reference_response.status(), StatusCode::CREATED);

    let assessment_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/restart-card/assessment")
                .header("content-type", "application/json")
                .body(Body::from(json!({"knowledge_id": knowledge_id}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(assessment_response.status(), StatusCode::CREATED);
    let bytes = assessment_response.into_body().collect().await.unwrap().to_bytes();
    let assessment: Value = serde_json::from_slice(&bytes).unwrap();

    let mut body = request("answer-1", "2026-09-02T00:00:00+00:00");
    body["answer"] = json!("用自己的话说明 FSRS 如何安排下一次复习");
    body["assessment_id"] = assessment["assessment_id"].clone();
    body["knowledge_version"] = assessment["knowledge_version"].clone();
    let (status, value) = post(&router, body, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{value}");

    // Reopen the same workspace and read the persisted learning receipt.
    drop(router);
    let reopened = app(db.to_str().unwrap()).unwrap();
    let response = reopened
        .clone()
        .oneshot(
            Request::get("/api/v1/learning/events/restart-card")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let history: Value = serde_json::from_slice(&bytes).unwrap();
    let outcome: Value = serde_json::from_str(history["events"][0]["outcome"].as_str().unwrap()).unwrap();
    assert_eq!(outcome["answer"], "用自己的话说明 FSRS 如何安排下一次复习");
}

#[tokio::test]
async fn core_creates_and_reads_back_assessment_bound_to_accepted_knowledge() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();

    let knowledge_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/knowledge-items")
                .header("content-type", "application/json")
                .body(Body::from(
                    r#"{"knowledge_type":"FACTUAL_CLAIM","body":"FSRS schedules a next review from review history.","status":"accepted","created_by":"owner"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(knowledge_response.status(), StatusCode::CREATED);
    let bytes = knowledge_response.into_body().collect().await.unwrap().to_bytes();
    let knowledge: Value = serde_json::from_slice(&bytes).unwrap();
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap();

    let reference_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/card-assessment/references")
                .header("content-type", "application/json")
                .body(Body::from(json!({"knowledge_id": knowledge_id}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(reference_response.status(), StatusCode::CREATED);

    let assessment_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/card-assessment/assessment")
                .header("content-type", "application/json")
                .body(Body::from(json!({"knowledge_id": knowledge_id}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(assessment_response.status(), StatusCode::CREATED);
    let bytes = assessment_response.into_body().collect().await.unwrap().to_bytes();
    let assessment: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(assessment["item_key"], "card-assessment");
    assert_eq!(assessment["knowledge_id"], knowledge_id);
    assert!(assessment["question"].as_str().unwrap().contains("请回答"));
    assert_eq!(assessment["content"], "FSRS schedules a next review from review history.");
    assert!(assessment["source_id"].is_null());
    assert!(assessment["anchor_id"].is_null());

    let mut review = request("assessment-review", "2026-09-02T00:00:00+00:00");
    review["item_key"] = json!("card-assessment");
    review["assessment_id"] = assessment["assessment_id"].clone();
    review["knowledge_version"] = assessment["knowledge_version"].clone();
    review["answer"] = json!("FSRS uses the prior review history.");
    let replay_body = review.clone();
    let (review_status, review_response) = post(&router, review, "human").await;
    assert_eq!(review_status, StatusCode::CREATED, "{review_response}");
    assert_eq!(review_response["answer"], "FSRS uses the prior review history.");
    assert_eq!(review_response["mastery_projection"]["status"], "projection");
    assert_eq!(review_response["mastery_projection"]["closed"], false);
    let (replay_status, replay_response) = post(&router, replay_body, "human").await;
    assert_eq!(replay_status, StatusCode::OK, "{replay_response}");
    assert_eq!(replay_response["answer"], review_response["answer"]);
    assert_eq!(replay_response["mastery_projection"], review_response["mastery_projection"]);

    drop(router);
    let reopened = app(db.to_str().unwrap()).unwrap();
    let response = reopened
        .clone()
        .oneshot(
            Request::get("/api/v1/learning/items/card-assessment/assessment")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let readback: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(readback, assessment);
}
