use archeaxis_api::app;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use tower::ServiceExt;

async fn post(router: &axum::Router, value: Value, actor: &str) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/reviews")
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(value.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn get_items(router: &axum::Router) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::get("/api/v1/learning/items")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn get_path(router: &axum::Router, path: &str) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(Request::get(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

fn assessment_revision_fixture(
    db: &std::path::Path,
) -> (
    archeaxis_domain::learning::AssessmentRecord,
    archeaxis_domain::learning::AssessmentRecord,
) {
    use archeaxis_domain::{knowledge, learning};
    let item = "assessment-tie-1";
    {
        let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        let old_id = knowledge::create_knowledge(
            &mut conn,
            "FACTUAL_CLAIM",
            "Synthetic original fact",
            "accepted",
            None,
            None,
            "fixture",
        )
        .unwrap();
        learning::record_card_reference(&mut conn, item, &old_id, None).unwrap();
        let old = learning::create_assessment(&mut conn, item, &old_id).unwrap();
        learning::record_review_with_state_and_answer(&mut conn, item, "review", true,
            "synthetic-old-review", "synthetic", Some("synthetic answer"), Some(&old.assessment_id), None,
            |_| Ok(learning::ReviewSchedule {
                schedule_json: r#"{"authority":"fsrs","state":{"state":"review","step":null,"stability":30.0,"difficulty":3.0,"last_review":"2026-09-02T00:00:00+00:00","due":"2026-10-02T00:00:00+00:00"}}"#.into(),
                next_review: Some("2026-10-02T00:00:00+00:00".into()), next_review_days: 30,
            })).unwrap();
        let new_id = knowledge::review(
            &mut conn,
            &old_id,
            "modified",
            "fixture",
            None,
            Some("Synthetic revised fact"),
        )
        .unwrap();
        knowledge::review(&mut conn, &new_id, "accepted", "fixture", None, None).unwrap();
        learning::record_card_reference(&mut conn, item, &new_id, None).unwrap();
        let revised = learning::create_assessment(&mut conn, item, &new_id).unwrap();
        assert!(old.assessment_id > revised.assessment_id);
        conn.execute(
            "UPDATE learning_assessments SET created_at='2026-11-09 00:00:00' WHERE item_key=?1",
            [item],
        )
        .unwrap();
        (old, revised)
    }
}

#[tokio::test]
async fn assessment_and_learning_state_keep_newest_snapshot_and_old_review_separate() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assessment-order-api.sqlite");
    let item = "assessment-tie-1";
    let (old, revised) = assessment_revision_fixture(&db);
    for _ in 0..2 {
        let router = app(db.to_str().unwrap()).unwrap();
        let (status, assessment) = get_path(
            &router,
            &format!("/api/v1/learning/items/{item}/assessment"),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(assessment["assessment_id"], revised.assessment_id);
        assert_eq!(assessment["knowledge_id"], revised.knowledge_id);
        assert_eq!(assessment["knowledge_state"]["currentness"], "current");
        let (status, state) =
            get_path(&router, &format!("/api/v1/learning/items/{item}/state")).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            state["learner"]["assessment"]["assessment_id"],
            revised.assessment_id
        );
        assert_eq!(
            state["learner"]["latest_review"]["assessment_id"],
            old.assessment_id
        );
        assert_eq!(state["learner"]["event_count"], 1);
    }
}

#[tokio::test]
async fn revised_assessment_starts_its_own_review_history_and_schedule() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assessment-review-isolation.sqlite");
    let (old, revised) = assessment_revision_fixture(&db);
    let router = app(db.to_str().unwrap()).unwrap();
    let body = json!({"item_key":"assessment-tie-1", "client_event_id":"revised-review",
        "correct":true, "rating":3, "now":"2026-10-02T00:00:00+00:00",
        "answer":"synthetic revised answer", "assessment_id":revised.assessment_id,
        "knowledge_version":revised.knowledge_version});
    let (status, response) = post(&router, body.clone(), "human").await;
    assert_eq!(status, StatusCode::CREATED, "{response}");
    assert_eq!(response["schedule_authority"], "fsrs", "{response}");
    assert_eq!(
        response["schedule_state"]["state"], "learning",
        "{response}"
    );
    assert_eq!(response["schedule_state"]["step"], 1, "{response}");
    assert_eq!(
        response["next_review"], "2026-10-02T00:10:00+00:00",
        "{response}"
    );
    assert_eq!(response["streak_after"], 1, "{response}");
    assert_eq!(response["mastery_projection"]["attempts"], 1, "{response}");
    let (_, history) = get_path(&router, "/api/v1/learning/events/assessment-tie-1").await;
    assert_eq!(history["count"], 2);
    let first: Value =
        serde_json::from_str(history["events"][0]["outcome"].as_str().unwrap()).unwrap();
    let second: Value =
        serde_json::from_str(history["events"][1]["outcome"].as_str().unwrap()).unwrap();
    assert_eq!(first["assessment_id"], old.assessment_id);
    assert_eq!(second["assessment_id"], revised.assessment_id);
    let (status, replay) = post(&router, body.clone(), "human").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(replay["event_id"], response["event_id"]);
    assert_eq!(replay["schedule_state"], response["schedule_state"]);
    assert_eq!(replay["mastery_projection"], response["mastery_projection"]);

    let mut next = body.clone();
    next["client_event_id"] = json!("revised-review-next");
    next["now"] = json!("2026-10-02T00:10:00+00:00");
    let (status, continued) = post(&router, next, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{continued}");
    assert_eq!(continued["streak_after"], 2);
    assert_eq!(continued["mastery_projection"]["attempts"], 2);
    assert_eq!(continued["next_review"], "2026-10-04T00:10:00+00:00");

    // A later historical-version review must not replace the new version's
    // deadline or streak, though it remains the newest item-level event.
    let mut historical = body;
    historical["client_event_id"] = json!("old-review-later");
    historical["assessment_id"] = json!(old.assessment_id);
    historical["knowledge_version"] = json!(old.knowledge_version);
    historical["correct"] = json!(false);
    historical["rating"] = json!(1);
    let (status, old_later) = post(&router, historical, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{old_later}");
    let (_, state) = get_path(&router, "/api/v1/learning/items/assessment-tie-1/state").await;
    assert_eq!(
        state["learner"]["latest_review"]["assessment_id"],
        old.assessment_id
    );
    assert_eq!(
        state["learner"]["assessment_progress"]["latest_review"]["event_id"],
        continued["event_id"]
    );
    assert_eq!(state["learner"]["assessment_progress"]["event_count"], 2);
    assert_eq!(state["learner"]["correct_streak"], 2);
    assert_eq!(state["learner"]["next_review"], continued["next_review"]);
    let (_, queue) = get_items(&router).await;
    let entry = queue["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|entry| entry["item_key"] == "assessment-tie-1")
        .unwrap();
    assert_eq!(entry["next_review"], continued["next_review"]);
}

#[tokio::test]
async fn revised_assessment_does_not_display_the_old_assessment_due_or_streak() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("assessment-queue-isolation.sqlite");
    let (old, revised) = assessment_revision_fixture(&db);
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, state) = get_path(&router, "/api/v1/learning/items/assessment-tie-1/state").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(
        state["learner"]["assessment"]["assessment_id"],
        revised.assessment_id
    );
    assert_eq!(state["learner"]["correct_streak"], 0, "{state}");
    assert!(state["learner"]["next_review"].is_null(), "{state}");
    assert_eq!(
        state["learner"]["assessment_progress"]["event_count"], 0,
        "{state}"
    );
    assert!(state["learner"]["assessment_progress"]["latest_review"].is_null());
    // The old review stays visible as historical item activity, with its original identity.
    assert_eq!(
        state["learner"]["latest_review"]["assessment_id"],
        old.assessment_id
    );
    assert_eq!(state["learner"]["event_count"], 1);
    let (_, queue) = get_items(&router).await;
    let entry = queue["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|entry| entry["item_key"] == "assessment-tie-1")
        .unwrap();
    assert!(entry["next_review"].is_null(), "{entry}");
}

fn request(key: &str, instant: &str) -> Value {
    json!({"item_key":"restart-card", "client_event_id":key, "correct":true,
           "rating":3, "now":instant})
}

#[tokio::test]
async fn legacy_review_replays_but_new_unbound_review_cannot_bypass_assessment() {
    use archeaxis_domain::{knowledge, learning};
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy-assessment-boundary.sqlite");
    let first_request = request("legacy-before", "2026-10-01T00:00:00+00:00");
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, first) = post(&router, first_request.clone(), "human").await;
    assert_eq!(status, StatusCode::CREATED, "{first}");
    assert_eq!(first["schedule_authority"], "fsrs");
    drop(router);

    let assessment = {
        let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        let knowledge_id = knowledge::create_knowledge(
            &mut conn,
            "FACTUAL_CLAIM",
            "Synthetic assessed fact",
            "accepted",
            None,
            None,
            "fixture",
        )
        .unwrap();
        learning::record_card_reference(&mut conn, "restart-card", &knowledge_id, None).unwrap();
        learning::create_assessment(&mut conn, "restart-card", &knowledge_id).unwrap()
    };
    let router = app(db.to_str().unwrap()).unwrap();
    let (_, before) = get_path(&router, "/api/v1/learning/items/restart-card/state").await;
    assert_eq!(
        before["learner"]["assessment"]["assessment_id"],
        assessment.assessment_id
    );
    assert_eq!(before["learner"]["event_count"], 1);
    assert!(before["learner"]["next_review"].is_null());

    let (status, replay) = post(&router, first_request.clone(), "human").await;
    assert_eq!(status, StatusCode::OK, "{replay}");
    assert_eq!(replay["event_id"], first["event_id"]);
    assert_eq!(replay["next_review"], first["next_review"]);
    assert_eq!(replay["duplicate"], true);

    let (status, refused) = post(
        &router,
        request("legacy-after", "2026-10-01T00:10:00+00:00"),
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::CONFLICT, "{refused}");
    let (_, after) = get_path(&router, "/api/v1/learning/items/restart-card/state").await;
    assert_eq!(after, before);
    let (_, history) = get_path(&router, "/api/v1/learning/events/restart-card").await;
    assert_eq!(history["count"], 1);

    let mut conflicting = first_request;
    conflicting["rating"] = json!(4);
    assert_eq!(
        post(&router, conflicting, "human").await.0,
        StatusCode::CONFLICT
    );
    // A refusal wrote no key: the caller can attach the assessment and retry
    // the same pending event instead of losing or duplicating the review.
    let mut bound = request("legacy-after", "2026-10-01T00:10:00+00:00");
    bound["assessment_id"] = json!(assessment.assessment_id);
    bound["knowledge_version"] = json!(assessment.knowledge_version);
    let (status, accepted) = post(&router, bound, "human").await;
    assert_eq!(status, StatusCode::CREATED, "{accepted}");
    assert_eq!(accepted["schedule_authority"], "fsrs");
    assert_eq!(accepted["streak_after"], 1);
    assert_eq!(accepted["next_review"], "2026-10-01T00:20:00+00:00");
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
    let (status, second) = post(
        &router,
        request("second", "2026-09-02T00:10:00+00:00"),
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::CREATED, "{second}");
    assert_eq!(second["schedule_state"]["state"], "review");
    assert_eq!(second["next_review"], "2026-09-04T00:10:00+00:00");
    assert_eq!(second["streak_after"], 2);
    let (status, replay) = post(&router, first_request, "human").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(replay["event_id"], first["event_id"]);
    assert_eq!(replay["schedule_state"], first["schedule_state"]);
    assert_eq!(replay["next_review"], first["next_review"]);
    let (status, _) = post(
        &router,
        request("first", "2026-09-03T00:00:00+00:00"),
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::CONFLICT);
    let conn = rusqlite::Connection::open(&db).unwrap();
    let count: i64 = conn
        .query_row("SELECT count(*) FROM learning_events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 2);
}

#[tokio::test]
async fn machine_and_client_supplied_schedule_cannot_write_human_state() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let body = request("key", "2026-09-02T00:00:00+00:00");
    assert_eq!(
        post(&router, body.clone(), "machine").await.0,
        StatusCode::FORBIDDEN
    );
    let mut injected = body.clone();
    injected["schedule_state"] = json!({"stability":999});
    assert_eq!(
        post(&router, injected, "human").await.0,
        StatusCode::UNPROCESSABLE_ENTITY
    );
    let mut invalid = body;
    invalid["now"] = json!("12:00");
    assert_eq!(
        post(&router, invalid, "human").await.0,
        StatusCode::BAD_REQUEST
    );
    let conn = rusqlite::Connection::open(&db).unwrap();
    let count: i64 = conn
        .query_row("SELECT count(*) FROM learning_events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 0);
}

#[tokio::test]
async fn learning_items_returns_one_latest_deadline_per_item() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    assert_eq!(get_items(&router).await.0, StatusCode::OK);
    assert_eq!(
        post(
            &router,
            request("first", "2026-09-02T00:00:00+00:00"),
            "human"
        )
        .await
        .0,
        StatusCode::CREATED
    );
    let (status, value) = get_items(&router).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(value["count"], 1);
    assert_eq!(value["items"][0]["item_key"], "restart-card");
    assert_eq!(
        value["items"][0]["next_review"],
        "2026-09-02T00:10:00+00:00"
    );
}

#[tokio::test]
async fn learning_items_includes_referenced_cards_before_the_first_review() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("learning.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let initial = get_items(&router).await;
    assert_eq!(initial.0, StatusCode::OK);
    assert_eq!(initial.1["count"], 0);

    let response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/knowledge-items")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "knowledge_type": "PERSONAL_DEFINITION",
                        "body": "A first-use personal learning item.",
                        "status": "candidate",
                        "created_by": "human"
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::CREATED);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let knowledge: Value = serde_json::from_slice(&bytes).unwrap();
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap();

    let reference = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/first-use-card/references")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"knowledge_id": knowledge_id}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(reference.status(), StatusCode::CREATED);

    let assessment = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/first-use-card/assessment")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"knowledge_id": knowledge_id}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
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
    let bytes = knowledge_response
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes();
    let knowledge: Value = serde_json::from_slice(&bytes).unwrap();
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap();

    let reference_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/restart-card/references")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"knowledge_id": knowledge_id}).to_string(),
                ))
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
                .body(Body::from(
                    json!({"knowledge_id": knowledge_id}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(assessment_response.status(), StatusCode::CREATED);
    let bytes = assessment_response
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes();
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
    let outcome: Value =
        serde_json::from_str(history["events"][0]["outcome"].as_str().unwrap()).unwrap();
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
    let bytes = knowledge_response
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes();
    let knowledge: Value = serde_json::from_slice(&bytes).unwrap();
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap();

    let reference_response = router
        .clone()
        .oneshot(
            Request::post("/api/v1/learning/items/card-assessment/references")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"knowledge_id": knowledge_id}).to_string(),
                ))
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
                .body(Body::from(
                    json!({"knowledge_id": knowledge_id}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(assessment_response.status(), StatusCode::CREATED);
    let bytes = assessment_response
        .into_body()
        .collect()
        .await
        .unwrap()
        .to_bytes();
    let assessment: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(assessment["item_key"], "card-assessment");
    assert_eq!(assessment["knowledge_id"], knowledge_id);
    assert!(
        assessment["question"]
            .as_str()
            .unwrap()
            .contains("请用自己的话")
    );
    assert!(!assessment["question"].as_str().unwrap().contains("FSRS"));
    assert_ne!(assessment["question"], assessment["content"]);
    assert_eq!(
        assessment["content"],
        "FSRS schedules a next review from review history."
    );
    assert!(assessment["source_id"].is_null());
    assert!(assessment["anchor_id"].is_null());

    let mut review = request("assessment-review", "2026-09-02T00:00:00+00:00");
    review["item_key"] = json!("card-assessment");
    review["assessment_id"] = assessment["assessment_id"].clone();
    review["knowledge_version"] = assessment["knowledge_version"].clone();
    review["answer"] = json!("FSRS uses the prior review history.");
    // Evidence versions are retained as submitted observations, not approved rubric authority.
    review["question_version"] = json!("fixture-question-v1");
    review["exposure_id"] = json!("fixture-exposure-01");
    review["assist_strategy"] = json!("reference-visible");
    review["rating_version"] = json!("fixture-human-self-rating-v1");
    review["correction_id"] = json!("fixture-declared-correction");
    let replay_body = review.clone();
    let (review_status, review_response) = post(&router, review, "human").await;
    assert_eq!(review_status, StatusCode::CREATED, "{review_response}");
    assert_eq!(
        review_response["answer"],
        "FSRS uses the prior review history."
    );
    assert_eq!(
        review_response["mastery_projection"]["status"],
        "projection"
    );
    assert_eq!(review_response["mastery_projection"]["closed"], false);
    for key in [
        "question_version",
        "knowledge_version",
        "exposure_id",
        "assist_strategy",
        "rating_version",
        "correction_id",
    ] {
        assert_eq!(review_response["review_evidence"][key], replay_body[key]);
    }
    assert_eq!(
        review_response["review_evidence"]["schema"],
        "archeaxis.learning-review-evidence/v2"
    );
    let (replay_status, replay_response) = post(&router, replay_body, "human").await;
    assert_eq!(replay_status, StatusCode::OK, "{replay_response}");
    assert_eq!(replay_response["answer"], review_response["answer"]);
    assert_eq!(
        replay_response["review_evidence"],
        review_response["review_evidence"]
    );
    assert_eq!(
        replay_response["mastery_projection"],
        review_response["mastery_projection"]
    );

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
    let response = reopened
        .clone()
        .oneshot(
            Request::get("/api/v1/learning/events/card-assessment")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let history: Value = serde_json::from_slice(&bytes).unwrap();
    let saved: Value =
        serde_json::from_str(history["events"][0]["outcome"].as_str().unwrap()).unwrap();
    assert_eq!(saved["review_evidence"], review_response["review_evidence"]);
    assert_eq!(history["count"], 1);
}

// Synthetic persisted-row fixtures isolate the read projection. They do not
// claim course-worker generation, human acceptance, or installed-runtime evidence.
fn title_assessment_fixture(conn: &rusqlite::Connection, key: &str, content: &str) {
    conn.execute(
        "INSERT OR IGNORE INTO knowledge(
            knowledge_id, knowledge_type, body, status, created_by, receipt_hash
         ) VALUES('title-fixture-knowledge','FACTUAL_CLAIM',
                  'Current knowledge is not the fixed assessment snapshot.',
                  'accepted','synthetic-title-test','synthetic-title-receipt')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO learning_assessments(
            assessment_id, item_key, knowledge_id, knowledge_version, question, content
         ) VALUES(?1,?2,'title-fixture-knowledge','title-fixture-knowledge',
                  'A generic assessment question must not become the title.',?3)",
        rusqlite::params![format!("title-assessment-{key}"), key, content],
    )
    .unwrap();
}

#[tokio::test]
async fn learning_items_display_title_requires_exact_course_artifact_membership() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("title-membership.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let conn = rusqlite::Connection::open(&db).unwrap();
    conn.execute(
        "INSERT INTO sources(source_id,sha256,original_name)
                  VALUES('title-source','fixed-title-revision','synthetic-title.md')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO anchors(anchor_id,source_id,source_revision,position)
                  VALUES('title-anchor','title-source','fixed-title-revision','{}')",
        [],
    )
    .unwrap();
    for (id, title) in [("course-a", "课程 A · 原标题"), ("course-b", "课程 B")] {
        conn.execute(
            "INSERT INTO general_courses(
                manifest_id,title,manifest_json,status,human_review_required
             ) VALUES(?1,?2,?3,'candidate',1)",
            rusqlite::params![id, title, json!({"title": title}).to_string()],
        )
        .unwrap();
    }
    for (artifact, course) in [("artifact-a", "course-a"), ("artifact-b", "course-b")] {
        conn.execute(
            "INSERT INTO general_course_artifacts(
                artifact_id,manifest_id,artifact_json,status,derived_only,human_review_required
             ) VALUES(?1,?2,?3,'candidate',1,1)",
            rusqlite::params![
                artifact,
                course,
                json!({"knowledge_ids":[format!("component-{artifact}")]}).to_string()
            ],
        )
        .unwrap();
    }
    let cases = [
        ("course:course-a:artifact:artifact-a", "课程 A · 原标题"),
        ("course:course-a:artifact:artifact-b", "固定题面摘要"),
        ("course:course-a:artifact:missing", "固定题面摘要"),
        ("course:course-a:artifact:artifact-a:extra", "固定题面摘要"),
        (
            "course:course-a' OR 1=1--:artifact:artifact-a",
            "固定题面摘要",
        ),
    ];
    for (key, _) in cases {
        title_assessment_fixture(&conn, key, "\n 固定题面摘要\n第二行不是标题");
    }
    conn.execute(
        "UPDATE knowledge SET anchor_id='title-anchor'
                  WHERE knowledge_id='title-fixture-knowledge'",
        [],
    )
    .unwrap();
    conn.execute(
        "UPDATE learning_assessments SET source_id='title-source',anchor_id='title-anchor'",
        [],
    )
    .unwrap();
    for (course, component) in [
        ("course-a", "component-artifact-a"),
        ("course-b", "component-artifact-b"),
    ] {
        conn.execute(
            "INSERT INTO general_course_bindings(manifest_id,component_id,knowledge_id,
                      knowledge_version,source_id,source_revision)
                      VALUES(?1,?2,'title-fixture-knowledge','title-fixture-knowledge',
                      'title-source','fixed-title-revision')",
            rusqlite::params![course, component],
        )
        .unwrap();
    }
    // A later source state must not replace a label bound to the fixed anchor.
    conn.execute(
        "UPDATE sources SET sha256='later-title-revision' WHERE source_id='title-source'",
        [],
    )
    .unwrap();
    let (status, queue) = get_items(&router).await;
    assert_eq!(status, StatusCode::OK, "{queue}");
    assert_eq!(queue["count"], cases.len());
    let keys: Vec<_> = queue["items"]
        .as_array()
        .unwrap()
        .iter()
        .map(|row| row["item_key"].as_str().unwrap())
        .collect();
    let mut sorted_keys = keys.clone();
    sorted_keys.sort_unstable();
    assert_eq!(keys, sorted_keys);
    for (key, expected) in cases {
        let row = queue["items"]
            .as_array()
            .unwrap()
            .iter()
            .find(|row| row["item_key"] == key)
            .unwrap();
        assert_eq!(row["display_title"], expected, "{key}");
        assert!(row["next_review"].is_null());
    }
    let readonly =
        rusqlite::Connection::open_with_flags(&db, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .unwrap();
    assert_eq!(
        archeaxis_domain::learning::item_display_title(
            &readonly,
            "course:course-a:artifact:artifact-a"
        )
        .unwrap(),
        "课程 A · 原标题"
    );
    drop(readonly);
    for mutation in [
        "UPDATE general_course_bindings SET component_id='another-component' WHERE manifest_id='course-a'",
        "UPDATE general_course_bindings SET source_revision='wrong-fixed-revision' WHERE manifest_id='course-a'",
        "UPDATE learning_assessments SET knowledge_version='wrong-version' WHERE item_key='course:course-a:artifact:artifact-a'",
        "UPDATE learning_assessments SET source_id=NULL WHERE item_key='course:course-a:artifact:artifact-a'",
        "UPDATE learning_assessments SET anchor_id=NULL WHERE item_key='course:course-a:artifact:artifact-a'",
    ] {
        conn.execute(mutation, []).unwrap();
        let (_, changed) = get_items(&router).await;
        let row = changed["items"]
            .as_array()
            .unwrap()
            .iter()
            .find(|row| row["item_key"] == "course:course-a:artifact:artifact-a")
            .unwrap();
        assert_eq!(row["display_title"], "固定题面摘要", "{mutation}");
        conn.execute(
            "UPDATE general_course_bindings SET component_id='component-artifact-a',
                      source_revision='fixed-title-revision' WHERE manifest_id='course-a'",
            [],
        )
        .unwrap();
        conn.execute(
            "UPDATE learning_assessments SET knowledge_version='title-fixture-knowledge',
                      source_id='title-source',anchor_id='title-anchor'
                      WHERE item_key='course:course-a:artifact:artifact-a'",
            [],
        )
        .unwrap();
    }
    // Legal IDs alone do not prove that this assessment belongs to that course.
    conn.execute(
        "INSERT INTO knowledge(knowledge_id,knowledge_type,body,status,created_by,receipt_hash)
         VALUES('other-title-knowledge','FACTUAL_CLAIM','Other fixed source','accepted','synthetic','other-receipt')", [],
    ).unwrap();
    conn.execute(
        "UPDATE learning_assessments SET knowledge_id='other-title-knowledge',
         knowledge_version='other-title-knowledge' WHERE item_key='course:course-a:artifact:artifact-a'", [],
    ).unwrap();
    let (_, changed) = get_items(&router).await;
    let changed_row = changed["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|row| row["item_key"] == "course:course-a:artifact:artifact-a")
        .unwrap();
    assert_eq!(changed_row["display_title"], "固定题面摘要");
}

#[tokio::test]
async fn learning_items_display_title_preserves_snapshot_unicode_fallback_and_read_only_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("title-snapshot.sqlite");
    let router = app(db.to_str().unwrap()).unwrap();
    let conn = rusqlite::Connection::open(&db).unwrap();
    title_assessment_fixture(
        &conn,
        "fixed-card",
        "\n \t\n 固定\t 摘要\u{0000} 内容\n不要取第二行",
    );
    title_assessment_fixture(
        &conn,
        "unicode-card",
        &format!("\n{}\nunused", "星🛰".repeat(50)),
    );
    title_assessment_fixture(&conn, "blank-card", "\n \t\n\u{0000}");
    conn.execute(
        "INSERT INTO learning_events(item_key,kind,outcome,next_review)
         VALUES('legacy-event','review','{}','2026-09-04T00:10:00+00:00')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO card_references(item_key,knowledge_id)
         VALUES('legacy-reference','title-fixture-knowledge')",
        [],
    )
    .unwrap();
    // Deliberately vary live knowledge in this synthetic fixture: labels must
    // remain bound to the already stored assessment, not read this mutable body.
    conn.execute(
        "UPDATE knowledge SET body='Later knowledge must not replace the snapshot.'
                  WHERE knowledge_id='title-fixture-knowledge'",
        [],
    )
    .unwrap();
    let data_version: i64 = conn
        .query_row("PRAGMA data_version", [], |row| row.get(0))
        .unwrap();
    let (status, queue) = get_items(&router).await;
    assert_eq!(status, StatusCode::OK, "{queue}");
    assert_eq!(queue["count"], 5);
    let expected = [
        ("fixed-card", "固定 摘要 内容".to_owned()),
        ("unicode-card", "星🛰".repeat(40)),
        ("blank-card", "学习项目".to_owned()),
        ("legacy-event", "学习项目".to_owned()),
        ("legacy-reference", "学习项目".to_owned()),
    ];
    for (key, title) in expected {
        let row = queue["items"]
            .as_array()
            .unwrap()
            .iter()
            .find(|row| row["item_key"] == key)
            .unwrap();
        assert_eq!(row["display_title"], title);
        assert!(title.chars().count() <= 80);
        assert_eq!(row["next_review"], Value::Null);
        if key == "legacy-event" {
            assert_eq!(
                row["schedule_integrity"]["reason"],
                "legacy_review_evidence_missing_or_invalid"
            );
        }
    }
    assert_eq!(get_items(&router).await.1, queue);
    let after_read: i64 = conn
        .query_row("PRAGMA data_version", [], |row| row.get(0))
        .unwrap();
    assert_eq!(
        after_read, data_version,
        "GET must not commit any persisted changes"
    );
    // Independently prove that the new helper works on a read-only connection.
    let read_only =
        rusqlite::Connection::open_with_flags(&db, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .unwrap();
    assert_eq!(
        archeaxis_domain::learning::item_display_title(&read_only, "fixed-card").unwrap(),
        "固定 摘要 内容"
    );
    drop(read_only);
    drop(conn);
    drop(router);
    let reopened = app(db.to_str().unwrap()).unwrap();
    assert_eq!(get_items(&reopened).await.1, queue);
}

#[tokio::test]
async fn unverified_gap_withholds_only_the_current_assessment_deadline() {
    fn event(conn: &rusqlite::Connection, assessment_id: &str, scheduled: bool) -> i64 {
        let due = "2026-09-10T00:00:00Z";
        let schedule = if scheduled {
            json!({"authority":"fsrs", "state":{"state":"review", "step":null,
                "stability":5.0, "difficulty":5.0, "last_review":"2026-09-03T00:00:00Z", "due":due}})
        } else {
            json!({"authority":"unavailable", "reviewed_at":"2026-09-02T00:00:00Z"})
        };
        let outcome = json!({"assessment_id":assessment_id, "outcome":if scheduled {"correct"} else {"incorrect"},
            "schedule":schedule, "review_evidence":{"rating":if scheduled {3} else {1}, "now":"2026-09-02T00:00:00Z"}});
        conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,?3)",
            rusqlite::params!["assessment-tie-1", outcome.to_string(), if scheduled {Some(due)} else {None}]).unwrap();
        conn.last_insert_rowid()
    }

    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("current-gap.sqlite");
    let (old, current) = assessment_revision_fixture(&db);
    let historical_latest = {
        let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        event(&conn, &current.assessment_id, false);
        event(&conn, &current.assessment_id, true);
        event(&conn, &old.assessment_id, true)
    };
    let router = app(db.to_str().unwrap()).unwrap();
    let (status, state) = get_path(&router, "/api/v1/learning/items/assessment-tie-1/state").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(state["learner"]["next_review"], Value::Null);
    assert_eq!(
        state["learner"]["assessment_progress"]["latest_review"]["next_review"],
        Value::Null
    );
    assert_eq!(
        state["learner"]["schedule_integrity"]["reason"],
        "scheduled_gap_replay_unverified"
    );
    assert_eq!(
        state["learner"]["latest_review"]["event_id"],
        historical_latest
    );
    assert_eq!(
        state["learner"]["latest_review"]["next_review"],
        "2026-09-10T00:00:00Z"
    );
    let (_, queue) = get_items(&router).await;
    let item = queue["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["item_key"] == "assessment-tie-1")
        .unwrap();
    assert_eq!(item["next_review"], Value::Null);
    assert_eq!(
        item["schedule_integrity"]["reason"],
        "scheduled_gap_replay_unverified"
    );

    let clean_db = dir.path().join("historical-gap.sqlite");
    let (old, current) = assessment_revision_fixture(&clean_db);
    {
        let conn = archeaxis_store_sqlite::init_workspace(clean_db.to_str().unwrap()).unwrap();
        event(&conn, &old.assessment_id, false);
        event(&conn, &old.assessment_id, true);
        event(&conn, &current.assessment_id, true);
    }
    let clean = app(clean_db.to_str().unwrap()).unwrap();
    let (_, state) = get_path(&clean, "/api/v1/learning/items/assessment-tie-1/state").await;
    assert_eq!(state["learner"]["next_review"], "2026-09-10T00:00:00Z");
    assert!(state["learner"].get("schedule_integrity").is_none());
    let (_, queue) = get_items(&clean).await;
    let item = queue["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["item_key"] == "assessment-tie-1")
        .unwrap();
    assert_eq!(item["next_review"], "2026-09-10T00:00:00Z");
    assert!(item.get("schedule_integrity").is_none());
}

async fn assert_unverified_projection(router: &axum::Router, item_key: &str, reason: &str) {
    let (status, state) =
        get_path(router, &format!("/api/v1/learning/items/{item_key}/state")).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(state["learner"]["next_review"], Value::Null);
    assert_eq!(
        state["learner"]["latest_review"]["next_review"],
        Value::Null
    );
    assert_eq!(
        state["learner"]["schedule_integrity"]["state"],
        "unverified"
    );
    assert_eq!(state["learner"]["schedule_integrity"]["reason"], reason);
    let (status, queue) = get_items(router).await;
    assert_eq!(status, StatusCode::OK);
    let item = queue["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|value| value["item_key"] == item_key)
        .unwrap();
    assert_eq!(item["next_review"], Value::Null);
    assert_eq!(item["schedule_integrity"]["reason"], reason);
}

#[tokio::test]
async fn legacy_review_gap_before_card_withholds_read_only_deadline() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy-gap-projection.sqlite");
    let item = "synthetic-legacy-projection";
    let due = "2026-09-10T00:00:00Z";
    {
        let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        let old = json!({"outcome":"incorrect", "schedule":{"authority":"placeholder_ladder"}});
        let card = json!({"outcome":"correct", "schedule":{"authority":"fsrs",
            "state":{"state":"review", "step":null, "stability":5.0, "difficulty":5.0,
                "last_review":"2026-09-03T00:00:00Z", "due":due}}});
        conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,NULL)",
            rusqlite::params![item, old.to_string()]).unwrap();
        conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,?3)",
            rusqlite::params![item, card.to_string(), due]).unwrap();
    }
    let router = app(db.to_str().unwrap()).unwrap();
    assert_unverified_projection(&router, item, "legacy_review_evidence_missing_or_invalid").await;
    let (_, history) = get_path(&router, &format!("/api/v1/learning/events/{item}")).await;
    assert_eq!(
        history["events"][1]["next_review"], due,
        "raw historical records must remain unchanged"
    );
}

