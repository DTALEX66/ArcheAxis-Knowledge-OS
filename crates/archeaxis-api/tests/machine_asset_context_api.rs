//! Owned SYNTHETIC assets; real bounded Python subprocess/Store/API, not a real model qualification.
use archeaxis_application::executor::Executor;
use archeaxis_domain::{ai_asset,document,knowledge,machine_evaluation::{self,Rubric,Criterion}};
use axum::{Router,body::Body,http::Request};
use http_body_util::BodyExt;
use serde_json::{Value,json};
use std::path::{Path,PathBuf};
use tower::ServiceExt;
async fn call(r:&Router,method:&str,path:&str,body:Value)->(u16,Value) {
    let response=r.clone().oneshot(Request::builder().method(method).uri(path).header("content-type","application/json")
        .header("x-archeaxis-actor","human").body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status=response.status().as_u16();let raw=response.into_body().collect().await.unwrap().to_bytes();
    (status,serde_json::from_slice(&raw).unwrap_or(Value::Null))
}
fn base_asset(kind:&str,members:Value)->Value {json!({"schema":"archeaxis.ai-asset/v1","kind":kind,"content":"ASSET_RULE_MARKER owned inert instruction",
    "purpose":"owned answer test","scope":[],"provenance":[],"state":"candidate","members":members,"conflicts":[],"expires_at":null,"review":null,"revises":null,"source_payload":null})}
fn adopt(c:&mut rusqlite::Connection,key:&str,asset:Value)->Value {
    let candidate=document::create_optional_with_request(c,None,None,"owned asset",json!({"type":"doc","content":[],"attrs":{"archeaxis_ai_asset":asset}}),Some(key)).unwrap();
    let rubric=machine_evaluation::create_rubric(c,"human",&Rubric{schema:machine_evaluation::RUBRIC_SCHEMA.into(),request_id:"owned-asset-runtime-rubric".into(),title:"fixed rubric".into(),purpose:"owned fit".into(),sources:vec![],
        criteria:vec![Criterion{criterion_id:"fit".into(),label:"fit".into(),expectation:"owned observed fit".into()}]}).unwrap();
    let mut editor=candidate["editor_json"].clone();editor["attrs"]["archeaxis_ai_asset"]["state"]=json!("adopted");
    editor["attrs"]["archeaxis_ai_asset"]["review"]=json!({"asset":ai_asset::snapshot(&candidate).unwrap(),"rubric":ai_asset::snapshot(&rubric).unwrap(),"reviewer":"owner annotation","basis":"SYNTHETIC observed criterion",
        "judgments":[{"criterion_id":"fit","basis":"observed fit","outcome":"passed"}],"outcome":"passed"});
    document::save(c,candidate["document_id"].as_str().unwrap(),1,editor).unwrap()
}
fn seconds()->u64 {std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs()}
async fn fixture(dir:&Path,expires:Option<u64>)->(Router,Executor,Value,Value) {
    let worker=dir.join("answer.py");std::fs::write(&worker,concat!(
        "import json,time,sys\nfrom pathlib import Path\np=Path(__file__)\n",
        "ctx=Path(sys.argv[1]).read_text(encoding='utf-8')\nassert 'CANONICAL_KNOWLEDGE:' in ctx and 'SYNTHETIC KNOWLEDGE' in ctx and 'ASSET_RULE_MARKER' in ctx\n",
        "p.with_suffix('.consumed').write_text(ctx,encoding='utf-8')\ncount=p.with_suffix('.count')\ncount.write_text(str(int(count.read_text())+1) if count.exists() else '1')\n",
        "p.with_suffix('.ready').write_text('ready')\nend=time.monotonic()+10\n",
        "while not p.with_suffix('.release').exists():\n if time.monotonic()>end: raise RuntimeError('owned release timeout')\n time.sleep(.01)\n",
        "print(json.dumps({'answer':'SYNTHETIC ASSET-GROUNDED OUTPUT','model':'synthetic/asset-worker','asset_seen':True}))\n"
    )).unwrap();
    let python=PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let executor=Executor::open_routes(&dir.join("db.sqlite"),&dir.join("staging"),&python,
        &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/python-workers/transport/text_ndjson.py"),&[("machine.answer",worker)]).await.unwrap();
    let setup=executor.store().submit(move |c| {
        let kid=knowledge::create_knowledge(c,"NOTE","SYNTHETIC KNOWLEDGE","accepted",None,None,"owner").unwrap();
        let kg=document::create_optional_with_request(c,None,None,"knowledge grant",json!({"type":"doc","content":[],"attrs":{"archeaxis_context_grant":{
            "schema":"archeaxis.context-grant/v1","purpose":"owned answer test","consumer":"local-machine","operations":["answer","retest"],"knowledge_id":kid,
            "provenance":[],"authorization_basis":"explicit SYNTHETIC owner grant","expires_at":null,"state":"granted"}}}),Some("asset-runtime-knowledge-grant")).unwrap();
        let member=adopt(c,"asset-runtime-rule",base_asset("rule",json!([])));
        let package=adopt(c,"asset-runtime-package",base_asset("knowledge_package",json!([ai_asset::snapshot(&member).unwrap()])));
        let ag=document::create_optional_with_request(c,None,None,"asset grant",json!({"type":"doc","content":[],"attrs":{"archeaxis_asset_context_grant":{
            "schema":"archeaxis.asset-context-grant/v1","asset":ai_asset::snapshot(&package).unwrap(),"purpose":"owned answer test","consumer":"local-machine",
            "operations":["answer","retest"],"authorization_basis":"explicit SYNTHETIC asset permission","expires_at":expires,"state":"granted"}}}),Some("asset-runtime-asset-grant")).unwrap();
        let request=json!({"client_request_id":"owned-asset-answer-key","knowledge_id":kid,"question":"owned asset question",
            "context_grant":{"document_id":kg["document_id"],"version":kg["version"],"content_sha256":kg["content_sha256"],"purpose":"owned answer test"},
            "asset_context_grant":{"request_id":"owned-asset-consumption-key","asset":ai_asset::snapshot(&package).unwrap(),"grant":ai_asset::snapshot(&ag).unwrap(),"purpose":"owned answer test","consumer":"local-machine","operation":"answer"}});
        (request,member)
    }).await.unwrap();
    (archeaxis_api::runtime::router(executor.clone()),executor,setup.0,setup.1)
}
async fn ready(dir:&Path) {tokio::time::timeout(std::time::Duration::from_secs(8),async {while !dir.join("answer.ready").exists() {tokio::time::sleep(std::time::Duration::from_millis(10)).await;}}).await.unwrap();}
#[tokio::test]
async fn actual_asset_packet_reaches_worker_and_exact_retry_never_runs_again_or_omits_asset() {
    let dir=tempfile::tempdir().unwrap();let (r,_,request,_)=fixture(dir.path(),None).await;
    let mut without_knowledge=request.clone();without_knowledge.as_object_mut().unwrap().remove("context_grant");assert_eq!(call(&r,"POST","/api/v1/machine/answers",without_knowledge).await.0,403);
    std::fs::write(dir.path().join("answer.release"),"release").unwrap();
    let (status,first)=call(&r,"POST","/api/v1/machine/answers",request.clone()).await;assert_eq!(status,200,"{first}");
    assert_eq!(first["answer"]["asset_seen"],true);assert_eq!(first["request"]["asset_context"]["grant"],request["asset_context_grant"]["grant"]);
    assert_eq!(first["request"]["asset_context"]["member_snapshots"].as_array().unwrap().len(),2);
    let context=std::fs::read_to_string(dir.path().join("answer.consumed")).unwrap();assert!(context.contains("ASSET_RULE_MARKER") && context.contains("SYNTHETIC KNOWLEDGE"));
    let (status,again)=call(&r,"POST","/api/v1/machine/answers",request.clone()).await;assert_eq!(status,200);assert_eq!(again,first);
    let mut omitted=request.clone();omitted.as_object_mut().unwrap().remove("asset_context_grant");assert_eq!(call(&r,"POST","/api/v1/machine/answers",omitted).await.0,409);
    let mut changed=request;changed["client_request_id"]=json!("other-client-key");changed["question"]=json!("changed frozen asset question");assert_eq!(call(&r,"POST","/api/v1/machine/answers",changed).await.0,409);
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
}
#[tokio::test]
async fn package_member_withdrawal_during_worker_redacts_answer_and_audits_actual_pins() {
    let dir=tempfile::tempdir().unwrap();let (r,_,request,member)=fixture(dir.path(),None).await;
    let active=r.clone();let original=request.clone();let task=tokio::spawn(async move {call(&active,"POST","/api/v1/machine/answers",original).await});ready(dir.path()).await;
    let mut editor=member["editor_json"].clone();editor["attrs"]["archeaxis_ai_asset"]["state"]=json!("withdrawn");
    let (status,d)=call(&r,"PUT",&format!("/api/v1/documents/{}/draft",member["document_id"].as_str().unwrap()),json!({"expected_version":2,"editor_json":editor})).await;assert_eq!(status,200,"{d}");
    std::fs::write(dir.path().join("answer.release"),"release").unwrap();let (status,withheld)=task.await.unwrap();assert_eq!(status,403,"{withheld}");
    assert_eq!(withheld["reason_code"],"ASSET_AUTHORIZATION_CHANGED");assert_eq!(withheld["execution_state"],"EXECUTED_BUT_WITHHELD");
    let (_,receipt)=call(&r,"GET",&format!("/api/v1/machine/tasks/{}",withheld["audit_task_id"].as_str().unwrap()),Value::Null).await;
    let audit:Value=serde_json::from_str(receipt["conditions"].as_str().unwrap()).unwrap();
    assert_eq!(audit["consumed_asset_context"]["grant"],request["asset_context_grant"]["grant"]);assert_eq!(audit["consumed_asset_context"]["asset"],request["asset_context_grant"]["asset"]);
    assert_eq!(audit["asset_request_id"],"owned-asset-consumption-key");assert!(!receipt["conditions"].as_str().unwrap().contains("ASSET_RULE_MARKER"));
    assert!(!receipt["conditions"].as_str().unwrap().contains("ASSET-GROUNDED OUTPUT"));
    assert_eq!(call(&r,"POST","/api/v1/machine/answers",request).await.0,403);assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
}
#[tokio::test]
async fn asset_grant_expiry_after_admission_withholds_actual_worker_output() {
    let dir=tempfile::tempdir().unwrap();let expiry=seconds()+4;let (r,_,request,_)=fixture(dir.path(),Some(expiry)).await;
    let active=r.clone();let task=tokio::spawn(async move {call(&active,"POST","/api/v1/machine/answers",request).await});ready(dir.path()).await;
    while seconds()<expiry {tokio::time::sleep(std::time::Duration::from_millis(20)).await;}
    std::fs::write(dir.path().join("answer.release"),"release expired execution").unwrap();let (status,result)=task.await.unwrap();
    assert_eq!(status,403,"{result}");assert_eq!(result["reason_code"],"ASSET_AUTHORIZATION_CHANGED");assert_eq!(result["audit_status"],"RECORDED");
    assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"1");
}
#[tokio::test]
async fn asset_retest_uses_same_packet_with_new_operation_key_and_preserves_prior_answer() {
    let dir=tempfile::tempdir().unwrap();let (r,_,request,member)=fixture(dir.path(),None).await;
    std::fs::write(dir.path().join("answer.release"),"release first").unwrap();let (status,answer)=call(&r,"POST","/api/v1/machine/answers",request.clone()).await;assert_eq!(status,200,"{answer}");
    let original_path=format!("/api/v1/machine/tasks/{}",answer["answer_id"].as_str().unwrap());let (_,before)=call(&r,"GET",&original_path,Value::Null).await;
    let (status,correction)=call(&r,"POST","/api/v1/machine/corrections",json!({"answer_id":answer["answer_id"],"knowledge_id":request["knowledge_id"],"question":request["question"],
        "machine_answer":answer["answer"]["answer"],"corrected_answer":"SYNTHETIC correction","error_note":"SYNTHETIC observed error","reviewer":"owner"})).await;assert_eq!(status,200,"{correction}");
    let mut asset=request["asset_context_grant"].clone();asset["operation"]=json!("retest");asset["request_id"]=json!("owned-asset-retest-key");
    let retest=json!({"retest_of":correction["failed_task_id"],"knowledge_id":request["knowledge_id"],"question":request["question"],"context_grant":request["context_grant"],"asset_context_grant":asset});
    let mut omitted=retest.clone();omitted.as_object_mut().unwrap().remove("asset_context_grant");assert_eq!(call(&r,"POST","/api/v1/machine/retests",omitted).await.0,409);
    let (status,first)=call(&r,"POST","/api/v1/machine/retests",retest.clone()).await;assert_eq!(status,200,"{first}");assert_eq!(first["execution_request"]["asset_context"]["operation"],"retest");
    assert_eq!(call(&r,"POST","/api/v1/machine/retests",retest.clone()).await.1,first);
    let mut changed=retest.clone();changed["timeout_s"]=json!(1);assert_eq!(call(&r,"POST","/api/v1/machine/retests",changed).await.0,409);
    let (_,after)=call(&r,"GET",&original_path,Value::Null).await;assert_eq!(before,after);
    // Cached retest never bypasses current package-member authorization.
    let mut editor=member["editor_json"].clone();editor["attrs"]["archeaxis_ai_asset"]["state"]=json!("withdrawn");
    assert_eq!(call(&r,"PUT",&format!("/api/v1/documents/{}/draft",member["document_id"].as_str().unwrap()),json!({"expected_version":2,"editor_json":editor})).await.0,200);
    assert_eq!(call(&r,"POST","/api/v1/machine/retests",retest).await.0,403);assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"2");
}

