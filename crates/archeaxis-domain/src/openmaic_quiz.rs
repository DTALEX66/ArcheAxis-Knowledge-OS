//! Outline-to-quiz candidates: Core reads one persisted `quiz` outline, captures
//! the donor quiz prompt, calls the declared local model, replays the reply
//! through the donor quiz adapter and then persists the existing scene
//! candidate through the fixed scene builder. Every stage keeps its own receipt;
//! a failure writes nothing.
//!
//! This module contains no process launch and no network access. It builds the
//! exact frames Core sends, re-checks what the workers returned and derives the
//! metadata Core stores beside the existing scene candidate Document.
use crate::course;
use crate::document::{self, Error};
use crate::openmaic_slide;
use crate::provider_material_grant::Snapshot;
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

/// The Core-derived record stored inside the existing scene candidate attrs.
pub const OPENMAIC_QUIZ_RECORD_SCHEMA: &str = "archeaxis.openmaic-quiz-candidate/v1";
pub const OPENMAIC_QUIZ_PROMPT_SCHEMA: &str = "archeaxis.openmaic-quiz-prompt/v1";
pub const OPENMAIC_QUIZ_PROMPT_RESULT_SCHEMA: &str = "archeaxis.openmaic-quiz-prompt-result/v1";
pub const OPENMAIC_QUIZ_PROMPT_BINDING_SCHEMA: &str = "archeaxis.openmaic-quiz-prompt-binding/v1";
pub const OPENMAIC_QUIZ_GENERATION_ROUTE: &str = "outline_quiz_local_model";
pub const OPENMAIC_QUIZ_RESPONSE_ORIGIN: &str = "LOCAL_MODEL_UNVERIFIED";
/// The donor reply budget; the quiz prompt worker caps the caller-supplied reply
/// at 120,000 UTF-8 bytes, so Core refuses an over-budget frame itself.
const OPENMAIC_QUIZ_MAX_REPLY_BYTES: usize = 120_000;
const OPENMAIC_QUIZ_PROMPT_FIELDS: [&str; 13] = [
    "schema",
    "request_id",
    "input_sha256",
    "outline_manifest_sha256",
    "quiz_manifest_sha256",
    "quiz_excerpt_sha256",
    "npm_members_sha256",
    "worker_sha256",
    "guard_sha256",
    "system",
    "user",
    "system_sha256",
    "user_sha256",
];
const OPENMAIC_QUIZ_QUESTION_TYPES: [&str; 3] = ["single", "multiple", "short_answer"];

fn invalid(reason: &'static str) -> Error {
    Error::Invalid(reason)
}

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

