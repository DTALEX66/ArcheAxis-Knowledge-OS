//! New in-flight regression only: real Core/SQLite and pinned workers, synthetic held model.
//! No user material, external network, model quality claim or older journey replay.
use archeaxis_application::executor::Executor;
use archeaxis_domain::document;
use archeaxis_store_sqlite::init_workspace;
use axum::{
    Router,
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::{TcpListener, TcpStream},
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicUsize, Ordering},
    },
    thread,
    time::{Duration, Instant},
};
use tower::ServiceExt;

struct HeldModel {
    port: u16,
    calls: Arc<AtomicUsize>,
    release: Arc<AtomicBool>,
    stop: Arc<AtomicBool>,
    owner: Option<thread::JoinHandle<()>>,
}
impl HeldModel {
    fn new() -> Self {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        listener.set_nonblocking(true).unwrap();
        let port = listener.local_addr().unwrap().port();
        let calls = Arc::new(AtomicUsize::new(0));
        let release = Arc::new(AtomicBool::new(false));
        let stop = Arc::new(AtomicBool::new(false));
        let (counted, allowed, ending) = (calls.clone(), release.clone(), stop.clone());
        let owner = thread::spawn(move || {
            let mut children = Vec::new();
            while !ending.load(Ordering::SeqCst) {
                match listener.accept() {
                    Ok((mut socket, _)) => {
                        let (counted, allowed, ending) =
                            (counted.clone(), allowed.clone(), ending.clone());
                        children.push(thread::spawn(move || {
                            socket.set_nonblocking(false).unwrap();socket.set_read_timeout(Some(Duration::from_secs(5))).unwrap();socket.set_write_timeout(Some(Duration::from_secs(5))).unwrap();
                            let mut reader=BufReader::new(socket.try_clone().unwrap());let mut length=0usize;
                            loop { let mut line=String::new();if reader.read_line(&mut line).unwrap_or(0)==0{return;}if line.trim().is_empty(){break;}
                                if let Some(value)=line.to_ascii_lowercase().strip_prefix("content-length:"){length=value.trim().parse::<usize>().unwrap_or(0).min(1<<20);}}
                            let mut bytes=vec![0;length];if reader.read_exact(&mut bytes).is_err(){return;}
                            counted.fetch_add(1,Ordering::SeqCst);
                            let until=Instant::now()+Duration::from_secs(30);
                            while !allowed.load(Ordering::SeqCst)&&!ending.load(Ordering::SeqCst)&&Instant::now()<until {thread::sleep(Duration::from_millis(5));}
                            let question=json!({"question_type":"choice","question":"Synthetic 2+2?","options":{"A":"3","B":"4","C":"5","D":"6"},"correct_answer":"B","explanation":"Synthetic only"}).to_string();
                            let payload=json!({"model":"synthetic-claim-model","choices":[{"index":0,"finish_reason":"stop","message":{"role":"assistant","content":question}}],"usage":{"prompt_tokens":3,"completion_tokens":4}}).to_string();
                            let _=write!(socket,"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",payload.len(),payload);
                        }));
                    }
                    Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                        thread::sleep(Duration::from_millis(5))
                    }
                    Err(_) => break,
                }
            }
            for child in children {
                child.join().unwrap();
            }
        });
        Self {
            port,
            calls,
            release,
            stop,
            owner: Some(owner),
        }
    }
    async fn entered(&self, count: usize) {
        tokio::time::timeout(Duration::from_secs(25), async {
            while self.calls.load(Ordering::SeqCst) < count {
                tokio::time::sleep(Duration::from_millis(10)).await;
            }
        })
        .await
        .expect("pinned worker must reach synthetic model; absence is not a pass");
    }
}
impl Drop for HeldModel {
    fn drop(&mut self) {
        self.release.store(true, Ordering::SeqCst);
        self.stop.store(true, Ordering::SeqCst);
        let _ = TcpStream::connect(("127.0.0.1", self.port));
        if let Some(owner) = self.owner.take() {
            owner.join().unwrap();
        }
    }
}
async fn call(router: Router, body: Value) -> (StatusCode, Value) {
    let response = router
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/learning/deeptutor/question-turn")
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap())
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn new_question_claim_blocks_inflight_repeat_without_blocking_saves_and_keeps_cancel_unknown()
{
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_owned();
    let python = root.join(".venv/Scripts/python.exe");
    assert!(
        python.is_file(),
        "new runtime regression requires the existing pinned local environment"
    );
    let model = HeldModel::new();
    // One test in this isolated binary: variables are scoped to the synthetic worker fixture.
    unsafe {
        std::env::set_var(
            "ARCHEAXIS_MACHINE_ENDPOINT",
            format!("http://127.0.0.1:{}/v1", model.port),
        );
        std::env::set_var("ARCHEAXIS_MACHINE_MODEL", "synthetic-claim-model");
        std::env::set_var("ARCHEAXIS_MACHINE_PROTOCOL", "openai");
    }
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let material=document::create_optional(&mut conn,None,None,"Synthetic claim material",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic arithmetic only"}]}]})).unwrap();
    let snapshot = json!({"document_id":material["document_id"],"version":material["version"],"content_sha256":material["content_sha256"]});
    document::create_optional(&mut conn,None,None,"Synthetic grant",json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snapshot,"authorization_basis":"Synthetic explicit authorization","expires_at":null,"state":"granted"}}})).unwrap();
    drop(conn);
    let executor = Executor::open_routes(
        &path,
        &dir.path().join("staging"),
        &python,
        &root.join("services/python-workers/transport/text_ndjson.py"),
        &[
            (
                "deeptutor.practice.import",
                root.join("services/learning-providers/deeptutor/practice_host_worker.py"),
            ),
            (
                "course.openmaic.outline-model",
                root.join("services/python-workers/course/worker_outline_local_model.py"),
            ),
        ],
    )
    .await
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"create_request_id":"synthetic_concurrent_claim","material":snapshot,"requirement":"Synthetic arithmetic question","model":null});
    let first = tokio::spawn(call(router.clone(), body.clone()));
    model.entered(1).await;
    let repeated =
        tokio::time::timeout(Duration::from_secs(2), call(router.clone(), body.clone())).await;
    let ordinary = tokio::time::timeout(
        Duration::from_secs(2),
        executor.store().submit_wait(|conn| {
            document::create_optional(
                conn,
                None,
                None,
                "Ordinary save during held inference",
                json!({"type":"doc","content":[]}),
            )
        }),
    )
    .await;
    model.release.store(true, Ordering::SeqCst);
    let first = tokio::time::timeout(Duration::from_secs(20), first)
        .await
        .unwrap()
        .unwrap();
    assert!(
        ordinary.is_ok_and(|saved| saved.is_ok_and(|result| result.is_ok())),
        "ordinary writer must not be held across inference"
    );
    assert_eq!(first.0, StatusCode::CREATED, "{}", first.1);
    assert!(
        repeated.is_ok(),
        "same in-flight create ID must refuse promptly before a second model dispatch"
    );
    let duplicate = repeated.unwrap();
    assert_eq!(duplicate.0, StatusCode::CONFLICT, "{}", duplicate.1);
    assert_eq!(duplicate.1["retryable"], false);
    let completed = call(router.clone(), body.clone()).await;
    assert_eq!(completed.0, StatusCode::OK);
    assert_eq!(completed.1["worker_invoked"], false);
    assert_eq!(model.calls.load(Ordering::SeqCst), 1);

    model.release.store(false, Ordering::SeqCst);
    let mut cancelled = body;
    cancelled["create_request_id"] = json!("synthetic_cancelled_claim");
    let unfinished = tokio::spawn(call(router.clone(), cancelled.clone()));
    model.entered(2).await;
    unfinished.abort();
    let _ = unfinished.await;
    let repeated = tokio::time::timeout(
        Duration::from_secs(2),
        call(router.clone(), cancelled.clone()),
    )
    .await;
    model.release.store(true, Ordering::SeqCst);
    assert!(
        repeated.is_ok(),
        "cancelled request must retain its barrier"
    );
    let repeated = repeated.unwrap();
    assert_eq!(repeated.0, StatusCode::CONFLICT);
    assert_eq!(repeated.1["retryable"], false);
    let id = archeaxis_domain::provider_question_turn::question_turn_document_id(
        "synthetic_cancelled_claim",
    );
    let exists = executor
        .store()
        .submit_wait(move |conn| document::read(conn, &id, None).is_ok())
        .await
        .unwrap();
    assert!(!exists, "aborted HTTP cannot publish a late result");
    assert_eq!(
        model.calls.load(Ordering::SeqCst),
        2,
        "no model redispatch after unknown completion"
    );
}
