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
use archeaxis_domain::source::{self, ImportOutcome, OriginInfo};
use rusqlite::{Connection, OptionalExtension};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

/// The origin kind that ties a rendered page back to the PDF it was rendered from.
const ORIGIN_KIND: &str = "import";

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
    let payload: serde_json::Value = serde_json::from_str(&content)
        .map_err(|_| JobError::InvalidReceipt("loss report is not JSON"))?;
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
    let Some((pdf_source_id, source_name)) = conn
        .query_row(
            "SELECT j.input_ref, COALESCE(s.original_name,'source') FROM jobs j
             JOIN sources s ON s.source_id=j.input_ref WHERE j.job_id=?1",
            [pdf_job_id],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        )
        .optional()?
    else {
        return Err(JobError::UnverifiableInput {
            job: pdf_job_id.to_string(),
            reason: "the PDF job has no source for its pages to come from".to_string(),
        });
    };
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
                reason: format!(
                    "declared page file {:?} is not a plain name",
                    candidate.file
                ),
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
                reason: format!(
                    "declared page {} digest does not match the rendered bytes",
                    candidate.page
                ),
            });
        }
        // R15/F06: the page is a source of its own, but it came from this PDF's page N, and
        // that relation is the only thing that can later carry the recognised text back to
        // the page it belongs to. `received_at` stays None - a clock value is never invented.
        let origin_ref = format!("{pdf_source_id}#page-{}", candidate.page);
        let origin = OriginInfo {
            kind: ORIGIN_KIND,
            origin_ref: &origin_ref,
            original_name: Some(&name),
            received_at: None,
        };
        let source_id =
            match source::import_source_with_origin(conn, &bytes, &name, None, Some(origin))? {
                ImportOutcome::Imported { source_id, .. } => source_id,
                ImportOutcome::Duplicate { source_id, .. } => source_id,
            };
        // The origin insert is INSERT OR IGNORE, so verify it landed instead of assuming it
        // did: a page whose provenance was dropped in silence would look chained and not be.
        let recorded = source::list_origins(conn, &source_id)?
            .into_iter()
            .any(|(kind, reference, _, _)| kind == ORIGIN_KIND && reference == origin_ref);
        if !recorded {
            return Err(JobError::UnverifiableInput {
                job: pdf_job_id.to_string(),
                reason: format!(
                    "the page relation for page {} was not recorded (origin {ORIGIN_KIND}:{origin_ref})",
                    candidate.page
                ),
            });
        }
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

/// One rendered page as the store knows it after chaining.
#[derive(Debug, Clone)]
pub struct PageRow {
    pub page: Option<u32>,
    pub source_id: String,
    pub origin_ref: String,
    pub original_name: String,
    pub sha256: String,
    /// True when the page image has its own transform, i.e. the OCR route read it.
    pub recognised: bool,
    /// The recognised text of that page, newest non-empty transform, when there is one.
    pub text: Option<String>,
    /// The job queued for this page, when the chain enqueued one.
    pub job_id: Option<String>,
}

/// The pages rendered from one PDF, each with the text its own OCR job produced.
///
/// This is the second half of R15/F06. The PDF job renders the pages it could not read and
/// chains an OCR job per page; the relation recorded at import time is what lets the answer
/// come back to the page it came from instead of ending as an unrelated image source. A page
/// with no recognised text is reported as such - absence is stated, never filled in.
pub fn pages_of(conn: &Connection, pdf_source_id: &str) -> Result<Vec<PageRow>, JobError> {
    let prefix = format!("{pdf_source_id}#page-");
    let mut statement = conn.prepare(
        "SELECT o.source_id, o.origin_ref, s.original_name, s.sha256,
                (SELECT t.text FROM transforms t
                  WHERE t.source_id=o.source_id AND t.text IS NOT NULL AND t.text<>''
                  ORDER BY t.transform_id DESC LIMIT 1),
                EXISTS(SELECT 1 FROM transforms t WHERE t.source_id=o.source_id),
                (SELECT j.job_id FROM jobs j WHERE j.input_ref=o.source_id ORDER BY j.rowid LIMIT 1)
         FROM source_origins o JOIN sources s ON s.source_id=o.source_id
         WHERE o.origin_kind=?1 AND o.origin_ref LIKE ?2
         ORDER BY o.imported_at, o.rowid",
    )?;
    let rows = statement.query_map(
        rusqlite::params![ORIGIN_KIND, format!("{prefix}%")],
        |row| {
            let reference: String = row.get(1)?;
            Ok(PageRow {
                page: reference
                    .strip_prefix(&prefix)
                    .and_then(|tail| tail.parse::<u32>().ok()),
                source_id: row.get(0)?,
                origin_ref: reference,
                original_name: row.get(2)?,
                sha256: row.get(3)?,
                text: row.get(4)?,
                recognised: row.get::<_, i64>(5)? == 1,
                job_id: row.get(6)?,
            })
        },
    )?;
    rows.collect::<rusqlite::Result<Vec<_>>>()
        .map_err(JobError::from)
}
