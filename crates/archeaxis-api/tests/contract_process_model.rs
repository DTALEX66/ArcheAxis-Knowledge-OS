//! The §1 process-model claims, pinned against the real binary.
//!
//! Most of §1 had only been exercised incidentally: the launches used elsewhere pass port 0 and a
//! valid document, which says nothing about the order the port is chosen in, what the readiness
//! line looks like, which failures exit `2` rather than `1`, or that the listener is IPv4 loopback
//! **only**.
//!
//! That last one carries the most consequence. If the Core also answered on `::1`, a client could
//! reach it by a route the contract says does not exist, and a UI that resolved `localhost` to
//! IPv6 would appear to work while depending on something that is not promised.
//!
//! Every check here was first run against the binary on this host; all fourteen held.

use std::{
    io::{BufRead, BufReader, Read, Write},
    net::{Ipv4Addr, SocketAddr, TcpListener, TcpStream},
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::Duration,
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

/// The same document with a caller-chosen launch token, so a restart can carry a new one.
fn launch_document_with(launch_token: &str, machine: &str) -> String {
    serde_json::json!({
        "launch_token": launch_token,
        "machine_token": machine,
        "session_id": SESSION,
        "actor": "human",
        "protocol": "archeaxis.desktop-launch/v2"
    })
    .to_string()
}

/// One request against a spawned Core: the status code and the raw response.
///
/// Raw rather than a client, because the point is to speak to whatever is really listening on the
/// port the readiness line named - the same reason `identifies` connects instead of trusting it.
fn request(
    address: &str,
    method: &str,
    path: &str,
    launch_token: &str,
    body: &str,
) -> (u16, String) {
    let Ok(target) = address.parse::<SocketAddr>() else {
        return (0, String::new());
    };
    let Ok(mut stream) = TcpStream::connect_timeout(&target, Duration::from_secs(3)) else {
        return (0, String::new());
    };
    let mut text = format!(
        "{method} {path} HTTP/1.1\r\nHost: {address}\r\nx-archeaxis-launch-token: {launch_token}\r\nConnection: close\r\n"
    );
    if !body.is_empty() {
        text.push_str(&format!(
            "content-type: application/json\r\ncontent-length: {}\r\n",
            body.len()
        ));
    }
    text.push_str("\r\n");
    text.push_str(body);
    if stream.write_all(text.as_bytes()).is_err() {
        return (0, String::new());
    }
    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return (0, String::new());
    }
    let status = response
        .split_whitespace()
        .nth(1)
        .and_then(|code| code.parse().ok())
        .unwrap_or(0);
    (status, response)
}

/// The value of a top-level string field, found without decoding chunks or content lengths.
fn string_field(response: &str, name: &str) -> Option<String> {
    let needle = format!("\"{name}\":\"");
    let start = response.find(&needle)? + needle.len();
    let rest = &response[start..];
    let end = rest.find('"')?;
    Some(rest[..end].to_string())
}

fn launch_document(machine: &str) -> String {
    launch_document_with(TOKEN, machine)
}

fn spawn(dir: &std::path::Path, args: &[&str], env_port: Option<&str>) -> Owned {
    let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
    command
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .current_dir(dir);
    match env_port {
        Some(port) => command.env("ARCHAXIS_VNEXT_PORT", port),
        None => command.env_remove("ARCHAXIS_VNEXT_PORT"),
    };
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    Owned(command.spawn().unwrap())
}

/// Write the launch line, then read the single readiness line from stdout.
fn handshake(child: &mut Owned, document: &str) -> String {
    writeln!(child.0.stdin.take().unwrap(), "{document}").unwrap();
    let stdout = child.0.stdout.take().unwrap();
    let (send, receive) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            if send.send(line.unwrap()).is_err() {
                break;
            }
        }
    });
    receive
        .recv_timeout(Duration::from_secs(12))
        .expect("bounded readiness")
}