// Append to CURRENT crates/archeaxis-api/tests/machine_asset_context_api.rs.
#[tokio::test]
async fn retest_member_withdrawal_during_owned_worker_appends_asset_audit_without_rewriting_prior_answer() {
    let dir=tempfile::tempdir().unwrap();let (r,_,request,member)=fixture(dir.path(),None).await;
    std::fs::write(dir.path().join("answer.release"),"release original").unwrap();
    let (status,answer)=call(&r,"POST","/api/v1/machine/answers",request.clone()).await;assert_eq!(status,200,"{answer}");
    let original_path=format!("/api/v1/machine/tasks/{}",answer["answer_id"].as_str().unwrap());let (_,before)=call(&r,"GET",&original_path,Value::Null).await;
    let (status,correction)=call(&r,"POST","/api/v1/machine/corrections",json!({"answer_id":answer["answer_id"],"knowledge_id":request["knowledge_id"],"question":request["question"],
        "machine_answer":answer["answer"]["answer"],"corrected_answer":"SYNTHETIC correction","error_note":"SYNTHETIC observed error","reviewer":"owner"})).await;assert_eq!(status,200,"{correction}");
    std::fs::remove_file(dir.path().join("answer.release")).unwrap();std::fs::remove_file(dir.path().join("answer.ready")).unwrap();
    let mut asset=request["asset_context_grant"].clone();asset["operation"]=json!("retest");asset["request_id"]=json!("owned-retest-race-key");
    let retest=json!({"retest_of":correction["failed_task_id"],"knowledge_id":request["knowledge_id"],"question":request["question"],"context_grant":request["context_grant"],"asset_context_grant":asset});
    let active=r.clone();let frozen=retest.clone();let task=tokio::spawn(async move {call(&active,"POST","/api/v1/machine/retests",frozen).await});ready(dir.path()).await;
    let mut editor=member["editor_json"].clone();editor["attrs"]["archeaxis_ai_asset"]["state"]=json!("withdrawn");
    assert_eq!(call(&r,"PUT",&format!("/api/v1/documents/{}/draft",member["document_id"].as_str().unwrap()),json!({"expected_version":2,"editor_json":editor})).await.0,200);
    std::fs::write(dir.path().join("answer.release"),"release withheld retest").unwrap();
    let (status,result)=task.await.unwrap();assert_eq!(status,403,"{result}");assert_eq!(result["execution_state"],"EXECUTED_BUT_WITHHELD");
    assert_eq!(result["reason_code"],"ASSET_AUTHORIZATION_CHANGED");assert_eq!(result["audit_status"],"RECORDED");assert_eq!(result["answer_published"],false);
    let (_,receipt)=call(&r,"GET",&format!("/api/v1/machine/tasks/{}",result["audit_task_id"].as_str().unwrap()),Value::Null).await;
    let audit:Value=serde_json::from_str(receipt["conditions"].as_str().unwrap()).unwrap();
    assert_eq!(receipt["retest_of"],correction["failed_task_id"]);assert_eq!(audit["operation"],"retest");
    assert_eq!(audit["consumed_asset_context"]["grant"],retest["asset_context_grant"]["grant"]);
    assert_eq!(audit["consumed_asset_context"]["member_snapshots"].as_array().unwrap().len(),2);
    assert!(!receipt["conditions"].as_str().unwrap().contains("ASSET_RULE_MARKER"));assert!(!receipt["conditions"].as_str().unwrap().contains("ASSET-GROUNDED OUTPUT"));
    let (_,after)=call(&r,"GET",&original_path,Value::Null).await;assert_eq!(before,after);
    assert_eq!(call(&r,"POST","/api/v1/machine/retests",retest).await.0,403);assert_eq!(std::fs::read_to_string(dir.path().join("answer.count")).unwrap(),"2");
}
