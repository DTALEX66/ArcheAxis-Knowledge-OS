//! R05: Core-side scheduling adapter.
//!
//! The reused py-fsrs worker (`services/python-workers/learning/worker_schedule.py`)
//! is the single scheduling authority. This adapter asks it for the next review
//! date and reports an explicit failure when the scheduler is unusable - it never
//! falls back to the temporary interval ladder in `archeaxis-domain::learning`,
//! so a review can be recorded as *unscheduled* instead of silently scheduled by
//! a placeholder.

use std::io::{Read, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};

const MAX_REQUEST_BYTES: usize = 65_536;
const MAX_RESPONSE_BYTES: usize = 65_536;
const MAX_STDERR_BYTES: usize = 32_768;

struct OwnedSchedulerChild(Child);
impl OwnedSchedulerChild {
    fn stop(&mut self) -> std::io::Result<()> {
        if self.0.try_wait()?.is_none() {
            self.0.kill()?;
            self.0.wait()?;
        }
        Ok(())
    }
}
impl Drop for OwnedSchedulerChild {
    fn drop(&mut self) {
        let _ = self.stop();
    }
}

fn bounded_read(reader: impl Read, maximum: usize, stream: &str) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    reader
        .take(maximum as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| format!("{stream} read failed: {e}"))?;
    if bytes.len() > maximum {
        return Err(format!("{stream} exceeds byte limit"));
    }
    Ok(bytes)
}

/// Scheduling authority reported by the reused FSRS worker.
pub const AUTHORITY_FSRS: &str = "fsrs";

/// Repository-relative location of the scheduler worker.
pub const WORKER_RELATIVE_PATH: &str = "services/python-workers/learning/worker_schedule.py";

/// Profile schema the desktop supervisor and the Green candidate already publish.
///
/// The runtime already resolves the worker interpreter once, in
/// `worker-profile.json`. Requiring every caller to *also* export
/// `ARCHEAXIS_PYTHON` duplicated that resolution and failed silently: a caller that
/// forgot it got `available` scheduling replaced by `unavailable` with no named
/// error, which reads like a product defect. The Core now reads the profile the
/// runtime already writes.
pub const WORKER_PROFILE_SCHEMA: &str = "archeaxis.worker-profile/v1";

/// File name the supervisor writes beside the executable.
pub const WORKER_PROFILE_NAME: &str = "worker-profile.json";

/// Read the interpreter out of one `archeaxis.worker-profile/v1` document.
///
/// A relative `python` is resolved against the profile's own directory, so a staged
/// runtime stays relocatable. Every rejection names its reason instead of degrading
/// to a default interval.
pub fn python_from_profile_text(
    text: &str,
    profile: &std::path::Path,
) -> Result<PathBuf, SchedulerError> {
    let document: serde_json::Value = serde_json::from_str(text).map_err(|error| {
        SchedulerError::Unavailable(format!("worker profile is not valid JSON: {error}"))
    })?;
    if document.get("schema").and_then(|value| value.as_str()) != Some(WORKER_PROFILE_SCHEMA) {
        return Err(SchedulerError::Unavailable(format!(
            "worker profile schema is not {WORKER_PROFILE_SCHEMA}"
        )));
    }
    let raw = document
        .get("python")
        .and_then(|value| value.as_str())
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| {
            SchedulerError::Unavailable("worker profile has no python interpreter".into())
        })?;
    let path = PathBuf::from(raw);
    let resolved = if path.is_absolute() {
        path
    } else {
        profile
            .parent()
            .unwrap_or_else(|| std::path::Path::new("."))
            .join(path)
    };
    if !resolved.is_file() {
        return Err(SchedulerError::Unavailable(format!(
            "worker profile python is not a file: {}",
            resolved.display()
        )));
    }
    Ok(resolved)
}

