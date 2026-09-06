use archeaxis_application::{bootstrap, jobs, attempts};
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_sidecar_protocol::worker::{Request, Response, Output};
use sha2::{Digest, Sha256};
use serde_json::json;

fn setup() -> (tempfile::TempDir,rusqlite::Connection) {
    let dir=tempfile::tempdir().unwrap();
    let (mut conn,_)=bootstrap(dir.path().join("attempt.sqlite").to_str().unwrap()).unwrap();
    let sid=match source::import_source(&mut conn,"中😀\r\n".as_bytes(),"test.txt",None).unwrap() {
        ImportOutcome::Imported{source_id,..}=>source_id,_=>unreachable!()};
    jobs::enqueue(&mut conn,"j","text",&sid).unwrap();
    (dir,conn)
}
fn output(req:&Request) -> (Response,Vec<Vec<u8>>) {
    let payloads=vec!["中😀\r\n".as_bytes().to_vec(),serde_json::to_vec(&json!([
        {"kind":"line","path":["line-1"],"char_start":0,"char_end":4}])).unwrap(),
        serde_json::to_vec(&json!({"engine":"python-worker-text","engine_version":"0.1.0","params":{},
            "loss_note":null,"losses":[],"covered":1,"total":1,"coverage":1.0})).unwrap()];
    let meta=[("text","archeaxis.text/v1","text/plain; charset=utf-8"),
        ("document_structure","archeaxis.document-structure/v1","application/json"),
        ("loss_report","archeaxis.loss-receipt/v1","application/json")];
    let outputs=meta.into_iter().zip(&payloads).map(|((kind,schema,media),bytes)| {
        let sha=hex::encode(Sha256::digest(bytes));
        Output{kind:kind.into(),schema:schema.into(),media_type:media.into(),byte_length:bytes.len() as u64,
            uri:format!("job://output/{sha}"),sha256:sha,authority_effect:"candidate_or_measurement_only".into()}
    }).collect();
    (Response{schema:"archeaxis.worker-response/v1".into(),message_type:"job_result".into(),
        request_id:req.request_id.clone(),job_id:req.job_id.clone(),attempt:req.attempt,protocol_minor:0,
        status:"succeeded".into(),outputs,measurements:Default::default(),warnings:vec![],error:None},payloads)
}
#[test]
fn attempt_results_survive_reopen_and_replay_without_duplicate_outputs() {
    let (dir,mut conn)=setup();
    let req=attempts::claim(&mut conn,"j","r",5000).unwrap();
    assert_eq!(req.attempt,1);
    assert!(attempts::claim(&mut conn,"j","second",5000).is_err());
    assert!(jobs::complete(&mut conn,"j","fake","bypass",None).is_err());
    assert!(jobs::fail(&mut conn,"j","bypass").is_err());
    let (response,bytes)=output(&req);
    attempts::finish(&mut conn,&req,&response,&bytes).unwrap();
    drop(conn);
    let (mut conn,_)=bootstrap(dir.path().join("attempt.sqlite").to_str().unwrap()).unwrap();
    attempts::finish(&mut conn,&req,&response,&bytes).unwrap();
    assert_eq!(jobs::job_state(&conn,"j").unwrap().as_deref(),Some("succeeded"));
    let stored:Vec<(String,String)>=conn.prepare("SELECT kind,content FROM job_outputs ORDER BY kind").unwrap()
        .query_map([],|r|Ok((r.get(0)?,r.get(1)?))).unwrap().collect::<Result<_,_>>().unwrap();
    assert_eq!(stored.len(),3);
    assert_eq!(stored.iter().find(|(k,_)| k=="text").unwrap().1,"中😀\r\n");
    assert_eq!(conn.query_row("SELECT count(*) FROM transforms",[],|r|r.get::<_,i64>(0)).unwrap(),1);
    let mut changed=response; changed.warnings.push("different".into());
    assert!(attempts::finish(&mut conn,&req,&changed,&bytes).is_err());
}
#[test]
fn cancellation_recovery_and_retries_reject_all_late_results() {
    let (_dir,mut conn)=setup();
    let first=attempts::claim(&mut conn,"j","first",5000).unwrap();
    attempts::terminate(&mut conn,&first,"cancelled","owner cancelled").unwrap();
    attempts::terminate(&mut conn,&first,"cancelled","owner cancelled").unwrap();
    assert!(attempts::terminate(&mut conn,&first,"cancelled","different reason").is_err());
    let second=attempts::claim(&mut conn,"j","second",5000).unwrap();
    assert_eq!(second.attempt,2);
    let (r,b)=output(&first);
    assert!(attempts::finish(&mut conn,&first,&r,&b).is_err());
    assert!(attempts::terminate(&mut conn,&first,"failed","late").is_err());
    assert_eq!(attempts::recover_interrupted(&mut conn).unwrap(),1);
    assert_eq!(attempts::recover_interrupted(&mut conn).unwrap(),0);
    let (r,b)=output(&second);
    assert!(attempts::finish(&mut conn,&second,&r,&b).is_err());
    let third=attempts::claim(&mut conn,"j","third",5000).unwrap();
    assert_eq!(third.attempt,3);
    let (r,b)=output(&third); attempts::finish(&mut conn,&third,&r,&b).unwrap();
}
#[test]
fn invalid_content_and_injected_commit_failure_leave_zero_partial_outputs() {
    let (_dir,mut conn)=setup();
    let req=attempts::claim(&mut conn,"j","r",5000).unwrap();
    let (mut r,mut b)=output(&req);
    b[0].push(b'x'); assert!(attempts::finish(&mut conn,&req,&r,&b).is_err()); b[0].pop();
    let bad=br#"[{"kind":"line","path":["line-1"],"char_start":0,"char_end":99}]"#.to_vec();
    let old=std::mem::replace(&mut b[1],bad);
    r.outputs[1].sha256=hex::encode(Sha256::digest(&b[1]));
    r.outputs[1].uri=format!("job://output/{}",r.outputs[1].sha256); r.outputs[1].byte_length=b[1].len() as u64;
    assert!(attempts::finish(&mut conn,&req,&r,&b).is_err());
    b[1]=old;
    let (r,b)=output(&req);
    conn.execute_batch("CREATE TRIGGER break_output BEFORE INSERT ON job_outputs WHEN NEW.kind='loss_report' BEGIN SELECT RAISE(ABORT,'injected'); END;").unwrap();
    assert!(attempts::finish(&mut conn,&req,&r,&b).is_err());
    for table in ["transforms","job_outputs"] {
        assert_eq!(conn.query_row(&format!("SELECT count(*) FROM {table}"),[],|r|r.get::<_,i64>(0)).unwrap(),0);
    }
    assert_eq!(jobs::job_state(&conn,"j").unwrap().as_deref(),Some("running"));
    conn.execute_batch("DROP TRIGGER break_output").unwrap();
    attempts::finish(&mut conn,&req,&r,&b).unwrap();
}
