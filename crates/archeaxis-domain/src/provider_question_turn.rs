//! DeepTutor's donor single-question step as a Core-owned candidate route.
//!
//! This route captures the donor prompt from a pinned local worker, sends the
//! captured system/user pair through a versioned single-response prompt adapter,
//! replays the unchanged model reply through the same worker and persists only a
//! `CANDIDATE` as an ordinary Core Document. It writes no activity or attempt, runs no grader and
//! establishes no answer secrecy: the body is visible text a human must review.
use crate::{
    document::{self, Error},
    openmaic_outline,
    provider_material_grant::{self as grant, Snapshot},
    ui_state,
};
use archeaxis_store_sqlite::authorization_fence;
use rusqlite::{Connection, TransactionBehavior, params};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

pub const DOCUMENT_NAMESPACE: &str = "archeaxis_deeptutor_question_turn_candidate";
pub const DOCUMENT_SCHEMA: &str = "archeaxis.deeptutor-question-turn-document/v1";
pub const BINDING_SCHEMA: &str = "archeaxis.deeptutor-question-turn-prompt-binding/v1";
pub const MODEL_PROMPT_BINDING_SCHEMA: &str = "archeaxis.deeptutor-question-model-prompt/v1";
const MODEL_PROMPT_ADAPTER: &str = "aaos-direct-json/v2";
pub const CHOICE_SCHEMA_MODE: &str = "choice_json_schema";
const CHOICE_SCHEMA_REQUEST_KIND: &str = "deeptutor_choice_json_schema";
pub const WORKER_SCHEMA: &str = "archeaxis.deeptutor-question-turn-replay/v1";
pub const RECEIPT_SCHEMA: &str = "archeaxis.deeptutor-question-turn-persistence/v1";
pub const GENERATION_ROUTE: &str = "deeptutor_question_turn_local_model";
/// The donor step is driven through the one Python worker declared beside the
/// practice import worker. The model call reuses the already declared local
/// text-model capability rather than a second implementation.
pub const WORKER_CAPABILITY: &str = "deeptutor.question.turn";

const MAX_REQUIREMENT_CHARS: usize = 8_000;
const MAX_REQUIREMENT_BYTES: usize = 12_000;
/// The donor worker's own `exploration_trace` bound.
const MAX_MATERIAL_TEXT_BYTES: usize = 80_000;
/// The donor worker's own input line bound.
const MAX_WORKER_FRAME: usize = 256 * 1024;
const MAX_QUESTION_BYTES: usize = 80_000;
const MAX_OPTION_BYTES: usize = 20_000;
const QUESTION_TYPE: &str = "choice";
const DIFFICULTY: &str = "medium";
const CHOICES: [&str; 4] = ["A", "B", "C", "D"];

/// The bounded generate contract the human caller may send.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct QuestionTurnRequest {
    pub create_request_id: String,
    pub material: Snapshot,
    pub requirement: String,
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub output_mode: Option<String>,
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

fn valid_model(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 256
        && value == value.trim()
        && !value.chars().any(char::is_control)
}

fn bounded_text(value: &str, max_bytes: usize, nonblank: bool) -> bool {
    !value.contains('\0') && value.len() <= max_bytes && (!nonblank || !value.trim().is_empty())
}

fn hex_digest(value: &Value) -> bool {
    value
        .as_str()
        .is_some_and(|text| text.len() == 64 && text.bytes().all(|b| b.is_ascii_hexdigit()))
}

fn now() -> Result<u64, Error> {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .map_err(|_| Error::Invalid("clock unavailable"))
}

/// Name a structurally invalid request before Core reads a grant or starts a
/// worker. `None` means the request may proceed; the write path repeats the
/// same checks.
pub fn request_refusal(request: &QuestionTurnRequest) -> Option<&'static str> {
    if !token(&request.create_request_id)
        || !grant::valid_snapshot_shape(&request.material)
        || !bounded_text(&request.requirement, MAX_REQUIREMENT_BYTES, true)
        || request.requirement.chars().count() > MAX_REQUIREMENT_CHARS
        || request
            .model
            .as_ref()
            .is_some_and(|model| !valid_model(model))
        || request
            .output_mode
            .as_deref()
            .is_some_and(|mode| mode != CHOICE_SCHEMA_MODE)
    {
        return Some("invalid question turn request");
    }
    None
}

