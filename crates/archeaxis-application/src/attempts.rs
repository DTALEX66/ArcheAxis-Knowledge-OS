//! Durable attempt identities and full text outputs, owned by the Core writer.
//! Process IO and file reading belong outside this transaction boundary.
use crate::jobs::{self, JobError, LossReceipt};
use archeaxis_sidecar_protocol::worker::{Request, Response, decode_response};
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::Deserialize;
use sha2::{Digest,Sha256};

/// R08: engine identities a successful receipt may report, one per extraction
/// route. The worker must name the engine it actually used; the Core no longer
/// requires the text engine from every route.
pub const ENGINE_PROFILES: &[(&str, &str)] = &[
    ("python-worker-text", "0.1.0"),
    ("pymupdf-native-pdf", "pymupdf"),
    ("python-worker-ocr", "0.1.0"),
];

/// R08: the extraction routes the Core can dispatch, declared once. A job's kind
/// selects the route, which fixes both the capability the worker must advertise
/// and the media type of the input asset - so a PDF or image job is a first-class
/// job instead of being refused by a text-only allow-list.
pub const ROUTES: &[(&str, &str, &str)] = &[
    ("text", "text.extract", "text/plain"),
    ("text.extract", "text.extract", "text/plain"),
    ("pdf", "pdf.extract", "application/pdf"),
    ("image", "image.ocr", "image/png"),
];

/// Resolve a job kind to its route: (capability, input media type).
pub fn route_for_kind(kind: &str) -> Option<(&'static str, &'static str)> {
    ROUTES
        .iter()
        .find(|(name, _, _)| *name == kind)
        .map(|(_, capability, media)| (*capability, *media))
}

/// R15/F04: the media types each route's worker actually accepts, mirroring the
/// transport's own route table (`services/python-workers/transport/text_ndjson.py`).
/// The Core used to pin one media type per job kind, which meant a JPEG was
/// announced to the OCR worker as `image/png`; a job's media type is now derived
/// from the source name and must be one of these.
pub const ROUTE_MEDIA_TYPES: &[(&str, &[&str])] = &[
    (
        "text.extract",
        &[
            "text/plain",
            "text/markdown",
            "text/csv",
            "text/tab-separated-values",
            "application/json",
            "application/xml",
            "text/xml",
        ],
    ),
    ("pdf.extract", &["application/pdf"]),
    (
        "image.ocr",
        &["image/png", "image/jpeg", "image/tiff", "image/webp", "image/bmp"],
    ),
];

/// The media types a capability's worker accepts (empty when the capability is unknown).
pub fn accepted_media_types(capability: &str) -> &'static [&'static str] {
    ROUTE_MEDIA_TYPES
        .iter()
        .find(|(name, _)| *name == capability)
        .map(|(_, types)| *types)
        .unwrap_or(&[])
}

/// R15/F06: the capabilities whose worker may write durable transfer files (the PDF
/// route renders text-less pages for the OCR route). The executor tells only these
/// workers where the artifact root is, so every other route keeps its launch shape
/// and an unexpected flag stays an error rather than being silently accepted.
pub const ARTIFACT_ROOT_CAPABILITIES: &[&str] = &["pdf.extract"];

/// R15/F06: routes whose successful job is followed by Core-side work, done inside the
/// same commit as the completion so there is no window in which the job says it
/// succeeded while the pages it declared were never queued.
pub const CHAINED_AFTER_SUCCESS: &[&str] = &["pdf.extract"];

