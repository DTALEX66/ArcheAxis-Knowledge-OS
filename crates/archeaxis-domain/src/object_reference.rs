//! Pinned references to existing workspace objects, never title-based resolution.
use crate::document::{self, Error};
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Reference {
    Document { document_id: String, version: i64, block_id: Option<String> },
    Source { source_id: String, sha256: String },
    Knowledge { knowledge_id: String },
}
fn token(s: &str) -> Result<(), Error> {
    if s.is_empty() || s.len() > 256 || s == "." || s == ".." ||
        !s.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.')) {
        return Err(Error::Invalid("reference ID must be a bounded ASCII token"));
    }
    Ok(())
}
/// Source validation pins the immutable ingestion record. Source rendering separately
/// verifies/reads CAS bytes; metadata validation does not load an unbounded asset.
pub fn validate(conn: &Connection, reference: &Reference) -> Result<(), Error> {
    resolve(conn, reference).map(|_| ())
}
/// Structural validation for historical projections. Missing objects remain
/// unavailable nodes; malformed identities never reach the resolver.
pub fn validate_shape(reference: &Reference) -> Result<(), Error> {
    match reference {
        Reference::Document { document_id, version, block_id } => {
            token(document_id)?;
            if *version < 1 { return Err(Error::Invalid("reference document version must be positive")); }
            if let Some(id) = block_id { token(id)?; }
        }
        Reference::Source { source_id, sha256 } => {
            token(source_id)?;
            if sha256.len() != 64 || !sha256.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
                return Err(Error::Invalid("reference source hash must be lowercase SHA-256"));
            }
        }
        Reference::Knowledge { knowledge_id } => token(knowledge_id)?,
    }
    Ok(())
}
pub fn resolve(conn: &Connection, reference: &Reference) -> Result<Value, Error> {
    validate_shape(reference)?;
    match reference {
        Reference::Document { document_id, version, block_id } => {
            token(document_id)?;
            if *version < 1 { return Err(Error::Invalid("reference document version must be positive")); }
            let snapshot = document::read(conn, document_id, Some(*version))?;
            if let Some(block_id) = block_id {
                token(block_id)?;
                if !snapshot["blocks"].as_array().is_some_and(|blocks| blocks.iter().any(|b| b["block_id"] == *block_id)) {
                    return Err(Error::Invalid("reference block is absent from pinned document version"));
                }
            }
            Ok(json!({"reference":reference,"title":snapshot["title"],"content_sha256":snapshot["content_sha256"],"source_id":snapshot["source_id"],"source_revision":snapshot["source_revision"]}))
        }
        Reference::Source { source_id, sha256 } => {
            token(source_id)?;
            if sha256.len() != 64 || !sha256.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
                return Err(Error::Invalid("reference source hash must be lowercase SHA-256"));
            }
            let record: Option<(String,String)> = conn.query_row("SELECT sha256,original_name FROM sources WHERE source_id=?1",[source_id],|r|Ok((r.get(0)?,r.get(1)?))).optional()?;
            let (digest,name) = record.ok_or(Error::NotFound)?;
            if digest != *sha256 { return Err(Error::Invalid("reference source hash differs from immutable ingestion record")); }
            Ok(json!({"reference":reference,"title":name,"content_sha256":digest,"cas_read":"NOT_EXECUTED_BY_METADATA_RESOLUTION"}))
        }
        Reference::Knowledge { knowledge_id } => {
            token(knowledge_id)?;
            let exists: bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM knowledge WHERE knowledge_id=?1)",[knowledge_id],|r|r.get(0))?;
            if !exists {return Err(Error::NotFound);}
            // Knowledge revision identity is the immutable ID; never substitute a
            // superseding item and never manufacture a Document/version relationship.
            Ok(json!({"reference":reference,"title":knowledge_id,"identity":"immutable_knowledge_id"}))
        }
    }
}
