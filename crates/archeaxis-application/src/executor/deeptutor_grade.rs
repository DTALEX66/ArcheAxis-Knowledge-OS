//! Internal DeepTutor grading process seam. This is not an authorization boundary.
//!
//! Until a Core admission/withdrawal boundary and final transaction are connected,
//! callers must use synthetic input only. No HTTP route, material grant, or durable
//! result is created here. The Python executable comes from the existing trusted
//! launch, never a request; its bytes are not yet pinned by a runtime manifest.
use super::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const CAPABILITY: &str = "deeptutor.practice.grade";
const SCHEMA: &str = "archeaxis.deeptutor-practice-grade/v1";
const WORKER_SHA: &str = "30d0a8e3f88a00186af0162f20953f14070cdc51ef42be4dca0e9948cb787b0e";
const UPSTREAM_SHA: &str = "fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f";
const MAX_INPUT: usize = 240_000;
const MAX_OUTPUT: u64 = 16_384;
const MAX_STDERR: u64 = 8_192;

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum GradeError {
    InvalidInput,
    InputMismatch,
    NotRegistered,
    IdentityMismatch,
    Unavailable,
    Rejected,
    BadReceipt,
    Cancelled,
    TimedOut,
    CleanupUnknown,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct InputEnvelope {
    schema: String,
    request_id: String,
    question: serde::de::IgnoredAny,
    answer: serde::de::IgnoredAny,
}

fn present_nullable_bool<'de, D: serde::Deserializer<'de>>(d: D) -> Result<Option<bool>, D::Error> {
    Option::<bool>::deserialize(d)
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct WorkerReceipt {
    schema: String,
    request_id: String,
    status: String,
    provider: String,
    adapter_version: String,
    upstream_member_sha256: String,
    #[serde(deserialize_with = "present_nullable_bool")]
    provider_correct: Option<bool>,
    question_binding: String,
    independent_mastery: String,
    input_sha256: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct FailureReceipt {
    schema: String,
    status: String,
    reason_code: String,
}

#[derive(Debug, Serialize)]
pub(crate) struct GradeObservation {
    pub(crate) provider_correct: Option<bool>,
    pub(crate) input_sha256: String,
    pub(crate) upstream_member_sha256: &'static str,
    pub(crate) question_binding: &'static str,
    pub(crate) independent_mastery: &'static str,
    pub(crate) descendant_state: &'static str,
}

fn valid_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"_-".contains(&c))
}

fn valid_sha(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}

fn validate_input(bytes: &[u8], request_id: &str, expected_sha: &str) -> Result<(), GradeError> {
    if bytes.is_empty()
        || bytes.len() > MAX_INPUT
        || bytes.last() != Some(&b'\n')
        || bytes[..bytes.len() - 1].contains(&b'\n')
        || !valid_id(request_id)
        || !valid_sha(expected_sha)
    {
        return Err(GradeError::InvalidInput);
    }
    if hex::encode(Sha256::digest(bytes)) != expected_sha {
        return Err(GradeError::InputMismatch);
    }
    let envelope: InputEnvelope =
        serde_json::from_slice(bytes).map_err(|_| GradeError::InvalidInput)?;
    let _ = (&envelope.question, &envelope.answer);
    if envelope.schema != SCHEMA || envelope.request_id != request_id {
        return Err(GradeError::InvalidInput);
    }
    Ok(())
}

fn file_matches(path: &Path, expected: &str) -> bool {
    if !derived::safe_local_file(path) {
        return false;
    }
    let Ok(metadata) = std::fs::metadata(path) else {
        return false;
    };
    if !metadata.is_file() || metadata.len() > 1_000_000 {
        return false;
    }
    let Ok(bytes) = std::fs::read(path) else {
        return false;
    };
    hex::encode(Sha256::digest(bytes)) == expected
}

fn worker_matches(worker: &Path) -> bool {
    worker.file_name().and_then(|s| s.to_str()) == Some("grade_worker.py")
        && file_matches(worker, WORKER_SHA)
        && worker
            .parent()
            .is_some_and(|dir| file_matches(&dir.join("upstream/answers.py"), UPSTREAM_SHA))
}

fn single_line(bytes: &[u8]) -> bool {
    !bytes.is_empty()
        && bytes.len() <= MAX_OUTPUT as usize
        && bytes.last() == Some(&b'\n')
        && !bytes[..bytes.len() - 1].contains(&b'\n')
}

fn parse_receipt(
    bytes: &[u8],
    request_id: &str,
    input_sha: &str,
) -> Result<GradeObservation, GradeError> {
    if !single_line(bytes) {
        return Err(GradeError::BadReceipt);
    }
    let receipt: WorkerReceipt =
        serde_json::from_slice(bytes).map_err(|_| GradeError::BadReceipt)?;
    if receipt.schema != SCHEMA
        || receipt.request_id != request_id
        || receipt.status != "OBSERVED"
        || receipt.provider != "deeptutor"
        || receipt.adapter_version != "1.7.1"
        || receipt.upstream_member_sha256 != UPSTREAM_SHA
        || receipt.input_sha256 != input_sha
        || receipt.question_binding != "caller_declared_unverified"
        || receipt.independent_mastery != "not_established"
    {
        return Err(GradeError::BadReceipt);
    }
    Ok(GradeObservation {
        provider_correct: receipt.provider_correct,
        input_sha256: receipt.input_sha256,
        upstream_member_sha256: UPSTREAM_SHA,
        question_binding: "caller_declared_unverified",
        independent_mastery: "not_established",
        descendant_state: "UNKNOWN",
    })
}

fn parse_failure(code: Option<i32>, bytes: &[u8]) -> GradeError {
    if !single_line(bytes) {
        return GradeError::BadReceipt;
    }
    let Ok(receipt) = serde_json::from_slice::<FailureReceipt>(bytes) else {
        return GradeError::BadReceipt;
    };
    if receipt.schema != SCHEMA {
        return GradeError::BadReceipt;
    }
    match (code, receipt.status.as_str(), receipt.reason_code.as_str()) {
        (Some(2), "INVALID_REQUEST", "INVALID_INPUT") => GradeError::Rejected,
        (Some(1), "UNAVAILABLE", "UPSTREAM_UNAVAILABLE") => GradeError::Unavailable,
        _ => GradeError::BadReceipt,
    }
}

struct CancelOnDrop(Option<Cancellation>);
impl Drop for CancelOnDrop {
    fn drop(&mut self) {
        if let Some(cancel) = &self.0 {
            cancel.cancel();
        }
    }
}

impl Executor {
    /// Internal synthetic seam only. Later Core integration must atomically
    /// bind dispatch and final persistence to current grants/attempt/epoch.
    #[allow(dead_code)]
    pub(crate) async fn deeptutor_grade_candidate(
        &self,
        bytes: Vec<u8>,
        request_id: String,
        expected_sha: String,
        timeout: Duration,
        cancel: Cancellation,
    ) -> Result<GradeObservation, GradeError> {
        if timeout.is_zero() || timeout > Duration::from_secs(120) {
            return Err(GradeError::InvalidInput);
        }
        let deadline = Instant::now() + timeout;
        validate_input(&bytes, &request_id, &expected_sha)?;
        if cancel.is_cancelled() {
            return Err(GradeError::Cancelled);
        }
        let (worker, _) = self
            .worker_for(CAPABILITY)
            .ok_or(GradeError::NotRegistered)?;
        let python = self.python.clone();
        if !derived::safe_local_file(&python) || !worker_matches(&worker) {
            return Err(GradeError::IdentityMismatch);
        }
        let permit = loop {
            if cancel.is_cancelled() {
                return Err(GradeError::Cancelled);
            }
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return Err(GradeError::TimedOut);
            }
            match tokio::time::timeout(
                remaining.min(Duration::from_millis(25)),
                self.derived_slots.clone().acquire_owned(),
            )
            .await
            {
                Ok(Ok(permit)) => break permit,
                Ok(Err(_)) => return Err(GradeError::Unavailable),
                Err(_) => continue,
            }
        };
        let staging = self.staging.clone();
        let task_cancel = cancel.clone();
        let mut cancel_on_drop = CancelOnDrop(Some(cancel));
        let task = tokio::task::spawn_blocking(move || {
            let _permit = permit;
            if task_cancel.is_cancelled() {
                return Err(GradeError::Cancelled);
            }
            if Instant::now() >= deadline {
                return Err(GradeError::TimedOut);
            }
            if !derived::safe_local_file(&python) || !worker_matches(&worker) {
                return Err(GradeError::IdentityMismatch);
            }
            let output = run_owned(&staging, &python, &worker, bytes, deadline, &task_cancel)?;
            if task_cancel.is_cancelled() {
                return Err(GradeError::Cancelled);
            }
            parse_receipt(&output, &request_id, &expected_sha)
        });
        let result = task.await.map_err(|_| GradeError::CleanupUnknown)?;
        cancel_on_drop.0 = None;
        result
    }
}