/// The media type a file name denotes, or `None` when the extension is not one we
/// are willing to name. Guessing here is what the old pinned value effectively did.
pub fn media_type_for_name(name: &str) -> Option<&'static str> {
    let file = name.rsplit(['/', '\\']).next().unwrap_or(name).to_ascii_lowercase();
    let extension = file.rsplit_once('.')?.1;
    Some(match extension {
        "txt" | "log" | "text" | "rs" | "py" | "ts" | "tsx" | "js" | "jsx" | "c" | "h" | "cpp" | "hpp"
        | "go" | "java" | "cs" | "rb" | "sh" | "ps1" | "bat" | "toml" | "yaml" | "yml" | "ini" | "cfg"
        | "sql" => "text/plain",
        "md" | "markdown" => "text/markdown",
        "csv" => "text/csv",
        "tsv" => "text/tab-separated-values",
        "json" | "canvas" => "application/json",
        "xml" => "application/xml",
        // subtitles are textual documents; the worker recognises their cue structure
        // and reports it as a fact rather than inventing a media type the route does
        // not accept
        "srt" | "vtt" => "text/plain",
        "pdf" => "application/pdf",
        "png" => "image/png",
        "jpg" | "jpeg" | "jpe" => "image/jpeg",
        "tif" | "tiff" => "image/tiff",
        "webp" => "image/webp",
        "bmp" => "image/bmp",
        _ => return None,
    })
}

/// The media type to announce for one claimed job: derived from the source name and
/// required to be accepted by the route's worker.
pub fn resolve_media_type(kind: &str, original_name: &str) -> Result<&'static str, JobError> {
    let (capability, _default) =
        route_for_kind(kind).ok_or(JobError::InvalidReceipt("undeclared job kind"))?;
    let accepted = accepted_media_types(capability);
    let derived = media_type_for_name(original_name);
    match derived {
        Some(media) if accepted.contains(&media) => Ok(media),
        _ => Err(JobError::MediaTypeNotAccepted {
            kind: kind.to_string(),
            name: original_name.to_string(),
            derived,
            accepted,
        }),
    }
}

pub fn claim(conn:&mut Connection, job_id:&str, request_id:&str, deadline_ms:u64) -> Result<Request,JobError> {
    let tx=conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let row:Option<(String,String,String,String)>=tx.query_row(
        "SELECT j.state,j.kind,s.sha256,COALESCE(s.original_name,'') FROM jobs j JOIN sources s ON s.source_id=j.input_ref WHERE j.job_id=?1",
        [job_id],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let (state,kind,sha,name)=row.ok_or(JobError::NotFound)?;
    if !matches!(state.as_str(),"queued"|"failed"|"cancelled") {
        return Err(JobError::InvalidState);
    }
    let capability=match route_for_kind(&kind) {
        Some((capability,_))=>capability,
        None=>return Err(JobError::InvalidReceipt("undeclared job kind")),
    };
    // the media type comes from what the file is, not from a value pinned to the kind
    let media_type=resolve_media_type(&kind,&name)?;
    let next:i64=tx.query_row("SELECT COALESCE(MAX(attempt),0)+1 FROM job_attempts WHERE job_id=?1",[job_id],|r|r.get(0))?;
    let request=Request::job(request_id,job_id,next as u64,capability,&sha,media_type,deadline_ms).map_err(JobError::InvalidReceipt)?;
    tx.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES(?1,?2,?3,?4,'running')",
        rusqlite::params![job_id,next,request_id,serde_json::to_string(&request).map_err(|_|JobError::Conflict)?])?;
    tx.execute("UPDATE jobs SET state='running',completed_at=NULL WHERE job_id=?1",[job_id])?;
    tx.commit()?;
    Ok(request)
}

/// R08: compare anchors by kind and character span, tolerating extra leading path
/// components. A page-qualified anchor `["page-3","line-12"]` addresses the same
/// projected line as the canonical `["line-12"]`, so the Core checks that the
/// spans and the final path segment match - not that every route spells its path
/// exactly like the text route.
fn same_spans(found:&[Line], expected:&[Line]) -> bool {
    found.len()==expected.len() && found.iter().zip(expected).all(|(a,b)|
        a.kind==b.kind && a.char_start==b.char_start && a.char_end==b.char_end
        && a.path.last()==b.path.last())
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
    if !ENGINE_PROFILES
        .iter()
        .any(|(name, version)| loss.engine == *name && loss.engine_version == *version)
        || !same_spans(&structure,&expected)
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
