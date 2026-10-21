//! Real Core/Store/owned-process protocol with synthetic public providers.
//! No network and no knowledge admission is represented by these tests.
use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::{Duration, Instant},
};
use tower::ServiceExt;

async fn call(router: &Router, path: &str, body: Value, actor: &str) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = axum::body::to_bytes(response.into_body(), 1_100_000)
        .await
        .unwrap();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}
async fn open(root: &Path, script: &str) -> Executor {
    let worker = root.join("public.py");
    std::fs::write(&worker, script).unwrap();
    let python = PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    Executor::open_routes(
        &root.join("workspace.sqlite"),
        &root.join("staging"),
        &python,
        &worker,
        &[("research.public", worker.clone())],
    )
    .await
    .unwrap()
}
async fn request(ex: &Executor, id: &str) -> Value {
    let state = ex
        .store()
        .submit_wait(|conn| archeaxis_domain::ui_state::read(conn))
        .await
        .unwrap()
        .unwrap();
    json!({"request_id":id,"workspace_id":state["workspace_id"],"restore_epoch":state["restore_epoch"],
        "query":"spaced repetition","families":["community"],"limit":1})
}
fn target(request: &Value) -> Value {
    json!({"request_id":request["request_id"],"workspace_id":request["workspace_id"],"restore_epoch":request["restore_epoch"]})
}
fn script(wait: bool) -> String {
    format!(
        r#"import json,sys,time,base64
from pathlib import Path
p=Path(__file__)
count=p.with_suffix('.calls')
count.write_text(str(int(count.read_text())+1) if count.exists() else '1')
r=json.load(sys.stdin)
assert set(r)=={{'schema','query','families','limit'}}
assert r['query']=='spaced repetition'
p.with_suffix('.ready').touch()
{}
when='2026-10-21T00:00:00Z'
hit={{'id':'stackexchange:academia:question:69100','family':'community','provider':'stackexchange','title':'Synthetic question','url':'https://academia.stackexchange.com/questions/69100','retrieved_at':when,'content':'full_text','excerpt':'Synthetic public text','locator':'question_id=69100;body','license':'CC BY-SA 3.0','free_access':'free','upstream_revision':None,'representation':'html_text','truncated':False}}
channel={{'family':'community','provider':'stackexchange','status':'complete','retrieved_at':when,'request_url':'https://api.stackexchange.com/2.3/search/advanced?site=academia&q=spaced+repetition&pagesize=1&sort=relevance&filter=withbody','retry_after_seconds':None,'error_code':None,'raw_response_base64':base64.b64encode(b'{{"items":[]}}').decode(),'hits':[hit]}}
print(json.dumps({{'schema':r['schema'],'query':r['query'],'families':r['families'],'channels':[channel]}}))
"#,
        if wait {
            "while not p.with_suffix('.release').exists(): time.sleep(.01)"
        } else {
            ""
        }
    )
}
async fn wait_for(path: &Path) {
    let until = Instant::now() + Duration::from_secs(5);
    while !path.exists() {
        assert!(Instant::now() < until, "worker did not start");
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
}

#[tokio::test]
async fn explicit_public_terms_receipt_and_pinned_selection_survive_reopen_without_network_replay()
{
    let dir = tempfile::tempdir().unwrap();
    let source = script(false);
    let ex = open(dir.path(), &source).await;
    let req = request(&ex, "public_api_1").await;
    let router = archeaxis_api::runtime::router(ex.clone());
    let (status, receipt) = call(
        &router,
        "/api/v1/research/public/search",
        req.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["state"], "complete");
    let mut selection = target(&req);
    selection["family"] = json!("community");
    selection["hit_id"] = json!("stackexchange:academia:question:69100");
    let (status, selected) = call(
        &router,
        "/api/v1/research/public/materialize",
        selection.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 200, "{selected}");
    assert_ne!(selected["reference"], selected["raw_reference"]);
    assert_eq!(
        ex.store()
            .submit_wait(
                |c| c.query_row("SELECT count(*) FROM knowledge", [], |r| r.get::<_, i64>(0))
            )
            .await
            .unwrap()
            .unwrap(),
        0
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/search",
            req.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    let mut bad = req.clone();
    bad["document_text"] = json!("PRIVATE_DOCUMENT_SENTINEL");
    assert_eq!(
        call(&router, "/api/v1/research/public/search", bad, "human")
            .await
            .0,
        422
    );
    let mut stale = selection.clone();
    stale["restore_epoch"] = json!("stale");
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/materialize",
            stale,
            "human"
        )
        .await
        .0,
        409
    );
    drop(router);
    drop(ex);
    let ex = open(dir.path(), &source).await;
    let router = archeaxis_api::runtime::router(ex);
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/read",
            target(&req),
            "human"
        )
        .await,
        (200, receipt.clone())
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/search",
            req.clone(),
            "human"
        )
        .await,
        (200, receipt.clone())
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/materialize",
            selection,
            "human"
        )
        .await,
        (200, selected)
    );
    let journal = call(
        &router,
        "/api/v1/research/public/list",
        json!({"workspace_id":req["workspace_id"],"restore_epoch":req["restore_epoch"]}),
        "human",
    )
    .await;
    assert_eq!(journal.0, 200);
    assert_eq!(journal.1["receipts"], json!([receipt]));
    assert_eq!(
        std::fs::read_to_string(dir.path().join("public.calls")).unwrap(),
        "1"
    );
}

