//! DeepTutor's donor teaching-feedback rules as a Core-owned candidate route.
//!
//! The donor worker updates one caller-supplied learner profile in memory and
//! returns the original objective-focused guidance. Core owns admission, the
//! pinned worker process, the persisted profile snapshot and every write. It
//! writes no activity, attempt, review or mastery and runs no model: the
//! resulting profile is a reviewable candidate, not a validated learner state.
use crate::{
    document::{self, Error},
    provider_material_grant::{self as grant, Snapshot},
    ui_state,
};
use archeaxis_store_sqlite::authorization_fence;
use rusqlite::{Connection, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

pub const DOCUMENT_NAMESPACE: &str = "archeaxis_deeptutor_teaching_feedback_candidate";
pub const DOCUMENT_SCHEMA: &str = "archeaxis.deeptutor-teaching-feedback-document/v1";
pub const RECEIPT_SCHEMA: &str = "archeaxis.deeptutor-teaching-feedback-persistence/v1";
pub const WORKER_SCHEMA: &str = "archeaxis.deeptutor-teaching-feedback/v1";
pub const GENERATION_ROUTE: &str = "deeptutor_teaching_feedback_donor_rules";
pub const WORKER_CAPABILITY: &str = "deeptutor.teaching.feedback";

const MAX_MESSAGE_BYTES: usize = 16_384;
const MAX_OBJECTIVES: usize = 128;
const MAX_OBJECTIVE_CHARS: usize = 200;
const MAX_OBJECTIVE_BYTES: usize = 800;
const MAX_UPDATES: usize = 6;
const MAX_WORKER_FRAME: usize = 128 * 1024;
const MAX_DOCUMENT_BYTES: usize = 512 * 1024;

/// One caller-declared teaching turn. `profile` names the candidate Document
/// whose stored profile is the base snapshot; omitting it starts from the
/// donor's default empty profile.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct TeachingFeedbackRequest {
    pub create_request_id: String,
    pub session_id: String,
    pub turn_id: String,
    #[serde(default)]
    pub profile: Option<Snapshot>,
    pub current_message: String,
    pub objective_ids: Vec<String>,
    pub focus_objective_id: String,
    pub updates: Vec<Value>,
    pub include_history: bool,
}

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn sha(value: &Value) -> String {
    digest(value.to_string().as_bytes())
}

fn token(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

fn bounded_text(value: &str, max_bytes: usize, nonblank: bool) -> bool {
    !value.contains('\0') && value.len() <= max_bytes && (!nonblank || !value.trim().is_empty())
}

fn objective(value: &str) -> bool {
    bounded_text(value, MAX_OBJECTIVE_BYTES, true)
        && value.trim() == value
        && value.chars().count() <= MAX_OBJECTIVE_CHARS
}

/// Name a structurally invalid request before Core starts a worker. `None`
/// means the request may proceed; the write path repeats the same checks.
pub fn request_refusal(request: &TeachingFeedbackRequest) -> Option<&'static str> {
    if !token(&request.create_request_id)
        || !token(&request.session_id)
        || !token(&request.turn_id)
        || !bounded_text(&request.current_message, MAX_MESSAGE_BYTES, true)
        || request
            .profile
            .as_ref()
            .is_some_and(|profile| !grant::valid_snapshot_shape(profile))
        || request.objective_ids.is_empty()
        || request.objective_ids.len() > MAX_OBJECTIVES
        || request.objective_ids.iter().any(|id| !objective(id))
        || !objective(&request.focus_objective_id)
        || !request
            .objective_ids
            .iter()
            .any(|id| id == &request.focus_objective_id)
        || request.updates.is_empty()
        || request.updates.len() > MAX_UPDATES
        || request.updates.iter().any(|update| !update.is_object())
    {
        return Some("invalid teaching feedback request");
    }
    let mut seen = std::collections::HashSet::new();
    if request.objective_ids.iter().any(|id| !seen.insert(id)) {
        return Some("duplicate teaching objective");
    }
    None
}

pub fn request_sha256(request: &TeachingFeedbackRequest) -> Result<String, Error> {
    let frame = json!({"create_request_id":request.create_request_id,
        "session_id":request.session_id,"turn_id":request.turn_id,
        "profile":request.profile,"current_message":request.current_message,
        "objective_ids":request.objective_ids,"focus_objective_id":request.focus_objective_id,
        "updates":request.updates,"include_history":request.include_history});
    Ok(sha(&frame))
}

fn internal_request_id(create_request_id: &str) -> String {
    format!(
        "deeptutor_teaching_feedback_{}",
        digest(create_request_id.as_bytes())
    )
}

