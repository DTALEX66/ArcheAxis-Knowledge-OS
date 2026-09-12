//! R11: machine task receipts.
//!
//! A machine principal records what it was asked to do, which versions it worked
//! with, what happened, and whether a retest followed. The receipt is a
//! *candidate or measurement* record only: it never accepts knowledge, never
//! grants authority, and an unmeasured result stays explicitly `unmeasured`
//! rather than being rounded up to success.
//!
//! The table is created on demand (the same approach the FTS indexes and
//! card_references use), so no schema-version bump and no archive-layout change is
//! involved. Recorded limitation: because it is created on demand it is not part
//! of EXPORT_TABLES, so archives do not carry machine receipts yet.

use rusqlite::{Connection, OptionalExtension};

/// Outcomes a receipt may carry. `unmeasured` exists so "we did not measure this"
/// is a first-class result instead of a silent success.
pub const OUTCOMES: &[&str] = &["succeeded", "failed", "unmeasured"];

fn ensure_machine_tasks(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS machine_tasks(
             task_id TEXT PRIMARY KEY,
             principal TEXT NOT NULL,
             conditions TEXT NOT NULL,
             knowledge_version TEXT,
             method_version TEXT,
             tool_version TEXT,
             model_version TEXT NOT NULL,
             scope TEXT NOT NULL,
             outcome TEXT NOT NULL,
             failure TEXT,
             retest_of TEXT,
             recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
         );",
    )?;
    Ok(())
}

/// What a machine principal reports about one task it ran.
pub struct MachineTask<'a> {
    pub task_id: &'a str,
    pub principal: &'a str,
    pub conditions: &'a str,
    pub knowledge_version: Option<&'a str>,
    pub method_version: Option<&'a str>,
    pub tool_version: Option<&'a str>,
    pub model_version: &'a str,
    pub scope: &'a str,
    pub outcome: &'a str,
    pub failure: Option<&'a str>,
    pub retest_of: Option<&'a str>,
}

/// Record one machine task receipt.
///
/// Refusals are deliberate: only a machine principal may write here (a human
/// outcome belongs in the learning, human-owned records), the outcome must be one
/// of [`OUTCOMES`], a failed task must say why it failed, and a succeeded task
/// must not carry a failure note. Recording the same task twice is rejected
/// rather than silently overwritten, so a receipt cannot be rewritten after the
/// fact.
pub fn record_machine_task(conn: &mut Connection, task: &MachineTask<'_>) -> rusqlite::Result<()> {
    if task.principal != "machine" {
        return Err(rusqlite::Error::InvalidParameterName(
            "machine task receipts are written by a machine principal only".into(),
        ));
    }
    if task.task_id.trim().is_empty()
        || task.conditions.trim().is_empty()
        || task.model_version.trim().is_empty()
        || task.scope.trim().is_empty()
    {
        return Err(rusqlite::Error::InvalidParameterName(
            "a machine task receipt needs a task id, conditions, model version and scope".into(),
        ));
    }
    if !OUTCOMES.contains(&task.outcome) {
        return Err(rusqlite::Error::InvalidParameterName(
            "outcome must be succeeded, failed or unmeasured".into(),
        ));
    }
    if task.outcome == "failed" && task.failure.map(str::trim).unwrap_or("").is_empty() {
        return Err(rusqlite::Error::InvalidParameterName(
            "a failed machine task must record why it failed".into(),
        ));
    }
    if task.outcome == "succeeded" && task.failure.is_some() {
        return Err(rusqlite::Error::InvalidParameterName(
            "a succeeded machine task cannot carry a failure note".into(),
        ));
    }
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    ensure_machine_tasks(&tx)?;
    let existing: Option<i64> = tx
        .query_row("SELECT 1 FROM machine_tasks WHERE task_id=?1", [task.task_id], |r| r.get(0))
        .optional()?;
    if existing.is_some() {
        return Err(rusqlite::Error::InvalidParameterName(
            "a machine task receipt is immutable; this task id is already recorded".into(),
        ));
    }
    tx.execute(
        "INSERT INTO machine_tasks(task_id, principal, conditions, knowledge_version, method_version,
                                    tool_version, model_version, scope, outcome, failure, retest_of)
         VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",
        rusqlite::params![
            task.task_id,
            task.principal,
            task.conditions,
            task.knowledge_version,
            task.method_version,
            task.tool_version,
            task.model_version,
            task.scope,
            task.outcome,
            task.failure,
            task.retest_of
        ],
    )?;
    tx.commit()?;
    Ok(())
}

/// Read one receipt back: (outcome, model_version, scope, failure, retest_of).
pub fn machine_task(
    conn: &Connection,
    task_id: &str,
) -> rusqlite::Result<Option<(String, String, String, Option<String>, Option<String>)>> {
    ensure_machine_tasks(conn)?;
    conn.query_row(
        "SELECT outcome, model_version, scope, failure, retest_of FROM machine_tasks WHERE task_id=?1",
        [task_id],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
    )
    .optional()
}

/// Count receipts along with how many were explicitly unmeasured, so a caller can
/// report coverage instead of implying that every task was verified.
pub fn machine_task_counts(conn: &Connection) -> rusqlite::Result<(i64, i64)> {
    ensure_machine_tasks(conn)?;
    let total: i64 = conn.query_row("SELECT count(*) FROM machine_tasks", [], |r| r.get(0))?;
    let unmeasured: i64 = conn.query_row(
        "SELECT count(*) FROM machine_tasks WHERE outcome='unmeasured'",
        [],
        |r| r.get(0),
    )?;
    Ok((total, unmeasured))
}
