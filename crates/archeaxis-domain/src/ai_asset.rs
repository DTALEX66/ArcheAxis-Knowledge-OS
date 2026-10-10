//! Versioned, inert AI assets; adoption is scoped human review, never knowledge truth.
use crate::{document::{self,Error},machine_evaluation::{Rubric,Judgment,Outcome},object_reference::{self,Reference}};
use rusqlite::{Connection,OptionalExtension};
use serde::{Serialize,Deserialize};
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::collections::BTreeSet;
pub const NAMESPACE:&str="archeaxis_ai_asset";
pub const SCHEMA:&str="archeaxis.ai-asset/v1";
#[derive(Debug,Clone,PartialEq,Eq,Serialize,Deserialize)]
#[serde(rename_all="snake_case")]
pub enum Kind {Memory,KnowledgePackage,Rule,Skill,Experience}
#[derive(Debug,Clone,PartialEq,Eq,Serialize,Deserialize)]
#[serde(rename_all="snake_case")]
pub enum State {Candidate,Adopted,Withdrawn}
#[derive(Debug,Clone,PartialEq,Eq,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Snapshot {pub document_id:String,pub version:i64,pub content_sha256:String}
#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Review {pub asset:Snapshot,pub rubric:Snapshot,pub reviewer:String,pub basis:String,pub judgments:Vec<Judgment>,pub outcome:Outcome}
#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AiAsset {
    pub schema:String,pub kind:Kind,pub content:Value,pub purpose:String,
    pub scope:Vec<Reference>,pub provenance:Vec<Reference>,pub expires_at:Option<u64>,pub state:State,
    pub members:Vec<Snapshot>,pub conflicts:Vec<Snapshot>,pub revises:Option<Snapshot>,
    pub review:Option<Review>,pub source_payload:Option<Value>,
}
fn invalid(s:&'static str)->Error {Error::Invalid(s)}
pub fn hash(value:&Value)->String {hex::encode(Sha256::digest(value.to_string().as_bytes()))}
fn bounded_json(value:&Value,depth:usize,nodes:&mut usize)->bool {
    *nodes+=1;if depth>16 || *nodes>4096 {return false;}
    match value {Value::Array(a)=>a.iter().all(|v|bounded_json(v,depth+1,nodes)),Value::Object(o)=>o.values().all(|v|bounded_json(v,depth+1,nodes)),_=>true}
}
pub fn metadata(editor:&Value)->Result<Option<AiAsset>,Error> {
    editor.get("attrs").and_then(|a|a.get(NAMESPACE)).map(|v|serde_json::from_value(v.clone())
        .map_err(|_|invalid("unknown AI asset shape; preserve original read-only"))).transpose()
}
pub fn read_snapshot(conn:&Connection,snapshot:&Snapshot,current:bool)->Result<Value,Error> {
    if snapshot.version<1 || snapshot.document_id.is_empty() || snapshot.document_id.len()>128
        || snapshot.content_sha256.len()!=64 || !snapshot.content_sha256.bytes().all(|b|b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
        return Err(invalid("AI asset reference requires a real document/version/SHA256"));
    }
    let d=document::read(conn,&snapshot.document_id,if current {None}else{Some(snapshot.version)})?;
    if d["version"]!=snapshot.version || d["content_sha256"]!=snapshot.content_sha256 {return Err(invalid("AI asset reference is stale or hash differs"));}
    Ok(d)
}
pub fn snapshot(doc:&Value)->Result<Snapshot,Error> {Ok(Snapshot {
    document_id:doc["document_id"].as_str().ok_or(invalid("missing document identity"))?.into(),
    version:doc["version"].as_i64().ok_or(invalid("missing version"))?,
    content_sha256:doc["content_sha256"].as_str().ok_or(invalid("missing snapshot hash"))?.into(),
})}
fn semantic_payload(asset:&AiAsset)->Result<Value,Error> {
    let mut v=serde_json::to_value(asset).map_err(|_|invalid("asset serialization failed"))?;
    v.as_object_mut().unwrap().remove("state");v.as_object_mut().unwrap().remove("review");Ok(v)
}
fn validate_review(conn:&Connection,id:&str,asset:&AiAsset,review:&Review)->Result<(),Error> {
    if review.asset.document_id!=id || review.reviewer.trim().is_empty() || review.reviewer.len()>128
        || review.basis.trim().is_empty() || review.basis.len()>16384 {return Err(invalid("review requires same saved asset identity and human observation basis"));}
    let original=read_snapshot(conn,&review.asset,false)?;
    let reviewed=metadata(&original["editor_json"])?.ok_or(invalid("reviewed version is not an AI asset"))?;
    if reviewed.state==State::Withdrawn || semantic_payload(&reviewed)?!=semantic_payload(asset)? {
        return Err(invalid("asset changed after reviewed snapshot; save a new candidate and review it"));
    }
    let rubric_doc=read_snapshot(conn,&review.rubric,false)?;
    let raw=rubric_doc["editor_json"]["attrs"].get(crate::machine_evaluation::RUBRIC_NAMESPACE).ok_or(invalid("review rubric is not a fixed real rubric"))?;
    let rubric:Rubric=serde_json::from_value(raw.clone()).map_err(|_|invalid("unsupported rubric shape"))?;
    if rubric.schema!=crate::machine_evaluation::RUBRIC_SCHEMA || rubric.criteria.is_empty() || rubric.criteria.len()>64
        || review.judgments.len()!=rubric.criteria.len() {return Err(invalid("asset review must cover every fixed rubric criterion"));}
    let mut seen=BTreeSet::new();
    for j in &review.judgments {
        if !seen.insert(&j.criterion_id) || !rubric.criteria.iter().any(|c|c.criterion_id==j.criterion_id)
            || j.basis.trim().is_empty() || j.basis.len()>16384 {return Err(invalid("review judgments require unique actual criteria and explicit basis"));}
    }
    let outcome=if review.judgments.iter().any(|j|j.outcome==Outcome::Failed) {Outcome::Failed}
        else if review.judgments.iter().any(|j|j.outcome==Outcome::Unmeasured) {Outcome::Unmeasured}else{Outcome::Passed};
    if review.outcome!=outcome {return Err(invalid("review outcome differs from individual human judgments"));}
    Ok(())
}
pub fn validate_editor(conn:&Connection,id:&str,editor:&Value)->Result<(),Error> {
    let Some(asset)=metadata(editor)? else{return Ok(());};
    let serialized=serde_json::to_value(&asset).map_err(|_|invalid("AI asset serialization failed"))?;
    if asset.schema!=SCHEMA || asset.purpose.len()>1024 || asset.scope.len()>32 || asset.provenance.len()>32
        || asset.members.len()>64 || asset.conflicts.len()>32 || asset.expires_at.is_some_and(|n|n>253402300799)
        || asset.content.to_string().len()+asset.source_payload.as_ref().map(|v|v.to_string().len()).unwrap_or(0)>65536
        || serialized.to_string().len()>128000 || !bounded_json(&serialized,0,&mut 0)
        || (asset.kind!=Kind::KnowledgePackage && !asset.members.is_empty()) {return Err(invalid("AI asset bounds or package shape unsupported"));}
    let withdrawn:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1
        AND json_extract(editor_json,'$.attrs.archeaxis_ai_asset.state')='withdrawn')",[id],|r|r.get(0))?;
    if withdrawn && asset.state!=State::Withdrawn {return Err(invalid("withdrawn asset identity cannot be reactivated; create a new candidate"));}
    if asset.state==State::Withdrawn {
        // Permission removal must remain possible when old source/member/rubric is unavailable.
        for r in asset.scope.iter().chain(asset.provenance.iter()) {object_reference::validate_shape(r)?;}
        for r in asset.members.iter().chain(asset.conflicts.iter()).chain(asset.revises.iter()) {
            if r.document_id.is_empty() || r.document_id.len()>128 || r.version<1 || r.content_sha256.len()!=64 {
                return Err(invalid("withdrawn asset must retain well-shaped historical references"));
            }
        }
        return Ok(());
    }
    // Drafts need no adoption or purpose. Explicit typed references still identify real objects.
    for r in asset.scope.iter().chain(asset.provenance.iter()) {object_reference::validate(conn,r)?;}
    let mut members=BTreeSet::new();
    for r in &asset.members {
        if !members.insert((&r.document_id,r.version)) {return Err(invalid("duplicate package member"));}
        let d=read_snapshot(conn,r,false)?;
        metadata(&d["editor_json"])?.ok_or(invalid("package member is not a real AI asset"))?;
    }
    for r in asset.conflicts.iter().chain(asset.revises.iter()) {
        let d=read_snapshot(conn,r,false)?;metadata(&d["editor_json"])?.ok_or(invalid("conflict/revision must reference a real AI asset version"))?;
    }
    if let Some(review)=&asset.review {validate_review(conn,id,&asset,review)?;}
    if asset.state==State::Adopted && (asset.purpose.trim().is_empty() || !asset.review.as_ref().is_some_and(|r|r.outcome==Outcome::Passed)) {
        return Err(invalid("adoption requires explicit purpose and passed fixed human asset review"));
    }
    Ok(())
}

