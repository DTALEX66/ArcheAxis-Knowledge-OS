//! R7/G1: the capability surface, and the limits it must not exceed.
//!
//! The master taskpack's section 42 asks the first version for a registry with health, default and
//! fallback, and names `AAOS_CAPABILITY_REGISTRY_V1`. A capability surface is where a project most
//! easily starts lying to itself, so the checks below are as much about what it must *not* claim as
//! about what it reports.
//!
//! Three rules are pinned executably:
//!
//! * it reports the routes the Core registered, not the routes a checkout contains;
//! * `health` is file existence and says so, because only a job can show a capability works;
//! * an unknown capability is a `404` rather than the nearest match.

use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

async fn executor_with(routes: &[(&str, PathBuf)]) -> (tempfile::TempDir, Executor) {
    let dir = tempfile::tempdir().unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
        routes,
    )
    .await
    .unwrap();
    (dir, executor)
}

async fn get(router: &Router, path: &str) -> (u16, serde_json::Value) {
    let response = router
        .clone()
        .oneshot(Request::builder().uri(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(serde_json::Value::Null),
    )
}

#[tokio::test]
async fn the_registry_reports_the_routes_the_core_registered() {
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/vision/worker_caption.py");
    let (_dir, executor) = executor_with(&[("image.caption", worker)]).await;
    let (status, body) = get(
        &archeaxis_api::runtime::router(executor),
        "/api/v1/capabilities",
    )
    .await;

    assert_eq!(status, 200, "{body}");
    assert_eq!(body["schema"], "archeaxis.capabilities/v1");
    // the default text route is always present, and the declared one was added
    let names: Vec<String> = body["capabilities"]
        .as_array()
        .unwrap()
        .iter()
        .map(|record| record["capability"].as_str().unwrap().to_string())
        .collect();
    assert!(names.contains(&"text.extract".to_string()), "{names:?}");
    assert!(names.contains(&"image.caption".to_string()), "{names:?}");
    assert_eq!(body["count"], names.len());
}

#[tokio::test]
async fn a_registered_capability_names_the_worker_that_would_answer() {
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/vision/worker_caption.py");
    let (_dir, executor) = executor_with(&[("image.caption", worker)]).await;
    let (status, body) = get(
        &archeaxis_api::runtime::router(executor),
        "/api/v1/capabilities/image.caption",
    )
    .await;

    assert_eq!(status, 200, "{body}");
    let record = &body["capability"];
    assert_eq!(record["capability"], "image.caption");
    assert_eq!(record["provider"]["kind"], "python-worker");
    // the provider is a path that really exists, not a name
    assert_eq!(record["provider"]["worker_present"], true, "{record}");
    assert_eq!(record["health"], "declared", "{record}");
}

#[tokio::test]
async fn health_says_it_is_file_existence_rather_than_a_working_capability() {
    let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/vision/worker_caption.py");
    let (_dir, executor) = executor_with(&[("image.caption", worker)]).await;
    let (_, body) = get(
        &archeaxis_api::runtime::router(executor),
        "/api/v1/capabilities",
    )
    .await;

    // The surface must not let a passing entry be read as proof the capability works.
    assert_eq!(body["declared_only"], true);
    let basis = body["capabilities"][0]["health_basis"].as_str().unwrap();
    assert!(basis.contains("job has to run"), "{basis}");
    assert_eq!(
        body["capabilities"][0]["health_basis"],
        body["capabilities"][1]["health_basis"]
    );
}

#[tokio::test]
async fn a_capability_whose_worker_is_absent_is_unusable_rather_than_unhealthy() {
    let (_dir, executor) = executor_with(&[(
        "image.caption",
        PathBuf::from("this/worker/does/not/exist.py"),
    )])
    .await;
    let (status, body) = get(
        &archeaxis_api::runtime::router(executor),
        "/api/v1/capabilities/image.caption",
    )
    .await;

    assert_eq!(status, 200, "{body}");
    let record = &body["capability"];
    assert_eq!(record["provider"]["worker_present"], false);
    assert_eq!(record["health"], "worker_missing", "{record}");
    // and the difference is stated rather than folded into a generic unhealthy
    assert_ne!(record["health"], "declared");
}

#[tokio::test]
async fn enable_is_recorded_rather_than_asserted_and_fallback_is_still_absent() {
    let (_dir, executor) = executor_with(&[]).await;
    let (_, body) = get(
        &archeaxis_api::runtime::router(executor),
        "/api/v1/capabilities",
    )
    .await;

    let record = &body["capabilities"][0];
    // `enabled` is now read from the workspace's record, and the basis says which record
    assert_eq!(record["enabled"], true);
    assert!(
        record["enabled_basis"]
            .as_str()
            .unwrap()
            .contains("absent record means enabled"),
        "{record}"
    );
    // no capability has a second provider yet, and the surface must not imply one
    assert!(record["fallback"].is_null());
    assert!(
        record["fallback_note"]
            .as_str()
            .unwrap()
            .contains("no second provider")
    );
}

// --- enable / disable --------------------------------------------------------------------------

async fn put(router: &Router, path: &str, body: &str) -> (u16, serde_json::Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri(path)
                .header("content-type", "application/json")
                .body(Body::from(body.to_owned()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(serde_json::Value::Null),
    )
}

#[tokio::test]
async fn disabling_a_capability_is_recorded_and_reported_back() {
    let (_dir, executor) = executor_with(&[]).await;
    let router = archeaxis_api::runtime::router(executor);

    let (status, body) = put(
        &router,
        "/api/v1/capabilities/text.extract/enabled",
        r#"{"enabled":false}"#,
    )
    .await;
    assert_eq!(status, 200, "{body}");
    // the response is the record as it now stands, re-read rather than echoed from the request
    assert_eq!(body["capability"]["enabled"], false, "{body}");

    let (_, listing) = get(&router, "/api/v1/capabilities").await;
    assert_eq!(listing["disabled"], 1, "{listing}");
    assert_eq!(listing["capabilities"][0]["enabled"], false, "{listing}");

    // and it can be turned back on
    let (status, body) = put(
        &router,
        "/api/v1/capabilities/text.extract/enabled",
        r#"{"enabled":true}"#,
    )
    .await;
    assert_eq!(status, 200, "{body}");
    assert_eq!(body["capability"]["enabled"], true, "{body}");
    let (_, listing) = get(&router, "/api/v1/capabilities").await;
    assert_eq!(listing["disabled"], 0, "{listing}");
}

#[tokio::test]
async fn an_empty_or_misspelled_body_never_silently_disables_a_capability() {
    let (_dir, executor) = executor_with(&[]).await;
    let router = archeaxis_api::runtime::router(executor);

    // `{}` must not mean "disable": that would make the most destructive action the default.
    let (status, _) = put(&router, "/api/v1/capabilities/text.extract/enabled", "{}").await;
    assert_eq!(
        status, 422,
        "an empty body must be refused rather than read as disable"
    );

    // and a misspelled key must be refused rather than silently ignored
    let (status, _) = put(
        &router,
        "/api/v1/capabilities/text.extract/enabled",
        r#"{"enable":false}"#,
    )
    .await;
    assert_eq!(
        status, 422,
        "an unknown field must be refused rather than ignored"
    );

    let (_, listing) = get(&router, "/api/v1/capabilities").await;
    assert_eq!(listing["disabled"], 0, "{listing}");
}

#[tokio::test]
async fn a_capability_that_does_not_exist_cannot_be_switched() {
    let (_dir, executor) = executor_with(&[]).await;
    let router = archeaxis_api::runtime::router(executor);

    // Rows for capabilities that do not exist would later read as decisions about nothing.
    let (status, _) = put(
        &router,
        "/api/v1/capabilities/does.not.exist/enabled",
        r#"{"enabled":false}"#,
    )
    .await;
    assert_eq!(status, 404);
}

#[tokio::test]
async fn a_disabled_capability_is_refused_by_the_execute_path() {
    // This is the check that makes the field mean something: if disabling only changed a report,
    // the registry would be describing a setting that does not exist.
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
    executor
        .store()
        .submit(|conn| {
            let id = match archeaxis_domain::source::import_source(
                conn,
                b"alpha beta gamma\n",
                "n.txt",
                None,
            )
            .unwrap()
            {
                archeaxis_domain::source::ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            archeaxis_application::jobs::enqueue(conn, "job", "text", &id).unwrap();
        })
        .await
        .unwrap();

    let router = archeaxis_api::runtime::router(executor);
    put(
        &router,
        "/api/v1/capabilities/text.extract/enabled",
        r#"{"enabled":false}"#,
    )
    .await;

    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/jobs/job/executions")
                .header("content-type", "application/json")
                .header("idempotency-key", "key-job")
                .body(Body::from(r#"{"deadline_ms":60000}"#))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let text = String::from_utf8_lossy(&bytes);

    assert_eq!(status, 409, "{text}");
    assert!(text.contains("text.extract"), "{text}");
    assert!(text.contains("disabled"), "{text}");
}

#[tokio::test]
async fn an_unknown_capability_is_a_not_found_rather_than_the_nearest_match() {
    let (_dir, executor) = executor_with(&[]).await;
    let (status, _body) = get(
        &archeaxis_api::runtime::router(executor),
        "/api/v1/capabilities/text",
    )
    .await;

    // `text` is a prefix of `text.extract`; a registry that guesses would be worse than one that
    // admits it does not know.
    assert_eq!(status, 404);
}

#[tokio::test]
async fn the_registry_answers_even_when_no_extra_worker_was_declared() {
    // The contract says the capability paths depend on the runtime router rather than on a
    // declared worker, so a launch that declared none can still be asked what exists. That is the
    // question a broken launch most needs answered, so it is pinned rather than described.
    let (_dir, executor) = executor_with(&[]).await;
    let (status, body) = get(
        &archeaxis_api::runtime::router(executor),
        "/api/v1/capabilities",
    )
    .await;

    assert_eq!(status, 200, "{body}");
    // with nothing declared, the built-in text route is still what the Core serves
    let names: Vec<String> = body["capabilities"]
        .as_array()
        .unwrap()
        .iter()
        .map(|record| record["capability"].as_str().unwrap().to_string())
        .collect();
    assert_eq!(names, vec!["text.extract".to_string()], "{names:?}");
}
