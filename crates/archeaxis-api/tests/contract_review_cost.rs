//! What a review costs, and the behavioural difference behind the cost.
//!
//! `docs/architecture/CURRENT_ARCHITECTURE.md` records a known limitation: the review route waits
//! for the FSRS worker **inside** the single-writer callback, so the writer is occupied for the
//! duration. Measured on this host with five reviews each way:
//!
//! | Launch | `schedule_authority` | median |
//! | --- | --- | --- |
//! | no usable scheduler interpreter | `unavailable` | 3.0 ms |
//! | interpreter with `fsrs` | `fsrs` | 83.1 ms |
//!
//! The assertion is deliberately about the **difference**, not the milliseconds: a machine that
//! spawns a subprocess takes measurably longer than one that does not, and that is what makes the
//! writer-occupancy claim true. A tight millisecond bound would fail on a loaded CI runner for
//! reasons that say nothing about the contract, so the bound here is generous and the ratio does
//! the work.
//!
//! The `fsrs` side is skipped where the launcher's interpreter cannot import `fsrs`, so this runs
//! everywhere; `crates/archeaxis-application/tests/scheduler_adapter.rs` requires it and covers the
//! other side.

use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpStream,
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::{Duration, Instant},
};

const TOKEN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const MACHINE: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const SESSION: &str = "cccccccccccccccccccccccccccccccc";

struct Owned(Child);
impl Drop for Owned {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

struct Session {
    _child: Owned,
    port: u16,
}

fn launch(dir: &std::path::Path, interpreter: &str) -> Session {
    let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
    command
        .arg(dir.join("ws.sqlite"))
        .arg("0")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .current_dir(dir)
        .env("ARCHEAXIS_PYTHON", interpreter);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = Owned(command.spawn().unwrap());
    writeln!(
        child.0.stdin.take().unwrap(),
        "{}",
        serde_json::json!({
            "launch_token": TOKEN, "machine_token": MACHINE, "session_id": SESSION,
            "actor": "human", "protocol": "archeaxis.desktop-launch/v2"
        })
    )
    .unwrap();
    let stdout = child.0.stdout.take().unwrap();
    let (send, receive) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            if send.send(line.unwrap()).is_err() {
                break;
            }
        }
    });
    let line = receive
        .recv_timeout(Duration::from_secs(15))
        .expect("bounded readiness");
    let port = line
        .rsplit(':')
        .next()
        .and_then(|p| p.trim().parse().ok())
        .unwrap();
    Session {
        _child: child,
        port,
    }
}

fn request(port: u16, method: &str, path: &str, body: Option<&str>) -> (u16, serde_json::Value) {
    let mut socket = TcpStream::connect(("127.0.0.1", port)).unwrap();
    socket
        .set_read_timeout(Some(Duration::from_secs(60)))
        .unwrap();
    let payload = body.unwrap_or("");
    write!(
        socket,
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\
         x-archeaxis-launch-token: {TOKEN}\r\nContent-Type: application/json\r\n\
         idempotency-key: cost-key\r\nContent-Length: {}\r\n\r\n{payload}",
        payload.len()
    )
    .unwrap();
    let mut response = String::new();
    socket.read_to_string(&mut response).unwrap();
    let code = response
        .split_whitespace()
        .nth(1)
        .unwrap_or("0")
        .parse()
        .unwrap_or(0);
    let body = response.split("\r\n\r\n").nth(1).unwrap_or("");
    (
        code,
        serde_json::from_str(body).unwrap_or(serde_json::Value::Null),
    )
}

/// Submit `count` reviews, returning each one's wall time and the authorities observed.
fn review_times(port: u16, knowledge_id: &str, count: usize) -> (Vec<Duration>, Vec<String>) {
    let mut times = Vec::new();
    let mut authorities = Vec::new();
    for index in 0..count {
        let (_, assessment) = request(
            port,
            "POST",
            "/api/v1/learning/items/card-1/assessment",
            Some(&serde_json::json!({"knowledge_id": knowledge_id}).to_string()),
        );
        let body = serde_json::json!({
            "item_key": "card-1", "client_event_id": format!("r-{index}"),
            "assessment_id": assessment["assessment_id"],
            "knowledge_version": assessment["knowledge_version"],
            "answer": "alpha", "correct": true
        })
        .to_string();
        let started = Instant::now();
        let (status, review) = request(port, "POST", "/api/v1/learning/reviews", Some(&body));
        let elapsed = started.elapsed();
        assert_eq!(status, 201, "review {index}: {review}");
        times.push(elapsed);
        authorities.push(
            review["schedule_authority"]
                .as_str()
                .unwrap_or_default()
                .to_owned(),
        );
    }
    (times, authorities)
}

fn seed(port: u16) -> String {
    request(
        port,
        "POST",
        "/api/v1/imports",
        Some(r#"{"name":"a.txt","content_base64":"YWxwaGE="}"#),
    );
    let (status, knowledge) = request(
        port,
        "POST",
        "/api/v1/knowledge-items",
        Some(
            r#"{"knowledge_type":"NOTE","body":"a note","status":"accepted","created_by":"human"}"#,
        ),
    );
    assert_eq!(status, 201, "{knowledge}");
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap().to_owned();
    let (status, reference) = request(
        port,
        "POST",
        "/api/v1/learning/items/card-1/references",
        Some(&serde_json::json!({"knowledge_id": knowledge_id}).to_string()),
    );
    assert_eq!(status, 201, "{reference}");
    knowledge_id
}

fn median(mut values: Vec<Duration>) -> Duration {
    values.sort();
    values[values.len() / 2]
}

#[test]
fn a_review_that_spawns_a_scheduler_takes_longer_than_one_that_does_not() {
    // The no-scheduler side always runs: point the Core at an interpreter that cannot exist.
    let dir = tempfile::tempdir().unwrap();
    let missing = dir.path().join("no-such-interpreter.exe");
    let without = launch(dir.path(), missing.to_str().unwrap());
    let knowledge_id = seed(without.port);
    let (times_without, authorities_without) = review_times(without.port, &knowledge_id, 5);
    assert_eq!(
        authorities_without,
        vec!["unavailable"; 5],
        "an interpreter that cannot answer must report unavailable"
    );
    let baseline = median(times_without);

    // The fsrs side is skipped when the launcher's interpreter cannot import it.
    let interpreter = std::env::var("ARCHEAXIS_PYTHON").unwrap_or_default();
    let has_fsrs = Command::new(&interpreter)
        .args(["-c", "import fsrs"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false);
    if !has_fsrs {
        eprintln!("skipping the fsrs half: {interpreter} cannot import fsrs");
        // The authority must still never be the placeholder ladder on this route.
        assert!(
            !authorities_without
                .iter()
                .any(|a| a == "placeholder_ladder")
        );
        return;
    }

    let second = tempfile::tempdir().unwrap();
    let with = launch(second.path(), &interpreter);
    let knowledge_id = seed(with.port);
    let (times_with, authorities_with) = review_times(with.port, &knowledge_id, 5);
    assert_eq!(
        authorities_with,
        vec!["fsrs"; 5],
        "an interpreter with fsrs must report fsrs"
    );
    let scheduled = median(times_with);

    // The difference is the point: one spawns a subprocess inside the writer callback and the
    // other does not. The bound is generous so a loaded runner does not fail for its own reasons.
    assert!(
        scheduled > baseline,
        "a scheduled review ({scheduled:?}) must not be faster than an unscheduled one ({baseline:?})"
    );
    assert!(
        scheduled >= Duration::from_millis(5),
        "a subprocess round trip should be visible: {scheduled:?} vs {baseline:?}"
    );
}
