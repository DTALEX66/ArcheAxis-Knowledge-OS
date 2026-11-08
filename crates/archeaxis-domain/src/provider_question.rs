//! Local, version-bound candidate questions for the DeepTutor adapter.
//!
//! This is a read-only projection, not provider execution or authorization.
//! Ordinary Document reads and exports retain the full editor, including any
//! answer key. This projection suppresses those fields only in the practice
//! view; neither its digest nor this workspace is an answer-secrecy boundary.
use crate::{
    document::{self, Error},
    provider_material_grant::{self as grant, Snapshot},
    ui_state,
};
use archeaxis_store_sqlite::{authorization_fence, raw_objects};
use base64::{Engine as _, engine::general_purpose::STANDARD};
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::{
    Deserialize, Deserializer, Serialize,
    de::{self, MapAccess, SeqAccess, Visitor},
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

const NAMESPACE: &str = "archeaxis_deeptutor_question";
const SCHEMA: &str = "archeaxis.deeptutor-question/v1";
const PRACTICE_HOST_SCHEMA: &str = "archeaxis.deeptutor-practice-host-worker/v1";
const MAX_PRACTICE_SOURCE: usize = 5 * 1024 * 1024;
const MAX_PRACTICE_FRAME: usize = ((MAX_PRACTICE_SOURCE + 2) / 3) * 4 + 65_536;
const MAX_PRACTICE_REPLY: usize = 1024 * 1024 + 65_536;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Candidate {
    schema: String,
    source_material: Snapshot,
    origin: String,
    #[serde(default)]
    upstream_entry_id: Option<String>,
    question: Question,
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Question {
    question_id: String,
    question: String,
    question_type: String,
    options: BTreeMap<String, String>,
    correct_answer: String,
    #[serde(default)]
    explanation: String,
}

fn text(value: &str, max: usize, nonblank: bool) -> bool {
    !value.contains('\0') && value.len() <= max && (!nonblank || !value.trim().is_empty())
}

fn token(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 256
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"_-".contains(&b))
}

fn validate(value: &Candidate, question_document: &Snapshot) -> Result<(), Error> {
    let question = &value.question;
    if value.schema != SCHEMA
        || value.origin != "user_import_unverified"
        || !grant::valid_snapshot_shape(&value.source_material)
        || value.source_material.document_id == question_document.document_id
        || value
            .upstream_entry_id
            .as_ref()
            .is_some_and(|id| !text(id, 1024, true))
        || !token(&question.question_id)
        || !text(&question.question, 128_000, true)
        || !text(&question.question_type, 128, false)
        || !text(&question.correct_answer, 20_000, false)
        || !text(&question.explanation, 128_000, false)
        || question.options.len() > 64
        || question
            .options
            .iter()
            .any(|(key, option)| !text(key, 256, true) || !text(option, 20_000, false))
    {
        return Err(Error::Invalid("invalid DeepTutor question candidate"));
    }
    Ok(())
}

fn sha(value: &Value) -> String {
    hex::encode(Sha256::digest(value.to_string().as_bytes()))
}

/// A trusted human-facing host supplies this request after Core has imported
/// the original source. `source_duplicate` is the import operation's reported
/// flag, not proof of a new origin or authorization. The ordinary import does
/// not require a provider grant and does not contact the provider or a model.
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PracticeImportRequest {
    pub request_id: String,
    pub source_id: String,
    pub source_sha256: String,
    pub source_duplicate: bool,
    pub source_format: String,
    pub source_row: u64,
    pub material_snapshot: Snapshot,
    pub question_id: String,
    pub create_request_id: String,
    pub title: String,
}

/// A private, in-process preparation captured before invoking the worker.
/// Its frame contains the original source bytes and must not be logged, put
/// into a generic job result, or returned to a learner. It intentionally has
/// no `Debug` or serialization implementation.
pub struct PracticeImportPlan {
    request: PracticeImportRequest,
    workspace_id: String,
    restore_epoch: Option<String>,
    worker_frame: Vec<u8>,
    worker_frame_sha256: String,
}

impl PracticeImportPlan {
    /// Exact bounded JSON line to send to the dedicated private worker. The
    /// host must close stdin and retain the frame's privacy through cleanup.
    pub fn worker_frame(&self) -> &[u8] {
        &self.worker_frame
    }
}

fn practice_source(conn: &Connection, source_id: &str, expected: &str) -> Result<(), Error> {
    let stored: Option<String> = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [source_id],
            |row| row.get(0),
        )
        .optional()?;
    if stored.as_deref() != Some(expected) {
        return Err(Error::Invalid("practice source identity mismatch"));
    }
    Ok(())
}

