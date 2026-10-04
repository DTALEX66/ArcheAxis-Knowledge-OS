//! Which `schedule_authority` a review reports, and why it is a property of the launch.
//!
//! Two contracts describe this route differently. `docs/current/DSH-BACKEND-CONTRACT-20260927.md`
//! §9.2 says the Core needs `ARCHEAXIS_PYTHON` pointing at an interpreter with `fsrs`, and that
//! otherwise `/api/v1/learning/reviews` reports `schedule_authority: "unavailable"` with a null
//! `next_review`. The contract written on this branch had said the same request reports
//! `placeholder_ladder` — the 1/2/4/7/14 stub. Measuring it settled the question and the branch
//! contract was wrong: against the real binary on this host,
//!
//! | `ARCHEAXIS_PYTHON` | `schedule_authority` | `next_review` | `next_review_days` |
//! | --- | --- | --- | --- |
//! | an interpreter with `fsrs` | `fsrs` | a real timestamp | `0` |
//! | unset, or a path that does not exist | `unavailable` | `null` | `-2` |
//!
//! `placeholder_ladder` appears only on `POST /learning/events` with no `schedule_state`. The
//! distinction matters because a UI that renders `unavailable` as "scheduled" makes a claim the
//! Core explicitly declined to make, which is why the launch injects the interpreter rather than
//! asking a user to set it.
//!
//! The test below drives the case that holds on every host: a Core launched with an interpreter
//! that cannot provide `fsrs` must say `unavailable`, and must never say `placeholder_ladder`.
//! `crates/archeaxis-application/tests/scheduler_adapter.rs` covers the other side, where a real
//! `fsrs` interpreter is required.

use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpStream,
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

/// Start the real binary with `ARCHEAXIS_PYTHON` pointing somewhere that cannot import `fsrs`.
fn launch_without_fsrs(dir: &std::path::Path) -> (Owned, u16) {
    let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
    command
        .arg(dir.join("ws.sqlite"))
        .arg("0")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .current_dir(dir)
        .env("ARCHEAXIS_PYTHON", dir.join("no-such-interpreter.exe"));
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
        .recv_timeout(Duration::from_secs(12))
        .expect("bounded readiness");
    let port = line
        .rsplit(':')
        .next()
        .and_then(|value| value.trim().parse().ok())
        .expect("the readiness line names a port");
    (child, port)
}

fn request(port: u16, method: &str, path: &str, body: Option<&str>) -> (u16, serde_json::Value) {
    let mut socket = TcpStream::connect(("127.0.0.1", port)).unwrap();
    socket
        .set_read_timeout(Some(Duration::from_secs(20)))
        .unwrap();
    let payload = body.unwrap_or("");
    write!(
        socket,
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\
         x-archeaxis-launch-token: {TOKEN}\r\nContent-Type: application/json\r\n\
         idempotency-key: authority-key\r\nContent-Length: {}\r\n\r\n{payload}",
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

#[test]
fn a_review_without_a_usable_interpreter_reports_unavailable_never_a_stub() {
    let dir = tempfile::tempdir().unwrap();
    let (_child, port) = launch_without_fsrs(dir.path());

    let (status, _) = request(
        port,
        "POST",
        "/api/v1/imports",
        Some(r#"{"name":"a.txt","content_base64":"YWxwaGE="}"#),
    );
    assert!(status == 202 || status == 201, "import answered {status}");

    let (status, knowledge) = request(
        port,
        "POST",
        "/api/v1/knowledge-items",
        Some(
            r#"{"knowledge_type":"NOTE","body":"a note","status":"accepted","created_by":"human"}"#,
        ),
    );
    assert_eq!(status, 201, "knowledge: {knowledge}");
    let knowledge_id = knowledge["knowledge_id"].as_str().unwrap().to_owned();

    let (status, reference) = request(
        port,
        "POST",
        "/api/v1/learning/items/card-1/references",
        Some(&serde_json::json!({"knowledge_id": knowledge_id}).to_string()),
    );
    assert_eq!(status, 201, "reference: {reference}");

    let (status, assessment) = request(
        port,
        "POST",
        "/api/v1/learning/items/card-1/assessment",
        Some(&serde_json::json!({"knowledge_id": knowledge_id}).to_string()),
    );
    assert_eq!(status, 201, "assessment: {assessment}");
    let assessment_id = assessment["assessment_id"].as_str().unwrap().to_owned();
    let version = assessment["knowledge_version"].as_str().unwrap().to_owned();

    let (status, review) = request(
        port,
        "POST",
        "/api/v1/learning/reviews",
        Some(
            &serde_json::json!({
                "item_key": "card-1", "client_event_id": "r-1", "assessment_id": assessment_id,
                "knowledge_version": version, "answer": "alpha", "correct": true
            })
            .to_string(),
        ),
    );
    assert_eq!(status, 201, "review: {review}");
    assert_eq!(
        review["schedule_authority"], "unavailable",
        "an interpreter without fsrs must be reported as having no scheduling authority: {review}"
    );
    assert!(
        review["next_review"].is_null(),
        "no authority means no scheduled date, and inventing one is the failure this guards: {review}"
    );
    assert_ne!(
        review["schedule_authority"], "placeholder_ladder",
        "the 1/2/4/7/14 stub belongs to /learning/events, not to a review: {review}"
    );
    // The projection carries no schedule of its own, so a UI reading only the projection would
    // show nothing rather than the wrong thing - which is why this is asserted.
    assert!(
        review["mastery_projection"]["schedule"].is_null(),
        "the projection does not restate the schedule: {review}"
    );
}

#[test]
fn the_placeholder_ladder_belongs_to_events_not_reviews() {
    let dir = tempfile::tempdir().unwrap();
    let (_child, port) = launch_without_fsrs(dir.path());

    // The same launch, so the interpreter state is identical; only the route differs.
    let (status, event) = request(
        port,
        "POST",
        "/api/v1/learning/events",
        Some(
            r#"{"item_key":"card-1","kind":"quiz","outcome":"correct","client_event_id":"e-1","correct":true}"#,
        ),
    );
    assert_eq!(status, 201, "event: {event}");
    assert_eq!(
        event["schedule_authority"], "placeholder_ladder",
        "the ladder is what an unscheduled event reports: {event}"
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
    request(
        port,
        "POST",
        "/api/v1/learning/items/card-1/references",
        Some(&serde_json::json!({"knowledge_id": knowledge_id}).to_string()),
    );
    let (status, assessment) = request(
        port,
        "POST",
        "/api/v1/learning/items/card-1/assessment",
        Some(&serde_json::json!({"knowledge_id": knowledge_id}).to_string()),
    );
    assert_eq!(status, 201, "{assessment}");
    let (status, review) = request(
        port,
        "POST",
        "/api/v1/learning/reviews",
        Some(
            &serde_json::json!({
                "item_key": "card-1", "client_event_id": "r-1",
                "assessment_id": assessment["assessment_id"],
                "knowledge_version": assessment["knowledge_version"],
                "answer": "alpha", "correct": true
            })
            .to_string(),
        ),
    );
    assert_eq!(status, 201, "{review}");
    assert_eq!(
        review["schedule_authority"], "unavailable",
        "the two routes must not report the same authority for the same launch: {review}"
    );
}
