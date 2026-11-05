//! Offline OpenMAIC outline replay candidates.
//!
//! This slice calls no model and performs no network access. It accepts the
//! caller-declared model reply, validates its bounded shape and persists the
//! exact request frame plus the worker reply as one ordinary Core Document.
//! The worker's own receipt declares `CALLER_DECLARED_UNVERIFIED`; Core records
//! that derivation instead of promoting it to a verified outline or render grant.
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

/// The bounded replay request contract. The field set is exactly these five.
pub const OPENMAIC_OUTLINE_REQUEST_SCHEMA: &str = "archeaxis.openmaic-outline-replay/v1";
pub const OPENMAIC_OUTLINE_RESULT_SCHEMA: &str = "archeaxis.openmaic-outline-replay-result/v1";
pub const OPENMAIC_OUTLINE_DOCUMENT_SCHEMA: &str = "archeaxis.openmaic-outline-document/v1";
pub const OPENMAIC_OUTLINE_NAMESPACE: &str = "archeaxis_openmaic_outline_candidate";
/// The provider gate this slice shares with the existing scene builder: one
/// OpenMAIC Node launch owns both fixed scripts.
pub const OPENMAIC_OUTLINE_CAPABILITY: &str = "course.openmaic.scene-build";
pub const OPENMAIC_OUTLINE_MAX_FRAME: usize = 256_000;
const OPENMAIC_OUTLINE_MAX_REPLY_BYTES: usize = 120_000;
const OPENMAIC_OUTLINE_REQUEST_FIELDS: [&str; 5] = [
    "schema",
    "request_id",
    "requirement",
    "source_text",
    "reply",
];
const OPENMAIC_OUTLINE_TYPES: [&str; 2] = ["slide", "quiz"];

fn invalid(message: &'static str) -> crate::document::Error {
    crate::document::Error::Invalid(message)
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

fn bounded_text(value: &Value, max_chars: usize) -> bool {
    value
        .as_str()
        .is_some_and(|text| !text.trim().is_empty() && text.chars().count() <= max_chars)
}

fn reply_shape(reply: &Value) -> bool {
    let Some(object) = reply.as_object() else {
        return false;
    };
    match object.get("kind").and_then(Value::as_str) {
        // The worker's error replay carries nothing else.
        Some("synthetic_error") => object.len() == 1,
        Some("synthetic_response") => {
            object.len() == 2
                && object
                    .get("value")
                    .and_then(Value::as_str)
                    .is_some_and(|value| value.as_bytes().len() <= OPENMAIC_OUTLINE_MAX_REPLY_BYTES)
        }
        _ => false,
    }
}

/// Name everything this offline slice refuses before a worker could run. `None`
/// means the request may proceed to the write path, which repeats every check.
pub fn openmaic_outline_refusal(request: &Value) -> Option<Value> {
    let Some(object) = request.as_object() else {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_SHAPE","declared":"not an object",
            "supported":[OPENMAIC_OUTLINE_REQUEST_SCHEMA]}),
        );
    };
    if object.get("schema").and_then(Value::as_str) != Some(OPENMAIC_OUTLINE_REQUEST_SCHEMA) {
        return Some(json!({"reason":"UNSUPPORTED_REQUEST_VERSION",
            "declared":object.get("schema").cloned().unwrap_or(Value::Null),
            "supported":[OPENMAIC_OUTLINE_REQUEST_SCHEMA]}));
    }
    if object.len() != OPENMAIC_OUTLINE_REQUEST_FIELDS.len()
        || OPENMAIC_OUTLINE_REQUEST_FIELDS
            .iter()
            .any(|key| !object.contains_key(*key))
    {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_FIELDS","declared":object.len(),
            "supported":OPENMAIC_OUTLINE_REQUEST_FIELDS.len()}),
        );
    }
    if request["request_id"]
        .as_str()
        .is_none_or(|value| !token(value))
    {
        return Some(json!({"reason":"INVALID_REQUEST_ID","declared":Value::Null,
            "supported":"1-128 ASCII [A-Za-z0-9_-] token"}));
    }
    let requirement = request["requirement"].as_str();
    if requirement.is_none_or(|value| value.trim().is_empty() || value.chars().count() > 8_000) {
        return Some(json!({"reason":"REQUIREMENT_OUT_OF_BOUNDS",
            "declared":requirement.map(|value| value.chars().count()),
            "supported":"1 to 8000 characters"}));
    }
    let source_text = request["source_text"].as_str();
    if source_text.is_none_or(|value| value.chars().count() > 50_000) {
        return Some(json!({"reason":"SOURCE_TEXT_OUT_OF_BOUNDS",
            "declared":source_text.map(|value| value.chars().count()),
            "supported":"0 to 50000 characters"}));
    }
    if !reply_shape(&request["reply"]) {
        return Some(json!({"reason":"INVALID_REPLY",
            "declared":request["reply"].get("kind").cloned().unwrap_or(Value::Null),
            "supported":["synthetic_error","synthetic_response"]}));
    }
    None
}

