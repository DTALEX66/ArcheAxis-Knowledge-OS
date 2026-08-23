use crate::job::Job;
use crate::protocol::{launch_token, readiness_payload_valid};
use crate::runtime::RuntimeSpec;
use std::collections::VecDeque;
use std::io::{BufRead, BufReader, ErrorKind, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const MIGRATION_TIMEOUT: Duration = Duration::from_secs(120);
const READINESS_TIMEOUT: Duration = Duration::from_secs(30);
const READINESS_POLL_INTERVAL: Duration = Duration::from_millis(500);
const SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(8);
const RESTORE_TIMEOUT: Duration = Duration::from_secs(120);
const MAX_LOG_LINES: usize = 200;
const MAX_ONE_SHOT_OUTPUT_BYTES: usize = 16 * 1024;
const SANITIZED_ENVIRONMENT: [&str; 16] = [
    "PYTHONPATH",
    "PYTHONHOME",
    "VIRTUAL_ENV",
    // canonical ARCHEAXIS_* (AXW-RUN-205) and legacy COGNITIVE_* are both
    // stripped from the inherited environment; the launcher sets its own.
    "ARCHEAXIS_HOST",
    "ARCHEAXIS_PORT",
    "ARCHEAXIS_DATA_DIR",
    "ARCHEAXIS_DESKTOP_CONTROL",
    "ARCHEAXIS_DESKTOP_LAUNCH_TOKEN",
    "COGNITIVE_DATA_DIR",
    "COGNITIVE_HOST",
    "COGNITIVE_PORT",
    "COGNITIVE_DESKTOP_CONTROL",
    "COGNITIVE_DESKTOP_LAUNCH_TOKEN",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
];

type LogBuffer = Arc<Mutex<VecDeque<String>>>;

pub struct BackendProcess {
    pub port: u16,
    pub token: String,
    child: Child,
    job: Job,
    logs: LogBuffer,
}

impl BackendProcess {
    pub fn launch(runtime: &RuntimeSpec) -> Result<Self, String> {
        std::fs::create_dir_all(&runtime.data_dir)
            .map_err(|error| format!("failed to create desktop data directory: {error}"))?;
        let job = Job::new()?;
        let migration_logs = new_log_buffer();
        run_migration(runtime, &job, Arc::clone(&migration_logs))?;

        let port = choose_loopback_port()?;
        let token = launch_token()?;
        let logs = new_log_buffer();
        let mut command = runtime_command(runtime);
        command
            .args(["-m", "app.runtime_entrypoint", "core"])
            .env("ARCHEAXIS_HOST", "127.0.0.1")
            .env("ARCHEAXIS_PORT", port.to_string())
            .env("ARCHEAXIS_DESKTOP_CONTROL", "stdio-v1")
            .env("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", &token)
            // legacy COGNITIVE_* mirrors keep two stable releases readable
            // (AXW-RUN-205); Python prefers ARCHEAXIS_* when both exist.
            .env("COGNITIVE_HOST", "127.0.0.1")
            .env("COGNITIVE_PORT", port.to_string())
            .env("COGNITIVE_DESKTOP_CONTROL", "stdio-v1")
            .env("COGNITIVE_DESKTOP_LAUNCH_TOKEN", &token)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        let mut child = command
            .spawn()
            .map_err(|error| format!("failed to start desktop Core: {error}"))?;
        if let Err(error) = job.assign(&child) {
            let _ = child.kill();
            let _ = child.wait();
            return Err(error);
        }
        drain_child_output(&mut child, Arc::clone(&logs), "core");
        if let Err(error) = wait_for_readiness(&mut child, port, &token, &logs) {
            let _ = child.kill();
            let _ = child.wait();
            return Err(error);
        }
        Ok(Self {
            port,
            token,
            child,
            job,
            logs,
        })
    }

    pub fn shutdown(&mut self) {
        if matches!(self.child.try_wait(), Ok(Some(_))) {
            return;
        }
        if let Some(mut stdin) = self.child.stdin.take() {
            let _ = stdin.write_all(b"shutdown\n");
            let _ = stdin.flush();
        }
        if wait_for_exit(&mut self.child, SHUTDOWN_TIMEOUT).is_err() {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }

    pub fn log_tail(&self) -> String {
        format_logs(&self.logs)
    }

    pub fn exit_diagnostic(&mut self) -> Result<Option<String>, String> {
        self.child
            .try_wait()
            .map(|status| {
                status
                    .map(|status| format!("desktop Core exited with {status}\n{}", self.log_tail()))
            })
            .map_err(|error| format!("failed to inspect desktop Core: {error}"))
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        self.shutdown();
        let _ = &self.job;
    }
}

struct BoundedOutput {
    bytes: Vec<u8>,
    truncated: bool,
}

fn read_bounded_output<R: Read>(mut reader: R) -> BoundedOutput {
    let mut bytes = Vec::with_capacity(MAX_ONE_SHOT_OUTPUT_BYTES);
    let mut truncated = false;
    let mut chunk = [0_u8; 4096];
    loop {
        let Ok(size) = reader.read(&mut chunk) else {
            break;
        };
        if size == 0 {
            break;
        }
        let remaining = MAX_ONE_SHOT_OUTPUT_BYTES.saturating_sub(bytes.len());
        let retained = remaining.min(size);
        bytes.extend_from_slice(&chunk[..retained]);
        truncated |= retained != size;
    }
    BoundedOutput { bytes, truncated }
}

fn restore_receipt_valid(output: &[u8], truncated: bool) -> bool {
    if truncated {
        return false;
    }
    matches!(
        std::str::from_utf8(output),
        Ok("{\"status\":\"restored\"}")
            | Ok("{\"status\":\"restored\"}\n")
            | Ok("{\"status\":\"restored\"}\r\n")
    )
}

pub fn run_restore_backup(runtime: &RuntimeSpec, backup_path: &Path) -> Result<(), String> {
    let job = Job::new()?;
    let mut command = runtime_command(runtime);
    command
        .args(["-m", "app.runtime_entrypoint", "restore-backup"])
        .arg(backup_path)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command
        .spawn()
        .map_err(|error| format!("failed to start offline restore: {error}"))?;
    if let Err(error) = job.assign(&child) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "offline restore stdout was unavailable".to_owned())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "offline restore stderr was unavailable".to_owned())?;
    let stdout_reader = thread::spawn(move || read_bounded_output(stdout));
    let stderr_reader = thread::spawn(move || read_bounded_output(stderr));
    let status = match wait_for_exit(&mut child, RESTORE_TIMEOUT) {
        Ok(status) => status,
        Err(error) => {
            let _ = child.kill();
            let _ = child.wait();
            let _ = stdout_reader.join();
            let _ = stderr_reader.join();
            return Err(format!("offline restore timed out: {error}"));
        }
    };
    let stdout = stdout_reader
        .join()
        .map_err(|_| "offline restore stdout reader failed".to_owned())?;
    let stderr = stderr_reader
        .join()
        .map_err(|_| "offline restore stderr reader failed".to_owned())?;
    if !status.success() {
        return Err(format!(
            "offline restore failed with {status}: {}",
            String::from_utf8_lossy(&stderr.bytes)
        ));
    }
    if !restore_receipt_valid(&stdout.bytes, stdout.truncated) {
        return Err(format!(
            "offline restore returned an invalid receipt: {}",
            String::from_utf8_lossy(&stdout.bytes)
        ));
    }
    Ok(())
}