/// Read only a bounded tree of current, adopted asset metadata. Source refs are
/// descriptors: no full Document body, CAS bytes, private session or tool execution.
pub fn packet_items(conn:&Connection,root:&Snapshot,now:u64)->Result<Vec<Value>,Error> {
    fn visit(conn:&Connection,s:&Snapshot,now:u64,depth:usize,seen:&mut BTreeSet<String>,out:&mut Vec<Value>)->Result<(),Error> {
        if depth>4 || out.len()>=128 || !seen.insert(s.document_id.clone()) {return Err(invalid("package graph cyclic, duplicate or exceeds bounded expansion"));}
        let d=read_snapshot(conn,s,true)?;let asset=metadata(&d["editor_json"])?.ok_or(invalid("referenced document is not an AI asset"))?;
        validate_editor(conn,&s.document_id,&d["editor_json"])?;
        if asset.state!=State::Adopted || asset.expires_at.is_some_and(|expiry|now>=expiry) {return Err(invalid("asset/member is unadopted, withdrawn or expired"));}
        if !asset.conflicts.is_empty() {return Err(invalid("declared unresolved asset conflicts require a new reviewed revision"));}
        out.push(json!({"snapshot":s,"kind":asset.kind,"content":asset.content,"purpose":asset.purpose,
            "scope":asset.scope,"provenance":asset.provenance,"engine_execution":"NOT_EXECUTED",
            "grants_professional_truth":false,"grants_human_mastery":false,"grants_machine_qualification":false}));
        for member in &asset.members {visit(conn,member,now,depth+1,seen,out)?;}
        Ok(())
    }
    let mut out=Vec::new();visit(conn,root,now,0,&mut BTreeSet::new(),&mut out)?;
    if serde_json::to_vec(&out).map_err(|_|invalid("packet serialization failed"))?.len()>128000 {return Err(invalid("context packet exceeds bounded output"));}
    Ok(out)
}
