//! Product-owned context grants on canonical versioned Documents. Inert source
//! material never authorizes private sessions, commands, network or file access.
use crate::{document::{self, Error}, knowledge, object_reference::{self, Reference}};
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

pub const SCHEMA: &str = "archeaxis.context-grant/v1";
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContextGrant {
    pub schema: String,
    pub purpose: String,
    pub consumer: String,
    pub operations: Vec<Operation>,
    pub knowledge_id: Option<String>,
    pub provenance: Vec<Reference>,
    pub authorization_basis: String,
    pub expires_at: Option<u64>,
    pub state: GrantState,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all="snake_case")]
pub enum Operation { Answer, Retest }
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all="snake_case")]
pub enum GrantState { Candidate, Granted, Revoked }
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Consumption {
    pub document_id: String,
    pub version: i64,
    pub content_sha256: String,
    pub purpose: String,
}
fn invalid(message: &'static str) -> Error { Error::Invalid(message) }
fn decode(editor: &Value) -> Result<Option<ContextGrant>, Error> {
    editor["attrs"].get("archeaxis_context_grant").map(|raw| serde_json::from_value(raw.clone())
        .map_err(|_| invalid("context grant metadata shape is invalid or unsupported"))).transpose()
}

pub fn validate_editor(conn: &Connection, document_id: &str, editor: &Value) -> Result<(), Error> {
    let Some(grant) = decode(editor)? else { return Ok(()); };
    if grant.schema != SCHEMA || grant.consumer != "local-machine" || grant.purpose.trim().is_empty()
        || grant.purpose.len()>1024 || grant.authorization_basis.len()>16_384
        || grant.provenance.len()>32 || grant.operations.len()>2
        || (grant.operations.len()==2 && grant.operations[0]==grant.operations[1])
        || grant.expires_at.is_some_and(|n| n>253_402_300_799) {
        return Err(invalid("context grant scope or bounds are unsupported"));
    }
    // Revocation is terminal for this object identity, including restore of an
    // old granted version. A new authorization requires a new Document grant.
    let revoked: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1
         AND json_extract(editor_json,'$.attrs.archeaxis_context_grant.state')='revoked')",
        [document_id], |r|r.get(0),
    )?;
    if revoked && grant.state != GrantState::Revoked {
        return Err(invalid("revoked context grant cannot be reactivated or restored"));
    }
    for reference in &grant.provenance {
        object_reference::validate_shape(reference)?;
        if grant.state != GrantState::Revoked { object_reference::validate(conn, reference)?; }
    }
    if let Some(id) = &grant.knowledge_id {
        object_reference::validate_shape(&Reference::Knowledge { knowledge_id: id.clone() })?;
        if grant.state != GrantState::Revoked {
            object_reference::validate(conn, &Reference::Knowledge { knowledge_id: id.clone() })?;
        }
    }
    if grant.state == GrantState::Granted && (grant.knowledge_id.is_none() || grant.operations.is_empty()
        || grant.authorization_basis.trim().is_empty()) {
        return Err(invalid("granted context requires explicit knowledge, operations and authorization basis"));
    }
    Ok(())
}

/// Check the current grant and current knowledge, never a historical permission.
/// The caller supplies a clock value so expiry boundary tests remain deterministic.
pub fn consume(conn: &Connection, input: &Consumption, operation: Operation, knowledge_id: &str, now: u64)
    -> Result<Value, Error> {
    archeaxis_store_sqlite::authorization_fence::assert_grant_not_fenced(conn,&input.document_id)
        .map_err(|error| match error {
            rusqlite::Error::InvalidParameterName(_) => invalid("restored grant requires a new explicit human authorization object"),
            other => Error::Sql(other),
        })?;
    let snapshot = document::read(conn, &input.document_id, None)?;
    if snapshot["version"].as_i64()!=Some(input.version) || snapshot["content_sha256"]!=input.content_sha256 {
        return Err(invalid("context grant snapshot is no longer current"));
    }
    let grant = decode(&snapshot["editor_json"])?.ok_or(invalid("context grant metadata is absent"))?;
    validate_editor(conn, &input.document_id, &snapshot["editor_json"])?;
    if grant.state != GrantState::Granted || grant.purpose != input.purpose
        || !grant.operations.contains(&operation) || grant.knowledge_id.as_deref()!=Some(knowledge_id)
        || grant.expires_at.is_some_and(|expiry| now>=expiry) {
        return Err(invalid("context consumption exceeds current authorization or expiry"));
    }
    let status: Option<(String,String)> = conn.query_row(
        "SELECT status,knowledge_type FROM knowledge WHERE knowledge_id=?1", [knowledge_id],
        |r|Ok((r.get(0)?,r.get(1)?)),
    ).optional()?;
    if !knowledge::is_knowledge_active(conn, knowledge_id)? || !status.is_some_and(|(state,kind)|
        state=="accepted" || matches!(kind.as_str(),"PERSONAL_DEFINITION"|"PERSONAL_EXPERIENCE")) {
        return Err(invalid("context knowledge is not currently eligible for machine consumption"));
    }
    Ok(json!({"document_id":input.document_id,"version":input.version,"content_sha256":input.content_sha256,
        "authorization":grant,"operation":operation,"checked_at":now,"current_permission_valid":true}))
}