/// Resolve the scheduler interpreter without requiring manual configuration.
///
/// Order: `ARCHEAXIS_PYTHON`, then the profile named by `ARCHEAXIS_WORKER_PROFILE`
/// (or the legacy `ARCHAXIS_WORKER_PROFILE`), then `worker-profile.json` beside the
/// running executable. Neither the profile nor the variable is allowed to point at a
/// missing file silently.
fn resolve_python() -> Result<PathBuf, SchedulerError> {
    if let Some(value) = std::env::var_os("ARCHEAXIS_PYTHON") {
        let configured = PathBuf::from(value);
        if !configured.is_file() {
            return Err(SchedulerError::Unavailable(format!(
                "ARCHEAXIS_PYTHON is not a file: {}",
                configured.display()
            )));
        }
        return Ok(configured);
    }
    let mut candidates: Vec<PathBuf> = Vec::new();
    for name in ["ARCHEAXIS_WORKER_PROFILE", "ARCHAXIS_WORKER_PROFILE"] {
        if let Some(value) = std::env::var_os(name) {
            candidates.push(PathBuf::from(value));
        }
    }
    if let Ok(executable) = std::env::current_exe() {
        if let Some(directory) = executable.parent() {
            candidates.push(directory.join(WORKER_PROFILE_NAME));
        }
    }
    let mut reasons: Vec<String> = Vec::new();
    for candidate in candidates {
        if !candidate.is_file() {
            reasons.push(format!("{} is not a file", candidate.display()));
            continue;
        }
        match std::fs::read_to_string(&candidate) {
            Ok(text) => match python_from_profile_text(&text, &candidate) {
                Ok(python) => return Ok(python),
                Err(SchedulerError::Unavailable(reason)) => {
                    reasons.push(format!("{}: {reason}", candidate.display()));
                }
                Err(other) => return Err(other),
            },
            Err(error) => reasons.push(format!("{}: {error}", candidate.display())),
        }
    }
    if reasons.is_empty() {
        reasons.push("no worker profile was found".into());
    }
    Err(SchedulerError::Unavailable(format!(
        "no scheduler interpreter: set ARCHEAXIS_PYTHON or publish {WORKER_PROFILE_NAME} \
         ({})",
        reasons.join("; ")
    )))
}

#[cfg(test)]
mod tests {
    use super::{
        WORKER_PROFILE_SCHEMA, WORKER_RELATIVE_PATH, python_from_profile_text,
        resolve_scheduler_worker,
    };
    use std::path::Path;

    /// Any path that certainly exists, so the file check is exercised rather than
    /// mocked: the running test binary itself.
    fn existing_file() -> String {
        std::env::current_exe()
            .unwrap()
            .to_string_lossy()
            .into_owned()
    }

    fn profile(python: &str, schema: &str) -> String {
        format!(
            r#"{{"schema":"{schema}","python":{},"script":"workers/transport/text_ndjson.py","staging":"data/worker-staging"}}"#,
            serde_json::Value::String(python.to_string())
        )
    }

    #[test]
    fn profile_interpreter_is_accepted() {
        let python = existing_file();
        let resolved = python_from_profile_text(
            &profile(&python, WORKER_PROFILE_SCHEMA),
            Path::new(r"C:\candidate\worker-profile.json"),
        )
        .unwrap();
        assert_eq!(resolved, Path::new(&python));
    }

    #[test]
    fn relative_profile_interpreter_resolves_against_the_profile_directory() {
        // A staged runtime keeps `runtime/python.exe` relative so the candidate stays
        // relocatable; the resolved path must be what the caller sees in the error.
        let error = python_from_profile_text(
            &profile(r"runtime\python.exe", WORKER_PROFILE_SCHEMA),
            Path::new(r"C:\candidate\worker-profile.json"),
        )
        .unwrap_err();
        let message = error.to_string();
        assert!(message.contains("is not a file"), "{message}");
        assert!(
            message.contains(r"C:\candidate\runtime\python.exe"),
            "{message}"
        );
    }

    #[test]
    fn wrong_schema_missing_interpreter_and_broken_json_each_name_their_reason() {
        let python = existing_file();
        let cases = [
            // Not a version-shaped literal: `scripts/check_language_boundaries.py`
            // scans source text for `<name>/v<digit>` envelope versions, so writing
            // `worker-profile/v2` here read as a second version of the same envelope
            // inside one language and failed a real repository gate.
            (
                profile(&python, "archeaxis.worker-profile/unsupported"),
                "schema is not",
            ),
            (
                r#"{"schema":"archeaxis.worker-profile/v1"}"#.to_string(),
                "no python interpreter",
            ),
            (
                r#"{"schema":"archeaxis.worker-profile/v1","python":"  "}"#.to_string(),
                "no python interpreter",
            ),
            ("not json".to_string(), "not valid JSON"),
        ];
        for (text, expected) in cases {
            let error =
                python_from_profile_text(&text, Path::new(r"C:\candidate\worker-profile.json"))
                    .unwrap_err();
            assert!(
                error.to_string().contains(expected),
                "expected {expected:?} in {error}"
            );
        }
    }