#[tokio::test]
async fn invalid_previous_card_withholds_read_only_deadline() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("invalid-card-projection.sqlite");
    let item = "synthetic-invalid-card-projection";
    let due = "2026-09-10T00:00:00Z";
    {
        let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        let card = json!({"outcome":"correct", "schedule":{"authority":"fsrs", "state":null}});
        conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,?3)",
            rusqlite::params![item, card.to_string(), due]).unwrap();
    }
    let router = app(db.to_str().unwrap()).unwrap();
    assert_unverified_projection(&router, item, "invalid_previous_card").await;
    let (_, history) = get_path(&router, &format!("/api/v1/learning/events/{item}")).await;
    assert_eq!(
        history["events"][0]["next_review"], due,
        "raw historical records must remain unchanged"
    );
}

#[tokio::test]
async fn legacy_projection_is_assessment_scoped_and_human_reset_restores_deadline() {
    fn event(
        conn: &rusqlite::Connection,
        assessment: &str,
        legacy: bool,
        reset_from: Option<i64>,
    ) -> i64 {
        let due = "2026-09-10T00:00:00Z";
        let mut outcome = if legacy {
            json!({"assessment_id":assessment,"outcome":"incorrect","schedule":{"authority":"placeholder_ladder"}})
        } else {
            json!({"assessment_id":assessment,"outcome":"correct", "schedule":{"authority":"fsrs",
                "state":{"state":"review","step":null,"stability":5.0,"difficulty":5.0,
                    "last_review":"2026-09-03T00:00:00Z","due":due}}})
        };
        if let Some(cursor) = reset_from {
            outcome["review_evidence"] = json!({"schedule_reset":{"mode":"start_new",
                "reason":"Synthetic explicit reset","expected_latest_event_id":cursor}});
            outcome["schedule"]["recovery"] = json!({"mode":"start_new","state":"reset",
                "reason":"Synthetic explicit reset","excluded_through_event_id":cursor});
        }
        conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,?3)",
            rusqlite::params!["assessment-tie-1", outcome.to_string(), if legacy {None} else {Some(due)}]).unwrap();
        conn.last_insert_rowid()
    }

    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("legacy-projection-assessment.sqlite");
    let (old, current) = assessment_revision_fixture(&db);
    {
        let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        event(&conn, &old.assessment_id, true, None);
        event(&conn, &old.assessment_id, false, None);
        event(&conn, &current.assessment_id, false, None);
    }
    let router = app(db.to_str().unwrap()).unwrap();
    let (_, state) = get_path(&router, "/api/v1/learning/items/assessment-tie-1/state").await;
    assert_eq!(state["learner"]["next_review"], "2026-09-10T00:00:00Z");
    assert!(state["learner"].get("schedule_integrity").is_none());
    drop(router);
    let (current_cursor, historical_latest) = {
        let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        event(&conn, &current.assessment_id, true, None);
        let current_cursor = event(&conn, &current.assessment_id, false, None);
        let historical_latest = event(&conn, &old.assessment_id, false, None);
        (current_cursor, historical_latest)
    };
    let router = app(db.to_str().unwrap()).unwrap();
    let (_, state) = get_path(&router, "/api/v1/learning/items/assessment-tie-1/state").await;
    assert_eq!(state["learner"]["next_review"], Value::Null);
    assert_eq!(
        state["learner"]["assessment_progress"]["latest_review"]["next_review"],
        Value::Null
    );
    assert_eq!(
        state["learner"]["schedule_integrity"]["reason"],
        "legacy_review_evidence_missing_or_invalid"
    );
    assert_eq!(
        state["learner"]["latest_review"]["event_id"],
        historical_latest
    );
    assert_eq!(
        state["learner"]["latest_review"]["next_review"],
        "2026-09-10T00:00:00Z"
    );
    let (_, queue) = get_items(&router).await;
    let item = queue["items"]
        .as_array()
        .unwrap()
        .iter()
        .find(|row| row["item_key"] == "assessment-tie-1")
        .unwrap();
    assert_eq!(item["next_review"], Value::Null);
    let (_, history_before) = get_path(&router, "/api/v1/learning/events/assessment-tie-1").await;
    drop(router);
    {
        let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        event(&conn, &current.assessment_id, false, Some(current_cursor));
    }
    let router = app(db.to_str().unwrap()).unwrap();
    let (_, state) = get_path(&router, "/api/v1/learning/items/assessment-tie-1/state").await;
    assert_eq!(state["learner"]["next_review"], "2026-09-10T00:00:00Z");
    assert!(state["learner"].get("schedule_integrity").is_none());
    let (_, history_after) = get_path(&router, "/api/v1/learning/events/assessment-tie-1").await;
    let before = history_before["events"].as_array().unwrap();
    let after = history_after["events"].as_array().unwrap();
    assert_eq!(&after[..before.len()], before.as_slice());
    assert_eq!(after.len(), before.len() + 1);
}

