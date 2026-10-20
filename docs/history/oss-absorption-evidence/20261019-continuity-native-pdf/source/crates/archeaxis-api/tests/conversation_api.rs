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
    assert_eq!(
        preview["plan"]["destination_candidates"],
        json!(["http://127.0.0.1:1234/v1"])
    );
    let (policy, version) = if request["purpose"] == "companion" {
        ("companion_general", "archeaxis.companion/v1 2026-10-19")
    } else {
        assert_eq!(request["purpose"], "material_learning");
        ("grounded", "archeaxis.vnext/v1 2026-10-02")
    };
    assert_eq!(preview["plan"]["answer_policy"], policy);
    assert_eq!(preview["plan"]["prompt_version"], version);
    assert_eq!(
        preview["plan_sha256"],
        hash(preview["plan"].to_string().as_bytes())
    );
    for field in ["answer_policy", "prompt_version"] {
        let mut altered = preview["plan"].clone();
        altered.as_object_mut().unwrap().remove(field);
        assert_ne!(preview["plan_sha256"], hash(altered.to_string().as_bytes()));
    }
    request["preview"] = json!(false);
    request["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    request
}
#[tokio::test]
async fn failed_conversation_measurements_survive_restart_without_repeating_worker() {
    for (code, expected_reason, expected_diagnostics) in [
        (
            "NO_FINAL_ANSWER",
            "conversation_model_failed",
            json!({"finish_reason":"length","elapsed_s":1.5,"usage":{"output_tokens":128}}),
        ),
        (
            "MODEL_CALL_TIMEOUT",
            "conversation_model_timeout",
            json!({"request_stage":"model_request","discovery_elapsed_s":0.25,"elapsed_s":5.0,"error_type":"TimeoutError"}),
        ),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("worker.py");
        let count = dir.path().join("count");
        let mut diagnostics = expected_diagnostics.clone();
        diagnostics["stderr"] = json!("PRIVATE_SENTINEL");
        let failure = json!({"schema":"archeaxis.machine-worker-failure/v1","reason_code":code,"diagnostics":diagnostics});
        std::fs::write(&script,format!("import sys\nfrom pathlib import Path\np=Path({})\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\nprint({})\nsys.exit(1)\n",serde_json::to_string(&count).unwrap(),serde_json::to_string(&failure.to_string()).unwrap())).unwrap();
        let router = archeaxis_api::runtime::router(open(dir.path(), &script).await);
        create(&router, "failed_session").await;
        let request = confirmed(&router, body("failed_session", "failed_request")).await;
        let (status, receipt) =
            call(&router, "/api/v1/conversation/requests", request.clone()).await;
        assert_eq!(status, 200, "{receipt}");
        assert_eq!(receipt["state"], "failed");
        assert_eq!(receipt["reason_code"], expected_reason);
        assert_eq!(receipt["diagnostics"], expected_diagnostics);
        assert!(receipt["answer"].is_null());
        assert!(!receipt.to_string().contains("PRIVATE_SENTINEL"));
        drop(router);
        let router = archeaxis_api::runtime::router(open(dir.path(), &script).await);
        assert_eq!(
            call(&router, "/api/v1/conversation/requests", request)
                .await
                .1,
            receipt
        );
        let (_, history) = call(
            &router,
            "/api/v1/conversation/history",
            json!({"session_id":"failed_session","after_sequence":0,"limit":64}),
        )
        .await;
        assert_eq!(history["requests"][0]["receipt"], receipt);
        assert_eq!(std::fs::read_to_string(count).unwrap(), "1");
    }
}

