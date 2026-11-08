//! Local-model generation of interactive course outlines.
//!
//! Core captures the donor `interactive-outlines` prompt through the private
//! adapter, calls the declared local model, replays the reply through the same
//! adapter and persists one inert outline candidate Document. No scene content,
//! HTML or rendering authorization is produced here. Every stage keeps its own
//! receipt; a failure writes nothing.
use crate::document::Error;
use crate::openmaic_outline;
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

/// The bounded generate contract the HTTP caller may send.
pub const OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_SCHEMA: &str =
    "archeaxis.openmaic-interactive-outline-generate/v1";
/// The adapter request frame (capture or replay).
pub const OPENMAIC_INTERACTIVE_OUTLINE_PROMPT_SCHEMA: &str =
    "archeaxis.openmaic-interactive-outline/v1";
pub const OPENMAIC_INTERACTIVE_OUTLINE_RESULT_SCHEMA: &str =
    "archeaxis.openmaic-interactive-outline-result/v1";
pub const OPENMAIC_INTERACTIVE_OUTLINE_BINDING_SCHEMA: &str =
    "archeaxis.openmaic-interactive-outline-binding/v1";
pub const OPENMAIC_INTERACTIVE_OUTLINE_DOCUMENT_SCHEMA: &str =
    "archeaxis.openmaic-interactive-outline-generate-document/v1";
pub const OPENMAIC_INTERACTIVE_OUTLINE_NAMESPACE: &str =
    "archeaxis_openmaic_interactive_outline_generate_candidate";
pub const OPENMAIC_INTERACTIVE_OUTLINE_GENERATION_ROUTE: &str = "local_model_interactive_outline";
const OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_FIELDS: [&str; 5] = [
    "schema",
    "create_request_id",
    "requirement",
    "source_text",
    "model",
];
const OPENMAIC_INTERACTIVE_OUTLINE_BINDING_FIELDS: [&str; 9] = [
    "schema",
    "request_id",
    "input_sha256",
    "templates_manifest_sha256",
    "worker_sha256",
    "system",
    "user",
    "system_sha256",
    "user_sha256",
];
/// The prompt worker's own request budget: 16,384 bytes inside a 32,768-byte
/// frame. The model reply is bounded by the outline route's own 120,000 bytes.
const OPENMAIC_INTERACTIVE_OUTLINE_MAX_PROMPT_REQUEST: usize = 16_384;
const OPENMAIC_INTERACTIVE_OUTLINE_MAX_PROMPT_BYTES: usize = 200_000;

fn invalid(message: &'static str) -> Error {
    Error::Invalid(message)
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

fn sha_matches(text: &Value, expected: &Value) -> bool {
    text.as_str()
        .is_some_and(|text| expected.as_str() == Some(&digest(text.as_bytes())))
}

/// Name everything this slice refuses before Core captures a prompt or calls a
/// model. `None` means the request may proceed; the write path repeats the checks.
pub fn openmaic_interactive_outline_refusal(request: &Value) -> Option<Value> {
    let Some(object) = request.as_object() else {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_SHAPE","declared":"not an object",
            "supported":[OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_SCHEMA]}),
        );
    };
    if object.get("schema").and_then(Value::as_str)
        != Some(OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_SCHEMA)
    {
        return Some(json!({"reason":"UNSUPPORTED_REQUEST_VERSION",
            "declared":object.get("schema").cloned().unwrap_or(Value::Null),
            "supported":[OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_SCHEMA]}));
    }
    if object.len() != OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_FIELDS.len()
        || OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_FIELDS
            .iter()
            .any(|key| !object.contains_key(*key))
    {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_FIELDS","declared":object.len(),
            "supported":OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_FIELDS.len()}),
        );
    }
    if request["create_request_id"]
        .as_str()
        .is_none_or(|value| !token(value))
    {
        return Some(json!({"reason":"INVALID_REQUEST_ID","declared":Value::Null,
            "supported":"1-128 ASCII [A-Za-z0-9_-] token"}));
    }
    let requirement = request["requirement"].as_str();
    // The adapter bounds these fields in bytes; Core refuses the same span so a
    // request it admits can never be rejected as over-budget by the worker.
    if requirement.is_none_or(|value| value.trim().is_empty() || value.len() > 8_000) {
        return Some(json!({"reason":"REQUIREMENT_OUT_OF_BOUNDS",
            "declared":requirement.map(str::len),
            "supported":"1 to 8000 bytes"}));
    }
    let source_text = request["source_text"].as_str();
    if source_text.is_none_or(|value| value.len() > 50_000) {
        return Some(json!({"reason":"SOURCE_TEXT_OUT_OF_BOUNDS",
            "declared":source_text.map(str::len),
            "supported":"0 to 50000 bytes"}));
    }
    if !request["model"].is_null() && !model_identity(&request["model"]) {
        return Some(
            json!({"reason":"INVALID_MODEL_SELECTION","declared":Value::Null,
            "supported":"an omitted model or 1-256 printable characters"}),
        );
    }
    None
}

