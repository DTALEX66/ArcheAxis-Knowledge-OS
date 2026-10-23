//! External context stays external. This offline boundary accepts only reviewed,
//! bounded knowledge candidates into existing versioned AI-asset Documents.
//! No transport, session capture, new table, background task or automatic adoption.
use crate::{
    ai_asset,
    document::{self, Error},
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

pub const SCHEMA: &str = "archeaxis.external-knowledge-candidate/v1";
pub const PROVIDER_STATE: &str = "NOT_CONNECTED";
pub fn contract() -> Value {
    json!({"schema_version":1,"owner":"EXTERNAL_CONTEXT_PROVIDER",
        "fetch_status":PROVIDER_STATE,"provider_id":null,
        "capabilities":["receive_knowledge_candidate","query_candidate_metadata","read_evidence_reference_status"],
        "raw_context_capture":false,"network_fetch":false,"automatic_recall":false})
}
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum FetchStatus {
    Available,
    Offline,
    Timeout,
    Revoked,
    Missing,
    Deleted,
    Unknown,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Source {
    pub provider_id: String,
    pub project_id: String,
    pub source_app: String,
    pub source_ref: String,
    pub auth_scope: String,
    pub fetch_status: FetchStatus,
    pub provenance: Vec<String>,
    pub updated_at: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KnowledgeKind {
    CodingPitfall,
    RootCause,
    VerifiedFix,
    DecisionRule,
    ReusableProcedure,
    Other,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ClaimedStatus {
    Pass,
    Fail,
    Partial,
    Unknown,
    NotRun,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Verification {
    pub status: ClaimedStatus,
    pub command: Option<String>,
    pub exit_code: Option<i32>,
    pub artifact_hash: Option<String>,
    pub diff_ref: Option<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Candidate {
    pub schema_version: u32,
    pub candidate_id: String,
    pub knowledge_kind: KnowledgeKind,
    pub title: String,
    pub summary: String,
    pub problem: String,
    pub root_cause: String,
    pub failed_attempts: Vec<String>,
    pub resolution: String,
    pub applicability: String,
    pub contraindications: String,
    pub evidence_refs: Vec<String>,
    pub verification: Verification,
    pub source: Source,
}
/// Caller-supplied scope must originate in a trusted admission (HTTP: authenticated
/// human explicitly importing a sanitized packet), never inferred from provider data.
pub struct Admission<'a> {
    pub provider_id: &'a str,
    pub project_id: &'a str,
    pub auth_scope: &'a str,
    pub material_authorized: bool,
    pub redaction_confirmed: bool,
}
fn invalid(message: &'static str) -> Error {
    Error::Invalid(message)
}
fn identifier(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 128
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.'))
}
fn reference(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 1024
        && s.is_ascii()
        && !s
            .bytes()
            .any(|b| b.is_ascii_whitespace() || b.is_ascii_control())
        && !s.contains(['\\', '?', '@'])
        && !s.starts_with(['/', '~'])
        && !s.to_ascii_lowercase().starts_with("file:")
        && !(s.as_bytes().get(1) == Some(&b':') && s.as_bytes().get(2) == Some(&b'/'))
}
fn scope(c: &Candidate, a: &Admission<'_>) -> Result<(), Error> {
    if !a.material_authorized
        || !a.redaction_confirmed
        || c.source.provider_id != a.provider_id
        || c.source.project_id != a.project_id
        || c.source.auth_scope != a.auth_scope
        || a.auth_scope != "knowledge_candidate:import"
    {
        return Err(invalid(
            "candidate material authorization or namespace mismatch",
        ));
    }
    if c.source.fetch_status != FetchStatus::Available {
        return Err(invalid(
            "external evidence unavailable; no new access or import",
        ));
    }
    Ok(())
}
pub fn validate(c: &Candidate, a: &Admission<'_>) -> Result<(), Error> {
    scope(c, a)?;
    if c.schema_version != 1
        || !identifier(&c.candidate_id)
        || !identifier(&c.source.project_id)
        || !identifier(&c.source.provider_id)
        || !identifier(&c.source.source_app)
        || c.title.trim().is_empty()
        || c.summary.trim().is_empty()
        || c.root_cause.trim().is_empty()
        || c.source.updated_at.trim().is_empty()
        || c.source.source_ref.trim().is_empty()
        || c.failed_attempts.len() > 16
        || c.evidence_refs.len() > 32
        || c.source.provenance.len() > 32
        || !reference(&c.source.source_ref)
        || !c
            .evidence_refs
            .iter()
            .chain(c.source.provenance.iter())
            .all(|r| reference(r))
        || c.verification
            .diff_ref
            .as_ref()
            .is_some_and(|r| !reference(r))
        || c.verification
            .artifact_hash
            .as_ref()
            .is_some_and(|h| h.len() != 64 || !h.bytes().all(|b| b.is_ascii_hexdigit()))
    {
        return Err(invalid("invalid external candidate schema or bounds"));
    }
    // No arbitrary nested payload: every admitted field is a bounded string/enum.
    let v = serde_json::to_value(c).map_err(|_| invalid("candidate serialization"))?;
    fn bounded(v: &Value) -> bool {
        match v {
            Value::String(s) => s.len() <= 4096 && !s.contains('\0'),
            Value::Array(a) => a.iter().all(bounded),
            Value::Object(o) => o.values().all(bounded),
            _ => true,
        }
    }
    if !bounded(&v) || v.to_string().len() > 48000 {
        return Err(invalid("candidate exceeds bounded knowledge packet"));
    }
    Ok(())
}
/// External PASS is a claim, even with a diff/hash: only the existing governed
/// human review may adopt an asset. This function never verifies external logs.
pub fn receive(conn: &mut Connection, c: &Candidate, a: &Admission<'_>) -> Result<Value, Error> {
    validate(c, a)?;
    let key = hex::encode(Sha256::digest(
        serde_json::to_vec(&json!([
            SCHEMA,
            c.source.provider_id,
            c.source.project_id,
            c.candidate_id
        ]))
        .map_err(|_| invalid("candidate identity"))?,
    ));
    document::create_optional_with_request(
        conn,
        None,
        None,
        &c.title,
        json!({
            "type":"doc", "content":[], "attrs":{ai_asset::NAMESPACE:{
                "schema":ai_asset::SCHEMA, "kind":"experience", "state":"candidate",
                "content":{"schema":SCHEMA,"candidate":c,"evidence_assessment":"UNVERIFIED_EXTERNAL"},
                "purpose":"Reusable knowledge candidate; external context not imported",
                "scope":[],"provenance":[],"expires_at":null,"members":[],"conflicts":[],
                "revises":null,"review":null,"source_payload":null
            }}
        }),
        Some(&format!("external-knowledge-{key}")),
    )
}
/// Read only through an explicit namespace and current admission. External status
/// is supplied by the admission adapter, never silently fetched or guessed.
pub fn read(
    conn: &Connection,
    id: &str,
    a: &Admission<'_>,
    status: FetchStatus,
) -> Result<Value, Error> {
    if !a.material_authorized || !a.redaction_confirmed {
        return Err(invalid("candidate access authorization withdrawn"));
    }
    let d = document::read(conn, id, None)?;
    let asset = ai_asset::metadata(&d["editor_json"])?.ok_or(invalid("not an AI asset"))?;
    if asset.content["schema"] != SCHEMA {
        return Err(invalid("not an external candidate"));
    }
    let c: Candidate = serde_json::from_value(asset.content["candidate"].clone())
        .map_err(|_| invalid("unsupported external candidate"))?;
    scope(&c, a)?;
    if status != FetchStatus::Available {
        return Ok(json!({"document_id":id,"fetch_status":status,"candidate":null}));
    }
    Ok(
        json!({"document_id":id,"version":d["version"],"fetch_status":status,
        "state":asset.state,"candidate":c,"evidence_assessment":"UNVERIFIED_EXTERNAL"}),
    )
}