pub(crate) fn token(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

pub(crate) fn hex_digest(value: &Value) -> bool {
    value
        .as_str()
        .is_some_and(|text| text.len() == 64 && text.bytes().all(|b| b.is_ascii_hexdigit()))
}

pub(crate) fn bounded_text(value: &Value, max_chars: usize) -> bool {
    value
        .as_str()
        .is_some_and(|text| !text.trim().is_empty() && text.chars().count() <= max_chars)
}

fn quiz_config_shape(value: &Value) -> bool {
    let Some(object) = value.as_object() else {
        return false;
    };
    object.len() == 3
        && object.contains_key("questionCount")
        && object.contains_key("difficulty")
        && object.contains_key("questionTypes")
        && value["questionCount"]
            .as_u64()
            .is_some_and(|count| (1..=30).contains(&count))
        && ["easy", "medium", "hard"].contains(&value["difficulty"].as_str().unwrap_or(""))
        && value["questionTypes"].as_array().is_some_and(|types| {
            (1..=3).contains(&types.len())
                && types
                    .iter()
                    .all(|kind| OPENMAIC_QUIZ_QUESTION_TYPES.contains(&kind.as_str().unwrap_or("")))
                && {
                    let mut seen = HashSet::new();
                    types
                        .iter()
                        .all(|kind| seen.insert(kind.as_str().unwrap_or("")))
                }
        })
}

/// The bounded outline entry the donor quiz prompt accepts. The worker's own
/// `validOutline` rejects any key outside this set, so Core sends exactly these.
pub fn openmaic_quiz_outline(selection: &Value) -> Result<Value, Error> {
    let outline = &selection["outline"];
    if outline["type"].as_str() != Some("quiz") {
        return Err(invalid("UNSUPPORTED_OUTLINE_TYPE"));
    }
    if !token(outline["id"].as_str().unwrap_or("")) {
        return Err(invalid("OUTLINE_CANDIDATE_CONTENT_INVALID"));
    }
    let title = outline["title"]
        .as_str()
        .filter(|value| !value.trim().is_empty() && value.chars().count() <= 240)
        .ok_or(invalid("OUTLINE_TITLE_OUT_OF_PROMPT_BOUNDS"))?;
    let description = outline["description"]
        .as_str()
        .filter(|value| value.chars().count() <= 16_000)
        .ok_or(invalid("OUTLINE_DESCRIPTION_OUT_OF_PROMPT_BOUNDS"))?;
    let key_points = outline["keyPoints"]
        .as_array()
        .filter(|points| {
            points.len() <= 200 && points.iter().all(|point| bounded_text(point, 2_000))
        })
        .ok_or(invalid("OUTLINE_KEY_POINTS_OUT_OF_PROMPT_BOUNDS"))?;
    let mut frame = json!({"id":outline["id"],"type":"quiz","title":title,
        "description":description,"keyPoints":key_points});
    if let Some(config) = outline.get("quizConfig") {
        if !quiz_config_shape(config) {
            return Err(invalid("OUTLINE_QUIZ_CONFIG_INVALID"));
        }
        frame["quizConfig"] = config.clone();
    }
    Ok(frame)
}

pub(crate) fn quiz_language_directive(selection: &Value) -> Result<String, Error> {
    let directive = selection["language_directive"].as_str().unwrap_or("");
    if directive.chars().count() > 2_000 || directive.contains('\0') {
        return Err(invalid("OUTLINE_LANGUAGE_DIRECTIVE_OUT_OF_BOUNDS"));
    }
    Ok(directive.to_owned())
}

/// The capture frame Core sends to the Node quiz worker. It carries no reply, so
/// the worker can only produce the prompt binding.
pub fn openmaic_quiz_capture_request(
    create_request_id: &str,
    selection: &Value,
) -> Result<Value, Error> {
    if !token(create_request_id) {
        return Err(invalid("OUTLINE_DOCUMENT_ID_INVALID"));
    }
    let outline = openmaic_quiz_outline(selection)?;
    let language_directive = quiz_language_directive(selection)?;
    Ok(
        json!({"schema":OPENMAIC_QUIZ_PROMPT_SCHEMA,"stage":"capture",
        "request_id":create_request_id,"outline":outline,
        "language_directive":language_directive}),
    )
}

fn sha_matches(text: &Value, expected: &Value) -> bool {
    text.as_str()
        .is_some_and(|text| expected.as_str() == Some(&digest(text.as_bytes())))
}

fn binding_shape(binding: &Value, create_request_id: &str) -> bool {
    binding.as_object().is_some_and(|object| {
        object.len() == OPENMAIC_QUIZ_PROMPT_FIELDS.len()
            && OPENMAIC_QUIZ_PROMPT_FIELDS
                .iter()
                .all(|key| object.contains_key(*key))
            && binding["schema"] == OPENMAIC_QUIZ_PROMPT_BINDING_SCHEMA
            && binding["request_id"].as_str() == Some(create_request_id)
            && [
                "input_sha256",
                "outline_manifest_sha256",
                "quiz_manifest_sha256",
                "quiz_excerpt_sha256",
                "npm_members_sha256",
                "worker_sha256",
                "guard_sha256",
                "system_sha256",
                "user_sha256",
            ]
            .iter()
            .all(|key| hex_digest(&binding[*key]))
            && binding["system"]
                .as_str()
                .is_some_and(|text| text.as_bytes().len() <= 200_000 && !text.contains('\0'))
            && binding["user"]
                .as_str()
                .is_some_and(|text| text.as_bytes().len() <= 200_000 && !text.contains('\0'))
            && sha_matches(&binding["system"], &binding["system_sha256"])
            && sha_matches(&binding["user"], &binding["user_sha256"])
    })
}

/// The prompt binding a `PROMPT_CAPTURED` result carries, or a named refusal.
pub fn openmaic_quiz_capture_binding(
    create_request_id: &str,
    capture: &Value,
) -> Result<Value, Error> {
    if capture["schema"] != OPENMAIC_QUIZ_PROMPT_RESULT_SCHEMA
        || capture["status"] != "PROMPT_CAPTURED"
        || capture["stage"] != "capture"
        || capture["request_id"].as_str() != Some(create_request_id)
        || capture["model_call"] != "NOT_INVOKED"
        || capture["network_performed"] != false
        || capture["core_task"] != "NOT_CONNECTED"
        || capture["core_authorization"] != "NOT_ESTABLISHED"
        || capture["canonical_bindings_verified"] != false
        || capture["persisted"] != false
        || capture["active_content_executed"] != false
        || capture["binding"].is_null()
    {
        return Err(invalid("QUIZ_PROMPT_RECEIPT_INVALID"));
    }
    if !binding_shape(&capture["binding"], create_request_id) {
        return Err(invalid("QUIZ_PROMPT_BINDING_UNSUPPORTED"));
    }
    Ok(capture["binding"].clone())
}

/// The prompt binding without the prompt text, as stored in the candidate record.
pub fn openmaic_quiz_prompt_record(binding: &Value) -> Value {
    let bytes = |key: &str| {
        binding[key]
            .as_str()
            .map(|text| text.as_bytes().len())
            .map_or(Value::Null, |len| json!(len))
    };
    json!({
        "schema":OPENMAIC_QUIZ_PROMPT_BINDING_SCHEMA,
        "request_id":binding["request_id"],
        "input_sha256":binding["input_sha256"],
        "outline_manifest_sha256":binding["outline_manifest_sha256"],
        "quiz_manifest_sha256":binding["quiz_manifest_sha256"],
        "quiz_excerpt_sha256":binding["quiz_excerpt_sha256"],
        "npm_members_sha256":binding["npm_members_sha256"],
        "worker_sha256":binding["worker_sha256"],
        "guard_sha256":binding["guard_sha256"],
        "system_sha256":binding["system_sha256"],
        "user_sha256":binding["user_sha256"],
        "system_bytes":bytes("system"),
        "user_bytes":bytes("user"),
    })
}

/// The replay frame: the captured binding plus the model's final text.
pub fn openmaic_quiz_replay_request(
    create_request_id: &str,
    selection: &Value,
    binding: &Value,
    content: &str,
) -> Result<Value, Error> {
    if !binding_shape(binding, create_request_id) {
        return Err(invalid("QUIZ_PROMPT_BINDING_UNSUPPORTED"));
    }
    if content.as_bytes().len() > OPENMAIC_QUIZ_MAX_REPLY_BYTES {
        return Err(invalid("MODEL_REPLY_EXCEEDS_BOUND"));
    }
    let outline = openmaic_quiz_outline(selection)?;
    let language_directive = quiz_language_directive(selection)?;
    Ok(
        json!({"schema":OPENMAIC_QUIZ_PROMPT_SCHEMA,"stage":"replay",
        "request_id":create_request_id,"outline":outline,
        "language_directive":language_directive,"binding":binding,
        "reply":{"kind":"caller_supplied","value":content}}),
    )
}

pub(crate) fn quiz_question_shape(question: &Value) -> bool {
    let Some(object) = question.as_object() else {
        return false;
    };
    let allowed = [
        "id",
        "type",
        "question",
        "options",
        "answer",
        "correctAnswer",
        "correct_answer",
        "analysis",
        "points",
        "commentPrompt",
        "hasAnswer",
    ];
    if object.keys().any(|key| !allowed.contains(&key.as_str()))
        || !token(object.get("id").and_then(Value::as_str).unwrap_or(""))
        || !OPENMAIC_QUIZ_QUESTION_TYPES.contains(&question["type"].as_str().unwrap_or(""))
        || !bounded_text(&question["question"], 8_000)
    {
        return false;
    }
    if question["type"] == "short_answer" {
        return question["hasAnswer"] == false
            && question.get("answer").is_none()
            && question.get("options").is_none();
    }
    if question["hasAnswer"] != true {
        return false;
    }
    let Some(options) = question["options"]
        .as_array()
        .filter(|items| (1..=26).contains(&items.len()))
    else {
        return false;
    };
    if options.iter().any(|option| {
        !option.is_object()
            || !bounded_text(&option["label"], 4_000)
            || !bounded_text(&option["value"], 512)
    }) {
        return false;
    }
    let Some(answer) = question["answer"]
        .as_array()
        .filter(|items| items.len() <= 26)
    else {
        return false;
    };
    if answer.iter().any(|item| !bounded_text(item, 4_000)) {
        return false;
    }
    let mut seen = HashSet::new();
    if !answer
        .iter()
        .all(|item| seen.insert(item.as_str().unwrap_or("")))
    {
        return false;
    }
    match question["type"].as_str() {
        Some("single") => answer.len() == 1,
        Some("multiple") => answer.len() >= 2,
        _ => false,
    }
}

/// The admitted question list, or `Ok(None)` for the worker's named refusal.
pub fn openmaic_quiz_replay_candidate(replay_document: &Value) -> Result<Option<Value>, Error> {
    if replay_document["schema"] != OPENMAIC_QUIZ_PROMPT_RESULT_SCHEMA {
        return Err(invalid("QUIZ_REPLAY_RECEIPT_INVALID"));
    }
    if replay_document["status"] != "CANDIDATE" {
        return Ok(None);
    }
    if replay_document["stage"] != "replay"
        || replay_document["response_origin"] != "CALLER_SUPPLIED_UNVERIFIED"
        || replay_document["model_call"] != "NOT_INVOKED"
        || replay_document["network_performed"] != false
        || replay_document["core_task"] != "NOT_CONNECTED"
        || replay_document["core_authorization"] != "NOT_ESTABLISHED"
        || replay_document["canonical_bindings_verified"] != false
        || replay_document["persisted"] != false
        || replay_document["active_content_executed"] != false
        || replay_document["human_review_required"] != true
        || replay_document["data"].is_null()
    {
        return Err(invalid("QUIZ_REPLAY_RECEIPT_INVALID"));
    }
    let questions = replay_document["data"]["questions"]
        .as_array()
        .filter(|items| (1..=30).contains(&items.len()))
        .ok_or(invalid("QUIZ_REPLAY_QUESTIONS_INVALID"))?;
    let mut ids = HashSet::new();
    for question in questions {
        if !quiz_question_shape(question)
            || !ids.insert(question["id"].as_str().unwrap_or("").to_owned())
        {
            return Err(invalid("QUIZ_REPLAY_QUESTIONS_INVALID"));
        }
    }
    Ok(Some(json!({"questions":questions})))
}

fn scene_digest_id(prefix: &str, create_request_id: &str) -> String {
    format!("{prefix}_{}", &digest(create_request_id.as_bytes())[..32])
}

/// The scene-build request for the already admitted questions. It carries the
/// selected outline verbatim, the caller's source snapshot and the exact
/// question list; `actions` stays empty because no action slice runs here.
pub fn openmaic_quiz_scene_build_request(
    create_request_id: &str,
    selection: &Value,
    questions: &Value,
    source: &Value,
) -> Result<Value, Error> {
    let list = questions["questions"]
        .as_array()
        .filter(|items| (1..=30).contains(&items.len()))
        .ok_or(invalid("QUIZ_REPLAY_QUESTIONS_INVALID"))?;
    let outline = &selection["outline"];
    Ok(json!({"schema":"archeaxis.openmaic-scene-build/v1",
        "request_id":create_request_id,"attempt":1,
        "source":source,
        "stage_id":scene_digest_id("stage", create_request_id),
        "scene_id":scene_digest_id("scene", create_request_id),
        "outline":{"id":outline["id"],"type":"quiz","title":outline["title"],
            "description":outline["description"],"keyPoints":outline["keyPoints"],
            "order":outline["order"]},
        "content":{"questions":list},
        "actions":[]}))
}

/// The scene-build request for an admitted quiz plus its admitted narration.
/// The action list is re-checked here so a non-speech, duplicate or oversize
/// action can never reach the builder.
pub fn openmaic_quiz_scene_build_request_with_actions(
    create_request_id: &str,
    selection: &Value,
    questions: &Value,
    source: &Value,
    actions: &Value,
) -> Result<Value, Error> {
    let mut request =
        openmaic_quiz_scene_build_request(create_request_id, selection, questions, source)?;
    let list = actions["actions"]
        .as_array()
        .filter(|items| (1..=2).contains(&items.len()))
        .ok_or(invalid("QUIZ_ACTIONS_INVALID"))?;
    let mut ids = HashSet::new();
    for action in list {
        let shaped = action.as_object().is_some_and(|object| {
            object.len() == 3
                && object.contains_key("id")
                && object.contains_key("type")
                && object.contains_key("text")
                && token(action["id"].as_str().unwrap_or(""))
                && action["type"].as_str() == Some("speech")
                && bounded_text(&action["text"], 8_000)
        });
        if !shaped || !ids.insert(action["id"].as_str().unwrap_or("").to_owned()) {
            return Err(invalid("QUIZ_ACTIONS_INVALID"));
        }
    }
    request["actions"] = json!(list);
    Ok(request)
}

fn stage_record(document: &Value, keys: &[(&str, &str)]) -> Value {
    let mut record = serde_json::Map::new();
    for (field, path) in keys {
        record.insert((*field).to_string(), lookup(document, path));
    }
    Value::Object(record)
}

fn lookup(document: &Value, path: &str) -> Value {
    let mut value = document;
    for part in path.split('.') {
        let Some(next) = value.get(part) else {
            return Value::Null;
        };
        value = next;
    }
    value.clone()
}

/// The Core-derived record stored beside the scene candidate. It names every
/// stage's declared identity without copying prompt text, model text or content.
pub fn openmaic_quiz_record(
    create_request_id: &str,
    request_sha256: &str,
    selection: &Value,
    prompt_binding: &Value,
    model_reply: &Value,
    replay: &Value,
) -> Value {
    let replay_record = stage_record(
        replay,
        &[
            ("status", "status"),
            ("reason", "reason"),
            ("callback_count", "callback_count"),
            ("exact_json_output", "exact_json_output"),
            ("transformations", "transformations"),
            ("question_count", "data.questions"),
        ],
    );
    let question_count = replay["data"]["questions"]
        .as_array()
        .map_or(Value::Null, |items| json!(items.len()));
    let mut replay_record = replay_record;
    replay_record["question_count"] = question_count;
    json!({
        "schema":OPENMAIC_QUIZ_RECORD_SCHEMA,
        "create_request_id":create_request_id,
        "request_sha256":request_sha256,
        "outline_document_id":selection["document_id"],
        "outline_document_version":selection["version"],
        "outline_document_content_sha256":selection["content_sha256"],
        "outline_index":selection["index"],
        "outline_id":selection["outline"]["id"],
        "outline_order":selection["outline"]["order"],
        "outline_type":"quiz",
        "generation_route":OPENMAIC_QUIZ_GENERATION_ROUTE,
        "model_call":"INVOKED",
        "model":model_reply["model"],
        "model_observed":model_reply["observed_model"],
        "model_reply_sha256":model_reply["content_sha256"],
        "model_reply_bytes":model_reply["content_bytes"],
        "model_finish_reason":model_reply["finish_reason"],
        "model_usage":model_reply["usage"],
        "prompt_binding":prompt_binding,
        "replay":replay_record,
        "response_origin":OPENMAIC_QUIZ_RESPONSE_ORIGIN,
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "provider":"openmaic",
        "provider_version":"1.3.0",
        "generation_version":"0.3.28",
    })
}

/// The existing quiz record plus the narration stage's own receipt. The stage
/// record names what ran and never copies prompt or model text.
pub fn openmaic_quiz_record_with_actions(
    create_request_id: &str,
    request_sha256: &str,
    selection: &Value,
    prompt_binding: &Value,
    model_reply: &Value,
    replay: &Value,
    actions_stage: &Value,
) -> Value {
    let mut record = openmaic_quiz_record(
        create_request_id,
        request_sha256,
        selection,
        prompt_binding,
        model_reply,
        replay,
    );
    record["actions_stage"] = actions_stage.clone();
    record
}

/// The persisted candidate as a client reads it, with the Core-derived chain
/// metadata surfaced next to the existing scene projection and render reports.
fn quiz_receipt(scene_receipt: Value) -> Value {
    let stored = &scene_receipt["document"]["editor_json"]["attrs"]
        [course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    json!({
        "schema":"archeaxis.openmaic-quiz-persistence/v1",
        "document":scene_receipt["document"],
        "candidate_document_status":scene_receipt["candidate_document_status"],
        "source_snapshot_status":scene_receipt["source_snapshot_status"],
        "generation_route":stored["generation_route"],
        "model_call":stored["model_call"],
        "model":stored["model"],
        "model_observed":stored["model_observed"],
        "model_reply_sha256":stored["model_reply_sha256"],
        "model_finish_reason":stored["model_finish_reason"],
        "prompt_binding":stored["prompt_binding"],
        "outline_document_id":stored["outline_document_id"],
        "outline_index":stored["outline_index"],
        "outline_id":stored["outline_id"],
        "replay":stored["replay"],
        "actions_stage":stored["actions_stage"],
        "response_origin":stored["response_origin"],
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "contract_version":scene_receipt["contract_version"],
        "projection":scene_receipt["projection"],
        "render":scene_receipt["render"],
    })
}

fn quiz_existing(
    conn: &Connection,
    create_request_id: &str,
    request_sha256: &str,
    selection: &Value,
) -> Result<Option<Value>, Error> {
    let Some(receipt) = course::openmaic_scene_candidate(conn, create_request_id)? else {
        return Ok(None);
    };
    let stored = &receipt["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    if stored["schema"].as_str() != Some(OPENMAIC_QUIZ_RECORD_SCHEMA)
        || stored["create_request_id"].as_str() != Some(create_request_id)
        || stored["request_sha256"].as_str() != Some(request_sha256)
        || stored["outline_document_id"] != selection["document_id"]
        || stored["outline_index"] != selection["index"]
    {
        return Err(invalid("QUIZ_REQUEST_CONFLICT"));
    }
    Ok(Some(quiz_receipt(receipt)))
}

/// Captured by Core before dispatch and checked again when admitting the result.
#[derive(Clone)]
pub struct OpenMaicQuizPending {
    restore_epoch: Option<String>,
    workspace_id: String,
    request_sha256: String,
    create_request_id: String,
    selection: Value,
}

#[derive(Clone)]
pub enum OpenMaicQuizPreparation {
    Existing(Value),
    Pending(OpenMaicQuizPending),
}

/// Check a retry and capture the outline version, source snapshot, workspace and
/// restore epoch in one Core transaction before any stage runs.
pub fn prepare_openmaic_quiz_candidate(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    selection: &Value,
) -> Result<OpenMaicQuizPreparation, Error> {
    if openmaic_slide::openmaic_slide_refusal(request).is_some()
        || request["create_request_id"].as_str() != Some(create_request_id)
    {
        return Err(invalid("INVALID_QUIZ_REQUEST"));
    }
    if selection["outline"]["type"].as_str() != Some("quiz") {
        return Err(invalid("UNSUPPORTED_OUTLINE_TYPE"));
    }
    let material: Snapshot = serde_json::from_value(request["source"].clone())
        .map_err(|_| invalid("INVALID_SOURCE_SNAPSHOT"))?;
    let request_sha256 = openmaic_slide::openmaic_slide_request_sha256(request, selection);
    let document_id = selection["document_id"]
        .as_str()
        .ok_or(invalid("OUTLINE_DOCUMENT_ID_INVALID"))?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let current = document::read_verified(&tx, document_id, None)?;
    if current["version"] != selection["version"]
        || current["content_sha256"] != selection["content_sha256"]
    {
        return Err(invalid("OUTLINE_DOCUMENT_CHANGED"));
    }
    let source = document::read_verified(&tx, &material.document_id, None)?;
    if source["version"].as_i64() != Some(material.version)
        || source["content_sha256"].as_str() != Some(material.content_sha256.as_str())
    {
        return Err(invalid("SOURCE_SNAPSHOT_NOT_CURRENT"));
    }
    if let Some(receipt) = quiz_existing(&tx, create_request_id, &request_sha256, selection)? {
        tx.commit()?;
        return Ok(OpenMaicQuizPreparation::Existing(receipt));
    }
    let restore_epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC quiz workspace identity unavailable"))?;
    tx.commit()?;
    Ok(OpenMaicQuizPreparation::Pending(OpenMaicQuizPending {
        restore_epoch,
        workspace_id,
        request_sha256,
        create_request_id: create_request_id.to_owned(),
        selection: selection.clone(),
    }))
}

/// The admitted chain. Core stores the exact stage receipts beside the scene;
/// nothing here can turn a non-candidate into content.
#[derive(Clone)]
pub struct OpenMaicQuizGeneration {
    pub scene_request: Value,
    pub record: Value,
}

/// Persist the existing scene candidate together with the Core-derived chain
/// record in one transaction. The worker document is re-checked against the exact
/// scene-build frame Core sent by `course::commit_openmaic_scene_with`.
pub fn commit_openmaic_quiz_candidate(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    pending: &OpenMaicQuizPending,
    scene_pending: &course::OpenMaicPending,
    worker_document: &Value,
    generation: &OpenMaicQuizGeneration,
) -> Result<Value, Error> {
    if create_request_id != pending.create_request_id.as_str()
        || openmaic_slide::openmaic_slide_request_sha256(request, &pending.selection)
            != pending.request_sha256
        || generation.record["schema"].as_str() != Some(OPENMAIC_QUIZ_RECORD_SCHEMA)
        || generation.record["create_request_id"].as_str() != Some(create_request_id)
        || generation.record["request_sha256"].as_str() != Some(pending.request_sha256.as_str())
        || generation.record["outline_document_id"] != pending.selection["document_id"]
        || generation.record["outline_index"] != pending.selection["index"]
    {
        return Err(invalid("QUIZ_REQUEST_CHANGED"));
    }
    let epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(conn)?;
    let workspace_id = crate::ui_state::existing_workspace_id(conn)
        .map_err(|_| invalid("OpenMAIC quiz workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(invalid("QUIZ_WORKSPACE_CHANGED"));
    }
    let receipt = course::commit_openmaic_scene_with(
        conn,
        create_request_id,
        &generation.scene_request,
        scene_pending,
        worker_document,
        Some(&generation.record),
    )?;
    Ok(quiz_receipt(receipt))
}

/// Read the candidate a repeated request already owns without running a stage.
pub fn read_openmaic_quiz_candidate(
    conn: &Connection,
    create_request_id: &str,
    request: &Value,
    selection: &Value,
) -> Result<Option<Value>, Error> {
    let Some(receipt) = course::openmaic_scene_candidate(conn, create_request_id)? else {
        return Ok(None);
    };
    let stored = &receipt["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    if stored["schema"].as_str() != Some(OPENMAIC_QUIZ_RECORD_SCHEMA) {
        return Err(invalid("QUIZ_REQUEST_CONFLICT"));
    }
    let request_sha256 = openmaic_slide::openmaic_slide_request_sha256(request, selection);
    if stored["create_request_id"].as_str() != Some(create_request_id)
        || stored["request_sha256"].as_str() != Some(request_sha256.as_str())
        || stored["outline_document_id"] != selection["document_id"]
        || stored["outline_index"] != selection["index"]
    {
        return Err(invalid("QUIZ_REQUEST_CONFLICT"));
    }
    Ok(Some(quiz_receipt(receipt)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn quiz_selection() -> Value {
        json!({"document_id":"doc_req_1","version":1,"content_sha256":"0".repeat(64),
            "index":0,
            "outline":{"id":"o1","type":"quiz","title":"Quiz","description":"Body",
                "keyPoints":["One"],"order":1,
                "quizConfig":{"questionCount":2,"difficulty":"easy",
                    "questionTypes":["single","multiple"]}},
            "language_directive":"Use Chinese."})
    }

    fn binding() -> Value {
        let system = "system text";
        let user = "user text";
        json!({"schema":OPENMAIC_QUIZ_PROMPT_BINDING_SCHEMA,"request_id":"quiz_1",
            "input_sha256":digest(b"input"),"outline_manifest_sha256":digest(b"outline"),
            "quiz_manifest_sha256":digest(b"quiz"),"quiz_excerpt_sha256":digest(b"excerpt"),
            "npm_members_sha256":digest(b"npm"),"worker_sha256":digest(b"worker"),
            "guard_sha256":digest(b"guard"),"system":system,"user":user,
            "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes())})
    }

    #[test]
    fn a_quiz_prompt_frame_keeps_the_quiz_config_and_rejects_other_types() {
        let selection = quiz_selection();
        let capture = openmaic_quiz_capture_request("quiz_1", &selection).unwrap();
        assert_eq!(capture["schema"], OPENMAIC_QUIZ_PROMPT_SCHEMA);
        assert_eq!(capture["stage"], "capture");
        assert_eq!(capture["outline"]["quizConfig"]["questionCount"], 2);
        assert!(capture["outline"].get("order").is_none());
        let replay =
            openmaic_quiz_replay_request("quiz_1", &selection, &binding(), "REPLY").unwrap();
        assert_eq!(replay["stage"], "replay");
        assert_eq!(replay["reply"]["kind"], "caller_supplied");
        let mut slide = selection.clone();
        slide["outline"]["type"] = json!("slide");
        assert!(matches!(
            openmaic_quiz_capture_request("quiz_1", &slide),
            Err(Error::Invalid("UNSUPPORTED_OUTLINE_TYPE"))
        ));
        let mut bad = selection.clone();
        bad["outline"]["quizConfig"]["questionTypes"] = json!(["single", "single"]);
        assert!(matches!(
            openmaic_quiz_capture_request("quiz_1", &bad),
            Err(Error::Invalid("OUTLINE_QUIZ_CONFIG_INVALID"))
        ));
    }

    #[test]
    fn a_non_candidate_replay_is_not_turned_into_questions() {
        let quarantined = json!({"schema":OPENMAIC_QUIZ_PROMPT_RESULT_SCHEMA,
            "status":"UPSTREAM_RESULT_NOT_ADMITTED","reason":"ambiguous"});
        assert!(
            openmaic_quiz_replay_candidate(&quarantined)
                .unwrap()
                .is_none()
        );
        let rejected = json!({"schema":"other/v1","status":"CANDIDATE"});
        assert!(openmaic_quiz_replay_candidate(&rejected).is_err());
    }

    #[test]
    fn the_record_keeps_digests_only_and_names_the_replay_outcome() {
        let mut binding = binding();
        binding["request_id"] = json!("quiz_1");
        let record = openmaic_quiz_prompt_record(&binding);
        assert_eq!(record["system_sha256"], digest(b"system text"));
        assert!(record.get("system").is_none());
        assert!(record.get("user").is_none());
        assert_eq!(record["system_bytes"], 11);
        let replay = json!({"status":"CANDIDATE","reason":null,
            "callback_count":1,"exact_json_output":false,
            "transformations":["UPSTREAM_JSON_REPAIRED"],
            "data":{"questions":[
                {"id":"q1","type":"single","question":"Q",
                 "options":[{"value":"A","label":"a"}],"answer":["A"],"hasAnswer":true}]}});
        let record = openmaic_quiz_record(
            "quiz_1",
            &digest(b"request"),
            &quiz_selection(),
            &record,
            &json!({"model":"m","observed_model":"m","content_sha256":digest(b"reply"),
                "content_bytes":5,"finish_reason":"stop","usage":null}),
            &replay,
        );
        assert_eq!(record["schema"], OPENMAIC_QUIZ_RECORD_SCHEMA);
        assert_eq!(record["generation_route"], OPENMAIC_QUIZ_GENERATION_ROUTE);
        assert_eq!(record["replay"]["question_count"], 1);
        assert_eq!(record["replay"]["exact_json_output"], false);
        assert_eq!(record["response_origin"], OPENMAIC_QUIZ_RESPONSE_ORIGIN);
    }
}
