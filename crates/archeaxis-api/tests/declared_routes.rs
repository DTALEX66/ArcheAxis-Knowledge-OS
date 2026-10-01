//! The production binary must reach a non-text engine when the launch declares it.
//!
//! `main.rs` used to call `Executor::open`, which seeds exactly one capability route
//! (`text.extract`), so every format job in a real launch settled `failed` with
//! "Core execution ended without a terminal receipt" - the capability was implemented
//! and tested, but unreachable from the shipped process. These tests launch the real
//! binary and declare the route, which is what the fix adds.
//!
//! They need `ARCHEAXIS_PYTHON` and the repository layout the workers resolve their
//! transport from, so they skip loudly rather than fail when that is unavailable - a
//! skip is not evidence, and the receipt says so.

use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpStream,
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::{Duration, Instant},
};

const TOKEN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const SESSION: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

struct Owned(Child);
impl Drop for Owned {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

/// A working directory for one launch.
///
/// The system temporary directory can sit behind a reparse point on some machines,
/// and the Core's launch validation refuses any linked ancestor. A project-local
/// directory keeps this test measuring route registration rather than temp layout.
struct Work(PathBuf);
impl Drop for Work {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
fn work_dir(label: &str) -> Work {
    let base = repo()
        .join(".project-local")
        .join("runs")
        .join("declared-routes")
        .join(format!("{label}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);
    std::fs::create_dir_all(&base).unwrap();
    Work(base)
}

fn repo() -> PathBuf {
    // Resolved (so no `..` component remains, which the Core refuses) but with the
    // Windows verbatim prefix removed, because the raw manifest directory is what the
    // other process tests use. Core also accepts the `\\?\` spelling.
    let resolved = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap();
    let text = resolved.to_string_lossy();
    match text.strip_prefix(r"\\?\") {
        Some(stripped) => PathBuf::from(stripped),
        None => resolved,
    }
}

fn spawn(db: &std::path::Path) -> Owned {
    let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
    command
        .arg(db)
        .arg("0")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    Owned(command.spawn().unwrap())
}

/// Surface why the child exited instead of reporting a bare disconnect.
fn child_stderr(child: &mut Owned) -> String {
    let Some(mut stream) = child.0.stderr.take() else {
        return String::new();
    };
    let mut text = String::new();
    let _ = stream.read_to_string(&mut text);
    text.trim().to_string()
}

fn ready(child: &mut Owned) -> u16 {
    let stdout = child.0.stdout.take().unwrap();
    let (send, receive) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            if send.send(line.unwrap()).is_err() {
                break;
            }
        }
    });
    let line = match receive.recv_timeout(Duration::from_secs(10)) {
        Ok(line) => line,
        Err(_) => panic!("no readiness line; child stderr: {}", child_stderr(child)),
    };
    line.split("127.0.0.1:")
        .nth(1)
        .unwrap()
        .split_whitespace()
        .next()
        .unwrap()
        .parse()
        .unwrap()
}

fn http_body(port: u16, method: &str, path: &str, body: &str) -> (u16, String) {
    http_with(port, method, path, body, "")
}

/// The execute route requires an `idempotency-key`, so the extra header is explicit.
fn http_with(port: u16, method: &str, path: &str, body: &str, extra: &str) -> (u16, String) {
    let mut socket = TcpStream::connect(("127.0.0.1", port)).unwrap();
    socket
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    let headers = format!(
        "x-archeaxis-launch-token: {TOKEN}\r\nContent-Type: application/json\r\n{extra}"
    );
    write!(
        socket,
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\nContent-Length: {}\r\n{headers}\r\n{body}",
        body.len()
    )
    .unwrap();
    let mut response = String::new();
    socket.read_to_string(&mut response).unwrap();
    (
        response.split_whitespace().nth(1).unwrap().parse().unwrap(),
        response.split("\r\n\r\n").nth(1).unwrap_or("").into(),
    )
}

fn get(port: u16, path: &str) -> (u16, String) {
    http_body(port, "GET", path, "")
}

fn base64(bytes: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in bytes.chunks(3) {
        let b = [
            chunk[0],
            *chunk.get(1).unwrap_or(&0),
            *chunk.get(2).unwrap_or(&0),
        ];
        let n = ((b[0] as u32) << 16) | ((b[1] as u32) << 8) | b[2] as u32;
        out.push(TABLE[(n >> 18) as usize & 63] as char);
        out.push(TABLE[(n >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 {
            TABLE[(n >> 6) as usize & 63] as char
        } else {
            '='
        });
        out.push(if chunk.len() > 2 {
            TABLE[n as usize & 63] as char
        } else {
            '='
        });
    }
    out
}

fn prerequisites() -> Option<(PathBuf, PathBuf)> {
    let python = std::env::var_os("ARCHEAXIS_PYTHON").map(PathBuf::from)?;
    let transport = repo().join("services/python-workers/transport/text_ndjson.py");
    let worker = repo().join("services/python-workers/document/worker_canvas.py");
    let canvas = repo().join("tests/fixtures/golden/learning-evidence.canvas");
    if python.is_file() && transport.is_file() && worker.is_file() && canvas.is_file() {
        Some((python, transport))
    } else {
        eprintln!(
            "skipping: needs ARCHEAXIS_PYTHON and the repository worker layout; \
             this skip is not evidence"
        );
        None
    }
}

/// Launch the real binary with one declared route and run a job through it.
fn run_declared_route(capability: &str, worker: &str, kind: &str, source_name: &str, payload: &[u8]) -> (u16, String) {
    let dir = work_dir("declared");
    let db = dir.0.join("workspace.sqlite");
    let transport = repo().join("services/python-workers/transport/text_ndjson.py");
    let worker_script = repo().join(worker);
    let mut child = spawn(&db);
    writeln!(
        child.0.stdin.take().unwrap(),
        "{}",
        serde_json::json!({
            "launch_token": TOKEN,
            "session_id": SESSION,
            "text_worker": {
                "python": std::env::var("ARCHEAXIS_PYTHON").unwrap(),
                "script": transport,
                "staging": dir.0.join("staging"),
                "routes": [{"capability": capability, "script": worker_script}],
            }
        })
    )
    .unwrap();
    let port = ready(&mut child);

    let import = serde_json::json!({
        "name": source_name,
        "content_base64": base64(payload),
    })
    .to_string();
    let (code, body) = http_body(port, "POST", "/api/v1/imports", &import);
    assert_eq!(code, 202, "import body: {body}");
    let source_id = body
        .split("\"source_id\":\"")
        .nth(1)
        .and_then(|rest| rest.split('"').next())
        .expect("import returns a source_id")
        .to_string();

    let job_id = format!("declared-{kind}");
    let enqueue = serde_json::json!({
        "job_id": job_id, "kind": kind, "input_ref": source_id,
    })
    .to_string();
    let (code, body) = http_body(port, "POST", "/api/v1/jobs", &enqueue);
    assert_eq!(code, 202, "enqueue body: {body}");

    let (code, body) = http_with(
        port,
        "POST",
        &format!("/api/v1/jobs/{job_id}/executions"),
        &serde_json::json!({"deadline_ms": 120000}).to_string(),
        &format!("idempotency-key: {job_id}\r\n"),
    );
    assert_eq!(code, 202, "execute body: {body}");

    let deadline = Instant::now() + Duration::from_secs(60);
    loop {
        let (code, body) = get(port, &format!("/api/v1/jobs/{job_id}"));
        assert_eq!(code, 200, "job readback body: {body}");
        if !body.contains("\"state\":\"running\"") && !body.contains("\"state\":\"queued\"") {
            return (code, body);
        }
        assert!(Instant::now() < deadline, "job did not settle: {body}");
        std::thread::sleep(Duration::from_millis(50));
    }
}

#[test]
fn a_declared_route_reaches_its_worker_in_the_production_binary() {
    let Some(_) = prerequisites() else { return };
    let canvas = std::fs::read(repo().join("tests/fixtures/golden/learning-evidence.canvas")).unwrap();
    let (_, body) = run_declared_route(
        "canvas.structure",
        "services/python-workers/document/worker_canvas.py",
        "canvas",
        "map.canvas",
        &canvas,
    );
    assert!(
        body.contains("\"state\":\"succeeded\""),
        "a declared route must reach its worker, got: {body}"
    );
}

#[test]
fn an_undeclared_route_still_fails_closed() {
    let Some(_) = prerequisites() else { return };
    // Only text.extract is registered here, so the canvas job must fail rather than
    // be dispatched to a worker that was never declared.
    let canvas = std::fs::read(repo().join("tests/fixtures/golden/learning-evidence.canvas")).unwrap();
    let dir = work_dir("undeclared");
    let db = dir.0.join("workspace.sqlite");
    let transport = repo().join("services/python-workers/transport/text_ndjson.py");
    let mut child = spawn(&db);
    writeln!(
        child.0.stdin.take().unwrap(),
        "{}",
        serde_json::json!({
            "launch_token": TOKEN,
            "session_id": SESSION,
            "text_worker": {
                "python": std::env::var("ARCHEAXIS_PYTHON").unwrap(),
                "script": transport,
                "staging": dir.0.join("staging"),
            }
        })
    )
    .unwrap();
    let port = ready(&mut child);

    let import = serde_json::json!({
        "name": "map.canvas",
        "content_base64": base64(&canvas),
    })
    .to_string();
    let (code, body) = http_body(port, "POST", "/api/v1/imports", &import);
    assert_eq!(code, 202, "import body: {body}");
    let source_id = body
        .split("\"source_id\":\"")
        .nth(1)
        .and_then(|rest| rest.split('"').next())
        .unwrap()
        .to_string();
    let job_id = "undeclared-canvas";
    let (code, _) = http_body(
        port,
        "POST",
        "/api/v1/jobs",
        &serde_json::json!({"job_id": job_id, "kind": "canvas", "input_ref": source_id}).to_string(),
    );
    assert_eq!(code, 202);
    let (code, body) = http_with(
        port,
        "POST",
        &format!("/api/v1/jobs/{job_id}/executions"),
        &serde_json::json!({"deadline_ms": 60000}).to_string(),
        &format!("idempotency-key: {job_id}\r\n"),
    );
    assert_eq!(code, 202, "execute body: {body}");

    let deadline = Instant::now() + Duration::from_secs(30);
    loop {
        let (_, body) = get(port, &format!("/api/v1/jobs/{job_id}"));
        if !body.contains("\"state\":\"running\"") && !body.contains("\"state\":\"queued\"") {
            assert!(
                body.contains("\"state\":\"failed\""),
                "an undeclared capability must fail closed, got: {body}"
            );
            return;
        }
        assert!(Instant::now() < deadline, "job did not settle: {body}");
        std::thread::sleep(Duration::from_millis(50));
    }
}
