//! Trusted, bounded JSON adapters. No executable path is accepted from HTTP.
use super::*;
use serde_json::{Value, json};

const MAX_INPUT: usize = 256_000;
const MAX_OUTPUT: usize = 1_000_000;
const MAX_ERROR: usize = 8192;

pub(super) fn supported(capability: &str) -> bool {
    matches!(capability, "course.general" | "search.semantic")
}

impl Executor {
    /// Preserves declared worker outcomes, including PARTIAL/UNAVAILABLE exit 2.
    pub async fn derived_json(
        &self,
        capability: &str,
        request: Value,
        timeout: Duration,
    ) -> Result<Value, String> {
        let deadline = Instant::now() + timeout.min(Duration::from_secs(120));
        if !supported(capability) {
            return Err("unsupported derived capability".into());
        }
        let disabled = self
            .store
            .submit_wait(|conn| capability_settings::disabled_capabilities(conn))
            .await
            .map_err(|_| "capability settings unavailable")?
            .map_err(|_| "capability settings unavailable")?;
        if disabled.iter().any(|name| name == capability) {
            return Err("derived capability is disabled".into());
        }
        let mut bytes = serde_json::to_vec(&request).map_err(|_| "invalid JSON request")?;
        bytes.push(b'\n');
        if bytes.len() > MAX_INPUT {
            return Err("derived input exceeds bound".into());
        }
        let timeout = deadline.saturating_duration_since(Instant::now());
        let permit = tokio::time::timeout(timeout, self.derived_slots.clone().acquire_owned())
            .await
            .map_err(|_| "derived worker admission timed out")?
            .map_err(|_| "derived worker unavailable")?;
        // Settings may change while all four process slots are occupied.
        let disabled = self
            .store
            .submit_wait(|conn| capability_settings::disabled_capabilities(conn))
            .await
            .map_err(|_| "capability settings unavailable")?
            .map_err(|_| "capability settings unavailable")?;
        if disabled.iter().any(|name| name == capability) {
            return Err("derived capability was disabled while queued".into());
        }
        let (worker, site) = self
            .worker_for(capability)
            .ok_or("derived worker is not registered")?;
        let python = self.python.clone();
        let staging = self.staging.clone();
        let store = self.store.clone();
        let capability = capability.to_owned();
        let runtime = tokio::runtime::Handle::current();
        tokio::task::spawn_blocking(move || {
            let _permit = permit;
            // The blocking pool can queue after semaphore admission. Recheck
            // through the same SQLite owner before creating any process.
            let enabled = runtime.block_on(async {
                tokio::time::timeout(
                    deadline.saturating_duration_since(Instant::now()),
                    store.submit_wait(move |conn| {
                        capability_settings::is_enabled(conn, &capability)
                    }),
                )
                .await
                .map_err(|_| "derived worker timed out before spawn")?
                .map_err(|_| "capability settings unavailable")?
                .map_err(|_| "capability settings unavailable")
            })?;
            if !enabled {
                return Err("derived capability was disabled before spawn".into());
            }
            let timeout = deadline.saturating_duration_since(Instant::now());
            if timeout.is_zero() {
                return Err("derived worker timed out before spawn".into());
            }
            run(&staging, &python, &worker, site, Some(bytes), timeout)
        })
        .await
        .map_err(|_| "derived worker task failed")?
    }
}

pub(super) fn run(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    input: Option<Vec<u8>>,
    timeout: Duration,
) -> Result<Value, String> {
    run_mode(staging, python, worker, site, input, timeout, false, None)
}

pub(super) fn inventory(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    timeout: Duration,
) -> Result<Value, String> {
    run_mode(staging, python, worker, site, None, timeout, true, None)
}

pub(super) fn configured_inventory(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    timeout: Duration,
    profile: &archeaxis_domain::model_configuration::Profile,
) -> Result<Value, String> {
    run_mode(
        staging,
        python,
        worker,
        site,
        None,
        timeout,
        true,
        Some(profile),
    )
}

