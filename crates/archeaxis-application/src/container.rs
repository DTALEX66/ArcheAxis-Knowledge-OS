//! R15/F15 second half: a container's members become sources of their own.
//!
//! The archive worker extracts the members it could read and declares each one with
//! its digest. This module is the Core half: it verifies every declared member against
//! the bytes in the transfer area, imports each one as its own source **recording that
//! it came from this container**, and enqueues a job for each member whose name the
//! Core can resolve to a route.
//!
//! Two things are deliberately explicit:
//!
//! * the relation is recorded with the existing origin mechanism
//!   (`origin_kind = "archive-member"`, `origin_ref = "<container source_id>#<member>"`),
//!   so a member can be traced back to its container without a schema change and
//!   without inventing a second store of relations;
//! * a member whose name resolves to no route is imported anyway and reported as
//!   custody-only, because "we kept it but could not read it" is a fact, whereas
//!   dropping it would be a loss nobody can see.

use crate::attempts;
use crate::jobs::JobError;
use archeaxis_domain::source::{self, ImportOutcome, OriginInfo};
use rusqlite::{Connection, OptionalExtension};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

/// The origin kind recorded for a member. The store's vocabulary is fixed
/// (`path`, `url`, `import`, `manual`), so the relation rides in the reference:
/// `"<container source_id>#<member path>"`. Inventing a kind outside that vocabulary
/// is NOT an option: `import_source_with_origin` uses `INSERT OR IGNORE`, so an
/// out-of-vocabulary kind would be dropped in silence, which is exactly what this
/// module must not allow - `expand_members` therefore verifies the relation landed.
pub const ORIGIN_KIND: &str = "import";
const MEMBER_LIMIT: usize = 50;

/// One member the archive worker offered as a source.
#[derive(Debug, Clone, Deserialize)]
pub struct ArchiveMember {
    pub name: String,
    pub file: String,
    pub bytes: u64,
    pub sha256: String,
}

/// What one expansion produced.
#[derive(Debug, Default)]
pub struct Expansion {
    /// Sources imported for members, in declaration order.
    pub sources: Vec<String>,
    /// Members whose name resolved to a route, with the job that now reads them.
    pub jobs: Vec<String>,
    /// Members kept as sources but with no route that can read their bytes.
    pub custody_only: Vec<String>,
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex::encode(hasher.finalize())
}

/// The members the newest finished attempt of `archive_job_id` declared.
pub fn declared_members(conn: &Connection, archive_job_id: &str) -> Result<Vec<ArchiveMember>, JobError> {
    let content: Option<String> = conn
        .query_row(
            "SELECT content FROM job_outputs WHERE job_id=?1 AND kind='loss_report'
             ORDER BY attempt DESC LIMIT 1",
            [archive_job_id],
            |row| row.get(0),
        )
        .optional()?;
    let Some(content) = content else {
        return Ok(Vec::new());
    };
    let payload: serde_json::Value =
        serde_json::from_str(&content).map_err(|_| JobError::InvalidReceipt("loss report is not JSON"))?;
    let declared = payload
        .get("params")
        .and_then(|params| params.get("structure"))
        .and_then(|structure| structure.get("extractable_members"))
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    let mut members: Vec<ArchiveMember> = Vec::new();
    for item in declared {
        members.push(
            serde_json::from_value(item).map_err(|_| JobError::InvalidReceipt("a declared member is malformed"))?,
        );
    }
    Ok(members)
}

/// The route a member's own name selects, if any: (job kind, expected media type).
fn route_for_member(name: &str) -> Option<(&'static str, &'static str)> {
    for kind in ["text", "pdf", "image", "archive"] {
        if let Ok(media) = attempts::resolve_media_type(kind, name) {
            return Some((kind, media));
        }
    }
    None
}

/// Import every declared member as its own source and enqueue the readable ones.
pub fn expand_members(
    conn: &mut Connection,
    staging_root: &Path,
    archive_job_id: &str,
) -> Result<Expansion, JobError> {
    let members = declared_members(conn, archive_job_id)?;
    let mut expansion = Expansion::default();
    if members.is_empty() {
        return Ok(expansion);
    }
    let container_source: String = conn
        .query_row(
            "SELECT j.input_ref FROM jobs j WHERE j.job_id=?1",
            [archive_job_id],
            |row| row.get(0),
        )
        .optional()?
        .unwrap_or_default();

    for member in members.into_iter().take(MEMBER_LIMIT) {
        // a declared file may not leave the transfer area, whatever it contains
        if Path::new(&member.file).components().count() != 1
            || member.file.contains("..")
            || member.file.contains(['/', '\\'])
        {
            return Err(JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: format!("declared member file {:?} is not a plain name", member.file),
            });
        }
        let path: PathBuf = staging_root.join("members").join(&member.file);
        let bytes = std::fs::read(&path).map_err(|error| JobError::UnverifiableInput {
            job: archive_job_id.to_string(),
            reason: format!("declared member {:?} is unreadable: {error}", member.name),
        })?;
        if bytes.len() as u64 != member.bytes || sha256_hex(&bytes) != member.sha256 {
            return Err(JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: format!("declared member {:?} does not match its digest and size", member.name),
            });
        }
        let origin_ref = format!("{container_source}#{}", member.name);
        let origin = OriginInfo {
            kind: ORIGIN_KIND,
            origin_ref: &origin_ref,
            original_name: Some(&member.name),
            received_at: None,
        };
        let source_id = match source::import_source_with_origin(conn, &bytes, &member.name, None, Some(origin))? {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        // The origin insert is an INSERT OR IGNORE: verify the relation really landed
        // rather than assuming it did, because a member whose provenance was silently
        // dropped is worse than a refused member.
        let recorded = source::list_origins(conn, &source_id)?
            .into_iter()
            .any(|(kind, reference, _, _)| kind == ORIGIN_KIND && reference == origin_ref);
        if !recorded {
            return Err(JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: format!(
                    "the container relation for member {:?} was not recorded (origin {ORIGIN_KIND}:{origin_ref})",
                    member.name
                ),
            });
        }
        expansion.sources.push(source_id.clone());
        match route_for_member(&member.name) {
            Some((kind, _media)) => {
                let job_id = format!("{archive_job_id}-member-{}", member.file);
                let existed: bool = conn.query_row(
                    "SELECT EXISTS(SELECT 1 FROM jobs WHERE job_id=?1)",
                    [&job_id],
                    |row| row.get(0),
                )?;
                crate::jobs::enqueue(conn, &job_id, kind, &source_id)?;
                if !existed {
                    expansion.jobs.push(job_id);
                }
            }
            None => expansion.custody_only.push(member.name.clone()),
        }
    }
    Ok(expansion)
}
