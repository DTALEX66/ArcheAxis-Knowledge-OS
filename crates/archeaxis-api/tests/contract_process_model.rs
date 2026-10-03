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
    io::{BufRead, BufReader, Write},
    net::{Ipv4Addr, SocketAddr, TcpStream},
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

fn launch_document(machine: &str) -> String {
    serde_json::json!({
        "launch_token": TOKEN,
        "machine_token": machine,
        "session_id": SESSION,
        "actor": "human",
        "protocol": "archeaxis.desktop-launch/v2"
    })
    .to_string()
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

fn port_of(line: &str) -> u16 {
    line.rsplit(':')
        .next()
        .and_then(|value| value.trim().parse().ok())
        .unwrap_or(0)
}

fn free_port() -> u16 {
    for candidate in 49152..49252u16 {
        let address = SocketAddr::from((Ipv4Addr::LOCALHOST, candidate));
        if TcpStream::connect_timeout(&address, Duration::from_millis(120)).is_err() {
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
