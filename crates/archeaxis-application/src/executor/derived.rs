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
        tokio::task::spawn_blocking(move || {
            let _permit = permit;
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
    let dir = tempfile::tempdir_in(staging).map_err(|_| "derived staging unavailable")?;
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
    // -I ignores Python environment/user site; route policy controls installed site packages.
    command.arg("-I").arg("-B").arg("-X").arg("utf8");
    if !site {
        command.arg("-S");
    }
    command.arg(worker);
    if input.is_none() {
        command.arg("--hello");
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
    let stdout = reader(
        child.0.stdout.take().ok_or("derived stdout unavailable")?,
        MAX_OUTPUT,
        overflow.clone(),
    );
    let stderr = reader(
        child.0.stderr.take().ok_or("derived stderr unavailable")?,
        MAX_ERROR,
        overflow.clone(),
    );
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