#[tokio::test]
async fn accepted_cancellation_cannot_publish_late_results_or_repeat_a_terminal_request() {
    let dir = tempfile::tempdir().unwrap();
    let ex = open(dir.path(), &script(true)).await;
    let req = request(&ex, "public_cancel").await;
    let router = archeaxis_api::runtime::router(ex.clone());
    let copy = router.clone();
    let body = req.clone();
    let run =
        tokio::spawn(
            async move { call(&copy, "/api/v1/research/public/search", body, "human").await },
        );
    wait_for(&dir.path().join("public.ready")).await;
    let (status, cancel) = call(
        &router,
        "/api/v1/research/public/cancel",
        target(&req),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(cancel["cancel_requested"], true);
    assert_eq!(cancel["provider_stop_state"], "unknown");
    let (status, receipt) = tokio::time::timeout(Duration::from_secs(3), run)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["state"], "cancelled");
    assert!(receipt["channels"].is_null());
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/search",
            req.clone(),
            "human"
        )
        .await,
        (200, receipt)
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/cancel",
            target(&req),
            "human"
        )
        .await
        .1["cancel_requested"],
        false
    );
    assert_eq!(ex.store().submit_wait(|c|c.query_row("SELECT count(*) FROM sources",[],|r|r.get::<_,i64>(0))).await.unwrap().unwrap(),0);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("public.calls")).unwrap(),
        "1"
    );
}

#[tokio::test]
async fn dropped_http_request_remains_unknown_and_cannot_silently_restart() {
    let dir = tempfile::tempdir().unwrap();
    let source = script(true);
    let ex = open(dir.path(), &source).await;
    let req = request(&ex, "public_aborted").await;
    let router = archeaxis_api::runtime::router(ex);
    let copy = router.clone();
    let body = req.clone();
    let run =
        tokio::spawn(
            async move { call(&copy, "/api/v1/research/public/search", body, "human").await },
        );
    wait_for(&dir.path().join("public.ready")).await;
    run.abort();
    assert!(run.await.unwrap_err().is_cancelled());
    tokio::time::sleep(Duration::from_millis(600)).await;
    let (status, receipt) = call(
        &router,
        "/api/v1/research/public/read",
        target(&req),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(receipt["state"], "unknown");
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/search",
            req.clone(),
            "human"
        )
        .await
        .0,
        409
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("public.calls")).unwrap(),
        "1"
    );
}

async fn enable_public(router: &Router, enabled: bool) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("PUT")
                .uri("/api/v1/capabilities/research.public/enabled")
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(json!({"enabled":enabled}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), 200);
}

#[cfg(windows)]
struct OwnedObservation(std::os::windows::io::OwnedHandle);
#[cfg(unix)]
struct OwnedObservation(u32);

impl OwnedObservation {
    fn capture(pid: u32) -> Self {
        assert!(
            pid > 0 && pid <= i32::MAX as u32,
            "invalid owned fixture PID"
        );
        #[cfg(windows)]
        let observation = {
            use std::os::windows::io::FromRawHandle;
            #[link(name = "kernel32")]
            unsafe extern "system" {
                fn OpenProcess(access: u32, inherit: i32, pid: u32) -> *mut std::ffi::c_void;
            }
            let handle = unsafe { OpenProcess(0x00100000, 0, pid) };
            assert!(
                !handle.is_null(),
                "UNKNOWN opening owned fixture: {}",
                std::io::Error::last_os_error()
            );
            Self(unsafe { std::os::windows::io::OwnedHandle::from_raw_handle(handle) })
        };
        #[cfg(unix)]
        let observation = Self(pid);
        assert!(
            observation.alive(),
            "owned fixture exited before observation"
        );
        observation
    }

    fn alive(&self) -> bool {
        #[cfg(windows)]
        {
            use std::os::windows::io::AsRawHandle;
            #[link(name = "kernel32")]
            unsafe extern "system" {
                fn WaitForSingleObject(handle: *mut std::ffi::c_void, milliseconds: u32) -> u32;
            }
            match unsafe { WaitForSingleObject(self.0.as_raw_handle(), 0) } {
                0 => false,
                258 => true,
                result => panic!(
                    "UNKNOWN owned process wait {result}: {}",
                    std::io::Error::last_os_error()
                ),
            }
        }
        #[cfg(unix)]
        {
            unsafe extern "C" {
                fn kill(pid: i32, sig: i32) -> i32;
            }
            if unsafe { kill(self.0 as i32, 0) } == 0 {
                return true;
            }
            let error = std::io::Error::last_os_error();
            assert_eq!(
                error.raw_os_error(),
                Some(3),
                "UNKNOWN owned process observation: {error}"
            );
            false
        }
    }
}