/// The ordinary Core Document this request owns, derived only from its ID.
pub fn teaching_feedback_document_id(create_request_id: &str) -> String {
    format!(
        "doc_req_{}",
        digest(internal_request_id(create_request_id).as_bytes())
    )
}

fn worker_frame(value: &Value) -> Result<Vec<u8>, Error> {
    let mut bytes =
        serde_json::to_vec(value).map_err(|_| Error::Invalid("worker frame unavailable"))?;
    bytes.push(b'\n');
    if bytes.len() > MAX_WORKER_FRAME {
        return Err(Error::Invalid("worker frame exceeds limit"));
    }
    Ok(bytes)
}

/// The stored profile of a previously persisted feedback candidate. A different
/// version or hash is a conflict, never a silently substituted snapshot.
fn profile_snapshot(conn: &Connection, source: &Snapshot) -> Result<Value, Error> {
    let current = document::read_verified(conn, &source.document_id, Some(source.version))?;
    if current["content_sha256"] != json!(source.content_sha256) {
        return Err(Error::Conflict(source.version));
    }
    let saved = &current["editor_json"]["attrs"][DOCUMENT_NAMESPACE];
    if saved["schema"].as_str() != Some(DOCUMENT_SCHEMA) {
        return Err(Error::Invalid(
            "profile source is not a teaching feedback candidate",
        ));
    }
    let profile = saved["result_profile"].clone();
    if !profile.is_object() {
        return Err(Error::Invalid(
            "profile source carries no persisted profile",
        ));
    }
    Ok(profile)
}

/// A private preparation captured before any worker runs.
pub struct TeachingFeedbackPending {
    create_request_id: String,
    request_sha256: String,
    restore_epoch: Option<String>,
    workspace_id: String,
    input_profile: Value,
    profile_source: Option<Snapshot>,
    frame: Vec<u8>,
}

impl TeachingFeedbackPending {
    /// The exact bounded worker line. The caller owns the worker lifecycle.
    pub fn frame(&self) -> &[u8] {
        &self.frame
    }

    pub fn input_profile(&self) -> &Value {
        &self.input_profile
    }

    pub fn profile_source(&self) -> Option<&Snapshot> {
        self.profile_source.as_ref()
    }
}

pub enum TeachingFeedbackPreparation {
    /// A committed candidate is a history read, never a second execution.
    Existing(Value),
    Pending(TeachingFeedbackPending),
}

fn candidate_status(conn: &Connection, document: &Value) -> &'static str {
    match document["document_id"].as_str() {
        Some(id) => match document::read_verified(conn, id, None) {
            Ok(current)
                if current["version"] == document["version"]
                    && current["content_sha256"] == document["content_sha256"] =>
            {
                "current"
            }
            Ok(current) if current["version"].as_i64().is_some_and(|v| v > 1) => "historical",
            _ => "unavailable",
        },
        None => "unavailable",
    }
}

fn receipt(conn: &Connection, document: Value) -> Value {
    let saved = &document["editor_json"]["attrs"][DOCUMENT_NAMESPACE];
    json!({"schema":RECEIPT_SCHEMA,"document":document,
        "candidate_document_status":candidate_status(conn, &document),
        "generation_route":saved["generation_route"],"status":saved["update_status"],
        "changed_fields":saved["changed_fields"],"result_profile":saved["result_profile"],
        "guidance":saved["guidance"],"profile_source":saved["profile_source"],
        "response_origin":saved["response_origin"],
        "update_evidence_verification":saved["worker_document"]["update_evidence_verification"],
        "existing_profile_evidence_verification":saved["worker_document"]["existing_profile_evidence_verification"],
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,"independent_mastery":"not_established",
        "persistence":"CORE_DOCUMENT","model_call":"NOT_INVOKED"})
}

fn existing(
    conn: &Connection,
    create_request_id: &str,
    request_sha256: &str,
) -> Result<Option<Value>, Error> {
    let id = teaching_feedback_document_id(create_request_id);
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
        [&id],
        |row| row.get(0),
    )?;
    if !exists {
        return Ok(None);
    }
    let document = document::read_verified(conn, &id, Some(1))?;
    let saved = &document["editor_json"]["attrs"][DOCUMENT_NAMESPACE];
    if saved["schema"].as_str() != Some(DOCUMENT_SCHEMA)
        || saved["create_request_id"] != create_request_id
        || saved["generation_request_sha256"].as_str() != Some(request_sha256)
    {
        return Err(Error::Conflict(1));
    }
    Ok(Some(receipt(conn, document)))
}

