//! Public research is a fixed, launch-owned JSON worker, never a caller executable.
use super::*;
use serde_json::Value;
use std::io::Seek;

const MAX_INPUT: usize = 16 * 1024;
const MAX_OUTPUT: usize = 1024 * 1024;
const POLL: Duration = Duration::from_millis(5);
pub(super) const HELLO_SCHEMA: &str = "archeaxis.public-research-worker-hello/v1";

enum Mode {
    Query(Vec<u8>),
    Hello,
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct Hello {
    schema: String,
    version: u64,
    worker: String,
    capability: String,
    protocol: String,
    task_executed: bool,
    network_performed: bool,
    model_executed: bool,
}

pub(super) fn health(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
) -> Result<Value, String> {
    let value = run_mode(
        staging,
        python,
        worker,
        site,
        Mode::Hello,
        &Cancellation::new(),
        Instant::now() + Duration::from_secs(2),
    )?;
    let hello: Hello =
        serde_json::from_value(value).map_err(|_| "public_research_invalid_hello")?;
    if hello.schema != HELLO_SCHEMA
        || hello.version != 1
        || hello.worker != "python-worker-machine-answer-ndjson"
        || hello.capability != "research.public"
        || hello.protocol != "public-research-worker/v1"
        || hello.task_executed
        || hello.network_performed
        || hello.model_executed
    {
        return Err("public_research_invalid_hello".into());
    }
    Ok(serde_json::json!({"worker_identity":hello.worker,"runtime_dependency":null}))
}

fn guard(cancel: &Cancellation, deadline: Instant) -> Result<(), String> {
    if cancel.is_cancelled() {
        return Err("public_research_cancelled".into());
    }
    if Instant::now() >= deadline {
        return Err("public_research_timeout".into());
    }
    Ok(())
}

async fn cancelled(cancel: &Cancellation) {
    while !cancel.is_cancelled() {
        tokio::time::sleep(POLL).await;
    }
}

impl Executor {
    pub async fn public_research(
        &self,
        request: Value,
        cancel: Cancellation,
    ) -> Result<Value, String> {
        self.public_research_until(request, cancel, Instant::now() + Duration::from_secs(90))
            .await
    }