/// Internal create-request identity of the candidate Document.
pub fn openmaic_outline_internal_request_id(create_request_id: &str) -> String {
    format!("openmaic_outline_{}", digest(create_request_id.as_bytes()))
}

/// Deterministic candidate Document ID for a client create request ID.
pub fn openmaic_outline_document_id(create_request_id: &str) -> String {
    let internal_id = openmaic_outline_internal_request_id(create_request_id);
    format!("doc_req_{}", digest(internal_id.as_bytes()))
}

/// Match the executor's serialization and frame limit before starting Node.
fn outline_frame(
    create_request_id: &str,
    request: &Value,
) -> Result<(String, String), crate::document::Error> {
    if !token(create_request_id) {
        return Err(invalid("invalid OpenMAIC outline create request ID"));
    }
    if let Some(_refusal) = openmaic_outline_refusal(request) {
        return Err(invalid("invalid OpenMAIC outline request"));
    }
    let mut bytes =
        serde_json::to_vec(request).map_err(|_| invalid("invalid OpenMAIC outline JSON"))?;
    bytes.push(b'\n');
    if bytes.len() > OPENMAIC_OUTLINE_MAX_FRAME {
        return Err(invalid("OpenMAIC outline frame exceeds bound"));
    }
    let sha = digest(&bytes);
    let frame = String::from_utf8(bytes).map_err(|_| invalid("invalid OpenMAIC outline frame"))?;
    Ok((frame, sha))
}

fn outline_bounded_id(value: &Value) -> bool {
    value.as_str().is_some_and(token)
}

/// Reject a worker reply that is not exactly the bounded candidate this slice
/// can persist. The worker's own receipt declares the unverified origin; Core
/// still checks that the candidate belongs to the request it actually sent.
fn outline_check_result(
    request: &Value,
    input_sha256: &str,
    worker: &Value,
) -> Result<(), crate::document::Error> {
    if worker["schema"] != OPENMAIC_OUTLINE_RESULT_SCHEMA
        || worker["status"] != "CANDIDATE"
        || worker["model_call"] != "NOT_INVOKED"
        || worker["network_performed"] != false
        || worker["core_task"] != "NOT_CONNECTED"
        || worker["canonical_bindings_verified"] != false
        || worker["human_review_required"] != true
        || worker["active_content_executed"] != false
        || worker["response_origin_verification"] != "CALLER_DECLARED_UNVERIFIED"
        || worker["input_sha256"] != input_sha256
        || worker["input"] != *request
    {
        return Err(invalid(
            "OpenMAIC outline worker receipt does not match input",
        ));
    }
    outlines_admitted(&worker["data"])
}

/// The bounded 1-30 `slide`/`quiz` outline list both slices persist.
fn outlines_admitted(data: &Value) -> Result<(), crate::document::Error> {
    let outlines = data["outlines"]
        .as_array()
        .filter(|items| (1..=30).contains(&items.len()));
    let Some(outlines) = outlines else {
        return Err(invalid(
            "OpenMAIC outline worker returned an unsupported outline list",
        ));
    };
    for outline in outlines {
        if !outline.is_object()
            || !outline_bounded_id(&outline["id"])
            || !OPENMAIC_OUTLINE_TYPES.contains(&outline["type"].as_str().unwrap_or(""))
            || !bounded_text(&outline["title"], 240)
            || outline["description"]
                .as_str()
                .is_none_or(|value| value.chars().count() > 16_000)
            || !outline["keyPoints"].as_array().is_some_and(|points| {
                (0..=200).contains(&points.len())
                    && points.iter().all(|point| {
                        point
                            .as_str()
                            .is_some_and(|value| value.chars().count() <= 2_000)
                    })
            })
        {
            return Err(invalid(
                "OpenMAIC outline worker returned an unsupported outline entry",
            ));
        }
    }
    Ok(())
}