#[tokio::test]
async fn material_and_companion_history_replay_restart_and_presentation_reads_never_repeat_inference()
 {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("worker.py");
    let count = dir.path().join("count");
    std::fs::write(&script,format!("import json,sys\nfrom pathlib import Path\np=Path({})\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\ncontext=Path(sys.argv[1]).read_text()\nassert '原文😀' in context or 'SYNTHETIC answer' in context\npolicy=sys.argv[sys.argv.index('--answer-policy')+1]\nversion=sys.argv[sys.argv.index('--prompt-version')+1]\nprint(json.dumps({{'answer':'SYNTHETIC answer','model':'fixture','endpoint':'http://127.0.0.1:1234/v1','protocol':'synthetic','answer_policy':policy,'prompt_version':version,'loss_receipt':{{'params':{{'answer_policy':policy,'prompt_version':version}}}}}}))\n",serde_json::to_string(&count).unwrap())).unwrap();
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
    std::fs::write(&script,format!("import time,json\nfrom pathlib import Path\nPath({}).write_text('started')\ntime.sleep(20)\nprint(json.dumps({{'answer':'late answer','endpoint':'http://127.0.0.1:1234/v1'}}))\n",serde_json::to_string(&started).unwrap())).unwrap();
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
    // A full execution DTO must never become cancellation authority. The UI
    // adapter must project the finite identity before entering this route.
    assert_eq!(
        call(
            &router,
            "/api/v1/conversation/cancel",
            body("cancel_session", "cancel_request")
        )
        .await
        .0,
        422
    );
    assert!(
        !task.is_finished(),
        "rejected fields must not cancel the worker"
    );
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

async fn journal_raw(executor: &Executor, session: &str) -> String {
    let key = format!("conversation_session_{}", hash(session.as_bytes()));
    executor
        .store()
        .submit_wait(move |conn| {
            conn.query_row(
                "SELECT value FROM workspace_meta WHERE key=?1",
                [key],
                |row| row.get(0),
            )
        })
        .await
        .unwrap()
        .unwrap()
}

#[tokio::test]
async fn client_cannot_supply_answer_policy_or_prompt_version_and_preview_has_no_journal_effect() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("never.py");
    let count = dir.path().join("count");
    std::fs::write(&script, format!("from pathlib import Path\nPath({}).write_text('unexpected')\nraise AssertionError('never execute')", serde_json::to_string(&count).unwrap())).unwrap();
    let executor = open(dir.path(), &script).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    create(&router, "policy_owner").await;
    let before = journal_raw(&executor, "policy_owner").await;
    for additions in [
        json!({"answer_policy":"companion_general"}),
        json!({"prompt_version":"archeaxis.companion/v1 2026-10-19"}),
        json!({"answer_policy":"grounded","prompt_version":"archeaxis.vnext/v1 2026-10-02"}),
    ] {
        let mut request = body("policy_owner", "client_policy");
        for (field, value) in additions.as_object().unwrap() {
            request[field] = value.clone();
        }
        assert_eq!(
            call(&router, "/api/v1/conversation/requests", request)
                .await
                .0,
            422
        );
    }
    let current = confirmed(&router, body("policy_owner", "unadmitted")).await;
    let (_, preview) = call(
        &router,
        "/api/v1/conversation/requests",
        body("policy_owner", "unadmitted"),
    )
    .await;
    let mut legacy = preview["plan"].clone();
    let object = legacy.as_object_mut().unwrap();
    assert!(object.remove("answer_policy").is_some());
    assert!(object.remove("prompt_version").is_some());
    let legacy_sha = hash(legacy.to_string().as_bytes());
    assert_ne!(current["confirmed_plan_sha256"], legacy_sha);
    let mut old_confirmation = current;
    old_confirmation["confirmed_plan_sha256"] = json!(legacy_sha);
    let (status, refused) = call(&router, "/api/v1/conversation/requests", old_confirmation).await;
    assert_eq!(status, 403, "{refused}");
    assert_eq!(refused["reason_code"], "conversation_confirmation_required");
    assert_eq!(journal_raw(&executor, "policy_owner").await, before);
    assert!(
        !count.exists(),
        "preview and rejected confirmation must not spawn worker"
    );
}