/// Deterministic identity of the caller's generate request. The model reply is
/// deliberately excluded: a second run must not create a second document.
pub fn openmaic_interactive_outline_request_sha256(request: &Value) -> String {
    digest(request.to_string().as_bytes())
}

pub fn openmaic_interactive_outline_internal_request_id(create_request_id: &str) -> String {
    format!(
        "openmaic_interactive_outline_generate_{}",
        digest(create_request_id.as_bytes())
    )
}

pub fn openmaic_interactive_outline_document_id(create_request_id: &str) -> String {
    let internal_id = openmaic_interactive_outline_internal_request_id(create_request_id);
    format!("doc_req_{}", digest(internal_id.as_bytes()))
}

/// The capture frame Core sends to the Node adapter. It carries no reply, so the
/// worker can only render the prompt binding.
pub fn openmaic_interactive_outline_capture_request(request: &Value) -> Value {
    json!({"schema":OPENMAIC_INTERACTIVE_OUTLINE_PROMPT_SCHEMA,"stage":"capture",
        "request_id":request["create_request_id"],"requirement":request["requirement"],
        "source_text":request["source_text"]})
}

/// The local-model request reuses the outline route's own frame and capability.
pub fn openmaic_interactive_outline_model_request(binding: &Value, model: &Value) -> Value {
    openmaic_outline::openmaic_outline_model_request(binding, model)
}

pub fn openmaic_interactive_outline_model_content(reply: &Value) -> Option<&str> {
    openmaic_outline::openmaic_outline_model_content(reply)
}

/// The replay frame: the captured binding plus the model's final text.
pub fn openmaic_interactive_outline_replay_request(
    request: &Value,
    binding: &Value,
    content: &str,
) -> Value {
    json!({"schema":OPENMAIC_INTERACTIVE_OUTLINE_PROMPT_SCHEMA,"stage":"replay",
        "request_id":request["create_request_id"],"requirement":request["requirement"],
        "source_text":request["source_text"],"binding":binding,
        "reply":{"kind":"caller_supplied","value":content}})
}

fn binding_shape(binding: &Value, create_request_id: &str) -> bool {
    binding.as_object().is_some_and(|object| {
        object.len() == OPENMAIC_INTERACTIVE_OUTLINE_BINDING_FIELDS.len()
            && OPENMAIC_INTERACTIVE_OUTLINE_BINDING_FIELDS
                .iter()
                .all(|key| object.contains_key(*key))
            && binding["schema"] == OPENMAIC_INTERACTIVE_OUTLINE_BINDING_SCHEMA
            && binding["request_id"].as_str() == Some(create_request_id)
            && [
                "input_sha256",
                "templates_manifest_sha256",
                "worker_sha256",
                "system_sha256",
                "user_sha256",
            ]
            .iter()
            .all(|key| hex_digest(&binding[*key]))
            && binding["system"].as_str().is_some_and(|text| {
                text.as_bytes().len() <= OPENMAIC_INTERACTIVE_OUTLINE_MAX_PROMPT_BYTES
                    && !text.contains('\0')
            })
            && binding["user"].as_str().is_some_and(|text| {
                text.as_bytes().len() <= OPENMAIC_INTERACTIVE_OUTLINE_MAX_PROMPT_BYTES
                    && !text.contains('\0')
            })
            && sha_matches(&binding["system"], &binding["system_sha256"])
            && sha_matches(&binding["user"], &binding["user_sha256"])
    })
}