/// Read the base profile and capture the restore identity inside one Core
/// transaction before the worker starts.
pub fn prepare_teaching_feedback(
    conn: &mut Connection,
    request: &TeachingFeedbackRequest,
) -> Result<TeachingFeedbackPreparation, Error> {
    if request_refusal(request).is_some() {
        return Err(Error::Invalid("invalid teaching feedback request"));
    }
    let request_sha256 = request_sha256(request)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    if let Some(value) = existing(&tx, &request.create_request_id, &request_sha256)? {
        tx.commit()?;
        return Ok(TeachingFeedbackPreparation::Existing(value));
    }
    let input_profile = match request.profile.as_ref() {
        Some(source) => profile_snapshot(&tx, source)?,
        None => json!({}),
    };
    let restore_epoch = authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = ui_state::workspace_id(&tx)
        .map_err(|_| Error::Invalid("teaching feedback workspace identity unavailable"))?;
    let frame = worker_frame(&json!({
        "schema":WORKER_SCHEMA,
        "request_id":request.create_request_id,
        "session_id":request.session_id,
        "turn_id":request.turn_id,
        "profile":input_profile,
        "current_message":request.current_message,
        "objective_ids":request.objective_ids,
        "focus_objective_id":request.focus_objective_id,
        "updates":request.updates,
        "include_history":request.include_history,
    }))?;
    tx.commit()?;
    Ok(TeachingFeedbackPreparation::Pending(
        TeachingFeedbackPending {
            create_request_id: request.create_request_id.clone(),
            request_sha256,
            restore_epoch,
            workspace_id,
            input_profile,
            profile_source: request.profile.clone(),
            frame,
        },
    ))
}

/// The donor worker document, unmodified. Core checks its shape and status and
/// never rewrites the profile or the guidance it returned.
#[derive(Clone)]
pub struct TeachingFeedbackGeneration {
    pub worker_document: Value,
}

fn worker_outcome(value: &Value, create_request_id: &str) -> Result<&'static str, Error> {
    if value["schema"] != WORKER_SCHEMA || value["request_id"].as_str() != Some(create_request_id) {
        return Err(Error::Invalid("teaching feedback worker identity mismatch"));
    }
    let status = match value["status"].as_str() {
        Some("UPDATED") => "UPDATED",
        Some("UNCHANGED") => "UNCHANGED",
        _ => {
            return Err(Error::Invalid(
                "teaching feedback worker is not a candidate",
            ));
        }
    };
    if !value["profile"].is_object() || !value["guidance"].is_object() {
        return Err(Error::Invalid(
            "teaching feedback worker returned no profile or guidance",
        ));
    }
    if !value["changed_fields"].is_array() {
        return Err(Error::Invalid(
            "teaching feedback worker returned no changed fields",
        ));
    }
    Ok(status)
}

fn guidance_nodes(focus: &str, guidance: &Value) -> Vec<Value> {
    let mut nodes = Vec::new();
    for (label, key) in [
        ("Teaching preferences", "teaching_preferences"),
        ("Teaching observations", "teaching_observations"),
    ] {
        let Some(entries) = guidance[key].as_object() else {
            continue;
        };
        if entries.is_empty() {
            continue;
        }
        nodes.push(json!({"type":"paragraph",
            "content":[{"type":"text","text":label}]}));
        for (name, item) in entries.iter() {
            let text = item["text"].as_str().unwrap_or_default();
            nodes.push(json!({"type":"paragraph",
                "content":[{"type":"text","text":format!("{name} · {text}")}]}));
        }
    }
    if nodes.is_empty() {
        nodes.push(json!({"type":"paragraph","content":[{"type":"text",
            "text":format!("No teaching preference or observation applies to {focus}.")}]}));
    }
    nodes
}

