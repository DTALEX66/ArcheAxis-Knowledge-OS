//! Outline-to-interactive candidates: Core reads one persisted `interactive`
//! outline, captures the donor widget prompt, calls the declared local model,
//! extracts and post-processes the model HTML through the interactive normalize
//! adapter and persists only the resulting scene candidate. Every stage keeps its
//! own receipt; a failure writes nothing.
//!
//! This module contains no process launch and no network access. It builds the
//! exact frames Core sends, re-checks what the workers returned and derives the
//! metadata Core stores beside the existing scene candidate Document. It does not
//! execute, sanitize or authorize the generated HTML.
use crate::course;
use crate::document::{self, Error};
use crate::openmaic_outline;
use crate::provider_material_grant::Snapshot;
use base64::Engine;
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

pub const OPENMAIC_INTERACTIVE_REQUEST_SCHEMA: &str =
    "archeaxis.openmaic-interactive-candidate-generate/v1";
/// The Core-derived record stored inside the existing scene candidate attrs.
pub const OPENMAIC_INTERACTIVE_RECORD_SCHEMA: &str = "archeaxis.openmaic-interactive-candidate/v1";
pub const OPENMAIC_INTERACTIVE_PROMPT_SCHEMA: &str = "archeaxis.openmaic-interactive-prompt/v1";
pub const OPENMAIC_INTERACTIVE_PROMPT_RESULT_SCHEMA: &str =
    "archeaxis.openmaic-interactive-prompt-result/v1";
pub const OPENMAIC_INTERACTIVE_PROMPT_BINDING_SCHEMA: &str =
    "archeaxis.openmaic-interactive-prompt-binding/v1";
/// The normalize adapter uses one schema for its request and its result.
pub const OPENMAIC_INTERACTIVE_NORMALIZE_SCHEMA: &str =
    "archeaxis.openmaic-interactive-normalize/v1";
pub const OPENMAIC_INTERACTIVE_GENERATION_ROUTE: &str = "outline_interactive_local_model";
pub const OPENMAIC_INTERACTIVE_RESPONSE_ORIGIN: &str = "LOCAL_MODEL_UNVERIFIED";
/// The ordinary widgets the prompt and normalize adapters admit.
const OPENMAIC_WIDGET_TYPES: [&str; 5] =
    ["simulation", "diagram", "code", "game", "visualization3d"];
/// The prompt worker's own request budget: 16,384 bytes inside a 32,768-byte
/// frame. Core refuses an over-budget request itself instead of sending it.
const OPENMAIC_INTERACTIVE_MAX_PROMPT_REQUEST: usize = 16_384;
/// The model reply budget the normalize worker accepts (131,072) and the HTML
/// it extracts (65,536) and emits (98,304) after post-processing.
const OPENMAIC_INTERACTIVE_MAX_REPLY_BYTES: usize = 131_072;
const OPENMAIC_INTERACTIVE_MAX_HTML_BYTES: usize = 65_536;
const OPENMAIC_INTERACTIVE_MAX_OUTPUT_BYTES: usize = 98_304;
const OPENMAIC_INTERACTIVE_REQUEST_FIELDS: [&str; 6] = [
    "schema",
    "create_request_id",
    "outline_document_id",
    "outline_index",
    "source",
    "model",
];
const OPENMAIC_INTERACTIVE_EXTRACTIONS: [&str; 3] =
    ["COMPLETE_DOCUMENT", "FENCED_BLOCK", "TRIMMED_DOCUMENT"];

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

/// The normalize adapter caps its request id at 64 characters, so Core passes a
/// deterministic derived id instead of the caller's create request ID.
pub fn openmaic_interactive_normalize_request_id(create_request_id: &str) -> String {
    format!("int_{}", &digest(create_request_id.as_bytes())[..32])
}