fn request_frame(request: &QuestionTurnRequest) -> Value {
    let mut frame = json!({"create_request_id":request.create_request_id,
        "material":request.material,"requirement":request.requirement,"model":request.model});
    if let Some(mode) = &request.output_mode {
        frame["output_mode"] = json!(mode);
    }
    frame
}

pub fn request_sha256(request: &QuestionTurnRequest) -> Result<String, Error> {
    Ok(sha(&request_frame(request)))
}

fn internal_request_id(create_request_id: &str) -> String {
    format!(
        "deeptutor_question_turn_{}",
        digest(create_request_id.as_bytes())
    )
}

/// The ordinary Core Document this request owns, derived only from its ID.
pub fn question_turn_document_id(create_request_id: &str) -> String {
    format!(
        "doc_req_{}",
        digest(internal_request_id(create_request_id).as_bytes())
    )
}

fn question_id(request: &QuestionTurnRequest) -> String {
    let seed = format!(
        "{}|{}|{}|{}",
        request.create_request_id,
        request.material.document_id,
        request.material.version,
        request.requirement
    );
    format!("q_{}", &digest(seed.as_bytes())[..32])
}

fn language(requirement: &str) -> &'static str {
    if requirement
        .chars()
        .any(|c| ('\u{4e00}'..='\u{9fff}').contains(&c))
    {
        "zh"
    } else {
        "en"
    }
}

/// Locate the one current grant a human wrote for exactly this material and
/// consume it. A missing, revoked, expired, foreign-consumer or non-practice
/// grant is refused by the same checks an activity admission uses.
fn consume_material_grant(conn: &Connection, material: &Snapshot) -> Result<(), Error> {
    let mut statement = conn.prepare(
            "SELECT d.document_id, d.current_version, v.content_sha256 \
             FROM documents d JOIN document_versions v \
               ON v.document_id=d.document_id AND v.version=d.current_version \
             WHERE json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.schema')=?4 \
               AND json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.consumer')='deeptutor' \
               AND json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.state')='granted' \
               AND json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.material.document_id')=?1 \
               AND json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.material.version')=?2 \
               AND json_extract(v.editor_json,'$.attrs.archeaxis_provider_material_grant.material.content_sha256')=?3 \
             ORDER BY d.document_id")?;
    let matches = statement.query_map(
        params![
            material.document_id,
            material.version,
            material.content_sha256,
            grant::SCHEMA
        ],
        |row| {
            Ok(Snapshot {
                document_id: row.get(0)?,
                version: row.get(1)?,
                content_sha256: row.get(2)?,
            })
        },
    )?;
    let at = now()?;
    for candidate in matches {
        let candidate = candidate?;
        match grant::consume(conn, &candidate, material, at) {
            Ok(()) => return Ok(()),
            // An expired, revoked, malformed or restored grant never grants
            // access, but must not hide another independently valid grant.
            Err(Error::Invalid(_) | Error::NotFound | Error::Conflict(_)) => continue,
            Err(error @ Error::Sql(_)) => return Err(error),
        }
    }
    Err(Error::Invalid("provider material access not authorized"))
}

fn material_text(conn: &Connection, material: &Snapshot) -> Result<String, Error> {
    let snapshot = document::read_verified(conn, &material.document_id, Some(material.version))?;
    if snapshot["content_sha256"] != material.content_sha256 {
        return Err(Error::Invalid("material snapshot hash mismatch"));
    }
    let text = snapshot["text_projection"]
        .as_str()
        .ok_or(Error::Invalid("material has no text"))?;
    if text.len() > MAX_MATERIAL_TEXT_BYTES {
        return Err(Error::Invalid(
            "material text exceeds the donor question bound",
        ));
    }
    Ok(text.to_owned())
}

