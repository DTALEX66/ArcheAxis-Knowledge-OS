//! SYNTHETIC local worker, real Store/API protocol; no provider inference.
use archeaxis_application::{
    executor::{Cancellation, Executor},
    jobs,
};
use archeaxis_domain::{document, material_question::hash, source};
use axum::{Router, body::Body, http::Request};
use serde_json::{Value, json};
use tower::ServiceExt;
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
    let (status, receipt) = call(&router, "/api/v1/material/questions", body).await;
    assert_eq!(status, 200, "{receipt}");
    assert_eq!(receipt["outcome"], "succeeded");
    assert_eq!(receipt["answer"]["answer"], "SYNTHETIC imported answer");
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