/// Name everything this route refuses before Core reads an outline or captures a
/// prompt. `None` means the request may proceed; every later check repeats.
pub fn openmaic_interactive_refusal(request: &Value) -> Option<Value> {
    let Some(object) = request.as_object() else {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_SHAPE","declared":"not an object",
            "supported":[OPENMAIC_INTERACTIVE_REQUEST_SCHEMA]}),
        );
    };
    if object.get("schema").and_then(Value::as_str) != Some(OPENMAIC_INTERACTIVE_REQUEST_SCHEMA) {
        return Some(json!({"reason":"UNSUPPORTED_REQUEST_VERSION",
            "declared":object.get("schema").cloned().unwrap_or(Value::Null),
            "supported":[OPENMAIC_INTERACTIVE_REQUEST_SCHEMA]}));
    }
    if object.len() != OPENMAIC_INTERACTIVE_REQUEST_FIELDS.len()
        || OPENMAIC_INTERACTIVE_REQUEST_FIELDS
            .iter()
            .any(|key| !object.contains_key(*key))
    {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_FIELDS","declared":object.len(),
            "supported":OPENMAIC_INTERACTIVE_REQUEST_FIELDS.len()}),
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
        .is_ok_and(|snapshot| crate::provider_material_grant::valid_snapshot_shape(&snapshot));
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
pub fn openmaic_interactive_request_sha256(request: &Value, selection: &Value) -> String {
    digest(format!("{request}\n{selection}").as_bytes())
}

fn required_text(value: &Value, max: usize) -> bool {
    value
        .as_str()
        .is_some_and(|text| !text.trim().is_empty() && text.len() <= max && !text.contains('\0'))
}

/// The widget selection one interactive outline decided. Core reads it back from
/// the persisted outline and never asks a model for it again.
pub fn openmaic_interactive_widget(selection: &Value) -> Result<(String, Value), Error> {
    let outline = &selection["outline"];
    if outline["type"].as_str() != Some("interactive") {
        return Err(invalid("UNSUPPORTED_OUTLINE_TYPE"));
    }
    let widget = outline["widgetType"]
        .as_str()
        .filter(|widget| OPENMAIC_WIDGET_TYPES.contains(widget))
        .ok_or(invalid("INTERACTIVE_OUTLINE_WIDGET_INVALID"))?;
    // The prompt adapter accepts only the fields that widget declares; the
    // outline admission already bounded them, this re-check keeps the frame
    // meaningful even if a future writer stored something else.
    let outline_fields: &[&str] = match widget {
        "simulation" => &["concept", "keyVariables"],
        "diagram" => &["diagramType", "nodeCount", "nodes"],
        "code" => &["language"],
        "game" => &["gameType"],
        _ => &["visualizationType", "objects", "interactions"],
    };
    let fields = outline["widgetOutline"]
        .as_object()
        .filter(|fields| fields.len() <= outline_fields.len())
        .filter(|fields| {
            fields.iter().all(|(key, value)| {
                outline_fields.contains(&key.as_str()) && widget_field_ok(key, value)
            })
        })
        .ok_or(invalid("INTERACTIVE_OUTLINE_WIDGET_INVALID"))?;
    // Map the donor outline (camelCase) names to the prompt adapter's own frame.
    let mut mapped = serde_json::Map::new();
    for (key, value) in fields {
        let name = match key.as_str() {
            "concept" => "concept",
            "keyVariables" => "key_variables",
            "diagramType" => "diagram_type",
            "nodeCount" => "node_count",
            "nodes" => "nodes",
            "language" => "language",
            "gameType" => "game_type",
            "visualizationType" => "visualization_type",
            "objects" => "objects",
            _ => "interactions",
        };
        mapped.insert(name.to_owned(), value.clone());
    }
    Ok((widget.to_owned(), Value::Object(mapped)))
}

fn widget_field_ok(key: &str, value: &Value) -> bool {
    if key == "nodeCount" {
        return value.as_u64().is_some_and(|count| count <= 200);
    }
    if ["keyVariables", "nodes", "objects", "interactions"].contains(&key) {
        return value.as_array().is_some_and(|items| {
            items.len() <= 64
                && items
                    .iter()
                    .all(|item| item.as_str().is_some_and(|text| text.len() <= 512))
        });
    }
    value.as_str().is_some_and(|text| text.len() <= 512)
}

