//! Outline-to-slide candidates: Core reads one persisted `slide` outline, captures
//! the donor slide prompt, calls the declared local model, parses the reply through
//! the donor reply/normalize adapters and persists only the resulting scene
//! candidate. Every stage keeps its own receipt; a failure writes nothing.
//!
//! This module contains no process launch and no network access. It builds the
//! exact frames Core sends, re-checks what the workers returned and derives the
//! metadata Core stores beside the existing scene candidate Document.
use crate::course;
use crate::document::{self, Error};
use crate::openmaic_outline;
use crate::provider_material_grant::{Snapshot, valid_snapshot_shape};
use base64::Engine;
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

pub const OPENMAIC_SLIDE_REQUEST_SCHEMA: &str = "archeaxis.openmaic-slide-candidate-generate/v1";
/// The Core-derived record stored inside the existing scene candidate attrs.
pub const OPENMAIC_SLIDE_RECORD_SCHEMA: &str = "archeaxis.openmaic-slide-candidate/v1";
pub const OPENMAIC_SLIDE_PROMPT_SCHEMA: &str = "archeaxis.openmaic-slide-prompt/v1";
pub const OPENMAIC_SLIDE_PROMPT_RESULT_SCHEMA: &str = "archeaxis.openmaic-slide-prompt-result/v1";
pub const OPENMAIC_SLIDE_PROMPT_BINDING_SCHEMA: &str = "archeaxis.openmaic-slide-prompt-binding/v1";
pub const OPENMAIC_SLIDE_REPLY_SCHEMA: &str = "archeaxis.openmaic-slide-reply/v1";
pub const OPENMAIC_SLIDE_REPLY_RESULT_SCHEMA: &str = "archeaxis.openmaic-slide-reply-result/v1";
pub const OPENMAIC_SLIDE_NORMALIZE_SCHEMA: &str = "archeaxis.openmaic-slide-normalize/v1";
pub const OPENMAIC_SLIDE_NORMALIZE_RESULT_SCHEMA: &str =
    "archeaxis.openmaic-slide-normalize-result/v1";
pub const OPENMAIC_SLIDE_GENERATION_ROUTE: &str = "outline_slide_local_model";
pub const OPENMAIC_SLIDE_RESPONSE_ORIGIN: &str = "LOCAL_MODEL_UNVERIFIED";
/// The donor reply budget; the reply and normalize workers both cap their input at
/// 16,384 bytes, so Core refuses an over-budget frame itself instead of sending it.
const OPENMAIC_SLIDE_MAX_REPLY_BYTES: usize = 16_384;
const OPENMAIC_SLIDE_MAX_SCENE_BYTES: usize = 16_384;
const OPENMAIC_SLIDE_REQUEST_FIELDS: [&str; 6] = [
    "schema",
    "create_request_id",
    "outline_document_id",
    "outline_index",
    "source",
    "model",
];

fn invalid(reason: &'static str) -> Error {
    Error::Invalid(reason)
}

fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn token(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

fn model_identity(value: &Value) -> bool {
    value.as_str().is_some_and(|name| {
        !name.is_empty()
            && name.len() <= 256
            && name == name.trim()
            && !name.chars().any(char::is_control)
    })
}

fn hex_digest(value: &Value) -> bool {
    value
        .as_str()
        .is_some_and(|text| text.len() == 64 && text.bytes().all(|b| b.is_ascii_hexdigit()))
}

/// Name everything this route refuses before Core reads an outline or captures a
/// prompt. `None` means the request may proceed; every later check repeats.
pub fn openmaic_slide_refusal(request: &Value) -> Option<Value> {
    let Some(object) = request.as_object() else {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_SHAPE","declared":"not an object",
            "supported":[OPENMAIC_SLIDE_REQUEST_SCHEMA]}),
        );
    };
    if object.get("schema").and_then(Value::as_str) != Some(OPENMAIC_SLIDE_REQUEST_SCHEMA) {
        return Some(json!({"reason":"UNSUPPORTED_REQUEST_VERSION",
            "declared":object.get("schema").cloned().unwrap_or(Value::Null),
            "supported":[OPENMAIC_SLIDE_REQUEST_SCHEMA]}));
    }
    if object.len() != OPENMAIC_SLIDE_REQUEST_FIELDS.len()
        || OPENMAIC_SLIDE_REQUEST_FIELDS
            .iter()
            .any(|key| !object.contains_key(*key))
    {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_FIELDS","declared":object.len(),
            "supported":OPENMAIC_SLIDE_REQUEST_FIELDS.len()}),
        );
    }
    if request["create_request_id"]
        .as_str()
        .is_none_or(|value| !token(value))
    {
        return Some(json!({"reason":"INVALID_REQUEST_ID","declared":Value::Null,
            "supported":"1-128 ASCII [A-Za-z0-9_-] token"}));
    }
    if request["outline_document_id"]
        .as_str()
        .is_none_or(|value| !token(value))
    {
        return Some(
            json!({"reason":"INVALID_OUTLINE_DOCUMENT_ID","declared":Value::Null,
            "supported":"1-128 ASCII [A-Za-z0-9_-] token"}),
        );
    }
    if !request["outline_index"]
        .as_i64()
        .is_some_and(|value| (0..=29).contains(&value))
    {
        return Some(json!({"reason":"OUTLINE_INDEX_OUT_OF_RANGE",
            "declared":request["outline_index"],
            "supported":"0 to 29 (the stored outline list is 1-30 entries)"}));
    }
    let source_ok = serde_json::from_value::<Snapshot>(request["source"].clone())
        .is_ok_and(|snapshot| valid_snapshot_shape(&snapshot));
    if !source_ok {
        return Some(
            json!({"reason":"INVALID_SOURCE_SNAPSHOT","declared":request["source"],
            "supported":"{document_id, version, content_sha256}"}),
        );
    }
    if !request["model"].is_null() && !model_identity(&request["model"]) {
        return Some(
            json!({"reason":"INVALID_MODEL_SELECTION","declared":Value::Null,
            "supported":"an omitted model or 1-256 printable characters"}),
        );
    }
    None
}

