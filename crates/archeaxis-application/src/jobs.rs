//! Atomic worker completion and durable idempotency.
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use sha2::{Digest, Sha256};

pub const STATE_QUEUED: &str = archeaxis_contracts::JOB_QUEUED;
pub const STATE_RUNNING: &str = archeaxis_contracts::JOB_RUNNING;
/// Compatibility symbol; persisted state follows the canonical schema.
pub const STATE_COMPLETED: &str = archeaxis_contracts::JOB_SUCCEEDED;
pub const STATE_FAILED: &str = archeaxis_contracts::JOB_FAILED;

pub use archeaxis_contracts::loss_receipt::LossReceipt;

#[derive(Debug)]
pub enum JobError {
    Sql(rusqlite::Error),
    NotFound,
    Conflict,
    InvalidState,
    InvalidReceipt(&'static str),
}
impl From<rusqlite::Error> for JobError {
    fn from(error: rusqlite::Error) -> Self { Self::Sql(error) }
}
impl std::fmt::Display for JobError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Sql(e) => write!(f, "job storage: {e}"),
            Self::NotFound => write!(f, "job not found"),
            Self::Conflict => write!(f, "idempotency key has a different or unverifiable result"),
            Self::InvalidState => write!(f, "job state does not permit this transition"),
            Self::InvalidReceipt(reason) => write!(f, "invalid receipt: {reason}"),
        }
    }
}
impl std::error::Error for JobError {}

pub fn enqueue(conn: &mut Connection, job_id: &str, kind: &str, input_ref: &str) -> Result<(), JobError> {
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let old: Option<(String, String)> = tx.query_row(
        "SELECT kind, input_ref FROM jobs WHERE job_id=?1", [job_id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    ).optional()?;
    if let Some((old_kind, old_input)) = old {
        return if old_kind == kind && old_input == input_ref { Ok(()) } else { Err(JobError::Conflict) };
    }
    let source_exists: bool = tx.query_row(
        "SELECT EXISTS(SELECT 1 FROM sources WHERE source_id=?1)", [input_ref], |r| r.get(0),
    )?;
    if !source_exists { return Err(JobError::NotFound); }
    tx.execute(
        "INSERT INTO jobs(job_id,kind,state,input_ref) VALUES(?1,?2,?3,?4)",
        rusqlite::params![job_id, kind, STATE_QUEUED, input_ref],
    )?;
    tx.commit()?;
    Ok(())
}

/// Output and terminal state commit together. A restart preserves the result
/// binding; replaying a different payload never creates another transform.
pub fn complete(
    conn: &mut Connection, job_id: &str, engine: &str, text: &str,
    loss: Option<&LossReceipt>,
) -> Result<(), JobError> {
    if engine.trim().is_empty() { return Err(JobError::InvalidReceipt("engine is empty")); }
    if let Some(receipt) = loss { receipt.validate().map_err(JobError::InvalidReceipt)?; }
    if loss.is_some_and(|r| r.engine != engine) { return Err(JobError::Conflict); }
    let receipt = serde_json::to_string(&loss).map_err(|_| JobError::Conflict)?;
    let payload = serde_json::to_vec(&(engine, text, loss)).map_err(|_| JobError::Conflict)?;
    let digest = hex::encode(Sha256::digest(payload));
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let row: Option<(String, String, Option<String>)> = tx.query_row(
        "SELECT state,input_ref,completion_digest FROM jobs WHERE job_id=?1", [job_id],
        |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?)),
    ).optional()?;
    let (state, source, old_digest) = row.ok_or(JobError::NotFound)?;
    if state == STATE_COMPLETED {
        return if old_digest.as_deref() == Some(&digest) { Ok(()) } else { Err(JobError::Conflict) };
    }
    if state != STATE_QUEUED && state != STATE_RUNNING { return Err(JobError::InvalidState); }
    tx.execute(
        "INSERT INTO transforms(source_id,engine,text,loss_note) VALUES(?1,?2,?3,?4)",
        rusqlite::params![source, engine, text, loss.and_then(|r| r.loss_note.as_deref())],
    )?;
    let transform_id = tx.last_insert_rowid();
    tx.execute(
        "UPDATE jobs SET state=?1,engine=?2,loss_receipt=?3,completion_digest=?4,
         transform_id=?5,completed_at=datetime('now') WHERE job_id=?6",
        rusqlite::params![STATE_COMPLETED, engine, receipt, digest, transform_id, job_id],
    )?;
    tx.commit()?;
    Ok(())
}

pub fn fail(conn: &mut Connection, job_id: &str, error: &str) -> Result<(), JobError> {
    let receipt = serde_json::json!({"error": error}).to_string();
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let old: Option<(String, Option<String>)> = tx.query_row(
        "SELECT state,loss_receipt FROM jobs WHERE job_id=?1", [job_id],
        |r| Ok((r.get(0)?,r.get(1)?)),
    ).optional()?;
    let (state, old_receipt) = old.ok_or(JobError::NotFound)?;
    if state == STATE_FAILED {
        return if old_receipt.as_deref() == Some(&receipt) { Ok(()) } else { Err(JobError::Conflict) };
    }
    if state != STATE_QUEUED && state != STATE_RUNNING { return Err(JobError::InvalidState); }
    tx.execute(
        "UPDATE jobs SET state=?1,loss_receipt=?2,completed_at=datetime('now') WHERE job_id=?3",
        rusqlite::params![STATE_FAILED,receipt,job_id],
    )?;
    tx.commit()?;
    Ok(())
}

pub fn job_state(conn: &Connection, job_id: &str) -> rusqlite::Result<Option<String>> {
    conn.query_row("SELECT state FROM jobs WHERE job_id=?1", [job_id], |r| r.get(0)).optional()
}