#[tokio::test]
async fn incomplete_or_mismatched_answer_policy_is_failed_without_publishing_candidate() {
    // 返回有效JSON及非空答案，只破坏策略证据，以免负例因无关传输错误通过。
    for mutation in [
        "out.pop('answer_policy'); out.pop('prompt_version'); out.pop('loss_receipt')",
        "out.pop('answer_policy')",
        "out.pop('prompt_version')",
        "out['loss_receipt']['params'].pop('answer_policy')",
        "out['loss_receipt']['params'].pop('prompt_version')",
        "out['answer_policy']='grounded'",
        "out['prompt_version']='archeaxis.vnext/v1 2026-10-02'",
        "out['loss_receipt']['params']['answer_policy']='grounded'",
        "out['loss_receipt']['params']['prompt_version']='archeaxis.vnext/v1 2026-10-02'",
        "out['answer_policy']=True",
        "out['loss_receipt']['params']['prompt_version']=None",
    ] {
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("wrong_policy.py");
        let count = dir.path().join("count");
        std::fs::write(&script, format!(
            "import json,sys\nfrom pathlib import Path\nPath({}).write_text('1')\np=sys.argv[sys.argv.index('--answer-policy')+1]\nv=sys.argv[sys.argv.index('--prompt-version')+1]\nassert p=='companion_general' and v=='archeaxis.companion/v1 2026-10-19'\nout={{'answer':'SYNTHETIC must not publish','model':'fixture','endpoint':'http://127.0.0.1:1234/v1','protocol':'synthetic','answer_policy':p,'prompt_version':v,'loss_receipt':{{'params':{{'answer_policy':p,'prompt_version':v}}}}}}\n{mutation}\nprint(json.dumps(out))\n",
            serde_json::to_string(&count).unwrap(),
        )).unwrap();
        let executor = open(dir.path(), &script).await;
        let router = archeaxis_api::runtime::router(executor.clone());
        create(&router, "policy_fail").await;
        let request = confirmed(&router, body("policy_fail", "wrong")).await;
        let (status, receipt) =
            call(&router, "/api/v1/conversation/requests", request.clone()).await;
        assert_eq!(status, 200, "mutation={mutation}: {receipt}");
        assert_eq!(receipt["state"], "failed", "mutation={mutation}: {receipt}");
        assert_eq!(
            receipt["reason_code"], "conversation_answer_policy_unverified",
            "mutation={mutation}: {receipt}"
        );
        assert!(receipt["answer"].is_null());
        assert_eq!(receipt["authority"], "candidate");
        assert_eq!(receipt["grants_knowledge_acceptance"], false);
        assert_eq!(std::fs::read_to_string(&count).unwrap(), "1");
        assert_eq!(
            call(&router, "/api/v1/conversation/requests", request)
                .await
                .1,
            receipt
        );
        let (_, history) = call(
            &router,
            "/api/v1/conversation/history",
            json!({"session_id":"policy_fail","after_sequence":0,"limit":64}),
        )
        .await;
        assert_eq!(history["events"][1]["kind"], "failed");
        assert_eq!(history["requests"][0]["receipt"], receipt);
        assert_eq!(std::fs::read_to_string(&count).unwrap(), "1");
        assert_eq!(
            executor
                .store()
                .submit_wait(
                    |conn| conn.query_row("SELECT COUNT(*) FROM knowledge", [], |row| row
                        .get::<_, i64>(0))
                )
                .await
                .unwrap()
                .unwrap(),
            0
        );
    }
}

