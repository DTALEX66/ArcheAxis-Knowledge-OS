//! INTEGRATED Core/SQLite API candidate tests with a SYNTHETIC owned local worker.
//! NOT_EXECUTED until root integrates the helper and handler wiring.
use archeaxis_application::executor::Executor;
use archeaxis_domain::knowledge;
use axum::{Router,body::Body,http::Request};
use http_body_util::BodyExt;
use serde_json::{Value,json};
use std::path::{Path,PathBuf};
use tower::ServiceExt;

async fn call(router:&Router,method:&str,path:&str,body:Value)->(u16,Value) {
    let response=router.clone().oneshot(Request::builder().method(method).uri(path)
        .header("content-type","application/json").header("x-archeaxis-actor","human")
        .body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status=response.status().as_u16();let bytes=response.into_body().collect().await.unwrap().to_bytes();
    (status,serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}
fn editor(id:&str,state:&str)->Value {json!({"type":"doc","attrs":{"archeaxis_context_grant":{
    "schema":"archeaxis.context-grant/v1","purpose":"owned withheld race fixture","consumer":"local-machine",
    "operations":["answer","retest"],"knowledge_id":id,"provenance":[],"authorization_basis":"SYNTHETIC owner fixture",
    "expires_at":null,"state":state}},"content":[]})}
async fn fixture(dir:&Path)->(Router,Executor,String) {
    let python=PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let worker=dir.join("answer.py");
    std::fs::write(&worker,concat!(
        "import json,time\nfrom pathlib import Path\np=Path(__file__)\n",
        "count=p.with_suffix('.count')\ncount.write_text(str(int(count.read_text())+1) if count.exists() else '1')\n",
        "p.with_suffix('.ready').write_text('ready')\nend=time.monotonic()+10\n",
        "while not p.with_suffix('.release').exists():\n",
        " if time.monotonic()>end: raise RuntimeError('fixture release timeout')\n",
        " time.sleep(0.01)\n",
        "print(json.dumps({'answer':'SECRET SYNTHETIC WITHHELD ANSWER','model':'synthetic/actual-worker'}))\n"
    )).unwrap();
    let executor=Executor::open_routes(&dir.join("db.sqlite"),&dir.join("staging"),&python,
        &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/python-workers/transport/text_ndjson.py"),
        &[("machine.answer",worker)]).await.unwrap();
    let id=executor.store().submit(|conn|knowledge::create_knowledge(conn,"NOTE","SECRET SYNTHETIC CONTEXT","accepted",None,None,"owner")).await.unwrap().unwrap();
    (archeaxis_api::runtime::router(executor.clone()),executor,id)
}
async fn ready(dir:&Path) {
    tokio::time::timeout(std::time::Duration::from_secs(8),async {
        while !dir.join("answer.ready").exists() {tokio::time::sleep(std::time::Duration::from_millis(10)).await;}
    }).await.expect("owned worker did not signal admission");
}
async fn revoke_race(dir:&Path,router:&Router,id:&str)->(u16,Value,Value) {
    let (status,doc)=call(router,"POST","/api/v1/documents",json!({
        "title":"owned race grant","create_request_id":"withheld-race-grant","editor_json":editor(id,"granted")
    })).await;assert_eq!(status,201,"{doc}");
    let request=json!({"client_request_id":"withheld-race-answer","knowledge_id":id,"question":"SECRET SYNTHETIC QUESTION",
        "context_grant":{"document_id":doc["document_id"],"version":doc["version"],
            "content_sha256":doc["content_sha256"],"purpose":"owned withheld race fixture"}});
    let active=router.clone();
    let task=tokio::spawn(async move {call(&active,"POST","/api/v1/machine/answers",request).await});
    ready(dir).await;
    let (status,revoked)=call(router,"PUT",&format!("/api/v1/documents/{}/draft",doc["document_id"].as_str().unwrap()),
        json!({"expected_version":1,"editor_json":editor(id,"revoked")})).await;
    assert_eq!(status,200,"{revoked}");
    std::fs::write(dir.join("answer.release"),"release").unwrap();
    let (status,response)=task.await.unwrap();(status,response,doc)
}

#[tokio::test]
async fn revoked_during_actual_worker_execution_records_redacted_failed_audit() {
    let dir=tempfile::tempdir().unwrap();let (router,_,id)=fixture(dir.path()).await;
    let (status,response,grant)=revoke_race(dir.path(),&router,&id).await;
    assert_eq!(status,403,"{response}");assert_eq!(response["execution_state"],"EXECUTED_BUT_WITHHELD");
    assert_eq!(response["answer_published"],false);assert_eq!(response["audit_status"],"RECORDED");
    assert!(!response.to_string().contains("SECRET"));
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
    let audit=response["audit_task_id"].as_str().unwrap();
    let (status,receipt)=call(&router,"GET",&format!("/api/v1/machine/tasks/{audit}"),Value::Null).await;
    assert_eq!(status,200);assert_eq!(receipt["scope"],"runtime.execution.withheld");assert_eq!(receipt["outcome"],"failed");
    assert!(receipt["knowledge_version"].is_null());assert_eq!(receipt["model_version"],"synthetic/actual-worker");
    let conditions=receipt["conditions"].as_str().unwrap();assert!(!conditions.contains("SECRET"));
    let stored:Value=serde_json::from_str(conditions).unwrap();assert_eq!(stored["knowledge_id"],id);
    assert_eq!(stored["consumed_context_grant"]["document_id"],grant["document_id"]);
    assert_eq!(stored["consumed_context_grant"]["version"],1);
    assert_eq!(stored["consumed_context_grant"]["content_sha256"],grant["content_sha256"]);
    let (_,tasks)=call(&router,"GET","/api/v1/machine/tasks",Value::Null).await;
    assert_eq!(tasks["items"].as_array().unwrap().len(),1,"no runtime.answer may be published");
    let forged=json!({"task_id":"forged-withheld","principal":"machine","conditions":"{}","model_version":"fake",
        "scope":"runtime.execution.withheld","outcome":"failed","failure":"fake"});
    assert_eq!(call(&router,"POST","/api/v1/machine/tasks",forged).await.0,403);
}

#[tokio::test]
async fn failed_durable_audit_does_not_claim_recorded_or_not_run() {
    let dir=tempfile::tempdir().unwrap();let (router,executor,id)=fixture(dir.path()).await;
    executor.store().submit(|conn|conn.execute_batch(
        "CREATE TRIGGER deny_withheld BEFORE INSERT ON machine_tasks WHEN NEW.scope='runtime.execution.withheld' BEGIN SELECT RAISE(ABORT,'SYNTHETIC audit failure'); END;"
    )).await.unwrap().unwrap();
    let (status,response,_)=revoke_race(dir.path(),&router,&id).await;
    assert_eq!(status,500,"{response}");assert_eq!(response["execution_state"],"EXECUTED_BUT_WITHHELD");
    assert_eq!(response["audit_status"],"FAILED");assert!(response["audit_task_id"].is_null());
    assert_eq!(response["answer_published"],false);assert_eq!(response["error_code"],"WITHHELD_AUDIT_WRITE_FAILED");
    assert!(!response.to_string().contains("SECRET"));
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
    let (_,tasks)=call(&router,"GET","/api/v1/machine/tasks",Value::Null).await;
    assert!(tasks["items"].as_array().unwrap().is_empty());
}

#[tokio::test]
async fn frozen_client_key_replays_terminal_audit_without_second_worker_and_rejects_new_payload() {
    let dir=tempfile::tempdir().unwrap();let (router,executor,id)=fixture(dir.path()).await;
    let (status,doc)=call(&router,"POST","/api/v1/documents",json!({
        "title":"owned terminal grant","editor_json":editor(&id,"granted")
    })).await;assert_eq!(status,201);
    let request=json!({"client_request_id":"terminal-replay-fixture","knowledge_id":id,"question":"SECRET SYNTHETIC QUESTION",
        "context_grant":{"document_id":doc["document_id"],"version":doc["version"],
            "content_sha256":doc["content_sha256"],"purpose":"owned withheld race fixture"}});
    let active=router.clone();let original=request.clone();
    let task=tokio::spawn(async move {call(&active,"POST","/api/v1/machine/answers",original).await});
    ready(dir.path()).await;
    let knowledge_id=id.clone();
    // SYNTHETIC owned database fault: keep authorization active but change delivered body.
    executor.store().submit(move |conn|conn.execute("UPDATE knowledge SET body='SYNTHETIC changed body' WHERE knowledge_id=?1",[knowledge_id])).await.unwrap().unwrap();
    std::fs::write(dir.path().join("answer.release"),"release").unwrap();
    let (status,first)=task.await.unwrap();assert_eq!(status,403,"{first}");
    assert_eq!(first["reason_code"],"KNOWLEDGE_BODY_CHANGED");
    let knowledge_id=id.clone();
    executor.store().submit(move |conn|conn.execute("UPDATE knowledge SET body='SECRET SYNTHETIC CONTEXT' WHERE knowledge_id=?1",[knowledge_id])).await.unwrap().unwrap();
    let (status,replayed)=call(&router,"POST","/api/v1/machine/answers",request.clone()).await;
    assert_eq!(status,403,"{replayed}");assert_eq!(replayed["replayed"],true);
    assert_eq!(replayed["audit_task_id"],first["audit_task_id"]);
    let mut changed=request;changed["question"]=json!("different frozen question");
    assert_eq!(call(&router,"POST","/api/v1/machine/answers",changed).await.0,409);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
}

#[tokio::test]
async fn retest_revoke_during_worker_preserves_prior_answer_and_appends_only_failed_audit() {
    let dir=tempfile::tempdir().unwrap();let (router,_,id)=fixture(dir.path()).await;
    let (status,grant)=call(&router,"POST","/api/v1/documents",json!({
        "title":"owned retest grant","editor_json":editor(&id,"granted")
    })).await;assert_eq!(status,201,"{grant}");
    let consumption=json!({"document_id":grant["document_id"],"version":grant["version"],
        "content_sha256":grant["content_sha256"],"purpose":"owned withheld race fixture"});
    // First execution completes normally; the second owned worker invocation is blocked.
    std::fs::write(dir.path().join("answer.release"),"release first execution").unwrap();
    let question="SECRET SYNTHETIC RETEST QUESTION";
    let (status,answer)=call(&router,"POST","/api/v1/machine/answers",json!({
        "client_request_id":"retest-prior-answer","knowledge_id":id,"question":question,"context_grant":consumption
    })).await;assert_eq!(status,200,"{answer}");
    let original_path=format!("/api/v1/machine/tasks/{}",answer["answer_id"].as_str().unwrap());
    let (_,original_receipt)=call(&router,"GET",&original_path,Value::Null).await;
    let (status,correction)=call(&router,"POST","/api/v1/machine/corrections",json!({
        "answer_id":answer["answer_id"],"knowledge_id":id,"question":question,
        "machine_answer":answer["answer"]["answer"],"corrected_answer":"SYNTHETIC human correction",
        "error_note":"SYNTHETIC error requiring retest","reviewer":"fixture-human"
    })).await;assert_eq!(status,200,"{correction}");
    let failed=correction["failed_task_id"].as_str().unwrap().to_string();
    std::fs::remove_file(dir.path().join("answer.ready")).unwrap();
    std::fs::remove_file(dir.path().join("answer.release")).unwrap();
    let request=json!({"retest_of":failed,"knowledge_id":id,"question":question,"context_grant":consumption});
    let active=router.clone();let original=request.clone();
    let task=tokio::spawn(async move {call(&active,"POST","/api/v1/machine/retests",original).await});
    ready(dir.path()).await;
    let (status,revoked)=call(&router,"PUT",&format!("/api/v1/documents/{}/draft",grant["document_id"].as_str().unwrap()),
        json!({"expected_version":1,"editor_json":editor(&id,"revoked")})).await;
    assert_eq!(status,200,"{revoked}");
    std::fs::write(dir.path().join("answer.release"),"release withheld retest").unwrap();
    let (status,response)=task.await.unwrap();assert_eq!(status,403,"{response}");
    assert_eq!(response["execution_state"],"EXECUTED_BUT_WITHHELD");assert_eq!(response["audit_status"],"RECORDED");
    assert_eq!(response["answer_published"],false);assert!(!response.to_string().contains("SECRET"));
    let audit_path=format!("/api/v1/machine/tasks/{}",response["audit_task_id"].as_str().unwrap());
    let (_,receipt)=call(&router,"GET",&audit_path,Value::Null).await;
    assert_eq!(receipt["scope"],"runtime.execution.withheld");assert_eq!(receipt["outcome"],"failed");
    assert_eq!(receipt["retest_of"],failed);assert!(receipt["knowledge_version"].is_null());
    let conditions=receipt["conditions"].as_str().unwrap();assert!(!conditions.contains("SECRET"));
    let stored:Value=serde_json::from_str(conditions).unwrap();assert_eq!(stored["operation"],"retest");
    assert_eq!(stored["knowledge_id"],id);assert_eq!(stored["consumed_context_grant"]["version"],1);
    assert_eq!(stored["consumed_context_grant"]["content_sha256"],grant["content_sha256"]);
    let (_,after)=call(&router,"GET",&original_path,Value::Null).await;assert_eq!(after,original_receipt);
    let (_,tasks)=call(&router,"GET","/api/v1/machine/tasks",Value::Null).await;
    assert!(!tasks["items"].as_array().unwrap().iter().any(|item|item["scope"]=="runtime.retest"));
    assert_eq!(call(&router,"POST","/api/v1/machine/retests",request).await.0,403);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"2");
}

#[tokio::test]
async fn actual_grant_expiry_while_worker_waits_creates_failed_execution_audit() {
    let dir=tempfile::tempdir().unwrap();let (router,_,id)=fixture(dir.path()).await;
    fn now()->u64 {std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs()}
    let expiry=now()+8;
    let mut envelope=editor(&id,"granted");
    envelope["attrs"]["archeaxis_context_grant"]["expires_at"]=json!(expiry);
    let (status,grant)=call(&router,"POST","/api/v1/documents",json!({"title":"owned expiry grant","editor_json":envelope})).await;
    assert_eq!(status,201,"{grant}");
    let request=json!({"client_request_id":"expiry-during-worker","knowledge_id":id,"question":"SECRET SYNTHETIC EXPIRY QUESTION",
        "context_grant":{"document_id":grant["document_id"],"version":grant["version"],
            "content_sha256":grant["content_sha256"],"purpose":"owned withheld race fixture"}});
    let active=router.clone();let original=request.clone();
    let task=tokio::spawn(async move {call(&active,"POST","/api/v1/machine/answers",original).await});
    ready(dir.path()).await;
    assert!(now()<expiry,"fixture must observe worker running before expiry, not just pre-admission refusal");
    // Wait against the actual wall-clock expiry, not an assumed scheduling delay.
    tokio::time::timeout(std::time::Duration::from_secs(10),async {
        while now()<expiry {tokio::time::sleep(std::time::Duration::from_millis(25)).await;}
    }).await.unwrap();
    std::fs::write(dir.path().join("answer.release"),"release after expiry").unwrap();
    let (status,response)=task.await.unwrap();assert_eq!(status,403,"{response}");
    assert_eq!(response["execution_state"],"EXECUTED_BUT_WITHHELD");assert_eq!(response["audit_status"],"RECORDED");
    assert_eq!(response["answer_published"],false);assert_eq!(response["reason_code"],"CONTEXT_AUTHORIZATION_CHANGED");
    let (_,receipt)=call(&router,"GET",&format!("/api/v1/machine/tasks/{}",response["audit_task_id"].as_str().unwrap()),Value::Null).await;
    assert_eq!(receipt["scope"],"runtime.execution.withheld");assert_eq!(receipt["outcome"],"failed");
    let conditions=receipt["conditions"].as_str().unwrap();assert!(!conditions.contains("SECRET"));
    let stored:Value=serde_json::from_str(conditions).unwrap();assert_eq!(stored["operation"],"answer");
    assert_eq!(stored["consumed_context_grant"]["document_id"],grant["document_id"]);
    assert_eq!(stored["consumed_context_grant"]["content_sha256"],grant["content_sha256"]);
    assert_eq!(call(&router,"POST","/api/v1/machine/answers",request).await.0,403);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
}
