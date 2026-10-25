//! SYNTHETIC local worker, real Store/API protocol; no provider inference.
use archeaxis_application::{
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::{document, material_question::hash, source};
use axum::{Router, body::Body, http::Request};
use serde_json::{Value, json};
use tower::ServiceExt;

#[tokio::test]
async fn unconfigured_material_cloud_never_admits_a_production_request() {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("worker.py");
    std::fs::write(&worker,"from pathlib import Path\nPath(__file__).with_suffix('.started').touch()\nraise SystemExit(1)\n").unwrap();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap()),
        &worker,
        &[("machine.answer", worker.clone())],
    )
    .await
    .unwrap();
    let doc=executor.store().submit_wait(|c|document::create_optional(c,None,None,"synthetic material",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic material"}]}]}))).await.unwrap().unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"request_id":"dormant_cloud","material":{"kind":"document","document_id":doc["document_id"],"version":1,"content_sha256":doc["content_sha256"],"block_id":null},
        "selection":null,"question":"Synthetic question","purpose":"learning","model":"synthetic-model","max_tokens":128,"timeout_s":5,"preview":true,"confirmed_plan_sha256":null,
        "model_configuration":{"workspace_id":"a".repeat(32),"restore_epoch":"initial","schema":"archeaxis.resolved-model/v1","configuration_revision":1,"configuration_sha256":"b".repeat(64),"purpose":"material","lane":"fast","profile_id":"synthetic_cloud",
            "profile":{"endpoint":"https://api.openai.com/v1","protocol":"openai","model":"synthetic-model","credential_ref":format!("aak_cred_{}","c".repeat(32)),"max_tokens":128,"timeout_s":5}}});
    for (path, preview, asynchronous) in [
        ("/api/v1/material/questions", true, false),
        ("/api/v1/material/questions", false, false),
        ("/api/v1/material/questions/submissions", false, true),
    ] {
        let mut request = body.clone();
        request["preview"] = json!(preview);
        if !preview {
            request["confirmed_plan_sha256"] = json!("d".repeat(64));
        }
        if asynchronous {
            request["execution_mode"] = json!("async");
        }
        let (status, receipt) = call(&router, path, request).await;
        assert_eq!(status, 422, "{receipt}");
        assert_eq!(receipt["reason_code"], "MODEL_CONFIGURATION_CHANGED");
        assert_eq!(receipt["answer_published"], false);
    }
    assert!(!worker.with_extension("started").exists());
    assert_eq!(
        executor
            .store()
            .submit_wait(|c| c.query_row(
                "SELECT count(*) FROM workspace_meta WHERE key LIKE 'material_request_%'",
                [],
                |r| r.get::<_, i64>(0)
            ))
            .await
            .unwrap()
            .unwrap(),
        0
    );
}
async fn call(router: &Router, path: &str, body: Value) -> (u16, Value) {
    let r = router
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
    let status = r.status().as_u16();
    let b = axum::body::to_bytes(r.into_body(), 1000000).await.unwrap();
    (status, serde_json::from_slice(&b).unwrap_or(Value::Null))
}
#[tokio::test]
async fn failed_material_measurements_survive_restart_without_repeating_worker() {
    for (code, expected_reason, expected_diagnostics) in [
        (
            "MODEL_CALL_FAILED",
            "material_model_call_failed",
            json!({"http_status":503,"elapsed_s":1.5,"error_type":"HTTPError"}),
        ),
        (
            "MODEL_CALL_TIMEOUT",
            "material_model_timeout",
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
        let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
        let db = dir.path().join("w.sqlite");
        let staging = dir.path().join("staging");
        let routes = [("machine.answer", script.clone())];
        let open = || Executor::open_routes(&db, &staging, &python, &script, &routes);
        let executor = open().await.unwrap();
        let doc=executor.store().submit_wait(|c|document::create_optional(c,None,None,"material",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic material"}]}]}))).await.unwrap().unwrap();
        let router = archeaxis_api::runtime::router(executor);
        let mut body = json!({"request_id":"failed_material","material":{"kind":"document","document_id":doc["document_id"],"version":1,"content_sha256":doc["content_sha256"],"block_id":null},"selection":null,"question":"Question","purpose":"learning","model":null,"max_tokens":128,"timeout_s":5,"preview":true,"confirmed_plan_sha256":null});
        let (status, preview) = call(&router, "/api/v1/material/questions", body.clone()).await;
        assert_eq!(status, 200, "{preview}");
        body["preview"] = json!(false);
        body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
        let (status, receipt) = call(&router, "/api/v1/material/questions", body.clone()).await;
        assert_eq!(status, 200, "{receipt}");
        assert_eq!(receipt["outcome"], "failed");
        assert_eq!(receipt["reason_code"], expected_reason);
        assert_eq!(receipt["diagnostics"], expected_diagnostics);
        assert!(receipt["answer"].is_null());
        assert!(!receipt.to_string().contains("PRIVATE_SENTINEL"));
        drop(router);
        let router = archeaxis_api::runtime::router(open().await.unwrap());
        assert_eq!(
            call(&router, "/api/v1/material/questions", body).await.1,
            receipt
        );
        assert_eq!(
            call(
                &router,
                "/api/v1/material/questions/status",
                json!({"request_id":"failed_material"})
            )
            .await
            .1,
            receipt
        );
        assert_eq!(std::fs::read_to_string(count).unwrap(), "1");
    }
}

#[tokio::test]
async fn hard_timeout_measurements_survive_reopen_without_repeating_inference() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("worker.py");
    let count = dir.path().join("count");
    std::fs::write(&script, format!(
        "import time\nfrom pathlib import Path\np=Path({})\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\ntime.sleep(60)\n",
        serde_json::to_string(&count).unwrap()
    )).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let db = dir.path().join("w.sqlite");
    let staging = dir.path().join("staging");
    let routes = [("machine.answer", script.clone())];
    let open = || Executor::open_routes(&db, &staging, &python, &script, &routes);
    let executor = open().await.unwrap();
    let doc = executor.store().submit_wait(|c| document::create_optional(
        c, None, None, "material", json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Synthetic material"}]}]})
    )).await.unwrap().unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let mut body = json!({"request_id":"timeout_material","material":{"kind":"document","document_id":doc["document_id"],"version":1,"content_sha256":doc["content_sha256"],"block_id":null},"selection":null,"question":"SYNTHETIC_PRIVATE_QUESTION","purpose":"learning","model":null,"max_tokens":128,"timeout_s":1,"preview":true,"confirmed_plan_sha256":null});
    let (status, preview) = call(&router, "/api/v1/material/questions", body.clone()).await;
    assert_eq!(status, 200);
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    let (status, receipt) = call(&router, "/api/v1/material/questions", body.clone()).await;
    assert_eq!(status, 200);
    assert_eq!(receipt["outcome"], "failed");
    assert_eq!(receipt["reason_code"], "material_model_timeout");
    assert!(receipt["answer"].is_null());
    assert_eq!(receipt["diagnostics"]["timeout_s"], 1);
    assert_eq!(receipt["diagnostics"]["max_tokens"], 128);
    assert_eq!(receipt["diagnostics"]["error_type"], "TimeoutError");
    assert!(receipt["diagnostics"]["elapsed_s"].as_f64().unwrap() >= 1.0);
    assert!(receipt["diagnostics"].get("observed_model").is_none());
    assert!(
        !receipt["diagnostics"]
            .to_string()
            .contains("SYNTHETIC_PRIVATE")
    );
    assert_eq!(receipt["provider_stop_state"], "NOT_REQUESTED");
    drop(router);
    let router = archeaxis_api::runtime::router(open().await.unwrap());
    assert_eq!(
        call(&router, "/api/v1/material/questions", body).await.1,
        receipt
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/material/questions/status",
            json!({"request_id":"timeout_material"})
        )
        .await
        .1,
        receipt
    );
    assert_eq!(std::fs::read_to_string(count).unwrap(), "1");
}

#[tokio::test]
async fn new_unaccepted_material_is_bound_confirmed_and_exactly_replayed_after_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let script = dir.path().join("worker.py");
    let marker = dir.path().join("calls");
    std::fs::write(&script,format!("import json,sys\nfrom pathlib import Path\np=Path({})\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\ncontext=Path(sys.argv[1]).read_text()\nassert context=='原文😀'\nprint(json.dumps({{'answer':'SYNTHETIC answer','model':'fixture','endpoint':'http://127.0.0.1:1234/v1','protocol':'synthetic','loss_receipt':{{'params':{{'authority':'candidate'}}}}}}))\n",serde_json::to_string(&marker).unwrap())).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let staging = dir.path().join("staging");
    let routes = [("machine.answer", script.clone())];
    let open = || Executor::open_routes(&db, &staging, &python, &script, &routes);
    let executor = open().await.unwrap();
    let saved=executor.store().submit_wait(|c|document::create_optional(c,None,None,"new material",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"前缀原文😀后缀"}]}]}))).await.unwrap().unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let mut body = json!({"request_id":"material_request","material":{"kind":"document","document_id":saved["document_id"],"version":1,"content_sha256":saved["content_sha256"],"block_id":null},"selection":{"start_utf16":2,"end_utf16":6,"quote_sha256":hash("原文😀".as_bytes())},"question":"这段说什么","purpose":"学习材料","model":null,"max_tokens":128,"timeout_s":5,"preview":false,"confirmed_plan_sha256":null});
    assert_eq!(
        call(&router, "/api/v1/material/questions", body.clone())
            .await
            .0,
        403
    );
    assert!(!marker.exists());
    let (status, context) = call(
        &router,
        "/api/v1/material/context",
        json!({"material":body["material"],"selection":body["selection"]}),
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(context["text"], "原文😀");
    assert!(!marker.exists());
    body["preview"] = json!(true);
    let (status, preview) = call(&router, "/api/v1/material/questions", body.clone()).await;
    assert_eq!(status, 200, "{preview}");
    assert_eq!(
        preview["plan"]["destination_candidates"],
        json!(["http://127.0.0.1:1234/v1"])
    );
    assert!(!marker.exists());
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    let (status, receipt) = call(&router, "/api/v1/material/questions", body.clone()).await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["outcome"], "succeeded");
    assert_eq!(receipt["answer"]["endpoint"], "http://127.0.0.1:1234/v1");
    assert_eq!(
        call(&router, "/api/v1/material/questions", body.clone())
            .await
            .1,
        receipt
    );
    assert_eq!(std::fs::read_to_string(&marker).unwrap(), "1");
    drop(router);
    drop(executor);
    let restarted = archeaxis_api::runtime::router(open().await.unwrap());
    assert_eq!(
        call(&restarted, "/api/v1/material/questions", body.clone())
            .await
            .1,
        receipt
    );
    let history = call(
        &restarted,
        "/api/v1/material/questions/status",
        json!({"request_id":null}),
    )
    .await
    .1;
    assert_eq!(
        history["plans"][0]["request"]["request_id"],
        "material_request"
    );
    assert_eq!(
        call(
            &restarted,
            "/api/v1/material/questions/status",
            json!({"request_id":"material_request"})
        )
        .await
        .1,
        receipt
    );
    body["question"] = json!("changed");
    body["preview"] = json!(true);
    let changed = call(&restarted, "/api/v1/material/questions", body.clone())
        .await
        .1;
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = changed["plan_sha256"].clone();
    assert_eq!(
        call(&restarted, "/api/v1/material/questions", body).await.0,
        409
    );
}
#[tokio::test]
async fn imported_text_extracts_and_answers_without_entering_accepted_knowledge() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("answer.py");
    std::fs::write(&script,"import json,sys\nfrom pathlib import Path\nassert Path(sys.argv[1]).read_text()=='新导入材料😀'\nprint(json.dumps({'answer':'SYNTHETIC imported answer','model':'fixture','endpoint':'http://127.0.0.1:1234/v1','protocol':'synthetic'}))\n").unwrap();
    let worker = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../services/python-workers/transport/text_ndjson.py");
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &dir.path().join("w.sqlite"),
        &dir.path().join("staging"),
        &python,
        &worker,
        &[("machine.answer", script)],
    )
    .await
    .unwrap();
    let source_id = executor
        .store()
        .submit_wait(|c| {
            let id = match source::import_source(c, "新导入材料😀".as_bytes(), "new.txt", None)
                .unwrap()
            {
                source::ImportOutcome::Imported { source_id, .. } => source_id,
                _ => unreachable!(),
            };
            jobs::enqueue(c, "imported-text-job", "text", &id).unwrap();
            id
        })
        .await
        .unwrap();
    executor
        .execute(
            "imported-text-job",
            "material-text",
            5000,
            &Cancellation::new(),
        )
        .await
        .unwrap();
    let material = executor.store().submit_wait(move |c| {
        c.query_row("SELECT j.state,t.transform_id,t.text,s.sha256 FROM jobs j JOIN transforms t ON t.transform_id=j.transform_id JOIN sources s ON s.source_id=j.input_ref WHERE j.job_id='imported-text-job'", [], |r| {
            let state:String=r.get(0)?;assert_eq!(state,"succeeded");
            let content:String=r.get(2)?;
            Ok(json!({"kind":"transform","source_id":source_id,"raw_sha256":r.get::<_,String>(3)?,"job_id":"imported-text-job","transform_id":r.get::<_,i64>(1)?,"transform_sha256":hash(content.as_bytes())}))
        }).unwrap()
    }).await.unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let mut body = json!({"request_id":"imported_question","material":material,"selection":null,"question":"解释材料","purpose":"学习","model":null,"max_tokens":128,"timeout_s":5,"preview":true,"confirmed_plan_sha256":null});
    let (status, preview) = call(&router, "/api/v1/material/questions", body.clone()).await;
    assert_eq!(status, 200, "{preview}");
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    let readable_material = body["material"].clone();
    let (status, receipt) = call(&router, "/api/v1/material/questions", body).await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["outcome"], "succeeded");
    assert_eq!(receipt["answer"]["answer"], "SYNTHETIC imported answer");
    machine_enabled(&router, false).await;
    let (code, context) = call(
        &router,
        "/api/v1/material/context",
        json!({"material":readable_material,"selection":null}),
    )
    .await;
    assert_eq!(code, 200);
    assert_eq!(context["text"], "新导入材料😀");
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
}
#[tokio::test]
async fn cancellation_preserves_frozen_material_request_and_returns_no_answer() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("slow.py");
    let started = dir.path().join("started");
    std::fs::write(&script,format!("import time\nfrom pathlib import Path\nPath({}).write_text('SYNTHETIC started')\ntime.sleep(20)\n",serde_json::to_string(&started).unwrap())).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap();
    let saved=executor.store().submit_wait(|c|document::create_optional(c,None,None,"note",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"SYNTHETIC material"}]}]}))).await.unwrap().unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let mut body = json!({"request_id":"cancel_request","material":{"kind":"document","document_id":saved["document_id"],"version":1,"content_sha256":saved["content_sha256"],"block_id":null},"selection":null,"question":"question","purpose":"learning","model":null,"max_tokens":128,"timeout_s":10,"preview":true,"confirmed_plan_sha256":null});
    let preview = call(&router, "/api/v1/material/questions", body.clone())
        .await
        .1;
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    let worker_router = router.clone();
    let task =
        tokio::spawn(async move { call(&worker_router, "/api/v1/material/questions", body).await });
    let limit = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while !started.exists() && std::time::Instant::now() < limit {
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }
    assert!(started.exists());
    let cancelled = call(
        &router,
        "/api/v1/material/questions/cancel",
        json!({"request_id":"cancel_request"}),
    )
    .await
    .1;
    assert_eq!(cancelled["cancel_requested"], true);
    let (_, receipt) = task.await.unwrap();
    assert_eq!(receipt["outcome"], "failed");
    assert_eq!(receipt["reason_code"], "material_question_cancelled");
    assert!(receipt["answer"].is_null());
    assert_eq!(
        call(
            &router,
            "/api/v1/material/questions/status",
            json!({"request_id":"cancel_request"})
        )
        .await
        .1,
        receipt
    );
}
#[test]
fn transform_binding_and_unicode_selection_refuse_wrong_identity_without_knowledge() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("w.sqlite").to_str().unwrap())
            .unwrap();
    let raw = b"synthetic pdf bytes";
    let source_id = match source::import_source(&mut c, raw, "material.pdf", None).unwrap() {
        source::ImportOutcome::Imported { source_id, .. }
        | source::ImportOutcome::Duplicate { source_id, .. } => source_id,
    };
    let text = "原文😀";
    let transform_id =
        source::record_transform(&mut c, &source_id, "synthetic-pdf", text, None).unwrap();
    c.execute("INSERT INTO jobs(job_id,kind,state,input_ref,engine,transform_id) VALUES('pdf-job','pdf','succeeded',?1,'synthetic-pdf',?2)",rusqlite::params![source_id,transform_id]).unwrap();
    let material = archeaxis_domain::material_question::Material::Transform {
        source_id: source_id.clone(),
        raw_sha256: hash(raw),
        job_id: "pdf-job".into(),
        transform_id,
        transform_sha256: hash(text.as_bytes()),
    };
    assert_eq!(
        archeaxis_domain::material_question::prepare(&c, &material, None)
            .unwrap()
            .0,
        text
    );
    for (start, end) in [(2, 3), (1, 10), (2, 2)] {
        assert!(
            archeaxis_domain::material_question::prepare(
                &c,
                &material,
                Some(&archeaxis_domain::material_question::Selection {
                    start_utf16: start,
                    end_utf16: end,
                    quote_sha256: hash("😀".as_bytes())
                })
            )
            .is_err()
        )
    }
    let wrong = archeaxis_domain::material_question::Material::Transform {
        source_id,
        raw_sha256: hash(b"wrong"),
        job_id: "pdf-job".into(),
        transform_id,
        transform_sha256: hash(text.as_bytes()),
    };
    assert!(archeaxis_domain::material_question::prepare(&c, &wrong, None).is_err());
    assert_eq!(
        c.query_row("SELECT COUNT(*) FROM knowledge", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        0
    );
}