/// Core-derived per-outline summary. `order` is the stored outline order, or the
/// one-based position when the donor result did not record one.
fn outline_summary(worker: &Value) -> Vec<Value> {
    worker["data"]["outlines"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_default()
        .iter()
        .enumerate()
        .map(|(index, outline)| {
            json!({
                "id":outline["id"],
                "type":outline["type"],
                "title":outline["title"],
                "order":outline["order"].as_i64().unwrap_or(index as i64 + 1),
                "key_points_count":outline["keyPoints"].as_array().map(Vec::len).unwrap_or(0),
            })
        })
        .collect()
}

fn candidate_status(conn: &Connection, document: &Value) -> &'static str {
    match document["document_id"].as_str() {
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
    }
}

fn outline_receipt(conn: &Connection, document: Value) -> Value {
    let status = candidate_status(conn, &document).to_owned();
    let stored = &document["editor_json"]["attrs"][OPENMAIC_OUTLINE_NAMESPACE];
    json!({
        "schema":"archeaxis.openmaic-outline-persistence/v1",
        "document":document,
        "candidate_document_status":status,
        "response_origin":"client_declared_unverified",
        "model_call":"NOT_INVOKED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "outline_count":stored["outlines"].as_array().map(Vec::len).unwrap_or(0),
        "outlines":stored["outlines"],
    })
}

fn outline_existing(
    conn: &Connection,
    create_request_id: &str,
    frame: &str,
    input_sha256: &str,
) -> Result<Option<Value>, crate::document::Error> {
    let id = openmaic_outline_document_id(create_request_id);
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
        [&id],
        |row| row.get(0),
    )?;
    if !exists {
        return Ok(None);
    }
    let document = crate::document::read_verified(conn, &id, Some(1))?;
    let saved = &document["editor_json"]["attrs"][OPENMAIC_OUTLINE_NAMESPACE];
    if saved["schema"].as_str() != Some(OPENMAIC_OUTLINE_DOCUMENT_SCHEMA)
        || saved["create_request_id"] != create_request_id
        || saved["request_frame"] != frame
        || saved["input_sha256"] != input_sha256
    {
        return Err(invalid(
            "OpenMAIC outline create request ID conflicts with another document",
        ));
    }
    outline_check_result(
        &serde_json::from_str(frame.trim()).map_err(|_| invalid("invalid stored outline frame"))?,
        input_sha256,
        &saved["worker_document"],
    )?;
    Ok(Some(outline_receipt(conn, document)))
}

/// Captured by Core before dispatch and checked again when admitting the result.
/// Private fields prevent an HTTP caller from constructing an admission token.
#[derive(Clone)]
pub struct OpenMaicOutlinePending {
    restore_epoch: Option<String>,
    workspace_id: String,
    input_sha256: String,
    create_request_id: String,
}

/// Repeated requests return the first saved document without running a worker.
#[derive(Clone)]
pub enum OpenMaicOutlinePreparation {
    Existing(Value),
    Pending(OpenMaicOutlinePending),
}

/// Check a retry and capture the workspace and restore epoch in one Core
/// transaction before launching the worker. The caller must independently
/// enforce human access, process lifecycle, capability admission and
/// cancellation.
pub fn prepare_openmaic_outline(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
) -> Result<OpenMaicOutlinePreparation, crate::document::Error> {
    let (frame, input_sha256) = outline_frame(create_request_id, request)?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if let Some(receipt) = outline_existing(&tx, create_request_id, &frame, &input_sha256)? {
        tx.commit()?;
        return Ok(OpenMaicOutlinePreparation::Existing(receipt));
    }
    let restore_epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    // Existing Core UI-state identity is also the workspace identity used by
    // other long-lived operations. Initialize it once for a fresh workspace.
    let workspace_id = crate::ui_state::workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC outline workspace identity unavailable"))?;
    tx.commit()?;
    Ok(OpenMaicOutlinePreparation::Pending(
        OpenMaicOutlinePending {
            restore_epoch,
            workspace_id,
            input_sha256,
            create_request_id: create_request_id.to_owned(),
        },
    ))
}

