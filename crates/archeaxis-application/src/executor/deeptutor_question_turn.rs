//! DeepTutor's private single-question worker process. Capture and replay use
//! the same fixed worker; the Core owns admission, the model call and every
//! write. Input and output may carry material and generated answers and must
//! never enter job logs.
use super::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const WORKER_NAME: &str = "question_turn_worker.py";
const WORKER_SIZE: u64 = 24_499;
const WORKER_SHA: &str = "e77a572778a1738195684dcaa672c7e68afc316a8ac7e6312f9ae4eb6f958570";
const MAX_FRAME: usize = 256 * 1024;
const MAX_REPLY: u64 = 512 * 1024;
const MAX_STDERR: u64 = 8_192;

#[derive(Debug, PartialEq, Eq)]
pub enum QuestionTurnWorkerError {
    InvalidInput,
    Unavailable,
    IdentityMismatch,
    Cancelled,
    TimedOut,
    CleanupUnknown,
}

fn worker_matches(path: &Path) -> bool {
    if path.file_name().and_then(|value| value.to_str()) != Some(WORKER_NAME)
        || !derived::safe_local_file(path)
    {
        return false;
    }
    let Ok(mut file) = std::fs::File::open(path) else {
        return false;
    };
    let Ok(before) = file.metadata() else {
        return false;
    };
    if !before.is_file() || before.len() != WORKER_SIZE {
        return false;
    }
    let mut bytes = Vec::with_capacity((WORKER_SIZE + 1) as usize);
    if (&mut file)
        .take(WORKER_SIZE + 1)
        .read_to_end(&mut bytes)
        .is_err()
    {
        return false;
    }
    let Ok(after) = file.metadata() else {
        return false;
    };
    bytes.len() as u64 == WORKER_SIZE
        && after.len() == before.len()
        && after.modified().ok() == before.modified().ok()
        && hex::encode(Sha256::digest(&bytes)) == WORKER_SHA
}

impl Executor {
    /// The fixed question worker, resolved as a sibling of the launch-declared
    /// practice import worker and then pinned by name, size and SHA.
    fn question_turn_worker(&self) -> Option<PathBuf> {
        self.deeptutor_practice_worker
            .as_ref()
            .and_then(|path| path.parent())
            .map(|dir| dir.join(WORKER_NAME))
    }

    /// Run one bounded capture or replay line and return its declared outcome.
    /// Exit 0/1/2 are preserved with the worker's own document, so the caller
    /// maps `UNAVAILABLE` and the named invalid/rejected statuses itself. No
    /// database write happens here and no partial result is invented.
    pub async fn run_deeptutor_question_turn(
        &self,
        frame: Vec<u8>,
        timeout: Duration,
        cancel: Cancellation,
    ) -> Result<Value, QuestionTurnWorkerError> {
        use QuestionTurnWorkerError as E;
        if frame.is_empty()
            || frame.len() > MAX_FRAME
            || frame.last() != Some(&b'\n')
            || frame[..frame.len() - 1].contains(&b'\n')
            || timeout.is_zero()
            || timeout > Duration::from_secs(120)
        {
            return Err(E::InvalidInput);
        }
        if cancel.is_cancelled() {
            return Err(E::Cancelled);
        }
        let worker = self.question_turn_worker().ok_or(E::Unavailable)?;
        let python = self.python.clone();
        if !derived::safe_local_file(&python) || !worker_matches(&worker) {
            return Err(E::IdentityMismatch);
        }
        let deadline = Instant::now() + timeout;
        let permit = loop {
            if cancel.is_cancelled() {
                return Err(E::Cancelled);
            }
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return Err(E::TimedOut);
            }
            match tokio::time::timeout(
                remaining.min(Duration::from_millis(25)),
                self.derived_slots.clone().acquire_owned(),
            )
            .await
            {
                Ok(Ok(permit)) => break permit,
                Ok(Err(_)) => return Err(E::Unavailable),
                Err(_) => continue,
            }
        };
        let staging = self.staging.clone();
        let task_cancel = cancel.clone();
        let task = tokio::task::spawn_blocking(move || {
            let _permit = permit;
            if task_cancel.is_cancelled() {
                return Err(E::Cancelled);
            }
            if Instant::now() >= deadline {
                return Err(E::TimedOut);
            }
            if !derived::safe_local_file(&python) || !worker_matches(&worker) {
                return Err(E::IdentityMismatch);
            }
            run_owned(&staging, &python, &worker, frame, deadline, &task_cancel)
        });
        match task.await {
            Ok(result) => result,
            Err(_) => Err(E::CleanupUnknown),
        }
    }
}

