//! Request-owned local-model transport. No provider service or shared process is stopped.
use super::*;
use std::future::Future;

const CANCELLED: &str = "local model request cancelled";
const TIMED_OUT: &str = "local model request timed out";
const CLEANUP_UNKNOWN: &str = "local model worker cleanup unknown";

pub(super) struct Lease {
    cancel: Cancellation,
    armed: bool,
}
impl Lease {
    pub(super) fn new(cancel: Cancellation) -> Self {
        Self {
            cancel,
            armed: true,
        }
    }
    pub(super) fn disarm(&mut self) {
        self.armed = false;
    }
}
impl Drop for Lease {
    fn drop(&mut self) {
        if self.armed {
            self.cancel.cancel();
        }
    }
}

pub(super) async fn join(
    mut task: tokio::task::JoinHandle<Result<Value, String>>,
    cancel: Option<Cancellation>,
    deadline: Instant,
) -> Result<Value, String> {
    let Some(cancel) = cancel else {
        return task.await.map_err(|_| "derived worker task failed")?;
    };
    loop {
        let stopped = if cancel.is_cancelled() {
            Some(CANCELLED)
        } else if Instant::now() >= deadline {
            Some(TIMED_OUT)
        } else {
            None
        };
        if let Some(reason) = stopped {
            cancel.cancel();
            // Abort only helps a blocking job still in the pool's queue. A running
            // job sees the token and must prove its own bounded cleanup below.
            task.abort();
            return match tokio::time::timeout(Duration::from_secs(3), &mut task).await {
                Ok(Ok(Err(error))) if error == CLEANUP_UNKNOWN => Err(error),
                Ok(Ok(_)) => Err(reason.into()),
                Ok(Err(error)) if error.is_cancelled() => Err(reason.into()),
                _ => Err(CLEANUP_UNKNOWN.into()),
            };
        }
        match tokio::time::timeout(Duration::from_millis(25), &mut task).await {
            Ok(Ok(result)) => {
                return if result.as_ref().is_err_and(|error| error == CLEANUP_UNKNOWN) {
                    result
                } else if cancel.is_cancelled() {
                    Err(CANCELLED.into())
                } else {
                    result
                };
            }
            Ok(Err(_)) => return Err(CLEANUP_UNKNOWN.into()),
            Err(_) => {}
        }
    }
}

pub(super) fn check(cancel: &Option<Cancellation>) -> Result<(), String> {
    if cancel.as_ref().is_some_and(Cancellation::is_cancelled) {
        Err(CANCELLED.into())
    } else {
        Ok(())
    }
}

/// Preserve the existing uncancellable entry points; only the new request lane polls its token.
pub(super) async fn wait<F: Future>(
    cancel: &Option<Cancellation>,
    deadline: Instant,
    future: F,
) -> Result<F::Output, String> {
    if cancel.is_none() {
        return Ok(future.await);
    }
    tokio::pin!(future);
    loop {
        check(cancel)?;
        if Instant::now() >= deadline {
            return Err(TIMED_OUT.into());
        }
        tokio::select! {
            value = &mut future => { check(cancel)?; return Ok(value); }
            _ = tokio::time::sleep(Duration::from_millis(25)) => {}
        }
    }
}

/// OwnedChild's final wait can block when the OS cannot confirm exit. Keep that
/// fallback off the request thread; callers report UNKNOWN, never successful cleanup.
struct ChildGuard(Option<OwnedChild>);
impl Drop for ChildGuard {
    fn drop(&mut self) {
        if let Some(child) = self.0.take() {
            thread::spawn(move || drop(child));
        }
    }
}

fn reader(
    stream: impl Read + Send + 'static,
    limit: usize,
    overflow: Arc<AtomicBool>,
) -> thread::JoinHandle<std::io::Result<Vec<u8>>> {
    thread::spawn(move || {
        let mut bytes = Vec::new();
        stream.take((limit + 1) as u64).read_to_end(&mut bytes)?;
        if bytes.len() > limit {
            overflow.store(true, Ordering::Relaxed);
        }
        Ok(bytes)
    })
}

