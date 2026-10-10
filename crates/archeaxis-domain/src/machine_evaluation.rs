//! Human observations bound to immutable Document rubric and persisted runtime answers.
//! No machine receipt rewriting, automatic knowledge promotion, mastery or Agent execution.
use crate::{document::{self, Error}, object_reference::{self, Reference}};
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

pub const RUBRIC_NAMESPACE: &str = "archeaxis_machine_rubric";
pub const EVALUATION_NAMESPACE: &str = "archeaxis_machine_evaluation";
pub const RUBRIC_SCHEMA: &str = "archeaxis.machine-rubric/v1";
pub const EVALUATION_SCHEMA: &str = "archeaxis.machine-evaluation/v1";
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Criterion { pub criterion_id: String, pub label: String, pub expectation: String }
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rubric { pub schema: String, pub request_id: String, pub title: String, pub purpose: String, pub criteria: Vec<Criterion>, pub sources: Vec<Reference> }
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RubricSnapshot { pub document_id: String, pub version: i64, pub content_sha256: String }
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome { Passed, Failed, Unmeasured }
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Judgment { pub criterion_id: String, pub outcome: Outcome, pub basis: String }
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Evaluation {
    pub schema: String, pub request_id: String, pub task_id: String, pub knowledge_id: String,
    pub original_answer_sha256: String, pub task_receipt_sha256: String,
    pub rubric: RubricSnapshot, pub reviewer: String, pub basis: String,
    pub judgments: Vec<Judgment>, pub outcome: Outcome,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvaluationRequest { pub request_id: String, pub task_id: String, pub rubric: RubricSnapshot, pub reviewer: String, pub basis: String, pub judgments: Vec<Judgment>, pub outcome: Outcome }
fn invalid(message: &'static str) -> Error { Error::Invalid(message) }
fn token(s: &str) -> bool { !s.is_empty() && s.len() <= 128 && s.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-')) }
fn nonblank(s: &str, limit: usize) -> bool { !s.trim().is_empty() && s.len() <= limit }
fn hash(s: &str) -> String { hex::encode(Sha256::digest(s.as_bytes())) }
fn digest(s: &str) -> bool { s.len() == 64 && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) }
fn document_id(request_id: &str) -> String { format!("doc_req_{}", hash(request_id)) }
fn metadata<'a>(editor: &'a Value, key: &str) -> Option<&'a Value> { editor.get("attrs").and_then(|a| a.get(key)) }
pub fn is_protected(editor: &Value) -> bool { metadata(editor, RUBRIC_NAMESPACE).is_some() || metadata(editor, EVALUATION_NAMESPACE).is_some() }
pub fn require_human(trusted_actor: &str) -> Result<(), Error> { if trusted_actor == "human" { Ok(()) } else { Err(invalid("machine rubric/evaluation requires a trusted human actor; reviewer is annotation only")) } }

fn validate_rubric(conn: &Connection, rubric: &Rubric) -> Result<(), Error> {
    if rubric.schema != RUBRIC_SCHEMA || !token(&rubric.request_id) || !nonblank(&rubric.title, 512) || !nonblank(&rubric.purpose, 512) || rubric.criteria.is_empty() || rubric.criteria.len() > 64 || rubric.sources.len() > 64 { return Err(invalid("invalid bounded rubric metadata")); }
    let mut ids = BTreeSet::new();
    for criterion in &rubric.criteria {
        if !token(&criterion.criterion_id) || !ids.insert(&criterion.criterion_id) || !nonblank(&criterion.label, 512) || !nonblank(&criterion.expectation, 4096) { return Err(invalid("rubric criteria require distinct IDs and explicit bounded expectations")); }
    }
    for source in &rubric.sources { object_reference::validate(conn, source)?; }
    Ok(())
}
fn pinned_rubric(conn: &Connection, reference: &RubricSnapshot) -> Result<Rubric, Error> {
    if reference.version < 1 || !token(&reference.document_id) || !digest(&reference.content_sha256) { return Err(invalid("rubric needs a pinned real document/version/SHA256")); }
    let d = document::read(conn, &reference.document_id, Some(reference.version))?;
    if d["content_sha256"].as_str() != Some(reference.content_sha256.as_str()) { return Err(invalid("rubric snapshot hash differs from stored immutable version")); }
    let rubric: Rubric = serde_json::from_value(metadata(&d["editor_json"], RUBRIC_NAMESPACE).ok_or(invalid("pinned document is not a machine rubric"))?.clone()).map_err(|_| invalid("unsupported stored rubric shape; preserve historical original"))?;
    validate_rubric(conn, &rubric)?;
    Ok(rubric)
}
/// Read only: never ensure/create machine_tasks, never read external native memory or CAS bytes.
pub fn answer_snapshot(conn: &Connection, task_id: &str) -> Result<Value, Error> {
    if !token(task_id) { return Err(invalid("machine answer task ID must be bounded ASCII")); }
    let exists: bool = conn.query_row("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='machine_tasks')", [], |r| r.get(0))?;
    if !exists { return Err(Error::NotFound); }
    let row: Option<(String,String,String,Option<String>,Option<String>,Option<String>,String,String,Option<String>,Option<String>,String)> = conn.query_row(
        "SELECT principal,scope,conditions,knowledge_version,method_version,tool_version,model_version,outcome,failure,retest_of,recorded_at FROM machine_tasks WHERE task_id=?1", [task_id],
        |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?,r.get(5)?,r.get(6)?,r.get(7)?,r.get(8)?,r.get(9)?,r.get(10)?))).optional()?;
    let (principal,scope,conditions,knowledge_version,method_version,tool_version,model_version,outcome,failure,retest_of,recorded_at) = row.ok_or(Error::NotFound)?;
    if principal != "machine" || !matches!(scope.as_str(), "runtime.answer" | "runtime.retest") || conditions.len() > 1_048_576 { return Err(invalid("evaluation must bind a persisted Core runtime answer/retest, not a self-reported task")); }
    let doc: Value = serde_json::from_str(&conditions).map_err(|_| invalid("stored answer conditions are not JSON"))?;
    let expected_schema = if scope == "runtime.answer" { "archeaxis.machine-answer/v1" } else { "archeaxis.machine-retest/v1" };
    if doc["schema"] != expected_schema || doc["answer_id"].as_str() != Some(task_id) || (scope == "runtime.retest" && doc["retest_task_id"].as_str() != Some(task_id)) { return Err(invalid("stored answer identity/schema is inconsistent")); }
    let knowledge_id = doc["knowledge_id"].as_str().filter(|s| token(s)).ok_or(invalid("stored answer needs real immutable knowledge identity"))?;
    let declared = knowledge_version.as_deref().ok_or(invalid("stored receipt lacks knowledge binding"))?.split_once('@').map(|(id,_)| id).unwrap_or(knowledge_version.as_deref().unwrap());
    if declared != knowledge_id { return Err(invalid("stored receipt and answer knowledge identity differ")); }
    object_reference::validate(conn, &Reference::Knowledge { knowledge_id: knowledge_id.to_owned() })?;
    let answer = doc["answer"]["answer"].as_str().filter(|s| !s.trim().is_empty()).ok_or(invalid("stored answer is empty or missing"))?;
    if answer.len() > 65_536 || doc["question"].as_str().is_none_or(|s| !nonblank(s, 16_384)) || doc["answer"]["model"].as_str() != Some(model_version.as_str()) { return Err(invalid("stored answer question/model/size is inconsistent")); }
    let receipt = json!({"task_id":task_id,"principal":principal,"scope":scope,"conditions":conditions,"knowledge_version":knowledge_version,"method_version":method_version,"tool_version":tool_version,"model_version":model_version,"outcome":outcome,"failure":failure,"retest_of":retest_of,"recorded_at":recorded_at});
    Ok(json!({"task_id":task_id,"knowledge_id":knowledge_id,"question":doc["question"],"original_answer":answer,"model_version":model_version,"original_answer_sha256":hash(answer),"task_receipt_sha256":hash(&receipt.to_string()),"receipt":receipt,"evaluation_authority":"human_observation_only","grants_machine_qualification":false,"grants_human_mastery":false,"grants_professional_truth":false}))
}
fn validate_evaluation(conn: &Connection, e: &Evaluation) -> Result<(), Error> {
    if e.schema != EVALUATION_SCHEMA || !token(&e.request_id) || !nonblank(&e.reviewer, 128) || !nonblank(&e.basis, 16_384) || e.judgments.is_empty() || e.judgments.len() > 64 { return Err(invalid("evaluation needs fixed schema/request identity, reviewer annotation and concrete basis")); }
    let original = answer_snapshot(conn, &e.task_id)?;
    if original["knowledge_id"].as_str() != Some(e.knowledge_id.as_str()) || original["original_answer_sha256"].as_str() != Some(e.original_answer_sha256.as_str()) || original["task_receipt_sha256"].as_str() != Some(e.task_receipt_sha256.as_str()) { return Err(invalid("evaluation original answer/receipt/knowledge differs from persisted immutable task")); }
    let rubric = pinned_rubric(conn, &e.rubric)?;
    let criteria: BTreeSet<&str> = rubric.criteria.iter().map(|c| c.criterion_id.as_str()).collect();
    let mut judged = BTreeSet::new(); let mut overall = Outcome::Passed;
    for judgment in &e.judgments {
        if !criteria.contains(judgment.criterion_id.as_str()) || !judged.insert(judgment.criterion_id.as_str()) || !nonblank(&judgment.basis, 4096) { return Err(invalid("each rubric criterion must have one human judgment and a bounded basis")); }
        if judgment.outcome == Outcome::Failed { overall = Outcome::Failed; } else if judgment.outcome == Outcome::Unmeasured && overall != Outcome::Failed { overall = Outcome::Unmeasured; }
    }
    if judged != criteria || e.outcome != overall { return Err(invalid("evaluation must cover the fixed rubric; overall failed/unmeasured/passed must match judgments")); }
    Ok(())
}
/// Required canonical Document.append hook; rejection occurs before any version is inserted.
pub fn validate_transition(conn: &Connection, id: &str, expected: i64, editor: &Value) -> Result<(), Error> {
    let rubric_raw = metadata(editor, RUBRIC_NAMESPACE); let evaluation_raw = metadata(editor, EVALUATION_NAMESPACE);
    if rubric_raw.is_some() && evaluation_raw.is_some() { return Err(invalid("one document cannot be both a rubric and an evaluation")); }
    if evaluation_raw.is_some() {
        let was_rubric:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1
            AND json_type(editor_json,'$.attrs.archeaxis_machine_rubric') IS NOT NULL)",[id],|r|r.get(0))?;
        if was_rubric {return Err(invalid("rubric document identity cannot become an evaluation after metadata removal"));}
    }
    if expected > 0 {
        let prior = document::read(conn, id, Some(expected))?;
        if let Some(old) = metadata(&prior["editor_json"], EVALUATION_NAMESPACE) {
            if evaluation_raw != Some(old) || rubric_raw.is_some() { return Err(invalid("registered machine evaluation cannot be changed, removed or repurposed; create a new evaluation request")); }
        }
        if metadata(&prior["editor_json"], RUBRIC_NAMESPACE).is_some() && evaluation_raw.is_some() { return Err(invalid("rubric document cannot be repurposed as an evaluation")); }
    }
    if let Some(raw) = rubric_raw {
        let rubric: Rubric = serde_json::from_value(raw.clone()).map_err(|_| invalid("rubric metadata shape is invalid or unsupported"))?;
        if document_id(&rubric.request_id) != id { return Err(invalid("rubric request ID must identify its canonical document")); }
        validate_rubric(conn, &rubric)?;
    }
    if let Some(raw) = evaluation_raw {
        let e: Evaluation = serde_json::from_value(raw.clone()).map_err(|_| invalid("evaluation metadata shape is invalid or unsupported"))?;
        if document_id(&e.request_id) != id { return Err(invalid("evaluation request ID must identify its canonical document")); }
        validate_evaluation(conn, &e)?;
    }
    Ok(())
}
pub fn create_rubric(conn: &mut Connection, trusted_actor: &str, rubric: &Rubric) -> Result<Value, Error> {
    require_human(trusted_actor)?; validate_rubric(conn, rubric)?;
    let editor = json!({"type":"doc","attrs":{(RUBRIC_NAMESPACE):rubric},"content":[]});
    document::create_optional_with_request(conn,None,None,&rubric.title,editor,Some(&rubric.request_id))
}
pub fn create_evaluation(conn: &mut Connection, trusted_actor: &str, request: &EvaluationRequest) -> Result<Value, Error> {
    require_human(trusted_actor)?;
    let original = answer_snapshot(conn, &request.task_id)?;
    let evaluation = Evaluation { schema:EVALUATION_SCHEMA.into(),request_id:request.request_id.clone(),task_id:request.task_id.clone(),knowledge_id:original["knowledge_id"].as_str().unwrap().into(),original_answer_sha256:original["original_answer_sha256"].as_str().unwrap().into(),task_receipt_sha256:original["task_receipt_sha256"].as_str().unwrap().into(),rubric:request.rubric.clone(),reviewer:request.reviewer.clone(),basis:request.basis.clone(),judgments:request.judgments.clone(),outcome:request.outcome };
    validate_evaluation(conn, &evaluation)?;
    let editor = json!({"type":"doc","attrs":{(EVALUATION_NAMESPACE):evaluation},"content":[]});
    document::create_optional_with_request(conn,None,None,"人工机器评测",editor,Some(&request.request_id))
}
pub fn text_projection(editor: &Value) -> Option<String> {
    if let Some(raw) = metadata(editor, RUBRIC_NAMESPACE) {
        let r: Rubric = serde_json::from_value(raw.clone()).ok()?;
        return Some(std::iter::once(r.title).chain(std::iter::once(r.purpose)).chain(r.criteria.into_iter().flat_map(|c| [c.label,c.expectation])).collect::<Vec<_>>().join("\n"));
    }
    let e: Evaluation = serde_json::from_value(metadata(editor, EVALUATION_NAMESPACE)?.clone()).ok()?;
    Some(std::iter::once(e.basis).chain(e.judgments.into_iter().map(|j| j.basis)).collect::<Vec<_>>().join("\n"))
}
