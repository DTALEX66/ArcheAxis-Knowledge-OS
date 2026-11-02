//! Explicit, version-bound material access for an optional learning provider.
//! This is separate from the existing Knowledge and AI-asset grants.
use crate::document::{self, Error};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const SCHEMA: &str = "archeaxis.provider-material-grant/v1";
const NAMESPACE: &str = "archeaxis_provider_material_grant";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Snapshot {
    pub document_id: String,
    pub version: i64,
    pub content_sha256: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Grant {
    pub schema: String,
    pub purpose: String,
    pub consumer: String,
    pub operations: Vec<String>,
    pub material: Snapshot,
    pub authorization_basis: String,
    #[serde(deserialize_with = "Option::deserialize")]
    pub expires_at: Option<u64>,
    pub state: String,
}

fn invalid(message: &'static str) -> Error {
    Error::Invalid(message)
}

pub fn valid_snapshot_shape(snapshot: &Snapshot) -> bool {
    !snapshot.document_id.is_empty()
        && snapshot.document_id.len() <= 128
        && snapshot.document_id.bytes().all(|b| b.is_ascii_alphanumeric() || b"_-".contains(&b))
        && (1..=9_007_199_254_740_991).contains(&snapshot.version)
        && snapshot.content_sha256.len() == 64
        && snapshot.content_sha256.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn metadata(editor: &Value) -> Result<Option<Grant>, Error> {
    editor["attrs"]
        .get(NAMESPACE)
        .map(|value| serde_json::from_value(value.clone()).map_err(|_| invalid("invalid provider material grant")))
        .transpose()
}

pub fn assert_material(conn: &Connection, material: &Snapshot) -> Result<(), Error> {
    if !valid_snapshot_shape(material) {
        return Err(invalid("invalid material snapshot"));
    }
    let source = document::read_verified(conn, &material.document_id, Some(material.version))?;
    if source["content_sha256"] != material.content_sha256 {
        return Err(invalid("material snapshot hash mismatch"));
    }
    Ok(())
}

fn assert_material_current(conn: &Connection, material: &Snapshot) -> Result<(), Error> {
    assert_material(conn, material)?;
    let current = document::read_verified(conn, &material.document_id, None)?;
    if current["version"].as_i64() != Some(material.version) || current["content_sha256"] != material.content_sha256 {
        return Err(invalid("provider material is not the current document version"));
    }
    Ok(())
}

pub fn validate_editor(conn: &Connection, document_id: &str, editor: &Value) -> Result<(), Error> {
    let Some(grant) = metadata(editor)? else { return Ok(()); };
    if grant.schema != SCHEMA
        || grant.consumer != "deeptutor"
        || grant.operations.len() != 1
        || grant.operations[0] != "practice"
        || !matches!(grant.state.as_str(), "granted" | "revoked")
        || grant.purpose.trim().is_empty()
        || grant.purpose.len() > 1024
        || grant.authorization_basis.len() > 16_384
        || grant.expires_at.is_some_and(|t| t > 253_402_300_799)
        || !valid_snapshot_shape(&grant.material)
        || grant.material.document_id == document_id
    {
        return Err(invalid("unsupported provider grant scope"));
    }
    let revoked: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM document_versions WHERE document_id=?1 AND json_extract(editor_json,'$.attrs.archeaxis_provider_material_grant.state')='revoked')",
        [document_id], |row| row.get(0),
    )?;
    if revoked && grant.state != "revoked" {
        return Err(invalid("revoked provider grant cannot be reactivated"));
    }
    // Revocation must remain possible after the material disappears.
    if grant.state == "granted" {
        if grant.authorization_basis.trim().is_empty() {
            return Err(invalid("provider grant requires human authorization"));
        }
        assert_material_current(conn, &grant.material)?;
    }
    Ok(())
}

/// Check the current grant and exact material, in the caller's Store view or
/// transaction. A restored grant identity can never authorize a new operation.
pub fn consume(conn: &Connection, grant_ref: &Snapshot, material: &Snapshot, now: u64) -> Result<(), Error> {
    consume_with_expiry(conn, grant_ref, material, now).map(|_| ())
}

/// Return the expiry only after exactly the same current-version, restoration,
/// revocation and material checks as ordinary consumption. This is internal
/// to a transaction holding the write lock; it is not a transferable grant.
pub(crate) fn consume_with_expiry(conn: &Connection, grant_ref: &Snapshot, material: &Snapshot, now: u64) -> Result<Option<u64>, Error> {
    if !valid_snapshot_shape(grant_ref) || !valid_snapshot_shape(material) {
        return Err(invalid("invalid provider grant snapshot"));
    }
    archeaxis_store_sqlite::authorization_fence::assert_grant_not_fenced(conn, &grant_ref.document_id)
        .map_err(|_| invalid("restored grant requires new human authorization"))?;
    let doc = document::read_verified(conn, &grant_ref.document_id, None)?;
    if doc["version"].as_i64() != Some(grant_ref.version) || doc["content_sha256"] != grant_ref.content_sha256 {
        return Err(invalid("provider grant snapshot is no longer current"));
    }
    validate_editor(conn, &grant_ref.document_id, &doc["editor_json"])?;
    let grant = metadata(&doc["editor_json"])?.ok_or(invalid("provider grant absent"))?;
    if grant.state != "granted" || grant.material != *material || grant.expires_at.is_some_and(|expiry| now >= expiry) {
        return Err(invalid("provider material access not authorized"));
    }
    assert_material_current(conn, material)?;
    Ok(grant.expires_at)
}