/// Persist one inert candidate. The request, the base snapshot and the worker
/// document are re-checked, and the restore identity must still match.
pub fn commit_teaching_feedback(
    conn: &mut Connection,
    request: &TeachingFeedbackRequest,
    pending: &TeachingFeedbackPending,
    generation: &TeachingFeedbackGeneration,
) -> Result<Value, Error> {
    if request_refusal(request).is_some()
        || request.create_request_id != pending.create_request_id
        || request_sha256(request)? != pending.request_sha256
    {
        return Err(Error::Invalid(
            "teaching feedback request changed after admission",
        ));
    }
    let update_status = worker_outcome(&generation.worker_document, &request.create_request_id)?;
    let frame = String::from_utf8(pending.frame.clone())
        .map_err(|_| Error::Invalid("teaching feedback frame is not text"))?;

    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let epoch = authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = ui_state::existing_workspace_id(&tx)
        .map_err(|_| Error::Invalid("teaching feedback workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(Error::Invalid(
            "teaching feedback workspace or restore epoch changed",
        ));
    }
    if let Some(existing) = existing(&tx, &request.create_request_id, &pending.request_sha256)? {
        tx.commit()?;
        return Ok(existing);
    }
    let saved = json!({
        "schema":DOCUMENT_SCHEMA,
        "create_request_id":request.create_request_id,
        "generation_request_sha256":pending.request_sha256,
        "generation_route":GENERATION_ROUTE,
        "session_id":request.session_id,
        "turn_id":request.turn_id,
        "objective_ids":request.objective_ids,
        "focus_objective_id":request.focus_objective_id,
        "include_history":request.include_history,
        "profile_source":pending.profile_source,
        "input_profile":pending.input_profile,
        "result_profile":generation.worker_document["profile"],
        "guidance":generation.worker_document["guidance"],
        "changed_fields":generation.worker_document["changed_fields"],
        "update_status":update_status,
        "worker_document":generation.worker_document,
        "request_frame":frame,
        "response_origin":"DONOR_RULES_UNVERIFIED",
        "model_call":"NOT_INVOKED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "independent_mastery":"not_established",
    });
    let editor = json!({"type":"doc","attrs":{(DOCUMENT_NAMESPACE):saved},
        "content":guidance_nodes(&request.focus_objective_id, &generation.worker_document["guidance"])});
    let bytes = serde_json::to_vec(&editor).map_err(|_| Error::Invalid("document unavailable"))?;
    if bytes.len() > MAX_DOCUMENT_BYTES {
        return Err(Error::Invalid("teaching feedback document exceeds limit"));
    }
    let title = format!(
        "DeepTutor teaching feedback · {}",
        request
            .focus_objective_id
            .chars()
            .take(120)
            .collect::<String>()
    );
    let internal = internal_request_id(&request.create_request_id);
    let document = document::create_optional_tx(&tx, None, None, &title, editor, Some(&internal))?;
    let id = document["document_id"].as_str().ok_or(Error::Invalid(
        "created teaching feedback identity unavailable",
    ))?;
    let verified = document::read_verified(&tx, id, Some(1))?;
    if verified["content_sha256"] != document["content_sha256"]
        || verified["editor_json"]["attrs"][DOCUMENT_NAMESPACE]["create_request_id"]
            != json!(request.create_request_id)
    {
        return Err(Error::Invalid(
            "created teaching feedback identity mismatch",
        ));
    }
    let result = receipt(&tx, verified);
    tx.commit()?;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base() -> TeachingFeedbackRequest {
        TeachingFeedbackRequest {
            create_request_id: "client_1".into(),
            session_id: "session_1".into(),
            turn_id: "turn_1".into(),
            profile: None,
            current_message: "I prefer short examples".into(),
            objective_ids: vec!["objective_1".into()],
            focus_objective_id: "objective_1".into(),
            updates: vec![json!({"kind":"preference","op":"upsert","key":"examples",
                "text":"Use short examples","basis":"learner_report",
                "evidence":"short examples"})],
            include_history: false,
        }
    }

    #[test]
    fn request_bounds_are_refused_before_any_work() {
        assert_eq!(request_refusal(&base()), None);
        let mut extra = base();
        extra.focus_objective_id = "objective_2".into();
        assert!(request_refusal(&extra).is_some());
        let mut blank = base();
        blank.current_message = "   ".into();
        assert!(request_refusal(&blank).is_some());
        let mut many = base();
        many.updates = vec![json!({}); 7];
        assert!(request_refusal(&many).is_some());
        let mut dup = base();
        dup.objective_ids = vec!["objective_1".into(), "objective_1".into()];
        assert!(request_refusal(&dup).is_some());
    }

    #[test]
    fn document_identity_is_deterministic_and_request_specific() {
        assert_eq!(
            teaching_feedback_document_id("client_1"),
            teaching_feedback_document_id("client_1")
        );
        assert_ne!(
            teaching_feedback_document_id("client_1"),
            teaching_feedback_document_id("client_2")
        );
        assert!(teaching_feedback_document_id("client_1").starts_with("doc_req_"));
    }

    #[test]
    fn worker_shape_is_refused_unless_it_is_a_named_candidate() {
        let good = json!({"schema":WORKER_SCHEMA,"request_id":"client_1","status":"UPDATED",
            "profile":{},"guidance":{},"changed_fields":[]});
        assert!(matches!(worker_outcome(&good, "client_1"), Ok("UPDATED")));
        let mut wrong = good.clone();
        wrong["status"] = json!("INVALID_REQUEST");
        assert!(worker_outcome(&wrong, "client_1").is_err());
        let mut other = good;
        other["request_id"] = json!("client_2");
        assert!(worker_outcome(&other, "client_1").is_err());
    }
}