fn runtime_command(runtime: &RuntimeSpec) -> Command {
    let mut command = Command::new(&runtime.python);
    command.arg("-B");
    if runtime.isolated {
        command.arg("-I");
    }
    command.current_dir(&runtime.cwd);
    for name in SANITIZED_ENVIRONMENT {
        command.env_remove(name);
    }
    command
        .env("ARCHEAXIS_DATA_DIR", &runtime.data_dir)
        .env("COGNITIVE_DATA_DIR", &runtime.data_dir)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .env("PYTHONNOUSERSITE", "1")
        .env("NO_PROXY", "127.0.0.1")
        .env("no_proxy", "127.0.0.1");
    command
}

fn run_migration(runtime: &RuntimeSpec, job: &Job, logs: LogBuffer) -> Result<(), String> {
    let mut command = runtime_command(runtime);
    command
        .args(["-m", "app.runtime_entrypoint", "migrate"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command
        .spawn()
        .map_err(|error| format!("failed to start desktop migration: {error}"))?;
    if let Err(error) = job.assign(&child) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }
    drain_child_output(&mut child, Arc::clone(&logs), "migration");
    let status = wait_for_exit(&mut child, MIGRATION_TIMEOUT).map_err(|error| {
        let _ = child.kill();
        let _ = child.wait();
        format!("{error}\n{}", format_logs(&logs))
    })?;
    if !status.success() {
        return Err(format!(
            "desktop migration failed with {status}\n{}",
            format_logs(&logs)
        ));
    }
    Ok(())
}

fn choose_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|error| format!("failed to allocate desktop port: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("failed to inspect desktop port: {error}"))
}

fn wait_for_readiness(
    child: &mut Child,
    port: u16,
    token: &str,
    logs: &LogBuffer,
) -> Result<(), String> {
    let deadline = Instant::now() + READINESS_TIMEOUT;
    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("failed to inspect desktop Core: {error}"))?
        {
            return Err(format!(
                "desktop Core exited before readiness with {status}\n{}",
                format_logs(logs)
            ));
        }
        if probe_readiness(port, token).is_ok() {
            return Ok(());
        }
        if Instant::now() >= deadline {
            return Err(format!(
                "desktop Core readiness timed out\n{}",
                format_logs(logs)
            ));
        }
        thread::sleep(READINESS_POLL_INTERVAL);
    }
}