fn pending_base(request: &QuestionTurnRequest, material_text: &str, question_id: &str) -> Value {
    let template = json!({"question_id":question_id,"topic":request.requirement,
        "question_type":QUESTION_TYPE,"difficulty":DIFFICULTY,"source":"custom",
        "reference_question":"","reference_answer":""});
    json!({"schema":WORKER_SCHEMA,"request_id":request.create_request_id,
        "language":language(&request.requirement),
        "plan":{"analysis":request.requirement,"templates":[template]},
        "question_number":1,"exploration_trace":material_text,"previous_questions":[]})
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

/// A private, in-process preparation captured before any worker or model call.
pub struct QuestionTurnPending {
    create_request_id: String,
    request_sha256: String,
    restore_epoch: Option<String>,
    workspace_id: String,
    base: Value,
    question_id: String,
    capture_frame: Vec<u8>,
}

impl QuestionTurnPending {
    /// The exact bounded capture line. The caller owns the worker lifecycle.
    pub fn capture_frame(&self) -> &[u8] {
        &self.capture_frame
    }

    /// The replay line over the same plan and the captured prompt identity.
    pub fn replay_frame(
        &self,
        expected_prompt_sha256: &str,
        response_body: &str,
    ) -> Result<Vec<u8>, Error> {
        let mut replay = self.base.clone();
        replay["mode"] = json!("replay");
        replay["expected_prompt_sha256"] = json!(expected_prompt_sha256);
        replay["response_body"] = json!(response_body);
        worker_frame(&replay)
    }

    pub fn question_id(&self) -> &str {
        &self.question_id
    }
}

pub enum QuestionTurnPreparation {
    /// A committed candidate is a history read, never a second execution.
    Existing(Value),
    Pending(QuestionTurnPending),
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
        "generation_route":saved["generation_route"],"model_call":saved["model_call"],
        "model":saved["model"],"model_observed":saved["model_observed"],
        "model_reply_sha256":saved["model_reply_sha256"],
        "model_finish_reason":saved["model_finish_reason"],
        "model_usage":saved["model_usage"],
        "capture_binding":saved["capture_binding"],
        "model_prompt_binding":saved["model_prompt_binding"],
        "model_response_format":saved["model_response_format"],"material":saved["material"],
        "question":saved["question"],"answer_secrecy":saved["answer_secrecy"],
        "response_origin":saved["response_origin"],
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false})
}

fn existing(
    conn: &Connection,
    create_request_id: &str,
    request_sha256: &str,
) -> Result<Option<Value>, Error> {
    let id = question_turn_document_id(create_request_id);
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
    check_generation(
        create_request_id,
        &saved["capture_binding"],
        &saved["model_reply"],
        &saved["worker_document"],
    )?;
    // Old v1 candidates were created before a model prompt adapter existed.
    // New records carry a separately inspectable, internally consistent binding.
    if let Some(model_prompt) = saved.get("model_prompt_binding") {
        if !model_prompt_binding_shape(&saved["capture_binding"], model_prompt) {
            return Err(Error::Invalid(
                "DeepTutor model prompt binding is unsupported",
            ));
        }
    }
    if let Some(format) = saved
        .get("model_response_format")
        .filter(|value| !value.is_null())
    {
        let expected = choice_response_format_binding();
        if *format != expected
            || saved["request_frame"]["output_mode"] != CHOICE_SCHEMA_MODE
            || saved["model_reply"]["response_format_sha256"] != expected["sha256"]
        {
            return Err(Error::Invalid(
                "DeepTutor model response format binding is unsupported",
            ));
        }
    }
    Ok(Some(receipt(conn, document)))
}