#[tokio::test]
async fn malformed_legacy_and_bad_timestamps_do_not_expose_a_deadline() {
    for (name, legacy, card, expected) in [
        (
            "bad-json",
            Some("{".to_owned()),
            json!({"state":"review","step":null,"stability":5.0,
            "difficulty":5.0,"last_review":"2026-09-03T00:00:00Z","due":"2026-09-10T00:00:00Z"}),
            "legacy_review_evidence_missing_or_invalid",
        ),
        (
            "bad-time",
            None,
            json!({"state":"review","step":null,"stability":5.0,
            "difficulty":5.0,"last_review":"not-a-time","due":"2026-09-10T00:00:00Z"}),
            "invalid_previous_card",
        ),
        (
            "bad-number",
            None,
            json!({"state":"review","step":null,"stability":"bad",
            "difficulty":5.0,"last_review":"2026-09-03T00:00:00Z","due":"2026-09-10T00:00:00Z"}),
            "invalid_previous_card",
        ),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join(format!("{name}.sqlite"));
        let due = "2026-09-10T00:00:00Z";
        {
            let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
            if let Some(raw) = legacy {
                conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,NULL)",
                    rusqlite::params![name, raw]).unwrap();
            }
            let outcome = json!({"outcome":"correct","schedule":{"authority":"fsrs","state":card}});
            conn.execute("INSERT INTO learning_events(item_key,kind,outcome,next_review) VALUES(?1,'review',?2,?3)",
                rusqlite::params![name, outcome.to_string(), due]).unwrap();
        }
        let router = app(db.to_str().unwrap()).unwrap();
        assert_unverified_projection(&router, name, expected).await;
    }
}
