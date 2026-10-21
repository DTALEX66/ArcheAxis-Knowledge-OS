//! Real owned Core processes; synthetic local content, no network/model service.
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpStream,
    path::Path,
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::{Duration, Instant},
};
const HUMAN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const MACHINE: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const SESSION: &str = "cccccccccccccccccccccccccccccccc";
struct Owned(Child);
impl Drop for Owned {
    fn drop(&mut self) {
        if self.0.try_wait().ok().flatten().is_none() {
            let _ = self.0.kill();
        }
        let _ = self.0.wait();
    }
}
fn start(db: &Path, worker: Option<Value>) -> (Owned, u16) {
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
    let mut child = Owned(command.spawn().unwrap());
    let mut launch = json!({"protocol":"archeaxis.desktop-launch/v2", "launch_token":HUMAN,"machine_token":MACHINE,"session_id":SESSION,"actor":"human"});
    if let Some(worker) = worker {
        launch["text_worker"] = worker;
    }
    writeln!(child.0.stdin.take().unwrap(), "{launch}").unwrap();
    let stdout = child.0.stdout.take().unwrap();
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            if let Some(port) = line
                .unwrap()
                .strip_prefix("archeaxis-api ready on http://127.0.0.1:")
            {
                let _ = tx.send(port.parse().unwrap());
                break;
            }
        }
    });
    let port = rx
        .recv_timeout(Duration::from_secs(10))
        .unwrap_or_else(|e| {
            let _ = child.0.kill();
            let _ = child.0.wait();
            let mut diagnostic = String::new();
            child
                .0
                .stderr
                .take()
                .unwrap()
                .take(2048)
                .read_to_string(&mut diagnostic)
                .unwrap();
            panic!("Core readiness {e}: {diagnostic}");
        });
    (child, port)
}
fn call(port: u16, method: &str, path: &str, token: &str, body: Value) -> (u16, Value) {
    let body = if body.is_null() {
        String::new()
    } else {
        body.to_string()
    };
    let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    write!(stream,"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nx-archeaxis-launch-token: {token}\r\nx-archeaxis-actor: human\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len()).unwrap();
    let mut raw = String::new();
    stream.read_to_string(&mut raw).unwrap();
    let (head, body) = raw.split_once("\r\n\r\n").unwrap();
    let declared = head
        .lines()
        .find_map(|line| {
            line.to_ascii_lowercase()
                .strip_prefix("content-length: ")
                .map(str::to_owned)
        })
        .map(|n| n.parse::<usize>().unwrap());
    if let Some(declared) = declared {
        assert_eq!(body.len(), declared, "response was truncated");
    }
    (
        head.split_whitespace().nth(1).unwrap().parse().unwrap(),
        serde_json::from_str(body).unwrap_or(Value::Null),
    )
}
fn exit_zero(child: &mut Owned) {
    let end = Instant::now() + Duration::from_secs(7);
    loop {
        if let Some(status) = child.0.try_wait().unwrap() {
            assert_eq!(status.code(), Some(0), "Core did not exit normally");
            assert_eq!(child.0.wait().unwrap().code(), Some(0));
            return;
        }
        assert!(Instant::now() < end, "Core did not close without kill");
        std::thread::sleep(Duration::from_millis(10));
    }
}
#[test]
fn acknowledged_objects_survive_response_then_normal_exit_and_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let (mut core, port) = start(&db, None);
    let (code, doc) = call(
        port,
        "POST",
        "/api/v1/documents",
        HUMAN,
        json!({"create_request_id":"shutdown-doc","title":"saved before shutdown","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"acknowledged text"}]}]}}),
    );
    assert_eq!(code, 201, "{doc}");
    let (code, source) = call(
        port,
        "POST",
        "/api/v1/imports",
        HUMAN,
        json!({"name":"saved.txt","content_base64":"aGVsbG8="}),
    );
    assert_eq!(code, 202, "{source}");
    let source_path = format!(
        "/api/v1/sources/{}/original",
        source["source_id"].as_str().unwrap()
    );
    let (code, original) = call(port, "GET", &source_path, HUMAN, Value::Null);
    assert_eq!(code, 200);
    assert_eq!(original["content_base64"], "aGVsbG8=");
    let body = json!({"session_id":SESSION});
    let (code, ack) = call(port, "POST", "/api/v1/system/shutdown", HUMAN, body.clone());
    assert_eq!(code, 202, "missing canonical normal-close route: {ack}");
    assert_eq!(ack["state"], "draining");
    assert_eq!(ack["session_id"], SESSION);
    exit_zero(&mut core);
    let (mut reopened, port) = start(&db, None);
    assert_eq!(
        call(
            port,
            "GET",
            &format!("/api/v1/documents/{}", doc["document_id"].as_str().unwrap()),
            HUMAN,
            Value::Null
        ),
        (200, doc)
    );
    assert_eq!(
        call(port, "GET", &source_path, HUMAN, Value::Null),
        (200, original)
    );
    assert_eq!(
        call(port, "POST", "/api/v1/system/shutdown", HUMAN, body).0,
        202
    );
    exit_zero(&mut reopened);
}

#[test]
fn accepted_background_conversion_finishes_before_exit_and_is_durable() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let script = root.join("services/python-workers/transport/text_ndjson.py");
    let worker = dir.path().join("controlled_text.py");
    let started = dir.path().join("started");
    let release = dir.path().join("release");
    // The original transport and parser do the conversion. Only its timing is synthetic.
    std::fs::write(&worker,format!("import runpy,time\nfrom pathlib import Path\nm=runpy.run_path({:?})\ng=m['serve_stdio'].__globals__\noriginal=g['execute']\ndef controlled(*args):\n Path({:?}).write_text('running')\n end=time.monotonic()+6\n while not Path({:?}).exists():\n  if time.monotonic()>end: raise TimeoutError('fixture release timeout')\n  time.sleep(.01)\n return original(*args)\ng['execute']=controlled\nraise SystemExit(m['main']())\n",script.to_str().unwrap(),started.to_str().unwrap(),release.to_str().unwrap())).unwrap();
    let profile = json!({"python":std::env::var("ARCHEAXIS_PYTHON").unwrap(),"script":worker,"staging":dir.path().join("staging")});
    let (mut core, port) = start(&db, Some(profile.clone()));
    let (code, source) = call(
        port,
        "POST",
        "/api/v1/imports",
        HUMAN,
        json!({"name":"real.txt","content_base64":"aGVsbG8="}),
    );
    assert_eq!(code, 202);
    assert_eq!(
        call(
            port,
            "POST",
            "/api/v1/jobs",
            HUMAN,
            json!({"job_id":"shutdown-job","kind":"text","input_ref":source["source_id"]})
        )
        .0,
        202
    );
    // Execution uses a durable request identity in the real HTTP header.
    let token = format!("{HUMAN}\r\nidempotency-key: shutdown-attempt");
    let (code, admitted) = call(
        port,
        "POST",
        "/api/v1/jobs/shutdown-job/executions",
        &token,
        json!({"deadline_ms":7000}),
    );
    assert_eq!(code, 202, "{admitted}");
    let end = Instant::now() + Duration::from_secs(5);
    while !started.is_file() {
        assert!(
            Instant::now() < end,
            "real worker never reached controlled parser"
        );
        std::thread::sleep(Duration::from_millis(10));
    }
    assert_eq!(
        call(port, "GET", "/api/v1/jobs/shutdown-job", HUMAN, Value::Null).1["state"],
        "running"
    );
    assert_eq!(
        call(
            port,
            "POST",
            "/api/v1/system/shutdown",
            HUMAN,
            json!({"session_id":SESSION})
        )
        .0,
        202
    );
    std::thread::sleep(Duration::from_millis(100));
    assert!(
        core.0.try_wait().unwrap().is_none(),
        "202 worker was abandoned by an early Core exit"
    );
    std::fs::write(&release, b"release").unwrap();
    exit_zero(&mut core);
    let (mut reopened, port) = start(&db, Some(profile));
    assert_eq!(
        call(port, "GET", "/api/v1/jobs/shutdown-job", HUMAN, Value::Null).1["state"],
        "succeeded"
    );
    assert_eq!(
        call(
            port,
            "GET",
            "/api/v1/jobs/shutdown-job/outputs/text",
            HUMAN,
            Value::Null
        )
        .1["content"],
        "hello"
    );
    assert_eq!(
        call(
            port,
            "POST",
            "/api/v1/system/shutdown",
            HUMAN,
            json!({"session_id":SESSION})
        )
        .0,
        202
    );
    exit_zero(&mut reopened);
}
