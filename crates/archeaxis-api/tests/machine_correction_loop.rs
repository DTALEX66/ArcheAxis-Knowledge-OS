//! C06: machine error -> candidate correction -> human modified review (new
//! version supersedes) -> machine re-call sees only the corrected current
//! version; durable across a store reopen (restart consistency). Machines can
//! propose candidates and read qualification but cannot run any human review
//! action, including "modified".

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

use archeaxis_api::app;

async fn call(router: &axum::Router, method: &str, path: &str, actor: Option<&str>, body: &str) -> (StatusCode, String) {
    let mut req = Request::builder().method(method).uri(path).header("content-type", "application/json");
    if let Some(a) = actor {
        req = req.header("x-archeaxis-actor", a);
    }
    let resp = router.clone().oneshot(req.body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8_lossy(&bytes).to_string())
}

async fn search(router: &axum::Router, q: &str, active_only: bool) -> Value {
    let path = if active_only {
        format!("/api/v1/search?q={q}&active_only=true")
    } else {
        format!("/api/v1/search?q={q}")
    };
    let resp = router.clone().oneshot(Request::get(path).body(Body::empty()).unwrap()).await.unwrap();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap_or(Value::Null)
}

fn id_of(text: &str) -> String {
    serde_json::from_str::<Value>(text).unwrap()["knowledge_id"].as_str().unwrap().to_string()
}

fn active_ids(v: &Value) -> Vec<String> {
    v["items"]
        .as_array()
        .map(|items| {
            items
                .iter()
                .filter(|it| it["active"] == true)
                .filter_map(|it| it["knowledge_id"].as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default()
}

#[tokio::test]
async fn machine_correction_loop_requalifies_and_survives_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("api.sqlite");
    let db_str = db.to_str().unwrap().to_string();
    let marker = "lpmark1";

    // 1. A current fact is accepted by a human.
    let router = app(&db_str).unwrap();
    let (s, body) = call(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        None,
        &format!(r#"{{"knowledge_type":"FACTUAL_CLAIM","body":"{marker} v1 fact alpha","status":"accepted","created_by":"owner"}}"#),
    )
    .await;
    assert_eq!(s, StatusCode::CREATED, "human accept failed: {body}");
    let id_a = id_of(&body);

    // 2. A machine consumer reads the current fact (qualification gate).
    let v = search(&router, marker, true).await;
    assert_eq!(active_ids(&v), vec![id_a.clone()], "machine should see the accepted fact as the only active unit");

    // 3. Machine discovers an error and proposes a corrected candidate.
    let (s, body) = call(
        &router,
        "POST",
        "/api/v1/knowledge-items",
        Some("machine"),
        &format!(r#"{{"knowledge_type":"FACTUAL_CLAIM","body":"{marker} v2 machine correction","status":"candidate","created_by":"python-worker"}}"#),
    )
    .await;
    assert_eq!(s, StatusCode::CREATED, "machine candidate rejected: {body}");
    let id_b = id_of(&body);

    // 4. Machine cannot itself turn that correction into a review action.
    let (s, _) = call(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{id_a}/review-decisions"),
        Some("machine"),
        &format!(r#"{{"action":"modified","reviewer":"python-worker","new_body":"{marker} forged revision"}}"#),
    )
    .await;
    assert_eq!(s, StatusCode::FORBIDDEN, "machine must not run a modified review");

    // 5. Human review applies the corrected content as a new superseding version.
    let (s, body) = call(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{id_a}/review-decisions"),
        None,
        &format!(r#"{{"action":"modified","reviewer":"owner","note":"human applied the machine proposal","new_body":"{marker} v3 reviewed correction"}}"#),
    )
    .await;
    assert_eq!(s, StatusCode::OK, "modified review failed: {body}");
    let id_c = id_of(&body);
    assert_ne!(id_a, id_c, "modified review must create a successor id");
    assert_ne!(id_b, id_c, "successor id must not collide with the machine candidate");

    let (s, _) = call(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{id_c}/review-decisions"),
        None,
        r#"{"action":"accepted","reviewer":"owner"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::OK, "accepting the successor failed");

    // The machine proposal was consumed by the adopted correction: the human
    // deprecates it so it no longer masquerades as a current unit. (Candidates
    // remain a legal assumption path until then, per C06.)
    let (s, _) = call(
        &router,
        "POST",
        &format!("/api/v1/knowledge-items/{id_b}/review-decisions"),
        None,
        r#"{"action":"deprecated","reviewer":"owner","note":"adopted via corrected version"}"#,
    )
    .await;
    assert_eq!(s, StatusCode::OK, "deprecating the consumed proposal failed");

    // 6. Machine re-call: only the corrected version is current/active.
    let v = search(&router, marker, true).await;
    assert_eq!(active_ids(&v), vec![id_c.clone()], "machine must now see only the corrected version as active");
    let v_all = search(&router, marker, false).await;
    assert_eq!(v_all["items"].as_array().unwrap().len(), 3, "old, candidate and successor all still searchable");
    let old = v_all["items"].as_array().unwrap().iter().find(|it| it["knowledge_id"] == id_a).unwrap();
    assert_eq!(old["active"], false, "superseded original must not be current context");

    // 7. Restart: reopen the same database file; the corrected version stays current.
    drop(router);
    let router2 = app(&db_str).unwrap();
    let v2 = search(&router2, marker, true).await;
    assert_eq!(active_ids(&v2), vec![id_c.clone()], "after restart the corrected version must still be the only active unit");
    let resp = router2
        .clone()
        .oneshot(Request::get(format!("/api/v1/knowledge-items/{id_a}/qualification")).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let q: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(q["active"], false, "superseded original stays inactive after restart");
}