#[tokio::test]
async fn legacy_terminal_and_pending_plans_replay_unchanged_after_restart_without_worker() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("never.py");
    let count = dir.path().join("count");
    std::fs::write(&script, format!("from pathlib import Path\nPath({}).write_text('unexpected')\nraise AssertionError('legacy must not execute')", serde_json::to_string(&count).unwrap())).unwrap();
    let executor = open(dir.path(), &script).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    let mut saved_cases = Vec::new();
    for (session_id, terminal) in [("legacy_terminal", true), ("legacy_pending", false)] {
        create(&router, session_id).await;
        let (_, preview) = call(
            &router,
            "/api/v1/conversation/requests",
            body(session_id, "legacy_request"),
        )
        .await;
        let mut plan = preview["plan"].clone();
        assert!(
            plan.as_object_mut()
                .unwrap()
                .remove("answer_policy")
                .is_some()
        );
        assert!(
            plan.as_object_mut()
                .unwrap()
                .remove("prompt_version")
                .is_some()
        );
        let sha = hash(plan.to_string().as_bytes());
        let receipt = if terminal {
            json!({"schema":"archeaxis.conversation-receipt/v1","session_id":session_id,"request_id":"legacy_request","state":"completed","answer":{"answer":"SYNTHETIC legacy candidate"},"reason_code":null,"plan":plan,"plan_sha256":sha,"delivery":"BUFFERED","provider_stop_state":"UNKNOWN","authority":"candidate","grants_knowledge_acceptance":false})
        } else {
            Value::Null
        };
        let mut journal: Value =
            serde_json::from_str(&journal_raw(&executor, session_id).await).unwrap();
        journal["requests"] = json!([{"request_id":"legacy_request","plan":plan,"plan_sha256":sha,"state":if terminal {"completed"} else {"EXECUTING"},"receipt":receipt}]);
        journal["last_sequence"] = json!(if terminal { 2 } else { 1 });
        journal["events"] = json!([{"session_id":session_id,"request_id":"legacy_request","sequence":1,"kind":"accepted","data":{"question":"conversation question","purpose":"companion","plan_sha256":sha},"delivery":"BUFFERED"}]);
        if terminal {
            journal["events"].as_array_mut().unwrap().push(json!({"session_id":session_id,"request_id":"legacy_request","sequence":2,"kind":"completed","data":receipt,"delivery":"BUFFERED"}));
        }
        let raw = journal.to_string();
        let stored = raw.clone();
        let key = format!("conversation_session_{}", hash(session_id.as_bytes()));
        executor
            .store()
            .submit_wait(move |conn| {
                conn.execute(
                    "UPDATE workspace_meta SET value=?1 WHERE key=?2",
                    rusqlite::params![stored, key],
                )
            })
            .await
            .unwrap()
            .unwrap();
        let mut retry = plan["request"].clone();
        retry["preview"] = json!(false);
        retry["confirmed_plan_sha256"] = json!(sha);
        saved_cases.push((session_id, terminal, plan, sha, receipt, raw, retry));
    }
    drop(router);
    drop(executor);
    let executor = open(dir.path(), &script).await;
    let router = archeaxis_api::runtime::router(executor.clone());
    for (session_id, terminal, plan, sha, receipt, raw, retry) in saved_cases {
        let (status, observed) = call(
            &router,
            "/api/v1/conversation/status",
            json!({"session_id":session_id,"request_id":"legacy_request"}),
        )
        .await;
        assert_eq!(status, 200, "{observed}");
        if terminal {
            assert_eq!(observed, receipt, "old terminal receipt must remain exact");
        } else {
            assert_eq!(observed["execution_state"], "UNKNOWN");
            assert_eq!(observed["answer_published"], false);
        }
        assert_eq!(observed["plan"], plan);
        assert_eq!(observed["plan_sha256"], sha);
        assert!(observed["plan"].get("answer_policy").is_none());
        assert!(observed["plan"].get("prompt_version").is_none());
        assert_eq!(
            call(&router, "/api/v1/conversation/requests", retry)
                .await
                .1,
            observed
        );
        let (_, history) = call(
            &router,
            "/api/v1/conversation/history",
            json!({"session_id":session_id,"after_sequence":0,"limit":64}),
        )
        .await;
        assert_eq!(history["requests"][0]["plan"], plan);
        assert_eq!(history["requests"][0]["plan_sha256"], sha);
        assert_eq!(history["requests"][0]["receipt"], receipt);
        assert_eq!(
            journal_raw(&executor, session_id).await,
            raw,
            "read/replay must not migrate historical bytes"
        );
    }
    assert!(
        !count.exists(),
        "no legacy status/history/replay may rerun inference"
    );
    assert_eq!(
        executor
            .store()
            .submit_wait(
                |conn| conn.query_row("SELECT COUNT(*) FROM knowledge", [], |row| row
                    .get::<_, i64>(0))
            )
            .await
            .unwrap()
            .unwrap(),
        0
    );
}

#[tokio::test]
async fn material_learning_rejects_general_companion_worker_policy() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("wrong_material_policy.py");
    std::fs::write(&script, "import json,sys\nassert sys.argv[sys.argv.index('--answer-policy')+1]=='grounded'\nassert sys.argv[sys.argv.index('--prompt-version')+1]=='archeaxis.vnext/v1 2026-10-02'\np='companion_general'\nv='archeaxis.companion/v1 2026-10-19'\nprint(json.dumps({'answer':'SYNTHETIC general advice must not become material evidence','model':'fixture','endpoint':'http://127.0.0.1:1234/v1','protocol':'synthetic','answer_policy':p,'prompt_version':v,'loss_receipt':{'params':{'answer_policy':p,'prompt_version':v}}}))\n").unwrap();
    let executor = open(dir.path(), &script).await;
    let saved = executor.store().submit_wait(|conn| document::create_optional(conn, None, None, "SYNTHETIC material", json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"SYNTHETIC material fact"}]}]}))).await.unwrap().unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    create(&router, "material_policy").await;
    let mut request = body("material_policy", "wrong_general");
    request["purpose"] = json!("material_learning");
    request["material"] = json!({"kind":"document","document_id":saved["document_id"],"version":1,"content_sha256":saved["content_sha256"],"block_id":null});
    let request = confirmed(&router, request).await;
    let (status, receipt) = call(&router, "/api/v1/conversation/requests", request).await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["state"], "failed", "{receipt}");
    assert_eq!(
        receipt["reason_code"],
        "conversation_answer_policy_unverified"
    );
    assert!(receipt["answer"].is_null());
    assert_eq!(receipt["grants_knowledge_acceptance"], false);
    assert_eq!(
        executor
            .store()
            .submit_wait(
                |conn| conn.query_row("SELECT COUNT(*) FROM knowledge", [], |row| row
                    .get::<_, i64>(0))
            )
            .await
            .unwrap()
            .unwrap(),
        0
    );
}