/// Identity of one caller request bound to the outline document version it read.
/// The model reply is deliberately excluded: a second run must not write a second
/// candidate for the same request.
pub fn openmaic_slide_request_sha256(request: &Value, selection: &Value) -> String {
    digest(format!("{request}\n{selection}").as_bytes())
}

/// The outline metadata either persisted outline route writes, if this Document
/// carries one. Both namespaces are read; nothing is re-generated.
fn outline_metadata(document: &Value) -> Option<&Value> {
    let attrs = &document["editor_json"]["attrs"];
    let generated = &attrs[openmaic_outline::OPENMAIC_OUTLINE_GENERATE_NAMESPACE];
    if generated["schema"].as_str()
        == Some(openmaic_outline::OPENMAIC_OUTLINE_GENERATE_DOCUMENT_SCHEMA)
    {
        return Some(generated);
    }
    let replay = &attrs[openmaic_outline::OPENMAIC_OUTLINE_NAMESPACE];
    if replay["schema"].as_str() == Some(openmaic_outline::OPENMAIC_OUTLINE_DOCUMENT_SCHEMA) {
        return Some(replay);
    }
    None
}

/// Read the current version of one persisted outline candidate and select the
/// outline at `index`. The selected identity (`document_id`, `version`,
/// `content_sha256`) is part of the request identity and of the stored record.
pub fn read_outline_candidate(
    conn: &Connection,
    document_id: &str,
    index: i64,
) -> Result<Value, Error> {
    if !token(document_id) {
        return Err(invalid("OUTLINE_DOCUMENT_ID_INVALID"));
    }
    let document = document::read_verified(conn, document_id, None)?;
    let stored = outline_metadata(&document).ok_or(invalid("NOT_AN_OUTLINE_CANDIDATE"))?;
    let worker = &stored["worker_document"];
    if worker["status"].as_str() != Some("CANDIDATE") {
        return Err(invalid("OUTLINE_CANDIDATE_NOT_CURRENT"));
    }
    let outlines = worker["data"]["outlines"]
        .as_array()
        .filter(|items| (1..=30).contains(&items.len()))
        .ok_or(invalid("OUTLINE_CANDIDATE_CONTENT_INVALID"))?;
    let index = usize::try_from(index).map_err(|_| invalid("OUTLINE_INDEX_OUT_OF_RANGE"))?;
    let outline = outlines
        .get(index)
        .ok_or(invalid("OUTLINE_INDEX_OUT_OF_RANGE"))?;
    if !outline.is_object()
        || outline["id"].as_str().is_none_or(|id| !token(id))
        || !outline["type"].is_string()
        || outline["title"]
            .as_str()
            .is_none_or(|title| title.trim().is_empty())
        || !outline["description"].is_string()
        || !outline["keyPoints"].is_array()
    {
        return Err(invalid("OUTLINE_CANDIDATE_CONTENT_INVALID"));
    }
    let language_directive = worker["data"]["languageDirective"].as_str().unwrap_or("");
    if language_directive.as_bytes().len() > 2_000 {
        return Err(invalid("OUTLINE_LANGUAGE_DIRECTIVE_OUT_OF_BOUNDS"));
    }
    let order = outline["order"]
        .as_i64()
        .or_else(|| stored["outlines"][index]["order"].as_i64())
        .unwrap_or(index as i64 + 1);
    Ok(json!({
        "document_id":document["document_id"],
        "version":document["version"],
        "content_sha256":document["content_sha256"],
        "index":index,
        "outline":{"id":outline["id"],"type":outline["type"],"title":outline["title"],
            "description":outline["description"],"keyPoints":outline["keyPoints"],
            "order":order},
        "language_directive":language_directive,
    }))
}

