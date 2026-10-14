//! Real Core/SQLite/HTTP with SYNTHETIC model transport. No real provider call.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{document, material_question::hash};
use axum::{Router, body::Body, http::Request};
use serde_json::{Value, json};
use tower::ServiceExt;
async fn call(router: &Router, path: &str, body: Value) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let code = response.status().as_u16();
    let raw = axum::body::to_bytes(response.into_body(), 2000000)
        .await
        .unwrap();
    (code, serde_json::from_slice(&raw).unwrap_or(Value::Null))
}
async fn open(dir: &std::path::Path, script: &std::path::Path) -> Executor {
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    Executor::open_routes(
        &dir.join("w.sqlite"),
        &dir.join("staging"),
        &python,
        script,
        &[("machine.answer", script.to_path_buf())],
    )
    .await
    .unwrap()
}
fn body(session: &str, request: &str) -> Value {
    json!({"session_id":session,"request_id":request,"purpose":"companion","material":null,"selection":null,"question":"conversation question","model":null,"max_tokens":128,"timeout_s":5,"preview":true,"confirmed_plan_sha256":null})
}
async fn create(router: &Router, session: &str) {
    assert_eq!(
        call(
            router,
            "/api/v1/conversation/sessions",
            json!({"session_id":session,"title":"SYNTHETIC session","consumer":"archeaxis"})
        )
        .await
        .0,
        200
    );
}
async fn confirmed(router: &Router, mut request: Value) -> Value {
    let (status, preview) = call(router, "/api/v1/conversation/requests", request.clone()).await;
    assert_eq!(status, 200, "{preview}");
    request["preview"] = json!(false);
    request["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    request
}
#[tokio::test]
async fn material_and_companion_history_replay_restart_and_presentation_reads_never_repeat_inference()
 {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("worker.py");
    let count = dir.path().join("count");
    std::fs::write(&script,format!("import json,sys\nfrom pathlib import Path\np=Path({})\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\ncontext=Path(sys.argv[1]).read_text()\nassert '原文😀' in context or 'SYNTHETIC answer' in context\nprint(json.dumps({{'answer':'SYNTHETIC answer','model':'fixture','endpoint':'http://127.0.0.1:11434','protocol':'synthetic'}}))\n",serde_json::to_string(&count).unwrap())).unwrap();
    let executor = open(dir.path(), &script).await;
    let saved=executor.store().submit_wait(|c|document::create_optional(c,None,None,"new material",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"前缀原文😀后缀"}]}]}))).await.unwrap().unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    create(&router, "session_a").await;
    let mut first = body("session_a", "request_a");
    first["purpose"] = json!("material_learning");
    first["material"] = json!({"kind":"document","document_id":saved["document_id"],"version":1,"content_sha256":saved["content_sha256"],"block_id":null});
    first["selection"] =
        json!({"start_utf16":2,"end_utf16":6,"quote_sha256":hash("原文😀".as_bytes())});
    let mut unauthorized = first.clone();
    unauthorized["preview"] = json!(false);
    assert_eq!(
        call(&router, "/api/v1/conversation/requests", unauthorized)
            .await
            .0,
        403
    );
    assert!(!count.exists());
    let first = confirmed(&router, first).await;
    let (status, receipt) = call(&router, "/api/v1/conversation/requests", first.clone()).await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["state"], "completed");
    assert_eq!(receipt["delivery"], "BUFFERED");
    assert_eq!(
        call(&router, "/api/v1/conversation/requests", first.clone())
            .await
            .1,
        receipt
    );
    let history = call(
        &router,
        "/api/v1/conversation/history",
        json!({"session_id":"session_a","after_sequence":0,"limit":64}),
    )
    .await
    .1;
    assert_eq!(history["last_sequence"], 2);
    assert_eq!(history["events"][0]["sequence"], 1);
    assert_eq!(history["events"][1]["sequence"], 2);
    assert_eq!(history["events"][1]["kind"], "completed");
    assert_eq!(history["events"][1]["request_id"], "request_a");
    let stale = confirmed(&router, body("session_a", "stale_request")).await;
    let second = confirmed(&router, body("session_a", "request_b")).await;
    assert_eq!(
        call(&router, "/api/v1/conversation/requests", second)
            .await
            .1["state"],
        "completed"
    );
    assert_eq!(
        call(&router, "/api/v1/conversation/requests", stale)
            .await
            .0,
        403
    );
    let page = call(
        &router,
        "/api/v1/conversation/history",
        json!({"session_id":"session_a","after_sequence":2,"limit":1}),
    )
    .await
    .1;
    assert_eq!(page["events"].as_array().unwrap().len(), 1);
    assert_eq!(page["events"][0]["sequence"], 3);
    assert_eq!(std::fs::read_to_string(&count).unwrap(), "2");
    assert_eq!(
        executor
            .store()
            .submit_wait(|c| c
                .query_row("SELECT COUNT(*) FROM knowledge", [], |r| r.get::<_, i64>(0))
                .unwrap())
            .await
            .unwrap(),
        0
    );
    drop(router);
    drop(executor);
    let restarted = archeaxis_api::runtime::router(open(dir.path(), &script).await);
    assert_eq!(
        call(&restarted, "/api/v1/conversation/requests", first.clone())
            .await
            .1,
        receipt
    );
    assert_eq!(
        call(
            &restarted,
            "/api/v1/conversation/status",
            json!({"session_id":"session_a","request_id":"request_a"})
        )
        .await
        .1,
        receipt
    );
    assert_eq!(std::fs::read_to_string(&count).unwrap(), "2");
    let mut conflict = first;
    conflict["question"] = json!("changed");
    assert_eq!(
        call(&restarted, "/api/v1/conversation/requests", conflict)
            .await
            .0,
        409
    );
    create(&restarted, "session_b").await;
    assert_eq!(
        call(
            &restarted,
            "/api/v1/conversation/status",
            json!({"session_id":"session_b","request_id":"request_a"})
        )
        .await
        .0,
        404
    );
}
#[tokio::test]
async fn cancellation_is_request_bound_and_publishes_no_late_answer() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("slow.py");
    let started = dir.path().join("started");
    std::fs::write(&script,format!("import time,json\nfrom pathlib import Path\nPath({}).write_text('started')\ntime.sleep(20)\nprint(json.dumps({{'answer':'late answer','endpoint':'http://127.0.0.1:11434'}}))\n",serde_json::to_string(&started).unwrap())).unwrap();
    let router = archeaxis_api::runtime::router(open(dir.path(), &script).await);
    create(&router, "cancel_session").await;
    let request = confirmed(&router, body("cancel_session", "cancel_request")).await;
    let r = router.clone();
    let task =
        tokio::spawn(async move { call(&r, "/api/v1/conversation/requests", request).await });
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while !started.exists() && std::time::Instant::now() < deadline {
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }
    assert!(started.exists());
    assert_eq!(
        call(
            &router,
            "/api/v1/conversation/cancel",
            json!({"session_id":"other","request_id":"cancel_request"})
        )
        .await
        .1["cancel_requested"],
        false
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/conversation/cancel",
            json!({"session_id":"cancel_session","request_id":"cancel_request"})
        )
        .await
        .1["cancel_requested"],
        true
    );
    let (_, receipt) = task.await.unwrap();
    assert_eq!(receipt["state"], "cancelled");
    assert!(receipt["answer"].is_null());
    let history = call(
        &router,
        "/api/v1/conversation/history",
        json!({"session_id":"cancel_session","after_sequence":0,"limit":64}),
    )
    .await
    .1;
    assert_eq!(history["events"][1]["kind"], "cancelled");
    assert_eq!(
        call(
            &router,
            "/api/v1/conversation/status",
            json!({"session_id":"cancel_session","request_id":"cancel_request"})
        )
        .await
        .1,
        receipt
    );
}
#[tokio::test]
async fn unfinished_request_restart_returns_unknown_without_retry_and_finite_fields_reject_expansion()
 {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("unused.py");
    std::fs::write(&script, "raise RuntimeError('must never execute')").unwrap();
    let executor = open(dir.path(), &script).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    create(&router, "lost_session").await;
    let request = confirmed(&router, body("lost_session", "lost_request")).await;
    executor
        .store()
        .submit_wait(|c| {
            let key = format!(
                "conversation_session_{}",
                hash("corrupt_session".as_bytes())
            );
            c.execute(
                "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
                rusqlite::params![key, "{invalid"],
            )
            .unwrap();
        })
        .await
        .unwrap();
    assert_eq!(call(&router,"/api/v1/conversation/sessions",json!({"session_id":"corrupt_session","title":"SYNTHETIC session","consumer":"archeaxis"})).await.0,409);
    assert_eq!(
        executor
            .store()
            .submit_wait(|c| c
                .query_row(
                    "SELECT value FROM workspace_meta WHERE key=?1",
                    [format!(
                        "conversation_session_{}",
                        hash("corrupt_session".as_bytes())
                    )],
                    |r| r.get::<_, String>(0)
                )
                .unwrap())
            .await
            .unwrap(),
        "{invalid"
    );
    let preview_request = body("lost_session", "pending");
    let preview = call(&router, "/api/v1/conversation/requests", preview_request)
        .await
        .1;
    let plan = preview["plan"].clone();
    let sha = preview["plan_sha256"].clone();
    executor.store().submit_wait(move|c|{let key=format!("conversation_session_{}",hash("lost_session".as_bytes()));let raw:String=c.query_row("SELECT value FROM workspace_meta WHERE key=?1",[&key],|r|r.get(0)).unwrap();let mut session:Value=serde_json::from_str(&raw).unwrap();session["requests"]=json!([{"request_id":"pending","plan":plan,"plan_sha256":sha,"state":"EXECUTING","receipt":null}]);c.execute("UPDATE workspace_meta SET value=?1 WHERE key=?2",rusqlite::params![session.to_string(),key]).unwrap();}).await.unwrap();
    drop(router);
    drop(executor);
    let router = archeaxis_api::runtime::router(open(dir.path(), &script).await);
    let status = call(
        &router,
        "/api/v1/conversation/status",
        json!({"session_id":"lost_session","request_id":"pending"}),
    )
    .await
    .1;
    assert_eq!(status["execution_state"], "UNKNOWN");
    let mut retry = status["plan"]["request"].clone();
    retry["preview"] = json!(false);
    retry["confirmed_plan_sha256"] = status["plan_sha256"].clone();
    assert_eq!(
        call(&router, "/api/v1/conversation/requests", retry)
            .await
            .1,
        status
    );
    assert_eq!(
        call(&router, "/api/v1/conversation/requests", request)
            .await
            .0,
        409
    );
    let mut expanded = body("lost_session", "expanded");
    expanded["url"] = json!("http://other");
    assert_eq!(
        call(&router, "/api/v1/conversation/requests", expanded)
            .await
            .0,
        422
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/conversation/sessions",
            json!({"session_id":"external","title":"external","consumer":"astryn"})
        )
        .await
        .0,
        422
    );
}
