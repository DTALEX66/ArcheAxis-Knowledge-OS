use archeaxis_domain::{document, knowledge, machine::{self, MachineTask}, machine_evaluation::{self as evaluation, Rubric, Criterion, RubricSnapshot, EvaluationRequest, Judgment, Outcome}};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::{json, Value};
type Fixture = (tempfile::TempDir, Connection, String, Value);
fn rubric(request: &str) -> Rubric { Rubric {schema:evaluation::RUBRIC_SCHEMA.into(),request_id:request.into(),title:"固定写入职责标准".into(),purpose:"人工评价这次机器回答，不授予人类掌握或专业可信".into(),criteria:vec![Criterion{criterion_id:"core".into(),label:"写入者".into(),expectation:"明确 Rust Core 是 canonical writer".into()},Criterion{criterion_id:"candidate".into(),label:"候选边界".into(),expectation:"机器输出保持候选，不能自行采纳".into()}],sources:vec![]} }
fn fixture() -> Fixture {
 let dir=tempfile::tempdir().unwrap();let mut conn=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
 let kid=knowledge::create_knowledge(&mut conn,"NOTE","Rust Core writes canonical storage","accepted",None,None,"human").unwrap();
 let conditions=json!({"schema":"archeaxis.machine-answer/v1","answer_id":"answer_one","knowledge_id":kid,"question":"Who writes?","answer":{"answer":"Rust Core is the writer; this answer is a candidate.","model":"synthetic-model"},"authority":"candidate"}).to_string();
 machine::record_machine_task(&mut conn,&MachineTask{task_id:"answer_one",principal:"machine",conditions:&conditions,knowledge_version:Some(&format!("{kid}@v1")),method_version:None,tool_version:None,model_version:"synthetic-model",scope:"runtime.answer",outcome:"unmeasured",failure:None,retest_of:None}).unwrap();
 let rd=evaluation::create_rubric(&mut conn,"human",&rubric("rubric_one")).unwrap();(dir,conn,kid,rd)
}
fn request(rd:&Value,id:&str) -> EvaluationRequest { EvaluationRequest {request_id:id.into(),task_id:"answer_one".into(),rubric:RubricSnapshot{document_id:rd["document_id"].as_str().unwrap().into(),version:rd["version"].as_i64().unwrap(),content_sha256:rd["content_sha256"].as_str().unwrap().into()},reviewer:"owner annotation".into(),basis:"逐条核对原答案与固定标准".into(),judgments:vec![Judgment{criterion_id:"core".into(),outcome:Outcome::Passed,basis:"答案明确Rust Core".into()},Judgment{criterion_id:"candidate".into(),outcome:Outcome::Passed,basis:"答案明确candidate".into()}],outcome:Outcome::Passed} }
fn versions(c:&Connection)->i64{c.query_row("SELECT count(*) FROM document_versions",[],|r|r.get(0)).unwrap()}
#[test]
fn fixed_rubric_evaluation_idempotency_restart_and_no_authority_promotion() {
 let (dir,mut c,kid,rd)=fixture();let r=request(&rd,"eval_one");let first=evaluation::create_evaluation(&mut c,"human",&r).unwrap();let n=versions(&c);
 assert_eq!(evaluation::create_evaluation(&mut c,"human",&r).unwrap(),first);assert_eq!(versions(&c),n);
 let e=&first["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE];assert_eq!(e["outcome"],"passed");assert_eq!(e["rubric"]["content_sha256"],rd["content_sha256"]);
 let snapshot=evaluation::answer_snapshot(&c,"answer_one").unwrap();assert_eq!(e["task_receipt_sha256"],snapshot["task_receipt_sha256"]);assert_eq!(snapshot["grants_machine_qualification"],false);
 assert_eq!(c.query_row("SELECT outcome FROM machine_tasks WHERE task_id='answer_one'",[],|r|r.get::<_,String>(0)).unwrap(),"unmeasured");assert_eq!(c.query_row("SELECT body FROM knowledge WHERE knowledge_id=?1",[&kid],|r|r.get::<_,String>(0)).unwrap(),"Rust Core writes canonical storage");
 drop(c);let c=init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();assert_eq!(document::read(&c,first["document_id"].as_str().unwrap(),Some(1)).unwrap(),first);
}
#[test]
fn rubric_revisions_keep_original_pinned_snapshot_in_evaluation() {
 let (_dir,mut c,_kid,rd)=fixture();let old=rd["editor_json"].clone();let mut next=old.clone();next["attrs"][evaluation::RUBRIC_NAMESPACE]["criteria"][0]["expectation"]=json!("不同的新标准");
 let current=document::save(&mut c,rd["document_id"].as_str().unwrap(),1,next).unwrap();assert_eq!(current["version"],2);assert_eq!(document::read(&c,rd["document_id"].as_str().unwrap(),Some(1)).unwrap()["editor_json"],old);
 let e=evaluation::create_evaluation(&mut c,"human",&request(&rd,"eval_old_rubric")).unwrap();assert_eq!(e["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE]["rubric"]["version"],1);
}
#[test]
fn registered_evaluation_cannot_be_changed_removed_or_repurposed_through_generic_save() {
 let (_dir,mut c,_kid,rd)=fixture();let first=evaluation::create_evaluation(&mut c,"human",&request(&rd,"eval_locked")).unwrap();let id=first["document_id"].as_str().unwrap();
 let mut changed=first["editor_json"].clone();changed["attrs"][evaluation::EVALUATION_NAMESPACE]["reviewer"]=json!("rewritten");let before=versions(&c);assert!(document::save(&mut c,id,1,changed).is_err());
 assert!(document::save(&mut c,id,1,json!({"type":"doc","content":[]})).is_err());assert_eq!(versions(&c),before);
 let mut compatible=first["editor_json"].clone();compatible["attrs"]["unrelated"]=json!({"future":[1,null,true]});let next=document::save(&mut c,id,1,compatible).unwrap();assert_eq!(next["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE],first["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE]);
}
#[test]
fn pinned_hash_wrong_version_and_forged_answer_digest_fail_without_partial_documents() {
 let (_dir,mut c,_kid,rd)=fixture();let before=versions(&c);
 let mut r=request(&rd,"wrong_hash");r.rubric.content_sha256="f".repeat(64);assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());
 r=request(&rd,"wrong_version");r.rubric.version=99;assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());assert_eq!(versions(&c),before);
 let first=evaluation::create_evaluation(&mut c,"human",&request(&rd,"eval_good")).unwrap();let mut forged=first["editor_json"].clone();forged["attrs"][evaluation::EVALUATION_NAMESPACE]["original_answer_sha256"]=json!("0".repeat(64));assert!(evaluation::validate_transition(&c,first["document_id"].as_str().unwrap(),0,&forged).is_err());
}
#[test]
fn changed_payload_same_request_conflicts_and_never_rewrites_original() {
 let (_dir,mut c,_kid,rd)=fixture();let mut r=request(&rd,"same_request");let first=evaluation::create_evaluation(&mut c,"human",&r).unwrap();r.basis="另一份人工依据".into();let n=versions(&c);assert!(matches!(evaluation::create_evaluation(&mut c,"human",&r),Err(document::Error::Conflict(_))));assert_eq!(versions(&c),n);assert_eq!(document::read(&c,first["document_id"].as_str().unwrap(),Some(1)).unwrap(),first);
}
#[test]
fn machine_unknown_actor_and_blank_basis_refused_before_writes() {
 let (_dir,mut c,_kid,rd)=fixture();let before=versions(&c);let mut r=request(&rd,"actor_guard");for actor in ["machine","human-in-body","", "unknown"]{assert!(evaluation::create_evaluation(&mut c,actor,&r).is_err());assert!(evaluation::create_rubric(&mut c,actor,&rubric("not_created")).is_err());}r.basis=" ".into();assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());assert_eq!(versions(&c),before);
}
#[test]
fn duplicate_missing_unknown_criterion_and_inconsistent_overall_are_not_success() {
 let (_dir,mut c,_kid,rd)=fixture();let n=versions(&c);let mut r=request(&rd,"bad_judgments");r.judgments.pop();assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());
 r=request(&rd,"bad_judgments");r.judgments[1].criterion_id="core".into();assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());r.judgments[1].criterion_id="unknown".into();assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());
 r=request(&rd,"bad_judgments");r.judgments[0].outcome=Outcome::Unmeasured;assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());r.outcome=Outcome::Unmeasured;let e=evaluation::create_evaluation(&mut c,"human",&r).unwrap();assert_eq!(e["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE]["outcome"],"unmeasured");assert_eq!(versions(&c),n+1);
}
#[test]
fn past_answer_evaluation_survives_knowledge_withdrawal_without_new_inference() {
 let (_dir,mut c,kid,rd)=fixture();knowledge::review(&mut c,&kid,"deprecated","human",Some("撤回当前消费"),None).unwrap();let e=evaluation::create_evaluation(&mut c,"human",&request(&rd,"historical_evaluation")).unwrap();assert_eq!(e["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE]["knowledge_id"],kid);assert!(!knowledge::is_knowledge_active(&c,&kid).unwrap());assert_eq!(c.query_row("SELECT count(*) FROM machine_tasks",[],|r|r.get::<_,i64>(0)).unwrap(),1);
}
#[test]
fn generic_self_reported_task_is_not_a_runtime_answer() {
 let (_dir,mut c,_kid,rd)=fixture();machine::record_machine_task(&mut c,&MachineTask{task_id:"generic",principal:"machine",conditions:"self reported",knowledge_version:None,method_version:None,tool_version:None,model_version:"synthetic-model",scope:"generic.allowed",outcome:"succeeded",failure:None,retest_of:None}).unwrap();let mut r=request(&rd,"eval_generic");r.task_id="generic".into();assert!(evaluation::create_evaluation(&mut c,"human",&r).is_err());r.task_id="missing".into();assert!(matches!(evaluation::create_evaluation(&mut c,"human",&r),Err(document::Error::NotFound)));
}
#[test]
fn unknown_fields_and_request_namespace_copy_fail_closed_preserving_original() {
 let (_dir,mut c,_kid,rd)=fixture();let mut e=rd["editor_json"].clone();e["attrs"][evaluation::RUBRIC_NAMESPACE]["script"]=json!("inert future field");assert!(document::save(&mut c,rd["document_id"].as_str().unwrap(),1,e).is_err());let before=versions(&c);assert!(document::create_optional_with_request(&mut c,None,None,"copied rubric",rd["editor_json"].clone(),Some("copy_wrong_id")).is_err());assert_eq!(versions(&c),before);
}
#[test]
fn real_persisted_retest_identity_can_be_evaluated_without_replacing_original_answer() {
 let (_dir,mut c,kid,rd)=fixture();
 machine::record_machine_task(&mut c,&MachineTask{task_id:"failed_before",principal:"machine",conditions:"synthetic failure fixture",knowledge_version:Some(&kid),method_version:None,tool_version:None,model_version:"synthetic-model",scope:"fixture.failure",outcome:"failed",failure:Some("test failure"),retest_of:None}).unwrap();
 let raw=json!({"schema":"archeaxis.machine-retest/v1","answer_id":"retest_one","retest_task_id":"retest_one","knowledge_id":kid,"question":"Who writes?","answer":{"answer":"Corrected candidate answer", "model":"synthetic-model"},"retest_of":"failed_before"}).to_string();
 machine::record_machine_task(&mut c,&MachineTask{task_id:"retest_one",principal:"machine",conditions:&raw,knowledge_version:Some(&kid),method_version:None,tool_version:None,model_version:"synthetic-model",scope:"runtime.retest",outcome:"unmeasured",failure:None,retest_of:Some("failed_before")}).unwrap();
 let original=evaluation::answer_snapshot(&c,"answer_one").unwrap();let mut r=request(&rd,"eval_retest");r.task_id="retest_one".into();let e=evaluation::create_evaluation(&mut c,"human",&r).unwrap();assert_eq!(e["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE]["task_id"],"retest_one");assert_ne!(e["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE]["original_answer_sha256"],original["original_answer_sha256"]);assert_eq!(evaluation::answer_snapshot(&c,"answer_one").unwrap(),original);
}
#[test]
fn human_failure_outcome_is_explicit_and_never_rewrites_runtime_outcome() {
 let (_dir,mut c,_kid,rd)=fixture();let mut r=request(&rd,"eval_failed");r.judgments[0].outcome=Outcome::Failed;r.judgments[0].basis="人工认为证据不足，并保留原回答".into();r.outcome=Outcome::Failed;let e=evaluation::create_evaluation(&mut c,"human",&r).unwrap();assert_eq!(e["editor_json"]["attrs"][evaluation::EVALUATION_NAMESPACE]["outcome"],"failed");assert_eq!(c.query_row("SELECT outcome FROM machine_tasks WHERE task_id='answer_one'",[],|r|r.get::<_,String>(0)).unwrap(),"unmeasured");
}

#[test]
fn removing_rubric_metadata_cannot_launder_its_identity_into_an_evaluation() {
 let (_dir,mut c,_kid,rd)=fixture();
 let e=evaluation::create_evaluation(&mut c,"human",&request(&rd,"separate_eval")).unwrap();
 let id=rd["document_id"].as_str().unwrap();
 document::save(&mut c,id,1,json!({"type":"doc","content":[]})).unwrap();
 let mut repurposed=e["editor_json"].clone();
 repurposed["attrs"][evaluation::EVALUATION_NAMESPACE]["request_id"]=json!("rubric_one");
 let n=versions(&c);
 let error=document::save(&mut c,id,2,repurposed).unwrap_err();
 assert!(format!("{error:?}").contains("rubric document identity"),"{error:?}");
 assert_eq!(versions(&c),n);
 let original:String=c.query_row("SELECT editor_json FROM document_versions WHERE document_id=?1 AND version=1",[id],|r|r.get(0)).unwrap();
 assert_eq!(serde_json::from_str::<Value>(&original).unwrap(),rd["editor_json"]);
}