/// The prompt binding a `PROMPT_CAPTURED` result carries, or a named refusal.
pub fn openmaic_interactive_outline_capture_binding(
    create_request_id: &str,
    capture: &Value,
) -> Result<Value, Error> {
    if capture["schema"] != OPENMAIC_INTERACTIVE_OUTLINE_RESULT_SCHEMA
        || capture["status"] != "PROMPT_CAPTURED"
        || capture["stage"] != "capture"
        || capture["request_id"].as_str() != Some(create_request_id)
        || capture["model_call"] != "NOT_INVOKED"
        || capture["network_performed"] != false
        || capture["core_task"] != "NOT_CONNECTED"
        || capture["canonical_bindings_verified"] != false
        || capture["persisted"] != false
        || capture["active_content_executed"] != false
        || capture["prompt_template"] != "interactive-outlines"
        || capture["binding"].is_null()
    {
        return Err(invalid(
            "OpenMAIC interactive outline capture receipt does not match the request",
        ));
    }
    if !binding_shape(&capture["binding"], create_request_id) {
        return Err(invalid(
            "OpenMAIC interactive outline prompt binding is unsupported",
        ));
    }
    Ok(capture["binding"].clone())
}

/// The worker's replay result must belong to the frames Core actually sent, and
/// its outlines must pass the same bounded admission as the outline route.
fn replay_check(
    request: &Value,
    binding: &Value,
    reply: &Value,
    worker: &Value,
) -> Result<(), Error> {
    let create_request_id = request["create_request_id"]
        .as_str()
        .ok_or_else(|| invalid("invalid OpenMAIC interactive outline create request ID"))?;
    if !binding_shape(binding, create_request_id) {
        return Err(invalid(
            "OpenMAIC interactive outline prompt binding is unsupported",
        ));
    }
    if openmaic_outline::openmaic_outline_model_content(reply).is_none() {
        return Err(invalid(
            "OpenMAIC interactive outline model reply was not admitted for replay",
        ));
    }
    if worker["schema"] != OPENMAIC_INTERACTIVE_OUTLINE_RESULT_SCHEMA
        || worker["status"] != "CANDIDATE"
        || worker["stage"] != "replay"
        || worker["request_id"].as_str() != Some(create_request_id)
        || worker["model_call"] != "NOT_INVOKED"
        || worker["network_performed"] != false
        || worker["core_task"] != "NOT_CONNECTED"
        || worker["canonical_bindings_verified"] != false
        || worker["human_review_required"] != true
        || worker["active_content_executed"] != false
        || worker["response_origin"] != "CALLER_SUPPLIED_UNVERIFIED"
        || worker["prompt_template"] != "interactive-outlines"
        || worker["exact_json_output"].as_bool().is_none()
        || !worker["transformations"].as_array().is_some_and(|items| {
            items.iter().all(|item| {
                item.as_str().is_some_and(|value| {
                    matches!(
                        value,
                        "UPSTREAM_JSON_REPAIRED"
                            | "UNSTABLE_GENERATED_OUTLINE_IDS"
                            | "OUTLINE_ORDER_ASSIGNED"
                    )
                })
            })
        })
    {
        return Err(invalid(
            "OpenMAIC interactive outline replay receipt does not match the request",
        ));
    }
    openmaic_outline::outlines_admitted(&worker["data"])
}

fn receipt(conn: &Connection, document: Value) -> Value {
    let candidate_status = match document["document_id"].as_str() {
        Some(id) => match crate::document::read_verified(conn, id, None) {
            Ok(current)
                if current["version"] == document["version"]
                    && current["content_sha256"] == document["content_sha256"] =>
            {
                "current"
            }
            Ok(current)
                if current["version"]
                    .as_i64()
                    .is_some_and(|version| version > 1) =>
            {
                "historical"
            }
            _ => "unavailable",
        },
        None => "unavailable",
    };
    let stored = &document["editor_json"]["attrs"][OPENMAIC_INTERACTIVE_OUTLINE_NAMESPACE];
    json!({
        "schema":"archeaxis.openmaic-interactive-outline-generate-persistence/v1",
        "document":document,
        "candidate_document_status":candidate_status,
        "generation_route":OPENMAIC_INTERACTIVE_OUTLINE_GENERATION_ROUTE,
        "model_call":"INVOKED",
        "model":stored["model"],
        "model_observed":stored["model_observed"],
        "model_reply_sha256":stored["model_reply_sha256"],
        "model_finish_reason":stored["model_finish_reason"],
        "model_usage":stored["model_usage"],
        "prompt_binding":stored["prompt_binding"],
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "outline_count":stored["outlines"].as_array().map(Vec::len).unwrap_or(0),
        "outlines":stored["outlines"],
    })
}

