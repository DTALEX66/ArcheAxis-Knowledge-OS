//! The route families a UI must not try, because they do not exist, and the shape of what comes
//! back when something is missing.
//!
//! `docs/current/DSH-BACKEND-CONTRACT-20260927.md` §6 states that `/api/v1/research*`,
//! `/api/v1/plugins*` and `/api/v1/models*` have no route, and that a frontend must show "not
//! connected" rather than any success state. That is the strongest kind of claim a contract can
//! make about an API, and it is the kind a UI otherwise discovers at runtime - so it is checked
//! here.
//!
//! "Does not exist" has to be told apart from "exists but has no such object", and both answer
//! `404`. The separating probe is the wrong method: a mounted path answers `405 Method Not
//! Allowed` for a method it does not serve, an unmounted one answers `404`. `DELETE` is the probe
//! method because no route in this API serves it, so a `405` would mean the path is mounted.
//!
//! Measuring this also turned up something the branch contract had described wrongly: error
//! bodies are **not** uniform JSON. Across one representative error per family, nine of eleven
//! were plain text and two had no body at all - only the auth middleware's `401`/`403` are JSON.
//! A client that unconditionally parses JSON fails on almost every error this API returns, so the
//! shapes are asserted here too.

use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use std::path::PathBuf;
use tower::ServiceExt;

async fn router() -> (tempfile::TempDir, Router) {
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
    // The runtime router is the larger of the two surfaces, so a path absent here is absent from
    // the shipped binary's superset as well.
    (dir, archeaxis_api::runtime::router(executor))
}

/// The raw body as text plus the parsed JSON, because most error bodies here are **not** JSON and
/// a helper that parsed eagerly would hide the thing under test.
struct Answer {
    status: u16,
    text: String,
    json: serde_json::Value,
    content_type: Option<String>,
}

impl Answer {
    /// True only if the body parses as JSON, which is what a client would discover.
    fn parses_as_json(&self) -> bool {
        serde_json::from_str::<serde_json::Value>(&self.text).is_ok()
    }
}

async fn ask(router: &Router, method: &str, path: &str, body: Option<serde_json::Value>) -> Answer {
    let mut builder = Request::builder().method(method).uri(path);
    let request = match body {
        Some(value) => {
            builder = builder.header("content-type", "application/json");
            builder.body(Body::from(value.to_string())).unwrap()
        }
        None => builder.body(Body::empty()).unwrap(),
    };
    let resp = router.clone().oneshot(request).await.unwrap();
    let status = resp.status().as_u16();
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|value| value.to_str().ok())
        .map(str::to_owned);
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let text = String::from_utf8_lossy(&bytes).into_owned();
    let json = serde_json::from_str(&text).unwrap_or(serde_json::Value::Null);
    Answer {
        status,
        text,
        json,
        content_type,
    }
}

/// Every family `DSH §6` says has no route, with the method a UI would reach for.
const ABSENT: &[(&str, &str)] = &[
    ("GET", "/api/v1/research"),
    ("POST", "/api/v1/research"),
    ("GET", "/api/v1/research/tasks"),
    ("GET", "/api/v1/plugins"),
    ("POST", "/api/v1/plugins"),
    ("GET", "/api/v1/models"),
    ("POST", "/api/v1/models"),
    ("GET", "/api/v1/models/providers"),
    ("GET", "/api/v1/embeddings/search"),
    ("GET", "/api/v1/graph/search"),
];

#[tokio::test]
async fn the_absent_families_answer_404_to_their_own_method() {
    let (_dir, router) = router().await;
    for (method, path) in ABSENT {
        let answer = ask(&router, method, path, None).await;
        assert_eq!(
            answer.status, 404,
            "{method} {path} must not exist: {}",
            answer.text
        );
    }
}

#[tokio::test]
async fn and_404_to_a_wrong_method_which_is_what_proves_they_are_unmounted() {
    let (_dir, router) = router().await;
    for (_method, path) in ABSENT {
        // No route in this API serves DELETE, so this separates "unmounted" (404) from
        // "mounted but wrong method" (405).
        let answer = ask(&router, "DELETE", path, None).await;
        assert_eq!(
            answer.status, 404,
            "DELETE {path} answered {}; a 405 would mean the path IS mounted",
            answer.status
        );
    }
}