/// The readiness line is a claim about a listener, so this checks the claim rather than the string.
///
/// The address it names must answer as this Core, carrying the session this launch was given. That
/// is what makes the port real: a test that only compared the number it passed to the number
/// printed would still pass if the child bound something else and echoed what it was told.
fn identifies(address: &str, launch_token: &str, session: &str) -> bool {
    let Ok(target) = address.parse::<SocketAddr>() else {
        return false;
    };
    let Ok(mut stream) = TcpStream::connect_timeout(&target, Duration::from_secs(2)) else {
        return false;
    };
    let request = format!(
        "GET /api/v1/system/version HTTP/1.1\r\nHost: {address}\r\nx-archeaxis-launch-token: {launch_token}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }
    response.contains("archeaxis-api") && response.contains(session)
}

fn port_of(line: &str) -> u16 {
    line.rsplit(':')
        .next()
        .and_then(|value| value.trim().parse().ok())
        .unwrap_or(0)
}

/// A port that nothing answers on is not necessarily a port this process may bind.
///
/// The probe here used to be a connect: an error meant "free". On a host that reserves the low
/// end of this range the two properties come apart - connecting is refused because nothing
/// listens, and binding is refused with WSAEACCES (os error 10013) - so the launch under test
/// exited before readiness and this test failed for a reason that has nothing to do with the
/// port-selection contract it pins. Binding is the property the child actually needs.
/// A port to express precedence with. Choosing one and then letting the child bind it leaves a
/// window, and the probe cannot prove bindability - which is why every assertion below checks the
/// listener the Core actually reported rather than trusting this number.
/// A cold start is a new process holding a new token over the workspace the last one left behind.
///
/// W18/Q24 asks for four things and each is asserted separately: a new process, a new token, the
/// old token no longer accepted - so nothing is answering for the process that stopped - and the
/// data still readable. The last one is what makes this a restart rather than a fresh workspace,
/// so the row is written through the Core's own route before the first process is stopped.
#[test]
fn a_cold_start_is_a_new_process_with_a_new_token_over_the_same_workspace() {
    const SECOND: &str = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";
    const SECOND_MACHINE: &str = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee";

    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("cold.sqlite");
    let db = db.to_str().unwrap().to_string();

    let (first_pid, first_address, item) = {
        let mut first = spawn(dir.path(), &[&db, "0"], None);
        let line = handshake(&mut first, &launch_document(MACHINE));
        let address = format!("127.0.0.1:{}", port_of(&line));
        assert!(identifies(&address, TOKEN, SESSION), "first launch: {line}");

        let (status, body) = request(
            &address,
            "POST",
            "/api/v1/knowledge-items",
            TOKEN,
            r#"{"knowledge_type":"FACTUAL_CLAIM","body":"survives a restart","status":"candidate","created_by":"python-worker"}"#,
        );
        assert_eq!(status, 201, "the first process must record the row: {body}");
        let id = string_field(&body, "knowledge_id").expect("a created item names itself");
        let (status, read) = request(
            &address,
            "GET",
            &format!("/api/v1/knowledge-items/{id}/v3"),
            TOKEN,
            "",
        );
        assert_eq!(
            status, 200,
            "the row must be readable before the restart: {read}"
        );
        assert!(
            read.contains("survives a restart"),
            "the read must be the row that was written: {read}"
        );
        (first.0.id(), address, id)
    };

    // The first process is gone by here; anything still answering on its port would be an
    // instance outliving the launch that owned it.
    assert!(
        !identifies(&first_address, TOKEN, SESSION),
        "the stopped process must not still be answering"
    );

    let mut second = spawn(dir.path(), &[&db, "0"], None);
    let line = handshake(&mut second, &launch_document_with(SECOND, SECOND_MACHINE));
    let second_address = format!("127.0.0.1:{}", port_of(&line));

    assert_ne!(
        second.0.id(),
        first_pid,
        "a cold start is a different process"
    );
    assert!(
        identifies(&second_address, SECOND, SESSION),
        "the new process must answer for the new token: {line}"
    );
    let item_path = format!("/api/v1/knowledge-items/{item}/v3");
    let (status, _) = request(&second_address, "GET", &item_path, TOKEN, "");
    assert_eq!(
        status, 401,
        "the previous launch token must not be accepted by the new process"
    );
    let (status, body) = request(&second_address, "GET", &item_path, SECOND, "");
    assert_eq!(status, 200, "the new token must read the workspace: {body}");
    assert!(
        body.contains("survives a restart"),
        "the row written before the restart must still be there: {body}"
    );
}

fn free_port() -> u16 {
    // Two calls used to return the same candidate, because the first bind is released before the
    // second call looks. The precedence test then compared a number with itself and passed without
    // checking anything - so a port handed out once is never handed out again in this process.
    static ISSUED: std::sync::Mutex<Option<std::collections::HashSet<u16>>> =
        std::sync::Mutex::new(None);
    let mut guard = ISSUED.lock().unwrap();
    let issued = guard.get_or_insert_with(std::collections::HashSet::new);
    for candidate in 49152..49252u16 {
        if issued.contains(&candidate) {
            continue;
        }
        let address = SocketAddr::from((Ipv4Addr::LOCALHOST, candidate));
        if TcpListener::bind(address).is_ok() {
            issued.insert(candidate);
            return candidate;
        }
    }
    panic!("no free port in the probe range");
}

#[test]
fn the_readiness_line_names_the_port_it_chose() {
    let dir = tempfile::tempdir().unwrap();
    let mut child = spawn(
        dir.path(),
        &[dir.path().join("ws.sqlite").to_str().unwrap(), "0"],
        None,
    );
    let line = handshake(&mut child, &launch_document(MACHINE));

    assert!(
        line.starts_with("archeaxis-api ready on http://"),
        "the Supervisor matches this prefix: {line}"
    );
    assert!(
        line.contains("127.0.0.1:"),
        "the line must name loopback: {line}"
    );
    assert!(
        port_of(&line) > 0,
        "port 0 must yield a usable port: {line}"
    );
    // The number is not the point; this is. The address it named must be serving this Core, which
    // is what lets the launch use port 0 instead of a port the test picked and hoped to keep.
    assert!(
        identifies(&format!("127.0.0.1:{}", port_of(&line)), TOKEN, SESSION),
        "the readiness line must name a live listener for this session: {line}"
    );
}

#[test]
fn the_listener_is_ipv4_loopback_and_nothing_else() {
    let dir = tempfile::tempdir().unwrap();
    let mut child = spawn(
        dir.path(),
        &[dir.path().join("ws.sqlite").to_str().unwrap(), "0"],
        None,
    );
    let line = handshake(&mut child, &launch_document(MACHINE));
    let port = port_of(&line);
    assert!(port > 0, "{line}");

    let v4 = TcpStream::connect_timeout(
        &SocketAddr::from((Ipv4Addr::LOCALHOST, port)),
        Duration::from_secs(3),
    );
    assert!(v4.is_ok(), "IPv4 loopback must serve: {:?}", v4.err());

    // §1 says there is no IPv6 surface. A successful connect here would be a defect, so any
    // failure counts as the contract holding - including a host with no IPv6 at all.
    let v6 = TcpStream::connect_timeout(
        &SocketAddr::from((std::net::Ipv6Addr::LOCALHOST, port)),
        Duration::from_secs(3),
    );
    assert!(
        v6.is_err(),
        "the Core answered on ::1, which §1 states must not exist"
    );
}

#[test]
fn an_argv_port_wins_over_the_environment_and_the_environment_over_the_default() {
    let dir = tempfile::tempdir().unwrap();
    let chosen = free_port();
    let other = free_port();

    // argv wins
    let mut child = spawn(
        dir.path(),
        &[
            dir.path().join("ws.sqlite").to_str().unwrap(),
            &chosen.to_string(),
        ],
        Some(&other.to_string()),
    );
    let line = handshake(&mut child, &launch_document(MACHINE));
    assert!(
        line.ends_with(&format!(":{chosen}")),
        "argv must win: {line}"
    );
    assert!(
        identifies(&format!("127.0.0.1:{chosen}"), TOKEN, SESSION),
        "the argv port must be the live listener: {line}"
    );
    assert!(
        !identifies(&format!("127.0.0.1:{other}"), TOKEN, SESSION),
        "the environment port must not be serving when argv names one: {line}"
    );
    drop(child);

    // and the environment is used when argv omits the port
    let second = tempfile::tempdir().unwrap();
    let mut child = spawn(
        second.path(),
        &[second.path().join("ws.sqlite").to_str().unwrap()],
        Some(&other.to_string()),
    );
    let line = handshake(&mut child, &launch_document(MACHINE));
    assert!(
        line.ends_with(&format!(":{other}")),
        "ARCHAXIS_VNEXT_PORT must be used when argv omits the port: {line}"
    );
    assert!(
        identifies(&format!("127.0.0.1:{other}"), TOKEN, SESSION),
        "the environment port must be the live listener when argv omits one: {line}"
    );
}

#[test]
fn a_launch_document_that_is_not_utf8_exits_two() {
    // Bounded and decodable are separate promises. These bytes are well inside the limit and still
    // not text, so the launch must be refused for its encoding rather than read as a bad document.
    let dir = tempfile::tempdir().unwrap();
    let mut child = spawn(
        dir.path(),
        &[dir.path().join("ws.sqlite").to_str().unwrap(), "0"],
        None,
    );
    child
        .0
        .stdin
        .as_mut()
        .unwrap()
        .write_all(&[0xff, 0xfe, 0xfd, b'{', b'}'])
        .unwrap();
    let status = wait_timeout(&mut child.0, Duration::from_secs(12))
        .expect("the core must exit on a document that is not utf-8");
    assert_eq!(
        status.code(),
        Some(2),
        "an undecodable document must exit 2"
    );
}

/// Wait up to `timeout` for the child to exit, so a hung launch fails the test rather than the
/// suite. `Child::wait` has no timeout and this binary is expected to exit promptly on bad input.
fn wait_timeout(child: &mut Child, timeout: Duration) -> Option<std::process::ExitStatus> {
    let deadline = std::time::Instant::now() + timeout;
    while std::time::Instant::now() < deadline {
        match child.try_wait() {
            Ok(Some(status)) => return Some(status),
            Ok(None) => std::thread::sleep(Duration::from_millis(25)),
            Err(_) => return None,
        }
    }
    None
}

fn oversized_document() -> String {
    // A valid document with one extra field large enough to pass the launch limit. Built by
    // serialisation rather than string surgery so it cannot become malformed JSON by accident.
    serde_json::json!({
        "launch_token": TOKEN,
        "machine_token": MACHINE,
        "session_id": SESSION,
        "actor": "human",
        "protocol": "archeaxis.desktop-launch/v2",
        "pad": "x".repeat(70_000)
    })
    .to_string()
}

#[test]
fn launch_input_failures_exit_two() {
    let cases: Vec<(&str, String)> = vec![
        ("an empty document", String::new()),
        (
            "an unknown field",
            serde_json::json!({
                "launch_token": TOKEN, "machine_token": MACHINE, "session_id": SESSION,
                "actor": "human", "protocol": "archeaxis.desktop-launch/v2",
                "unexpected": true
            })
            .to_string(),
        ),
        (
            "v2 without a machine token",
            serde_json::json!({
                "launch_token": TOKEN, "session_id": SESSION, "actor": "human",
                "protocol": "archeaxis.desktop-launch/v2"
            })
            .to_string(),
        ),
        (
            "a machine token equal to the launch token",
            launch_document(TOKEN),
        ),
        ("a document over the launch limit", oversized_document()),
    ];

    for (label, document) in cases {
        let dir = tempfile::tempdir().unwrap();
        let mut child = spawn(
            dir.path(),
            &[dir.path().join("ws.sqlite").to_str().unwrap(), "0"],
            None,
        );
        writeln!(child.0.stdin.take().unwrap(), "{document}").unwrap();
        let status = wait_timeout(&mut child.0, Duration::from_secs(20))
            .unwrap_or_else(|| panic!("{label} must be rejected rather than hang"));
        assert_eq!(
            status.code(),
            Some(2),
            "{label} must be a launch-input failure (exit 2), got {status:?}"
        );
    }
}

#[test]
fn a_missing_workspace_argument_exits_two() {
    let dir = tempfile::tempdir().unwrap();
    let mut child = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"))
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .current_dir(dir.path())
        .spawn()
        .unwrap();
    let status =
        wait_timeout(&mut child, Duration::from_secs(20)).expect("usage failure must exit");
    assert_eq!(status.code(), Some(2), "usage failure is exit 2");
}