fn run_mode(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    input: Option<Vec<u8>>,
    timeout: Duration,
    inventory: bool,
    profile: Option<&archeaxis_domain::model_configuration::Profile>,
) -> Result<Value, String> {
    let dir = tempfile::tempdir_in(staging).map_err(|_| "derived staging unavailable")?;
    let mut command = Command::new(python);
    command.env_clear();
    if inventory {
        for key in [
            "ARCHEAXIS_MACHINE_ENDPOINT",
            "ARCHEAXIS_MACHINE_MODEL",
            "ARCHEAXIS_MACHINE_PROTOCOL",
        ] {
            if let Some(value) = std::env::var_os(key) {
                command.env(key, value);
            }
        }
    }
    if let Some(p) = profile {
        command
            .env("ARCHEAXIS_MACHINE_ENDPOINT", &p.endpoint)
            .env("ARCHEAXIS_MACHINE_MODEL", &p.model)
            .env("ARCHEAXIS_MACHINE_PROTOCOL", &p.protocol);
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
    // -I ignores Python environment/user site; route policy controls installed site packages.
    command.arg("-I").arg("-B").arg("-X").arg("utf8");
    if !site {
        command.arg("-S");
    }
    command.arg(worker);
    if input.is_none() {
        command.arg(if inventory { "--probe" } else { "--hello" });
    }
    command
        .current_dir(dir.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = OwnedChild(command.spawn().map_err(|_| "derived worker spawn failed")?);
    let mut stdin = child.0.stdin.take().ok_or("derived stdin unavailable")?;
    let writer = thread::spawn(move || -> std::io::Result<()> {
        if let Some(bytes) = input {
            stdin.write_all(&bytes)?;
        }
        Ok(())
    });
    let overflow = Arc::new(AtomicBool::new(false));
    fn reader(
        stream: impl Read + Send + 'static,
        limit: usize,
        overflow: Arc<AtomicBool>,
    ) -> thread::JoinHandle<std::io::Result<Vec<u8>>> {
        thread::spawn(move || {
            let mut data = Vec::new();
            stream.take((limit + 1) as u64).read_to_end(&mut data)?;
            if data.len() > limit {
                overflow.store(true, Ordering::Relaxed);
            }
            Ok(data)
        })
    }
    let out_stream = child.0.stdout.take().ok_or("derived stdout unavailable")?;
    let err_stream = child.0.stderr.take().ok_or("derived stderr unavailable")?;
    #[cfg(windows)]
    let pipe_cancel_handles = {
        use std::os::windows::io::AsHandle;
        if inventory {
            Some((
                out_stream
                    .as_handle()
                    .try_clone_to_owned()
                    .map_err(|_| "inventory stdout cancellation handle unavailable")?,
                err_stream
                    .as_handle()
                    .try_clone_to_owned()
                    .map_err(|_| "inventory stderr cancellation handle unavailable")?,
            ))
        } else {
            None
        }
    };
    let stdout = reader(out_stream, MAX_OUTPUT, overflow.clone());
    let stderr = reader(err_stream, MAX_ERROR, overflow.clone());
    let started = Instant::now();
    let status = loop {
        if overflow.load(Ordering::Relaxed) {
            break Err("derived worker output exceeds bound");
        }
        if started.elapsed() >= timeout {
            break Err("derived worker timed out");
        }
        match child.0.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(_) => break Err("derived process status unavailable"),
        }
    };
    drop(child);
    {
        let drain_deadline = Instant::now() + Duration::from_secs(1);
        while !(writer.is_finished() && stdout.is_finished() && stderr.is_finished()) {
            if Instant::now() >= drain_deadline {
                #[cfg(windows)]
                {
                    use std::os::windows::io::AsRawHandle;
                    unsafe extern "system" {
                        fn CancelSynchronousIo(thread: *mut std::ffi::c_void) -> i32;
                        fn GetThreadId(thread: *mut std::ffi::c_void) -> u32;
                        fn OpenThread(access: u32, inherit: i32, id: u32) -> *mut std::ffi::c_void;
                        fn CloseHandle(handle: *mut std::ffi::c_void) -> i32;
                        fn CancelIoEx(
                            file: *mut std::ffi::c_void,
                            overlapped: *mut std::ffi::c_void,
                        ) -> i32;
                    }
                    if let Some((out_handle, err_handle)) = &pipe_cancel_handles {
                        unsafe {
                            CancelIoEx(out_handle.as_raw_handle(), std::ptr::null_mut());
                            CancelIoEx(err_handle.as_raw_handle(), std::ptr::null_mut());
                        }
                    }
                    for handle in [
                        writer.as_raw_handle(),
                        stdout.as_raw_handle(),
                        stderr.as_raw_handle(),
                    ] {
                        // JoinHandle may not carry THREAD_TERMINATE, required for
                        // CancelSynchronousIo. Open only this owned thread's handle.
                        unsafe {
                            let id = GetThreadId(handle);
                            if id != 0 {
                                let cancellable = OpenThread(0x0001, 0, id);
                                if !cancellable.is_null() {
                                    CancelSynchronousIo(cancellable);
                                    CloseHandle(cancellable);
                                }
                            }
                        }
                    }
                }
                let cancel_deadline = Instant::now() + Duration::from_millis(100);
                while !(writer.is_finished() && stdout.is_finished() && stderr.is_finished())
                    && Instant::now() < cancel_deadline
                {
                    thread::sleep(Duration::from_millis(5));
                }
                let all_finished =
                    writer.is_finished() && stdout.is_finished() && stderr.is_finished();
                if writer.is_finished() {
                    let _ = writer.join();
                }
                if stdout.is_finished() {
                    let _ = stdout.join();
                }
                if stderr.is_finished() {
                    let _ = stderr.join();
                }
                if !all_finished {
                    return Err(if inventory {
                        "inventory reader cleanup unverified"
                    } else {
                        "derived reader cleanup unverified"
                    }
                    .into());
                }
                return Err(if inventory {
                    "inventory worker pipe drain timed out"
                } else {
                    "derived worker pipe drain timed out"
                }
                .into());
            }
            thread::sleep(Duration::from_millis(5));
        }
    }
    let written = writer.join();
    let out = stdout.join();
    let err = stderr.join();
    let status = status?;
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
mod withdrawal_tests {
    use super::*;
    use std::{future::Future, task::Poll};

    fn blocking_queue_withdrawal(capability: &'static str) {
        tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .max_blocking_threads(1)
            .build()
            .unwrap()
            .block_on(async {
                let dir = tempfile::tempdir().unwrap();
                let worker = dir.path().join("worker.py");
                std::fs::write(&worker, "from pathlib import Path\nPath(__file__).with_suffix('.started').touch()\nprint('{}')\n").unwrap();
                let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
                let ex = Executor::open_routes(
                    &dir.path().join("db"), &dir.path().join("staging"),
                    &python, &worker, &[(capability, worker.clone())],
                ).await.unwrap();
                let (started_send, started_receive) = mpsc::channel();
                let (release_send, release_receive) = mpsc::channel();
                let blocker = tokio::task::spawn_blocking(move || {
                    started_send.send(()).unwrap();
                    release_receive.recv_timeout(Duration::from_secs(10)).unwrap();
                });
                started_receive.recv_timeout(Duration::from_secs(2)).unwrap();
                let mut request = Box::pin(ex.derived_json(capability, json!({}), Duration::from_secs(5)));
                let end = Instant::now() + Duration::from_secs(2);
                loop {
                    std::future::poll_fn(|cx| {
                        assert!(request.as_mut().poll(cx).is_pending());
                        Poll::Ready(())
                    }).await;
                    if ex.derived_slots.available_permits() == 3 {
                        // The second settings read is already submitted. Drain it,
                        // then poll once to reach the blocked spawn_blocking join.
                        ex.store.submit_wait(|_| ()).await.unwrap();
                        std::future::poll_fn(|cx| {
                            assert!(request.as_mut().poll(cx).is_pending());
                            Poll::Ready(())
                        }).await;
                        break;
                    }
                    assert!(Instant::now() < end, "request never reached slot admission");
                    tokio::time::sleep(Duration::from_millis(5)).await;
                }
                ex.store.submit_wait(move |conn| capability_settings::set_enabled(conn, capability, false))
                    .await.unwrap().unwrap();
                release_send.send(()).unwrap();
                blocker.await.unwrap();
                let result = tokio::time::timeout(Duration::from_secs(3), request).await.unwrap();
                assert!(!worker.with_extension("started").exists(), "withdrawn queued worker was spawned");
                assert_eq!(result.unwrap_err(), "derived capability was disabled before spawn");
                ex.store.submit_wait(move |conn| capability_settings::set_enabled(conn, capability, true))
                    .await.unwrap().unwrap();
                ex.derived_json(capability, json!({}), Duration::from_secs(3)).await.unwrap();
                assert!(worker.with_extension("started").exists(), "enabled control worker did not execute");
            });
    }

    #[test]
    fn search_disabled_in_blocking_queue_never_spawns() {
        blocking_queue_withdrawal("search.semantic");
    }

    #[test]
    fn course_disabled_in_blocking_queue_never_spawns() {
        blocking_queue_withdrawal("course.general");
    }
}

#[cfg(all(test, windows))]
mod inventory_pipe_tests {
    use super::*;

    #[test]
    fn held_descendant_pipes_cancel_and_join_owned_readers() {
        let dir = tempfile::tempdir().unwrap();
        let worker = dir.path().join("inventory.py");
        let holder = dir.path().join("holder.py");
        // Owned fixture descendant exits by itself; never touches a shared process.
        std::fs::write(&holder, "import time\nfrom pathlib import Path\nPath(__file__).with_suffix('.ready').write_text('ready')\ntime.sleep(4)\nPath(__file__).with_suffix('.done').write_text('done')\n").unwrap();
        std::fs::write(&worker, "import subprocess,sys,time,json\nfrom pathlib import Path\np=Path(__file__).with_name('holder.py')\nsubprocess.Popen([sys.executable,'-I','-B',str(p)],stdout=sys.stdout,stderr=sys.stderr,creationflags=0x08000000)\ndeadline=time.monotonic()+2\nwhile not p.with_suffix('.ready').exists():\n assert time.monotonic()<deadline\n time.sleep(.005)\nprint(json.dumps({'synthetic':'candidate'}))\n").unwrap();
        let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON")
            .expect("canonical Python required")
            .into();
        let started = Instant::now();
        let result = inventory(dir.path(), &python, &worker, false, Duration::from_secs(3));
        let completed_before_holder = !holder.with_extension("done").exists();
        let deadline = Instant::now() + Duration::from_secs(6);
        while !holder.with_extension("done").exists() && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(10));
        }
        assert!(
            holder.with_extension("ready").exists(),
            "holder never started"
        );
        assert!(
            holder.with_extension("done").exists(),
            "owned holder did not finish"
        );
        assert!(
            completed_before_holder,
            "fixture must hold pipes beyond inventory return"
        );
        assert!(started.elapsed() < Duration::from_secs(7));
        assert_eq!(
            result.unwrap_err(),
            "inventory worker pipe drain timed out",
            "this outcome requires cancellation and joining of every owned reader"
        );
    }
}