/// Own the direct child and bounded private pipes. The worker needs its
/// installed YAML reader, so the hardened `-S` launch used by the NDJSON routes
/// is deliberately not applied; every other isolation step matches them.
fn run_owned(
    staging: &Path,
    python: &Path,
    worker: &Path,
    frame: Vec<u8>,
    deadline: Instant,
    cancel: &Cancellation,
) -> Result<Value, QuestionTurnWorkerError> {
    use QuestionTurnWorkerError as E;
    if cancel.is_cancelled() {
        return Err(E::Cancelled);
    }
    if Instant::now() >= deadline {
        return Err(E::TimedOut);
    }
    let dir = tempfile::tempdir_in(staging).map_err(|_| E::Unavailable)?;
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
        .arg("-X")
        .arg("utf8")
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
    let mut child = OwnedChild(command.spawn().map_err(|_| E::Unavailable)?);
    let mut input = child.0.stdin.take().ok_or(E::CleanupUnknown)?;
    let mut output = child.0.stdout.take().ok_or(E::CleanupUnknown)?;
    let mut errors = child.0.stderr.take().ok_or(E::CleanupUnknown)?;
    let writer = thread::spawn(move || input.write_all(&frame).map_err(|_| ()));
    let reader = thread::spawn(move || {
        let mut value = Vec::new();
        output
            .by_ref()
            .take(MAX_REPLY + 1)
            .read_to_end(&mut value)
            .map(|_| value)
            .map_err(|_| ())
    });
    let err_reader = thread::spawn(move || {
        std::io::copy(
            &mut errors.by_ref().take(MAX_STDERR + 1),
            &mut std::io::sink(),
        )
        .map_err(|_| ())
    });
    let status = loop {
        if cancel.is_cancelled() {
            break Err(E::Cancelled);
        }
        if Instant::now() >= deadline {
            break Err(E::TimedOut);
        }
        match child.0.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(_) => break Err(E::CleanupUnknown),
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
        for (unfinished, handle) in [
            (!writer.is_finished(), writer.as_raw_handle()),
            (!reader.is_finished(), reader.as_raw_handle()),
            (!err_reader.is_finished(), err_reader.as_raw_handle()),
        ] {
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
    if !reaped || !writer.is_finished() || !reader.is_finished() || !err_reader.is_finished() {
        let _ = dir.keep();
        return Err(E::CleanupUnknown);
    }
    let wrote = match writer.join() {
        Ok(value) => value,
        Err(_) => {
            let _ = dir.keep();
            return Err(E::CleanupUnknown);
        }
    };
    let stdout = match reader.join() {
        Ok(value) => value,
        Err(_) => {
            let _ = dir.keep();
            return Err(E::CleanupUnknown);
        }
    };
    let stderr = match err_reader.join() {
        Ok(value) => value,
        Err(_) => {
            let _ = dir.keep();
            return Err(E::CleanupUnknown);
        }
    };
    let status = match status {
        Ok(status) => status,
        // Only the direct child is owned here. A forced stop cannot establish
        // the descendant state, so it stays a named unknown rather than a verdict.
        Err(E::Cancelled | E::TimedOut) => {
            let _ = dir.keep();
            return Err(E::CleanupUnknown);
        }
        Err(error) => {
            let _ = dir.keep();
            return Err(error);
        }
    };
    if dir.close().is_err() {
        return Err(E::CleanupUnknown);
    }
    let stdout = stdout.map_err(|_| E::Unavailable)?;
    let stderr_len = stderr.map_err(|_| E::Unavailable)?;
    if wrote.is_err() || stderr_len != 0 || stdout.len() > MAX_REPLY as usize {
        return Err(E::Unavailable);
    }
    if cancel.is_cancelled() {
        return Err(E::Cancelled);
    }
    let code = status.code().ok_or(E::Unavailable)?;
    if !matches!(code, 0 | 1 | 2) {
        return Err(E::Unavailable);
    }
    let document: Value = serde_json::from_slice(&stdout).map_err(|_| E::Unavailable)?;
    if !document.is_object() {
        return Err(E::Unavailable);
    }
    Ok(json!({"exit_code":code,"document":document}))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn the_question_worker_requires_an_explicit_private_route() {
        let dir = tempfile::tempdir().unwrap();
        let executor = Executor::open(
            &dir.path().join("workspace.sqlite"),
            &dir.path().join("staging"),
            &dir.path().join("unused-python"),
            &dir.path().join("unused-worker"),
        )
        .await
        .unwrap();
        assert_eq!(
            executor
                .run_deeptutor_question_turn(
                    b"{}\n".to_vec(),
                    Duration::from_secs(1),
                    Cancellation::new()
                )
                .await
                .unwrap_err(),
            QuestionTurnWorkerError::Unavailable
        );
    }
}
