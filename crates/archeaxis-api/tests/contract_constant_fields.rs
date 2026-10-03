//! The contract's "fields that are constants, not data" list, as executable checks.
//!
//! docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md §4 warns the UI not to render six
//! things as measured values. A warning like that is only useful if it is true, so each is
//! driven through the real HTTP router here.
//!
//! The strongest is the first: `machine.status` is `not_recorded` *even when machine receipts
//! exist*, because no route writes the machine competence ledger. If that were false, a UI
//! showing "no machine record" while receipts sit in the database would be showing the user
//! something untrue.
//!
//! Driving these against a live Core first refuted four of the checks and none of the claims -
//! the fields were where the contract said, but not where an optimistic reading looked for them.
//! Two corrections are worth keeping in view: the mastery projection travels with a review and
//! reaches item state under `learner.latest_review` rather than at the top level, and an event's
//! `outcome` is a JSON document carried as a string rather than a bare word.

use archeaxis_application::{executor::Executor, jobs};
use archeaxis_domain::{knowledge, learning, source};
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::{path::PathBuf, time::Duration};
use tower::ServiceExt;

/// The fixture, plus the knowledge id the learning routes need.
struct Fixture {
    _dir: tempfile::TempDir,
    executor: Executor,
    knowledge_id: String,
}

async fn fixture() -> Fixture {
    let dir = tempfile::tempdir().unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
    )
    .await
    .unwrap();
    let knowledge_id = executor
        .store()
        .submit(|conn| {
            let id =
                match source::import_source(conn, b"alpha beta gamma\n", "n.txt", None).unwrap() {
                    source::ImportOutcome::Imported { source_id, .. } => source_id,
                    _ => unreachable!(),
                };
            let knowledge_id = knowledge::create_knowledge(
                conn, "NOTE", "a note", "accepted", None, None, "human",
            )
            .unwrap();
            learning::record_card_reference(conn, "card-1", &knowledge_id, None).unwrap();
            jobs::enqueue(conn, "job", "text", &id).unwrap();
            Ok::<String, rusqlite::Error>(knowledge_id)
        })
        .await
        .unwrap()
        .unwrap();
    Fixture {
        _dir: dir,
        executor,
        knowledge_id,
    }
}

async fn call(
    router: &Router,
    method: &str,
    path: &str,
    body: Option<serde_json::Value>,
) -> (u16, serde_json::Value) {
    call_as(router, method, path, body, None).await
}

/// `actor` sets the header the Core reads to decide human or machine; the machine routes
/// refuse a human and the human routes refuse a machine, so it has to be explicit. `key` is the
/// `idempotency-key` an execution requires.
async fn call_as(
    router: &Router,
    method: &str,
    path: &str,
    body: Option<serde_json::Value>,
    actor: Option<&str>,
) -> (u16, serde_json::Value) {
    call_with(router, method, path, body, actor, None).await
}

async fn call_with(
    router: &Router,
    method: &str,
    path: &str,
    body: Option<serde_json::Value>,
    actor: Option<&str>,
    key: Option<&str>,
) -> (u16, serde_json::Value) {
    let mut builder = Request::builder().method(method).uri(path);
    if let Some(actor) = actor {
        builder = builder.header("x-archeaxis-actor", actor);
    }
    if let Some(key) = key {
        builder = builder.header("idempotency-key", key);
    }
    let request = match body {
        Some(value) => {
            builder = builder.header("content-type", "application/json");
            builder.body(Body::from(value.to_string())).unwrap()
        }
        None => builder.body(Body::empty()).unwrap(),
    };
    let resp = router.clone().oneshot(request).await.unwrap();
    let status = resp.status().as_u16();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap_or_default())
}