fn practice_document_id(request_id: &str) -> String {
    format!(
        "doc_req_{}",
        hex::encode(Sha256::digest(request_id.as_bytes()))
    )
}

/// Capture the Core-owned source, selected material and restore identity.
/// The caller must independently enforce the human actor and own the worker
/// lifecycle. No provider authorization is needed for this local import.
pub fn prepare_practice_import(
    conn: &mut Connection,
    request: &PracticeImportRequest,
) -> Result<PracticeImportPlan, Error> {
    if !token(&request.request_id)
        || request.request_id.len() > 128
        || request.source_id.is_empty()
        || !text(&request.source_id, 128, false)
        || request.source_sha256.len() != 64
        || !request
            .source_sha256
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        || !matches!(request.source_format.as_str(), "csv" | "tsv" | "json")
        || !(1..=502).contains(&request.source_row)
        || !grant::valid_snapshot_shape(&request.material_snapshot)
        || !token(&request.question_id)
        || !token(&request.create_request_id)
        || request.create_request_id.len() > 128
        || !text(&request.title, 1024, false)
        || request.material_snapshot.document_id == practice_document_id(&request.create_request_id)
    {
        return Err(Error::Invalid("invalid practice import request"));
    }

    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    practice_source(&tx, &request.source_id, &request.source_sha256)?;
    grant::assert_material(&tx, &request.material_snapshot)?;
    let workspace_id = ui_state::workspace_id(&tx)
        .map_err(|_| Error::Invalid("practice workspace identity unavailable"))?;
    let restore_epoch = authorization_fence::authorization_epoch(&tx)?;
    tx.commit()?;

    // Bound the source read outside the write transaction. A restore or source
    // change before publication is checked again under the final transaction.
    let bytes = raw_objects::read_bounded(conn, &request.source_sha256, MAX_PRACTICE_SOURCE)?;
    if bytes.is_empty() {
        return Err(Error::Invalid("practice source is empty"));
    }
    let frame = json!({"schema":PRACTICE_HOST_SCHEMA,"request_id":request.request_id,
        "source":{"format":request.source_format,"content_base64":STANDARD.encode(&bytes),"sha256":request.source_sha256},
        "source_row":request.source_row,"material_snapshot":request.material_snapshot,
        "question_id":request.question_id,"create_request_id":request.create_request_id,
        "title":request.title,"import_receipt":{"source_id":request.source_id,
            "sha256":request.source_sha256,"duplicate":request.source_duplicate}});
    let mut worker_frame = serde_json::to_vec(&frame)
        .map_err(|_| Error::Invalid("practice worker frame unavailable"))?;
    worker_frame.push(b'\n');
    if worker_frame.len() > MAX_PRACTICE_FRAME {
        return Err(Error::Invalid("practice worker frame exceeds limit"));
    }
    let worker_frame_sha256 = hex::encode(Sha256::digest(&worker_frame));
    Ok(PracticeImportPlan {
        request: request.clone(),
        workspace_id,
        restore_epoch,
        worker_frame,
        worker_frame_sha256,
    })
}