/// Check a retry and capture the restore identity inside one Core transaction
/// before capturing a prompt or calling a model.
pub fn prepare_question_turn(
    conn: &mut Connection,
    request: &QuestionTurnRequest,
) -> Result<QuestionTurnPreparation, Error> {
    if request_refusal(request).is_some() {
        return Err(Error::Invalid("invalid question turn request"));
    }
    let request_sha256 = request_sha256(request)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    if let Some(value) = existing(&tx, &request.create_request_id, &request_sha256)? {
        tx.commit()?;
        return Ok(QuestionTurnPreparation::Existing(value));
    }
    grant::assert_material(&tx, &request.material)?;
    consume_material_grant(&tx, &request.material)?;
    let restore_epoch = authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = ui_state::workspace_id(&tx)
        .map_err(|_| Error::Invalid("question turn workspace identity unavailable"))?;
    let text = material_text(&tx, &request.material)?;
    tx.commit()?;

    let id = question_id(request);
    let base = pending_base(request, &text, &id);
    let mut capture = base.clone();
    capture["mode"] = json!("capture");
    let capture_frame = worker_frame(&capture)?;
    Ok(QuestionTurnPreparation::Pending(QuestionTurnPending {
        create_request_id: request.create_request_id.clone(),
        request_sha256,
        restore_epoch,
        workspace_id,
        base,
        question_id: id,
        capture_frame,
    }))
}

/// The capture receipt's prompt identity, or a named refusal. This binding
/// keeps the donor's original messages; the model-bound prompt is stored separately.
pub fn capture_binding(create_request_id: &str, capture: &Value) -> Result<Value, Error> {
    if capture["schema"] != WORKER_SCHEMA
        || capture["status"] != "CAPTURED"
        || capture["mode"] != "capture"
        || capture["request_id"].as_str() != Some(create_request_id)
        || !hex_digest(&capture["prompt_sha256"])
        || capture["model_call"] != "NOT_INVOKED"
        || capture["upstream_agentic_loop"] != "NOT_INVOKED"
        || capture["origin"] != "CALLER_SUPPLIED_UNVERIFIED"
        || capture["core_authorization"] != "NOT_ESTABLISHED"
        || capture["privacy_filter"] != "NOT_APPLIED"
        || capture["original_input_preserved"] != false
        || capture["loss_receipt"] != "NOT_GENERATED"
    {
        return Err(Error::Invalid(
            "DeepTutor capture receipt does not match the request",
        ));
    }
    let messages = capture["messages"]
        .as_array()
        .filter(|items| items.len() == 2)
        .ok_or(Error::Invalid("DeepTutor capture messages are unsupported"))?;
    if messages[0]["role"] != "system" || messages[1]["role"] != "user" {
        return Err(Error::Invalid(
            "DeepTutor capture message roles are unsupported",
        ));
    }
    let system = messages[0]["content"]
        .as_str()
        .filter(|text| bounded_text(text, 200_000, true))
        .ok_or(Error::Invalid(
            "DeepTutor capture system prompt is unsupported",
        ))?;
    let user = messages[1]["content"]
        .as_str()
        .filter(|text| bounded_text(text, 200_000, true))
        .ok_or(Error::Invalid(
            "DeepTutor capture user prompt is unsupported",
        ))?;
    if system.len() + user.len() > 300_000 {
        return Err(Error::Invalid(
            "DeepTutor capture prompt exceeds the model bound",
        ));
    }
    Ok(
        json!({"schema":BINDING_SCHEMA,"request_id":create_request_id,
        "prompt_sha256":capture["prompt_sha256"],
        "system":system,"user":user,
        "system_sha256":digest(system.as_bytes()),"user_sha256":digest(user.as_bytes()),
        "messages":messages}),
    )
}

fn binding_shape(binding: &Value, create_request_id: &str) -> bool {
    binding
        .as_object()
        .is_some_and(|object| object.len() == 8 && binding["schema"] == BINDING_SCHEMA)
        && binding["request_id"].as_str() == Some(create_request_id)
        && hex_digest(&binding["prompt_sha256"])
        && binding["system"]
            .as_str()
            .is_some_and(|text| bounded_text(text, 200_000, true))
        && binding["user"]
            .as_str()
            .is_some_and(|text| bounded_text(text, 200_000, true))
        && binding["system_sha256"].as_str().is_some_and(|value| {
            value == digest(binding["system"].as_str().unwrap_or("").as_bytes())
        })
        && binding["user_sha256"]
            .as_str()
            .is_some_and(|value| value == digest(binding["user"].as_str().unwrap_or("").as_bytes()))
}