/// The donor widget-prompt frame. It carries the outline title, description and
/// key points, the language directive the outline candidate recorded and the
/// widget selection; Core never asks a model for those again.
pub fn openmaic_interactive_prompt_request(selection: &Value) -> Result<Value, Error> {
    let outline = &selection["outline"];
    let title = outline["title"]
        .as_str()
        .filter(|value| !value.trim().is_empty() && value.len() <= 1_024 && !value.contains('\0'))
        .ok_or(invalid("INTERACTIVE_OUTLINE_TITLE_OUT_OF_BOUNDS"))?;
    let description = outline["description"]
        .as_str()
        .filter(|value| value.len() <= 6_000)
        .ok_or(invalid("INTERACTIVE_OUTLINE_DESCRIPTION_OUT_OF_BOUNDS"))?;
    let key_points = outline["keyPoints"]
        .as_array()
        .ok_or(invalid("INTERACTIVE_OUTLINE_KEY_POINTS_OUT_OF_BOUNDS"))?;
    if key_points.len() > 20 || key_points.iter().any(|point| !required_text(point, 512)) {
        return Err(invalid("INTERACTIVE_OUTLINE_KEY_POINTS_OUT_OF_BOUNDS"));
    }
    let (widget, widget_outline) = openmaic_interactive_widget(selection)?;
    let language_directive = selection["language_directive"].as_str().unwrap_or("");
    if language_directive.len() > 2_000 {
        return Err(invalid(
            "INTERACTIVE_OUTLINE_LANGUAGE_DIRECTIVE_OUT_OF_BOUNDS",
        ));
    }
    let prompt = json!({
        "outline":{"title":title,"description":description,"key_points":key_points,
            "widget_type":widget,"widget_outline":widget_outline},
        "language_directive":language_directive,
    });
    let bytes = serde_json::to_vec(&prompt).map_err(|_| invalid("INVALID_PROMPT_FRAME"))?;
    if bytes.len() > OPENMAIC_INTERACTIVE_MAX_PROMPT_REQUEST {
        return Err(invalid("INTERACTIVE_PROMPT_REQUEST_EXCEEDS_BOUND"));
    }
    Ok(json!({"schema":OPENMAIC_INTERACTIVE_PROMPT_SCHEMA,
        "request_utf8_base64":base64::engine::general_purpose::STANDARD.encode(bytes),
        "include_private":true}))
}

/// The captured prompts plus their identities. The prompt text is kept in memory
/// only long enough to call the model; the stored record keeps the digests.
pub fn openmaic_interactive_prompt_binding(
    prompt_document: &Value,
    widget: &str,
) -> Result<Value, Error> {
    let fixed = prompt_document["schema"] == OPENMAIC_INTERACTIVE_PROMPT_RESULT_SCHEMA
        && prompt_document["status"] == "BUILT"
        && prompt_document["scope"] == "CALLER_SUPPLIED_UNVERIFIED"
        && prompt_document["operation"] == "UPSTREAM_INTERACTIVE_PROMPT_ONLY"
        && prompt_document["model_call"] == "NOT_INVOKED"
        && prompt_document["html_output"] == "NOT_PRODUCED"
        && prompt_document["full_generation"] == "NOT_PERFORMED"
        && prompt_document["core_authorization"] == "NOT_ESTABLISHED"
        && prompt_document["widget_type"] == widget;
    if !fixed {
        return Err(invalid("INTERACTIVE_PROMPT_RECEIPT_INVALID"));
    }
    let private = &prompt_document["private"];
    let Some(system) = private["system"].as_str() else {
        return Err(invalid("INTERACTIVE_PROMPT_RECEIPT_INVALID"));
    };
    let Some(user) = private["user"].as_str() else {
        return Err(invalid("INTERACTIVE_PROMPT_RECEIPT_INVALID"));
    };
    if system.len() > 65_536
        || user.len() > 32_768
        || private["system_sha256"].as_str() != Some(digest(system.as_bytes()).as_str())
        || private["user_sha256"].as_str() != Some(digest(user.as_bytes()).as_str())
        || !hex_digest(&private["system_sha256"])
        || !hex_digest(&private["user_sha256"])
    {
        return Err(invalid("INTERACTIVE_PROMPT_BINDING_OUT_OF_BOUNDS"));
    }
    Ok(json!({"schema":OPENMAIC_INTERACTIVE_PROMPT_BINDING_SCHEMA,
        "widget_type":widget,
        "system":system,"user":user,
        "system_bytes":system.len(),"user_bytes":user.len(),
        "system_sha256":private["system_sha256"],"user_sha256":private["user_sha256"]}))
}