#[tokio::test]
async fn disable_withdraws_running_research_and_reenable_cannot_revive_it() {
    let dir = tempfile::tempdir().unwrap();
    let ex = open(dir.path(), &script(false)).await;
    let router = archeaxis_api::runtime::router(ex.clone());
    let historical = request(&ex, "historical_public").await;
    let (status, history) = call(
        &router,
        "/api/v1/research/public/search",
        historical.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(history["state"], "complete");
    std::fs::remove_file(dir.path().join("public.ready")).unwrap();
    let waiting = script(true)
        .replace("p=Path(__file__)", "p=Path(__file__)\nimport os\np.with_suffix('.pid').write_text(str(os.getpid()))")
        .replace("while not p.with_suffix('.release').exists(): time.sleep(.01)",
            "end=time.monotonic()+10\nwhile not p.with_suffix('.release').exists():\n assert time.monotonic()<end, 'fixture release expired'\n time.sleep(.01)\np.with_suffix('.late').touch()");
    std::fs::write(dir.path().join("public.py"), waiting).unwrap();
    let current = request(&ex, "withdrawn_public").await;
    let copy = router.clone();
    let body = current.clone();
    let mut run =
        tokio::spawn(
            async move { call(&copy, "/api/v1/research/public/search", body, "human").await },
        );
    wait_for(&dir.path().join("public.ready")).await;
    let pid = std::fs::read_to_string(dir.path().join("public.pid"))
        .unwrap()
        .parse()
        .unwrap();
    let process = OwnedObservation::capture(pid);
    enable_public(&router, false).await;
    // Historical read/list remain available while execution is withdrawn.
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/read",
            target(&historical),
            "human"
        )
        .await,
        (200, history.clone())
    );
    let scope =
        json!({"workspace_id":current["workspace_id"],"restore_epoch":current["restore_epoch"]});
    let (status, journal) = call(&router, "/api/v1/research/public/list", scope, "human").await;
    assert_eq!(status, 200);
    assert!(journal["receipts"].as_array().unwrap().contains(&history));
    enable_public(&router, true).await;
    let completed = tokio::time::timeout(Duration::from_secs(2), &mut run).await;
    let withdrawn_without_release = completed.is_ok();
    let (status, receipt) = match completed {
        Ok(result) => result.unwrap(),
        Err(_) => {
            // Only failure cleanup releases this exact fixture, so a RED run
            // cannot strand its process or turn a release into cancellation proof.
            std::fs::write(dir.path().join("public.release"), "").unwrap();
            tokio::time::timeout(Duration::from_secs(3), run)
                .await
                .unwrap()
                .unwrap()
        }
    };
    let end = Instant::now() + Duration::from_millis(500);
    while process.alive() && Instant::now() < end {
        tokio::time::sleep(Duration::from_millis(5)).await;
    }
    assert!(!process.alive(), "owned worker was not observed exited");
    assert!(
        withdrawn_without_release,
        "disable did not withdraw its running worker; reenable revived the old execution"
    );
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["state"], "cancelled");
    assert!(receipt["channels"].is_null());
    assert!(!dir.path().join("public.late").exists());
    assert_eq!(
        std::fs::read_dir(dir.path().join("staging"))
            .unwrap()
            .count(),
        0
    );
    assert_eq!(
        call(&router, "/api/v1/research/public/search", current, "human").await,
        (200, receipt)
    );
    // A new request after reenabling can run; the old token stays withdrawn.
    std::fs::write(dir.path().join("public.py"), script(false)).unwrap();
    let fresh = request(&ex, "new_public_after_enable").await;
    let (status, receipt) = call(&router, "/api/v1/research/public/search", fresh, "human").await;
    assert_eq!(status, 200);
    assert_eq!(receipt["state"], "complete");
    assert_eq!(
        std::fs::read_to_string(dir.path().join("public.calls")).unwrap(),
        "3"
    );
}

#[tokio::test]
async fn restore_during_network_rejects_old_epoch_results_before_any_source_publication() {
    let dir = tempfile::tempdir().unwrap();
    let ex = open(dir.path(), &script(true)).await;
    let req = request(&ex, "public_restore").await;
    let router = archeaxis_api::runtime::router(ex.clone());
    let copy = router.clone();
    let body = req.clone();
    let run =
        tokio::spawn(
            async move { call(&copy, "/api/v1/research/public/search", body, "human").await },
        );
    wait_for(&dir.path().join("public.ready")).await;
    ex.store()
        .submit_wait(|c| {
            let tx = c.transaction()?;
            archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx)?;
            tx.commit()
        })
        .await
        .unwrap()
        .unwrap();
    std::fs::write(dir.path().join("public.release"), "").unwrap();
    let (status, _) = run.await.unwrap();
    assert_eq!(status, 503);
    assert_eq!(
        call(
            &router,
            "/api/v1/research/public/read",
            target(&req),
            "human"
        )
        .await
        .0,
        409
    );
    assert_eq!(ex.store().submit_wait(|c|c.query_row("SELECT count(*) FROM sources",[],|r|r.get::<_,i64>(0))).await.unwrap().unwrap(),0);
}