fn probe_readiness(port: u16, token: &str) -> Result<(), &'static str> {
    let address = ([127, 0, 0, 1], port).into();
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(300)) else {
        return Err("connect");
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(3)));
    let request = format!(
        "GET /workspace/api/_desktop/ready HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\nX-ArcheAxis-Launch-Token: {token}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return Err("write");
    }
    let mut response = Vec::new();
    let mut buffer = [0_u8; 4096];
    loop {
        match stream.read(&mut buffer) {
            Ok(0) => break,
            Ok(size) => response.extend_from_slice(&buffer[..size]),
            Err(error) if matches!(error.kind(), ErrorKind::TimedOut | ErrorKind::WouldBlock) => {
                break;
            }
            Err(_) if !response.is_empty() => break,
            Err(_) => return Err("read-before-response"),
        }
    }
    let Ok(response) = String::from_utf8(response) else {
        return Err("utf8");
    };
    let Some((headers, body)) = response.split_once("\r\n\r\n") else {
        return Err("headers");
    };
    let payload = response_body(headers, body).or_else(|| json_body(body));
    if !headers
        .lines()
        .next()
        .is_some_and(|line| line == "HTTP/1.1 200 OK" || line == "HTTP/1.0 200 OK")
    {
        return Err("status");
    }
    let Some(payload) = payload else {
        return Err("body");
    };
    if !readiness_payload_valid(&payload) {
        return Err("identity");
    }
    Ok(())
}

fn response_body(headers: &str, body: &str) -> Option<String> {
    let chunked = headers.lines().any(|line| {
        line.split_once(':').is_some_and(|(name, value)| {
            name.eq_ignore_ascii_case("transfer-encoding")
                && value.trim().eq_ignore_ascii_case("chunked")
        })
    });
    if !chunked {
        return json_body(body);
    }

    let mut remaining = body;
    let mut decoded = String::new();
    loop {
        let (size_line, after_size) = remaining.split_once("\r\n")?;
        let size = usize::from_str_radix(size_line.split(';').next()?.trim(), 16).ok()?;
        if size == 0 {
            return json_body(&decoded);
        }
        let (chunk, after_chunk) = after_size.split_at_checked(size)?;
        let after_chunk = after_chunk.strip_prefix("\r\n")?;
        decoded.push_str(chunk);
        remaining = after_chunk;
    }
}

fn json_body(body: &str) -> Option<String> {
    let trimmed = body.trim();
    let start = trimmed.find('{')?;
    let end = trimmed.rfind('}')?;
    (start <= end).then(|| trimmed[start..=end].to_owned())
}

fn wait_for_exit(child: &mut Child, timeout: Duration) -> Result<std::process::ExitStatus, String> {
    let deadline = Instant::now() + timeout;
    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("failed to wait for child process: {error}"))?
        {
            return Ok(status);
        }
        if Instant::now() >= deadline {
            return Err("child process did not exit before timeout".to_owned());
        }
        thread::sleep(Duration::from_millis(50));
    }
}

fn new_log_buffer() -> LogBuffer {
    Arc::new(Mutex::new(VecDeque::with_capacity(MAX_LOG_LINES)))
}

fn drain_child_output(child: &mut Child, logs: LogBuffer, label: &'static str) {
    if let Some(stdout) = child.stdout.take() {
        spawn_log_drain(stdout, Arc::clone(&logs), label, "stdout");
    }
    if let Some(stderr) = child.stderr.take() {
        spawn_log_drain(stderr, logs, label, "stderr");
    }
}

fn spawn_log_drain<R: Read + Send + 'static>(
    reader: R,
    logs: LogBuffer,
    label: &'static str,
    stream: &'static str,
) {
    thread::spawn(move || {
        for line in BufReader::new(reader).lines().map_while(Result::ok) {
            let Ok(mut buffer) = logs.lock() else {
                return;
            };
            if buffer.len() == MAX_LOG_LINES {
                buffer.pop_front();
            }
            buffer.push_back(format!("[{label}:{stream}] {line}"));
        }
    });
}