/// Own exactly the child returned by spawn. No assertion is made about descendants.
fn run_owned(
    staging: &Path,
    python: &Path,
    worker: &Path,
    bytes: Vec<u8>,
    deadline: Instant,
    cancel: &Cancellation,
) -> Result<Vec<u8>, GradeError> {
    if cancel.is_cancelled() {
        return Err(GradeError::Cancelled);
    }
    if Instant::now() >= deadline {
        return Err(GradeError::TimedOut);
    }
    let dir = tempfile::tempdir_in(staging).map_err(|_| GradeError::Unavailable)?;
    let mut command = Command::new(python);
    command.env_clear();
    for key in ["SystemRoot", "WINDIR", "SYSTEMDRIVE"] {
        if let Some(value) = std::env::var_os(key) {
            command.env(key, value);
        }
    }
    for key in [
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
    ] {
        command.env(key, dir.path());
    }
    command
        .arg("-I")
        .arg("-B")
        .arg("-S")
        .arg(worker)
        .current_dir(dir.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = OwnedChild(command.spawn().map_err(|_| GradeError::Unavailable)?);
    let mut input = child.0.stdin.take().ok_or(GradeError::CleanupUnknown)?;
    let mut output = child.0.stdout.take().ok_or(GradeError::CleanupUnknown)?;
    let mut errors = child.0.stderr.take().ok_or(GradeError::CleanupUnknown)?;
    let writer = thread::spawn(move || input.write_all(&bytes).map_err(|_| ()));
    let reader = thread::spawn(move || {
        let mut value = Vec::new();
        output
            .by_ref()
            .take(MAX_OUTPUT + 1)
            .read_to_end(&mut value)
            .map(|_| value)
            .map_err(|_| ())
    });
    let err_reader = thread::spawn(move || {
        let mut value = Vec::new();
        errors
            .by_ref()
            .take(MAX_STDERR + 1)
            .read_to_end(&mut value)
            .map(|_| value.len())
            .map_err(|_| ())
    });
    let result = loop {
        if cancel.is_cancelled() {
            break Err(GradeError::Cancelled);
        }
        if Instant::now() >= deadline {
            break Err(GradeError::TimedOut);
        }
        match child.0.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(_) => break Err(GradeError::CleanupUnknown),
        }
    };
    if !matches!(child.0.try_wait(), Ok(Some(_))) {
        let _ = child.0.kill();
    }
    let reap_deadline = Instant::now() + Duration::from_secs(1);
    let reaped = loop {
        match child.0.try_wait() {
            Ok(Some(_)) => break true,
            Ok(None) if Instant::now() < reap_deadline => thread::sleep(Duration::from_millis(5)),
            _ => break false,
        }
    };
    if reaped {
        drop(child);
    } else {
        // Keep ownership in a private reaper if the OS cannot confirm exit in
        // time; callers receive UNKNOWN and must not claim a successful cleanup.
        thread::spawn(move || drop(child));
    }
    let drain_deadline = Instant::now() + Duration::from_millis(500);
    while (!writer.is_finished() || !reader.is_finished() || !err_reader.is_finished())
        && Instant::now() < drain_deadline
    {
        thread::sleep(Duration::from_millis(5));
    }
    #[cfg(windows)]
    {
        use std::os::windows::io::AsRawHandle;
        #[link(name = "kernel32")]
        unsafe extern "system" {
            fn CancelSynchronousIo(thread: *mut std::ffi::c_void) -> i32;
        }
        let handles = [
            (!writer.is_finished(), writer.as_raw_handle()),
            (!reader.is_finished(), reader.as_raw_handle()),
            (!err_reader.is_finished(), err_reader.as_raw_handle()),
        ];
        for (unfinished, handle) in handles {
            if unfinished {
                unsafe {
                    CancelSynchronousIo(handle);
                }
            }
        }
    }
    let cleanup_deadline = Instant::now() + Duration::from_millis(500);
    while (!writer.is_finished() || !reader.is_finished() || !err_reader.is_finished())
        && Instant::now() < cleanup_deadline
    {
        thread::sleep(Duration::from_millis(5));
    }
    if !writer.is_finished() || !reader.is_finished() || !err_reader.is_finished() {
        return Err(GradeError::CleanupUnknown);
    }
    let write_result = writer.join().map_err(|_| GradeError::CleanupUnknown)?;
    let stdout_result = reader.join().map_err(|_| GradeError::CleanupUnknown)?;
    let stderr_result = err_reader.join().map_err(|_| GradeError::CleanupUnknown)?;
    if !reaped {
        return Err(GradeError::CleanupUnknown);
    }
    if dir.close().is_err() {
        return Err(GradeError::CleanupUnknown);
    }
    let status = result?;
    let stdout = stdout_result.map_err(|_| GradeError::Unavailable)?;
    let stderr_len = stderr_result.map_err(|_| GradeError::Unavailable)?;
    if write_result.is_err() || stderr_len != 0 || stdout.len() > MAX_OUTPUT as usize {
        return Err(GradeError::Unavailable);
    }
    if !status.success() {
        return Err(parse_failure(status.code(), &stdout));
    }
    Ok(stdout)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn input() -> Vec<u8> {
        let mut bytes = serde_json::to_vec(&json!({"schema":SCHEMA,"request_id":"synthetic_1",
            "question":{"question_type":"single_choice","options":{"A":"one","B":"two"},"correct_answer":"A"},
            "answer":"A"})).unwrap();
        bytes.push(b'\n');
        bytes
    }

    fn digest(bytes: &[u8]) -> String {
        hex::encode(Sha256::digest(bytes))
    }

    fn receipt(correct: serde_json::Value, input_sha: &str) -> Vec<u8> {
        let mut bytes = serde_json::to_vec(
            &json!({"schema":SCHEMA,"request_id":"synthetic_1","status":"OBSERVED",
            "provider":"deeptutor","adapter_version":"1.7.1","upstream_member_sha256":UPSTREAM_SHA,
            "provider_correct":correct,"question_binding":"caller_declared_unverified",
            "independent_mastery":"not_established","input_sha256":input_sha}),
        )
        .unwrap();
        bytes.push(b'\n');
        bytes
    }

    #[test]
    fn exact_receipt_requires_complete_identity_and_never_returns_answer_fields() {
        let hash = digest(&input());
        for expected in [json!(true), json!(false), json!(null)] {
            let output =
                parse_receipt(&receipt(expected.clone(), &hash), "synthetic_1", &hash).unwrap();
            assert_eq!(
                serde_json::to_value(output).unwrap()["provider_correct"],
                expected
            );
        }
        let valid: serde_json::Value =
            serde_json::from_slice(&receipt(json!(true), &hash)).unwrap();
        for field in [
            "input_sha256",
            "upstream_member_sha256",
            "request_id",
            "question_binding",
            "independent_mastery",
        ] {
            let mut changed = valid.clone();
            changed[field] = json!("untrusted");
            let mut bytes = serde_json::to_vec(&changed).unwrap();
            bytes.push(b'\n');
            assert!(
                matches!(
                    parse_receipt(&bytes, "synthetic_1", &hash),
                    Err(GradeError::BadReceipt)
                ),
                "{field}"
            );
        }
        let mut extra = valid.clone();
        extra["answer"] = json!("synthetic private field");
        let mut bytes = serde_json::to_vec(&extra).unwrap();
        bytes.push(b'\n');
        assert!(matches!(
            parse_receipt(&bytes, "synthetic_1", &hash),
            Err(GradeError::BadReceipt)
        ));
        let mut missing = valid.as_object().unwrap().clone();
        missing.remove("provider_correct");
        let mut bytes = serde_json::to_vec(&missing).unwrap();
        bytes.push(b'\n');
        assert!(matches!(
            parse_receipt(&bytes, "synthetic_1", &hash),
            Err(GradeError::BadReceipt)
        ));
        let mut duplicated = String::from_utf8(receipt(json!(true), &hash)).unwrap();
        duplicated = duplicated.replacen(
            "\"status\":\"OBSERVED\"",
            "\"status\":\"OBSERVED\",\"status\":\"OBSERVED\"",
            1,
        );
        assert!(matches!(
            parse_receipt(duplicated.as_bytes(), "synthetic_1", &hash),
            Err(GradeError::BadReceipt)
        ));
        let mut two_lines = receipt(json!(true), &hash);
        two_lines.push(b'\n');
        assert!(matches!(
            parse_receipt(&two_lines, "synthetic_1", &hash),
            Err(GradeError::BadReceipt)
        ));
        let invalid = format!(
            "{{\"schema\":\"{SCHEMA}\",\"status\":\"INVALID_REQUEST\",\"reason_code\":\"INVALID_INPUT\"}}\n"
        );
        let unavailable = format!(
            "{{\"schema\":\"{SCHEMA}\",\"status\":\"UNAVAILABLE\",\"reason_code\":\"UPSTREAM_UNAVAILABLE\"}}\n"
        );
        assert_eq!(
            parse_failure(Some(2), invalid.as_bytes()),
            GradeError::Rejected
        );
        assert_eq!(
            parse_failure(Some(1), unavailable.as_bytes()),
            GradeError::Unavailable
        );
        assert_eq!(
            parse_failure(Some(2), unavailable.as_bytes()),
            GradeError::BadReceipt
        );
    }

    #[tokio::test]
    async fn no_route_or_mismatched_exact_input_never_launches() {
        let dir = tempfile::tempdir().unwrap();
        let executor = Executor::open(
            &dir.path().join("db"),
            &dir.path().join("stage"),
            &dir.path().join("unused-python"),
            &dir.path().join("unused-worker"),
        )
        .await
        .unwrap();
        let bytes = input();
        let hash = digest(&bytes);
        assert!(matches!(
            executor
                .deeptutor_grade_candidate(
                    bytes.clone(),
                    "synthetic_1".into(),
                    "0".repeat(64),
                    Duration::from_secs(2),
                    Cancellation::new()
                )
                .await,
            Err(GradeError::InputMismatch)
        ));
        assert!(matches!(
            executor
                .deeptutor_grade_candidate(
                    bytes.clone(),
                    "synthetic_1".into(),
                    hash.clone(),
                    Duration::from_secs(2),
                    Cancellation::new()
                )
                .await,
            Err(GradeError::NotRegistered)
        ));
        let cancelled = Cancellation::new();
        cancelled.cancel();
        assert!(matches!(
            executor
                .deeptutor_grade_candidate(
                    bytes,
                    "synthetic_1".into(),
                    hash,
                    Duration::from_secs(2),
                    cancelled
                )
                .await,
            Err(GradeError::Cancelled)
        ));
    }

    #[test]
    fn fixed_worker_and_original_answer_source_must_match() {
        let source = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/learning-providers/deeptutor");
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir(dir.path().join("upstream")).unwrap();
        let worker = dir.path().join("grade_worker.py");
        let upstream = dir.path().join("upstream/answers.py");
        std::fs::copy(source.join("grade_worker.py"), &worker).unwrap();
        std::fs::copy(source.join("upstream/answers.py"), &upstream).unwrap();
        assert!(worker_matches(&worker));
        std::fs::write(&upstream, b"changed").unwrap();
        assert!(!worker_matches(&worker));
        std::fs::copy(source.join("upstream/answers.py"), &upstream).unwrap();
        std::fs::write(&worker, b"changed").unwrap();
        assert!(!worker_matches(&worker));
    }

    #[tokio::test]
    #[ignore = "requires explicit ARCHEAXIS_PYTHON and starts the retained upstream worker"]
    async fn explicit_python_runs_real_grade_worker_on_synthetic_input() {
        let python =
            PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("explicit Python required"));
        assert!(python.is_absolute());
        let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/learning-providers/deeptutor/grade_worker.py")
            .canonicalize()
            .unwrap();
        let dir = tempfile::tempdir().unwrap();
        let executor = Executor::open_routes(
            &dir.path().join("db"),
            &dir.path().join("stage"),
            &python,
            &dir.path().join("unused-worker"),
            &[(CAPABILITY, worker)],
        )
        .await
        .unwrap();
        let bytes = input();
        let hash = digest(&bytes);
        let observation = executor
            .deeptutor_grade_candidate(
                bytes,
                "synthetic_1".into(),
                hash.clone(),
                Duration::from_secs(15),
                Cancellation::new(),
            )
            .await
            .unwrap();
        assert_eq!(observation.provider_correct, Some(true));
        assert_eq!(observation.input_sha256, hash);
        assert_eq!(observation.independent_mastery, "not_established");
        assert_eq!(observation.descendant_state, "UNKNOWN");
        let body = serde_json::to_value(observation).unwrap();
        assert!(body.get("answer").is_none() && body.get("correct_answer").is_none());
    }

    #[test]
    #[ignore = "requires explicit ARCHEAXIS_PYTHON and starts one synthetic sleeping child"]
    fn timeout_reaps_owned_child_or_reports_cleanup_unknown() {
        let python =
            PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("explicit Python required"));
        assert!(python.is_absolute());
        let dir = tempfile::tempdir().unwrap();
        let worker = dir.path().join("sleep.py");
        std::fs::write(&worker, b"import time\ntime.sleep(1)\n").unwrap();
        let start = Instant::now();
        let result = run_owned(
            dir.path(),
            &python,
            &worker,
            Vec::new(),
            start + Duration::from_millis(100),
            &Cancellation::new(),
        );
        assert!(matches!(
            result,
            Err(GradeError::TimedOut | GradeError::CleanupUnknown)
        ));
        assert!(start.elapsed() < Duration::from_secs(5));
    }

    #[test]
    #[ignore = "requires explicit ARCHEAXIS_PYTHON and starts one synthetic sleeping child"]
    fn cancellation_during_worker_reaps_owned_child_or_reports_unknown() {
        let python =
            PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("explicit Python required"));
        assert!(python.is_absolute());
        let dir = tempfile::tempdir().unwrap();
        let worker = dir.path().join("sleep.py");
        let marker = dir.path().join("worker-started");
        let marker_literal = serde_json::to_string(&marker.to_string_lossy().to_string()).unwrap();
        std::fs::write(&worker, format!("from pathlib import Path\nimport time\nPath({marker_literal}).write_text('started')\ntime.sleep(1)\n")).unwrap();
        let cancel = Cancellation::new();
        let token = cancel.clone();
        let staging = dir.path().to_owned();
        let task = thread::spawn(move || {
            run_owned(
                &staging,
                &python,
                &worker,
                Vec::new(),
                Instant::now() + Duration::from_secs(5),
                &token,
            )
        });
        let end = Instant::now() + Duration::from_secs(3);
        while !marker.exists() && Instant::now() < end {
            thread::sleep(Duration::from_millis(5));
        }
        assert!(marker.exists(), "synthetic worker did not start");
        cancel.cancel();
        let result = task.join().unwrap();
        assert!(matches!(
            result,
            Err(GradeError::Cancelled | GradeError::CleanupUnknown)
        ));
    }
}
