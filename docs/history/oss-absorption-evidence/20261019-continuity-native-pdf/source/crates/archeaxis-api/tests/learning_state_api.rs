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
        assert_eq!(
            row["next_review"],
            if key == "legacy-event" {
                json!("2026-09-04T00:10:00+00:00")
            } else {
                Value::Null
            }
        );
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