/// Adapt only the donor's agentic output protocol, which conflicts with the
/// pinned replay worker's strict single-JSON contract. Preserve its schema and
/// the original captured binding; ambiguous or changed anchors fail closed.
pub fn model_prompt_binding(binding: &Value) -> Result<Value, Error> {
    let request_id = binding["request_id"].as_str().unwrap_or("");
    if !binding_shape(binding, request_id) || !token(request_id) {
        return Err(Error::Invalid("DeepTutor prompt binding is unsupported"));
    }
    let system = binding["system"].as_str().unwrap_or("");
    let protocols = [
        (
            "# 输出协议（强制）",
            "# FINISH 的 JSON schema（严格）",
            "# AAOS 单次输出协议\n直接输出一个符合下方 schema 的完整 JSON 对象。不要输出 FINISH、THINK、TOOL 标签、额外说明或 Markdown 代码块；不调用工具。对象必须且只能包含 question_type、question、options、correct_answer、explanation；question_type 必须是 choice，options 恰好包含 A、B、C、D，correct_answer 必须是其中一个字母。JSON 字符串中的反斜杠、双引号和换行必须按 JSON 规则转义；LaTeX 中的反斜杠也必须写成两个反斜杠。\n\n",
        ),
        (
            "# Output protocol (mandatory — every reply must comply)",
            "# FINISH JSON schema (strict)",
            "# AAOS single-response protocol\nReturn exactly one complete JSON object matching the schema below. Do not output FINISH, THINK or TOOL labels, extra prose or Markdown fences; do not call tools. The object must contain exactly question_type, question, options, correct_answer and explanation; question_type must be choice, options must contain exactly A, B, C and D, and correct_answer must be one of those letters. Escape backslashes, double quotes and line breaks in JSON strings; double every LaTeX backslash as well.\n\n",
        ),
    ];
    let mut selected = None;
    for (start, end, replacement) in protocols {
        let starts: Vec<_> = system.match_indices(start).map(|(i, _)| i).collect();
        let ends: Vec<_> = system.match_indices(end).map(|(i, _)| i).collect();
        if starts.is_empty() && ends.is_empty() {
            continue;
        }
        if starts.len() != 1 || ends.len() != 1 || starts[0] >= ends[0] || selected.is_some() {
            return Err(Error::Invalid(
                "DeepTutor prompt adapter anchors unsupported",
            ));
        }
        selected = Some((starts[0], ends[0], replacement));
    }
    let (start, end, replacement) = selected.ok_or(Error::Invalid(
        "DeepTutor prompt adapter anchors unsupported",
    ))?;
    let adapted = format!("{}{}{}", &system[..start], replacement, &system[end..]);
    let user = binding["user"].as_str().unwrap_or("");
    if !bounded_text(&adapted, 200_000, true) || adapted.len() + user.len() > 300_000 {
        return Err(Error::Invalid(
            "DeepTutor adapted prompt exceeds the model bound",
        ));
    }
    Ok(
        json!({"schema":MODEL_PROMPT_BINDING_SCHEMA,"adapter":MODEL_PROMPT_ADAPTER,
        "donor_prompt_sha256":binding["prompt_sha256"],"system":adapted,
        "system_sha256":digest(adapted.as_bytes()),"user_sha256":binding["user_sha256"]}),
    )
}

fn model_prompt_binding_shape(binding: &Value, model_prompt: &Value) -> bool {
    model_prompt
        .as_object()
        .is_some_and(|object| object.len() == 6)
        && model_prompt["schema"] == MODEL_PROMPT_BINDING_SCHEMA
        && matches!(
            model_prompt["adapter"].as_str(),
            Some("aaos-direct-json/v1" | "aaos-direct-json/v2")
        )
        && model_prompt["donor_prompt_sha256"] == binding["prompt_sha256"]
        && model_prompt["user_sha256"] == binding["user_sha256"]
        && model_prompt["system"].as_str().is_some_and(|text| {
            bounded_text(text, 200_000, true)
                && model_prompt["system_sha256"] == digest(text.as_bytes())
                && text.len() + binding["user"].as_str().unwrap_or("").len() <= 300_000
        })
}