fn format_logs(logs: &LogBuffer) -> String {
    logs.lock()
        .map(|buffer| buffer.iter().cloned().collect::<Vec<_>>().join("\n"))
        .unwrap_or_else(|_| "desktop log buffer unavailable".to_owned())
}

#[cfg(test)]
mod tests {
    use super::{readiness_payload_valid, response_body, restore_receipt_valid, runtime_command};
    use crate::runtime::RuntimeSpec;
    use std::ffi::OsStr;
    use std::path::PathBuf;
    use std::process::{Command, Stdio};
    use std::thread;
    use std::time::{Duration, Instant};

    #[test]
    fn installed_runtime_never_writes_bytecode_into_the_bundle() {
        let runtime = RuntimeSpec {
            python: PathBuf::from("runtime/python/python.exe"),
            cwd: PathBuf::from("writable-data"),
            data_dir: PathBuf::from("writable-data"),
            isolated: true,
            external_dev: false,
        };

        let command = runtime_command(&runtime);
        let setting = command
            .get_envs()
            .find(|(name, _)| *name == OsStr::new("PYTHONDONTWRITEBYTECODE"))
            .and_then(|(_, value)| value);
        let arguments = command.get_args().collect::<Vec<_>>();

        assert_eq!(setting, Some(OsStr::new("1")));
        assert_eq!(arguments, [OsStr::new("-B"), OsStr::new("-I")]);
    }

    #[test]
    fn readiness_decodes_chunked_http_json_before_validation() {
        let headers = "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked";
        let body = "63\r\n{\"schema_version\":\"v1\",\"product\":\"ArcheAxis Knowledge\",\"workspace\":\"Human–AI Learning Workspace\"}\r\n0\r\n\r\n";

        let decoded = response_body(headers, body).expect("chunked body");
        assert!(readiness_payload_valid(&decoded));
    }

    #[test]
    fn runtime_command_sets_canonical_and_legacy_data_dir() {
        let runtime = RuntimeSpec {
            python: PathBuf::from("runtime/python/python.exe"),
            cwd: PathBuf::from("writable-data"),
            data_dir: PathBuf::from("writable-data"),
            isolated: true,
            external_dev: false,
        };

        let command = runtime_command(&runtime);
        let envs = command.get_envs().collect::<Vec<_>>();
        let canonical = envs
            .iter()
            .find(|(name, _)| *name == OsStr::new("ARCHEAXIS_DATA_DIR"))
            .and_then(|(_, value)| *value);
        let legacy = envs
            .iter()
            .find(|(name, _)| *name == OsStr::new("COGNITIVE_DATA_DIR"))
            .and_then(|(_, value)| *value);
        assert_eq!(canonical, Some(OsStr::new("writable-data")));
        assert_eq!(legacy, Some(OsStr::new("writable-data")));
    }

    #[test]
    fn restore_receipt_rejects_paths_extra_output_and_truncation() {
        assert!(restore_receipt_valid(b"{\"status\":\"restored\"}\n", false));
        for invalid in [
            b"{\"status\":\"restored\",\"path\":\"private.sqlite\"}".as_slice(),
            b"C:\\private\\backup.sqlite\n{\"status\":\"restored\"}".as_slice(),
            b"{\"status\":\"restored\"}\nextra".as_slice(),
            b"{\"status\":\"failed\"}".as_slice(),
            b"\xff\xfe".as_slice(),
        ] {
            assert!(!restore_receipt_valid(invalid, false));
        }
        assert!(!restore_receipt_valid(b"{\"status\":\"restored\"}", true));
    }

    #[test]
    fn later_core_exit_is_reported_without_exposing_backend_info() {
        let job = crate::job::Job::new().expect("create test job");
        let child = Command::new("cmd.exe")
            .args(["/d", "/c", "exit 7"])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn short-lived child");
        job.assign(&child).expect("assign child to test job");
        let mut backend = super::BackendProcess {
            port: 4312,
            token: "test-only".to_owned(),
            child,
            job,
            logs: super::new_log_buffer(),
        };
        let deadline = Instant::now() + Duration::from_secs(2);

        let diagnostic = loop {
            if let Some(diagnostic) = backend.exit_diagnostic().expect("poll child exit") {
                break diagnostic;
            }
            assert!(Instant::now() < deadline, "child exit was not detected");
            thread::sleep(Duration::from_millis(20));
        };

        assert!(diagnostic.contains("exited"));
    }
}