/// The donor prompt frame. The worker receives only the outline title,
/// description and key points plus the language directive the outline candidate
/// already recorded; Core never asks a model for those again.
pub fn openmaic_slide_prompt_request(selection: &Value) -> Result<Value, Error> {
    let outline = &selection["outline"];
    let title = outline["title"]
        .as_str()
        .ok_or(invalid("OUTLINE_CANDIDATE_CONTENT_INVALID"))?;
    if title.trim().is_empty() || title.as_bytes().len() > 1_024 {
        return Err(invalid("OUTLINE_TITLE_OUT_OF_PROMPT_BOUNDS"));
    }
    let description = outline["description"]
        .as_str()
        .ok_or(invalid("OUTLINE_CANDIDATE_CONTENT_INVALID"))?;
    if description.as_bytes().len() > 6_000 {
        return Err(invalid("OUTLINE_DESCRIPTION_OUT_OF_PROMPT_BOUNDS"));
    }
    let key_points = outline["keyPoints"]
        .as_array()
        .ok_or(invalid("OUTLINE_CANDIDATE_CONTENT_INVALID"))?;
    if key_points.len() > 20
        || key_points.iter().any(|point| {
            point
                .as_str()
                .is_none_or(|value| value.trim().is_empty() || value.as_bytes().len() > 512)
        })
    {
        return Err(invalid("OUTLINE_KEY_POINTS_OUT_OF_PROMPT_BOUNDS"));
    }
    let language_directive = selection["language_directive"].as_str().unwrap_or("");
    let prompt = json!({
        "outline":{"title":title,"description":description,"key_points":key_points},
        "language_directive":language_directive,
    });
    let bytes = serde_json::to_vec(&prompt).map_err(|_| invalid("INVALID_PROMPT_FRAME"))?;
    Ok(json!({"schema":OPENMAIC_SLIDE_PROMPT_SCHEMA,
        "request_utf8_base64":base64::engine::general_purpose::STANDARD.encode(bytes),
        "include_private":true}))
}

/// The captured prompts plus their identities. The prompt text is kept in memory
/// only long enough to call the model; the stored record keeps the digests.
pub fn openmaic_slide_prompt_binding(prompt_document: &Value) -> Result<Value, Error> {
    let document = prompt_document;
    if document["schema"] != OPENMAIC_SLIDE_PROMPT_RESULT_SCHEMA
        || document["status"] != "BUILT"
        || document["scope"] != "CALLER_SUPPLIED_UNVERIFIED"
        || document["operation"] != "UPSTREAM_SLIDE_PROMPT_ONLY"
        || document["model_call"] != "NOT_INVOKED"
        || document["full_generation"] != "NOT_PERFORMED"
        || document["core_authorization"] != "NOT_ESTABLISHED"
    {
        return Err(invalid("SLIDE_PROMPT_RECEIPT_INVALID"));
    }
    let private = &document["private"];
    let system = private["system"]
        .as_str()
        .ok_or(invalid("SLIDE_PROMPT_RECEIPT_INVALID"))?;
    let user = private["user"]
        .as_str()
        .ok_or(invalid("SLIDE_PROMPT_RECEIPT_INVALID"))?;
    if system.as_bytes().len() > 65_536 || user.as_bytes().len() > 32_768 {
        return Err(invalid("SLIDE_PROMPT_BINDING_OUT_OF_BOUNDS"));
    }
    let system_sha256 = digest(system.as_bytes());
    let user_sha256 = digest(user.as_bytes());
    if private["system_sha256"].as_str() != Some(system_sha256.as_str())
        || private["user_sha256"].as_str() != Some(user_sha256.as_str())
    {
        return Err(invalid("SLIDE_PROMPT_BINDING_MISMATCH"));
    }
    Ok(json!({"schema":OPENMAIC_SLIDE_PROMPT_BINDING_SCHEMA,
        "system":system,"user":user,
        "system_sha256":system_sha256,"user_sha256":user_sha256,
        "system_bytes":system.as_bytes().len(),"user_bytes":user.as_bytes().len()}))
}