#[cfg(windows)]
fn cancel_io<T>(task: &thread::JoinHandle<T>) {
    use std::os::windows::io::AsRawHandle;
    unsafe extern "system" {
        fn CancelSynchronousIo(thread: *mut std::ffi::c_void) -> i32;
        fn GetThreadId(thread: *mut std::ffi::c_void) -> u32;
        fn OpenThread(access: u32, inherit: i32, id: u32) -> *mut std::ffi::c_void;
        fn CloseHandle(handle: *mut std::ffi::c_void) -> i32;
    }
    if task.is_finished() {
        return;
    }
    // JoinHandle may lack THREAD_TERMINATE, which CancelSynchronousIo requires.
    // Open only this invocation's own pipe thread, never enumerate processes/threads.
    unsafe {
        let id = GetThreadId(task.as_raw_handle());
        if id != 0 {
            let handle = OpenThread(0x0001, 0, id);
            if !handle.is_null() {
                CancelSynchronousIo(handle);
                CloseHandle(handle);
            }
        }
    }
}

pub(super) fn run(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    input: Vec<u8>,
    deadline: Instant,
    cancel: &Cancellation,
) -> Result<Value, String> {
    if cancel.is_cancelled() {
        return Err(CANCELLED.into());
    }
    if Instant::now() >= deadline {
        return Err(TIMED_OUT.into());
    }
    let dir = tempfile::tempdir_in(staging).map_err(|_| "derived staging unavailable")?;
    let mut command = Command::new(python);
    command.env_clear();
    // Same operator-owned local-model environment as run_local_model; no request endpoint.
    for key in [
        "ARCHEAXIS_MACHINE_ENDPOINT",
        "ARCHEAXIS_MACHINE_MODEL",
        "ARCHEAXIS_MACHINE_PROTOCOL",
        "SystemRoot",
        "WINDIR",
        "SYSTEMDRIVE",
    ] {
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
    command.arg("-I").arg("-B").arg("-X").arg("utf8");
    if !site {
        command.arg("-S");
    }
    command
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
    if cancel.is_cancelled() {
        return Err(CANCELLED.into());
    }
    if Instant::now() >= deadline {
        return Err(TIMED_OUT.into());
    }
    let mut owner = ChildGuard(Some(OwnedChild(
        command.spawn().map_err(|_| "derived worker spawn failed")?,
    )));
    let child = &mut owner.0.as_mut().expect("owned child").0;
    let mut stdin = child.stdin.take().ok_or(CLEANUP_UNKNOWN)?;
    let stdout = child.stdout.take().ok_or(CLEANUP_UNKNOWN)?;
    let stderr = child.stderr.take().ok_or(CLEANUP_UNKNOWN)?;
    let writer = thread::spawn(move || stdin.write_all(&input));
    let overflow = Arc::new(AtomicBool::new(false));
    let output = reader(stdout, MAX_OUTPUT, overflow.clone());
    let errors = reader(stderr, MAX_ERROR, overflow.clone());
    let outcome = loop {
        if cancel.is_cancelled() {
            break Err(CANCELLED);
        }
        if Instant::now() >= deadline {
            break Err(TIMED_OUT);
        }
        if overflow.load(Ordering::Relaxed) {
            break Err("derived worker output exceeds bound");
        }
        match child.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(_) => break Err(CLEANUP_UNKNOWN),
        }
    };
    let mut reaped = matches!(child.try_wait(), Ok(Some(_)));
    if !reaped {
        let _ = child.kill();
        let reap_until = Instant::now() + Duration::from_secs(1);
        while Instant::now() < reap_until {
            match child.try_wait() {
                Ok(Some(_)) => {
                    reaped = true;
                    break;
                }
                Ok(None) => thread::sleep(Duration::from_millis(5)),
                Err(_) => break,
            }
        }
    }
    // A confirmed-exited child has a cached wait result, so its existing RAII cleanup is immediate.
    if reaped {
        drop(owner.0.take());
    }
    let drain_until = Instant::now() + Duration::from_secs(1);
    while !(writer.is_finished() && output.is_finished() && errors.is_finished())
        && Instant::now() < drain_until
    {
        thread::sleep(Duration::from_millis(5));
    }
    #[cfg(windows)]
    {
        cancel_io(&writer);
        cancel_io(&output);
        cancel_io(&errors);
    }
    let cancel_until = Instant::now() + Duration::from_millis(250);
    while !(writer.is_finished() && output.is_finished() && errors.is_finished())
        && Instant::now() < cancel_until
    {
        thread::sleep(Duration::from_millis(5));
    }
    if !reaped || !writer.is_finished() || !output.is_finished() || !errors.is_finished() {
        if writer.is_finished() {
            let _ = writer.join();
        }
        if output.is_finished() {
            let _ = output.join();
        }
        if errors.is_finished() {
            let _ = errors.join();
        }
        let _ = dir.keep();
        return Err(CLEANUP_UNKNOWN.into());
    }
    let written = writer.join();
    let out = output.join();
    let err = errors.join();
    if dir.close().is_err() {
        return Err(CLEANUP_UNKNOWN.into());
    }
    if cancel.is_cancelled() {
        return Err(CANCELLED.into());
    }
    let status = outcome?;
    written
        .map_err(|_| "derived stdin task failed")?
        .map_err(|_| "derived stdin write failed")?;
    let out = out
        .map_err(|_| "derived stdout task failed")?
        .map_err(|_| "derived stdout read failed")?;
    let err = err
        .map_err(|_| "derived stderr task failed")?
        .map_err(|_| "derived stderr read failed")?;
    if out.len() > MAX_OUTPUT || err.len() > MAX_ERROR {
        return Err("derived worker output exceeds bound".into());
    }
    let document: Value =
        serde_json::from_slice(&out).map_err(|_| "derived worker returned invalid JSON")?;
    if !document.is_object() {
        return Err("derived worker returned non-object JSON".into());
    }
    let exit_code = status
        .code()
        .ok_or("derived worker terminated without exit code")?;
    if !matches!(exit_code, 0 | 2) {
        return Err("derived worker failed with unexpected exit code".into());
    }
    Ok(json!({"exit_code":exit_code,"document":document}))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn completed_cleanup_unknown_survives_cancellation() {
        let cancel = Cancellation::new();
        let worker_cancel = cancel.clone();
        let worker = tokio::spawn(async move {
            // The current-thread test enters join's pending wait before this
            // simulated owned cleanup reports both cancellation and unknown.
            tokio::task::yield_now().await;
            worker_cancel.cancel();
            Err(CLEANUP_UNKNOWN.to_owned())
        });
        let result = join(
            worker,
            Some(cancel),
            Instant::now() + Duration::from_secs(1),
        )
        .await;
        assert_eq!(result.unwrap_err(), CLEANUP_UNKNOWN);
    }

    #[test]
    fn queued_abort_remains_unknown_until_pool_can_observe_cleanup() {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .max_blocking_threads(1)
            .build()
            .unwrap();
        runtime.block_on(async {
            let (release, held) = std::sync::mpsc::channel();
            struct Release(Option<std::sync::mpsc::Sender<()>>);
            impl Drop for Release {
                fn drop(&mut self) {
                    if let Some(sender) = self.0.take() {
                        let _ = sender.send(());
                    }
                }
            }
            let release = Release(Some(release));
            let (started, entered) = tokio::sync::oneshot::channel();
            let blocker = tokio::task::spawn_blocking(move || {
                let _ = started.send(());
                let _ = held.recv_timeout(Duration::from_secs(10));
            });
            entered.await.unwrap();
            let ran = Arc::new(AtomicBool::new(false));
            let observed = ran.clone();
            // spawn_blocking synchronously enqueues this task while the only
            // pool thread is observably held; no admission timing is assumed.
            let queued = tokio::task::spawn_blocking(move || {
                observed.store(true, Ordering::SeqCst);
                Ok(json!({}))
            });
            let cancel = Cancellation::new();
            cancel.cancel();
            let at = Instant::now();
            let result = tokio::time::timeout(
                Duration::from_secs(4),
                join(queued, Some(cancel), at + Duration::from_secs(30)),
            )
            .await
            .unwrap();
            assert_eq!(result.unwrap_err(), CLEANUP_UNKNOWN);
            assert!(at.elapsed() >= Duration::from_secs(3));
            assert!(at.elapsed() < Duration::from_secs(4));
            assert!(!blocker.is_finished());
            assert!(!ran.load(Ordering::SeqCst));
            drop(release);
            blocker.await.unwrap();
            tokio::task::spawn_blocking(|| ()).await.unwrap();
            assert!(!ran.load(Ordering::SeqCst));
        });
    }
}
