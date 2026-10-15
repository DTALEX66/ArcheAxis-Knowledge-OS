//! Core-owned recoverable UI working state, separate from committed Document versions.
//! Existing workspace_meta participates in both archive and Online Backup; no new schema/DB.
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};

const ID_KEY: &str = "ui_workspace_identity_v1";
const STATE_KEY: &str = "ui_working_state_v1";
const ABANDONED_KEY: &str = "ui_job_abandonments_v1";
const MAX_BYTES: usize = 1_048_576;
const BASIS: &str = "archeaxis.ui-working-state/v1";

#[derive(Debug)]
pub enum Error {
    Invalid(&'static str),
    Conflict,
    Store(rusqlite::Error),
}
impl From<rusqlite::Error> for Error {
    fn from(e: rusqlite::Error) -> Self {
        Self::Store(e)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Draft {
    pub base_version: i64,
    pub editor_json: Value,
}
/// Editable human input, distinct from immutable pending_reviews execution intent.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct LearningDraft {
    pub item_key: String,
    pub assessment_id: String,
    pub knowledge_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub question_version: Option<String>,
    pub answer: String,
    #[serde(deserialize_with = "Option::deserialize")]
    pub checked_correct: Option<bool>,
    #[serde(deserialize_with = "Option::deserialize")]
    pub rating: Option<u8>,
    pub answer_revealed: bool,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct TeachingForm {
    pub kind: crate::teaching::RecordKind,
    pub purpose: String,
    pub content: String,
    pub scope: crate::teaching::RecordScope,
    pub privacy: crate::teaching::RecordPrivacy,
    pub assisted: bool,
    pub feedback_class: Option<crate::teaching::FeedbackClass>,
    pub rubric_version: String,
    pub producer_kind: crate::teaching::ProducerKind,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct TeachingPreparation {
    pub document_id: String,
    pub version: i64,
    pub title: String,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationEditor {
    #[serde(rename = "type")]
    pub kind: String,
    pub content: Vec<PreparationParagraph>,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationParagraph {
    #[serde(rename = "type")]
    pub kind: String,
    pub attrs: PreparationAttrs,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub content: Option<Vec<PreparationText>>,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationAttrs {
    pub block_id: String,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationText {
    #[serde(rename = "type")]
    pub kind: String,
    pub text: String,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationCreateBody {
    pub create_request_id: String,
    pub title: String,
    pub editor_json: PreparationEditor,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationCreatePayload {
    pub body: PreparationCreateBody,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationDraftBody {
    pub expected_version: i64,
    pub editor_json: PreparationEditor,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PreparationDraftPayload {
    pub document_id: String,
    pub body: PreparationDraftBody,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(tag = "operation", rename_all = "snake_case", deny_unknown_fields)]
pub enum PreparationAttempt {
    DocumentCreate {
        payload: PreparationCreatePayload,
        snapshot: String,
        #[serde(rename = "persistedPurpose")]
        persisted_purpose: String,
        #[serde(rename = "expectedTitle")]
        expected_title: String,
    },
    DocumentDraft {
        payload: PreparationDraftPayload,
        snapshot: String,
        #[serde(rename = "persistedPurpose")]
        persisted_purpose: String,
        #[serde(rename = "expectedTitle")]
        expected_title: String,
    },
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PreparationSnapshot {
    purpose: String,
    content: String,
}
/// Inert form input. Only teaching::put / document writes may publish domain objects.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct TeachingDraft {
    pub page_id: String,
    pub context_item_key: Option<String>,
    pub form: TeachingForm,
    pub knowledge_id: Option<String>,
    pub course_id: Option<String>,
    pub item_key: Option<String>,
    pub assessment_id: Option<String>,
    pub parent: Option<crate::teaching::RecordView>,
    pub preparation: Option<TeachingPreparation>,
    pub saved_preparation: String,
    pub pending_record: Option<crate::teaching::TeachingRecord>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub preparation_attempt: Option<PreparationAttempt>,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct OriginalAttempt {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_revision: Option<String>,
    pub create_request_id: String,
    pub title: String,
    pub editor_json: Value,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct JobBudget {
    pub deadline_ms: u64,
    pub split: bool,
    pub words: bool,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PendingJob {
    pub source_id: String,
    pub source_revision: String,
    pub job_id: String,
    pub request_id: String,
    pub kind: String,
    pub body: JobBudget,
    pub surface: String,
    pub mode: String,
    pub origin_restore_epoch: String,
    pub relative: Option<String>,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PendingReview {
    pub item_key: String,
    pub client_event_id: String,
    pub body: Value,
    pub origin_restore_epoch: String,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PendingMachine {
    pub journal_id: String,
    pub owner_knowledge_id: String,
    pub operation: String,
    pub body: Value,
    pub origin_restore_epoch: String,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClearJob {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub request_id: String,
    pub action: String,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClearMachine {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub journal_id: String,
    pub task_id: String,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MachineStatus {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub journal_id: String,
}
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct State {
    pub drafts: BTreeMap<String, Draft>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub learning_drafts: BTreeMap<String, LearningDraft>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub teaching_drafts: BTreeMap<String, TeachingDraft>,
    pub opened_documents: Vec<String>,
    pub active_document: Option<String>,
    pub page_id: Option<String>,
    #[serde(default)]
    pub pending_original: Option<OriginalAttempt>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub pending_jobs: BTreeMap<String, PendingJob>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub pending_reviews: BTreeMap<String, PendingReview>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub pending_machine: BTreeMap<String, PendingMachine>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Write {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub state: State,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub release_teaching: Option<ReleaseTeaching>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReleaseTeaching {
    pub draft_key: String,
    pub record_id: String,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClearSaved {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub document_id: String,
    pub base_version: i64,
    pub content_sha256: String,
    pub saved_version: i64,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Stored {
    schema: String,
    workspace_id: String,
    restore_epoch: String,
    state_revision: i64,
    state: State,
}
fn identity(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 128
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
}
fn hex32(s: &str) -> bool {
    s.len() == 32
        && s.bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}
fn meta(conn: &Connection, key: &str) -> Result<Option<String>, Error> {
    Ok(conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [key],
            |r| r.get(0),
        )
        .optional()?)
}
pub fn existing_workspace_id(conn: &Connection) -> Result<Option<String>, Error> {
    let id = meta(conn, ID_KEY)?;
    if id.as_ref().is_some_and(|id| !hex32(id)) {
        return Err(Error::Invalid("corrupt UI workspace identity"));
    }
    Ok(id)
}
pub fn workspace_id(conn: &Connection) -> Result<String, Error> {
    if let Some(id) = existing_workspace_id(conn)? {
        return Ok(id);
    }
    conn.execute(
        "INSERT INTO workspace_meta(key,value) VALUES(?1,lower(hex(randomblob(16))))",
        [ID_KEY],
    )?;
    meta(conn, ID_KEY)?.ok_or(Error::Invalid("workspace identity missing"))
}
pub(crate) fn epoch(conn: &Connection) -> Result<String, Error> {
    match meta(conn, archeaxis_store_sqlite::authorization_fence::KEY)? {
        None => Ok("initial".into()),
        Some(raw) => {
            let value: Value =
                serde_json::from_str(&raw).map_err(|_| Error::Invalid("corrupt restore fence"))?;
            let epoch = value["epoch"]
                .as_str()
                .ok_or(Error::Invalid("restore epoch missing"))?;
            if value["schema"] != archeaxis_store_sqlite::authorization_fence::SCHEMA
                || !hex32(epoch)
                || !value["blocked_grant_ids"].as_array().is_some_and(|items| {
                    items
                        .iter()
                        .all(|item| item.as_str().is_some_and(|s| !s.is_empty()))
                })
            {
                return Err(Error::Invalid("corrupt restore fence"));
            }
            Ok(epoch.into())
        }
    }
}
fn digest(content: &Value) -> String {
    hex::encode(Sha256::digest(
        serde_json::to_vec(content).expect("JSON Value serialization"),
    ))
}
/// Hash only finite transport inputs. Context execution digests remain separate.
pub fn machine_request_fingerprint(operation: &str, body: &Value) -> String {
    let mut request = serde_json::json!({"knowledge_id":body["knowledge_id"],"question":body["question"],
        "max_tokens":body["max_tokens"].as_u64().unwrap_or(2048),"timeout_s":body["timeout_s"].as_u64().unwrap_or(120),
        "context_grant":body["context_grant"],"asset_context_grant":body["asset_context_grant"],
        "client_request_id":if operation=="answer" {body["client_request_id"].clone()} else {Value::Null},
        "retest_of":if operation=="retest" {body["retest_of"].clone()} else {Value::Null}});
    if let Some(model) = body.get("model") {
        request["model"] = model.clone();
    }
    if let Some(config) = body.get("model_configuration") {
        request["model_configuration"] = config.clone();
    }
    digest(&serde_json::json!({"operation":operation,"request":request}))
}
fn machine_owner(conn: &Connection, pending: &PendingMachine) -> Result<(), Error> {
    if pending.operation == "answer" {
        return Ok(());
    }
    let raw:Option<String>=conn.query_row("SELECT conditions FROM machine_tasks WHERE task_id=?1 AND scope='runtime.evaluation.failed'",
        [pending.body["retest_of"].as_str().ok_or(Error::Invalid("retest journey identity missing"))?],|r|r.get(0)).optional()?;
    let prior: Value = serde_json::from_str(&raw.ok_or(Error::Invalid("retest journey missing"))?)
        .map_err(|_| Error::Invalid("retest journey unreadable"))?;
    if prior["knowledge_id"] != pending.owner_knowledge_id
        || prior["question"] != pending.body["question"]
    {
        return Err(Error::Invalid(
            "retest journal owner or question differs from failed journey",
        ));
    }
    Ok(())
}
fn machine_snapshot_shape(document_id: &str, version: i64, hash: &str, max_id: usize) -> bool {
    !document_id.trim().is_empty()
        && document_id.len() <= max_id
        && (1..=9_007_199_254_740_991).contains(&version)
        && hash.len() == 64
        && hash
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}
fn machine_grant_shapes(body: &Value, operation: &str) -> bool {
    if let Some(value) = body.get("context_grant") {
        let Ok(grant) = serde_json::from_value::<crate::context_grant::Consumption>(value.clone())
        else {
            return false;
        };
        if !machine_snapshot_shape(
            &grant.document_id,
            grant.version,
            &grant.content_sha256,
            256,
        ) || grant.purpose.trim().is_empty()
            || grant.purpose.len() > 1024
        {
            return false;
        }
    }
    if let Some(value) = body.get("asset_context_grant") {
        if body.get("context_grant").is_none() {
            return false;
        }
        let Ok(grant) =
            serde_json::from_value::<crate::asset_context_grant::PacketRequest>(value.clone())
        else {
            return false;
        };
        if grant.request_id.is_empty()
            || grant.request_id.len() > 128
            || !grant.request_id.bytes().all(|b| (33..=126).contains(&b))
            || grant.purpose.trim().is_empty()
            || grant.purpose.len() > 1024
            || grant.consumer != crate::asset_context_grant::Consumer::LocalMachine
            || !matches!(
                (operation, &grant.operation),
                ("answer", crate::asset_context_grant::Operation::Answer)
                    | ("retest", crate::asset_context_grant::Operation::Retest)
            )
            || !machine_snapshot_shape(
                &grant.grant.document_id,
                grant.grant.version,
                &grant.grant.content_sha256,
                128,
            )
            || !machine_snapshot_shape(
                &grant.asset.document_id,
                grant.asset.version,
                &grant.asset.content_sha256,
                128,
            )
        {
            return false;
        }
    }
    true
}
fn preparation_basis(
    attempt: &PreparationAttempt,
) -> Result<(String, i64, &str, &PreparationEditor, &str, &str), Error> {
    let (id, version, title, editor, snapshot, purpose) = match attempt {
        PreparationAttempt::DocumentCreate {
            payload,
            snapshot,
            persisted_purpose,
            expected_title,
        } => {
            if !identity(&payload.body.create_request_id) || payload.body.title != *expected_title {
                return Err(Error::Invalid("invalid preparation create identity"));
            }
            (
                format!(
                    "doc_req_{}",
                    hex::encode(Sha256::digest(payload.body.create_request_id.as_bytes()))
                ),
                1,
                expected_title.as_str(),
                &payload.body.editor_json,
                snapshot.as_str(),
                persisted_purpose.as_str(),
            )
        }
        PreparationAttempt::DocumentDraft {
            payload,
            snapshot,
            persisted_purpose,
            expected_title,
        } => {
            if !identity(&payload.document_id) || payload.body.expected_version < 1 {
                return Err(Error::Invalid("invalid preparation draft identity"));
            }
            (
                payload.document_id.clone(),
                payload
                    .body
                    .expected_version
                    .checked_add(1)
                    .ok_or(Error::Invalid("preparation version exhausted"))?,
                expected_title.as_str(),
                &payload.body.editor_json,
                snapshot.as_str(),
                persisted_purpose.as_str(),
            )
        }
    };
    if title.len() > 512
        || purpose.len() > 512
        || snapshot.len() > 400_000
        || editor.kind != "doc"
        || editor.content.is_empty()
        || editor.content.len() > 65_537
    {
        return Err(Error::Invalid("invalid frozen preparation shape"));
    }
    let plain: PreparationSnapshot = serde_json::from_str(snapshot)
        .map_err(|_| Error::Invalid("invalid preparation snapshot"))?;
    if matches!(attempt, PreparationAttempt::DocumentCreate { .. })
        && (purpose != plain.purpose
            || title
                != if plain.purpose.trim().is_empty() {
                    "教学准备草稿"
                } else {
                    plain.purpose.trim()
                })
    {
        return Err(Error::Invalid("preparation create title snapshot mismatch"));
    }
    let mut ids = HashSet::new();
    let mut lines = Vec::new();
    for paragraph in &editor.content {
        if paragraph.kind != "paragraph"
            || !identity(&paragraph.attrs.block_id)
            || !ids.insert(&paragraph.attrs.block_id)
            || paragraph.content.as_ref().is_some_and(|c| c.len() > 1)
        {
            return Err(Error::Invalid("invalid preparation paragraph"));
        }
        let child = paragraph.content.as_ref().and_then(|c| c.first());
        if child.is_some_and(|c| c.kind != "text" || c.text.is_empty() || c.text.contains('\n')) {
            return Err(Error::Invalid("invalid preparation inline text"));
        }
        lines.push(child.map(|c| c.text.as_str()).unwrap_or(""));
    }
    if plain.purpose.len() > 512
        || plain.content.len() > 65_536
        || lines.join("\n") != plain.content
    {
        return Err(Error::Invalid(
            "preparation snapshot does not match frozen editor",
        ));
    }
    Ok((id, version, title, editor, snapshot, purpose))
}
fn check_preparation_saved(conn: &Connection, attempt: &PreparationAttempt) -> Result<(), Error> {
    let (id, version, title, editor, _, _) = preparation_basis(attempt)?;
    let saved = crate::document::read(conn, &id, None)
        .map_err(|_| Error::Invalid("preparation saved document unavailable; intent retained"))?;
    let editor =
        serde_json::to_value(editor).map_err(|_| Error::Invalid("invalid preparation editor"))?;
    let nodes = editor["content"]
        .as_array()
        .ok_or(Error::Invalid("invalid preparation editor"))?;
    let lines = nodes
        .iter()
        .map(|node| node["content"][0]["text"].as_str().unwrap_or(""))
        .collect::<Vec<_>>();
    let blocks = saved["blocks"]
        .as_array()
        .ok_or(Error::Invalid("preparation blocks unavailable"))?;
    if saved["document_id"] != id
        || saved["version"] != version
        || saved["title"] != title
        || !saved["source_id"].is_null()
        || !saved["source_revision"].is_null()
        || !saved["revision_basis"].is_null()
        || saved["editor_json"] != editor
        || saved["content_sha256"] != digest(&editor)
        || saved["text_projection"]
            != lines
                .iter()
                .filter(|line| !line.is_empty())
                .copied()
                .collect::<Vec<_>>()
                .join("\n")
        || blocks.len() != nodes.len()
        || blocks.iter().enumerate().any(|(i, block)| {
            block["block_id"] != nodes[i]["attrs"]["block_id"]
                || block["ordinal"] != i
                || block["kind"] != "paragraph"
                || block["codec_status"] != "known"
                || block["node_json"] != nodes[i]
                || block["text_projection"] != lines[i]
        })
    {
        return Err(Error::Invalid(
            "preparation exact saved snapshot not confirmed; intent retained",
        ));
    }
    Ok(())
}
fn validate(state: &State) -> Result<(), Error> {
    if state.teaching_drafts.len() > 32 {
        return Err(Error::Invalid("teaching draft limit exceeded"));
    }
    for (key, draft) in &state.teaching_drafts {
        if let Some(attempt) = &draft.preparation_attempt {
            preparation_basis(attempt)?;
            if draft.pending_record.is_some() {
                return Err(Error::Invalid(
                    "preparation and teaching requests must be reconciled separately",
                ));
            }
        }
        use crate::teaching::RecordKind::*;
        let page = match draft.form.kind {
            Observation | Requirement => "08",
            Proposal => "09",
            Delivery => "10",
            TeachBack => "11",
            Feedback | Revision => "12",
        };
        if draft.page_id != page
            || key
                != &format!(
                    "{}:{}",
                    draft.page_id,
                    draft.context_item_key.as_deref().unwrap_or("")
                )
            || draft
                .context_item_key
                .as_ref()
                .is_some_and(|s| s.trim().is_empty() || s.len() > 512)
            || draft
                .item_key
                .as_ref()
                .is_some_and(|s| s.trim().is_empty() || s.len() > 512)
            || [&draft.knowledge_id, &draft.course_id, &draft.assessment_id]
                .iter()
                .any(|s| s.as_ref().is_some_and(|v| !identity(v)))
            || draft.form.purpose.len() > 512
            || draft.form.content.len() > 65_536
            || draft.form.rubric_version.len() > 128
            || draft.saved_preparation.len() > 400_000
            || draft
                .preparation
                .as_ref()
                .is_some_and(|p| !identity(&p.document_id) || p.version < 1 || p.title.len() > 512)
        {
            return Err(Error::Invalid("invalid teaching draft"));
        }
        if let Some(record) = &draft.pending_record {
            if record.schema != crate::teaching::RECORD_SCHEMA
                || !identity(&record.record_id)
                || record.kind != draft.form.kind
                || record.purpose != draft.form.purpose.trim()
                || record.content != draft.form.content
                || record.knowledge_id != draft.knowledge_id.as_deref().unwrap_or("")
                || record.knowledge_version != record.knowledge_id
                || record.course_id != draft.course_id
                || record.parent_id.as_deref()
                    != draft.parent.as_ref().map(|p| p.record.record_id.as_str())
                || record.scope != draft.form.scope
                || record.privacy != draft.form.privacy
                || record.assisted != draft.form.assisted
                || record.producer_kind != draft.form.producer_kind
                || record.feedback_class
                    != if record.kind == Feedback {
                        draft.form.feedback_class.clone()
                    } else {
                        None
                    }
                || record.assessment_id
                    != if record.kind == TeachBack {
                        draft.assessment_id.clone()
                    } else {
                        None
                    }
                || record.rubric_version.as_deref()
                    != if draft.form.rubric_version.trim().is_empty() {
                        None
                    } else {
                        Some(draft.form.rubric_version.trim())
                    }
            {
                return Err(Error::Invalid("teaching draft frozen record mismatch"));
            }
        }
    }
    if state.pending_machine.len() > 32 {
        return Err(Error::Invalid("pending machine limit exceeded"));
    }
    for (key, pending) in &state.pending_machine {
        let allowed = [
            "knowledge_id",
            "question",
            "max_tokens",
            "timeout_s",
            "model",
            "model_configuration",
            "context_grant",
            "asset_context_grant",
            "client_request_id",
            "retest_of",
        ];
        let body = &pending.body;
        if key != &pending.journal_id
            || !identity(key)
            || pending.owner_knowledge_id.trim().is_empty()
            || pending.owner_knowledge_id.len() > 256
            || !["answer", "retest"].contains(&pending.operation.as_str())
            || !(pending.origin_restore_epoch == "initial" || hex32(&pending.origin_restore_epoch))
            || !body
                .as_object()
                .is_some_and(|b| b.keys().all(|k| allowed.contains(&k.as_str())))
            || !body["knowledge_id"]
                .as_str()
                .is_some_and(|s| !s.trim().is_empty() && s.len() <= 256)
            || !body["question"]
                .as_str()
                .is_some_and(|s| !s.trim().is_empty() && s.len() <= 8192 && !s.contains('\0'))
            || !body["max_tokens"]
                .as_u64()
                .is_some_and(|n| (128..=4096).contains(&n))
            || !body["timeout_s"]
                .as_u64()
                .is_some_and(|n| (1..=120).contains(&n))
            || body.get("model").is_some_and(|v| {
                !v.as_str().is_some_and(|s| {
                    !s.is_empty()
                        && s.trim() == s
                        && s.len() <= 256
                        && !s.chars().any(char::is_control)
                })
            })
            || body.get("model_configuration").is_some_and(|v| {
                serde_json::from_value::<crate::model_configuration::Resolved>(v.clone()).is_err()
            })
            || !machine_grant_shapes(body, &pending.operation)
            || (pending.operation == "answer"
                && (body["knowledge_id"] != pending.owner_knowledge_id
                    || body.get("retest_of").is_some()
                    || !body["client_request_id"].as_str().is_some_and(identity)))
            || (pending.operation == "retest"
                && (body.get("client_request_id").is_some()
                    || !body["retest_of"].as_str().is_some_and(identity)))
        {
            return Err(Error::Invalid("invalid frozen machine journal"));
        }
    }
    if state.learning_drafts.len() > 32 {
        return Err(Error::Invalid("learning draft limit exceeded"));
    }
    for (key, draft) in &state.learning_drafts {
        if key != &draft.assessment_id
            || !identity(key)
            || draft.item_key.trim().is_empty()
            || draft.item_key.len() > 512
            || draft.knowledge_version.trim().is_empty()
            || draft.knowledge_version.len() > 512
            || draft
                .question_version
                .as_ref()
                .is_some_and(|v| v.trim().is_empty() || v.len() > 512)
            || draft.answer.len() > 65_536
            || draft.rating.is_some_and(|n| !(1..=4).contains(&n))
        {
            return Err(Error::Invalid("invalid learning draft"));
        }
    }
    if state.pending_reviews.len() > 32 {
        return Err(Error::Invalid("pending review limit exceeded"));
    }
    let mut review_items = HashSet::new();
    for (key, review) in &state.pending_reviews {
        let allowed = [
            "item_key",
            "client_event_id",
            "correct",
            "rating",
            "answer",
            "assessment_id",
            "question_version",
            "knowledge_version",
        ];
        if key != &review.client_event_id
            || !identity(key)
            || review.item_key.trim().is_empty()
            || review.item_key.len() > 512
            || !review_items.insert(&review.item_key)
            || review.body["item_key"].as_str() != Some(review.item_key.as_str())
            || review.body["client_event_id"].as_str() != Some(key.as_str())
            || !review
                .body
                .as_object()
                .is_some_and(|body| body.keys().all(|k| allowed.contains(&k.as_str())))
            || !review.body["answer"]
                .as_str()
                .is_some_and(|s| !s.trim().is_empty() && s.len() <= 65536)
            || !review.body["assessment_id"]
                .as_str()
                .is_some_and(|s| !s.is_empty())
            || !review.body["knowledge_version"]
                .as_str()
                .is_some_and(|s| !s.is_empty())
            || !review.body["rating"]
                .as_u64()
                .is_some_and(|n| (1..=4).contains(&n))
            || review
                .body
                .get("question_version")
                .is_some_and(|v| !v.as_str().is_some_and(|s| !s.is_empty()))
            || !review.body["correct"]
                .as_bool()
                .is_some_and(|correct| (review.body["rating"] == 1) == !correct)
            || !(review.origin_restore_epoch == "initial" || hex32(&review.origin_restore_epoch))
        {
            return Err(Error::Invalid("invalid frozen review journal"));
        }
    }
    if state.pending_jobs.len() > 64 {
        return Err(Error::Invalid("pending job limit exceeded"));
    }
    let mut job_ids = HashSet::new();
    for (key, job) in &state.pending_jobs {
        if !job_ids.insert(&job.job_id) {
            return Err(Error::Invalid(
                "another frozen request already owns this job",
            ));
        }
        if key != &job.request_id
            || !identity(key)
            || !identity(&job.source_id)
            || !identity(&job.job_id)
            || job.source_revision.len() != 64
            || !job
                .source_revision
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
            || !identity(&job.kind)
            || !(1..=300000).contains(&job.body.deadline_ms)
            || !matches!(job.surface.as_str(), "manual" | "folder" | "bounded")
            || !matches!(job.mode.as_str(), "single" | "split")
            || (job.mode == "split") != job.body.split
            || !(job.origin_restore_epoch == "initial" || hex32(&job.origin_restore_epoch))
            || job.relative.as_ref().is_some_and(|s| {
                s.len() > 1024
                    || s.contains('\\')
                    || s.starts_with('/')
                    || s.split('/').any(|p| p == ".." || p.contains(':'))
            })
        {
            return Err(Error::Invalid("invalid frozen job journal"));
        }
    }
    if let Some(attempt) = &state.pending_original {
        if !matches!((&attempt.source_id, &attempt.source_revision), (None, None))
            && !matches!((&attempt.source_id, &attempt.source_revision), (Some(id), Some(revision)) if identity(id) && revision.len() == 64 && revision.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)))
        {
            return Err(Error::Invalid("invalid frozen creation source binding"));
        }
        if !identity(&attempt.create_request_id)
            || attempt.title.len() > 1024
            || attempt.editor_json["type"] != "doc"
            || !attempt.editor_json["content"].is_array()
            || serde_json::to_vec(&attempt.editor_json)
                .map_err(|_| Error::Invalid("invalid original JSON"))?
                .len()
                > 262_144
        {
            return Err(Error::Invalid("invalid pending original request"));
        }
    }
    if state.drafts.len() > 32 || state.opened_documents.len() > 64 {
        return Err(Error::Invalid("UI object limit exceeded"));
    }
    let mut opened = HashSet::new();
    for id in &state.opened_documents {
        if !identity(id) || !opened.insert(id.as_str()) {
            return Err(Error::Invalid("invalid/duplicate opened document"));
        }
    }
    if let Some(id) = &state.active_document {
        if !identity(id) || !opened.contains(id.as_str()) {
            return Err(Error::Invalid("active document must be opened"));
        }
    }
    if let Some(page) = &state.page_id {
        if !matches!(
            page.as_str(),
            "01" | "02"
                | "03"
                | "04"
                | "05"
                | "06"
                | "07"
                | "08"
                | "09"
                | "10"
                | "11"
                | "12"
                | "13"
                | "14"
                | "15"
                | "16"
                | "17"
                | "18"
                | "19"
                | "20"
                | "21"
                | "22"
        ) {
            return Err(Error::Invalid("unknown UI page"));
        }
    }
    for (id, draft) in &state.drafts {
        if !identity(id)
            || draft.base_version <= 0
            || draft.editor_json["type"] != "doc"
            || !draft.editor_json["content"].is_array()
        {
            return Err(Error::Invalid("invalid draft"));
        }
        if serde_json::to_vec(&draft.editor_json)
            .map_err(|_| Error::Invalid("invalid JSON"))?
            .len()
            > 262_144
        {
            return Err(Error::Invalid("draft too large"));
        }
    }
    if serde_json::to_vec(state)
        .map_err(|_| Error::Invalid("invalid state JSON"))?
        .len()
        > MAX_BYTES
    {
        return Err(Error::Invalid("state too large"));
    }
    Ok(())
}
fn stored(conn: &Connection, id: &str, restore_epoch: &str) -> Result<Stored, Error> {
    match meta(conn, STATE_KEY)? {
        None => Ok(Stored {
            schema: BASIS.into(),
            workspace_id: id.into(),
            restore_epoch: restore_epoch.into(),
            state_revision: 0,
            state: State::default(),
        }),
        Some(raw) => {
            if raw.len() > MAX_BYTES + 1024 {
                return Err(Error::Invalid("stored UI state too large"));
            }
            let result: Stored =
                serde_json::from_str(&raw).map_err(|_| Error::Invalid("corrupt UI state"))?;
            if result.schema != BASIS
                || result.workspace_id != id
                || result.state_revision < 0
                || result.state_revision > 9_007_199_254_740_991
                || !(result.restore_epoch == "initial" || hex32(&result.restore_epoch))
            {
                return Err(Error::Invalid("corrupt UI state identity"));
            }
            validate(&result.state)?;
            Ok(result)
        }
    }
}
fn response(record: &Stored, current_epoch: &str) -> Value {
    let candidates = record.restore_epoch != current_epoch;
    let state = if candidates {
        State::default()
    } else {
        record.state.clone()
    };
    json!({"schema": BASIS, "workspace_id": record.workspace_id, "restore_epoch": current_epoch,
        "state_revision": record.state_revision, "state": state,
        "pending_document_id": if candidates { None } else { record.state.pending_original.as_ref().map(|a|format!("doc_req_{}",hex::encode(Sha256::digest(a.create_request_id.as_bytes())))) },
        "draft_digests": if candidates { BTreeMap::new() } else { record.state.drafts.iter().map(|(id,d)| (id.clone(),digest(&d.editor_json))).collect::<BTreeMap<_,_>>() },
        "recovery_candidates": if candidates { Some(&record.state) } else { None },
        "recovery_requires_confirmation": candidates})
}
fn next_revision(record: &Stored) -> Result<i64, Error> {
    if record.state_revision >= 9_007_199_254_740_991 {
        return Err(Error::Invalid("UI state revision exhausted"));
    }
    Ok(record.state_revision + 1)
}
fn publish(conn: &Connection, record: &Stored) -> Result<(), Error> {
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value", rusqlite::params![STATE_KEY,serde_json::to_string(record).map_err(|_|Error::Invalid("invalid state JSON"))?])?;
    Ok(())
}
fn compare(
    record: &Stored,
    id: &str,
    current_epoch: &str,
    request_id: &str,
    request_epoch: &str,
    revision: i64,
) -> Result<(), Error> {
    if request_id != id || request_epoch != current_epoch || revision != record.state_revision {
        return Err(Error::Conflict);
    }
    Ok(())
}
/// Called through Store even though named read: first-use identity initialization is a Core write.
pub fn read(conn: &mut Connection) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let record = stored(&tx, &id, &current_epoch)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}
pub fn write(conn: &mut Connection, request: Write) -> Result<Value, Error> {
    validate(&request.state)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let old = stored(&tx, &id, &current_epoch)?;
    compare(
        &old,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    // After restore, preserve candidate state until an explicit separate recovery decision exists.
    if old.restore_epoch != current_epoch {
        return Err(Error::Conflict);
    }
    if let Some(release) = &request.release_teaching {
        let prior = old
            .state
            .teaching_drafts
            .get(&release.draft_key)
            .ok_or(Error::Invalid("frozen teaching draft unavailable"))?;
        let record = prior
            .pending_record
            .as_ref()
            .ok_or(Error::Invalid("teaching request is not frozen"))?;
        let mut expected = prior.clone();
        expected.pending_record = None;
        if record.record_id != release.record_id
            || request.state.teaching_drafts.get(&release.draft_key) != Some(&expected)
        {
            return Err(Error::Invalid(
                "teaching release must retain exact editable draft",
            ));
        }
        // The same writer transaction proves absence and permanently retires the old ID.
        // A queued/unknown create arriving later cannot publish the released snapshot.
        crate::teaching::retire_unadmitted(&tx,&release.record_id).map_err(|_|Error::Invalid("teaching record already exists or retirement unavailable; retry exact record to reconcile"))?;
    }
    for (key, draft) in &old.state.teaching_drafts {
        if let Some(attempt) = &draft.preparation_attempt {
            match request
                .state
                .teaching_drafts
                .get(key)
                .and_then(|d| d.preparation_attempt.as_ref())
            {
                Some(next) if next == attempt => {}
                Some(_) => {
                    return Err(Error::Invalid(
                        "frozen preparation request cannot be replaced",
                    ));
                }
                None => check_preparation_saved(&tx, attempt)?,
            }
        }
        if let Some(pending) = &draft.pending_record {
            if request
                .release_teaching
                .as_ref()
                .is_some_and(|release| release.draft_key == *key)
            {
                continue;
            }
            if request.state.teaching_drafts.get(key) == Some(draft) {
                continue;
            }
            if request.state.teaching_drafts.contains_key(key) {
                return Err(Error::Invalid("frozen teaching draft cannot be replaced"));
            }
            let saved: Option<String> = tx
                .query_row(
                    "SELECT record_json FROM teaching_records WHERE record_id=?1",
                    [&pending.record_id],
                    |r| r.get(0),
                )
                .optional()?;
            if saved
                .as_deref()
                .and_then(|s| serde_json::from_str::<crate::teaching::TeachingRecord>(s).ok())
                .as_ref()
                != Some(pending)
            {
                return Err(Error::Invalid(
                    "frozen teaching draft requires exact saved record",
                ));
            }
        }
    }
    for (key, draft) in &request.state.learning_drafts {
        if old.state.learning_drafts.get(key).is_some_and(|prior| {
            prior.item_key != draft.item_key
                || prior.knowledge_version != draft.knowledge_version
                || prior.question_version != draft.question_version
        }) {
            return Err(Error::Invalid(
                "learning draft version binding cannot be replaced",
            ));
        }
        if old.state.learning_drafts.get(key) != Some(draft) {
            check_learning_draft_binding(&tx, draft)?;
        }
    }
    for (key, pending) in &old.state.pending_machine {
        if request.state.pending_machine.get(key) != Some(pending) {
            return Err(Error::Invalid(
                "frozen machine cannot be replaced or omitted; requires exact receipt clearance",
            ));
        }
    }
    for (key, pending) in &request.state.pending_machine {
        if !old.state.pending_machine.contains_key(key)
            && pending.origin_restore_epoch != current_epoch
        {
            return Err(Error::Invalid(
                "new frozen machine belongs to another restore epoch",
            ));
        }
        if !old.state.pending_machine.contains_key(key) {
            machine_owner(&tx, pending)?;
        }
    }
    for (key, pending) in &old.state.pending_reviews {
        if request.state.pending_reviews.get(key) == Some(pending) {
            continue;
        }
        if request.state.pending_reviews.contains_key(key) {
            return Err(Error::Invalid("frozen review cannot be replaced"));
        }
        let mut canonical = serde_json::Map::new();
        for field in [
            "item_key",
            "correct",
            "rating",
            "now",
            "answer",
            "assessment_id",
            "question_version",
            "knowledge_version",
            "exposure_id",
            "assist_strategy",
            "rating_version",
            "correction_id",
        ] {
            canonical.insert(
                field.into(),
                pending.body.get(field).cloned().unwrap_or(Value::Null),
            );
        }
        let canonical = Value::Object(canonical).to_string();
        let mut hash = Sha256::new();
        hash.update(b"archeaxis.learning-state/v1\0");
        for part in [
            "review",
            if pending.body["correct"] == true {
                "correct"
            } else {
                "incorrect"
            },
            canonical.as_str(),
        ] {
            hash.update((part.len() as u64).to_le_bytes());
            hash.update(part.as_bytes());
        }
        let confirmed = tx.query_row("SELECT EXISTS(SELECT 1 FROM learning_event_keys k JOIN learning_events e ON e.event_id=k.event_id WHERE k.event_key=?1 AND k.item_key=?2 AND e.item_key=?2 AND k.payload_hash=?3)", rusqlite::params![key, pending.item_key, hex::encode(hash.finalize())], |r| r.get::<_, bool>(0))?;
        if !confirmed {
            return Err(Error::Invalid(
                "frozen review requires exact committed receipt before removal",
            ));
        }
    }
    for (key, pending) in &request.state.pending_reviews {
        if !old.state.pending_reviews.contains_key(key) {
            if pending.origin_restore_epoch != current_epoch {
                return Err(Error::Invalid(
                    "new frozen review belongs to another restore epoch",
                ));
            }
            let bound = tx.query_row("SELECT EXISTS(SELECT 1 FROM learning_assessments WHERE assessment_id=?1 AND item_key=?2 AND knowledge_version=?3)", rusqlite::params![pending.body["assessment_id"].as_str(), pending.item_key, pending.body["knowledge_version"].as_str()], |r| r.get::<_, bool>(0))?;
            if !bound {
                return Err(Error::Invalid("frozen review assessment binding mismatch"));
            }
        }
    }
    for (key, pending) in &old.state.pending_jobs {
        if request.state.pending_jobs.get(key) != Some(pending) {
            return Err(Error::Invalid(
                "frozen job cannot be replaced or omitted; use verified clear",
            ));
        }
    }
    for (key, pending) in &request.state.pending_jobs {
        if !old.state.pending_jobs.contains_key(key) && job_abandoned(&tx, key)? {
            return Err(Error::Invalid(
                "abandoned request identity cannot be reused",
            ));
        }
        if !old.state.pending_jobs.contains_key(key)
            && pending.origin_restore_epoch != current_epoch
        {
            return Err(Error::Invalid(
                "new frozen job belongs to another restore epoch",
            ));
        }
        check_job_binding(&tx, pending)?;
    }
    if let (Some(old_attempt), Some(new_attempt)) =
        (&old.state.pending_original, &request.state.pending_original)
    {
        if old_attempt != new_attempt {
            return Err(Error::Invalid(
                "pending original request is frozen; resolve or explicitly cancel it first",
            ));
        }
    }
    for id in &request.state.opened_documents {
        if !tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
            [id],
            |r| r.get::<_, bool>(0),
        )? {
            return Err(Error::Invalid("opened document missing"));
        }
    }
    for (id, draft) in &request.state.drafts {
        if !tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1 AND version=?2)",
            rusqlite::params![id, draft.base_version],
            |r| r.get::<_, bool>(0),
        )? {
            return Err(Error::Invalid("draft base version missing"));
        }
    }
    let record = Stored {
        schema: BASIS.into(),
        workspace_id: id,
        restore_epoch: current_epoch.clone(),
        state_revision: next_revision(&old)?,
        state: request.state,
    };
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}
pub fn clear_saved(conn: &mut Connection, request: ClearSaved) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let mut record = stored(&tx, &id, &current_epoch)?;
    compare(
        &record,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    if record.restore_epoch != current_epoch {
        return Err(Error::Conflict);
    }
    let draft = record
        .state
        .drafts
        .get(&request.document_id)
        .ok_or(Error::Conflict)?;
    if draft.base_version != request.base_version
        || digest(&draft.editor_json) != request.content_sha256
        || request.saved_version != request.base_version.checked_add(1).ok_or(Error::Conflict)?
    {
        return Err(Error::Conflict);
    }
    let raw: Option<String> = tx
        .query_row(
            "SELECT editor_json FROM document_versions WHERE document_id=?1 AND version=?2",
            rusqlite::params![request.document_id, request.saved_version],
            |r| r.get(0),
        )
        .optional()?;
    let saved: Value = serde_json::from_str(&raw.ok_or(Error::Conflict)?)
        .map_err(|_| Error::Invalid("corrupt document version"))?;
    if digest(&saved) != request.content_sha256 {
        return Err(Error::Conflict);
    }
    record.state.drafts.remove(&request.document_id);
    record.state_revision = next_revision(&record)?;
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RecoveryAction {
    Preserve,
    Discard,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Recover {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub state_revision: i64,
    pub action: RecoveryAction,
}
/// Explicit human recovery after preview; never called by read/write/Document ACK.
pub fn recover(conn: &mut Connection, request: Recover) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let mut record = stored(&tx, &id, &current_epoch)?;
    compare(
        &record,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    if record.restore_epoch == current_epoch {
        return Err(Error::Conflict);
    }
    match request.action {
        RecoveryAction::Discard => {
            if !record.state.pending_machine.is_empty()
                || !record.state.pending_reviews.is_empty()
                || record
                    .state
                    .teaching_drafts
                    .values()
                    .any(|d| d.pending_record.is_some() || d.preparation_attempt.is_some())
            {
                return Err(Error::Invalid(
                    "unconfirmed machine, review or teaching recovery candidate requires exact receipt; preserve candidate before reconciliation",
                ));
            }
            record.state = State::default();
        }
        RecoveryAction::Preserve => {
            for draft in record.state.learning_drafts.values() {
                check_learning_draft_binding(&tx, draft)?;
            }
            for pending in record.state.pending_jobs.values() {
                check_job_binding(&tx, pending)?;
            }
            for (id, draft) in &record.state.drafts {
                if !tx.query_row("SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1 AND version=?2)",rusqlite::params![id,draft.base_version],|r|r.get::<_,bool>(0))? { return Err(Error::Invalid("recovery draft base version missing; candidate retained")); }
            }
            for id in &record.state.opened_documents {
                if !tx.query_row(
                    "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
                    [id],
                    |r| r.get::<_, bool>(0),
                )? {
                    return Err(Error::Invalid(
                        "recovery opened document missing; candidate retained",
                    ));
                }
            }
        }
    }
    record.restore_epoch = current_epoch.clone();
    record.state_revision = next_revision(&record)?;
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}

fn check_learning_draft_binding(conn: &Connection, draft: &LearningDraft) -> Result<(), Error> {
    let bound = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM learning_assessments WHERE assessment_id=?1 AND item_key=?2 AND knowledge_version=?3)",
        rusqlite::params![draft.assessment_id, draft.item_key, draft.knowledge_version],
        |r| r.get::<_, bool>(0),
    )?;
    if !bound {
        return Err(Error::Invalid("learning draft assessment binding mismatch"));
    }
    Ok(())
}

fn check_job_binding(conn: &Connection, pending: &PendingJob) -> Result<(), Error> {
    let sha: Option<String> = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&pending.source_id],
            |r| r.get(0),
        )
        .optional()?;
    if sha.as_deref() != Some(pending.source_revision.as_str()) {
        return Err(Error::Invalid("frozen source revision missing or changed"));
    }
    let job: Option<(String, String)> = conn
        .query_row(
            "SELECT input_ref,kind FROM jobs WHERE job_id=?1",
            [&pending.job_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    if job.is_some_and(|(source, kind)| source != pending.source_id || kind != pending.kind) {
        return Err(Error::Invalid("frozen job source/kind conflict"));
    }
    // Missing job is a staged enqueue intent; this journal neither creates nor executes it.
    Ok(())
}
/// Caller holds Runtime admission and active guards; the same Store transaction proves clearance.
fn machine_claim(conn: &Connection, pending: &PendingMachine) -> Result<Option<Value>, Error> {
    let fingerprint = machine_request_fingerprint(&pending.operation, &pending.body);
    let claim_id = if pending.operation == "answer" {
        format!(
            "answer_req_{}",
            hex::encode(Sha256::digest(
                pending.body["client_request_id"]
                    .as_str()
                    .ok_or(Error::Invalid("answer identity missing"))?
                    .as_bytes()
            ))
        )
    } else {
        format!("retest_input_{fingerprint}")
    };
    let key = format!(
        "machine_execution_claim_{}",
        hex::encode(Sha256::digest(claim_id.as_bytes()))
    );
    let Some(raw) = meta(conn, &key)? else {
        return Ok(None);
    };
    Ok(serde_json::from_str::<Value>(&raw).ok())
}
/// A fresh transport identity must not bypass an unresolved journal of this journey.
/// Headless callers without a UI journal retain the existing API contract.
pub fn machine_admission_guard(
    conn: &Connection,
    owner: &str,
    operation: &str,
    fingerprint: &str,
) -> Result<(), Error> {
    let Some(raw) = meta(conn, STATE_KEY)? else {
        return Ok(());
    };
    if raw.len() > 1_100_000 {
        return Err(Error::Invalid("working state exceeds bound"));
    }
    let record: Stored =
        serde_json::from_str(&raw).map_err(|_| Error::Invalid("working state unreadable"))?;
    validate(&record.state)?;
    for pending in record
        .state
        .pending_machine
        .values()
        .filter(|p| p.owner_knowledge_id == owner)
    {
        if pending.operation != operation
            || machine_request_fingerprint(&pending.operation, &pending.body) != fingerprint
        {
            return Err(Error::Conflict);
        }
    }
    Ok(())
}
fn failure_binding(
    conn: &Connection,
    pending: &PendingMachine,
    task_id: &str,
    doc: &Value,
    retest_of: Option<&str>,
) -> Result<bool, Error> {
    let fingerprint = machine_request_fingerprint(&pending.operation, &pending.body);
    let Some(claim) = machine_claim(conn, pending)? else {
        return Ok(false);
    };
    Ok(doc["schema"] == "archeaxis.machine-execution-failed/v1"
        && doc["execution_state"] == "UNVERIFIED"
        && doc["answer_published"] == false
        && doc["authority"] == "historical_execution_audit"
        && doc["audit_task_id"] == task_id
        && doc["operation"] == pending.operation
        && doc["knowledge_id"] == pending.body["knowledge_id"]
        && doc["admission_request_sha256"] == fingerprint
        && claim["schema"] == "archeaxis.machine-execution-claim/v1"
        && claim["state"] == "KNOWN_FAILURE"
        && claim["terminal_task_id"] == task_id
        && claim["attempt"] == doc["attempt"]
        && claim["request_sha256"] == doc["request_sha256"]
        && doc["attempt"]
            .as_u64()
            .is_some_and(|n| (1..=3).contains(&n))
        && doc["max_attempts"] == 3
        && claim["max_attempts"] == 3
        && (if pending.operation == "answer" {
            doc["client_request_id"] == pending.body["client_request_id"]
                && doc["retest_of"].is_null()
                && retest_of.is_none()
        } else {
            doc["retest_of"] == pending.body["retest_of"]
                && retest_of == pending.body["retest_of"].as_str()
        }))
}

/// Historical read only: never consumes grants, invokes inference or changes journals.
/// A persisted unfinished claim is UNKNOWN, not proof of a live worker.
pub fn machine_status(conn: &Connection, request: MachineStatus) -> Result<Value, Error> {
    let id = meta(conn, ID_KEY)?.ok_or(Error::Invalid("workspace identity missing"))?;
    let current_epoch = epoch(conn)?;
    let record = stored(conn, &id, &current_epoch)?;
    compare(
        &record,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    if record.restore_epoch != current_epoch {
        return Err(Error::Conflict);
    }
    let pending = record
        .state
        .pending_machine
        .get(&request.journal_id)
        .ok_or(Error::Invalid("frozen machine missing"))?;
    machine_owner(conn, pending)?;
    let mut result = serde_json::json!({"schema":"archeaxis.machine-journal-status/v1","journal_id":request.journal_id,
        "status":"UNKNOWN","can_clear":false,"task_id":null,"attempt":null,"max_attempts":3,"provider_stop_state":"UNKNOWN"});
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='machine_tasks')",
        [],
        |r| r.get(0),
    )?;
    if !exists {
        return Ok(result);
    }
    let Some(claim) = machine_claim(conn, pending)? else {
        return Ok(result);
    };
    let Some(task_id) = claim["terminal_task_id"].as_str() else {
        return Ok(result);
    };
    let row:Option<(String,Option<String>)>=conn.query_row("SELECT conditions,retest_of FROM machine_tasks WHERE scope='runtime.execution.failed' AND task_id=?1",[task_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
    if let Some((raw, retest_of)) = row {
        let Ok(doc) = serde_json::from_str::<Value>(&raw) else {
            return Ok(result);
        };
        if failure_binding(conn, pending, &task_id, &doc, retest_of.as_deref())? {
            result["status"] =
                serde_json::json!(if doc["reason_code"] == "machine worker cancelled" {
                    "CANCELLED_LOCAL_WORKER"
                } else {
                    "FAILED"
                });
            result["can_clear"] = serde_json::json!(true);
            result["task_id"] = serde_json::json!(task_id);
            result["attempt"] = doc["attempt"].clone();
        }
    }
    Ok(result)
}

/// CAS-bound cancellation target; an unfinished claim alone is not a live process.
pub fn machine_execution_epoch(conn: &Connection) -> Result<String, Error> {
    epoch(conn)
}
pub fn machine_cancel_target(
    conn: &Connection,
    request: MachineStatus,
) -> Result<Option<(String, u64, String)>, Error> {
    let journal = request.journal_id.clone();
    machine_status(conn, request)?;
    let id = workspace_id(conn)?;
    let current_epoch = epoch(conn)?;
    let record = stored(conn, &id, &current_epoch)?;
    let pending = record
        .state
        .pending_machine
        .get(&journal)
        .ok_or(Error::Invalid("frozen machine missing"))?;
    let Some(claim) = machine_claim(conn, pending)? else {
        return Ok(None);
    };
    if claim["state"] != "IN_FLIGHT" {
        return Ok(None);
    }
    let Some(attempt) = claim["attempt"].as_u64().filter(|n| (1..=3).contains(n)) else {
        return Ok(None);
    };
    Ok(Some((
        machine_request_fingerprint(&pending.operation, &pending.body),
        attempt,
        current_epoch,
    )))
}

/// Caller holds Runtime admission and active guards; the same Store transaction proves clearance.
pub fn clear_machine(conn: &mut Connection, request: ClearMachine) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let mut record = stored(&tx, &id, &current_epoch)?;
    compare(
        &record,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    if record.restore_epoch != current_epoch {
        return Err(Error::Conflict);
    }
    let pending = record
        .state
        .pending_machine
        .get(&request.journal_id)
        .ok_or(Error::Invalid("frozen machine missing"))?;
    machine_owner(&tx, pending)?;
    let scope = if pending.operation == "answer" {
        "runtime.answer"
    } else {
        "runtime.retest"
    };
    let raw:Option<(String,String,Option<String>)>=tx.query_row("SELECT conditions,scope,retest_of FROM machine_tasks WHERE task_id=?1 AND scope IN (?2,'runtime.execution.withheld','runtime.execution.failed')",rusqlite::params![request.task_id,scope],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).optional()?;
    let (raw, actual_scope, retest_of) =
        raw.ok_or(Error::Invalid("exact machine receipt missing"))?;
    let doc: Value =
        serde_json::from_str(&raw).map_err(|_| Error::Invalid("corrupt machine receipt"))?;
    if actual_scope == "runtime.execution.failed" {
        if !failure_binding(&tx, pending, &request.task_id, &doc, retest_of.as_deref())? {
            return Err(Error::Invalid(
                "failure audit frozen identity or current attempt mismatch",
            ));
        }
        record.state.pending_machine.remove(&request.journal_id);
        record.state_revision = next_revision(&record)?;
        publish(&tx, &record)?;
        let result = response(&record, &current_epoch);
        tx.commit()?;
        return Ok(result);
    }
    if actual_scope == "runtime.execution.withheld" {
        if doc["schema"] != "archeaxis.machine-execution-withheld/v1"
            || doc["execution_state"] != "EXECUTED_BUT_WITHHELD"
            || doc["answer_published"] != false
            || doc["authority"] != "historical_execution_audit"
            || doc["audit_task_id"] != request.task_id
            || doc["operation"] != pending.operation
            || doc["knowledge_id"] != pending.body["knowledge_id"]
            || doc["admission_request_sha256"]
                != machine_request_fingerprint(&pending.operation, &pending.body)
            || (pending.operation == "answer"
                && (doc["client_request_id"] != pending.body["client_request_id"]
                    || !doc["retest_of"].is_null()
                    || retest_of.is_some()))
            || (pending.operation == "retest"
                && (doc["retest_of"] != pending.body["retest_of"]
                    || retest_of.as_deref() != pending.body["retest_of"].as_str()))
        {
            return Err(Error::Invalid("withheld audit frozen identity mismatch"));
        }
        record.state.pending_machine.remove(&request.journal_id);
        record.state_revision = next_revision(&record)?;
        publish(&tx, &record)?;
        let result = response(&record, &current_epoch);
        tx.commit()?;
        return Ok(result);
    }
    let body = &pending.body;
    let proof = &doc["request"];
    let schema = if pending.operation == "answer" {
        "archeaxis.machine-answer/v1"
    } else {
        "archeaxis.machine-retest/v1"
    };
    let common = [
        "knowledge_id",
        "question",
        "max_tokens",
        "context_grant",
        "asset_context_grant",
        "model",
        "model_configuration",
    ];
    if doc["schema"] != schema
        || doc["authority"] != "candidate"
        || doc["answer_id"] != request.task_id
        || doc["knowledge_id"] != body["knowledge_id"]
        || doc["question"] != body["question"]
        || common.iter().any(|k| proof[*k] != body[*k])
        || !doc["answer"]["answer"]
            .as_str()
            .is_some_and(|s| !s.trim().is_empty())
    {
        return Err(Error::Invalid("machine receipt frozen input mismatch"));
    }
    if pending.operation == "answer" {
        let client = body["client_request_id"]
            .as_str()
            .ok_or(Error::Invalid("answer request identity missing"))?;
        let expected = format!(
            "answer_req_{}",
            hex::encode(Sha256::digest(client.as_bytes()))
        );
        if request.task_id != expected
            || doc["client_request_id"] != client
            || proof["timeout_s"] != body["timeout_s"]
            || (body.get("asset_context_grant").is_some()
                && proof["asset_client_request_id"] != client)
        {
            return Err(Error::Invalid("answer receipt identity mismatch"));
        }
    } else if doc["retest_of"] != body["retest_of"]
        || proof["retest_of"] != body["retest_of"]
        || doc["execution_request"]["timeout_s"] != body["timeout_s"]
    {
        return Err(Error::Invalid("retest receipt identity or budget mismatch"));
    }
    record.state.pending_machine.remove(&request.journal_id);
    record.state_revision = next_revision(&record)?;
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}

/// Caller holds Runtime admission and active guards; the same Store transaction proves clearance.
pub fn clear_job(conn: &mut Connection, request: ClearJob) -> Result<Value, Error> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = workspace_id(&tx)?;
    let current_epoch = epoch(&tx)?;
    let mut record = stored(&tx, &id, &current_epoch)?;
    compare(
        &record,
        &id,
        &current_epoch,
        &request.workspace_id,
        &request.restore_epoch,
        request.state_revision,
    )?;
    if record.restore_epoch != current_epoch {
        return Err(Error::Conflict);
    }
    let pending = record
        .state
        .pending_jobs
        .get(&request.request_id)
        .ok_or(Error::Invalid("frozen request missing"))?;
    check_job_binding(&tx, pending)?;
    let actual: Option<(String, String, String)> = tx
        .query_row(
            "SELECT job_id,state,request_json FROM job_attempts WHERE request_id=?1",
            [&request.request_id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .optional()?;
    match request.action.as_str() {
        "terminal" => {
            let (job, state, wire) =
                actual.ok_or(Error::Invalid("exact terminal request not recorded"))?;
            let value: Value = serde_json::from_str(&wire)
                .map_err(|_| Error::Invalid("corrupt execution request"))?;
            if job != pending.job_id
                || !matches!(
                    state.as_str(),
                    "succeeded" | "failed" | "cancelled" | "rejected"
                )
                || value["job_id"] != pending.job_id
                || value["request_id"] != pending.request_id
                || value["deadline_ms"].as_u64() != Some(pending.body.deadline_ms)
                || value
                    .pointer("/parameters/split")
                    .and_then(Value::as_bool)
                    .unwrap_or(false)
                    != pending.body.split
                || value
                    .pointer("/parameters/words")
                    .and_then(Value::as_bool)
                    .unwrap_or(false)
                    != pending.body.words
            {
                return Err(Error::Invalid("exact terminal request binding mismatch"));
            }
        }
        "abandon_unadmitted" => {
            if pending.origin_restore_epoch != current_epoch || actual.is_some() {
                return Err(Error::Invalid(
                    "request admission/history is not proven absent",
                ));
            }
            let running: bool = tx.query_row(
                "SELECT EXISTS(SELECT 1 FROM job_attempts WHERE job_id=?1 AND state='running')",
                [&pending.job_id],
                |r| r.get(0),
            )?;
            if running {
                return Err(Error::Invalid("job still has an active durable claim"));
            }
            let mut tombstones = abandoned(&tx)?;
            if tombstones.len() >= 256 {
                return Err(Error::Invalid(
                    "abandoned identity limit reached; journal retained",
                ));
            }
            tombstones.insert(pending.request_id.clone(), digest(&json!(pending)));
            tx.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",rusqlite::params![ABANDONED_KEY,serde_json::to_string(&tombstones).map_err(|_|Error::Invalid("invalid abandoned identity JSON"))?])?;
        }
        _ => return Err(Error::Invalid("unknown clear job action")),
    }
    record.state.pending_jobs.remove(&request.request_id);
    record.state_revision = next_revision(&record)?;
    publish(&tx, &record)?;
    let result = response(&record, &current_epoch);
    tx.commit()?;
    Ok(result)
}

fn abandoned(conn: &Connection) -> Result<BTreeMap<String, String>, Error> {
    let Some(raw) = meta(conn, ABANDONED_KEY)? else {
        return Ok(BTreeMap::new());
    };
    if raw.len() > 65536 {
        return Err(Error::Invalid("abandoned identity record too large"));
    }
    let values: BTreeMap<String, String> = serde_json::from_str(&raw)
        .map_err(|_| Error::Invalid("corrupt abandoned identity record"))?;
    if values.len() > 256
        || values.iter().any(|(key, value)| {
            !identity(key)
                || value.len() != 64
                || !value
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        })
    {
        return Err(Error::Invalid("invalid abandoned identity record"));
    }
    Ok(values)
}
/// A late HTTP request for an explicitly abandoned key must never start a worker.
pub fn job_abandoned(conn: &Connection, request_id: &str) -> Result<bool, Error> {
    Ok(abandoned(conn)?.contains_key(request_id))
}