/// The prompt binding without the prompt text, as stored in the candidate record.
pub fn openmaic_slide_prompt_record(binding: &Value) -> Value {
    json!({"schema":OPENMAIC_SLIDE_PROMPT_BINDING_SCHEMA,
        "system_sha256":binding["system_sha256"],"user_sha256":binding["user_sha256"],
        "system_bytes":binding["system_bytes"],"user_bytes":binding["user_bytes"]})
}

/// The donor reply frame: only the model's final text, and only if it fits the
/// donor's own 16,384-byte reply budget. Nothing is truncated or repaired.
pub fn openmaic_slide_reply_request(content: &str) -> Result<Value, Error> {
    if content.as_bytes().len() > OPENMAIC_SLIDE_MAX_REPLY_BYTES {
        return Err(invalid("MODEL_REPLY_EXCEEDS_BOUND"));
    }
    Ok(json!({"schema":OPENMAIC_SLIDE_REPLY_SCHEMA,
        "reply_utf8_base64":base64::engine::general_purpose::STANDARD
            .encode(content.as_bytes()),
        "include_private":true}))
}

fn blob_bytes(blob: &Value) -> Option<Vec<u8>> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(blob["utf8_base64"].as_str()?)
        .ok()?;
    if blob["bytes"].as_u64()? as usize != bytes.len() || blob["sha256"].as_str()? != digest(&bytes)
    {
        return None;
    }
    Some(bytes)
}

/// The text-element reply as the donor adapter normalized it. `Ok(None)` means
/// the worker declared a non-candidate outcome; the caller answers with the
/// worker's own status and reason instead of inventing content.
pub fn openmaic_slide_reply_candidate(reply_document: &Value) -> Result<Option<Value>, Error> {
    let document = reply_document;
    if document["schema"] != OPENMAIC_SLIDE_REPLY_RESULT_SCHEMA {
        return Err(invalid("SLIDE_REPLY_RECEIPT_INVALID"));
    }
    if document["status"] != "CANDIDATE" {
        return Ok(None);
    }
    if document["reason"] != "EXACT_TEXT_ELEMENTS_ONLY"
        || document["scope"] != "CALLER_SUPPLIED_UNVERIFIED"
        || document["model_call"] != "NOT_INVOKED"
        || document["content_trust"] != "UNTRUSTED"
        || document["rendering"] != "NOT_PERFORMED"
    {
        return Ok(None);
    }
    let Some(bytes) = blob_bytes(&document["private"]["normalized"]) else {
        return Err(invalid("SLIDE_REPLY_NORMALIZED_MISMATCH"));
    };
    let normalized: Value =
        serde_json::from_slice(&bytes).map_err(|_| invalid("SLIDE_REPLY_NORMALIZED_INVALID"))?;
    if !normalized["elements"]
        .as_array()
        .is_some_and(|items| (1..=200).contains(&items.len()))
    {
        return Err(invalid("SLIDE_REPLY_ELEMENTS_OUT_OF_BOUNDS"));
    }
    Ok(Some(normalized))
}

fn scene_digest_id(prefix: &str, create_request_id: &str) -> String {
    format!("{prefix}_{}", &digest(create_request_id.as_bytes())[..32])
}

