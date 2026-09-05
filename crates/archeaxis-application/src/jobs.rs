//! Worker job orchestration (Rust core = sole writer; workers call via API).

use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};

/// Job lifecycle states.
pub const STATE_QUEUED: &str = "queued";
pub const STATE_RUNNING: &str = "running";
pub const STATE_COMPLETED: &str = "completed";
pub const STATE_FAILED: &str = "failed";

/// Loss/transform receipt returned by a capability worker (JSON-Schema:
/// packages/contracts/v1/worker-protocol.schema.json).
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Eq)]
pub struct LossReceipt {
    pub engine: String,
    pub engine_version: String,
    pub params: serde_json::Value,
    pub loss_note: Option<String>,
}

/// Enqueue a worker job (e.g. transform/OCR/ASR for a source).
pub fn enqueue(
    conn: &mut Connection,
    job_id: &str,
    kind: &str,
    input_ref: &str,
) -> rusqlite::Result<()> {
    conn.execute(
        "INSERT OR IGNORE INTO jobs(job_id, kind, state, input_ref) VALUES(?1,?2,?3,?4)",
        rusqlite::params![job_id, kind, STATE_QUEUED, input_ref],
    )?;
    Ok(())
}

/// Complete a job with the worker's text/loss receipt (idempotent).
pub fn complete(
    conn: &mut Connection,
    job_id: &str,
    engine: &str,
    text: &str,
    loss: Option<&LossReceipt>,
) -> rusqlite::Result<()> {
    let receipt = match loss {
        Some(r) => serde_json::to_string(r).unwrap_or_else(|_| "{}".into()),
        None => "{}".into(),
    };
    conn.execute(
        "UPDATE jobs SET state=?1, engine=?2, loss_receipt=?3, completed_at=datetime('now')
         WHERE job_id=?4",
        rusqlite::params![STATE_COMPLETED, engine, receipt, job_id],
    )?;
    // persist extracted text as a transform receipt
    conn.execute(
        "INSERT INTO transforms(source_id, engine, text, loss_note)
         SELECT ?1, ?2, ?3, json_extract(?4, '$.loss_note') FROM jobs WHERE job_id=?5",
        rusqlite::params![
            input_source_ref(conn, job_id)?,
            engine,
            text,
            receipt,
            job_id
        ],
    )?;
    Ok(())
}

fn input_source_ref(conn: &Connection, job_id: &str) -> rusqlite::Result<String> {
    conn.query_row(
        "SELECT input_ref FROM jobs WHERE job_id=?1",
        [job_id],
        |r| r.get(0),
    )
}

/// Mark a job failed with an explicit error string (never fake success).
pub fn fail(conn: &mut Connection, job_id: &str, error: &str) -> rusqlite::Result<()> {
    conn.execute(
        "UPDATE jobs SET state=?1, loss_receipt=?2, completed_at=datetime('now') WHERE job_id=?3",
        rusqlite::params![STATE_FAILED, format!(r#"{{"error":"{error}"}}"#), job_id],
    )?;
    Ok(())
}

pub fn job_state(conn: &Connection, job_id: &str) -> rusqlite::Result<Option<String>> {
    conn.query_row("SELECT state FROM jobs WHERE job_id=?1", [job_id], |r| {
        r.get(0)
    })
    .optional()
}
