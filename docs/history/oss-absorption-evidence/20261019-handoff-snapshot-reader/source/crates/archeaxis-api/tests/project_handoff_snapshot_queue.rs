//! Owned in-process router/Store queue regression, not launch-token or native qualification.
use archeaxis_store_sqlite::writer::Store;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::{
    future::{Future, poll_fn},
    pin::Pin,
    sync::mpsc,
    task::Poll,
    time::{Duration, Instant},
};
use tower::ServiceExt;

async fn poll_once<F: Future>(mut future: Pin<&mut F>) -> Poll<F::Output> {
    poll_fn(|cx| Poll::Ready(future.as_mut().poll(cx))).await
}

// Assertion failure must release the owned Store callback before Store::drop joins it.
struct ReleaseOnDrop(Option<mpsc::Sender<()>>);
impl ReleaseOnDrop {
    fn release(&mut self) {
        if let Some(sender) = self.0.take() {
            let _ = sender.send(());
        }
    }
}
impl Drop for ReleaseOnDrop {
    fn drop(&mut self) {
        self.release();
    }
}

fn wait_until_expired(expires_at_ms: u64) {
    // Wait for the actual production clock predicate, not an assumed scheduling delay.
    // A fixed outer bound turns a stalled/backwards clock into a test failure.
    let outer = Instant::now() + Duration::from_secs(5);
    let (_sender, receiver) = mpsc::channel::<()>();
    loop {
        let now = archeaxis_api::project_observer::now_ms();
        if now > expires_at_ms {
            return;
        }
        assert!(
            Instant::now() < outer,
            "owned deadline clock did not advance"
        );
        let remaining = Duration::from_millis(expires_at_ms.saturating_sub(now) + 1);
        let budget = remaining.min(outer.saturating_duration_since(Instant::now()));
        assert!(matches!(
            receiver.recv_timeout(budget),
            Err(mpsc::RecvTimeoutError::Timeout)
        ));
    }
}

#[tokio::test]
async fn accepted_snapshot_expires_while_queued_and_returns_no_body_or_writes() {
    let directory = tempfile::tempdir().unwrap();
    let store = Store::open(&directory.path().join("owned.sqlite")).unwrap();
    let (workspace, reference, before_changes) = store
        .submit(|conn| {
            let workspace = archeaxis_domain::ui_state::workspace_id(conn).unwrap();
            let document = archeaxis_domain::document::create_optional(
                conn,
                None,
                None,
                "SYNTHETIC queue-only title",
                json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"SYNTHETIC QUEUED BODY MUST NOT RETURN"}]}]}),
            )
            .unwrap();
            let reference = json!({
                "document_id":document["document_id"],
                "version":document["version"],
                "content_sha256":document["content_sha256"],
            });
            (workspace, reference, conn.total_changes())
        })
        .await
        .unwrap();
    let app = archeaxis_api::router(store.clone());
    let (entered_tx, entered_rx) = mpsc::channel();
    let (release_tx, release_rx) = mpsc::channel();
    let mut release = ReleaseOnDrop(Some(release_tx));
    let mut blocker = Box::pin(store.submit(move |_| {
        entered_tx.send(()).unwrap();
        release_rx
            .recv_timeout(Duration::from_secs(10))
            .expect("owned queue blocker was not released");
    }));
    assert!(poll_once(blocker.as_mut()).await.is_pending());
    entered_rx
        .recv_timeout(Duration::from_secs(2))
        .expect("owned Store callback did not start");

    let created_at_ms = archeaxis_api::project_observer::now_ms();
    let expires_at_ms = created_at_ms + 2_000;
    let proposal = json!({
        "schema":"archeaxis.project-handoff/v1",
        "protocol":"archeaxis.project-observer/v1",
        "idempotency_key":"1".repeat(32),
        "producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},
        "consumer":{"namespace":"work-lab","instance_id":"2".repeat(32)},
        "created_at_ms":created_at_ms,"expires_at_ms":expires_at_ms,
        "authority":"PREPARATION_ONLY",
        "payload":{"kind":"context","source":{"reference":reference,"selection":{"kind":"whole_object"},"selection_qualification":"UNVERIFIED"},"purpose":"research","authorization_scope":"REFERENCE_METADATA_ONLY"},
    });
    let mut request = Box::pin(
        app.oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/project-handoff/snapshot")
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(proposal.to_string()))
                .unwrap(),
        ),
    );
    // With the complete in-memory body and a ready Router, this drives input admission
    // through the Store oneshot wait. HTTP 400 later would fail, not silently count as expiry.
    assert!(poll_once(request.as_mut()).await.is_pending());
    assert!(archeaxis_api::project_observer::now_ms() < expires_at_ms);
    wait_until_expired(expires_at_ms);
    release.release();
    blocker.await.unwrap();
    let response = request.await.unwrap();
    assert_eq!(response.status().as_u16(), 409);
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    let body: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(body["code"], "HANDOFF_SNAPSHOT_EXPIRED");
    assert!(body.get("editor_json").is_none());
    assert!(body.get("reference").is_none());
    assert!(!String::from_utf8_lossy(&bytes).contains("SYNTHETIC QUEUED BODY"));
    assert_eq!(
        store.submit(|conn| conn.total_changes()).await.unwrap(),
        before_changes
    );
}
