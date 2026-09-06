use axum::{body::Body, http::{Request, StatusCode}};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

async fn post(app: &axum::Router, path: &str, body: Value) -> (StatusCode, String) {
    let response = app.clone().oneshot(Request::post(path)
        .header("content-type", "application/json")
        .body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, String::from_utf8(bytes.to_vec()).unwrap())
}

#[tokio::test]
async fn real_python_loss_receipt_survives_http_restart_and_replay() {
    let dir = tempfile::tempdir().unwrap();
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let input = dir.path().join("中文 input.txt");
    let original = format!("\u{feff}{}", "行😀\r\n".repeat(5001));
    std::fs::write(&input, original.as_bytes()).unwrap();
    let python = std::env::var("ARCHEAXIS_PYTHON").expect("run cargo via scripts/runtime/dev.py to select the exact Python");
    let mut command = std::process::Command::new(python);
    command.arg("-B").arg(root.join("services/python-workers/document/worker_text.py")).arg(&input);
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW, no shell or visible console.
    }
    let output = command.output().unwrap();
    assert!(output.status.success(), "worker execution failed");
    let worker: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(worker["loss_receipt"]["covered"], 5000);
    assert_eq!(worker["loss_receipt"]["total"], 5001);
    assert_eq!(worker["loss_receipt"]["losses"].as_array().unwrap().len(), 2);
    // This slice projects the loss receipt, not document structure. The actual
    // structure output is asserted nonempty but its Core binding remains T05.
    assert_eq!(worker["structure"].as_array().unwrap().len(), 5000);
    let db = dir.path().join("api.sqlite");
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    use base64::Engine;
    let encoded = base64::engine::general_purpose::STANDARD.encode(original.as_bytes());
    let (_, text) = post(&app, "/api/v1/imports", json!({"name":"input.txt","content_base64":encoded})).await;
    let source: Value = serde_json::from_str(&text).unwrap();
    let enqueue = json!({"job_id":"python","kind":"text","input_ref":source["source_id"]});
    assert_eq!(post(&app, "/api/v1/jobs", enqueue).await.0, StatusCode::ACCEPTED);
    let payload = json!({"state":"succeeded","engine":worker["engine"],"text":worker["text"],"loss_receipt":worker["loss_receipt"]});
    assert_eq!(post(&app, "/api/v1/jobs/python/receipts", payload.clone()).await.0, StatusCode::OK);
    drop(app);
    let conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let stored: String = conn.query_row("SELECT loss_receipt FROM jobs WHERE job_id='python'", [], |r| r.get(0)).unwrap();
    assert_eq!(serde_json::from_str::<Value>(&stored).unwrap(), worker["loss_receipt"]);
    drop(conn);
    let app = archeaxis_api::app(db.to_str().unwrap()).unwrap();
    assert_eq!(post(&app, "/api/v1/jobs/python/receipts", payload).await.0, StatusCode::OK);
}

#[tokio::test]
async fn receipt_rejects_incoherent_payload_without_completing_job() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("api.sqlite");
    let app = archeaxis_api::app(path.to_str().unwrap()).unwrap();
    let (_, text) = post(&app, "/api/v1/imports", json!({"name":"x.txt","content_base64":"eA=="})).await;
    let source: Value = serde_json::from_str(&text).unwrap();
    let enqueue = json!({"job_id":"j","kind":"text","input_ref":source["source_id"]});
    assert_eq!(post(&app, "/api/v1/jobs", enqueue.clone()).await.0, StatusCode::ACCEPTED);
    for receipt in [
        json!({"state":"succeeded","engine":"worker","text":"x","error":"failed"}),
        json!({"state":"succeeded","engine":"worker","text":"x","structure":[{"unknown":"silently lost"}]}),
        json!({"state":"failed","error":"bad","text":"uncommitted output"}),
        json!({"state":"succeeded","engine":"worker","text":"x","loss_receipt":{
            "engine":"worker","engine_version":"1","params":{},"loss_note":null,
            "covered":2,"total":1,"coverage":1.0}}),
    ] {
        assert!(post(&app, "/api/v1/jobs/j/receipts", receipt).await.0.is_client_error());
        let (_, text) = post(&app, "/api/v1/jobs", enqueue.clone()).await;
        assert_eq!(serde_json::from_str::<Value>(&text).unwrap()["state"], "queued");
    }
}

#[tokio::test]
async fn job_responses_reflect_persisted_state_and_classify_conflicts() {
    let dir = tempfile::tempdir().unwrap();
    let app = archeaxis_api::app(dir.path().join("api.sqlite").to_str().unwrap()).unwrap();
    let (_, text) = post(&app, "/api/v1/imports", json!({"name":"x.txt","content_base64":"eA=="})).await;
    let source: Value = serde_json::from_str(&text).unwrap();
    let enqueue = json!({"job_id":"j","kind":"text","input_ref":source["source_id"]});
    assert_eq!(post(&app, "/api/v1/jobs", enqueue.clone()).await.0, StatusCode::ACCEPTED);
    let path = "/api/v1/jobs/j/receipts";
    assert_eq!(post(&app, path, json!({"state":"anything"})).await.0, StatusCode::BAD_REQUEST);
    assert_eq!(post(&app, path, json!({"state":"succeeded"})).await.0, StatusCode::BAD_REQUEST);
    let receipt = json!({"state":"succeeded","engine":"worker","text":"x"});
    assert_eq!(post(&app, path, receipt.clone()).await.0, StatusCode::OK);
    assert_eq!(post(&app, path, receipt).await.0, StatusCode::OK);
    let (_, readback) = post(&app, "/api/v1/jobs", enqueue).await;
    assert_eq!(serde_json::from_str::<Value>(&readback).unwrap()["state"], "succeeded");
    assert_eq!(post(&app, path, json!({"state":"failed","error":"late"})).await.0, StatusCode::CONFLICT);
    assert_eq!(post(&app, path, json!({"state":"succeeded","engine":"worker","text":"changed"})).await.0, StatusCode::CONFLICT);
    assert_eq!(post(&app, "/api/v1/jobs/missing/receipts", json!({"state":"failed"})).await.0, StatusCode::NOT_FOUND);
}