    async fn public_research_until(
        &self,
        request: Value,
        cancel: Cancellation,
        deadline: Instant,
    ) -> Result<Value, String> {
        guard(&cancel, deadline)?;
        // A bounded serializer avoids allocating an arbitrarily large second copy.
        struct Input(Vec<u8>);
        impl Write for Input {
            fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
                if bytes.len() > MAX_INPUT.saturating_sub(self.0.len()) {
                    return Err(std::io::Error::other("input bound"));
                }
                self.0.extend_from_slice(bytes);
                Ok(bytes.len())
            }
            fn flush(&mut self) -> std::io::Result<()> {
                Ok(())
            }
        }
        let mut input = Input(Vec::new());
        serde_json::to_writer(&mut input, &request)
            .map_err(|_| "public_research_input_exceeds_bound")?;
        self.research_enabled(&cancel, deadline).await?;
        let permit = tokio::select! {
            biased;
            _ = cancelled(&cancel) => return Err("public_research_cancelled".into()),
            result = tokio::time::timeout(deadline.saturating_duration_since(Instant::now()),self.derived_slots.clone().acquire_owned()) => result
                .map_err(|_| "public_research_timeout")?
                .map_err(|_| "public_research_unavailable")?,
        };
        // Recheck after admission: a queued request must not bypass withdrawal.
        self.research_enabled(&cancel, deadline).await?;
        let (worker, site) = self
            .worker_for("research.public")
            .ok_or("public_research_unregistered")?;
        let python = self.python.clone();
        let staging = self.staging.clone();
        let owned_cancel = Cancellation::new();
        struct StopOnDrop {
            cancel: Cancellation,
            state: Arc<std::sync::atomic::AtomicU8>,
            permit: Arc<std::sync::Mutex<Option<tokio::sync::OwnedSemaphorePermit>>>,
        }
        impl StopOnDrop {
            fn withdraw(&self) -> bool {
                self.cancel.cancel();
                let queued = self
                    .state
                    .compare_exchange(0, 2, Ordering::AcqRel, Ordering::Acquire)
                    .is_ok();
                if queued {
                    if let Ok(mut permit) = self.permit.lock() {
                        permit.take();
                    }
                }
                queued
            }
        }
        impl Drop for StopOnDrop {
            fn drop(&mut self) {
                self.withdraw();
            }
        }
        // Dropping an API future also withdraws its owned worker. A separate
        // token keeps deadline cleanup from changing the caller's cancellation.
        let state = Arc::new(std::sync::atomic::AtomicU8::new(0));
        let permit = Arc::new(std::sync::Mutex::new(Some(permit)));
        let stop = StopOnDrop {
            cancel: owned_cancel.clone(),
            state: state.clone(),
            permit: permit.clone(),
        };
        let launch_executor = self.clone();
        let runtime = tokio::runtime::Handle::current();
        let mut task = tokio::task::spawn_blocking(move || {
            // Exactly one side wins queued -> started/cancelled. A cancelled
            // queued closure has no child, pipe, or per-call thread to await.
            state
                .compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire)
                .map_err(|_| "public_research_cancelled")?;
            let _permit = permit
                .lock()
                .map_err(|_| "public_research_unavailable")?
                .take()
                .ok_or("public_research_unavailable")?;
            // The blocking pool may itself queue after slot admission.
            runtime.block_on(launch_executor.research_enabled(&owned_cancel, deadline))?;
            run(
                &staging,
                &python,
                &worker,
                site,
                input.0,
                &owned_cancel,
                deadline,
            )
        });
        let failure = tokio::select! {
            biased;
            _=cancelled(&cancel)=>"public_research_cancelled",
            _=tokio::time::sleep(deadline.saturating_duration_since(Instant::now()))=>"public_research_timeout",
            result=&mut task=>{
                let value=result.map_err(|_|"public_research_task_failed")??;
                // No candidate is returned after cancellation, expiry or disable.
                self.research_enabled(&cancel,deadline).await?;
                guard(&cancel,deadline)?;
                return Ok(value);
            }
        };
        // If the blocking pool itself is queued, abort prevents a later start;
        // if already running, cancellation is observed before owned cleanup.
        let queued = stop.withdraw();
        task.abort();
        if queued {
            return Err(failure.into());
        }
        withdrawal_result(failure, task.await)
    }

    async fn research_enabled(
        &self,
        cancel: &Cancellation,
        deadline: Instant,
    ) -> Result<(), String> {
        guard(cancel, deadline)?;
        let enabled = tokio::select! {
            biased;
            _ = cancelled(cancel) => return Err("public_research_cancelled".into()),
            result = tokio::time::timeout(deadline.saturating_duration_since(Instant::now()),self.store.submit_wait(|conn| capability_settings::is_enabled(conn,"research.public"))) => result
                .map_err(|_| "public_research_timeout")?
                .map_err(|_| "public_research_settings_unavailable")?
                .map_err(|_| "public_research_settings_unavailable")?,
        };
        guard(cancel, deadline)?;
        if !enabled {
            return Err("public_research_disabled".into());
        }
        Ok(())
    }
}

fn withdrawal_result(
    reason: &str,
    result: Result<Result<Value, String>, tokio::task::JoinError>,
) -> Result<Value, String> {
    match result {
        Err(_) => Err("public_research_task_failed".into()),
        Ok(Err(error))
            if matches!(
                error.as_str(),
                "public_research_cleanup_failed" | "public_research_task_failed"
            ) =>
        {
            Err(error)
        }
        _ => Err(reason.into()),
    }
}

fn cleanup_staging(
    input: Option<tempfile::NamedTempFile>,
    directory: tempfile::TempDir,
) -> Result<(), String> {
    let file = input.as_ref().map(|input| input.path().to_owned());
    drop(input);
    // No recursive removal: only this exact newly allocated file/directory.
    let directory = directory.keep();
    let end = Instant::now() + Duration::from_millis(500);
    loop {
        let removed = |result: std::io::Result<()>| match result {
            Ok(()) => true,
            Err(e) => e.kind() == std::io::ErrorKind::NotFound,
        };
        let absent = |path: &Path| matches!(std::fs::symlink_metadata(path),Err(e) if e.kind()==std::io::ErrorKind::NotFound);
        let file_removed = file
            .as_ref()
            .is_none_or(|file| removed(std::fs::remove_file(file)) && absent(file));
        let directory_removed = removed(std::fs::remove_dir(&directory)) && absent(&directory);
        if file_removed && directory_removed {
            return Ok(());
        }
        if Instant::now() >= end {
            return Err("public_research_cleanup_failed".into());
        }
        thread::sleep(POLL);
    }
}