    #[test]
    fn explicit_scheduler_worker_wins_for_portable_runtime() {
        let packaged = Path::new(r"C:\candidate\workers\learning\worker_schedule.py");
        let repo = Path::new(r"C:\repo");
        assert_eq!(
            resolve_scheduler_worker(Some(packaged), None, repo),
            packaged
        );
    }

    #[test]
    fn legacy_scheduler_worker_name_is_supported() {
        let packaged = Path::new(r"C:\candidate\workers\learning\worker_schedule.py");
        let repo = Path::new(r"C:\repo");
        assert_eq!(
            resolve_scheduler_worker(None, Some(packaged), repo),
            packaged
        );
    }

    #[test]
    fn repository_worker_remains_development_fallback() {
        let repo = Path::new(r"C:\repo");
        assert_eq!(
            resolve_scheduler_worker(None, None, repo),
            repo.join(WORKER_RELATIVE_PATH)
        );
    }
}

fn resolve_scheduler_worker(
    explicit: Option<&std::path::Path>,
    legacy: Option<&std::path::Path>,
    repository: &std::path::Path,
) -> PathBuf {
    explicit
        .or(legacy)
        .map(PathBuf::from)
        .unwrap_or_else(|| repository.join(WORKER_RELATIVE_PATH))
}

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
    pub card_state: serde_json::Value,
}

pub struct SchedulerClient {
    python: PathBuf,
    worker: PathBuf,
}

impl SchedulerClient {
    pub fn new(python: impl Into<PathBuf>, worker: impl Into<PathBuf>) -> Self {
        Self {
            python: python.into(),
            worker: worker.into(),
        }
    }

    /// Build a client from the runtime's own worker profile, or `ARCHEAXIS_PYTHON`
    /// when one is exported. The repository path remains the development fallback.
    pub fn from_env() -> Result<Self, SchedulerError> {
        let python = resolve_python()?;
        let repository = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..");
        let worker = resolve_scheduler_worker(
            std::env::var_os("ARCHEAXIS_SCHEDULER_WORKER")
                .as_deref()
                .map(std::path::Path::new),
            std::env::var_os("ARCHAXIS_SCHEDULER_WORKER")
                .as_deref()
                .map(std::path::Path::new),
            &repository,
        );
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
        self.review_with_timeout(request, Duration::from_secs(20))
    }