/// The complete scene object the donor normalize adapter receives. Core assigns
/// deterministic ids and the fixed slide viewport/theme; the reply only supplies
/// text elements and an optional solid background.
pub fn openmaic_slide_scene_request(
    create_request_id: &str,
    selection: &Value,
    reply: &Value,
) -> Result<Value, Error> {
    let elements = reply["elements"]
        .as_array()
        .ok_or(invalid("SLIDE_REPLY_ELEMENTS_OUT_OF_BOUNDS"))?;
    if !(1..=200).contains(&elements.len()) {
        return Err(invalid("SLIDE_REPLY_ELEMENTS_OUT_OF_BOUNDS"));
    }
    let mut seen = HashSet::new();
    let mut mounted = Vec::with_capacity(elements.len());
    for (index, element) in elements.iter().enumerate() {
        if element["type"].as_str() != Some("text")
            || !element["content"]
                .as_str()
                .is_some_and(|text| !text.trim().is_empty() && text.as_bytes().len() <= 16_000)
            || ["left", "top", "width", "height", "rotate"]
                .iter()
                .any(|key| !element[*key].is_number())
        {
            return Err(invalid("SLIDE_REPLY_ELEMENT_UNSUPPORTED"));
        }
        let id = element["id"]
            .as_str()
            .filter(|id| token(id))
            .map(str::to_owned)
            .unwrap_or_else(|| format!("el_{}", index + 1));
        if !seen.insert(id.clone()) {
            return Err(invalid("SLIDE_REPLY_ELEMENT_ID_CONFLICT"));
        }
        let mut mounted_element = json!({"id":id,"type":element["type"],
            "left":element["left"],"top":element["top"],"width":element["width"],
            "height":element["height"],"rotate":element["rotate"],
            "content":element["content"]});
        for key in ["defaultFontName", "defaultColor"] {
            if let Some(value) = element[key].as_str() {
                mounted_element[key] = json!(value);
            }
        }
        mounted.push(mounted_element);
    }
    let mut canvas = json!({
        "id":scene_digest_id("canvas", create_request_id),
        "viewportSize":1000,
        "viewportRatio":0.5625,
        "theme":{"backgroundColor":"#ffffff",
            "themeColors":["#5b9bd5","#ed7d31","#a5a5a5","#ffc000","#4472c4"],
            "fontColor":"#333333","fontName":"Microsoft YaHei"},
        "elements":mounted,
    });
    if reply["background"].is_object() {
        canvas["background"] = reply["background"].clone();
    }
    let title = selection["outline"]["title"]
        .as_str()
        .ok_or(invalid("OUTLINE_CANDIDATE_CONTENT_INVALID"))?;
    let scene = json!({
        "id":scene_digest_id("scene", create_request_id),
        "stageId":scene_digest_id("stage", create_request_id),
        "type":"slide","title":title,"order":selection["outline"]["order"],
        "content":{"type":"slide","canvas":canvas},
        "actions":[],
    });
    let bytes = serde_json::to_vec(&scene).map_err(|_| invalid("INVALID_SCENE_FRAME"))?;
    if bytes.len() > OPENMAIC_SLIDE_MAX_SCENE_BYTES {
        return Err(invalid("NORMALIZE_INPUT_EXCEEDS_BOUND"));
    }
    Ok(scene)
}

pub fn openmaic_slide_normalize_request(
    create_request_id: &str,
    scene: &Value,
) -> Result<Value, Error> {
    let bytes = serde_json::to_vec(scene).map_err(|_| invalid("INVALID_SCENE_FRAME"))?;
    Ok(json!({"schema":OPENMAIC_SLIDE_NORMALIZE_SCHEMA,
        "request_id":create_request_id,
        "scene_utf8_base64":base64::engine::general_purpose::STANDARD.encode(bytes)}))
}

/// The normalized scene the adapter declared, or `Ok(None)` for its named refusal.
pub fn openmaic_slide_normalized_scene(normalize_document: &Value) -> Result<Option<Value>, Error> {
    let document = normalize_document;
    if document["schema"] != OPENMAIC_SLIDE_NORMALIZE_RESULT_SCHEMA
        || document["provider"] != "openmaic"
        || document["provider_version"] != "1.3.0"
        || document["dsl_package_version"] != "0.12.0"
        || document["core_authorization"] != "NOT_ESTABLISHED"
        || document["rendering_authorized"] != false
    {
        return Err(invalid("SLIDE_NORMALIZE_RECEIPT_INVALID"));
    }
    if document["status"] != "CANDIDATE" {
        return Ok(None);
    }
    if document["source_verification"] != "VERIFIED_SELECTED_MEMBERS" {
        return Err(invalid("SLIDE_NORMALIZE_SOURCE_UNVERIFIED"));
    }
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(
            document["output_utf8_base64"]
                .as_str()
                .ok_or(invalid("SLIDE_NORMALIZE_OUTPUT_INVALID"))?,
        )
        .map_err(|_| invalid("SLIDE_NORMALIZE_OUTPUT_INVALID"))?;
    if document["output_bytes"].as_u64() != Some(bytes.len() as u64)
        || document["output_sha256"].as_str() != Some(digest(&bytes).as_str())
    {
        return Err(invalid("SLIDE_NORMALIZE_OUTPUT_MISMATCH"));
    }
    let scene: Value =
        serde_json::from_slice(&bytes).map_err(|_| invalid("SLIDE_NORMALIZE_OUTPUT_INVALID"))?;
    if !scene["content"]["canvas"]["elements"]
        .as_array()
        .is_some_and(|items| (1..=200).contains(&items.len()))
    {
        return Err(invalid("SLIDE_NORMALIZE_OUTPUT_INVALID"));
    }
    Ok(Some(scene))
}

