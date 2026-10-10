//! The §2 authentication boundaries, pinned against the real binary.
//!
//! Every line of the contract's credential model was exercised against a live Core before being
//! asserted here, and two findings are the kind a client gets wrong:
//!
//! * **both principals use the same header.** The machine token travels in
//!   `x-archeaxis-launch-token`; there is no machine header. A client that sends the machine
//!   token under `x-archeaxis-machine-token` - a name this protocol has never read, and the name
//!   the launcher itself wrongly used once - gets `401`, not a machine request.
//! * **the actor comes from which token matched, not from the request**, so a machine token that
//!   also claims `x-archeaxis-actor: human` still succeeds as a machine.
//!
//! This test speaks raw HTTP on a socket rather than through the in-process router, because a
//! duplicated header cannot be expressed through a typed request builder: a client that sets the
//! same header twice is exactly the case the contract rules out.

use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpStream,
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::Duration,
};

const HUMAN: &str = "1111111111111111111111111111111111111111111111111111111111111111";
const MACHINE: &str = "2222222222222222222222222222222222222222222222222222222222222222";
const SESSION: &str = "33333333333333333333333333333333";

struct Owned(Child);
impl Drop for Owned {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn spawn(db: &std::path::Path) -> Owned {
    let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
    command
        .arg(db)
        .arg("0")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    Owned(command.spawn().unwrap())
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
    let line = receive
        .recv_timeout(Duration::from_secs(10))
        .expect("bounded readiness");
    line.split("127.0.0.1:")
        .nth(1)
        .unwrap()
        .split_whitespace()
        .next()
        .unwrap()
        .parse()
        .unwrap()
}

/// Start the real binary with a launch document that carries both credentials and no worker,
/// so the projection router is the one under test.
fn started(dir: &tempfile::TempDir) -> (Owned, u16) {
    let mut child = spawn(&dir.path().join("ws.sqlite"));
    writeln!(
        child.0.stdin.take().unwrap(),
        "{}",
        serde_json::json!({
            "launch_token": HUMAN,
            "machine_token": MACHINE,
            "session_id": SESSION,
            "actor": "human",
            "protocol": "archeaxis.desktop-launch/v2"
        })
    )
    .unwrap();
    let port = ready(&mut child);
    (child, port)
}

/// One raw request with the header block given verbatim, so a header may appear twice.
fn ask(port: u16, header_block: &str) -> (u16, serde_json::Value) {
    let mut socket = TcpStream::connect(("127.0.0.1", port)).unwrap();
    socket
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    write!(
        socket,
        "GET /api/v1/system/version HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n{header_block}\r\n"
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

#[test]
fn both_principals_use_the_same_header() {
    let dir = tempfile::tempdir().unwrap();
    let (_child, port) = started(&dir);

    let (code, body) = ask(port, &format!("x-archeaxis-launch-token: {HUMAN}\r\n"));
    assert_eq!(code, 200, "the launch token must authenticate: {body}");

    let (code, body) = ask(port, &format!("x-archeaxis-launch-token: {MACHINE}\r\n"));
    assert_eq!(
        code, 200,
        "the machine token is a credential for the same header: {body}"
    );

    // The plausible mistake: a header this protocol has never read.
    for header in ["x-archeaxis-machine-token", "x-machine-token"] {
        let (code, body) = ask(port, &format!("{header}: {MACHINE}\r\n"));
        assert_eq!(
            code, 401,
            "{header} must fail as a missing credential: {body}"
        );
        assert_eq!(body["code"], "AAK-AUTH-001", "{header}: {body}");
    }
}

#[test]
fn a_duplicated_credential_header_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    let (_child, port) = started(&dir);

    let (code, body) = ask(
        port,
        &format!("x-archeaxis-launch-token: {HUMAN}\r\nx-archeaxis-launch-token: {HUMAN}\r\n"),
    );
    assert_eq!(
        code, 401,
        "the contract allows exactly one credential header, so two must be refused: {body}"
    );
    assert_eq!(body["code"], "AAK-AUTH-001", "{body}");
}

#[test]
fn unmatched_and_malformed_values_answer_the_same_401() {
    let dir = tempfile::tempdir().unwrap();
    let (_child, port) = started(&dir);

    let cases = [
        ("no header", String::new()),
        ("empty value", "x-archeaxis-launch-token: \r\n".to_string()),
        (
            "wrong length",
            "x-archeaxis-launch-token: abc\r\n".to_string(),
        ),
        (
            "right length, wrong content",
            format!("x-archeaxis-launch-token: {}\r\n", "f".repeat(64)),
        ),
    ];
    for (label, block) in cases {
        let (code, body) = ask(port, &block);
        assert_eq!(code, 401, "{label}: {body}");
        assert_eq!(body["code"], "AAK-AUTH-001", "{label}: {body}");
        assert_eq!(body["retryable"], false, "{label}: {body}");
    }
}

#[test]
fn a_browser_origin_is_refused_even_with_a_valid_credential() {
    let dir = tempfile::tempdir().unwrap();
    let (_child, port) = started(&dir);

    for origin in ["http://127.0.0.1:1", "null", "file://"] {
        let (code, body) = ask(
            port,
            &format!("x-archeaxis-launch-token: {HUMAN}\r\norigin: {origin}\r\n"),
        );
        assert_eq!(code, 403, "{origin}: {body}");
        assert_eq!(body["code"], "AAK-AUTH-002", "{origin}: {body}");
        assert_eq!(
            body["message"], "browser origin not allowed",
            "{origin}: {body}"
        );
    }
}
