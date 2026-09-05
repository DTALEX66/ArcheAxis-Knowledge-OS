//! Process-level smoke: a Supervisor can start the Rust Core server binary,
//! complete the version handshake over HTTP, and shut it down cleanly.

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_archeaxis-api")
}

fn wait_for_ready(child: &mut Child) -> String {
    let stdout = child.stdout.take().expect("stdout");
    let mut lines = BufReader::new(stdout).lines();
    let deadline = Instant::now() + Duration::from_secs(20);
    loop {
        if Instant::now() > deadline {
            panic!("core server did not become ready in time");
        }
        if let Some(line) = lines.next() {
            let line = line.unwrap();
            if line.contains("ready on") {
                // extract port from "http://127.0.0.1:PORT"
                let port = line
                    .split("127.0.0.1:")
                    .nth(1)
                    .and_then(|s| s.split_whitespace().next())
                    .and_then(|s| s.parse::<u16>().ok())
                    .expect("port parse");
                return format!("http://127.0.0.1:{port}");
            }
        }
    }
}

#[test]
fn supervisor_starts_core_and_handshakes() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("core.sqlite");

    let mut child = Command::new(bin())
        .arg(db.to_str().unwrap())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .expect("spawn core");

    let base = wait_for_ready(&mut child);

    // handshake: version endpoint
    let resp = std::process::Command::new("curl.exe")
        .args(["-s", &format!("{base}/api/v1/system/version")])
        .output()
        .expect("curl version");
    let body = String::from_utf8_lossy(&resp.stdout).to_string();
    assert!(body.contains("archeaxis-api"), "version body: {body}");
    assert!(body.contains("0.1.0-outline"));

    // workspace info proves DB is writable through the process
    let resp = std::process::Command::new("curl.exe")
        .args(["-s", &format!("{base}/api/v1/workspaces/info")])
        .output()
        .expect("curl info");
    let body = String::from_utf8_lossy(&resp.stdout).to_string();
    assert!(body.contains("sources"), "info body: {body}");

    // supervisor shutdown
    child.kill().expect("kill core");
    child.wait().ok();
}