/// Persist one inert outline candidate through the existing Document writer.
/// The stored Document keeps the caller-declared reply and may contain source
/// material; Core never treats the outlines as executable content or as a
/// rendering authorization.
pub fn commit_openmaic_outline(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    pending: &OpenMaicOutlinePending,
    worker_document: &Value,
) -> Result<Value, crate::document::Error> {
    let (frame, input_sha256) = outline_frame(create_request_id, request)?;
    if input_sha256 != pending.input_sha256
        || create_request_id != pending.create_request_id.as_str()
    {
        return Err(invalid("OpenMAIC outline request changed after admission"));
    }
    outline_check_result(request, &input_sha256, worker_document)?;
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::existing_workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC outline workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(invalid(
            "OpenMAIC outline workspace or restore epoch changed",
        ));
    }
    if !archeaxis_store_sqlite::capability_settings::is_enabled(&tx, OPENMAIC_OUTLINE_CAPABILITY)? {
        return Err(invalid("OpenMAIC capability is disabled"));
    }
    // Two requests may have passed preparation concurrently. Never replace the
    // first candidate with a second run's content.
    if let Some(existing) = outline_existing(&tx, create_request_id, &frame, &input_sha256)? {
        tx.commit()?;
        return Ok(existing);
    }
    let summary = outline_summary(worker_document);
    let first_title = summary
        .first()
        .and_then(|outline| outline["title"].as_str())
        .unwrap_or("outline");
    let title = format!(
        "OpenMAIC outline candidate · {}",
        first_title.chars().take(200).collect::<String>()
    );
    let saved = json!({
        "schema":OPENMAIC_OUTLINE_DOCUMENT_SCHEMA,
        "create_request_id":create_request_id,
        "input_sha256":input_sha256,
        "request_frame":frame,
        "worker_document":worker_document,
        "response_origin":"CALLER_DECLARED_UNVERIFIED",
        "model_call":"NOT_INVOKED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "provider":"openmaic",
        "provider_version":"1.3.0",
        "generation_version":"0.3.28",
        "outlines":summary,
    });
    let editor = json!({"type":"doc","attrs":{(OPENMAIC_OUTLINE_NAMESPACE):saved},
        "content":[{"type":"paragraph","attrs":{"block_id":"openmaic_outline_candidate"},
            "content":[{"type":"text","text":title.clone()}]}]});
    let internal_id = openmaic_outline_internal_request_id(create_request_id);
    let document =
        crate::document::create_optional_tx(&tx, None, None, &title, editor, Some(&internal_id))?;
    let document_id = document["document_id"]
        .as_str()
        .ok_or_else(|| invalid("OpenMAIC outline document ID missing"))?;
    let verified = crate::document::read_verified(&tx, document_id, Some(1))?;
    let receipt = outline_receipt(&tx, verified);
    tx.commit()?;
    Ok(receipt)
}

// ---------------------------------------------------------------------------
// Local-model generation: Core captures the donor prompts, calls the local
// model, replays the reply through the same Node worker, and persists only a
// `CANDIDATE`. Each stage keeps its own receipt; a failure never becomes text,
// never falls back to a cloud provider and never writes a partial candidate.
// ---------------------------------------------------------------------------

/// The bounded generate contract the HTTP caller may send.
pub const OPENMAIC_OUTLINE_GENERATE_REQUEST_SCHEMA: &str = "archeaxis.openmaic-outline-generate/v1";
pub const OPENMAIC_OUTLINE_PROMPT_REQUEST_SCHEMA: &str = "archeaxis.openmaic-outline-prompt/v1";
pub const OPENMAIC_OUTLINE_PROMPT_RESULT_SCHEMA: &str =
    "archeaxis.openmaic-outline-prompt-result/v1";
pub const OPENMAIC_OUTLINE_PROMPT_BINDING_SCHEMA: &str =
    "archeaxis.openmaic-outline-prompt-binding/v1";
pub const OPENMAIC_OUTLINE_MODEL_REQUEST_SCHEMA: &str =
    "archeaxis.openmaic-outline-model-request/v1";
pub const OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA: &str = "archeaxis.openmaic-outline-model-reply/v1";
pub const OPENMAIC_OUTLINE_GENERATE_DOCUMENT_SCHEMA: &str =
    "archeaxis.openmaic-outline-generate-document/v1";
pub const OPENMAIC_OUTLINE_GENERATE_NAMESPACE: &str =
    "archeaxis_openmaic_outline_generate_candidate";
