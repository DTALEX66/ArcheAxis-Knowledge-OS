//! Durable attempt identities and full text outputs, owned by the Core writer.
//! Process IO and file reading belong outside this transaction boundary.
use crate::jobs::{self, JobError, LossReceipt};
use archeaxis_sidecar_protocol::worker::{Request, Response, decode_response};
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::Deserialize;
use sha2::{Digest,Sha256};

pub fn claim(conn:&mut Connection, job_id:&str, request_id:&str, deadline_ms:u64) -> Result<Request,JobError> {
    let tx=conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let row:Option<(String,String,String)>=tx.query_row(
        "SELECT j.state,j.kind,s.sha256 FROM jobs j JOIN sources s ON s.source_id=j.input_ref WHERE j.job_id=?1",
        [job_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let (state,kind,sha)=row.ok_or(JobError::NotFound)?;
    if !matches!(state.as_str(),"queued"|"failed"|"cancelled") || !matches!(kind.as_str(),"text"|"text.extract") {
        return Err(JobError::InvalidState);
    }
    let next:i64=tx.query_row("SELECT COALESCE(MAX(attempt),0)+1 FROM job_attempts WHERE job_id=?1",[job_id],|r|r.get(0))?;
    let request=Request::text(request_id,job_id,next as u64,&sha,"text/plain",deadline_ms).map_err(JobError::InvalidReceipt)?;
    tx.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES(?1,?2,?3,?4,'running')",
        rusqlite::params![job_id,next,request_id,serde_json::to_string(&request).map_err(|_|JobError::Conflict)?])?;
    tx.execute("UPDATE jobs SET state='running',completed_at=NULL WHERE job_id=?1",[job_id])?;
    tx.commit()?;
    Ok(request)
}

fn identity(conn:&Connection, req:&Request) -> Result<(String,Option<String>),JobError> {
    let row:Option<(String,Option<String>,String,i64)>=conn.query_row(
        "SELECT state,result_digest,request_json,(SELECT MAX(attempt) FROM job_attempts WHERE job_id=?1) FROM job_attempts WHERE job_id=?1 AND attempt=?2",
        rusqlite::params![req.job_id,req.attempt],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let (state,digest,stored,latest)=row.ok_or(JobError::NotFound)?;
    if latest as u64!=req.attempt || stored!=serde_json::to_string(req).map_err(|_|JobError::Conflict)? { return Err(JobError::Conflict); }
    Ok((state,digest))
}

#[derive(Deserialize,PartialEq,Debug)]
#[serde(deny_unknown_fields)]
struct Line { kind:String, path:Vec<String>, char_start:usize, char_end:usize }

fn expected_lines(text:&str) -> (Vec<Line>,usize) {
    // Python str.splitlines(keepends=True), in Unicode scalar offsets.
    let mut chars=text.chars().peekable();
    let mut lines=Vec::new(); let mut start=0; let mut i=0; let mut total=0;
    while let Some(ch)=chars.next() {
        let separator=matches!(ch,'\n'|'\r'|'\u{b}'|'\u{c}'|'\u{1c}'|'\u{1d}'|'\u{1e}'|'\u{85}'|'\u{2028}'|'\u{2029}');
        if ch=='\r' && chars.peek()==Some(&'\n') { chars.next(); i+=1; }
        i+=1;
        if separator || chars.peek().is_none() {
            total+=1;
            if lines.len()<5000 {lines.push(Line{kind:"line".into(),path:vec![format!("line-{total}")],char_start:start,char_end:i});}
            start=i;
        }
    }
    (lines,total)
}

/// Validate metadata AND bytes before any authoritative write. Contents remain
/// byte-faithful UTF-8 in this text profile; binary workers need a separate profile.
pub fn finish(conn:&mut Connection, req:&Request, response:&Response, payloads:&[Vec<u8>]) -> Result<(),JobError> {
    let wire=serde_json::to_string(response).map_err(|_|JobError::Conflict)?;
    let response=decode_response(&wire,req).map_err(JobError::InvalidReceipt)?;
    if response.status!="succeeded" || payloads.len()!=3 { return Err(JobError::InvalidState); }
    let mut text=None; let mut structure=None; let mut loss=None; let mut strings=Vec::new();
    for (output,bytes) in response.outputs.iter().zip(payloads) {
        if bytes.len()>16*1024*1024 || output.byte_length!=bytes.len() as u64
            || hex::encode(Sha256::digest(bytes))!=output.sha256 { return Err(JobError::InvalidReceipt("output hash or size mismatch")); }
        let content=std::str::from_utf8(bytes).map_err(|_|JobError::InvalidReceipt("text profile output is not UTF-8"))?;
        match output.kind.as_str() {
            "text"=>text=Some(content),
            "document_structure"=>structure=Some(serde_json::from_str::<Vec<Line>>(content).map_err(|_|JobError::InvalidReceipt("invalid line structure"))?),
            "loss_report"=>loss=Some(serde_json::from_str::<LossReceipt>(content).map_err(|_|JobError::InvalidReceipt("invalid loss receipt"))?),
            _=>return Err(JobError::InvalidReceipt("unsupported output")),
        }
        strings.push(content);
    }
    let text=text.ok_or(JobError::InvalidReceipt("missing text"))?;
    let (expected,total)=expected_lines(text);
    let structure=structure.ok_or(JobError::InvalidReceipt("missing structure"))?;
    let loss=loss.ok_or(JobError::InvalidReceipt("missing loss receipt"))?;
    loss.validate().map_err(JobError::InvalidReceipt)?;
    if loss.engine!="python-worker-text" || loss.engine_version!="0.1.0"
        || structure!=expected
        || loss.covered!=Some(structure.len() as u64) || loss.total!=Some(total as u64) {
        return Err(JobError::InvalidReceipt("structure or coverage does not match projected text"));
    }
    let digest=hex::encode(Sha256::digest(wire.as_bytes()));
    let tx=conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let (state,old)=identity(&tx,req)?;
    if state=="succeeded" { return if old.as_deref()==Some(&digest) {Ok(())} else {Err(JobError::Conflict)}; }
    if state!="running" {return Err(JobError::InvalidState);}
    jobs::complete_tx(&tx,&req.job_id,&loss.engine,text,Some(&loss))?;
    for (output,content) in response.outputs.iter().zip(strings) {
        tx.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES(?1,?2,?3,?4,?5)",
            rusqlite::params![req.job_id,req.attempt,output.kind,serde_json::to_string(output).map_err(|_|JobError::Conflict)?,content])?;
    }
    tx.execute("UPDATE job_attempts SET state='succeeded',response_json=?1,result_digest=?2,completed_at=datetime('now') WHERE job_id=?3 AND attempt=?4",
        rusqlite::params![wire,digest,req.job_id,req.attempt])?;
    tx.commit()?; Ok(())
}

pub fn terminate(conn:&mut Connection,req:&Request,status:&str,error:&str) -> Result<(),JobError> {
    if !matches!(status,"failed"|"rejected"|"cancelled") || error.trim().is_empty() {return Err(JobError::InvalidState);}
    let tx=conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let (state,_)=identity(&tx,req)?;
    if state==status {
        let old:Option<String>=tx.query_row("SELECT error FROM job_attempts WHERE job_id=?1 AND attempt=?2",
            rusqlite::params![req.job_id,req.attempt],|r|r.get(0))?;
        return if old.as_deref()==Some(error){Ok(())}else{Err(JobError::Conflict)};
    }
    if state!="running" {return Err(JobError::InvalidState);}
    tx.execute("UPDATE job_attempts SET state=?1,error=?2,completed_at=datetime('now') WHERE job_id=?3 AND attempt=?4",
        rusqlite::params![status,error,req.job_id,req.attempt])?;
    tx.execute("UPDATE jobs SET state=?1,loss_receipt=?2,completed_at=datetime('now') WHERE job_id=?3",
        rusqlite::params![status,serde_json::json!({"error":error}).to_string(),req.job_id])?;
    tx.commit()?; Ok(())
}

/// Invoke only during exclusive Core startup, before accepting work. Never run
/// as periodic maintenance while an executor can still be using these attempts.
pub fn recover_interrupted(conn:&mut Connection) -> Result<usize,JobError> {
    let tx=conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    tx.execute("UPDATE jobs SET state='failed',loss_receipt='{\"error\":\"interrupted Core attempt\"}',completed_at=datetime('now') WHERE state='running' AND job_id IN (SELECT job_id FROM job_attempts WHERE state='running')",[])?;
    let count=tx.execute("UPDATE job_attempts SET state='failed',error='interrupted Core attempt',completed_at=datetime('now') WHERE state='running'",[])?;
    tx.commit()?; Ok(count)
}