/// The fixed OpenAI-compatible grammar used only by explicit choice mode.
pub fn choice_response_format() -> Value {
    json!({"type":"json_schema","json_schema":{"name":"archeaxis_response","strict":true,
    "schema":{"type":"object","additionalProperties":false,
        "required":["question_type","question","options","correct_answer","explanation"],
        "properties":{
            "question_type":{"type":"string","enum":["choice"]},
            "question":{"type":"string"},
            "options":{"type":"object","additionalProperties":false,
                "required":["A","B","C","D"],"properties":{
                    "A":{"type":"string"},"B":{"type":"string"},
                    "C":{"type":"string"},"D":{"type":"string"}}},
            "correct_answer":{"type":"string","enum":["A","B","C","D"]},
            "explanation":{"type":"string"}
        }}}})
}

fn choice_response_format_binding() -> Value {
    let format = choice_response_format();
    json!({"mode":CHOICE_SCHEMA_MODE,"response_format":format,"sha256":sha(&format)})
}

fn response_format_binding(request: &QuestionTurnRequest) -> Value {
    if request.output_mode.as_deref() == Some(CHOICE_SCHEMA_MODE) {
        choice_response_format_binding()
    } else {
        Value::Null
    }
}

/// A format-bound request cannot accept an older or different model worker's
/// reply without evidence that the fixed format was actually sent.
pub fn model_reply_format_matches(request: &QuestionTurnRequest, reply: &Value) -> bool {
    if request.output_mode.as_deref() == Some(CHOICE_SCHEMA_MODE) {
        reply["response_format_sha256"] == choice_response_format_binding()["sha256"]
    } else {
        reply
            .get("response_format_sha256")
            .is_none_or(Value::is_null)
    }
}

/// Send the adapted system and the unchanged captured user prompt through the
/// same bounded local-model transport as the outline route.
pub fn model_request(
    binding: &Value,
    model_prompt: &Value,
    request: &QuestionTurnRequest,
) -> Value {
    let mut frame = json!({"schema":openmaic_outline::OPENMAIC_OUTLINE_MODEL_REQUEST_SCHEMA,
        "system":model_prompt["system"],"user":binding["user"],"timeout_s":110});
    if let Some(model) = &request.model {
        frame["model"] = json!(model);
    }
    if request.output_mode.as_deref() == Some(CHOICE_SCHEMA_MODE) {
        frame["request_kind"] = json!(CHOICE_SCHEMA_REQUEST_KIND);
    }
    frame
}

fn choices(value: &Value) -> bool {
    value.as_object().is_some_and(|options| {
        options.len() == CHOICES.len()
            && CHOICES.iter().all(|key| {
                options.get(*key).is_some_and(|option| {
                    option
                        .as_str()
                        .is_some_and(|text| bounded_text(text, MAX_OPTION_BYTES, true))
                })
            })
    })
}

/// The replay receipt must belong to the frame Core actually built: the same
/// prompt identity, a candidate question of the fixed shape and nothing else.
fn check_generation(
    create_request_id: &str,
    binding: &Value,
    model_reply: &Value,
    replay: &Value,
) -> Result<(), Error> {
    if openmaic_outline::openmaic_outline_model_content(model_reply).is_none() {
        return Err(Error::Invalid(
            "DeepTutor model reply was not admitted for replay",
        ));
    }
    if !binding_shape(binding, create_request_id) {
        return Err(Error::Invalid("DeepTutor prompt binding is unsupported"));
    }
    if replay["schema"] != WORKER_SCHEMA
        || replay["status"] != "CANDIDATE"
        || replay["mode"] != "replay"
        || replay["request_id"].as_str() != Some(create_request_id)
        || replay["prompt_sha256"] != binding["prompt_sha256"]
        || replay["model_call"] != "NOT_INVOKED"
        || replay["origin"] != "CALLER_SUPPLIED_UNVERIFIED"
        || replay["core_authorization"] != "NOT_ESTABLISHED"
        || replay["answer_correctness"] != "NOT_VERIFIED"
        || replay["privacy_filter"] != "NOT_APPLIED"
    {
        return Err(Error::Invalid(
            "DeepTutor replay receipt does not match the request",
        ));
    }
    let options = replay["question"]["options"]
        .as_object()
        .ok_or(Error::Invalid(
            "DeepTutor question candidate is unsupported",
        ))?;
    if !choices(&replay["question"]["options"]) {
        return Err(Error::Invalid(
            "DeepTutor question candidate is unsupported",
        ));
    }
    let id = replay["question"]["question_id"]
        .as_str()
        .ok_or(Error::Invalid("DeepTutor question identity missing"))?;
    if !token(id)
        || !replay["question"]["question"]
            .as_str()
            .is_some_and(|text| bounded_text(text, MAX_QUESTION_BYTES, true))
        || replay["question"]["question_type"] != QUESTION_TYPE
        || options.len() != CHOICES.len()
    {
        return Err(Error::Invalid(
            "DeepTutor question candidate is unsupported",
        ));
    }
    Ok(())
}

