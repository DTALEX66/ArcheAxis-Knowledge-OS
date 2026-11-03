//! Terminal-only reconciliation of stale grading dispatches: the explicit
//! operator trigger and the periodic sweep.
//!
//! Both apply one bounded rule - a `DISPATCHED` claim whose recorded second is
//! older than the budget window becomes terminal `UNKNOWN` - and neither starts,
//! re-sends or retries a worker. These cases never launch the real grader: the
//! Core is opened without a practice worker, so a case that could reach a worker
//! would fail closed instead of passing.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{
    document,
    provider_learning::{self as learning, Activity, Provider, Question, Start, grade},
    provider_material_grant::Snapshot,
    provider_question,
};
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use tower::ServiceExt;

const ACTIVITIES: &str = "/api/v1/learning/provider-activities";
const GRADE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade";
const RECONCILE_ROUTE: &str = "/api/v1/learning/deeptutor/practice-grade/reconcile";

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn grant(conn: &mut rusqlite::Connection, material: &Value) -> Value {
    document::create_optional(conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
            "purpose":"practice","consumer":"deeptutor","operations":["practice"],
            "material":snap(material),"authorization_basis":"SYNTHETIC explicit human authorization",
            "expires_at":null,"state":"granted"}
    }})).unwrap()
}

struct Workspace {
    _dir: tempfile::TempDir,
    db: PathBuf,
    staging: PathBuf,
    request: grade::GradeRequest,
}

/// A synthetic question Document, its two version-bound grants, one DeepTutor
/// 1.7.1 activity and one attempt whose dispatch intent is already recorded.
fn dispatched_workspace() -> Workspace {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let source = document::create_optional(
        &mut conn,
        None,
        None,
        "SYNTHETIC material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let question = document::create_optional(&mut conn,None,None,"SYNTHETIC question",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_deeptutor_question":{"schema":"archeaxis.deeptutor-question/v1","source_material":snap(&source),
            "origin":"user_import_unverified","question":{"question_id":"question_1","question":"synthetic?",
            "question_type":"choice","options":{"A":"first","B":"second"},"correct_answer":"A",
            "explanation":"SYNTHETIC_PRIVATE_EXPLANATION"}}
    }})).unwrap();
    let source_grant = grant(&mut conn, &source);
    let question_grant = grant(&mut conn, &question);
    let view = provider_question::read_view(&conn, &snap(&question)).unwrap();
    learning::create(
        &mut conn,
        &Activity {
            activity_id: "activity".into(),
            material: snap(&source),
            provider: Provider {
                id: "deeptutor".into(),
                version: "1.7.1".into(),
            },
            question: Question {
                question_id: "question_1".into(),
                question_version: view["question_version"].as_str().unwrap().into(),
            },
            grant: Some(snap(&source_grant)),
        },
    )
    .unwrap();
    learning::start(
        &mut conn,
        "activity",
        &Start {
            attempt_id: "attempt".into(),
        },
    )
    .unwrap();
    let request = grade::GradeRequest {
        client_event_id: "event".into(),
        question_document: snap(&question),
        question_grant: snap(&question_grant),
        answer: "A".into(),
    };
    let prepared = match grade::prepare(&mut conn, "activity", "attempt", &request).unwrap() {
        grade::Admission::Ready(prepared) => prepared,
        _ => panic!("expected a new reservation"),
    };
    grade::begin_dispatch(&mut conn, &prepared, Duration::from_secs(60)).unwrap();
    Workspace {
        staging: dir.path().join("staging"),
        _dir: dir,
        db,
        request,
    }
}

/// Open the Core over the prepared workspace. No practice worker is registered,
/// so any attempt to launch the grader fails closed rather than grading.
async fn core(workspace: &Workspace) -> Executor {
    Executor::open_routes(
        &workspace.db,
        &workspace.staging,
        Path::new("unused-python"),
        &workspace.staging.join("unused-worker"),
        &[],
    )
    .await
    .unwrap()
}

/// Age the durable dispatch second so the recorded window has closed.
async fn age_dispatch(executor: &Executor, seconds_ago: u64) {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    executor
        .store()
        .submit_wait(move |conn| {
            let key: String = conn.query_row(
                "SELECT key FROM workspace_meta WHERE key LIKE 'provider_grade_dispatch_%'",
                [],
                |row| row.get(0),
            )?;
            conn.execute(
                "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                rusqlite::params![now.saturating_sub(seconds_ago).to_string(), key],
            )?;
            Ok::<(), rusqlite::Error>(())
        })
        .await
        .unwrap()
        .unwrap();
}