    /// Bound stdin, both output streams and process exit by one deadline.
    /// This owns the direct FSRS process, not arbitrary descendant runtimes.
    pub fn review_with_timeout(
        &self,
        request: &str,
        timeout: Duration,
    ) -> Result<Schedule, SchedulerError> {
        if request.len() > MAX_REQUEST_BYTES {
            return Err(SchedulerError::Rejected(
                "request exceeds byte limit".into(),
            ));
        }
        if timeout.is_zero() || timeout > Duration::from_secs(60) {
            return Err(SchedulerError::Rejected(
                "deadline must be positive and at most 60 seconds".into(),
            ));
        }
        let deadline = Instant::now() + timeout;
        if !self.python.is_file() {
            return Err(SchedulerError::Unavailable(
                "interpreter is not a file".into(),
            ));
        }
        if !self.worker.is_file() {
            return Err(SchedulerError::Unavailable(
                "scheduler worker is not a file".into(),
            ));
        }
        let mut command = Command::new(&self.python);
        command
            .arg("-B")
            .arg(&self.worker)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        let mut child = OwnedSchedulerChild(
            command
                .spawn()
                .map_err(|e| SchedulerError::Unavailable(e.to_string()))?,
        );
        let mut stdin = child
            .0
            .stdin
            .take()
            .ok_or_else(|| SchedulerError::Unavailable("no stdin pipe".into()))?;
        let stdout = child
            .0
            .stdout
            .take()
            .ok_or_else(|| SchedulerError::Unavailable("no stdout pipe".into()))?;
        let stderr = child
            .0
            .stderr
            .take()
            .ok_or_else(|| SchedulerError::Unavailable("no stderr pipe".into()))?;
        let (send, receive) = mpsc::sync_channel::<Result<Option<Vec<u8>>, String>>(3);
        let mut threads = Vec::new();
        let payload = request.as_bytes().to_vec();
        let input_send = send.clone();
        threads.push(
            thread::Builder::new()
                .name("fsrs-stdin".into())
                .spawn(move || {
                    let result = stdin
                        .write_all(&payload)
                        .and_then(|_| stdin.write_all(b"\n"))
                        .map(|_| None)
                        .map_err(|e| format!("stdin write failed: {e}"));
                    drop(stdin);
                    let _ = input_send.send(result);
                })
                .map_err(|e| SchedulerError::Unavailable(e.to_string()))?,
        );
        let output_send = send.clone();
        threads.push(
            thread::Builder::new()
                .name("fsrs-stdout".into())
                .spawn(move || {
                    let _ = output_send
                        .send(bounded_read(stdout, MAX_RESPONSE_BYTES, "stdout").map(Some));
                })
                .map_err(|e| SchedulerError::Unavailable(e.to_string()))?,
        );
        threads.push(
            thread::Builder::new()
                .name("fsrs-stderr".into())
                .spawn(move || {
                    let _ =
                        send.send(bounded_read(stderr, MAX_STDERR_BYTES, "stderr").map(|_| None));
                })
                .map_err(|e| SchedulerError::Unavailable(e.to_string()))?,
        );
        let result = (|| {
            let mut finished = 0;
            let mut output = None;
            loop {
                if Instant::now() >= deadline {
                    return Err(SchedulerError::Unavailable(
                        "worker execution deadline exceeded".into(),
                    ));
                }
                let status = child
                    .0
                    .try_wait()
                    .map_err(|e| SchedulerError::Unavailable(e.to_string()))?;
                if finished == 3 {
                    if let Some(status) = status {
                        return Ok((output.unwrap_or_default(), status));
                    }
                    thread::sleep(Duration::from_millis(5));
                    continue;
                }
                match receive.recv_timeout(Duration::from_millis(5)) {
                    Ok(Ok(value)) => {
                        finished += 1;
                        if value.is_some() {
                            output = value;
                        }
                    }
                    Ok(Err(error)) => return Err(SchedulerError::Unavailable(error)),
                    Err(mpsc::RecvTimeoutError::Timeout) => {}
                    Err(mpsc::RecvTimeoutError::Disconnected) => {
                        return Err(SchedulerError::Unavailable(
                            "worker I/O thread stopped before completion".into(),
                        ));
                    }
                }
            }
        })();
        child
            .stop()
            .map_err(|e| SchedulerError::Unavailable(format!("worker cleanup failed: {e}")))?;
        let cleanup_deadline = Instant::now() + Duration::from_secs(1);
        while threads.iter().any(|t| !t.is_finished()) && Instant::now() < cleanup_deadline {
            thread::sleep(Duration::from_millis(5));
        }
        if threads.iter().any(|t| !t.is_finished()) {
            return Err(SchedulerError::Unavailable(
                "worker cleanup incomplete: pipe still held outside direct worker".into(),
            ));
        }
        for handle in threads {
            handle
                .join()
                .map_err(|_| SchedulerError::Unavailable("worker I/O thread panicked".into()))?;
        }
        let (line, status) = result?;
        let parsed: serde_json::Value = serde_json::from_slice(&line).map_err(|e| {
            SchedulerError::Unavailable(format!("unparsable scheduler response: {e}"))
        })?;
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
            .ok_or_else(|| {
                SchedulerError::Unavailable("response has no next_review_days".into())
            })?;
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
        let mut card_state = serde_json::Map::new();
        for field in [
            "state",
            "step",
            "stability",
            "difficulty",
            "due",
            "last_review",
        ] {
            let value = parsed.get(field).ok_or_else(|| {
                SchedulerError::Unavailable(format!("response missing card field {field}"))
            })?;
            card_state.insert(field.into(), value.clone());
        }
        Ok(Schedule {
            authority,
            next_review_days,
            due,
            state,
            card_state: card_state.into(),
        })
    }
}