async fn settle(router: &Router, job: &str) {
    tokio::time::timeout(Duration::from_secs(10), async {
        loop {
            let (_, value) = call(router, "GET", &format!("/api/v1/jobs/{job}"), None).await;
            if value["state"] != "running" && value["state"] != "queued" {
                return;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
}

#[tokio::test]
async fn machine_status_stays_not_recorded_even_when_receipts_exist() {
    let fixture = fixture().await;
    let router = archeaxis_api::runtime::router(fixture.executor.clone());

    let (status, before) = call(&router, "GET", "/api/v1/learning/items/card-1/state", None).await;
    assert_eq!(status, 200, "{before}");
    assert_eq!(
        before["machine"]["status"], "not_recorded",
        "with no receipts the ledger is still not recorded: {before}"
    );
    let note = before["machine"]["note"]
        .as_str()
        .unwrap_or_default()
        .to_owned();
    assert!(
        note.contains("never presented as machine competence"),
        "the fixed note must say what the UI is looking at: {note}"
    );

    let (status, posted) = call_as(
        &router,
        "POST",
        "/api/v1/machine/tasks",
        Some(serde_json::json!({
            "task_id": "task-1", "conditions": "none", "model_version": "stub/local-stub",
            "scope": "probe", "outcome": "failed", "failure": "declared stub model"
        })),
        Some("machine"),
    )
    .await;
    assert_eq!(status, 201, "{posted}");

    let (status, after) = call(&router, "GET", "/api/v1/learning/items/card-1/state", None).await;
    assert_eq!(status, 200, "{after}");
    assert_eq!(
        after["machine"]["status"], "not_recorded",
        "a receipt must not move this field, because nothing writes the competence ledger: {after}"
    );
    assert_eq!(after["machine"]["note"], before["machine"]["note"]);
}

#[tokio::test]
async fn the_mastery_projection_is_open_wherever_it_is_reported() {
    let fixture = fixture().await;
    let router = archeaxis_api::runtime::router(fixture.executor.clone());

    let (status, assessment) = call(
        &router,
        "POST",
        "/api/v1/learning/items/card-1/assessment",
        Some(serde_json::json!({"knowledge_id": fixture.knowledge_id})),
    )
    .await;
    assert_eq!(
        status, 201,
        "an assessment needs the card to reference the revision: {assessment}"
    );
    let assessment_id = assessment["assessment_id"].as_str().unwrap().to_owned();
    // The assessment states the revision it was built from; the review must name that same one.
    let assessed_version = assessment["knowledge_version"].as_str().unwrap().to_owned();

    let (status, review) = call(
        &router,
        "POST",
        "/api/v1/learning/reviews",
        Some(serde_json::json!({
            "item_key": "card-1", "client_event_id": "r-1", "assessment_id": assessment_id,
            "knowledge_version": assessed_version, "answer": "alpha", "correct": true
        })),
    )
    .await;
    assert_eq!(status, 201, "{review}");
    assert_eq!(
        review["mastery_projection"]["closed"], false,
        "mastery is deliberately an open projection, never a closed claim: {review}"
    );

    // and the same constant reaches item state under learner.latest_review
    let (status, state) = call(&router, "GET", "/api/v1/learning/items/card-1/state", None).await;
    assert_eq!(status, 200, "{state}");
    assert_eq!(
        state["learner"]["latest_review"]["mastery_projection"]["closed"], false,
        "the constant must read the same wherever it is exposed: {state}"
    );

    // correct_streak is derived: it equals the correct events on record, whose `outcome` is a
    // JSON document carried as a string rather than a bare word.
    let (_, history) = call(&router, "GET", "/api/v1/learning/events/card-1", None).await;
    let events = history["events"].as_array().cloned().unwrap_or_default();
    let correct = events
        .iter()
        .filter(|event| {
            event["outcome"]
                .as_str()
                .and_then(|raw| serde_json::from_str::<serde_json::Value>(raw).ok())
                .and_then(|parsed| {
                    parsed
                        .get("outcome")
                        .and_then(|v| v.as_str())
                        .map(str::to_owned)
                })
                .is_some_and(|outcome| outcome == "correct")
        })
        .count();
    assert!(
        correct > 0,
        "the fixture should have recorded a correct event: {history}"
    );
    assert_eq!(
        state["learner"]["correct_streak"].as_u64().unwrap_or(0) as usize,
        correct,
        "correct_streak must be re-derived from the events, not fixed: {state}"
    );

    // The recognisable counts and times come from that same log, so the product can show a
    // learner how they are doing without any of it turning into a mastery claim.
    let projection = &state["learner"]["latest_review"]["mastery_projection"];
    assert_eq!(
        projection["attempts"].as_u64().unwrap_or(0) as usize,
        events.len(),
        "attempts must equal the events on record, not a fixed number: {state}"
    );
    let distinct_days = projection["distinct_correct_days"].as_u64().unwrap_or(0);
    assert!(
        distinct_days >= 1 && distinct_days as usize <= correct,
        "distinct_correct_days must be a derived count bounded by the correct events: {state}"
    );
    assert!(
        projection["last_correct_at"].is_string(),
        "last_correct_at must name when the last correct answer happened: {state}"
    );
    assert!(
        projection["next_review_at"].is_string(),
        "next_review_at must carry the schedule the Core already computed: {state}"
    );
    assert_eq!(
        projection["closed"], false,
        "adding what the learner did must not close the mastery claim: {state}"
    );
}

#[tokio::test]
async fn the_placeholder_ladder_is_not_fsrs() {
    let fixture = fixture().await;
    let router = archeaxis_api::runtime::router(fixture.executor);

    let (status, event) = call(
        &router,
        "POST",
        "/api/v1/learning/events",
        Some(serde_json::json!({
            "item_key": "card-1", "kind": "quiz", "outcome": "correct",
            "client_event_id": "e-1", "correct": true
        })),
    )
    .await;
    assert_eq!(status, 201, "{event}");
    assert_eq!(
        event["schedule_authority"], "placeholder_ladder",
        "a review with no schedule_state must not claim fsrs: {event}"
    );
    assert!(
        event["next_review"].is_null(),
        "the ladder is a stub, so it reports no scheduled date: {event}"
    );
    assert!(
        event["next_review_days"].is_number(),
        "the ladder's own interval is reported as days so the UI can tell it apart: {event}"
    );
}

#[tokio::test]
async fn job_quality_and_source_members_carry_their_fixed_notes() {
    let fixture = fixture().await;
    let router = archeaxis_api::runtime::router(fixture.executor);

    let (execute_status, executed) = call_with(
        &router,
        "POST",
        "/api/v1/jobs/job/executions",
        Some(serde_json::json!({"deadline_ms": 60000})),
        None,
        Some("run-1"),
    )
    .await;
    assert!(
        execute_status == 202,
        "the execution must be accepted: {executed}"
    );
    settle(&router, "job").await;

    let (status, quality) = call(&router, "GET", "/api/v1/jobs/job/quality", None).await;
    assert_eq!(status, 200, "{quality}");
    assert!(
        quality["note"].is_string(),
        "job quality must carry its fixed note: {quality}"
    );

    let (_, job) = call(&router, "GET", "/api/v1/jobs/job", None).await;
    let source_id = job["input_ref"].as_str().unwrap().to_owned();
    let (status, members) = call(
        &router,
        "GET",
        &format!("/api/v1/sources/{source_id}/members"),
        None,
    )
    .await;
    assert_eq!(status, 200, "{members}");
    assert!(
        members["note"].is_string(),
        "source members must carry its fixed note: {members}"
    );
}