/// The normalize frame: one model reply and the widget whose prompt produced it.
/// The reply is byte-identical to the model text; Core never trims or repairs it.
pub fn openmaic_interactive_normalize_request(
    create_request_id: &str,
    widget: &str,
    reply: &str,
) -> Result<Value, Error> {
    if !OPENMAIC_WIDGET_TYPES.contains(&widget)
        || reply.is_empty()
        || reply.len() > OPENMAIC_INTERACTIVE_MAX_REPLY_BYTES
    {
        return Err(invalid("INTERACTIVE_REPLY_EXCEEDS_BOUND"));
    }
    Ok(json!({"schema":OPENMAIC_INTERACTIVE_NORMALIZE_SCHEMA,
        "request_id":openmaic_interactive_normalize_request_id(create_request_id),
        "widget_type":widget,
        "reply_utf8_base64":base64::engine::general_purpose::STANDARD.encode(reply.as_bytes())}))
}

/// The admitted normalize result, or `Ok(None)` for its named refusal. The HTML
/// is returned unchanged; this slice never sanitizes or executes it. The reply
/// bytes Core sent are re-checked so a receipt can only describe that reply.
pub fn openmaic_interactive_normalized(
    normalize_document: &Value,
    expected_request_id: &str,
    widget: &str,
    reply: &str,
) -> Result<Option<Value>, Error> {
    let document = normalize_document;
    let envelope = document["schema"] == OPENMAIC_INTERACTIVE_NORMALIZE_SCHEMA
        && document["scope"] == "CALLER_SUPPLIED_UNVERIFIED"
        && document["model_call"] == "NOT_INVOKED"
        && document["rendering_authorized"] != true
        && document["security_sanitizer"] == false
        && document["core_authorization"] == "NOT_ESTABLISHED"
        && document["script_validation"] == "CLASSIC_INLINE_COMPILED_NOT_EXECUTED";
    if !envelope {
        return Err(invalid("INTERACTIVE_NORMALIZE_RECEIPT_INVALID"));
    }
    if document["status"] != "OBSERVED_CANDIDATE" {
        return Ok(None);
    }
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(
            document["output_utf8_base64"]
                .as_str()
                .ok_or(invalid("INTERACTIVE_NORMALIZE_OUTPUT_INVALID"))?,
        )
        .map_err(|_| invalid("INTERACTIVE_NORMALIZE_OUTPUT_INVALID"))?;
    if document["request_id"].as_str() != Some(expected_request_id)
        || document["widget_type"].as_str() != Some(widget)
        || !document["extraction_strategy"]
            .as_str()
            .is_some_and(|strategy| OPENMAIC_INTERACTIVE_EXTRACTIONS.contains(&strategy))
        || document["katex_injected"].as_bool().is_none()
        || document["input_bytes"].as_u64() != Some(reply.len() as u64)
        || document["input_sha256"].as_str() != Some(digest(reply.as_bytes()).as_str())
        || document["extracted_bytes"]
            .as_u64()
            .is_none_or(|bytes| bytes > OPENMAIC_INTERACTIVE_MAX_HTML_BYTES as u64)
        || !hex_digest(&document["extracted_sha256"])
        || document["output_bytes"].as_u64() != Some(bytes.len() as u64)
        || document["output_sha256"].as_str() != Some(digest(&bytes).as_str())
        || bytes.len() > OPENMAIC_INTERACTIVE_MAX_OUTPUT_BYTES
        || std::str::from_utf8(&bytes).is_err()
    {
        return Err(invalid("INTERACTIVE_NORMALIZE_OUTPUT_MISMATCH"));
    }
    let html =
        std::str::from_utf8(&bytes).map_err(|_| invalid("INTERACTIVE_NORMALIZE_OUTPUT_INVALID"))?;
    if html.trim().is_empty() || html.len() > OPENMAIC_INTERACTIVE_MAX_HTML_BYTES {
        return Err(invalid("INTERACTIVE_NORMALIZE_OUTPUT_INVALID"));
    }
    Ok(Some(json!({"widgetType":widget,"html":html,
        "extraction_strategy":document["extraction_strategy"],
        "katex_injected":document["katex_injected"],
        "output_sha256":document["output_sha256"],
        "output_bytes":document["output_bytes"]})))
}

