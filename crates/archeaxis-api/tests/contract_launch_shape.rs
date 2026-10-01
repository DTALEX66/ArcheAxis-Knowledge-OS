//! The contract's launch-shape claim: no `text_worker` means projection routes only.
//!
//! §6 tells the UI that a launch **without** a `text_worker` serves the projection routes and
//! that `/jobs/{id}`, `/executions`, `/outputs` and `/cancel` are **absent**, answering `404`;
//! a launch **with** one serves all of them. That difference decides what the UI can do, and it
//! had only ever been read out of the source, so it is driven here.
//!
//! The distinction that makes this checkable is that an absent route and a route with no such
//! object both answer `404`. Asking the same path with the wrong method separates them: a
//! mounted path answers `405 Method Not Allowed`, an absent one answers `404`. Without that,
//! "the route is missing" and "the job does not exist" are indistinguishable, and a UI could be
//! built on the wrong one.
//!
//! Verified against the real binary first, by starting it both ways and asking over HTTP:
//! without a worker all four paths answered `404` to both methods, with one they answered `405`
//! to the wrong method. This test drives the same two routers in process.

use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use std::path::PathBuf;
use tower::ServiceExt;

async fn executor(dir: &std::path::Path) -> Executor {
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    Executor::open(
        &dir.join("db.sqlite"),
        &dir.join("staging"),
        &python,
        &script,
    )
    .await
    .unwrap()
}

async fn status(router: &Router, method: &str, path: &str) -> u16 {
    router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap()
        .status()
        .as_u16()
}

/// The runtime routes §6 says are absent from a worker-less launch, each with the method that
/// exists when a worker is present and a method that does not.
const RUNTIME_PATHS: &[(&str, &str, &str)] = &[
    ("GET", "DELETE", "/api/v1/jobs/absent"),
    ("POST", "GET", "/api/v1/jobs/absent/executions"),
    ("GET", "DELETE", "/api/v1/jobs/absent/outputs/text"),
    (
        "POST",
        "GET",
        "/api/v1/jobs/absent/executions/absent/cancel",
    ),
];

const PROJECTION_PATHS: &[&str] = &[
    "/api/v1/system/version",
    "/api/v1/workspaces/info",
    "/api/v1/evidence/anchors",
];

#[tokio::test]
async fn a_worker_less_launch_has_no_runtime_routes_at_all() {
    let dir = tempfile::tempdir().unwrap();
    let store = executor(dir.path()).await.store().clone();
    // `projections(.., false)` is exactly what main.rs builds when the launch carries no
    // text_worker: the legacy manual-receipts mount stays off too.
    let router = archeaxis_api::projections(store, false);

    for (method, other_method, path) in RUNTIME_PATHS {
        assert_eq!(
            status(&router, method, path).await,
            404,
            "{method} {path} must be absent, not merely empty"
        );
        assert_eq!(
            status(&router, other_method, path).await,
            404,
            "{other_method} {path} must also be 404, which is what proves the path is unmounted"
        );
    }
}

#[tokio::test]
async fn a_worker_less_launch_still_serves_the_projection_routes() {
    let dir = tempfile::tempdir().unwrap();
    let store = executor(dir.path()).await.store().clone();
    let router = archeaxis_api::projections(store, false);

    for path in PROJECTION_PATHS {
        assert_eq!(
            status(&router, "GET", path).await,
            200,
            "{path} is a projection route and must stay available without a worker"
        );
    }
}

#[tokio::test]
async fn a_launch_with_a_worker_mounts_the_runtime_routes() {
    let dir = tempfile::tempdir().unwrap();
    let executor = executor(dir.path()).await;
    let router = archeaxis_api::runtime::router(executor);

    for (_method, other_method, path) in RUNTIME_PATHS {
        // 405 is the signal: the path is mounted and only the method is wrong. A 404 here
        // would mean the route is missing, which is what the UI must be able to tell apart.
        assert_eq!(
            status(&router, other_method, path).await,
            405,
            "{other_method} {path} must answer 405, proving the route is mounted"
        );
    }

    // and with the correct method the answer is about the job, not about the route. A 404 here
    // is the honest "no such job"; the 405 above is what proves the route itself is mounted.
    for (method, _other, path) in RUNTIME_PATHS {
        let code = status(&router, method, path).await;
        assert!(
            (200..500).contains(&code),
            "{method} {path} answered {code}"
        );
    }
}

#[tokio::test]
async fn both_shapes_serve_the_same_projection_routes() {
    let dir = tempfile::tempdir().unwrap();
    let executor = executor(dir.path()).await;
    let store = executor.store().clone();
    let with_worker = archeaxis_api::runtime::router(executor);
    let without_worker = archeaxis_api::projections(store, false);

    for path in PROJECTION_PATHS {
        assert_eq!(
            status(&with_worker, "GET", path).await,
            200,
            "{path} with a worker"
        );
        assert_eq!(
            status(&without_worker, "GET", path).await,
            200,
            "{path} without one"
        );
    }
}

#[tokio::test]
async fn the_manual_receipts_mount_stays_off_in_the_shipped_shape() {
    // §6 states this explicitly, and it is the one route in this file that a reader might
    // expect to be present because it is mounted in the source under a condition.
    let dir = tempfile::tempdir().unwrap();
    let executor = executor(dir.path()).await;
    let store = executor.store().clone();
    let router = archeaxis_api::projections(store, false);
    assert_eq!(
        status(&router, "POST", "/api/v1/jobs/absent/receipts").await,
        404,
        "the shipped binary never mounts manual receipts"
    );
}

#[tokio::test]
async fn the_two_shapes_differ_by_exactly_the_runtime_routes() {
    // A reader's summary of §6, as an assertion. The mounting signal is the wrong-method probe,
    // because the correct method answers 404 for a job that does not exist in both shapes - so
    // comparing the correct-method answers would not say whether a route is there at all.
    let dir = tempfile::tempdir().unwrap();
    let executor = executor(dir.path()).await;
    let store = executor.store().clone();
    let with_worker = archeaxis_api::runtime::router(executor);
    let without_worker = archeaxis_api::projections(store, false);

    let mut differing = 0;
    for (_method, other_method, path) in RUNTIME_PATHS {
        let present = status(&with_worker, other_method, path).await;
        let absent = status(&without_worker, other_method, path).await;
        assert_eq!(
            present, 405,
            "{other_method} {path} is mounted with a worker"
        );
        assert_eq!(
            absent, 404,
            "{other_method} {path} is unmounted without one"
        );
        assert_ne!(
            present, absent,
            "{other_method} {path} must differ between the shapes"
        );
        differing += 1;
    }
    assert_eq!(differing, 4, "§6 names four runtime routes");
}