// A worker line is parsed without permitting duplicate object names at any
// depth, including inside options and editor attributes. The result remains
// private and no parse error includes input text.
struct UniqueJson(Value);
impl<'de> Deserialize<'de> for UniqueJson {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct UniqueVisitor;
        impl<'de> Visitor<'de> for UniqueVisitor {
            type Value = UniqueJson;
            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                f.write_str("JSON with unique object names")
            }
            fn visit_bool<E: de::Error>(self, value: bool) -> Result<Self::Value, E> {
                Ok(UniqueJson(json!(value)))
            }
            fn visit_i64<E: de::Error>(self, value: i64) -> Result<Self::Value, E> {
                Ok(UniqueJson(json!(value)))
            }
            fn visit_u64<E: de::Error>(self, value: u64) -> Result<Self::Value, E> {
                Ok(UniqueJson(json!(value)))
            }
            fn visit_f64<E: de::Error>(self, value: f64) -> Result<Self::Value, E> {
                serde_json::Number::from_f64(value)
                    .map(|n| UniqueJson(Value::Number(n)))
                    .ok_or_else(|| E::custom("invalid number"))
            }
            fn visit_str<E: de::Error>(self, value: &str) -> Result<Self::Value, E> {
                Ok(UniqueJson(json!(value)))
            }
            fn visit_string<E: de::Error>(self, value: String) -> Result<Self::Value, E> {
                Ok(UniqueJson(json!(value)))
            }
            fn visit_unit<E: de::Error>(self) -> Result<Self::Value, E> {
                Ok(UniqueJson(Value::Null))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Self::Value, A::Error> {
                let mut values = Vec::new();
                while let Some(value) = seq.next_element::<UniqueJson>()? {
                    values.push(value.0);
                }
                Ok(UniqueJson(Value::Array(values)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
                let mut values = serde_json::Map::new();
                while let Some((key, value)) = map.next_entry::<String, UniqueJson>()? {
                    if values.contains_key(&key) {
                        return Err(de::Error::custom("duplicate object name"));
                    }
                    values.insert(key, value.0);
                }
                Ok(UniqueJson(Value::Object(values)))
            }
        }
        deserializer.deserialize_any(UniqueVisitor)
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PracticeWorkerDocument {
    create_request_id: String,
    source_id: String,
    source_revision: String,
    title: String,
    editor_json: Value,
}

fn private_worker_document(
    plan: &PracticeImportPlan,
    line: &[u8],
) -> Result<PracticeWorkerDocument, Error> {
    if line.is_empty()
        || line.len() > MAX_PRACTICE_REPLY
        || line.last() != Some(&b'\n')
        || line[..line.len() - 1]
            .iter()
            .any(|&byte| matches!(byte, b'\n' | b'\r'))
    {
        return Err(Error::Invalid("invalid private practice worker frame"));
    }
    let mut parser = serde_json::Deserializer::from_slice(&line[..line.len() - 1]);
    let value = UniqueJson::deserialize(&mut parser)
        .map_err(|_| Error::Invalid("invalid private practice worker JSON"))?
        .0;
    parser
        .end()
        .map_err(|_| Error::Invalid("invalid private practice worker JSON"))?;
    let object = value
        .as_object()
        .ok_or(Error::Invalid("invalid private practice worker result"))?;
    if object.len() != 12
        || value["schema"] != PRACTICE_HOST_SCHEMA
        || value["status"] != "PRIVATE_CANDIDATE"
        || value["request_id"] != plan.request.request_id
        || value["input_sha256"] != plan.worker_frame_sha256
        || value["source_link"] != "PINNED_PARSER_OF_CALLER_BYTES_NOT_AUTHENTICATED"
        || value["import_receipt"] != "CALLER_SUPPLIED_NOT_AUTHENTICATED"
        || value["material_snapshot"] != "CALLER_DECLARED_NOT_AUTHENTICATED"
        || value["row_and_loss_receipt"] != "NOT_RETURNED_OR_PERSISTED_BY_WORKER"
        || value["core_write"] != "NOT_EXECUTED"
        || value["provider_execution"] != "NOT_INVOKED"
        || value["output_privacy_filter"] != "NOT_APPLIED"
    {
        return Err(Error::Invalid("private practice worker result mismatch"));
    }
    let document: PracticeWorkerDocument =
        serde_json::from_value(value["document_create_request"].clone())
            .map_err(|_| Error::Invalid("invalid private practice document"))?;
    if document.create_request_id != plan.request.create_request_id
        || document.source_id != plan.request.source_id
        || document.source_revision != plan.request.source_sha256
        || document.title != plan.request.title
    {
        return Err(Error::Invalid("private practice document binding mismatch"));
    }
    let root = document
        .editor_json
        .as_object()
        .filter(|root| root.len() == 3)
        .ok_or(Error::Invalid("invalid private practice editor"))?;
    let attrs = root
        .get("attrs")
        .and_then(Value::as_object)
        .filter(|attrs| attrs.len() == 1)
        .ok_or(Error::Invalid("invalid private practice editor attributes"))?;
    let candidate: Candidate = serde_json::from_value(
        attrs
            .get(NAMESPACE)
            .cloned()
            .ok_or(Error::Invalid("practice question candidate missing"))?,
    )
    .map_err(|_| Error::Invalid("invalid practice question candidate"))?;
    let future = Snapshot {
        document_id: practice_document_id(&plan.request.create_request_id),
        version: 1,
        content_sha256: "0".repeat(64),
    };
    validate(&candidate, &future)?;
    if candidate.source_material != plan.request.material_snapshot
        || candidate.question.question_id != plan.request.question_id
    {
        return Err(Error::Invalid("practice question binding mismatch"));
    }
    let mut texts = vec![candidate.question.question.clone()];
    texts.extend(
        candidate
            .question
            .options
            .iter()
            .map(|(key, option)| format!("{key}. {option}")),
    );
    let content: Vec<Value> = texts
        .into_iter()
        .map(|text| {
            json!({"type":"paragraph",
        "content":[{"type":"text","text":text}]})
        })
        .collect();
    if root.get("type") != Some(&json!("doc")) || root.get("content") != Some(&json!(content)) {
        return Err(Error::Invalid("practice editor projection mismatch"));
    }
    Ok(document)
}

/// Publish one private worker result through the canonical Core transaction.
/// The caller must authenticate/own the exact worker process, its exit status,
/// cancellation and private pipes, and serialize cancellation against this
/// call. This function validates the captured request and Core bindings; the
/// output alone cannot prove which process generated it or establish mastery.
pub fn finish_practice_import(
    conn: &mut Connection,
    plan: &PracticeImportPlan,
    private_worker_line: &[u8],
) -> Result<Value, Error> {
    let document = private_worker_document(plan, private_worker_line)?;
    // This is a bounded preflight, not a hard limit on the later existing
    // create_optional_tx CAS reread or on concurrent filesystem replacement.
    if raw_objects::read_bounded(conn, &plan.request.source_sha256, MAX_PRACTICE_SOURCE)?.is_empty()
    {
        return Err(Error::Invalid("practice source is empty"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let workspace = ui_state::existing_workspace_id(&tx)
        .map_err(|_| Error::Invalid("practice workspace identity unavailable"))?;
    if workspace.as_deref() != Some(plan.workspace_id.as_str())
        || authorization_fence::authorization_epoch(&tx)? != plan.restore_epoch
    {
        return Err(Error::Invalid(
            "practice workspace or restore epoch changed",
        ));
    }
    practice_source(&tx, &plan.request.source_id, &plan.request.source_sha256)?;
    grant::assert_material(&tx, &plan.request.material_snapshot)?;
    let id = practice_document_id(&plan.request.create_request_id);
    let duplicate: bool = tx.query_row(
        "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
        [&id],
        |row| row.get(0),
    )?;
    let created = document::create_optional_tx(
        &tx,
        Some(&document.source_id),
        Some(&document.source_revision),
        &document.title,
        document.editor_json,
        Some(&document.create_request_id),
    )?;
    let snapshot = Snapshot {
        document_id: created["document_id"]
            .as_str()
            .ok_or(Error::Invalid("created question identity unavailable"))?
            .to_owned(),
        version: created["version"]
            .as_i64()
            .ok_or(Error::Invalid("created question version unavailable"))?,
        content_sha256: created["content_sha256"]
            .as_str()
            .ok_or(Error::Invalid("created question digest unavailable"))?
            .to_owned(),
    };
    if snapshot.document_id != id || snapshot.version != 1 {
        return Err(Error::Invalid("created question identity mismatch"));
    }
    let view = read_view(&tx, &snapshot)?;
    if view["question"]["question_id"] != plan.request.question_id
        || view["source_material"] != json!(plan.request.material_snapshot)
        || !matches!(
            view["source_snapshot_status"].as_str(),
            Some("current" | "historical")
        )
        || view["question_document_origin"] == "portable_historical"
    {
        return Err(Error::Invalid("created question view mismatch"));
    }
    tx.commit()?;
    Ok(
        json!({"schema":"archeaxis.deeptutor-practice-import-result/v1",
        "question_document":snapshot,"question_view":view,"duplicate":duplicate,
        "source_link":"registered_source_and_cas_verified_not_row_proven","provider_execution":"NOT_INVOKED",
        "worker_process_identity":"HOST_RESPONSIBILITY","independent_mastery":"not_established"}),
    )
}

/// Produce a learner-facing view. No material, answer key, explanation,
/// client-claimed provider identity or grant is sent to a worker here.
///
/// When import provenance exists, a portable document remains historical even
/// if the destination has the same local ID. Missing provenance is unverified,
/// not proof of local origin; neither state grants provider access.
pub fn read_view(conn: &Connection, question_document: &Snapshot) -> Result<Value, Error> {
    if !grant::valid_snapshot_shape(question_document) {
        return Err(Error::Invalid("invalid question document snapshot"));
    }
    let snapshot = document::read_verified(
        conn,
        &question_document.document_id,
        Some(question_document.version),
    )?;
    if snapshot["content_sha256"] != question_document.content_sha256 {
        return Err(Error::Invalid("question document snapshot mismatch"));
    }
    let candidate: Candidate = serde_json::from_value(
        snapshot["editor_json"]["attrs"]
            .get(NAMESPACE)
            .cloned()
            .ok_or(Error::Invalid("question candidate missing"))?,
    )
    .map_err(|_| Error::Invalid("invalid question candidate fields"))?;
    validate(&candidate, question_document)?;

    // The import provenance is attached to version 1; later ordinary saves do
    // not erase it. Its absence cannot establish that the origin is local.
    let first = document::read_verified(conn, &question_document.document_id, Some(1))?;
    let portable = first["revision_basis"]["portable_import"].is_object();
    let (source_snapshot_status, question_document_origin) = if portable {
        ("not_compared", "portable_historical")
    } else {
        let status = if grant::assert_material(conn, &candidate.source_material).is_err() {
            "unavailable"
        } else {
            match document::read_verified(conn, &candidate.source_material.document_id, None) {
                Ok(current)
                    if current["version"].as_i64() == Some(candidate.source_material.version)
                        && current["content_sha256"]
                            == candidate.source_material.content_sha256 =>
                {
                    "current"
                }
                Ok(_) => "historical",
                Err(_) => "unavailable",
            }
        };
        (status, "unverified")
    };
    let current_question = document::read_verified(conn, &question_document.document_id, None)?;
    let question_status = if current_question["version"].as_i64() == Some(question_document.version)
        && current_question["content_sha256"] == question_document.content_sha256
    {
        "current"
    } else {
        "historical"
    };

    // The full digest includes the source, all visible fields, answer key and
    // explanation. It binds content but is not a secret or an origin proof.
    let binding = json!({"schema":"archeaxis.deeptutor-question-content/v1",
        "source_material":&candidate.source_material,"question":&candidate.question});
    let visible = json!({"question_id":&candidate.question.question_id,
        "question":&candidate.question.question,"question_type":&candidate.question.question_type,
        "options":&candidate.question.options});
    Ok(json!({"schema":"archeaxis.deeptutor-question-view/v1",
        "question_document":question_document,"question_status":question_status,
        "source_material":candidate.source_material,"source_snapshot_status":source_snapshot_status,
        "source_reference":"declared_unverified","question_document_origin":question_document_origin,
        "authorization_effect":"none",
        "question_version":format!("sha256:{}",sha(&binding)),"visible_sha256":sha(&visible),
        "question":visible,"origin":"user_import_unverified","provider_identity":"unverified",
        "provider_executed":false,"independent_mastery":"not_established"}))
}

/// Compare candidate content with a separately selected local snapshot. This
/// proves neither selection by a human nor derivation from that material. The
/// future caller must independently check the human-selected activity, both
/// grants, the attempt, cancellation and restore epoch in its own transaction.
/// This function does not authorize or start a worker.
pub fn assert_selected_snapshot_matches_candidate(
    conn: &Connection,
    question_document: &Snapshot,
    selected_source: &Snapshot,
    question_id: &str,
    question_version: &str,
) -> Result<(), Error> {
    let view = read_view(conn, question_document)?;
    let source: Snapshot = serde_json::from_value(view["source_material"].clone())
        .map_err(|_| Error::Invalid("question material reference invalid"))?;
    if view["question_status"] != "current"
        || view["source_snapshot_status"] != "current"
        || view["source_reference"] != "declared_unverified"
        || source != *selected_source
        || view["question"]["question_id"] != question_id
        || view["question_version"] != question_version
    {
        return Err(Error::Invalid("question content binding is not current"));
    }
    Ok(())
}

/// Private worker input. Call only inside the Core transaction that has also
/// checked both provider grants and the attempt's restore epoch.
pub(crate) fn grading_question(
    conn: &Connection,
    question_document: &Snapshot,
    selected_source: &Snapshot,
    question_id: &str,
    question_version: &str,
) -> Result<Value, Error> {
    assert_selected_snapshot_matches_candidate(
        conn,
        question_document,
        selected_source,
        question_id,
        question_version,
    )?;
    let snapshot = document::read_verified(
        conn,
        &question_document.document_id,
        Some(question_document.version),
    )?;
    let candidate: Candidate = serde_json::from_value(
        snapshot["editor_json"]["attrs"]
            .get(NAMESPACE)
            .cloned()
            .ok_or(Error::Invalid("question candidate missing"))?,
    )
    .map_err(|_| Error::Invalid("invalid question candidate fields"))?;
    validate(&candidate, question_document)?;
    Ok(json!({"question_type":candidate.question.question_type,
        "options":candidate.question.options,"correct_answer":candidate.question.correct_answer}))
}

// ---------------------------------------------------------------------------
// Human acceptance of a generated question candidate
// ---------------------------------------------------------------------------

pub const ACCEPT_RECEIPT_SCHEMA: &str = "archeaxis.deeptutor-question-accept-receipt/v1";
/// The candidate contract rejects unknown fields, so the acceptance record is
/// its own namespace beside the question rather than a sibling inside it.
pub const ACCEPTANCE_NAMESPACE: &str = "archeaxis_deeptutor_question_acceptance";
pub const QUESTION_TURN_NAMESPACE: &str = "archeaxis_deeptutor_question_turn_candidate";
pub const QUESTION_TURN_DOCUMENT_SCHEMA: &str = "archeaxis.deeptutor-question-turn-document/v1";
const MAX_ACCEPT_ANSWER: usize = 20_000;
const MAX_ACCEPT_TEXT: usize = 128_000;

/// One explicit human decision over a generated candidate. The answer key is
/// always caller-supplied: a model opinion never becomes the grading key by
/// itself, and nothing here revalidates the model or the prompt.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct AcceptRequest {
    pub create_request_id: String,
    pub candidate: Snapshot,
    pub correct_answer: String,
    #[serde(default)]
    pub explanation: Option<String>,
    #[serde(default)]
    pub question_text: Option<String>,
}

fn accept_text(value: &str, max: usize, nonblank: bool) -> bool {
    text(value, max, nonblank)
}

pub fn accept_request_refusal(request: &AcceptRequest) -> Option<&'static str> {
    if !token(&request.create_request_id)
        || !grant::valid_snapshot_shape(&request.candidate)
        || !accept_text(&request.correct_answer, MAX_ACCEPT_ANSWER, true)
        || request
            .explanation
            .as_ref()
            .is_some_and(|value| !accept_text(value, MAX_ACCEPT_TEXT, false))
        || request
            .question_text
            .as_ref()
            .is_some_and(|value| !accept_text(value, MAX_ACCEPT_TEXT, true))
    {
        return Some("invalid question acceptance request");
    }
    None
}

pub fn accept_request_sha256(request: &AcceptRequest) -> Result<String, Error> {
    let frame = json!({"create_request_id":request.create_request_id,
        "candidate":request.candidate,"correct_answer":request.correct_answer,
        "explanation":request.explanation,"question_text":request.question_text});
    Ok(sha(&frame))
}

fn accept_internal(create_request_id: &str) -> String {
    format!(
        "deeptutor_question_accept_{}",
        hex::encode(Sha256::digest(create_request_id.as_bytes()))
    )
}

/// The ordinary Core Document this acceptance owns, derived only from its ID.
pub fn accept_document_id(create_request_id: &str) -> String {
    format!(
        "doc_req_{}",
        hex::encode(Sha256::digest(
            accept_internal(create_request_id).as_bytes()
        ))
    )
}

fn accept_existing(
    conn: &Connection,
    request: &AcceptRequest,
    request_sha256: &str,
) -> Result<Option<Value>, Error> {
    let id = accept_document_id(&request.create_request_id);
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM documents WHERE document_id=?1)",
        [&id],
        |row| row.get(0),
    )?;
    if !exists {
        return Ok(None);
    }
    let snapshot = document::read_verified(conn, &id, Some(1))?;
    let saved = &snapshot["editor_json"]["attrs"][ACCEPTANCE_NAMESPACE];
    if saved["create_request_id"] != request.create_request_id
        || saved["request_sha256"].as_str() != Some(request_sha256)
    {
        return Err(Error::Conflict(1));
    }
    let snap = Snapshot {
        document_id: id,
        version: 1,
        content_sha256: snapshot["content_sha256"]
            .as_str()
            .unwrap_or_default()
            .to_owned(),
    };
    let mut receipt = accept_receipt(conn, &snap, snapshot);
    receipt["duplicate"] = json!(true);
    Ok(Some(receipt))
}

fn accept_receipt(conn: &Connection, snapshot: &Snapshot, document: Value) -> Value {
    let view = read_view(conn, snapshot).unwrap_or(Value::Null);
    let saved = &document["editor_json"]["attrs"][ACCEPTANCE_NAMESPACE];
    json!({"schema":ACCEPT_RECEIPT_SCHEMA,"question_document":snapshot,
        "question_view":view,"document":document,
        "accepted_from":saved["accepted_from"],
        "origin":"user_import_unverified","provider_identity":"unverified",
        "independent_mastery":"not_established","human_review_required":true,
        "active_content_executed":false,"rendering_authorized":false})
}

/// The model's own explanation text, read from the candidate receipt. The
/// candidate contract keeps only the visible question, so the explanation has
/// to come from the stored model reply rather than from the admitted fields.
fn staged_model_explanation(staged: &Value) -> Option<String> {
    let content = staged["model_reply"]["content"].as_str()?;
    let parsed: Value = serde_json::from_str(content).ok()?;
    let text = parsed["explanation"].as_str()?;
    (!text.trim().is_empty() && text.len() <= MAX_ACCEPT_TEXT && !text.contains('\0'))
        .then(|| text.to_owned())
}

/// Turn one generated candidate into an ordinary graded-question Document only
/// when a human supplies the answer key. Repeated requests read the accepted
/// Document; different content under the same ID is a conflict.
pub fn accept_question_candidate(
    conn: &mut Connection,
    request: &AcceptRequest,
) -> Result<Value, Error> {
    if accept_request_refusal(request).is_some() {
        return Err(Error::Invalid("invalid question acceptance request"));
    }
    let request_sha256 = accept_request_sha256(request)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    if let Some(value) = accept_existing(&tx, request, &request_sha256)? {
        tx.commit()?;
        return Ok(value);
    }
    // The candidate must still be the current version of a real question-turn
    // Document; a later edit is a different candidate, not this one.
    let source = document::read_verified(&tx, &request.candidate.document_id, None)?;
    let current_version = source["version"]
        .as_i64()
        .ok_or(Error::Invalid("candidate document version invalid"))?;
    if current_version != request.candidate.version
        || source["content_sha256"] != request.candidate.content_sha256
    {
        return Err(Error::Conflict(current_version));
    }
    let staged = &source["editor_json"]["attrs"][QUESTION_TURN_NAMESPACE];
    if staged["schema"].as_str() != Some(QUESTION_TURN_DOCUMENT_SCHEMA) {
        return Err(Error::Invalid(
            "candidate is not a DeepTutor question-turn document",
        ));
    }
    let material: Snapshot = serde_json::from_value(staged["material"].clone())
        .map_err(|_| Error::Invalid("candidate material reference invalid"))?;
    if !grant::valid_snapshot_shape(&material) {
        return Err(Error::Invalid("candidate material reference invalid"));
    }
    grant::assert_material(&tx, &material)?;
    let question = &staged["question"];
    let question_id = question["question_id"]
        .as_str()
        .ok_or(Error::Invalid("candidate question identity missing"))?;
    let question_type = question["question_type"]
        .as_str()
        .ok_or(Error::Invalid("candidate question type missing"))?;
    if question_type != "choice" {
        return Err(Error::Invalid(
            "only a choice candidate can be accepted as a graded question",
        ));
    }
    let options: BTreeMap<String, String> = serde_json::from_value(question["options"].clone())
        .map_err(|_| Error::Invalid("candidate options invalid"))?;
    if !options.contains_key(&request.correct_answer) {
        return Err(Error::Invalid(
            "accepted answer key must be one of the candidate options",
        ));
    }
    let body = request
        .question_text
        .as_deref()
        .or_else(|| question["question"].as_str())
        .ok_or(Error::Invalid("candidate question text missing"))?;
    let (explanation, explanation_source) = match request.explanation.clone() {
        Some(text) => (text, "human_supplied"),
        None => match staged_model_explanation(staged) {
            Some(text) => (text, "model_draft_reviewed"),
            None => (
                question["explanation"]
                    .as_str()
                    .unwrap_or_default()
                    .to_owned(),
                "absent",
            ),
        },
    };
    let candidate = json!({"schema":SCHEMA,"source_material":material,
        "origin":"user_import_unverified",
        "question":{"question_id":question_id,"question":body,"question_type":question_type,
            "options":options,"correct_answer":request.correct_answer,
            "explanation":explanation}});
    let acceptance = json!({
        "create_request_id":request.create_request_id,
        "request_sha256":request_sha256,
        "accepted_from":{"candidate":request.candidate,
            "generation_route":staged["generation_route"],
            "model_reply_sha256":staged["model_reply_sha256"],
            "capture_binding_sha256":staged["capture_binding"]["prompt_sha256"]},
        "answer_key_source":"human_declared",
        "model_answer_used_as_key":false,
        "explanation_source":explanation_source});
    let editor = json!({"type":"doc","attrs":{(NAMESPACE):candidate,
        (ACCEPTANCE_NAMESPACE):acceptance},
        "content":[{"type":"paragraph","content":[{"type":"text","text":body}]}]});
    if serde_json::to_vec(&editor)
        .map_err(|_| Error::Invalid("accepted question document unavailable"))?
        .len()
        > 512 * 1024
    {
        return Err(Error::Invalid("accepted question document exceeds limit"));
    }
    let title = format!(
        "Accepted question · {}",
        body.chars().take(120).collect::<String>()
    );
    let internal = accept_internal(&request.create_request_id);
    let document = document::create_optional_tx(&tx, None, None, &title, editor, Some(&internal))?;
    let id = document["document_id"]
        .as_str()
        .ok_or(Error::Invalid("accepted question identity unavailable"))?;
    let snapshot = Snapshot {
        document_id: id.to_owned(),
        version: 1,
        content_sha256: document["content_sha256"]
            .as_str()
            .unwrap_or_default()
            .to_owned(),
    };
    let verified = document::read_verified(&tx, id, Some(1))?;
    if verified["content_sha256"] != json!(snapshot.content_sha256) {
        return Err(Error::Invalid("accepted question identity mismatch"));
    }
    // The accepted Document must satisfy the same contract the grading chain
    // enforces, not a weaker one written for acceptance.
    read_view(&tx, &snapshot)?;
    let result = accept_receipt(&tx, &snapshot, verified);
    tx.commit()?;
    Ok(result)
}
