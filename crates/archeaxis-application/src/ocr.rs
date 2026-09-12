//! R15/F06: chaining the pages a PDF could not read into the OCR route.
//!
//! A PDF job that finds pages with no extractable text renders them and declares each
//! file with its digest in `loss_receipt.params.structure.ocr_candidates`. This module
//! is the Core half of that chain: it reads the declaration, verifies every digest
//! against the bytes actually in the transfer area, imports each page as its own
//! source, and enqueues one image job per page.
//!
//! The split is deliberate. The worker renders because only it holds the PDF engine,
//! and the Core enqueues because only it writes the database - so a worker still never
//! holds a database handle. Nothing is enqueued from an input that cannot be verified:
//! a missing file, a digest mismatch, a size mismatch or a name that tries to leave the
//! transfer area is refused with a reason, because a job whose input is unverifiable
//! would be a fake success waiting to happen.

use crate::jobs::{self, JobError};
use archeaxis_domain::source::{self, ImportOutcome};
use rusqlite::{Connection, OptionalExtension};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

/// One page a PDF job offered to the OCR route.
#[derive(Debug, Clone, Deserialize)]
pub struct OcrCandidate {
    pub page: u32,
    pub file: String,
    pub bytes: u64,
    pub sha256: String,
    #[serde(default)]
    pub media_type: Option<String>,
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex::encode(hasher.finalize())
}

/// The OCR candidates the newest finished attempt of `pdf_job_id` declared.
pub fn candidates(conn: &Connection, pdf_job_id: &str) -> Result<Vec<OcrCandidate>, JobError> {
    let content: Option<String> = conn
        .query_row(
            "SELECT content FROM job_outputs WHERE job_id=?1 AND kind='loss_report'
             ORDER BY attempt DESC LIMIT 1",
            [pdf_job_id],
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
        .and_then(|structure| structure.get("ocr_candidates"))
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    let mut found: Vec<OcrCandidate> = Vec::new();
    for item in declared {
        match serde_json::from_value::<OcrCandidate>(item) {
            Ok(candidate) => found.push(candidate),
            Err(_) => return Err(JobError::InvalidReceipt("an OCR candidate is malformed")),
        }
    }
    found.sort_by_key(|candidate| candidate.page);
    Ok(found)
}

/// Import every declared page as a source and enqueue one image job per page.
///
/// Returns the jobs that were newly enqueued; a second call returns none, because
/// enqueueing the same page twice would be duplicate work rather than more evidence.
pub fn enqueue_pages(
    conn: &mut Connection,
    staging_root: &Path,
    pdf_job_id: &str,
) -> Result<Vec<String>, JobError> {
    let candidates = candidates(conn, pdf_job_id)?;
    if candidates.is_empty() {
        return Ok(Vec::new());
    }
    let source_name: String = conn
        .query_row(
            "SELECT COALESCE(s.original_name,'source') FROM jobs j
             JOIN sources s ON s.source_id=j.input_ref WHERE j.job_id=?1",
            [pdf_job_id],
            |row| row.get(0),
        )
        .optional()?
        .unwrap_or_else(|| "source".to_string());
    let stem = Path::new(&source_name)
        .file_stem()
        .map(|value| value.to_string_lossy().to_string())
        .unwrap_or_else(|| "source".to_string());

    let mut enqueued = Vec::new();
    for candidate in candidates {
        let name = format!("{stem}-page-{}.png", candidate.page);
        // a declared name may not leave the transfer area, whatever it contains
        let declared = Path::new(&candidate.file);
        if declared.components().count() != 1
            || candidate.file.contains("..")
            || candidate.file.contains(['/', '\\'])
        {
            return Err(JobError::UnverifiableInput {
                job: pdf_job_id.to_string(),
                reason: format!("declared page file {:?} is not a plain name", candidate.file),
            });
        }
        let path: PathBuf = staging_root.join("ocr").join(&candidate.file);
        let bytes = std::fs::read(&path).map_err(|error| JobError::UnverifiableInput {
            job: pdf_job_id.to_string(),
            reason: format!("declared page {} is unreadable: {error}", candidate.page),
        })?;
        if bytes.len() as u64 != candidate.bytes {
            return Err(JobError::UnverifiableInput {
                job: pdf_job_id.to_string(),
                reason: format!(
                    "declared page {} claims {} bytes but the file holds {}",
                    candidate.page,
                    candidate.bytes,
                    bytes.len()
                ),
            });
        }
        let digest = sha256_hex(&bytes);
        if digest != candidate.sha256 {
            return Err(JobError::UnverifiableInput {
                job: pdf_job_id.to_string(),
                reason: format!("declared page {} digest does not match the rendered bytes", candidate.page),
            });
        }
        let source_id = match source::import_source(conn, &bytes, &name, None)? {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        let job_id = format!("{pdf_job_id}-page-{}", candidate.page);
        let existed: bool = conn.query_row(
            "SELECT EXISTS(SELECT 1 FROM jobs WHERE job_id=?1)",
            [&job_id],
            |row| row.get(0),
        )?;
        jobs::enqueue(conn, &job_id, "image", &source_id)?;
        if !existed {
            enqueued.push(job_id);
        }
    }
    Ok(enqueued)
}