fn existing(
    conn: &Connection,
    create_request_id: &str,
    request_sha256: &str,
) -> Result<Option<Value>, Error> {
    let id = openmaic_interactive_outline_document_id(create_request_id);
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
        [&id],
        |row| row.get(0),
    )?;
    if !exists {
        return Ok(None);
    }
    let document = crate::document::read_verified(conn, &id, Some(1))?;
    let saved = &document["editor_json"]["attrs"][OPENMAIC_INTERACTIVE_OUTLINE_NAMESPACE];
    if saved["schema"].as_str() != Some(OPENMAIC_INTERACTIVE_OUTLINE_DOCUMENT_SCHEMA)
        || saved["create_request_id"] != create_request_id
        || saved["generation_request_sha256"].as_str() != Some(request_sha256)
    {
        return Err(invalid(
            "OpenMAIC interactive outline create request ID conflicts with another document",
        ));
    }
    replay_check(
        &saved["request_frame"],
        &saved["prompt_binding"],
        &saved["model_reply"],
        &saved["worker_document"],
    )?;
    Ok(Some(receipt(conn, document)))
}

/// Captured by Core before dispatch and checked again when admitting the result.
#[derive(Clone)]
pub struct OpenMaicInteractiveOutlinePending {
    restore_epoch: Option<String>,
    workspace_id: String,
    request_sha256: String,
    create_request_id: String,
}

#[derive(Clone)]
pub enum OpenMaicInteractiveOutlinePreparation {
    Existing(Value),
    Pending(OpenMaicInteractiveOutlinePending),
}

/// Check a retry and capture the workspace and restore epoch in one Core
/// transaction before capturing the prompts or calling a model.
pub fn prepare_openmaic_interactive_outline(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
) -> Result<OpenMaicInteractiveOutlinePreparation, Error> {
    if openmaic_interactive_outline_refusal(request).is_some()
        || request["create_request_id"].as_str() != Some(create_request_id)
    {
        return Err(invalid("invalid OpenMAIC interactive outline request"));
    }
    let request_sha256 = openmaic_interactive_outline_request_sha256(request);
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if let Some(receipt) = existing(&tx, create_request_id, &request_sha256)? {
        tx.commit()?;
        return Ok(OpenMaicInteractiveOutlinePreparation::Existing(receipt));
    }
    let restore_epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC interactive outline workspace identity unavailable"))?;
    tx.commit()?;
    Ok(OpenMaicInteractiveOutlinePreparation::Pending(
        OpenMaicInteractiveOutlinePending {
            restore_epoch,
            workspace_id,
            request_sha256,
            create_request_id: create_request_id.to_owned(),
        },
    ))
}

/// The three audited stage results. Core keeps the capture binding, the model
/// receipt and the adapter's replay document verbatim; nothing is rewritten.
#[derive(Clone)]
pub struct OpenMaicInteractiveOutlineGeneration {
    pub binding: Value,
    pub model_reply: Value,
    pub replay_document: Value,
}