/// Named Python capability the local model call is dispatched through. It is
/// separate from the OpenMAIC Node gate: a runtime may declare Node without a
/// local model, and that must read as a named unavailability, not a success.
pub const OPENMAIC_OUTLINE_MODEL_CAPABILITY: &str = "course.openmaic.outline-model";
/// The donor's own per-prompt bound (`outline-prompt-guard.mjs`).
const OPENMAIC_OUTLINE_MAX_PROMPT_BYTES: usize = 200_000;
/// The reply budget the Node replay request accepts.
const OPENMAIC_OUTLINE_MAX_MODEL_REPLY_BYTES: usize = 120_000;
const OPENMAIC_OUTLINE_GENERATE_FIELDS: [&str; 5] = [
    "schema",
    "create_request_id",
    "requirement",
    "source_text",
    "model",
];
const OPENMAIC_OUTLINE_BINDING_FIELDS: [&str; 11] = [
    "schema",
    "request_id",
    "input_sha256",
    "upstream_manifest_sha256",
    "npm_members_sha256",
    "worker_sha256",
    "guard_sha256",
    "system",
    "user",
    "system_sha256",
    "user_sha256",
];

fn hex_digest(value: &Value) -> bool {
    value
        .as_str()
        .is_some_and(|text| text.len() == 64 && text.bytes().all(|b| b.is_ascii_hexdigit()))
}

fn sha_matches(text: &Value, expected: &Value) -> bool {
    text.as_str()
        .is_some_and(|text| expected.as_str() == Some(&digest(text.as_bytes())))
}

fn model_identity(value: &Value) -> bool {
    value.as_str().is_some_and(|name| {
        !name.is_empty()
            && name.len() <= 256
            && name == name.trim()
            && !name.chars().any(char::is_control)
    })
}