#[tokio::test]
async fn the_probe_distinguishes_mounted_paths() {
    // The control for the check above. If a mounted route did not answer 405, the absence claim
    // would pass for the wrong reason - the probe would be measuring nothing.
    let (_dir, router) = router().await;
    for path in [
        "/api/v1/search",
        "/api/v1/system/version",
        "/api/v1/learning/items",
    ] {
        let answer = ask(&router, "DELETE", path, None).await;
        assert_eq!(
            answer.status, 405,
            "DELETE {path} must be 405, proving the probe separates mounted from absent"
        );
    }
}

#[tokio::test]
async fn the_router_under_test_actually_serves_something() {
    let (_dir, router) = router().await;
    let answer = ask(&router, "GET", "/api/v1/system/version", None).await;
    assert_eq!(answer.status, 200, "{}", answer.text);
}

#[tokio::test]
async fn the_quality_route_is_a_summary_projection_and_not_a_loss_receipt() {
    let (_dir, router) = router().await;
    let answer = ask(&router, "GET", "/api/v1/jobs/absent-job/quality", None).await;
    assert_eq!(
        answer.status, 404,
        "an unknown job is a named 404: {}",
        answer.text
    );
    assert_eq!(
        answer.text, "unknown job",
        "the body is that plain string, so a UI must not parse a typed receipt out of it"
    );
    assert!(
        !answer.parses_as_json(),
        "the body is not JSON: {}",
        answer.text
    );
}

#[tokio::test]
async fn the_job_routes_answer_json_for_a_family_that_does_not_exist() {
    // Measured, and it corrected this test's own first draft: an earlier probe of the same routes
    // reported an empty body, which the live router contradicts. These two routes answer a JSON
    // envelope like the auth errors do, so the "not uniform" claim has a JSON group larger than
    // the auth middleware alone.
    let (_dir, router) = router().await;

    let answer = ask(&router, "GET", "/api/v1/jobs/absent-job", None).await;
    assert_eq!(answer.status, 404, "{}", answer.text);
    assert!(answer.parses_as_json(), "this one IS JSON: {}", answer.text);
    assert_eq!(answer.json["code"], "AAK-VAL-004", "{}", answer.text);
    assert_eq!(answer.json["message"], "job not found", "{}", answer.text);

    let answer = ask(&router, "GET", "/api/v1/jobs/absent-job/outputs/text", None).await;
    assert_eq!(answer.status, 404, "{}", answer.text);
    assert!(
        answer.parses_as_json(),
        "this one IS JSON too: {}",
        answer.text
    );
    assert_eq!(answer.json["code"], "AAK-VAL-004", "{}", answer.text);
}

#[tokio::test]
async fn error_bodies_are_plain_text_except_for_a_named_json_group() {
    // Measured across route families. The groups are not what a reader would guess: the auth
    // middleware and the two job routes answer JSON, and everything else answers plain text.
    let (_dir, router) = router().await;

    for (path, expected) in [
        ("/api/v1/sources/absent/members", "source not found"),
        ("/api/v1/knowledge-items/absent/v3", "knowledge not found"),
        ("/api/v1/machine/tasks/absent", "unknown machine task"),
        ("/api/v1/jobs/absent-job/quality", "unknown job"),
    ] {
        let answer = ask(&router, "GET", path, None).await;
        assert_eq!(answer.status, 404, "{path}: {}", answer.text);
        assert_eq!(answer.text, expected, "{path} must answer plain text");
        assert!(!answer.parses_as_json(), "{path} is plain text, not JSON");
    }

    let answer = ask(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        Some(serde_json::json!({"knowledge_type": "NOPE", "body": "x"})),
    )
    .await;
    assert_eq!(answer.status, 400, "{}", answer.text);
    assert!(
        answer.text.starts_with("Invalid parameter name:"),
        "a validation failure is plain text with a reason: {:?}",
        answer.text
    );
}

#[tokio::test]
async fn search_is_lexical_and_an_empty_result_is_a_success() {
    let (_dir, router) = router().await;
    let answer = ask(&router, "GET", "/api/v1/search?q=zzzz-no-such-term", None).await;
    assert_eq!(
        answer.status, 200,
        "a miss is a successful empty result: {}",
        answer.text
    );
    assert_eq!(answer.json["count"], 0, "{}", answer.text);
    assert_eq!(
        answer.json["items"].as_array().map(Vec::len),
        Some(0),
        "an empty result carries an empty list, not a null: {}",
        answer.text
    );
}