async fn async_fixture(dir: &std::path::Path) -> (Executor, Router, Value) {
    let script = dir.join("async-worker.py");
    let count = dir.join("async-count");
    let started = dir.join("async-started");
    let release = dir.join("async-release");
    std::fs::write(&script, format!("import json,time,os\nfrom pathlib import Path\np=Path({})\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\nPath({}).write_text(str(os.getpid()))\nwhile not Path({}).exists(): time.sleep(0.01)\nprint(json.dumps({{'answer':'SYNTHETIC owned async answer','model':'fixture','endpoint':'http://127.0.0.1:1234/v1','protocol':'synthetic','truncated':False}}))\n", serde_json::to_string(&count).unwrap(), serde_json::to_string(&started).unwrap(), serde_json::to_string(&release).unwrap())).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &dir.join("async.sqlite"),
        &dir.join("async-staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap();
    let doc = executor.store().submit_wait(|c| document::create_optional(c,None,None,"synthetic async material",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Bounded synthetic material"}]}]}))).await.unwrap().unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let body = json!({"request_id":"async_material","material":{"kind":"document","document_id":doc["document_id"],"version":1,"content_sha256":doc["content_sha256"],"block_id":null},"selection":null,"question":"question","purpose":"learning","model":null,"max_tokens":128,"timeout_s":5,"preview":true,"confirmed_plan_sha256":null});
    (executor, router, body)
}
async fn wait_started(dir: &std::path::Path) {
    // Parallel Rust tests share the runner; a cold Python worker can take longer
    // than three seconds to reach its first statement on a loaded machine.
    tokio::time::timeout(std::time::Duration::from_secs(15), async {
        while !dir.join("async-started").exists() {
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
}
async fn material_terminal(router: &Router, request: &str) -> Value {
    tokio::time::timeout(std::time::Duration::from_secs(7), async {
        loop {
            let (status, body) = call(
                router,
                "/api/v1/material/questions/status",
                json!({"request_id":request}),
            )
            .await;
            assert_eq!(status, 200);
            if body["schema"] == "archeaxis.material-answer/v1" {
                return body;
            }
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap()
}
#[tokio::test]
async fn synchronous_disconnected_material_keeps_unknown_without_repeating_inference() {
    let dir = tempfile::tempdir().unwrap();
    let (_executor, router, mut body) = async_fixture(dir.path()).await;
    let preview = call(&router, "/api/v1/material/questions", body.clone())
        .await
        .1;
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    let client = router.clone();
    let waiting =
        tokio::spawn(async move { call(&client, "/api/v1/material/questions", body).await });
    wait_started(dir.path()).await;
    waiting.abort();
    assert!(waiting.await.unwrap_err().is_cancelled());
    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    let state = call(
        &router,
        "/api/v1/material/questions/status",
        json!({"request_id":"async_material"}),
    )
    .await
    .1;
    assert_eq!(state["execution_state"], "UNKNOWN");
    assert_eq!(state["provider_stop_state"], "UNKNOWN");
    assert_eq!(
        std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
        "1"
    );
}
#[tokio::test]
async fn asynchronous_admission_survives_disconnected_submitter_and_replays_one_durable_answer() {
    let dir = tempfile::tempdir().unwrap();
    let (executor, router, mut body) = async_fixture(dir.path()).await;
    body["execution_mode"] = json!("async");
    let (code, preview) = call(&router, "/api/v1/material/questions", body.clone()).await;
    assert_eq!(code, 200, "{preview}");
    assert_eq!(preview["plan"]["request"]["execution_mode"], "async");
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    let (code, ack) = call(
        &router,
        "/api/v1/material/questions/submissions",
        body.clone(),
    )
    .await;
    assert_eq!(code, 202, "{ack}");
    assert_eq!(ack["schema"], "archeaxis.material-question-admission/v1");
    assert_eq!(ack["request_id"], "async_material");
    assert_eq!(ack["workspace_id"], preview["plan"]["workspace_id"]);
    assert_eq!(ack["plan_sha256"], preview["plan_sha256"]);
    assert_eq!(ack["answer_published"], false);
    assert_eq!(ack["provider_stop_state"], "UNKNOWN");
    wait_started(dir.path()).await;
    let duplicate = call(
        &router,
        "/api/v1/material/questions/submissions",
        body.clone(),
    )
    .await;
    assert_eq!(duplicate.0, 202);
    assert_eq!(duplicate.1["request_id"], ack["request_id"]);
    std::fs::write(dir.path().join("async-release"), b"release").unwrap();
    let terminal = material_terminal(&router, "async_material").await;
    assert_eq!(terminal["outcome"], "succeeded");
    assert_eq!(terminal["answer"]["answer"], "SYNTHETIC owned async answer");
    assert_eq!(
        std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
        "1"
    );
    assert_eq!(
        call(&router, "/api/v1/material/questions/submissions", body)
            .await
            .1,
        terminal
    );
    drop(router);
    drop(executor);
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script = dir.path().join("async-worker.py");
    let reopened = Executor::open_routes(
        &dir.path().join("async.sqlite"),
        &dir.path().join("async-staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap();
    let reopened = archeaxis_api::runtime::router(reopened);
    assert_eq!(
        call(
            &reopened,
            "/api/v1/material/questions/status",
            json!({"request_id":"async_material"})
        )
        .await
        .1,
        terminal
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
        "1"
    );
}

async fn confirmed_async(router: &Router, mut body: Value) -> Value {
    body["execution_mode"] = json!("async");
    body["preview"] = json!(true);
    body["confirmed_plan_sha256"] = Value::Null;
    let (code, preview) = call(router, "/api/v1/material/questions", body.clone()).await;
    assert_eq!(code, 200, "{preview}");
    body["preview"] = json!(false);
    body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
    body
}

async fn machine_enabled(router: &Router, enabled: bool) {
    let response = tokio::time::timeout(
        std::time::Duration::from_secs(1),
        router.clone().oneshot(
            Request::builder()
                .method("PUT")
                .uri("/api/v1/capabilities/machine.answer/enabled")
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", "human")
                .body(Body::from(json!({"enabled":enabled}).to_string()))
                .unwrap(),
        ),
    )
    .await
    .expect("withdrawal must not wait for inference")
    .unwrap();
    assert_eq!(response.status(), 200);
}

#[tokio::test]
async fn machine_disable_withdraws_live_material_and_reenable_only_admits_new_requests() {
    for asynchronous in [false, true] {
        let dir = tempfile::tempdir().unwrap();
        let (_executor, router, mut body) = async_fixture(dir.path()).await;
        // User IDs cannot impersonate the Core-owned public-research registry prefix.
        let request_id = if asynchronous {
            "public_research_spoof"
        } else {
            "async_material"
        };
        body["request_id"] = json!(request_id);
        let mut body = confirmed_async(&router, body).await;
        if !asynchronous {
            body.as_object_mut().unwrap().remove("execution_mode");
            body["preview"] = json!(true);
            let (code, preview) = call(&router, "/api/v1/material/questions", body.clone()).await;
            assert_eq!(code, 200);
            body["preview"] = json!(false);
            body["confirmed_plan_sha256"] = preview["plan_sha256"].clone();
        }
        let client = router.clone();
        let running_body = body.clone();
        let request = tokio::spawn(async move {
            call(
                &client,
                if asynchronous {
                    "/api/v1/material/questions/submissions"
                } else {
                    "/api/v1/material/questions"
                },
                running_body,
            )
            .await
        });
        wait_started(dir.path()).await;
        machine_enabled(&router, false).await;
        // Capability withdrawal does not delete the underlying ordinary material.
        let (code, context) = call(
            &router,
            "/api/v1/material/context",
            json!({"material":body["material"],"selection":null}),
        )
        .await;
        assert_eq!(code, 200);
        assert_eq!(context["text"], "Bounded synthetic material");
        machine_enabled(&router, true).await;
        std::fs::write(dir.path().join("async-release"), b"release").unwrap();
        let (code, response) = request.await.unwrap();
        assert_eq!(code, if asynchronous { 202 } else { 200 }, "{response}");
        let terminal = material_terminal(&router, request_id).await;
        assert_eq!(terminal["outcome"], "failed", "{terminal}");
        assert_eq!(terminal["reason_code"], "material_question_cancelled");
        assert_eq!(terminal["provider_stop_state"], "UNKNOWN");
        assert!(terminal["answer"].is_null());

        let mut fresh = body.clone();
        fresh["request_id"] = json!("new_after_enable");
        let fresh = confirmed_async(&router, fresh).await;
        assert_eq!(
            call(&router, "/api/v1/material/questions/submissions", fresh)
                .await
                .0,
            202
        );
        let successful = material_terminal(&router, "new_after_enable").await;
        assert_eq!(successful["outcome"], "succeeded", "{successful}");
        machine_enabled(&router, false).await;
        assert_eq!(
            call(
                &router,
                "/api/v1/material/questions/status",
                json!({"request_id":"new_after_enable"})
            )
            .await
            .1,
            successful
        );
        assert_eq!(
            call(
                &router,
                "/api/v1/material/questions/status",
                json!({"request_id":request_id})
            )
            .await
            .1,
            terminal
        );
    }
}
#[tokio::test]
async fn asynchronous_capacity_is_not_a_queue_and_explicit_cancel_keeps_provider_unknown() {
    let dir = tempfile::tempdir().unwrap();
    let (_executor, router, body) = async_fixture(dir.path()).await;
    let mut invalid_mode = body.clone();
    invalid_mode["execution_mode"] = Value::Null;
    assert_eq!(
        call(&router, "/api/v1/material/questions", invalid_mode)
            .await
            .0,
        400
    );
    let body = confirmed_async(&router, body).await;
    assert_eq!(
        call(&router, "/api/v1/material/questions", body.clone())
            .await
            .0,
        422
    );
    let mut no_confirmation = body.clone();
    no_confirmation["confirmed_plan_sha256"] = Value::Null;
    assert_eq!(
        call(
            &router,
            "/api/v1/material/questions/submissions",
            no_confirmation
        )
        .await
        .0,
        403
    );
    assert!(!dir.path().join("async-count").exists());
    assert_eq!(
        call(
            &router,
            "/api/v1/material/questions/submissions",
            body.clone()
        )
        .await
        .0,
        202
    );
    wait_started(dir.path()).await;
    let mut other = body.clone();
    other["request_id"] = json!("async_other");
    let other = confirmed_async(&router, other).await;
    assert_eq!(
        call(&router, "/api/v1/material/questions/submissions", other)
            .await
            .0,
        429
    );
    assert_eq!(
        call(
            &router,
            "/api/v1/material/questions/status",
            json!({"request_id":"async_other"})
        )
        .await
        .1["execution_state"],
        "NOT_EXECUTED"
    );
    let mut changed = body.clone();
    changed["question"] = json!("changed question");
    let changed = confirmed_async(&router, changed).await;
    assert_eq!(
        call(&router, "/api/v1/material/questions/submissions", changed)
            .await
            .0,
        409
    );
    let cancel = call(
        &router,
        "/api/v1/material/questions/cancel",
        json!({"request_id":"async_material"}),
    )
    .await;
    assert_eq!(cancel.0, 200);
    assert_eq!(cancel.1["cancel_requested"], true);
    assert_eq!(cancel.1["provider_stop_state"], "UNKNOWN");
    let terminal = material_terminal(&router, "async_material").await;
    assert_eq!(terminal["outcome"], "failed");
    assert_eq!(terminal["reason_code"], "material_question_cancelled");
    assert!(terminal["answer"].is_null());
    assert_eq!(terminal["provider_stop_state"], "UNKNOWN");
    assert_eq!(
        std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
        "1"
    );
    assert_eq!(
        call(&router, "/api/v1/material/questions/submissions", body)
            .await
            .1,
        terminal
    );
}
#[tokio::test]
async fn asynchronous_orphaned_durable_claim_is_unknown_and_never_retried() {
    let dir = tempfile::tempdir().unwrap();
    let (executor, router, body) = async_fixture(dir.path()).await;
    let mut preview_body = body.clone();
    preview_body["execution_mode"] = json!("async");
    let preview = call(&router, "/api/v1/material/questions", preview_body)
        .await
        .1;
    let body = confirmed_async(&router, body).await;
    let plan = preview["plan"].clone();
    let task_id = "material_answer_".to_owned() + &hash(b"async_material");
    let claim_key = "machine_execution_claim_".to_owned() + &hash(task_id.as_bytes());
    executor.store().submit_wait(move|c| {
        c.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",rusqlite::params![format!("material_request_{task_id}"),plan.to_string()]).unwrap();
        let claim=json!({"schema":"archeaxis.machine-execution-claim/v1","state":"IN_FLIGHT","request_sha256":hash(plan.to_string().as_bytes()),"attempt":1,"max_attempts":3});
        c.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",rusqlite::params![claim_key,claim.to_string()]).unwrap();
    }).await.unwrap();
    let state = call(
        &router,
        "/api/v1/material/questions/status",
        json!({"request_id":"async_material"}),
    )
    .await
    .1;
    assert_eq!(state["execution_state"], "UNKNOWN");
    assert_eq!(
        call(&router, "/api/v1/material/questions/submissions", body)
            .await
            .0,
        409
    );
    assert!(!dir.path().join("async-count").exists());
}
#[tokio::test]
async fn asynchronous_restore_fence_withholds_late_answer_and_preserves_plan() {
    let dir = tempfile::tempdir().unwrap();
    let (executor, router, body) = async_fixture(dir.path()).await;
    let body = confirmed_async(&router, body).await;
    assert_eq!(
        call(
            &router,
            "/api/v1/material/questions/submissions",
            body.clone()
        )
        .await
        .0,
        202
    );
    wait_started(dir.path()).await;
    executor
        .store()
        .submit_wait(|c| {
            let tx = c.transaction().unwrap();
            archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
            tx.commit().unwrap();
        })
        .await
        .unwrap();
    std::fs::write(dir.path().join("async-release"), b"release").unwrap();
    // A live owned lease is RUNNING. Its close/drop follows worker cleanup;
    // the fenced result must remain UNKNOWN without a published machine task.
    tokio::time::timeout(std::time::Duration::from_secs(3), async {
        loop {
            let state = call(
                &router,
                "/api/v1/material/questions/status",
                json!({"request_id":"async_material"}),
            )
            .await
            .1;
            if state["execution_state"] == "UNKNOWN" {
                break;
            }
            assert_eq!(state["execution_state"], "RUNNING");
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    assert_eq!(
        executor
            .store()
            .submit_wait(|c| c.query_row::<i64, _, _>(
                "SELECT count(*) FROM machine_tasks WHERE task_id LIKE 'material_answer_%'",
                [],
                |r| r.get(0)
            ))
            .await
            .unwrap()
            .unwrap(),
        0
    );
    assert_eq!(
        call(&router, "/api/v1/material/questions/submissions", body)
            .await
            .0,
        409
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
        "1"
    );
}

#[tokio::test]
async fn asynchronous_budget_and_dropped_submitter_preserve_owned_identity() {
    let dir = tempfile::tempdir().unwrap();
    let (_executor, router, body) = async_fixture(dir.path()).await;
    let mut oversized = body.clone();
    oversized["execution_mode"] = json!("async");
    oversized["timeout_s"] = json!(121);
    assert_eq!(
        call(&router, "/api/v1/material/questions", oversized)
            .await
            .0,
        422
    );
    let body = confirmed_async(&router, body).await;
    let client = router.clone();
    let submitted =
        tokio::spawn(
            async move { call(&client, "/api/v1/material/questions/submissions", body).await },
        );
    wait_started(dir.path()).await;
    submitted.abort();
    let _ = submitted.await;
    // Submission may have returned its ACK already; neither disconnect path owns the lease.
    assert_eq!(
        call(
            &router,
            "/api/v1/material/questions/status",
            json!({"request_id":"async_material"})
        )
        .await
        .1["execution_state"],
        "RUNNING"
    );
    std::fs::write(dir.path().join("async-release"), b"release").unwrap();
    assert_eq!(
        material_terminal(&router, "async_material").await["outcome"],
        "succeeded"
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
        "1"
    );
}

#[tokio::test]
async fn asynchronous_terminal_replay_after_configuration_or_restore_is_historical_only() {
    for change in ["configuration", "restore"] {
        let dir = tempfile::tempdir().unwrap();
        let (executor, router, body) = async_fixture(dir.path()).await;
        let body = confirmed_async(&router, body).await;
        let mut unadmitted = body.clone();
        unadmitted["request_id"] = json!("not_yet_admitted");
        let unadmitted = confirmed_async(&router, unadmitted).await;
        assert_eq!(
            call(
                &router,
                "/api/v1/material/questions/submissions",
                body.clone()
            )
            .await
            .0,
            202
        );
        wait_started(dir.path()).await;
        std::fs::write(dir.path().join("async-release"), b"release").unwrap();
        let receipt = material_terminal(&router, "async_material").await;
        assert_eq!(receipt["outcome"], "succeeded");
        if change == "configuration" {
            // An actual configuration transaction in this synthetic workspace;
            // no service/model/provider/global profile is changed.
            executor
                .store()
                .submit_wait(|c| {
                    let prior = archeaxis_domain::model_configuration::read(c).unwrap();
                    let saved =
                        archeaxis_domain::model_configuration::put(c, prior.revision, prior)
                            .unwrap();
                    assert_eq!(saved.revision, 1);
                })
                .await
                .unwrap();
        } else {
            executor
                .store()
                .submit_wait(|c| {
                    let tx = c.transaction().unwrap();
                    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx)
                        .unwrap();
                    tx.commit().unwrap();
                })
                .await
                .unwrap();
        }
        let (code, replayed) = call(
            &router,
            "/api/v1/material/questions/submissions",
            body.clone(),
        )
        .await;
        assert_eq!(code, 200, "{change}: {replayed}");
        assert_eq!(replayed, receipt);
        assert_eq!(
            call(
                &router,
                "/api/v1/material/questions/status",
                json!({"request_id":"async_material"})
            )
            .await
            .1,
            receipt
        );
        // Historical read never admits a new request under the old plan/config/epoch.
        let (code, _) = call(
            &router,
            "/api/v1/material/questions/submissions",
            unadmitted,
        )
        .await;
        assert_eq!(code, if change == "configuration" { 422 } else { 403 });
        let mut wrong = body.clone();
        wrong["question"] = json!("different frozen question");
        assert_eq!(
            call(&router, "/api/v1/material/questions/submissions", wrong)
                .await
                .0,
            409
        );
        let mut unconfirmed = body;
        unconfirmed["confirmed_plan_sha256"] = Value::Null;
        assert_eq!(
            call(
                &router,
                "/api/v1/material/questions/submissions",
                unconfirmed
            )
            .await
            .0,
            403
        );
        assert_eq!(
            std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
            "1"
        );
    }
}

// SYNTHETIC: actual Core, private stdin, owned worker, MockVault and fake HTTP.
#[tokio::test]
async fn cloud_owned_worker_vault_transport_publication_cancel_and_replay() {
    for cancel in [false, true] {
        let dir = tempfile::tempdir().unwrap();
        let (executor, router, mut body) = async_fixture(dir.path()).await;
        let resolved = executor
            .store()
            .submit_wait(|conn| {
                use archeaxis_domain::model_configuration::*;
                let mut c = read(conn).unwrap();
                c.profiles.insert(
                    "cloud".into(),
                    Profile {
                        endpoint: "https://api.openai.com/v1".into(),
                        protocol: "openai-buffered".into(),
                        model: "synthetic-model".into(),
                        credential_ref: Some(format!("aak_cred_{}", "c".repeat(32))),
                        max_tokens: 128,
                        timeout_s: 5,
                    },
                );
                c.bindings.push(Binding {
                    purpose: Purpose::Material,
                    lane: Lane::Fast,
                    profile_id: "cloud".into(),
                });
                put(conn, 0, c).unwrap();
                resolve(conn, Purpose::Material, Lane::Fast).unwrap()
            })
            .await
            .unwrap();
        body["model_configuration"] = serde_json::to_value(&resolved).unwrap();
        body["model"] = json!("synthetic-model");
        body["cloud_upload_confirmed"] = json!(true);
        body["cloud_unknown_cost_confirmed"] = json!(true);
        let source = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/python-workers/machine/material_cloud_worker.py")
            .canonicalize()
            .unwrap();
        let script = format!(
            r#"import importlib.util,json,sys,time,socket
from pathlib import Path
from types import SimpleNamespace
def forbidden(*a,**k): raise RuntimeError('NO_NETWORK')
socket.getaddrinfo=socket.create_connection=socket.socket.connect=forbidden
spec=importlib.util.spec_from_file_location('owned', {source})
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def vault(ref):
 assert ref == 'aak_cred_'+'c'*32
 return bytearray(b'SYNTHETIC_PRIVATE_KEY')
def transport(url, **kwargs):
 assert kwargs['headers']['Authorization']=='Bearer SYNTHETIC_PRIVATE_KEY'
 p=Path({count})
 p.write_text(str(int(p.read_text())+1) if p.exists() else '1')
 Path({started}).touch()
 while not Path({release}).exists(): time.sleep(.01)
 return SimpleNamespace(url=url,status=200,headers={{'content-type':'application/json'}},body=json.dumps({{'model':'synthetic-model','choices':[{{'message':{{'content':'SYNTHETIC cloud answer'}},'finish_reason':'stop'}}]}}).encode())
print(json.dumps(m.run(sys.stdin.buffer,resolver=vault,transport=transport)))
"#,
            source = serde_json::to_string(&source).unwrap(),
            count = serde_json::to_string(&dir.path().join("async-count")).unwrap(),
            started = serde_json::to_string(&dir.path().join("async-started")).unwrap(),
            release = serde_json::to_string(&dir.path().join("async-release")).unwrap()
        );
        std::fs::write(dir.path().join("material_cloud_worker.py"), script).unwrap();
        let body = confirmed_async(&router, body).await;
        let (status, ack) = call(
            &router,
            "/api/v1/material/questions/submissions",
            body.clone(),
        )
        .await;
        assert_eq!(status, 202, "{ack}");
        wait_started(dir.path()).await;
        if cancel {
            assert_eq!(
                call(
                    &router,
                    "/api/v1/material/questions/cancel",
                    json!({"request_id":"async_material"})
                )
                .await
                .0,
                200
            );
        }
        std::fs::write(dir.path().join("async-release"), "release").unwrap();
        let receipt = material_terminal(&router, "async_material").await;
        assert_eq!(
            receipt["outcome"],
            if cancel { "failed" } else { "succeeded" },
            "{receipt}"
        );
        if !cancel {
            assert_eq!(receipt["answer"]["answer"], "SYNTHETIC cloud answer");
        }
        assert!(!receipt.to_string().contains("SYNTHETIC_PRIVATE_KEY"));
        assert_eq!(
            call(&router, "/api/v1/material/questions/submissions", body)
                .await
                .1,
            receipt
        );
        assert_eq!(
            std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
            "1"
        );
        drop(router);
        drop(executor);
        let db = std::fs::read(dir.path().join("async.sqlite")).unwrap();
        assert!(
            !db.windows(b"SYNTHETIC_PRIVATE_KEY".len())
                .any(|w| w == b"SYNTHETIC_PRIVATE_KEY")
        );
        let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
        let script = dir.path().join("async-worker.py");
        let reopened = Executor::open_routes(
            &dir.path().join("async.sqlite"),
            &dir.path().join("async-staging"),
            &python,
            &script,
            &[("machine.answer", script.clone())],
        )
        .await
        .unwrap();
        let router = archeaxis_api::runtime::router(reopened);
        assert_eq!(
            call(
                &router,
                "/api/v1/material/questions/status",
                json!({"request_id":"async_material"})
            )
            .await
            .1,
            receipt
        );
        assert_eq!(
            std::fs::read_to_string(dir.path().join("async-count")).unwrap(),
            "1"
        );
    }
}