/// Name everything this slice refuses before Core captures a prompt or calls a
/// model. `None` means the request may proceed; the write path repeats every check.
pub fn openmaic_outline_generate_refusal(request: &Value) -> Option<Value> {
    let Some(object) = request.as_object() else {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_SHAPE","declared":"not an object",
            "supported":[OPENMAIC_OUTLINE_GENERATE_REQUEST_SCHEMA]}),
        );
    };
    if object.get("schema").and_then(Value::as_str)
        != Some(OPENMAIC_OUTLINE_GENERATE_REQUEST_SCHEMA)
    {
        return Some(json!({"reason":"UNSUPPORTED_REQUEST_VERSION",
            "declared":object.get("schema").cloned().unwrap_or(Value::Null),
            "supported":[OPENMAIC_OUTLINE_GENERATE_REQUEST_SCHEMA]}));
    }
    if object.len() != OPENMAIC_OUTLINE_GENERATE_FIELDS.len()
        || OPENMAIC_OUTLINE_GENERATE_FIELDS
            .iter()
            .any(|key| !object.contains_key(*key))
    {
        return Some(
            json!({"reason":"UNEXPECTED_REQUEST_FIELDS","declared":object.len(),
            "supported":OPENMAIC_OUTLINE_GENERATE_FIELDS.len()}),
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
    if requirement.is_none_or(|value| value.trim().is_empty() || value.chars().count() > 8_000) {
        return Some(json!({"reason":"REQUIREMENT_OUT_OF_BOUNDS",
            "declared":requirement.map(|value| value.chars().count()),
            "supported":"1 to 8000 characters"}));
    }
    let source_text = request["source_text"].as_str();
    if source_text.is_none_or(|value| value.chars().count() > 50_000) {
        return Some(json!({"reason":"SOURCE_TEXT_OUT_OF_BOUNDS",
            "declared":source_text.map(|value| value.chars().count()),
            "supported":"0 to 50000 characters"}));
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
pub fn openmaic_outline_generate_request_sha256(request: &Value) -> String {
    digest(request.to_string().as_bytes())
}

pub fn openmaic_outline_generate_internal_request_id(create_request_id: &str) -> String {
    format!(
        "openmaic_outline_generate_{}",
        digest(create_request_id.as_bytes())
    )
}

pub fn openmaic_outline_generate_document_id(create_request_id: &str) -> String {
    let internal_id = openmaic_outline_generate_internal_request_id(create_request_id);
    format!("doc_req_{}", digest(internal_id.as_bytes()))
}

/// The capture frame Core sends to the Node outline worker. It carries no reply,
/// so the worker can only produce the prompt binding.
pub fn openmaic_outline_capture_request(request: &Value) -> Value {
    json!({"schema":OPENMAIC_OUTLINE_PROMPT_REQUEST_SCHEMA,"stage":"capture",
        "request_id":request["create_request_id"],"requirement":request["requirement"],
        "source_text":request["source_text"]})
}

/// The local-model request: only the two captured prompts and an optional model
/// selection. Nothing else is sent to the model.
pub fn openmaic_outline_model_request(binding: &Value, model: &Value) -> Value {
    let mut request = json!({"schema":OPENMAIC_OUTLINE_MODEL_REQUEST_SCHEMA,
        "system":binding["system"],"user":binding["user"]});
    if !model.is_null() {
        request["model"] = model.clone();
    }
    request
}

/// The replay frame: the captured binding plus the model's final text. The Node
/// worker recomputes the binding identity itself and refuses any difference.
pub fn openmaic_outline_replay_request(request: &Value, binding: &Value, content: &str) -> Value {
    json!({"schema":OPENMAIC_OUTLINE_PROMPT_REQUEST_SCHEMA,"stage":"replay",
        "request_id":request["create_request_id"],"requirement":request["requirement"],
        "source_text":request["source_text"],"binding":binding,
        "reply":{"kind":"caller_supplied","value":content}})
}

fn binding_shape(binding: &Value, create_request_id: &str) -> bool {
    binding.as_object().is_some_and(|object| {
        object.len() == OPENMAIC_OUTLINE_BINDING_FIELDS.len()
            && OPENMAIC_OUTLINE_BINDING_FIELDS
                .iter()
                .all(|key| object.contains_key(*key))
            && binding["schema"] == OPENMAIC_OUTLINE_PROMPT_BINDING_SCHEMA
            && binding["request_id"].as_str() == Some(create_request_id)
            && [
                "input_sha256",
                "upstream_manifest_sha256",
                "npm_members_sha256",
                "worker_sha256",
                "guard_sha256",
                "system_sha256",
                "user_sha256",
            ]
            .iter()
            .all(|key| hex_digest(&binding[*key]))
            && binding["system"].as_str().is_some_and(|text| {
                text.as_bytes().len() <= OPENMAIC_OUTLINE_MAX_PROMPT_BYTES && !text.contains('\0')
            })
            && binding["user"].as_str().is_some_and(|text| {
                text.as_bytes().len() <= OPENMAIC_OUTLINE_MAX_PROMPT_BYTES && !text.contains('\0')
            })
            && sha_matches(&binding["system"], &binding["system_sha256"])
            && sha_matches(&binding["user"], &binding["user_sha256"])
    })
}

/// The prompt binding a `PROMPT_CAPTURED` result carries, or a named refusal.
pub fn openmaic_outline_capture_binding(
    create_request_id: &str,
    capture: &Value,
) -> Result<Value, crate::document::Error> {
    if capture["schema"] != OPENMAIC_OUTLINE_PROMPT_RESULT_SCHEMA
        || capture["status"] != "PROMPT_CAPTURED"
        || capture["stage"] != "capture"
        || capture["request_id"].as_str() != Some(create_request_id)
        || capture["model_call"] != "NOT_INVOKED"
        || capture["network_performed"] != false
        || capture["core_task"] != "NOT_CONNECTED"
        || capture["canonical_bindings_verified"] != false
        || capture["persisted"] != false
        || capture["active_content_executed"] != false
        || capture["binding"].is_null()
    {
        return Err(invalid(
            "OpenMAIC outline capture receipt does not match the request",
        ));
    }
    if !binding_shape(&capture["binding"], create_request_id) {
        return Err(invalid("OpenMAIC outline prompt binding is unsupported"));
    }
    Ok(capture["binding"].clone())
}

/// The model's final text, or `None` when the reply is not an admitted one. The
/// text is kept verbatim; only an empty or over-budget reply is refused.
pub fn openmaic_outline_model_content(reply: &Value) -> Option<&str> {
    if reply["schema"] != OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA
        || reply["status"] != "REPLY"
        || reply["model_call"] != "INVOKED"
        || reply["network_performed"] != true
        || reply["network_scope"] != "LOOPBACK_LOCAL_MODEL_ONLY"
        || reply["model_output_verification"] != "UNREVIEWED_LOCAL_MODEL_TEXT"
        || reply["persisted"] != false
        || reply["core_task"] != "NOT_CONNECTED"
        || !model_identity(&reply["model"])
        || !sha_matches(&reply["content"], &reply["content_sha256"])
    {
        return None;
    }
    reply["content"].as_str().filter(|text| {
        !text.trim().is_empty() && text.as_bytes().len() <= OPENMAIC_OUTLINE_MAX_MODEL_REPLY_BYTES
    })
}

/// The worker's replay result must belong to the frame Core actually built.
fn generate_check_result(
    request: &Value,
    binding: &Value,
    reply: &Value,
    worker: &Value,
) -> Result<(), crate::document::Error> {
    let create_request_id = request["create_request_id"]
        .as_str()
        .ok_or_else(|| invalid("invalid OpenMAIC outline create request ID"))?;
    if !binding_shape(binding, create_request_id) {
        return Err(invalid("OpenMAIC outline prompt binding is unsupported"));
    }
    if openmaic_outline_model_content(reply).is_none() {
        return Err(invalid(
            "OpenMAIC outline model reply was not admitted for replay",
        ));
    }
    if worker["schema"] != OPENMAIC_OUTLINE_PROMPT_RESULT_SCHEMA
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
    {
        return Err(invalid(
            "OpenMAIC outline replay receipt does not match the request",
        ));
    }
    outlines_admitted(&worker["data"])
}

fn generation_receipt(conn: &Connection, document: Value) -> Value {
    let status = candidate_status(conn, &document).to_owned();
    let stored = &document["editor_json"]["attrs"][OPENMAIC_OUTLINE_GENERATE_NAMESPACE];
    json!({
        "schema":"archeaxis.openmaic-outline-generate-persistence/v1",
        "document":document,
        "candidate_document_status":status,
        "generation_route":"local_model",
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

fn generation_existing(
    conn: &Connection,
    create_request_id: &str,
    request_sha256: &str,
) -> Result<Option<Value>, crate::document::Error> {
    let id = openmaic_outline_generate_document_id(create_request_id);
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
        [&id],
        |row| row.get(0),
    )?;
    if !exists {
        return Ok(None);
    }
    let document = crate::document::read_verified(conn, &id, Some(1))?;
    let saved = &document["editor_json"]["attrs"][OPENMAIC_OUTLINE_GENERATE_NAMESPACE];
    if saved["schema"].as_str() != Some(OPENMAIC_OUTLINE_GENERATE_DOCUMENT_SCHEMA)
        || saved["create_request_id"] != create_request_id
        || saved["generation_request_sha256"].as_str() != Some(request_sha256)
    {
        return Err(invalid(
            "OpenMAIC outline create request ID conflicts with another document",
        ));
    }
    generate_check_result(
        &saved["request_frame"],
        &saved["prompt_binding"],
        &saved["model_reply"],
        &saved["worker_document"],
    )?;
    Ok(Some(generation_receipt(conn, document)))
}

/// Captured by Core before dispatch and checked again when admitting the result.
#[derive(Clone)]
pub struct OpenMaicOutlineGenerationPending {
    restore_epoch: Option<String>,
    workspace_id: String,
    request_sha256: String,
    create_request_id: String,
}

#[derive(Clone)]
pub enum OpenMaicOutlineGenerationPreparation {
    Existing(Value),
    Pending(OpenMaicOutlineGenerationPending),
}

/// Check a retry and capture the workspace and restore epoch in one Core
/// transaction before capturing the prompts or calling a model.
pub fn prepare_openmaic_outline_generation(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
) -> Result<OpenMaicOutlineGenerationPreparation, crate::document::Error> {
    if openmaic_outline_generate_refusal(request).is_some()
        || request["create_request_id"].as_str() != Some(create_request_id)
    {
        return Err(invalid("invalid OpenMAIC outline generate request"));
    }
    let request_sha256 = openmaic_outline_generate_request_sha256(request);
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if let Some(receipt) = generation_existing(&tx, create_request_id, &request_sha256)? {
        tx.commit()?;
        return Ok(OpenMaicOutlineGenerationPreparation::Existing(receipt));
    }
    let restore_epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC outline workspace identity unavailable"))?;
    tx.commit()?;
    Ok(OpenMaicOutlineGenerationPreparation::Pending(
        OpenMaicOutlineGenerationPending {
            restore_epoch,
            workspace_id,
            request_sha256,
            create_request_id: create_request_id.to_owned(),
        },
    ))
}

/// The three audited stage results. Core keeps the capture binding, the model
/// receipt and the worker's replay document verbatim; nothing is rewritten.
#[derive(Clone)]
pub struct OpenMaicLocalGeneration {
    pub binding: Value,
    pub model_reply: Value,
    pub replay_document: Value,
}

/// Persist one inert candidate produced by the local-model route. Every stage
/// is re-checked here, and the exact capture and replay frames Core sent are
/// stored beside the model receipt so a later reader can recompute what ran.
pub fn commit_openmaic_outline_generation(
    conn: &mut Connection,
    create_request_id: &str,
    request: &Value,
    pending: &OpenMaicOutlineGenerationPending,
    generation: &OpenMaicLocalGeneration,
) -> Result<Value, crate::document::Error> {
    if openmaic_outline_generate_refusal(request).is_some()
        || request["create_request_id"].as_str() != Some(create_request_id)
        || create_request_id != pending.create_request_id.as_str()
        || openmaic_outline_generate_request_sha256(request) != pending.request_sha256
    {
        return Err(invalid("OpenMAIC outline request changed after admission"));
    }
    generate_check_result(
        request,
        &generation.binding,
        &generation.model_reply,
        &generation.replay_document,
    )?;
    let content = openmaic_outline_model_content(&generation.model_reply).unwrap_or_default();
    let replay = openmaic_outline_replay_request(request, &generation.binding, content);
    let mut replay_bytes = serde_json::to_vec(&replay)
        .map_err(|_| invalid("invalid OpenMAIC outline replay frame"))?;
    replay_bytes.push(b'\n');
    if replay_bytes.len() > OPENMAIC_OUTLINE_MAX_FRAME {
        return Err(invalid("OpenMAIC outline replay frame exceeds bound"));
    }
    let replay_frame =
        String::from_utf8(replay_bytes).map_err(|_| invalid("invalid replay frame"))?;
    let mut capture_bytes = serde_json::to_vec(&openmaic_outline_capture_request(request))
        .map_err(|_| invalid("invalid OpenMAIC outline capture frame"))?;
    capture_bytes.push(b'\n');
    let capture_frame =
        String::from_utf8(capture_bytes).map_err(|_| invalid("invalid capture frame"))?;

    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    let epoch = archeaxis_store_sqlite::authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = crate::ui_state::existing_workspace_id(&tx)
        .map_err(|_| invalid("OpenMAIC outline workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(invalid(
            "OpenMAIC outline workspace or restore epoch changed",
        ));
    }
    if !archeaxis_store_sqlite::capability_settings::is_enabled(&tx, OPENMAIC_OUTLINE_CAPABILITY)? {
        return Err(invalid("OpenMAIC capability is disabled"));
    }
    // Two requests may have passed preparation concurrently. Never replace the
    // first candidate with a second run's text.
    if let Some(existing) = generation_existing(&tx, create_request_id, &pending.request_sha256)? {
        tx.commit()?;
        return Ok(existing);
    }
    let summary = outline_summary(&generation.replay_document);
    let first_title = summary
        .first()
        .and_then(|outline| outline["title"].as_str())
        .unwrap_or("outline");
    let title = format!(
        "OpenMAIC local-model outline candidate · {}",
        first_title.chars().take(200).collect::<String>()
    );
    let binding = &generation.binding;
    let saved = json!({
        "schema":OPENMAIC_OUTLINE_GENERATE_DOCUMENT_SCHEMA,
        "create_request_id":create_request_id,
        "generation_request_sha256":pending.request_sha256,
        "capture_frame":capture_frame,
        "replay_frame":replay_frame,
        "request_frame":request,
        "generation_route":"local_model",
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
        "outlines":summary,
    });
    let editor = json!({"type":"doc","attrs":{(OPENMAIC_OUTLINE_GENERATE_NAMESPACE):saved},
        "content":[{"type":"paragraph","attrs":{"block_id":"openmaic_outline_generate_candidate"},
            "content":[{"type":"text","text":title.clone()}]}]});
    let internal_id = openmaic_outline_generate_internal_request_id(create_request_id);
    let document =
        crate::document::create_optional_tx(&tx, None, None, &title, editor, Some(&internal_id))?;
    let document_id = document["document_id"]
        .as_str()
        .ok_or_else(|| invalid("OpenMAIC outline document ID missing"))?;
    let verified = crate::document::read_verified(&tx, document_id, Some(1))?;
    let receipt = generation_receipt(&tx, verified);
    tx.commit()?;
    Ok(receipt)
}
