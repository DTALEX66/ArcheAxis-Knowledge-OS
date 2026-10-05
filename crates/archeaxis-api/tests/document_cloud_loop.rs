//! Synthetic owned-worker protocol integration, not evidence of a real cloud/provider call.
use archeaxis_application::executor::{DocumentCheckConfig, Executor};
use axum::{Router, body::Body, http::Request};
use serde_json::{Value, json};
use tower::ServiceExt;
async fn call(router: &Router, method: &str, path: &str, body: Value, actor: &str) -> (u16, Value) {
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .method(method)
                .uri(path)
                .header("content-type", "application/json")
                .header("x-archeaxis-actor", actor)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status().as_u16();
    let bytes = axum::body::to_bytes(response.into_body(), 1048576)
        .await
        .unwrap();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}
#[tokio::test]
async fn configured_worker_is_outside_writer_transaction_and_old_version_readback_survives_restart()
{
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("db.sqlite");
    let ready = dir.path().join("ready");
    let release = dir.path().join("release");
    let script = dir.path().join("worker.py");
    let source = format!(
        r#"import hashlib,json,sys,time
from pathlib import Path
request=json.load(sys.stdin)
ready=Path({ready});release=Path({release})
ready.write_text('fixture-ready')
deadline=time.monotonic()+10
while not release.exists() and time.monotonic()<deadline: time.sleep(.01)
assert release.exists(), 'fixture timeout'
raw=json.dumps({{'status':'uncertain','basis':'synthetic fixture only'}})
digest=hashlib.sha256(b'fixture-not-network').hexdigest()
result={{'schema':'archeaxis.document-check.response/v1',**{{k:request[k] for k in ('attempt_id','request_check_id','document_id','version','content_sha256','dimension')}},'outcome':'succeeded','status':'uncertain','reason':None,'basis':'synthetic fixture only','raw_response':raw,'engine_receipt':{{'provider':request['config']['provider'],'requested_model':request['config']['model'],'model':'fixture-actual','prompt_sha256':digest,'response_sha256':hashlib.sha256(raw.encode()).hexdigest(),'tokens_used':1,'finish_reason':'stop'}},'retrieval_receipts':[{{'kind':kind,'body_sha256':digest,'http_status':200,'bytes':19,'retrieved_at':time.time()}} for kind in ('search','article')]}}
print(json.dumps(result))
"#,
        ready = serde_json::to_string(&ready.to_string_lossy()).unwrap(),
        release = serde_json::to_string(&release.to_string_lossy()).unwrap()
    );
    std::fs::write(&script, source).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &database,
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap()
    .with_document_check_config(Some(DocumentCheckConfig {
        provider: "fixture".into(),
        model: "fixture/explicit".into(),
        endpoint: None,
        max_tokens: 128,
        timeout_seconds: 10,
        search_limit: 1,
    }))
    .unwrap();
    let router = archeaxis_api::runtime::router(executor.clone());
    let (status,document)=call(&router,"POST","/api/v1/documents",json!({"title":"ordinary","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"saved original document"}]}]}}),"human").await;
    assert_eq!(status, 201);
    let id = document["document_id"].as_str().unwrap();
    let checks = format!("/api/v1/documents/{id}/checks");
    let execute = format!("{checks}/execute");
    let (status, pending) = call(
        &router,
        "POST",
        &checks,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud"}),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    let body = json!({"check_id":pending["check_id"],"expected_content_sha256":document["content_sha256"]});
    assert_eq!(
        call(&router, "POST", &execute, body.clone(), "machine")
            .await
            .0,
        403
    );
    assert!(!ready.exists());
    let launched_router = router.clone();
    let task =
        tokio::spawn(async move { call(&launched_router, "POST", &execute, body, "human").await });
    tokio::time::timeout(std::time::Duration::from_secs(5), async {
        while !ready.exists() {
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }
    })
    .await
    .unwrap();
    let (status,new)=call(&router,"PUT",&format!("/api/v1/documents/{id}/draft"),json!({"expected_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"save never waits for cloud"}]}]}}),"human").await;
    assert_eq!(status, 200);
    assert_eq!(new["version"], 2);
    std::fs::write(&release, b"release fixture").unwrap();
    let (status, terminal) = task.await.unwrap();
    assert_eq!(status, 201, "{terminal}");
    assert_eq!(terminal["version"], 1);
    assert_eq!(terminal["execution_verified"], true);
    assert_eq!(terminal["status"], "uncertain");
    assert_eq!(terminal["actor"], "machine");
    drop(router);
    drop(executor);
    let restarted = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let history = call(
        &restarted,
        "GET",
        &format!("{checks}?version=1"),
        Value::Null,
        "human",
    )
    .await
    .1;
    assert_eq!(history["historical"], true);
    assert_eq!(history["checks"].as_array().unwrap().len(), 3);
    assert_eq!(
        call(
            &restarted,
            "GET",
            &format!("/api/v1/documents/{id}"),
            Value::Null,
            "human"
        )
        .await
        .1["text_projection"],
        "save never waits for cloud"
    );
}

#[tokio::test]
async fn malformed_flood_and_timeout_are_failed_and_explicitly_retryable() {
    for (script_body, expected_reason) in [
        (
            "import sys\nsys.stdin.read()\nprint('{}')\n",
            "invalid_worker_response",
        ),
        (
            "import sys\nsys.stdin.read()\nsys.stdout.write('x'*200000)\nsys.stdout.flush()\n",
            "output_exceeds_bound",
        ),
        (
            "import sys,time\nsys.stdin.read()\ntime.sleep(60)\n",
            "worker_timeout",
        ),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("worker.py");
        std::fs::write(&script, script_body).unwrap();
        let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
        let executor = Executor::open_routes(
            &dir.path().join("db.sqlite"),
            &dir.path().join("staging"),
            &python,
            &script,
            &[("machine.answer", script.clone())],
        )
        .await
        .unwrap()
        .with_document_check_config(Some(DocumentCheckConfig {
            provider: "fixture".into(),
            model: "fixture/explicit".into(),
            endpoint: None,
            max_tokens: 128,
            timeout_seconds: 1,
            search_limit: 1,
        }))
        .unwrap();
        let router = archeaxis_api::runtime::router(executor);
        let (_, doc) = call(
            &router,
            "POST",
            "/api/v1/documents",
            json!({"title":"preserved","editor_json":{"type":"doc","content":[]}}),
            "human",
        )
        .await;
        let id = doc["document_id"].as_str().unwrap();
        let path = format!("/api/v1/documents/{id}/checks");
        let (_, request) = call(
            &router,
            "POST",
            &path,
            json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud"}),
            "human",
        )
        .await;
        let body =
            json!({"check_id":request["check_id"],"expected_content_sha256":doc["content_sha256"]});
        let started = std::time::Instant::now();
        let (status, result) = tokio::time::timeout(
            std::time::Duration::from_secs(24),
            call(
                &router,
                "POST",
                &format!("{path}/execute"),
                body.clone(),
                "human",
            ),
        )
        .await
        .unwrap();
        assert_eq!(status, 201, "{result}");
        assert_eq!(result["status"], "failed");
        assert_eq!(result["reason"], expected_reason);
        assert_eq!(result["execution_verified"], false);
        assert!(started.elapsed() < std::time::Duration::from_secs(24));
        assert_eq!(
            call(&router, "POST", &format!("{path}/execute"), body, "human")
                .await
                .0,
            400
        );
        let history = call(
            &router,
            "GET",
            &format!("{path}?version=1"),
            Value::Null,
            "human",
        )
        .await
        .1;
        assert_eq!(history["checks"].as_array().unwrap().len(), 3);
        drop(router);
        let restarted = archeaxis_api::app(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
        let recovered = call(
            &restarted,
            "GET",
            &format!("{path}?version=1"),
            Value::Null,
            "human",
        )
        .await
        .1;
        assert!(
            recovered["checks"].as_array().unwrap().contains(&result),
            "terminal must survive complete Store reopen unchanged"
        );

        assert_eq!(
            call(
                &restarted,
                "GET",
                &format!("/api/v1/documents/{id}"),
                Value::Null,
                "human"
            )
            .await
            .1["version"],
            1
        );
    }
}
#[tokio::test]
async fn invalid_owned_config_preserves_save_and_records_failed_attempt() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("never.py");
    std::fs::write(&script, "raise AssertionError('must not execute')").unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &dir.path().join("db.sqlite"),
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap()
    .with_document_check_config(Some(DocumentCheckConfig {
        provider: "invalid-provider".into(),
        model: "invalid-provider/explicit".into(),
        endpoint: None,
        max_tokens: 128,
        timeout_seconds: 1,
        search_limit: 1,
    }))
    .unwrap()
    .with_document_check_config_error(None)
    .unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let (status, doc) = call(
        &router,
        "POST",
        "/api/v1/documents",
        json!({"title":"ordinary save","editor_json":{"type":"doc","content":[]}}),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    let id = doc["document_id"].as_str().unwrap();
    let path = format!("/api/v1/documents/{id}/checks");
    let (_, request) = call(
        &router,
        "POST",
        &path,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud"}),
        "human",
    )
    .await;
    let body =
        json!({"check_id":request["check_id"],"expected_content_sha256":doc["content_sha256"]});
    let (status, result) = call(&router, "POST", &format!("{path}/execute"), body, "human").await;
    assert_eq!(status, 201);
    assert_eq!(result["reason"], "invalid_config");
    assert_eq!(result["execution_verified"], false);
    let (status, updated) = call(
        &router,
        "PUT",
        &format!("/api/v1/documents/{id}/draft"),
        json!({"expected_version":1,"editor_json":{"type":"doc","content":[]}}),
        "human",
    )
    .await;
    assert_eq!(status, 200);
    assert_eq!(updated["version"], 2);
}

#[tokio::test]
async fn legitimate_material_failure_is_persisted_retryable_and_never_runs_worker() {
    let dir = tempfile::tempdir().unwrap();
    let database = dir.path().join("db.sqlite");
    let script = dir.path().join("never.py");
    let marker = dir.path().join("worker-called");
    std::fs::write(&script,format!("from pathlib import Path\nPath({}).write_text('unexpected')\nraise AssertionError('must not run')",serde_json::to_string(&marker.to_string_lossy()).unwrap())).unwrap();
    let python = std::path::PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor = Executor::open_routes(
        &database,
        &dir.path().join("staging"),
        &python,
        &script,
        &[("machine.answer", script.clone())],
    )
    .await
    .unwrap()
    .with_document_check_config(Some(DocumentCheckConfig {
        provider: "fixture".into(),
        model: "fixture/explicit".into(),
        endpoint: None,
        max_tokens: 128,
        timeout_seconds: 1,
        search_limit: 1,
    }))
    .unwrap();
    let router = archeaxis_api::runtime::router(executor);
    let text = "x".repeat(65001);
    let editor = json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":text}]}]});
    let (status, doc) = call(
        &router,
        "POST",
        "/api/v1/documents",
        json!({"title":"large ordinary note","editor_json":editor}),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    assert_eq!(doc["text_projection"], text);
    let id = doc["document_id"].as_str().unwrap();
    let path = format!("/api/v1/documents/{id}/checks");
    let (_, request) = call(
        &router,
        "POST",
        &path,
        json!({"version":1,"dimension":"professional_basis","provider_mode":"cloud"}),
        "human",
    )
    .await;
    let body =
        json!({"check_id":request["check_id"],"expected_content_sha256":doc["content_sha256"]});
    assert_eq!(
        call(
            &router,
            "POST",
            &format!("{path}/execute"),
            body.clone(),
            "machine"
        )
        .await
        .0,
        403
    );
    let wrong = json!({"check_id":request["check_id"],"expected_content_sha256":"wrong"});
    assert_eq!(
        call(&router, "POST", &format!("{path}/execute"), wrong, "human")
            .await
            .0,
        400
    );
    assert_eq!(
        call(
            &router,
            "GET",
            &format!("{path}?version=1"),
            Value::Null,
            "human"
        )
        .await
        .1["checks"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    let (status, failed) = call(
        &router,
        "POST",
        &format!("{path}/execute"),
        body.clone(),
        "human",
    )
    .await;
    assert_eq!(status, 201);
    assert_eq!(failed["status"], "failed");
    assert_eq!(failed["reason"], "cloud_snapshot_exceeds_bound");
    assert_eq!(failed["execution_verified"], false);
    assert!(!marker.exists());
    let mut retry = body;
    retry["retry_of_task_id"] = failed["attempt_id"].clone();
    let (_, retried) = call(&router, "POST", &format!("{path}/execute"), retry, "human").await;
    assert_eq!(retried["reason"], "cloud_snapshot_exceeds_bound");
    assert_ne!(retried["attempt_id"], failed["attempt_id"]);
    assert!(!marker.exists());
    drop(router);
    let restarted = archeaxis_api::app(database.to_str().unwrap()).unwrap();
    let history = call(
        &restarted,
        "GET",
        &format!("{path}?version=1"),
        Value::Null,
        "human",
    )
    .await
    .1;
    let rows = history["checks"].as_array().unwrap();
    assert_eq!(rows.len(), 5);
    assert!(rows.contains(&failed));
    assert!(rows.contains(&retried));
    let readback = call(
        &restarted,
        "GET",
        &format!("/api/v1/documents/{id}"),
        Value::Null,
        "human",
    )
    .await
    .1;
    assert!(
        readback["editor_json"] == doc["editor_json"],
        "persisted editor including generated stable IDs must remain unchanged"
    );
    assert_eq!(readback["content_sha256"], doc["content_sha256"]);
    assert_eq!(readback["text_projection"], text);
}