fn scene_digest_id(prefix: &str, create_request_id: &str) -> String {
    format!("{prefix}_{}", &digest(create_request_id.as_bytes())[..32])
}

/// The scene-build request for the admitted HTML. It carries the selected
/// outline verbatim, the caller's source snapshot and the exact normalized HTML;
/// `actions` stays empty because no action slice runs here.
pub fn openmaic_interactive_scene_build_request(
    create_request_id: &str,
    selection: &Value,
    normalized: &Value,
    source: &Value,
) -> Result<Value, Error> {
    let html = normalized["html"]
        .as_str()
        .filter(|html| !html.trim().is_empty() && html.len() <= 200_000)
        .ok_or(invalid("INTERACTIVE_NORMALIZE_OUTPUT_INVALID"))?;
    let widget = normalized["widgetType"]
        .as_str()
        .filter(|widget| OPENMAIC_WIDGET_TYPES.contains(widget))
        .ok_or(invalid("INTERACTIVE_NORMALIZE_OUTPUT_INVALID"))?;
    let outline = &selection["outline"];
    Ok(json!({"schema":"archeaxis.openmaic-scene-build/v1",
        "request_id":create_request_id,"attempt":1,
        "source":source,
        "stage_id":scene_digest_id("stage", create_request_id),
        "scene_id":scene_digest_id("scene", create_request_id),
        "outline":{"id":outline["id"],"type":"interactive","title":outline["title"],
            "description":outline["description"],"keyPoints":outline["keyPoints"],
            "order":outline["order"]},
        "content":{"html":html,"widgetType":widget},
        "actions":[]}))
}

fn stage_record(document: &Value, keys: &[(&str, &str)]) -> Value {
    let mut record = serde_json::Map::new();
    for (field, path) in keys {
        let mut value = document;
        let mut found = true;
        for part in path.split('.') {
            match value.get(part) {
                Some(next) => value = next,
                None => {
                    found = false;
                    break;
                }
            }
        }
        record.insert(
            (*field).to_owned(),
            if found { value.clone() } else { Value::Null },
        );
    }
    Value::Object(record)
}

