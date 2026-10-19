//! Admission 必须在任何下游 handler 前截断；合成 fallthrough 计数是专门负例证据。
use archeaxis_store_sqlite::writer::Store;
use axum::{
    Router,
    body::Body,
    http::{Request, StatusCode},
};
use serde_json::json;
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};
use tower::ServiceExt;
#[tokio::test]
async fn observer_known_reads_and_denied_routes_never_reach_a_mutable_downstream_handler() {
    let dir = tempfile::tempdir().unwrap();
    let store = Store::open(&dir.path().join("admission.sqlite")).unwrap();
    let workspace = store
        .submit(|conn| archeaxis_domain::ui_state::workspace_id(conn))
        .await
        .unwrap()
        .unwrap();
    let calls = Arc::new(AtomicUsize::new(0));
    let captured = calls.clone();
    let downstream = Router::new().fallback(move || {
        let calls = captured.clone();
        async move {
            calls.fetch_add(1, Ordering::SeqCst);
            StatusCode::ACCEPTED
        }
    });
    let launch:archeaxis_api::launch::Launch=serde_json::from_value(json!({"protocol":"archeaxis.desktop-launch/v3","actor":"human","launch_token":"a".repeat(64),"machine_token":"b".repeat(64),"session_id":"c".repeat(32),"observer_grants":[{"token":"d".repeat(64),"consumer":{"namespace":"work-lab","instance_id":"e".repeat(32)},"producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},"expires_at_ms":archeaxis_api::project_observer::now_ms()+60_000,"document_ids":["doc_1"]}]})).unwrap();
    let router = archeaxis_api::launch::protect(downstream, &store, launch)
        .await
        .unwrap();
    let request = |token: &str, method: &str, path: &str| {
        Request::builder()
            .method(method)
            .uri(path)
            .header("x-archeaxis-launch-token", token)
            .header(
                "x-archeaxis-observer-protocol",
                "archeaxis.project-observer/v1",
            )
            .header("x-archeaxis-observer-namespace", "work-lab")
            .header("x-archeaxis-observer-instance", "e".repeat(32))
            .body(Body::empty())
            .unwrap()
    };
    assert_eq!(
        router
            .clone()
            .oneshot(request(&"a".repeat(64), "POST", "/synthetic-downstream"))
            .await
            .unwrap()
            .status(),
        StatusCode::ACCEPTED
    );
    assert_eq!(
        calls.load(Ordering::SeqCst),
        1,
        "positive control must actually reach downstream"
    );
    assert_eq!(
        router
            .clone()
            .oneshot(request(
                &"d".repeat(64),
                "GET",
                "/api/v1/project-observer/handshake"
            ))
            .await
            .unwrap()
            .status(),
        StatusCode::OK
    );
    for (method, path) in [
        ("GET", "/api/v1/system/version"),
        ("GET", "/synthetic-downstream"),
        ("POST", "/api/v1/jobs/job_1/execute"),
        ("POST", "/api/v1/conversation/requests"),
        ("POST", "/api/v1/project-observer/handshake"),
    ] {
        assert_eq!(
            router
                .clone()
                .oneshot(request(&"d".repeat(64), method, path))
                .await
                .unwrap()
                .status(),
            StatusCode::FORBIDDEN
        );
    }
    assert_eq!(
        calls.load(Ordering::SeqCst),
        1,
        "observer request reached a downstream handler"
    );
}
