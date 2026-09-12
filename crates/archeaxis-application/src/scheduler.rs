//! R05: Core-side scheduling adapter.
//!
//! The reused py-fsrs worker (`services/python-workers/learning/worker_schedule.py`)
//! is the single scheduling authority. This adapter asks it for the next review
//! date and reports an explicit failure when the scheduler is unusable - it never
//! falls back to the temporary interval ladder in `archeaxis-domain::learning`,
//! so a review can be recorded as *unscheduled* instead of silently scheduled by
//! a placeholder.

use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};

/// Scheduling authority reported by the reused FSRS worker.
pub const AUTHORITY_FSRS: &str = "fsrs";

/// Repository-relative location of the scheduler worker.
pub const WORKER_RELATIVE_PATH: &str =
    "services/python-workers/learning/worker_schedule.py";

#[derive(Debug)]
pub enum SchedulerError {
    /// The worker could not be run at all (missing interpreter/script, spawn or
    /// IO failure, no response). The caller must record the review as
    /// unscheduled - not invent an interval.
    Unavailable(String),
    /// The worker answered with an explicit rejection (`{"error": ...}`).
    Rejected(String),
}

impl std::fmt::Display for SchedulerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SchedulerError::Unavailable(m) => write!(f, "scheduler unavailable: {m}"),
            SchedulerError::Rejected(m) => write!(f, "scheduler rejected the request: {m}"),
        }
    }
}

impl std::error::Error for SchedulerError {}

/// A scheduling answer produced by the reused scheduler.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Schedule {
    pub authority: String,
    pub next_review_days: i64,
    pub due: String,
    pub state: String,
}

pub struct SchedulerClient {
    python: PathBuf,
    worker: PathBuf,
}

impl SchedulerClient {
    pub fn new(python: impl Into<PathBuf>, worker: impl Into<PathBuf>) -> Self {
        Self { python: python.into(), worker: worker.into() }
    }

    /// Build a client from `ARCHEAXIS_PYTHON` plus the repository worker path
    /// derived from this crate's manifest directory.
    pub fn from_env() -> Result<Self, SchedulerError> {
        let python = std::env::var_os("ARCHEAXIS_PYTHON")
            .map(PathBuf::from)
            .ok_or_else(|| SchedulerError::Unavailable("ARCHEAXIS_PYTHON is not set".into()))?;
        let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join(WORKER_RELATIVE_PATH);
        Ok(Self::new(python, worker))
    }

    pub fn worker_path(&self) -> &std::path::Path {
        &self.worker
    }

    /// Ask the reused scheduler for the next review of one item.
    ///
    /// `request` is the worker's JSON request (item_key, rating or correct,
    /// persisted card state, optional now).
    pub fn review(&self, request: &str) -> Result<Schedule, SchedulerError> {
        if !self.python.is_file() {
            return Err(SchedulerError::Unavailable("interpreter is not a file".into()));
        }
        if !self.worker.is_file() {
            return Err(SchedulerError::Unavailable("scheduler worker is not a file".into()));
        }
        let mut child = Command::new(&self.python)
            .arg(&self.worker)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| SchedulerError::Unavailable(e.to_string()))?;
        {
            let stdin = child
                .stdin
                .as_mut()
                .ok_or_else(|| SchedulerError::Unavailable("no stdin pipe".into()))?;
            stdin
                .write_all(request.as_bytes())
                .and_then(|_| stdin.write_all(b"\n"))
                .map_err(|e| SchedulerError::Unavailable(e.to_string()))?;
        }
        // Closing stdin lets the worker finish even if it waits for EOF.
        drop(child.stdin.take());
        let mut line = String::new();
        {
            let stdout = child
                .stdout
                .take()
                .ok_or_else(|| SchedulerError::Unavailable("no stdout pipe".into()))?;
            BufReader::new(stdout)
                .read_line(&mut line)
                .map_err(|e| SchedulerError::Unavailable(e.to_string()))?;
        }
        let status = child.wait().map_err(|e| SchedulerError::Unavailable(e.to_string()))?;
        let parsed: serde_json::Value = serde_json::from_str(line.trim())
            .map_err(|e| SchedulerError::Unavailable(format!("unparsable scheduler response: {e}")))?;
        if let Some(error) = parsed.get("error").and_then(|v| v.as_str()) {
            return Err(SchedulerError::Rejected(error.to_string()));
        }
        if !status.success() {
            return Err(SchedulerError::Unavailable(format!(
                "scheduler exited with {status}"
            )));
        }
        let next_review_days = parsed
            .get("next_review_days")
            .and_then(|v| v.as_i64())
            .ok_or_else(|| SchedulerError::Unavailable("response has no next_review_days".into()))?;
        let authority = parsed
            .get("authority")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string();
        if authority != AUTHORITY_FSRS {
            return Err(SchedulerError::Unavailable(format!(
                "unexpected scheduling authority {authority:?}"
            )));
        }
        let due = parsed
            .get("due")
            .and_then(|v| v.as_str())
            .ok_or_else(|| SchedulerError::Unavailable("response has no due date".into()))?
            .to_string();
        let state = parsed
            .get("state")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string();
        Ok(Schedule { authority, next_review_days, due, state })
    }
}