/// The three audited stage results. Core keeps the capture binding, the model
/// receipt and the worker's replay document verbatim; nothing is rewritten.
#[derive(Clone)]
pub struct QuestionTurnGeneration {
    pub capture_document: Value,
    pub model_prompt_binding: Value,
    pub model_reply: Value,
    pub replay_document: Value,
}

/// Persist one inert candidate. Every stage is re-checked, the material grant is
/// consumed again and the exact frames Core sent are stored beside the receipts.
pub fn commit_question_turn(
    conn: &mut Connection,
    request: &QuestionTurnRequest,
    pending: &QuestionTurnPending,
    generation: &QuestionTurnGeneration,
) -> Result<Value, Error> {
    if request_refusal(request).is_some()
        || request.create_request_id != pending.create_request_id
        || request_sha256(request)? != pending.request_sha256
    {
        return Err(Error::Invalid(
            "question turn request changed after admission",
        ));
    }
    let binding = capture_binding(&request.create_request_id, &generation.capture_document)?;
    if model_prompt_binding(&binding)? != generation.model_prompt_binding {
        return Err(Error::Invalid("DeepTutor model prompt binding mismatch"));
    }
    if openmaic_outline::openmaic_outline_new_model_content(&generation.model_reply).is_none()
        || !model_reply_format_matches(request, &generation.model_reply)
    {
        return Err(Error::Invalid(
            "DeepTutor model reply was not admitted for replay",
        ));
    }
    check_generation(
        &request.create_request_id,
        &binding,
        &generation.model_reply,
        &generation.replay_document,
    )?;
    let question = &generation.replay_document["question"];
    if question["question_id"].as_str() != Some(pending.question_id.as_str()) {
        return Err(Error::Invalid("DeepTutor question binding mismatch"));
    }
    let content = openmaic_outline::openmaic_outline_model_content(&generation.model_reply).ok_or(
        Error::Invalid("DeepTutor model reply was not admitted for replay"),
    )?;
    let mut replay = pending.base.clone();
    replay["mode"] = json!("replay");
    replay["expected_prompt_sha256"] = binding["prompt_sha256"].clone();
    replay["response_body"] = json!(content);
    let replay_frame = worker_frame(&replay)?;
    let capture_frame = String::from_utf8(pending.capture_frame.clone())
        .map_err(|_| Error::Invalid("capture frame is not text"))?;
    let replay_frame =
        String::from_utf8(replay_frame).map_err(|_| Error::Invalid("replay frame is not text"))?;

    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let epoch = authorization_fence::authorization_epoch(&tx)?;
    let workspace_id = ui_state::existing_workspace_id(&tx)
        .map_err(|_| Error::Invalid("question turn workspace identity unavailable"))?;
    if epoch != pending.restore_epoch
        || workspace_id.as_deref() != Some(pending.workspace_id.as_str())
    {
        return Err(Error::Invalid(
            "question turn workspace or restore epoch changed",
        ));
    }
    grant::assert_material(&tx, &request.material)?;
    consume_material_grant(&tx, &request.material)?;
    // Two concurrent requests may have passed preparation. Never replace the
    // first candidate with a second run's text.
    if let Some(existing) = existing(&tx, &request.create_request_id, &pending.request_sha256)? {
        tx.commit()?;
        return Ok(existing);
    }
    let body = question["question"].as_str().unwrap_or_default();
    let title = format!(
        "DeepTutor question candidate · {}",
        body.chars().take(120).collect::<String>()
    );
    let options = question["options"].as_object().cloned().unwrap_or_default();
    let mut content_nodes = vec![json!({"type":"paragraph",
        "content":[{"type":"text","text":body}]})];
    for key in CHOICES {
        if let Some(option) = options.get(key).and_then(Value::as_str) {
            content_nodes.push(json!({"type":"paragraph",
                "content":[{"type":"text","text":format!("{key}. {option}")}]}));
        }
    }
    let saved = json!({
        "schema":DOCUMENT_SCHEMA,
        "create_request_id":request.create_request_id,
        "generation_request_sha256":pending.request_sha256,
        "generation_route":GENERATION_ROUTE,
        "model_call":"INVOKED",
        "model":generation.model_reply["model"],
        "model_observed":generation.model_reply["observed_model"],
        "model_reply_sha256":generation.model_reply["content_sha256"],
        "model_reply_bytes":generation.model_reply["content_bytes"],
        "model_finish_reason":generation.model_reply["finish_reason"],
        "model_usage":generation.model_reply["usage"],
        "model_reply":generation.model_reply,
        "capture_binding":binding,
        "model_prompt_binding":generation.model_prompt_binding,
        "model_response_format":response_format_binding(request),
        "worker_document":generation.replay_document,
        "question":question,
        "material":request.material,
        "request_frame":request_frame(request),
        "capture_frame":capture_frame,
        "replay_frame":replay_frame,
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,
        "active_content_executed":false,
        "rendering_authorized":false,
        "answer_secrecy":"not_established",
    });
    let editor = json!({"type":"doc","attrs":{(DOCUMENT_NAMESPACE):saved},"content":content_nodes});
    let internal = internal_request_id(&request.create_request_id);
    let document = document::create_optional_tx(&tx, None, None, &title, editor, Some(&internal))?;
    let id = document["document_id"]
        .as_str()
        .ok_or(Error::Invalid("created question identity unavailable"))?;
    let verified = document::read_verified(&tx, id, Some(1))?;
    if verified["content_sha256"] != document["content_sha256"]
        || verified["editor_json"]["attrs"][DOCUMENT_NAMESPACE]["question"]["question_id"]
            != json!(pending.question_id)
    {
        return Err(Error::Invalid("created question identity mismatch"));
    }
    let result = receipt(&tx, verified);
    tx.commit()?;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn requirement_and_model_bounds_are_refused_before_any_work() {
        let base = QuestionTurnRequest {
            create_request_id: "client_1".into(),
            material: Snapshot {
                document_id: "doc_material".into(),
                version: 1,
                content_sha256: "0".repeat(64),
            },
            requirement: "Synthetic requirement".into(),
            model: None,
            output_mode: None,
        };
        assert_eq!(request_refusal(&base), None);
        let mut extra = base.clone();
        extra.create_request_id = "not a token".into();
        assert!(request_refusal(&extra).is_some());
        let mut long = base.clone();
        long.requirement = "x".repeat(8_001);
        assert!(request_refusal(&long).is_some());
        let mut blank = base;
        blank.requirement = "   ".into();
        assert!(request_refusal(&blank).is_some());
    }

    #[test]
    fn language_and_question_identity_are_deterministic() {
        assert_eq!(language("Synthetic arithmetic"), "en");
        assert_eq!(language("请解释这个例子"), "zh");
        let request = QuestionTurnRequest {
            create_request_id: "client_1".into(),
            material: Snapshot {
                document_id: "doc_material".into(),
                version: 1,
                content_sha256: "0".repeat(64),
            },
            requirement: "Synthetic requirement".into(),
            model: None,
            output_mode: None,
        };
        assert_eq!(question_id(&request), question_id(&request.clone()));
        assert!(token(&question_id(&request)));
        assert_eq!(
            question_turn_document_id("client_1"),
            question_turn_document_id("client_1")
        );
        assert_ne!(
            question_turn_document_id("client_1"),
            question_turn_document_id("client_2")
        );
    }
}
