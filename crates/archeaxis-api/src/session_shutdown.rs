//! Fixed native session control. Never changes bootstrap stdin or cancels work.
use axum::{
    Json, Router,
    extract::{Request, State},
    http::{HeaderMap, StatusCode},
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::post,
};
use serde::Deserialize;
use serde_json::json;
use tokio::sync::watch;

#[derive(Clone)]
struct Control {
    session_id: String,
    closing: watch::Sender<bool>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Body {
    session_id: String,
}

/// Install before launch::protect, so role headers are already authenticated.
/// The receiver is only a stop-admission signal, not a successful-exit receipt.
pub fn install(router: Router, session_id: String) -> (Router, watch::Receiver<bool>) {
    let (closing, receiver) = watch::channel(false);
    let control = Control {
        session_id,
        closing,
    };
    let router = router
        .merge(
            Router::new()
                .route("/api/v1/system/shutdown", post(request))
                .with_state(control.clone()),
        )
        .layer(middleware::from_fn_with_state(control, admission));
    (router, receiver)
}
async fn admission(State(control): State<Control>, request: Request, next: Next) -> Response {
    if *control.closing.borrow() {
        return (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({"code":"AAK-SESSION-CLOSING","retryable":false})),
        )
            .into_response();
    }
    next.run(request).await
}
async fn request(
    State(control): State<Control>,
    headers: HeaderMap,
    Json(body): Json<Body>,
) -> Response {
    if headers
        .get("x-archeaxis-actor")
        .and_then(|v| v.to_str().ok())
        != Some("human")
    {
        return StatusCode::FORBIDDEN.into_response();
    }
    if body.session_id != control.session_id {
        return StatusCode::CONFLICT.into_response();
    }
    // Axum graceful shutdown drains this response and other already admitted HTTP
    // requests. main then joins the single writer after background owners release it.
    control.closing.send_replace(true);
    (StatusCode::ACCEPTED, Json(json!({"schema":"archeaxis.session-shutdown/v1","session_id":control.session_id,"state":"draining"}))).into_response()
}

#[cfg(test)]
mod tests {
    use super::*;
    use archeaxis_store_sqlite::writer::Store;
    use axum::body::Body as HttpBody;
    use tower::ServiceExt;

    #[tokio::test]
    async fn credentials_identity_and_closing_gate_precede_mutations() {
        let dir = tempfile::tempdir().unwrap();
        let store = Store::open(&dir.path().join("session.sqlite")).unwrap();
        let workspace = store
            .submit(|c| archeaxis_domain::ui_state::workspace_id(c))
            .await
            .unwrap()
            .unwrap();
        let session = "c".repeat(32);
        let launch:crate::launch::Launch=serde_json::from_value(json!({"protocol":"archeaxis.desktop-launch/v3","actor":"human","launch_token":"a".repeat(64),"machine_token":"b".repeat(64),"session_id":session,"observer_grants":[{"token":"d".repeat(64),"consumer":{"namespace":"work-lab","instance_id":"e".repeat(32)},"producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},"expires_at_ms":crate::project_observer::now_ms()+60000,"document_ids":["doc_1"]}]})).unwrap();
        let (router, closing) = install(crate::projections(store.clone(), false), session.clone());
        let router = crate::launch::protect(router, &store, launch)
            .await
            .unwrap();
        let req = |token: String, path: &str, body: serde_json::Value| {
            Request::builder()
                .method("POST")
                .uri(path)
                .header("x-archeaxis-launch-token", token)
                .header("x-archeaxis-actor", "human")
                .header("content-type", "application/json")
                .body(HttpBody::from(body.to_string()))
                .unwrap()
        };
        for (token, expected) in [
            ("bad".into(), 401),
            ("b".repeat(64), 403),
            ("d".repeat(64), 403),
        ] {
            assert_eq!(
                router
                    .clone()
                    .oneshot(req(
                        token,
                        "/api/v1/system/shutdown",
                        json!({"session_id":session})
                    ))
                    .await
                    .unwrap()
                    .status()
                    .as_u16(),
                expected
            );
            assert!(!*closing.borrow());
        }
        for (body, expected) in [
            (json!({"session_id":"f".repeat(32)}), 409),
            (json!({"session_id":session,"force":true}), 422),
        ] {
            assert_eq!(
                router
                    .clone()
                    .oneshot(req("a".repeat(64), "/api/v1/system/shutdown", body))
                    .await
                    .unwrap()
                    .status()
                    .as_u16(),
                expected
            );
            assert!(!*closing.borrow());
        }
        assert_eq!(
            router
                .clone()
                .oneshot(req(
                    "a".repeat(64),
                    "/api/v1/system/shutdown",
                    json!({"session_id":session})
                ))
                .await
                .unwrap()
                .status(),
            StatusCode::ACCEPTED
        );
        assert!(*closing.borrow());
        assert_eq!(router.clone().oneshot(req("a".repeat(64),"/api/v1/documents",json!({"create_request_id":"too-late","title":"must not save","editor_json":{"type":"doc","content":[]}}))).await.unwrap().status(),StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(
            store
                .submit(|c| c
                    .query_row("SELECT count(*) FROM documents", [], |r| r.get::<_, i64>(0))
                    .unwrap())
                .await
                .unwrap(),
            0
        );
        drop(router);
        store.close().await.unwrap();
    }
}