/// Persist one inert candidate produced by the local-model route. Every stage is
/// re-checked here, and the exact capture and replay frames Core sent are stored
/// beside the model receipt so a later reader can recompute what ran.
pub fn commit_openmaic_interactive_outline_generation(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    pending: &OpenMaicInteractiveOutlinePending,
    generation: &OpenMaicInteractiveOutlineGeneration,
) -> Result<Value, Error> {
    if openmaic_interactive_outline_refusal(request).is_some()
        || request["create_request_id"].as_str() != Some(create_request_id)
        || create_request_id != pending.create_request_id.as_str()
        || openmaic_interactive_outline_request_sha256(request) != pending.request_sha256
    {
        return Err(invalid(
            "OpenMAIC interactive outline request changed after admission",
        ));
    }
    if openmaic_outline::openmaic_outline_new_model_content(&generation.model_reply).is_none() {
        return Err(invalid("OpenMAIC model completion was not confirmed"));
    }
    replay_check(
        request,
        &generation.binding,
        &generation.model_reply,
        &generation.replay_document,
    )?;
    let content = openmaic_outline::openmaic_outline_model_content(&generation.model_reply)
        .unwrap_or_default();
    let replay = openmaic_interactive_outline_replay_request(request, &generation.binding, content);
    let mut replay_bytes =
        serde_json::to_vec(&replay).map_err(|_| invalid("invalid interactive outline replay"))?;
    replay_bytes.push(b'\n');
    if replay_bytes.len() > openmaic_outline::OPENMAIC_OUTLINE_MAX_FRAME {
        return Err(invalid("OpenMAIC interactive outline replay exceeds bound"));
    }
    let replay_frame =
        String::from_utf8(replay_bytes).map_err(|_| invalid("invalid replay frame"))?;
    let mut capture_bytes =
        serde_json::to_vec(&openmaic_interactive_outline_capture_request(request))
            .map_err(|_| invalid("invalid interactive outline capture"))?;
    capture_bytes.push(b'\n');
    if capture_bytes.len() > OPENMAIC_INTERACTIVE_OUTLINE_MAX_PROMPT_REQUEST {
        return Err(invalid(
            "OpenMAIC interactive outline capture exceeds bound",
        ));
    }
    let capture_frame =
        String::from_utf8(capture_bytes).map_err(|_| invalid("invalid capture frame"))?;

    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::existing_workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC interactive outline workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(invalid(
            "OpenMAIC interactive outline workspace or restore epoch changed",
        ));
    }
    if !archeaxis_store_sqlite::capability_settings::is_enabled(
        &tx,
        openmaic_outline::OPENMAIC_OUTLINE_CAPABILITY,
    )? {
        return Err(invalid("OpenMAIC capability is disabled"));
    }
    // Two requests may have passed preparation concurrently. Never replace the
    // first candidate with a second run's text.
    if let Some(existing) = existing(&tx, create_request_id, &pending.request_sha256)? {
        tx.commit()?;
        return Ok(existing);
    }
    let outlines = &generation.replay_document["data"]["outlines"];
    let first_title = outlines
        .as_array()
        .and_then(|items| items.first())
        .and_then(|outline| outline["title"].as_str())
        .unwrap_or("outline");
    let title = format!(
        "OpenMAIC interactive outline candidate · {}",
        first_title.chars().take(200).collect::<String>()
    );
    let binding = &generation.binding;
    let saved = json!({
        "schema":OPENMAIC_INTERACTIVE_OUTLINE_DOCUMENT_SCHEMA,
        "create_request_id":create_request_id,
        "generation_request_sha256":pending.request_sha256,
        "capture_frame":capture_frame,
        "replay_frame":replay_frame,
        "request_frame":request,
        "generation_route":OPENMAIC_INTERACTIVE_OUTLINE_GENERATION_ROUTE,
        "model_call":"INVOKED",
        "model":generation.model_reply["model"],
        "model_observed":generation.model_reply["observed_model"],
        "model_reply_sha256":generation.model_reply["content_sha256"],
        "model_reply_bytes":generation.model_reply["content_bytes"],
        "model_finish_reason":generation.model_reply["finish_reason"],
        "model_usage":generation.model_reply["usage"],
        "model_reply":generation.model_reply,
        "prompt_binding":binding,
        "worker_document":generation.replay_document,
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "provider":"openmaic",
        "provider_version":"1.3.0",
        "generation_version":"0.3.28",
        "outlines":outlines,
    });
    let editor = json!({"type":"doc","attrs":{(OPENMAIC_INTERACTIVE_OUTLINE_NAMESPACE):saved},
        "content":[{"type":"paragraph",
            "attrs":{"block_id":"openmaic_interactive_outline_generate_candidate"},
            "content":[{"type":"text","text":title.clone()}]}]});
    let internal_id = openmaic_interactive_outline_internal_request_id(create_request_id);
    let document =
        crate::document::create_optional_tx(&tx, None, None, &title, editor, Some(&internal_id))?;
    let document_id = document["document_id"]
        .as_str()
        .ok_or_else(|| invalid("OpenMAIC interactive outline document ID missing"))?;
    let verified = crate::document::read_verified(&tx, document_id, Some(1))?;
    let receipt = receipt(&tx, verified);
    tx.commit()?;
    Ok(receipt)
}
