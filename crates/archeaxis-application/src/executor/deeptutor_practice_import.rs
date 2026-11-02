//! Private DeepTutor practice import process. This is not a generic job route.
//! Input and output can contain answers and must never enter job logs.
use super::*;
use sha2::{Digest, Sha256};
use std::sync::atomic::AtomicU8;

const WORKER_NAME: &str = "practice_host_worker.py";
const WORKER_SIZE: u64 = 11_888;
const WORKER_SHA: &str = "af186a32b2a98c248f28b447edbf9fb27399c1873fa93bd29bcda557a173b6d1";
const MAX_FRAME: usize = 7_056_044;
const MAX_REPLY: u64 = 1_114_112;
const MAX_STDERR: u64 = 8_192;
const PREPARED: u8 = 0;
const DISPATCHED: u8 = 1;
const CANCELLED: u8 = 2;
const COMMITTING: u8 = 3;

/// A request-local linearization point. Cancellation wins if it happens before
/// dispatch or commit admission. Once dispatch wins, bytes may already be sent;
/// once commit wins, a disconnect can leave the caller with an unknown result.
#[derive(Clone, Default)]
pub struct PracticeImportCancellation(Arc<AtomicU8>);
impl PracticeImportCancellation {
    pub fn new() -> Self { Self::default() }
    pub fn cancel(&self) { self.0.store(CANCELLED, Ordering::SeqCst); }
    pub fn is_cancelled(&self) -> bool { self.0.load(Ordering::SeqCst) == CANCELLED }
    fn begin_dispatch(&self) -> bool {
        self.0.compare_exchange(PREPARED, DISPATCHED, Ordering::SeqCst, Ordering::SeqCst).is_ok()
    }
    pub fn begin_commit(&self) -> bool {
        self.0.compare_exchange(DISPATCHED, COMMITTING, Ordering::SeqCst, Ordering::SeqCst).is_ok()
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum PracticeImportWorkerError {
    InvalidInput,
    Unavailable,
    IdentityMismatch,
    Rejected,
    Cancelled,
    TimedOut,
    CleanupUnknown,
}

fn fixed_worker_matches(path: &Path) -> bool {
    if path.file_name().and_then(|value| value.to_str()) != Some(WORKER_NAME)
        || !derived::safe_local_file(path)
    {
        return false;
    }
    let Ok(mut file) = std::fs::File::open(path) else { return false; };
    let Ok(before) = file.metadata() else { return false; };
    if !before.is_file() || before.len() != WORKER_SIZE { return false; }
    let mut bytes = Vec::with_capacity((WORKER_SIZE + 1) as usize);
    if (&mut file).take(WORKER_SIZE + 1).read_to_end(&mut bytes).is_err() { return false; }
    let Ok(after) = file.metadata() else { return false; };
    bytes.len() as u64 == WORKER_SIZE && after.len() == before.len()
        && after.modified().ok() == before.modified().ok()
        && hex::encode(Sha256::digest(&bytes)) == WORKER_SHA
}

struct CancelOnDrop(Option<PracticeImportCancellation>);
impl Drop for CancelOnDrop {
    fn drop(&mut self) { if let Some(cancel) = &self.0 { cancel.cancel(); } }
}

impl Executor {
    /// Run the launch-declared, fixed private worker. The caller owns result
    /// admission and must recheck cancellation and Core bindings before writes.
    pub async fn run_deeptutor_practice_import(
        &self, frame: Vec<u8>, timeout: Duration, cancel: PracticeImportCancellation,
    ) -> Result<Vec<u8>, PracticeImportWorkerError> {
        if frame.is_empty() || frame.len() > MAX_FRAME || frame.last() != Some(&b'\n')
            || frame[..frame.len() - 1].contains(&b'\n') || timeout.is_zero()
            || timeout > Duration::from_secs(120)
        { return Err(PracticeImportWorkerError::InvalidInput); }
        if self.deeptutor_practice_unknown.load(Ordering::SeqCst) {
            return Err(PracticeImportWorkerError::CleanupUnknown);
        }
        if cancel.is_cancelled() { return Err(PracticeImportWorkerError::Cancelled); }
        let worker = self.deeptutor_practice_worker.clone().ok_or(PracticeImportWorkerError::Unavailable)?;
        let python = self.python.clone();
        if !derived::safe_local_file(&python) || !fixed_worker_matches(&worker) {
            return Err(PracticeImportWorkerError::IdentityMismatch);
        }
        let deadline = Instant::now() + timeout;
        let permit = loop {
            if cancel.is_cancelled() { return Err(PracticeImportWorkerError::Cancelled); }
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() { return Err(PracticeImportWorkerError::TimedOut); }
            match tokio::time::timeout(remaining.min(Duration::from_millis(25)), self.derived_slots.clone().acquire_owned()).await {
                Ok(Ok(permit)) => break permit,
                Ok(Err(_)) => return Err(PracticeImportWorkerError::Unavailable),
                Err(_) => continue,
            }
        };
        let staging = self.staging.clone();
        let task_cancel = cancel.clone();
        let unknown = self.deeptutor_practice_unknown.clone();
        let mut cancel_on_drop = CancelOnDrop(Some(cancel));
        let task = tokio::task::spawn_blocking(move || {
            let _permit = permit;
            if unknown.load(Ordering::SeqCst) { return Err(PracticeImportWorkerError::CleanupUnknown); }
            if task_cancel.is_cancelled() { return Err(PracticeImportWorkerError::Cancelled); }
            if Instant::now() >= deadline { return Err(PracticeImportWorkerError::TimedOut); }
            if !derived::safe_local_file(&python) || !fixed_worker_matches(&worker) {
                return Err(PracticeImportWorkerError::IdentityMismatch);
            }
            let result = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                run_owned(&staging, &python, &worker, frame, deadline, &task_cancel)
            })) {
                Ok(result) => result,
                Err(_) => Err(PracticeImportWorkerError::CleanupUnknown),
            };
            if matches!(&result, Err(PracticeImportWorkerError::CleanupUnknown)) {
                unknown.store(true, Ordering::SeqCst);
            }
            result
        });
        let result = match task.await {
            Ok(result) => result,
            Err(_) => {
                self.deeptutor_practice_unknown.store(true, Ordering::SeqCst);
                return Err(PracticeImportWorkerError::CleanupUnknown);
            }
        };
        cancel_on_drop.0 = None;
        result
    }
}