/// The scene-build request for the already normalized content. It carries the
/// selected outline verbatim, the caller's source snapshot and the exact
/// normalized elements; `actions` stays empty because no action slice runs here.
pub fn openmaic_slide_scene_build_request(
    create_request_id: &str,
    selection: &Value,
    normalized: &Value,
    source: &Value,
) -> Result<Value, Error> {
    let canvas = &normalized["content"]["canvas"];
    let elements = canvas["elements"]
        .as_array()
        .ok_or(invalid("SLIDE_NORMALIZE_OUTPUT_INVALID"))?;
    if elements.is_empty() || elements.len() > 200 {
        return Err(invalid("SLIDE_NORMALIZE_OUTPUT_INVALID"));
    }
    let mut content = json!({"elements":elements});
    if canvas.get("background").is_some() {
        content["background"] = canvas["background"].clone();
    }
    let outline = &selection["outline"];
    Ok(json!({"schema":"archeaxis.openmaic-scene-build/v1",
        "request_id":create_request_id,"attempt":1,
        "source":source,
        "stage_id":scene_digest_id("stage", create_request_id),
        "scene_id":scene_digest_id("scene", create_request_id),
        "outline":{"id":outline["id"],"type":"slide","title":outline["title"],
            "description":outline["description"],"keyPoints":outline["keyPoints"],
            "order":outline["order"]},
        "content":content,
        "actions":[]}))
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
pub fn openmaic_slide_record(
    create_request_id: &str,
    request_sha256: &str,
    selection: &Value,
    prompt_binding: &Value,
    model_reply: &Value,
    reply: &Value,
    normalize: &Value,
) -> Value {
    let reply_record = stage_record(
        reply,
        &[
            ("status", "status"),
            ("reason", "reason"),
            ("reply_bytes", "private.reply.bytes"),
            ("reply_sha256", "private.reply.sha256"),
            ("normalized_bytes", "private.normalized.bytes"),
            ("normalized_sha256", "private.normalized.sha256"),
            ("semantic_changes", "private.semantic_changes"),
        ],
    );
    let normalize_record = stage_record(
        normalize,
        &[
            ("status", "status"),
            ("request_id", "request_id"),
            ("input_sha256", "input_sha256"),
            ("input_bytes", "input_bytes"),
            ("output_sha256", "output_sha256"),
            ("output_bytes", "output_bytes"),
            ("semantic_changes", "semantic_changes"),
        ],
    );
    json!({
        "schema":OPENMAIC_SLIDE_RECORD_SCHEMA,
        "create_request_id":create_request_id,
        "request_sha256":request_sha256,
        "outline_document_id":selection["document_id"],
        "outline_document_version":selection["version"],
        "outline_document_content_sha256":selection["content_sha256"],
        "outline_index":selection["index"],
        "outline_id":selection["outline"]["id"],
        "outline_order":selection["outline"]["order"],
        "generation_route":OPENMAIC_SLIDE_GENERATION_ROUTE,
        "model_call":"INVOKED",
        "model":model_reply["model"],
        "model_observed":model_reply["observed_model"],
        "model_reply_sha256":model_reply["content_sha256"],
        "model_reply_bytes":model_reply["content_bytes"],
        "model_finish_reason":model_reply["finish_reason"],
        "model_usage":model_reply["usage"],
        "prompt_binding":prompt_binding,
        "reply":reply_record,
        "normalize":normalize_record,
        "response_origin":OPENMAIC_SLIDE_RESPONSE_ORIGIN,
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "provider":"openmaic",
        "provider_version":"1.3.0",
        "generation_version":"0.3.28",
    })
}

/// The persisted candidate as a client reads it, with the Core-derived chain
/// metadata surfaced next to the existing scene projection and render reports.
fn slide_receipt(scene_receipt: Value) -> Value {
    let stored = &scene_receipt["document"]["editor_json"]["attrs"]
        [course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    json!({
        "schema":"archeaxis.openmaic-slide-persistence/v1",
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
        "reply":stored["reply"],
        "normalize":stored["normalize"],
        "response_origin":stored["response_origin"],
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "contract_version":scene_receipt["contract_version"],
        "projection":scene_receipt["projection"],
        "render":scene_receipt["render"],
    })
}

fn slide_existing(
    conn: &Connection,
    create_request_id: &str,
    request_sha256: &str,
    selection: &Value,
) -> Result<Option<Value>, Error> {
    let Some(receipt) = course::openmaic_scene_candidate(conn, create_request_id)? else {
        return Ok(None);
    };
    let stored = &receipt["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    if stored["schema"].as_str() != Some(OPENMAIC_SLIDE_RECORD_SCHEMA)
        || stored["create_request_id"].as_str() != Some(create_request_id)
        || stored["request_sha256"].as_str() != Some(request_sha256)
        || stored["outline_document_id"] != selection["document_id"]
        || stored["outline_index"] != selection["index"]
    {
        return Err(invalid("SLIDE_REQUEST_CONFLICT"));
    }
    Ok(Some(slide_receipt(receipt)))
}

/// Captured by Core before dispatch and checked again when admitting the result.
#[derive(Clone)]
pub struct OpenMaicSlidePending {
    restore_epoch: Option<String>,
    workspace_id: String,
    request_sha256: String,
    create_request_id: String,
    selection: Value,
}

#[derive(Clone)]
pub enum OpenMaicSlidePreparation {
    Existing(Value),
    Pending(OpenMaicSlidePending),
}

/// Check a retry and capture the outline version, source snapshot, workspace and
/// restore epoch in one Core transaction before any stage runs.
pub fn prepare_openmaic_slide_candidate(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    selection: &Value,
) -> Result<OpenMaicSlidePreparation, Error> {
    if openmaic_slide_refusal(request).is_some()
        || request["create_request_id"].as_str() != Some(create_request_id)
    {
        return Err(invalid("INVALID_SLIDE_REQUEST"));
    }
    if selection["outline"]["type"].as_str() != Some("slide") {
        return Err(invalid("UNSUPPORTED_OUTLINE_TYPE"));
    }
    let material: Snapshot = serde_json::from_value(request["source"].clone())
        .map_err(|_| invalid("INVALID_SOURCE_SNAPSHOT"))?;
    let request_sha256 = openmaic_slide_request_sha256(request, selection);
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
    if let Some(receipt) = slide_existing(&tx, create_request_id, &request_sha256, selection)? {
        tx.commit()?;
        return Ok(OpenMaicSlidePreparation::Existing(receipt));
    }
    let restore_epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC slide workspace identity unavailable"))?;
    tx.commit()?;
    Ok(OpenMaicSlidePreparation::Pending(OpenMaicSlidePending {
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
pub struct OpenMaicSlideGeneration {
    pub scene_request: Value,
    pub record: Value,
}

/// Persist the existing scene candidate together with the Core-derived chain
/// record in one transaction. The worker document is re-checked against the exact
/// scene-build frame Core sent by `course::commit_openmaic_scene_with`.
pub fn commit_openmaic_slide_candidate(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    pending: &OpenMaicSlidePending,
    scene_pending: &course::OpenMaicPending,
    worker_document: &Value,
    generation: &OpenMaicSlideGeneration,
) -> Result<Value, Error> {
    if create_request_id != pending.create_request_id.as_str()
        || openmaic_slide_request_sha256(request, &pending.selection) != pending.request_sha256
        || generation.record["schema"].as_str() != Some(OPENMAIC_SLIDE_RECORD_SCHEMA)
        || generation.record["create_request_id"].as_str() != Some(create_request_id)
        || generation.record["request_sha256"].as_str() != Some(pending.request_sha256.as_str())
        || generation.record["outline_document_id"] != pending.selection["document_id"]
        || generation.record["outline_index"] != pending.selection["index"]
    {
        return Err(invalid("SLIDE_REQUEST_CHANGED"));
    }
    // The scene writer repeats its own epoch/workspace check inside its write
    // transaction; this recheck keeps the earlier slide admission meaningful too.
    let epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(conn)?;
    let workspace_id = crate::ui_state::existing_workspace_id(conn)
        .map_err(|_| invalid("OpenMAIC slide workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(invalid("SLIDE_WORKSPACE_CHANGED"));
    }
    let receipt = course::commit_openmaic_scene_with(
        conn,
        create_request_id,
        &generation.scene_request,
        scene_pending,
        worker_document,
        Some(&generation.record),
    )?;
    Ok(slide_receipt(receipt))
}

/// Read the candidate a repeated request already owns without running a stage.
pub fn read_openmaic_slide_candidate(
    conn: &Connection,
    create_request_id: &str,
    request: &Value,
    selection: &Value,
) -> Result<Option<Value>, Error> {
    let Some(receipt) = course::openmaic_scene_candidate(conn, create_request_id)? else {
        return Ok(None);
    };
    let stored = &receipt["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    if stored["schema"].as_str() != Some(OPENMAIC_SLIDE_RECORD_SCHEMA) {
        return Err(invalid("SLIDE_REQUEST_CONFLICT"));
    }
    let request_sha256 = openmaic_slide_request_sha256(request, selection);
    if stored["create_request_id"].as_str() != Some(create_request_id)
        || stored["request_sha256"].as_str() != Some(request_sha256.as_str())
        || stored["outline_document_id"] != selection["document_id"]
        || stored["outline_index"] != selection["index"]
    {
        return Err(invalid("SLIDE_REQUEST_CONFLICT"));
    }
    Ok(Some(slide_receipt(receipt)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unknown_request_versions_and_bad_sources_are_named() {
        let base = json!({"schema":OPENMAIC_SLIDE_REQUEST_SCHEMA,
            "create_request_id":"client_1","outline_document_id":"doc_req_1",
            "outline_index":0,
            "source":{"document_id":"doc_req_2","version":1,"content_sha256":"0".repeat(64)},
            "model":null});
        assert_eq!(openmaic_slide_refusal(&base), None);
        assert_eq!(
            openmaic_slide_refusal(&json!({})).unwrap()["reason"],
            "UNSUPPORTED_REQUEST_VERSION"
        );
        let mut future = base.clone();
        future["schema"] = json!("archeaxis.openmaic-slide-candidate-generate/v2");
        assert_eq!(
            openmaic_slide_refusal(&future).unwrap()["reason"],
            "UNSUPPORTED_REQUEST_VERSION"
        );
        let mut extra = base.clone();
        extra["remark"] = json!("extra");
        assert_eq!(
            openmaic_slide_refusal(&extra).unwrap()["reason"],
            "UNEXPECTED_REQUEST_FIELDS"
        );
        let mut index = base.clone();
        index["outline_index"] = json!(30);
        assert_eq!(
            openmaic_slide_refusal(&index).unwrap()["reason"],
            "OUTLINE_INDEX_OUT_OF_RANGE"
        );
        let mut source = base.clone();
        source["source"]["document_id"] = json!("bad id");
        assert_eq!(
            openmaic_slide_refusal(&source).unwrap()["reason"],
            "INVALID_SOURCE_SNAPSHOT"
        );
        let mut model = base.clone();
        model["model"] = json!("bad\nmodel");
        assert_eq!(
            openmaic_slide_refusal(&model).unwrap()["reason"],
            "INVALID_MODEL_SELECTION"
        );
    }

    #[test]
    fn a_prompt_frame_keeps_the_outline_bounds_and_the_record_keeps_only_digests() {
        let selection = json!({"document_id":"doc_req_1","version":1,
            "content_sha256":"0".repeat(64),"index":0,
            "outline":{"id":"o1","type":"slide","title":"Title","description":"Body",
                "keyPoints":["One"],"order":1},
            "language_directive":"Use Chinese."});
        let request = openmaic_slide_prompt_request(&selection).unwrap();
        let prompt = base64::engine::general_purpose::STANDARD
            .decode(request["request_utf8_base64"].as_str().unwrap())
            .unwrap();
        let decoded: Value = serde_json::from_slice(&prompt).unwrap();
        assert_eq!(decoded["outline"]["key_points"], json!(["One"]));
        assert_eq!(decoded["language_directive"], "Use Chinese.");
        let mut long = selection.clone();
        long["outline"]["keyPoints"] = json!(["x".repeat(513)]);
        assert!(matches!(
            openmaic_slide_prompt_request(&long),
            Err(Error::Invalid("OUTLINE_KEY_POINTS_OUT_OF_PROMPT_BOUNDS"))
        ));
        let private = json!({"system":"system text","user":"user text",
            "system_sha256":digest(b"system text"),"user_sha256":digest(b"user text")});
        let document = json!({"schema":OPENMAIC_SLIDE_PROMPT_RESULT_SCHEMA,"status":"BUILT",
            "scope":"CALLER_SUPPLIED_UNVERIFIED","operation":"UPSTREAM_SLIDE_PROMPT_ONLY",
            "model_call":"NOT_INVOKED","full_generation":"NOT_PERFORMED",
            "core_authorization":"NOT_ESTABLISHED","private":private});
        let binding = openmaic_slide_prompt_binding(&document).unwrap();
        let record = openmaic_slide_prompt_record(&binding);
        assert_eq!(record["system_sha256"], digest(b"system text"));
        assert!(record.get("system").is_none());
    }

    #[test]
    fn a_non_candidate_reply_is_not_turned_into_content() {
        let quarantined = json!({"schema":OPENMAIC_SLIDE_REPLY_RESULT_SCHEMA,
            "status":"QUARANTINED","reason":"NONEXACT_OR_AMBIGUOUS_JSON"});
        assert!(
            openmaic_slide_reply_candidate(&quarantined)
                .unwrap()
                .is_none()
        );
        let rejected = json!({"schema":"other/v1","status":"REJECTED"});
        assert!(openmaic_slide_reply_candidate(&rejected).is_err());
    }
}