/// The Core-derived record stored beside the scene candidate. It names every
/// stage's declared identity without copying prompt text, model text or HTML.
pub fn openmaic_interactive_record(
    create_request_id: &str,
    request_sha256: &str,
    selection: &Value,
    prompt_binding: &Value,
    model_reply: &Value,
    normalize: &Value,
) -> Value {
    let normalize_record = stage_record(
        normalize,
        &[
            ("status", "status"),
            ("request_id", "request_id"),
            ("widget_type", "widget_type"),
            ("extraction_strategy", "extraction_strategy"),
            ("katex_injected", "katex_injected"),
            ("input_sha256", "input_sha256"),
            ("input_bytes", "input_bytes"),
            ("extracted_sha256", "extracted_sha256"),
            ("extracted_bytes", "extracted_bytes"),
            ("output_sha256", "output_sha256"),
            ("output_bytes", "output_bytes"),
        ],
    );
    json!({
        "schema":OPENMAIC_INTERACTIVE_RECORD_SCHEMA,
        "create_request_id":create_request_id,
        "request_sha256":request_sha256,
        "outline_document_id":selection["document_id"],
        "outline_document_version":selection["version"],
        "outline_document_content_sha256":selection["content_sha256"],
        "outline_index":selection["index"],
        "outline_id":selection["outline"]["id"],
        "outline_order":selection["outline"]["order"],
        "generation_route":OPENMAIC_INTERACTIVE_GENERATION_ROUTE,
        "model_call":"INVOKED",
        "model":model_reply["model"],
        "model_observed":model_reply["observed_model"],
        "model_reply_sha256":model_reply["content_sha256"],
        "model_reply_bytes":model_reply["content_bytes"],
        "model_finish_reason":model_reply["finish_reason"],
        "model_usage":model_reply["usage"],
        "widget_type":prompt_binding["widget_type"],
        "prompt_binding":{"schema":prompt_binding["schema"],
            "widget_type":prompt_binding["widget_type"],
            "system_bytes":prompt_binding["system_bytes"],
            "user_bytes":prompt_binding["user_bytes"],
            "system_sha256":prompt_binding["system_sha256"],
            "user_sha256":prompt_binding["user_sha256"]},
        "normalize":normalize_record,
        "response_origin":OPENMAIC_INTERACTIVE_RESPONSE_ORIGIN,
        "html_execution":"NOT_PERFORMED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "provider":"openmaic",
        "provider_version":"1.3.0",
        "generation_version":"0.3.28",
    })
}