fn run(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    input: Vec<u8>,
    cancel: &Cancellation,
    deadline: Instant,
) -> Result<Value, String> {
    run_mode(
        staging,
        python,
        worker,
        site,
        Mode::Query(input),
        cancel,
        deadline,
    )
}

fn run_mode(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    mode: Mode,
    cancel: &Cancellation,
    deadline: Instant,
) -> Result<Value, String> {
    guard(cancel, deadline)?;
    let hello = matches!(mode, Mode::Hello);
    let output_limit = if hello { 4096 } else { MAX_OUTPUT };
    let dir = tempfile::tempdir_in(staging).map_err(|_| "public_research_staging_unavailable")?;
    // An auto-cleaned file supplies bounded JSON stdin without a
    // writer thread that could block behind a worker/descendant retaining stdin.
    // Keep the temporary file in the controlled staging root: a descendant may
    // retain stdin after our worker exits, and must not prevent removal of our
    // per-call directory. Explicit bounded cleanup reports retained handles.
    let stdin = if let Mode::Query(input) = mode {
        let mut file = tempfile::NamedTempFile::new_in(staging)
            .map_err(|_| "public_research_input_unavailable")?;
        file.write_all(&input)
            .map_err(|_| "public_research_input_unavailable")?;
        file.rewind()
            .map_err(|_| "public_research_input_unavailable")?;
        Some(file)
    } else {
        None
    };
    let mut command = Command::new(python);
    command.env_clear();
    // The optional route is a launch-owned public-only numeric-loopback proxy.
    // Invalid/empty values are deliberately forwarded for worker fail-closed
    // validation; never infer a route or inherit generic proxy/auth variables.
    if let Some(route) = std::env::var_os("ARCHEAXIS_PUBLIC_RESEARCH_PROXY").filter(|_| !hello) {
        command.env("ARCHEAXIS_PUBLIC_RESEARCH_PROXY", route);
    }
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
    command.arg("-I").arg("-B").arg("-X").arg("utf8");
    if !site {
        command.arg("-S");
    }
    command
        .arg(worker)
        .arg(if hello {
            "--public-research-hello"
        } else {
            "--public-research"
        })
        // Windows descendants can retain cwd after the owned redirector exits.
        // Keep cwd at the controlled staging root; HOME/TEMP remain per-call.
        .current_dir(staging)
        .stdin(match stdin.as_ref() {
            Some(file) => Stdio::from(
                file.reopen()
                    .map_err(|_| "public_research_input_unavailable")?,
            ),
            None => Stdio::null(),
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    guard(cancel, deadline)?;
    let mut child = OwnedChild(
        command
            .spawn()
            .map_err(|_| "public_research_worker_start_failed")?,
    );
    // Readers run here, so none can outlive this owned execution task.
    let result = (|| -> Result<Value, String> {
        let mut stdout = child
            .0
            .stdout
            .take()
            .ok_or("public_research_pipe_unavailable")?;
        let mut stderr = child
            .0
            .stderr
            .take()
            .ok_or("public_research_pipe_unavailable")?;
        #[cfg(unix)]
        {
            nonblocking(&stdout)?;
            nonblocking(&stderr)?;
        }
        // Readers run in this owned task using readiness/nonblocking reads. No reader
        // thread can outlive it, even if a descendant retains an inherited pipe.
        let mut output = Vec::new();
        let mut output_eof = false;
        let mut error_eof = false;
        let mut status = None;
        let mut drain_deadline = None;
        loop {
            guard(cancel, deadline)?;
            let mut buffer = [0_u8; 8192];
            for _ in 0..8 {
                if output_eof {
                    break;
                }
                match read_available(&mut stdout, &mut buffer)
                    .map_err(|_| "public_research_read_failed")?
                {
                    Some(0) => {
                        output_eof = true;
                        break;
                    }
                    Some(n) => {
                        if n > output_limit.saturating_sub(output.len()) {
                            return Err("public_research_output_exceeds_bound".into());
                        }
                        output.extend_from_slice(&buffer[..n]);
                    }
                    None => break,
                }
            }
            for _ in 0..8 {
                if error_eof {
                    break;
                }
                match read_available(&mut stderr, &mut buffer)
                    .map_err(|_| "public_research_read_failed")?
                {
                    Some(0) => {
                        error_eof = true;
                        break;
                    }
                    Some(_) => {} // Drain only: stderr never becomes an error body or log.
                    None => break,
                }
            }
            if status.is_none() {
                status = child
                    .0
                    .try_wait()
                    .map_err(|_| "public_research_wait_failed")?;
            }
            if let Some(status) = status {
                if output_eof && error_eof {
                    if !(status.code() == Some(0) || (!hello && status.code() == Some(2))) {
                        return Err("public_research_worker_exit_failed".into());
                    }
                    return serde_json::from_slice(&output)
                        .map_err(|_| "public_research_invalid_json".into());
                }
                let end =
                    *drain_deadline.get_or_insert_with(|| Instant::now() + Duration::from_secs(1));
                if Instant::now() >= end {
                    return Err("public_research_pipe_incomplete".into());
                }
            }
            thread::sleep(POLL.min(deadline.saturating_duration_since(Instant::now())));
        }
    })();
    let cleanup = match child.0.try_wait() {
        Ok(Some(_)) => Ok(()),
        _ => {
            let _ = child.0.kill();
            child
                .0
                .wait()
                .map(|_| ())
                .map_err(|_| "public_research_cleanup_failed")
        }
    };
    drop(child);
    drop(command);
    let staging_cleanup = cleanup_staging(stdin, dir);
    cleanup?;
    staging_cleanup?;
    let value = result?;
    guard(cancel, deadline)?;
    Ok(value)
}

#[cfg(windows)]
fn read_available<R: Read + std::os::windows::io::AsRawHandle>(
    pipe: &mut R,
    bytes: &mut [u8],
) -> std::io::Result<Option<usize>> {
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn PeekNamedPipe(
            pipe: *mut std::ffi::c_void,
            buffer: *mut std::ffi::c_void,
            size: u32,
            read: *mut u32,
            available: *mut u32,
            left: *mut u32,
        ) -> i32;
    }
    let mut available = 0;
    let ok = unsafe {
        PeekNamedPipe(
            pipe.as_raw_handle(),
            std::ptr::null_mut(),
            0,
            std::ptr::null_mut(),
            &mut available,
            std::ptr::null_mut(),
        )
    };
    if ok == 0 {
        let error = std::io::Error::last_os_error();
        if matches!(error.raw_os_error(), Some(109 | 233)) {
            return Ok(Some(0));
        }
        return Err(error);
    }
    if available == 0 {
        return Ok(None);
    }
    let length = bytes.len().min(available as usize);
    pipe.read(&mut bytes[..length]).map(Some)
}

#[cfg(unix)]
fn read_available<R: Read>(pipe: &mut R, bytes: &mut [u8]) -> std::io::Result<Option<usize>> {
    match pipe.read(bytes) {
        Ok(n) => Ok(Some(n)),
        Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => Ok(None),
        Err(e) => Err(e),
    }
}

#[cfg(unix)]
fn nonblocking(pipe: &impl std::os::fd::AsRawFd) -> Result<(), String> {
    unsafe extern "C" {
        fn fcntl(fd: i32, command: i32, ...) -> i32;
    }
    #[cfg(target_os = "linux")]
    const NONBLOCK: i32 = 0x800;
    #[cfg(not(target_os = "linux"))]
    const NONBLOCK: i32 = 0x4;
    let fd = pipe.as_raw_fd();
    let flags = unsafe { fcntl(fd, 3) };
    if flags < 0 || unsafe { fcntl(fd, 4, flags | NONBLOCK) } < 0 {
        return Err("public_research_pipe_unavailable".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    async fn fixture(script: &str) -> (tempfile::TempDir, Executor) {
        let dir = tempfile::tempdir().unwrap();
        let worker = dir.path().join("research.py");
        std::fs::write(&worker, script).unwrap();
        let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON")
            .expect("canonical Python required")
            .into();
        let ex = Executor::open_routes(
            &dir.path().join("db"),
            &dir.path().join("staging"),
            &python,
            &worker,
            &[("research.public", worker.clone())],
        )
        .await
        .unwrap();
        (dir, ex)
    }

    async fn wait_for(path: &Path) {
        let end = Instant::now() + Duration::from_secs(4);
        while !path.exists() {
            assert!(Instant::now() < end, "fixture did not start");
            tokio::time::sleep(Duration::from_millis(5)).await;
        }
    }

    async fn set_enabled(ex: &Executor, enabled: bool) {
        ex.store
            .submit_wait(move |conn| {
                capability_settings::set_enabled(conn, "research.public", enabled)
            })
            .await
            .unwrap()
            .unwrap();
    }

    const ECHO: &str = "import json,sys,os\nassert sys.argv[1:]==['--public-research']\nassert not any((k.lower().endswith('proxy') and k!='ARCHEAXIS_PUBLIC_RESEARCH_PROXY') or k in ('PYTHONPATH','OPENAI_API_KEY') for k in os.environ)\nprint(json.dumps(json.load(sys.stdin)))\n";
    const HANG: &str = "import os,time\nfrom pathlib import Path\nPath(__file__).with_suffix('.pid').write_text(str(os.getpid()))\ntime.sleep(5)\nPath(__file__).with_suffix('.late').touch()\nprint('{}')\n";

    #[tokio::test]
    async fn fixed_worker_json_and_safe_input_bound() {
        let (_dir, ex) = fixture(ECHO).await;
        let request =
            json!({"query":"synthetic","url":"ignored execution selector","executable":"ignored"});
        assert_eq!(
            ex.public_research(request.clone(), Cancellation::new())
                .await
                .unwrap(),
            request
        );
        // {"x":""} is eight UTF-8 bytes; no unbudgeted framing byte is appended.
        let exact = json!({"x":"x".repeat(16384-8)});
        assert_eq!(serde_json::to_vec(&exact).unwrap().len(), 16384);
        assert_eq!(
            ex.public_research(exact.clone(), Cancellation::new())
                .await
                .unwrap(),
            exact
        );
        assert_eq!(
            ex.public_research(json!({"query":"x".repeat(16384)}), Cancellation::new())
                .await
                .unwrap_err(),
            "public_research_input_exceeds_bound"
        );
    }

    #[tokio::test]
    async fn invalid_json_and_unexpected_exit_are_safe_failures() {
        let (dir,ex)=fixture("import sys\nsys.stderr.write('private synthetic query')\nprint('private invalid JSON')\n").await;
        assert_eq!(
            ex.public_research(json!({}), Cancellation::new())
                .await
                .unwrap_err(),
            "public_research_invalid_json"
        );
        std::fs::write(
            dir.path().join("research.py"),
            "print('{}')\nraise SystemExit(3)\n",
        )
        .unwrap();
        assert_eq!(
            ex.public_research(json!({}), Cancellation::new())
                .await
                .unwrap_err(),
            "public_research_worker_exit_failed"
        );
        std::fs::write(
            dir.path().join("research.py"),
            "print('{\"status\":\"PARTIAL\"}')\nraise SystemExit(2)\n",
        )
        .unwrap();
        assert_eq!(
            ex.public_research(json!({}), Cancellation::new())
                .await
                .unwrap()["status"],
            "PARTIAL"
        );
    }

    #[tokio::test]
    async fn output_overflow_fails_before_worker_exit() {
        let (dir,ex)=fixture("import sys,time\nsys.stdout.write('x'*1048577)\nsys.stdout.flush()\ntime.sleep(5)\nfrom pathlib import Path\nPath(__file__).with_suffix('.late').touch()\n").await;
        let start = Instant::now();
        assert_eq!(
            ex.public_research(json!({}), Cancellation::new())
                .await
                .unwrap_err(),
            "public_research_output_exceeds_bound"
        );
        assert!(start.elapsed() < Duration::from_secs(3));
        assert!(!dir.path().join("research.late").exists());
    }

    #[tokio::test]
    async fn stderr_is_drained_without_a_body_or_size_limit() {
        let (_dir, ex) =
            fixture("import sys\nsys.stderr.write('s'*2000000)\nsys.stderr.flush()\nprint('{}')\n")
                .await;
        assert_eq!(
            ex.public_research(json!({}), Cancellation::new())
                .await
                .unwrap(),
            json!({})
        );
    }

    #[tokio::test]
    async fn cancellation_reaps_owned_process_and_rejects_late_output() {
        let (dir, ex) = fixture(HANG).await;
        let cancel = Cancellation::new();
        let cancellation = cancel.clone();
        let task = tokio::spawn(async move { ex.public_research(json!({}), cancellation).await });
        wait_for(&dir.path().join("research.pid")).await;
        let pid: u32 = std::fs::read_to_string(dir.path().join("research.pid"))
            .unwrap()
            .parse()
            .unwrap();
        cancel.cancel();
        assert_eq!(
            tokio::time::timeout(Duration::from_secs(2), task)
                .await
                .unwrap()
                .unwrap()
                .unwrap_err(),
            "public_research_cancelled"
        );
        await_process_exit(pid).await;
        assert!(!dir.path().join("research.late").exists());
        await_staging_clean(dir.path()).await;
    }

    #[tokio::test]
    async fn deadline_reaps_hung_process() {
        let (dir, ex) = fixture(HANG).await;
        let result = ex
            .public_research_until(
                json!({}),
                Cancellation::new(),
                Instant::now() + Duration::from_millis(500),
            )
            .await;
        assert_eq!(result.unwrap_err(), "public_research_timeout");
        let pid: u32 = std::fs::read_to_string(dir.path().join("research.pid"))
            .unwrap()
            .parse()
            .unwrap();
        await_process_exit(pid).await;
        assert!(!dir.path().join("research.late").exists());
        await_staging_clean(dir.path()).await;
    }

    #[tokio::test]
    async fn disabled_before_start_and_after_execution_deny_publication() {
        let (dir,ex)=fixture("import time\nfrom pathlib import Path\np=Path(__file__)\np.with_suffix('.ready').touch()\nwhile not p.with_suffix('.release').exists(): time.sleep(.005)\nprint('{}')\n").await;
        set_enabled(&ex, false).await;
        assert_eq!(
            ex.public_research(json!({}), Cancellation::new())
                .await
                .unwrap_err(),
            "public_research_disabled"
        );
        assert!(!dir.path().join("research.ready").exists());
        set_enabled(&ex, true).await;
        let owned = ex.clone();
        let task =
            tokio::spawn(
                async move { owned.public_research(json!({}), Cancellation::new()).await },
            );
        wait_for(&dir.path().join("research.ready")).await;
        set_enabled(&ex, false).await;
        std::fs::write(dir.path().join("research.release"), "").unwrap();
        assert_eq!(task.await.unwrap().unwrap_err(), "public_research_disabled");
    }

    #[tokio::test]
    async fn slot_queue_is_cancellable_and_consumes_deadline() {
        let (dir, ex) = fixture(HANG).await;
        let _slots = ex
            .derived_slots
            .clone()
            .acquire_many_owned(4)
            .await
            .unwrap();
        let cancel = Cancellation::new();
        let owned = ex.clone();
        let c = cancel.clone();
        let task = tokio::spawn(async move { owned.public_research(json!({}), c).await });
        tokio::time::sleep(Duration::from_millis(50)).await;
        assert!(!task.is_finished());
        cancel.cancel();
        assert_eq!(
            tokio::time::timeout(Duration::from_secs(1), task)
                .await
                .unwrap()
                .unwrap()
                .unwrap_err(),
            "public_research_cancelled"
        );
        assert_eq!(
            ex.public_research_until(
                json!({}),
                Cancellation::new(),
                Instant::now() + Duration::from_millis(50)
            )
            .await
            .unwrap_err(),
            "public_research_timeout"
        );
        assert!(!dir.path().join("research.pid").exists());
    }

    #[tokio::test]
    async fn disable_during_slot_queue_prevents_spawn() {
        let (dir, ex) = fixture(HANG).await;
        let slots = ex
            .derived_slots
            .clone()
            .acquire_many_owned(4)
            .await
            .unwrap();
        let owned = ex.clone();
        let task =
            tokio::spawn(
                async move { owned.public_research(json!({}), Cancellation::new()).await },
            );
        tokio::time::sleep(Duration::from_millis(50)).await;
        set_enabled(&ex, false).await;
        drop(slots);
        assert_eq!(task.await.unwrap().unwrap_err(), "public_research_disabled");
        assert!(!dir.path().join("research.pid").exists());
    }

    #[tokio::test]
    async fn precancelled_and_expired_requests_never_spawn() {
        let (dir, ex) = fixture(HANG).await;
        let cancel = Cancellation::new();
        cancel.cancel();
        assert_eq!(
            ex.public_research(json!({}), cancel).await.unwrap_err(),
            "public_research_cancelled"
        );
        assert_eq!(
            ex.public_research_until(json!({}), Cancellation::new(), Instant::now())
                .await
                .unwrap_err(),
            "public_research_timeout"
        );
        assert!(!dir.path().join("research.pid").exists());
    }

    #[tokio::test]
    async fn dropping_request_future_withdraws_its_owned_worker() {
        let (dir, ex) = fixture(HANG).await;
        let task =
            tokio::spawn(async move { ex.public_research(json!({}), Cancellation::new()).await });
        wait_for(&dir.path().join("research.pid")).await;
        let pid: u32 = std::fs::read_to_string(dir.path().join("research.pid"))
            .unwrap()
            .parse()
            .unwrap();
        task.abort();
        assert!(task.await.unwrap_err().is_cancelled());
        await_process_exit(pid).await;
        await_staging_clean(dir.path()).await;
        assert!(!dir.path().join("research.late").exists());
    }

    #[test]
    fn blocking_pool_queue_consumes_deadline_without_a_late_spawn() {
        tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .max_blocking_threads(1)
            .build()
            .unwrap()
            .block_on(async {
                let (dir, ex) = fixture(HANG).await;
                let (started_send, started_receive) = mpsc::channel();
                let (release_send, release_receive) = mpsc::channel();
                let blocker = tokio::task::spawn_blocking(move || {
                    started_send.send(()).unwrap();
                    release_receive.recv().unwrap();
                });
                started_receive
                    .recv_timeout(Duration::from_secs(1))
                    .unwrap();
                let result = ex
                    .public_research_until(
                        json!({}),
                        Cancellation::new(),
                        Instant::now() + Duration::from_millis(50),
                    )
                    .await;
                release_send.send(()).unwrap();
                blocker.await.unwrap();
                assert_eq!(result.unwrap_err(), "public_research_timeout");
                tokio::time::sleep(Duration::from_millis(20)).await;
                assert!(!dir.path().join("research.pid").exists());
            });
    }

    #[cfg(windows)]
    #[tokio::test]
    async fn descendant_held_read_pipes_do_not_leave_reader_threads() {
        let (dir,ex)=fixture("import subprocess,sys,time\nfrom pathlib import Path\np=Path(__file__).with_name('holder.py')\nsubprocess.Popen([sys.executable,'-I','-B',str(p)],stdout=sys.stdout,stderr=sys.stderr,creationflags=0x08000000)\nwhile not p.with_suffix('.ready').exists(): time.sleep(.005)\nprint('{}')\n").await;
        std::fs::write(dir.path().join("holder.py"),"import time\nfrom pathlib import Path\np=Path(__file__)\np.with_suffix('.ready').touch()\ntime.sleep(3)\np.with_suffix('.done').touch()\n").unwrap();
        let result = ex.public_research(json!({}), Cancellation::new()).await;
        let returned_before_descendant = !dir.path().join("holder.done").exists();
        wait_for(&dir.path().join("holder.done")).await;
        assert!(
            returned_before_descendant,
            "only owned child is reaped; descendant fixture must self-exit"
        );
        // Popen inherits stdin too: retained input makes cleanup uncertainty
        // take precedence over the earlier pipe-drain failure.
        assert_eq!(result.unwrap_err(), "public_research_cleanup_failed");
    }

    #[cfg(windows)]
    #[tokio::test]
    async fn descendant_held_stdin_reports_unverified_cleanup() {
        let (dir,ex)=fixture("import subprocess,sys,time\nfrom pathlib import Path\np=Path(__file__).with_name('holder.py')\nsubprocess.Popen([sys.executable,'-I','-B',str(p)],stdin=sys.stdin,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000)\nwhile not p.with_suffix('.ready').exists(): time.sleep(.005)\nprint('{}')\n").await;
        std::fs::write(dir.path().join("holder.py"),"import time\nfrom pathlib import Path\np=Path(__file__)\np.with_suffix('.ready').touch()\ntime.sleep(3)\np.with_suffix('.done').touch()\n").unwrap();
        let result = ex
            .public_research(json!({"x":"x".repeat(16384-8)}), Cancellation::new())
            .await;
        let returned_before_descendant = !dir.path().join("holder.done").exists();
        wait_for(&dir.path().join("holder.done")).await;
        assert!(
            returned_before_descendant,
            "stdin must not require a blocked writer or waiting for fixture descendant"
        );
        assert_eq!(result.unwrap_err(), "public_research_cleanup_failed");
    }

    #[tokio::test]
    async fn withdrawal_preserves_cleanup_and_join_uncertainty() {
        for reason in ["public_research_cancelled", "public_research_timeout"] {
            assert_eq!(
                withdrawal_result(reason, Ok(Err("public_research_cleanup_failed".into())))
                    .unwrap_err(),
                "public_research_cleanup_failed"
            );
            assert_eq!(
                withdrawal_result(reason, Ok(Ok(json!({"late":true})))).unwrap_err(),
                reason
            );
        }
        let task = tokio::spawn(std::future::pending::<()>());
        task.abort();
        let error = task.await.unwrap_err();
        assert_eq!(
            withdrawal_result("public_research_cancelled", Err(error)).unwrap_err(),
            "public_research_task_failed"
        );
    }

    #[tokio::test]
    async fn only_dedicated_launch_proxy_crosses_environment_boundary() {
        const MARKER: &str = "AAOS_PUBLIC_RESEARCH_ENV_FIXTURE";
        if std::env::var_os(MARKER).is_some() {
            let (_dir,ex)=fixture("import os,json\nassert 'AAOS_SYNTHETIC_PROXY' not in os.environ\nassert 'AAOS_SYNTHETIC_AUTH_TOKEN' not in os.environ\nprint(json.dumps({'route':os.environ.get('ARCHEAXIS_PUBLIC_RESEARCH_PROXY')}))\n").await;
            let value = ex
                .public_research(json!({}), Cancellation::new())
                .await
                .unwrap();
            assert_eq!(
                value["route"],
                std::env::var("ARCHEAXIS_PUBLIC_RESEARCH_PROXY").unwrap()
            );
            return;
        }
        // A separate test process avoids mutating environment under other tests.
        for route in ["http://127.0.0.1:7890", "", "invalid-route"] {
            let mut command = Command::new(std::env::current_exe().unwrap());
            command.arg("executor::public_research::tests::only_dedicated_launch_proxy_crosses_environment_boundary").arg("--exact")
                .env(MARKER,"1").env("ARCHEAXIS_PUBLIC_RESEARCH_PROXY",route)
                .env("AAOS_SYNTHETIC_PROXY","http://synthetic.invalid")
                .env("AAOS_SYNTHETIC_AUTH_TOKEN","synthetic-not-a-credential");
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            let result = command.output().unwrap();
            assert!(
                result.status.success(),
                "isolated environment fixture failed: {}",
                String::from_utf8_lossy(&result.stdout)
            );
        }
    }

    async fn await_staging_clean(root: &Path) {
        let end = Instant::now() + Duration::from_millis(500);
        while std::fs::read_dir(root.join("staging")).unwrap().count() != 0 && Instant::now() < end
        {
            tokio::time::sleep(POLL).await;
        }
        assert_eq!(
            std::fs::read_dir(root.join("staging")).unwrap().count(),
            0,
            "owned stdin and worker directory must be cleaned"
        );
    }

    async fn await_process_exit(pid: u32) {
        // The Windows venv redirector owns its real Python child. Its termination
        // notification can lag direct-child wait by a scheduler tick; never kill
        // by a discovered PID or mistake that wrapper PID for the worker itself.
        let end = Instant::now() + Duration::from_millis(500);
        while process_alive(pid) && Instant::now() < end {
            tokio::time::sleep(POLL).await;
        }
        assert!(
            !process_alive(pid),
            "launch-owned Python did not exit after direct child reaped"
        );
    }

    #[cfg(windows)]
    fn process_alive(pid: u32) -> bool {
        #[link(name = "kernel32")]
        unsafe extern "system" {
            fn OpenProcess(access: u32, inherit: i32, pid: u32) -> *mut std::ffi::c_void;
            fn WaitForSingleObject(h: *mut std::ffi::c_void, ms: u32) -> u32;
            fn CloseHandle(h: *mut std::ffi::c_void) -> i32;
        }
        unsafe {
            let h = OpenProcess(0x00100000, 0, pid);
            if h.is_null() {
                return false;
            }
            let alive = WaitForSingleObject(h, 0) == 258;
            CloseHandle(h);
            alive
        }
    }
    #[cfg(unix)]
    fn process_alive(pid: u32) -> bool {
        unsafe extern "C" {
            fn kill(pid: i32, sig: i32) -> i32;
        }
        unsafe { kill(pid as i32, 0) == 0 }
    }
}