/// Own the direct child and bounded private pipes. A forced stop is UNKNOWN;
/// successful direct-child cleanup does not certify the state of descendants.
fn run_owned(staging: &Path, python: &Path, worker: &Path, frame: Vec<u8>,
    deadline: Instant, cancel: &PracticeImportCancellation) -> Result<Vec<u8>, PracticeImportWorkerError> {
    use PracticeImportWorkerError as E;
    if cancel.is_cancelled() { return Err(E::Cancelled); }
    if Instant::now() >= deadline { return Err(E::TimedOut); }
    let dir = tempfile::tempdir_in(staging).map_err(|_| E::Unavailable)?;
    let mut command = Command::new(python);
    command.env_clear();
    for key in ["SystemRoot", "WINDIR", "SYSTEMDRIVE"] {
        if let Some(value) = std::env::var_os(key) { command.env(key, value); }
    }
    for key in ["TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"] {
        command.env(key, dir.path());
    }
    command.arg("-I").arg("-B").arg("-S").arg(worker).current_dir(dir.path())
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    if Instant::now() >= deadline { return Err(E::TimedOut); }
    if !cancel.begin_dispatch() { return Err(E::Cancelled); }
    let mut child = OwnedChild(command.spawn().map_err(|_| E::Unavailable)?);
    let mut input = child.0.stdin.take().ok_or(E::CleanupUnknown)?;
    let mut output = child.0.stdout.take().ok_or(E::CleanupUnknown)?;
    let mut errors = child.0.stderr.take().ok_or(E::CleanupUnknown)?;
    let writer = thread::spawn(move || input.write_all(&frame).map_err(|_| ()));
    let reader = thread::spawn(move || {
        let mut value = Vec::new();
        output.by_ref().take(MAX_REPLY + 1).read_to_end(&mut value).map(|_| value).map_err(|_| ())
    });
    let err_reader = thread::spawn(move || {
        std::io::copy(&mut errors.by_ref().take(MAX_STDERR + 1), &mut std::io::sink()).map_err(|_| ())
    });
    let result = loop {
        if cancel.is_cancelled() { break Err(E::Cancelled); }
        if Instant::now() >= deadline { break Err(E::TimedOut); }
        match child.0.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(_) => break Err(E::CleanupUnknown),
        }
    };
    if !matches!(child.0.try_wait(), Ok(Some(_))) { let _ = child.0.kill(); }
    let reap_deadline = Instant::now() + Duration::from_secs(1);
    let reaped = loop {
        match child.0.try_wait() {
            Ok(Some(_)) => break true,
            Ok(None) if Instant::now() < reap_deadline => thread::sleep(Duration::from_millis(5)),
            _ => break false,
        }
    };
    if reaped { drop(child); } else { thread::spawn(move || drop(child)); }
    let drain_deadline = Instant::now() + Duration::from_millis(500);
    while (!writer.is_finished() || !reader.is_finished() || !err_reader.is_finished()) && Instant::now() < drain_deadline {
        thread::sleep(Duration::from_millis(5));
    }
    #[cfg(windows)]
    {
        use std::os::windows::io::AsRawHandle;
        #[link(name = "kernel32")]
        unsafe extern "system" { fn CancelSynchronousIo(thread: *mut std::ffi::c_void) -> i32; }
        for (unfinished, handle) in [(!writer.is_finished(), writer.as_raw_handle()),
            (!reader.is_finished(), reader.as_raw_handle()), (!err_reader.is_finished(), err_reader.as_raw_handle())] {
            if unfinished { unsafe { CancelSynchronousIo(handle); } }
        }
    }
    let cleanup_deadline = Instant::now() + Duration::from_millis(500);
    while (!writer.is_finished() || !reader.is_finished() || !err_reader.is_finished()) && Instant::now() < cleanup_deadline {
        thread::sleep(Duration::from_millis(5));
    }
    if !reaped || !writer.is_finished() || !reader.is_finished() || !err_reader.is_finished() {
        let _ = dir.keep();
        return Err(E::CleanupUnknown);
    }
    let wrote = match writer.join() {
        Ok(value) => value,
        Err(_) => { let _ = dir.keep(); return Err(E::CleanupUnknown); }
    };
    let stdout = match reader.join() {
        Ok(value) => value,
        Err(_) => { let _ = dir.keep(); return Err(E::CleanupUnknown); }
    };
    let stderr = match err_reader.join() {
        Ok(value) => value,
        Err(_) => { let _ = dir.keep(); return Err(E::CleanupUnknown); }
    };
    let status = match result {
        Ok(status) => status,
        // Only the direct child is owned here. After a forced stop the
        // descendant state cannot be established by this runner.
        Err(E::Cancelled | E::TimedOut) => { let _ = dir.keep(); return Err(E::CleanupUnknown); }
        Err(error) => { let _ = dir.keep(); return Err(error); }
    };
    if dir.close().is_err() { return Err(E::CleanupUnknown); }
    let stdout = stdout.map_err(|_| E::Unavailable)?;
    let stderr_len = stderr.map_err(|_| E::Unavailable)?;
    if wrote.is_err() || stderr_len != 0 || stdout.len() > MAX_REPLY as usize {
        return Err(E::Unavailable);
    }
    if !status.success() { return Err(E::Rejected); }
    if cancel.is_cancelled() { return Err(E::Cancelled); }
    Ok(stdout)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cancellation_wins_before_dispatch_or_before_commit() {
        let before_dispatch = PracticeImportCancellation::new();
        before_dispatch.cancel();
        assert!(!before_dispatch.begin_dispatch());
        assert!(!before_dispatch.begin_commit());

        let after_dispatch = PracticeImportCancellation::new();
        assert!(after_dispatch.begin_dispatch());
        after_dispatch.cancel();
        assert!(!after_dispatch.begin_commit());

        let admitted_commit = PracticeImportCancellation::new();
        assert!(admitted_commit.begin_dispatch());
        assert!(admitted_commit.begin_commit());
        admitted_commit.cancel();
        assert!(!admitted_commit.begin_commit());
    }

    #[tokio::test]
    async fn private_protocol_requires_an_explicit_worker_and_bounded_frame() {
        let dir = tempfile::tempdir().unwrap();
        let executor = Executor::open(&dir.path().join("workspace.sqlite"), &dir.path().join("staging"),
            &dir.path().join("unused-python"), &dir.path().join("unused-worker")).await.unwrap();
        assert_eq!(executor.run_deeptutor_practice_import(b"{}\n".to_vec(), Duration::from_secs(1),
            PracticeImportCancellation::new()).await.unwrap_err(), PracticeImportWorkerError::Unavailable);
        assert_eq!(executor.run_deeptutor_practice_import(vec![b'x'; MAX_FRAME + 1], Duration::from_secs(1),
            PracticeImportCancellation::new()).await.unwrap_err(), PracticeImportWorkerError::InvalidInput);
        executor.deeptutor_practice_unknown.store(true, Ordering::SeqCst);
        assert_eq!(executor.run_deeptutor_practice_import(b"{}\n".to_vec(), Duration::from_secs(1),
            PracticeImportCancellation::new()).await.unwrap_err(), PracticeImportWorkerError::CleanupUnknown);
    }
}