fn interactive_receipt(scene_receipt: Value) -> Value {
    let stored = &scene_receipt["document"]["editor_json"]["attrs"]
        [course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    json!({
        "schema":"archeaxis.openmaic-interactive-persistence/v1",
        "document":scene_receipt["document"],
        "candidate_document_status":scene_receipt["candidate_document_status"],
        "source_snapshot_status":scene_receipt["source_snapshot_status"],
        "generation_route":stored["generation_route"],
        "model_call":stored["model_call"],
        "model":stored["model"],
        "model_observed":stored["model_observed"],
        "model_reply_sha256":stored["model_reply_sha256"],
        "model_finish_reason":stored["model_finish_reason"],
        "widget_type":stored["widget_type"],
        "prompt_binding":stored["prompt_binding"],
        "outline_document_id":stored["outline_document_id"],
        "outline_index":stored["outline_index"],
        "outline_id":stored["outline_id"],
        "normalize":stored["normalize"],
        "response_origin":stored["response_origin"],
        "html_execution":"NOT_PERFORMED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "contract_version":scene_receipt["contract_version"],
        "projection":scene_receipt["projection"],
        "render":scene_receipt["render"],
    })
}

fn interactive_existing(
    conn: &Connection,
    create_request_id: &str,
    request_sha256: &str,
    selection: &Value,
) -> Result<Option<Value>, Error> {
    let Some(receipt) = course::openmaic_scene_candidate(conn, create_request_id)? else {
        return Ok(None);
    };
    let stored = &receipt["document"]["editor_json"]["attrs"][course::OPENMAIC_SCENE_NAMESPACE]["derived_metadata"];
    if stored["schema"].as_str() != Some(OPENMAIC_INTERACTIVE_RECORD_SCHEMA)
        || stored["create_request_id"].as_str() != Some(create_request_id)
        || stored["request_sha256"].as_str() != Some(request_sha256)
        || stored["outline_document_id"] != selection["document_id"]
        || stored["outline_index"] != selection["index"]
    {
        return Err(invalid("INTERACTIVE_REQUEST_CONFLICT"));
    }
    Ok(Some(interactive_receipt(receipt)))
}

/// Captured by Core before dispatch and checked again when admitting the result.
#[derive(Clone)]
pub struct OpenMaicInteractivePending {
    restore_epoch: Option<String>,
    workspace_id: String,
    request_sha256: String,
    create_request_id: String,
    selection: Value,
}

#[derive(Clone)]
pub enum OpenMaicInteractivePreparation {
    Existing(Value),
    Pending(OpenMaicInteractivePending),
}

/// Check a retry and capture the outline version, source snapshot, workspace and
/// restore epoch in one Core transaction before any stage runs.
pub fn prepare_openmaic_interactive_candidate(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    selection: &Value,
) -> Result<OpenMaicInteractivePreparation, Error> {
    if openmaic_interactive_refusal(request).is_some()
        || request["create_request_id"].as_str() != Some(create_request_id)
    {
        return Err(invalid("INVALID_INTERACTIVE_REQUEST"));
    }
    if selection["outline"]["type"].as_str() != Some("interactive") {
        return Err(invalid("UNSUPPORTED_OUTLINE_TYPE"));
    }
    let material: Snapshot = serde_json::from_value(request["source"].clone())
        .map_err(|_| invalid("INVALID_SOURCE_SNAPSHOT"))?;
    let request_sha256 = openmaic_interactive_request_sha256(request, selection);
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
    if let Some(receipt) = interactive_existing(&tx, create_request_id, &request_sha256, selection)?
    {
        tx.commit()?;
        return Ok(OpenMaicInteractivePreparation::Existing(receipt));
    }
    let restore_epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC interactive workspace identity unavailable"))?;
    tx.commit()?;
    Ok(OpenMaicInteractivePreparation::Pending(
        OpenMaicInteractivePending {
            restore_epoch,
            workspace_id,
            request_sha256,
            create_request_id: create_request_id.to_owned(),
            selection: selection.clone(),
        },
    ))
}

/// The admitted chain. Core stores the exact stage receipts beside the scene;
/// nothing here can turn a non-candidate into content.
#[derive(Clone)]
pub struct OpenMaicInteractiveGeneration {
    pub scene_request: Value,
    pub record: Value,
}

/// Persist the existing scene candidate together with the Core-derived chain
/// record in one transaction. The worker document is re-checked against the exact
/// scene-build frame Core sent by `course::commit_openmaic_scene_with`.
pub fn commit_openmaic_interactive_candidate(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    pending: &OpenMaicInteractivePending,
    scene_pending: &course::OpenMaicPending,
    worker_document: &Value,
    generation: &OpenMaicInteractiveGeneration,
) -> Result<Value, Error> {
    if create_request_id != pending.create_request_id.as_str()
        || openmaic_interactive_request_sha256(request, &pending.selection)
            != pending.request_sha256
        || generation.record["schema"].as_str() != Some(OPENMAIC_INTERACTIVE_RECORD_SCHEMA)
        || generation.record["create_request_id"].as_str() != Some(create_request_id)
        || generation.record["request_sha256"].as_str() != Some(pending.request_sha256.as_str())
        || generation.record["outline_document_id"] != pending.selection["document_id"]
        || generation.record["outline_index"] != pending.selection["index"]
    {
        return Err(invalid("INTERACTIVE_REQUEST_CHANGED"));
    }
    let epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(conn)?;
    let workspace_id = crate::ui_state::existing_workspace_id(conn)
        .map_err(|_| invalid("OpenMAIC interactive workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(invalid("INTERACTIVE_WORKSPACE_CHANGED"));
    }
    let receipt = course::commit_openmaic_scene_with(
        conn,
        create_request_id,
        &generation.scene_request,
        scene_pending,
        worker_document,
        Some(&generation.record),
    )?;
    Ok(interactive_receipt(receipt))
}

/// The local-model request reuses the outline route's own model frame: only the
/// two captured prompts, an optional model selection and one bounded budget.
pub fn openmaic_interactive_model_request(binding: &Value, model: &Value) -> Value {
    openmaic_outline::openmaic_outline_model_request(binding, model)
}