async fn call(
    router: &axum::Router,
    method: &str,
    uri: &str,
    body: &Value,
    actor: &str,
) -> (StatusCode, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(uri)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
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

async fn disposition(router: &axum::Router) -> Value {
    let (status, body) = call(
        router,
        "GET",
        &format!("{ACTIVITIES}/activity"),
        &Value::Null,
        "human",
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{body}");
    body["attempts"][0]["grade_disposition"].clone()
}

#[tokio::test]
async fn reconcile_is_human_only_and_never_starts_a_worker() {
    let workspace = dispatched_workspace();
    let executor = core(&workspace).await;
    let router = archeaxis_api::runtime::router(executor);

    let (status, body) = call(&router, "POST", RECONCILE_ROUTE, &Value::Null, "machine").await;
    assert_eq!(status, StatusCode::FORBIDDEN, "{body}");
    assert_eq!(body["code"], "DEEPTUTOR_PRACTICE_GRADE");
    assert_eq!(body["reason"], "human_actor_required");

    // A dispatch inside its window is not stale: the trigger reports it as recent
    // and leaves the claim alone, so a worker that is still grading is not cut off.
    let (status, swept) = call(&router, "POST", RECONCILE_ROUTE, &Value::Null, "human").await;
    assert_eq!(status, StatusCode::OK, "{swept}");
    assert_eq!(swept["schema"], "archeaxis.grade-dispatch-reconcile/v1");
    assert_eq!(swept["abandoned"], 0);
    assert_eq!(swept["recent"], 1);
    assert_eq!(swept["skipped"], 0);
    assert_eq!(swept["worker_relaunches"], 0);
    assert_eq!(disposition(&router).await["state"], "DISPATCHED");
}

#[tokio::test]
async fn reconcile_finalizes_one_aged_dispatch_and_stays_terminal() {
    let workspace = dispatched_workspace();
    let executor = core(&workspace).await;
    age_dispatch(&executor, 1_000).await;
    let router = archeaxis_api::runtime::router(executor);

    let (status, swept) = call(&router, "POST", RECONCILE_ROUTE, &Value::Null, "human").await;
    assert_eq!(status, StatusCode::OK, "{swept}");
    assert_eq!(swept["abandoned"], 1);
    assert_eq!(swept["recent"], 0);
    assert_eq!(
        swept["window_seconds"],
        grade::DISPATCH_STALE_GRACE.as_secs()
    );
    assert_eq!(disposition(&router).await["state"], "UNKNOWN");

    // Repeating the trigger is a no-op, never a second finalization.
    let (status, again) = call(&router, "POST", RECONCILE_ROUTE, &Value::Null, "human").await;
    assert_eq!(status, StatusCode::OK, "{again}");
    assert_eq!(again["abandoned"], 0);
    assert_eq!(again["recent"], 0);
    assert_eq!(again["skipped"], 0);
    assert_eq!(disposition(&router).await["state"], "UNKNOWN");

    // The same event stays a read-only UNKNOWN: it is refused before any worker
    // could be launched, so "at most once" dispatch is unchanged.
    let body = json!({"activity_id":"activity","attempt_id":"attempt","request":workspace.request});
    let (status, refused) = call(&router, "POST", GRADE_ROUTE, &body, "human").await;
    assert_eq!(status, StatusCode::CONFLICT, "{refused}");
    assert_eq!(refused["reason"], "practice_grade_outcome_unknown");
    assert_eq!(disposition(&router).await["state"], "UNKNOWN");
}

#[tokio::test]
async fn periodic_sweep_finalizes_an_aged_dispatch_and_leaves_a_fresh_one() {
    let workspace = dispatched_workspace();
    let executor = core(&workspace).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    let sweeper = executor.spawn_grade_dispatch_sweeper(Duration::from_millis(50));

    // Several ticks pass while the dispatch is still inside its window: they must
    // not finalize it.
    for _ in 0..4 {
        tokio::time::sleep(Duration::from_millis(60)).await;
        assert_eq!(disposition(&router).await["state"], "DISPATCHED");
    }

    age_dispatch(&executor, 1_000).await;
    let deadline = tokio::time::Instant::now() + Duration::from_secs(5);
    loop {
        let observed = disposition(&router).await;
        if observed["state"] == "UNKNOWN" {
            break;
        }
        assert!(
            tokio::time::Instant::now() < deadline,
            "the sweep never finalized an aged dispatch, still {observed}"
        );
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    // It stays terminal across further ticks.
    tokio::time::sleep(Duration::from_millis(200)).await;
    assert_eq!(disposition(&router).await["state"], "UNKNOWN");
    sweeper.abort();
}
