//! Real owned Core + launch middleware; synthetic credentials and data only.
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpStream,
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::Duration,
};

const HUMAN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const MACHINE: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
struct Owned(Child);
fn absolute(path: &std::path::Path) -> std::path::PathBuf {
    let resolved = path.canonicalize().unwrap();
    #[cfg(windows)]
    {
        return std::path::PathBuf::from(
            resolved
                .to_str()
                .unwrap()
                .strip_prefix(r"\\?\")
                .unwrap_or(resolved.to_str().unwrap()),
        );
    }
    #[cfg(not(windows))]
    {
        resolved
    }
}
impl Drop for Owned {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}
fn start(db: &std::path::Path, legacy_machine: bool) -> (Owned, u16) {
    let root = absolute(&std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let python = absolute(&std::path::PathBuf::from(
        std::env::var_os("ARCHEAXIS_PYTHON").unwrap(),
    ));
    let profile = json!({"python":python,"script":root.join("services/python-workers/transport/text_ndjson.py"),"staging":absolute(db.parent().unwrap()).join("staging")});
    let launch = if legacy_machine {
        json!({"launch_token":HUMAN,"session_id":"c".repeat(32),"actor":"machine","text_worker":profile})
    } else {
        json!({"protocol":"archeaxis.desktop-launch/v2","launch_token":HUMAN,"machine_token":MACHINE,"session_id":"c".repeat(32),"actor":"human","text_worker":profile})
    };
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
    let mut owned = Owned(command.spawn().unwrap());
    writeln!(owned.0.stdin.take().unwrap(), "{launch}").unwrap();
    let stdout = owned.0.stdout.take().unwrap();
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            if let Some(port) = line
                .unwrap()
                .strip_prefix("archeaxis-api ready on http://127.0.0.1:")
            {
                let _ = tx.send(port.parse::<u16>().unwrap());
                return;
            }
        }
    });
    let port = rx
        .recv_timeout(Duration::from_secs(10))
        .unwrap_or_else(|error| {
            let _ = owned.0.kill();
            let _ = owned.0.wait();
            let mut diagnostic = String::new();
            owned
                .0
                .stderr
                .take()
                .unwrap()
                .take(2048)
                .read_to_string(&mut diagnostic)
                .unwrap();
            panic!("owned Core bounded readiness {error:?}: {diagnostic}");
        });
    (owned, port)
}
fn put(port: u16, token: &str, actor: &str, name: &str, body: &str) -> (u16, Value) {
    let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    write!(stream,"PUT /api/v1/capabilities/{name}/enabled HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nx-archeaxis-launch-token: {token}\r\nx-archeaxis-actor: {actor}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len()).unwrap();
    let mut raw = String::new();
    stream.read_to_string(&mut raw).unwrap();
    let (head, body) = raw.split_once("\r\n\r\n").unwrap();
    let code = head.split_whitespace().nth(1).unwrap().parse().unwrap();
    (code, serde_json::from_str(body).unwrap_or(Value::Null))
}
fn settings(db: &std::path::Path) -> Vec<(String, i64, String)> {
    let conn =
        rusqlite::Connection::open_with_flags(db, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .unwrap();
    let mut rows = conn
        .prepare(
            "SELECT capability,enabled,changed_at FROM capability_settings ORDER BY capability",
        )
        .unwrap();
    rows.query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)))
        .unwrap()
        .collect::<Result<Vec<_>, _>>()
        .unwrap()
}

#[test]
fn machine_cannot_change_host_capability_settings_even_with_forged_human_header() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("owned.sqlite");
    let (_core, port) = start(&db, false);
    let before = settings(&db);
    assert!(before.is_empty());
    for enabled in [false, true] {
        for actor in ["machine", "human", "invalid"] {
            let (code, _) = put(
                port,
                MACHINE,
                actor,
                "text.extract",
                &json!({"enabled":enabled}).to_string(),
            );
            assert_eq!(code, 403, "machine may not mutate capability policy");
            assert_eq!(settings(&db), before, "refused request changed settings");
        }
    }
    assert_eq!(
        put(
            port,
            "invalid",
            "human",
            "text.extract",
            r#"{"enabled":false}"#
        )
        .0,
        401
    );
    // Matched human credentials determine identity; caller-supplied actor cannot demote or elevate it.
    let (code, body) = put(
        port,
        HUMAN,
        "machine",
        "text.extract",
        r#"{"enabled":false}"#,
    );
    assert_eq!(code, 200);
    assert_eq!(body["capability"]["enabled"], false);
    let disabled = settings(&db);
    assert_eq!(disabled.len(), 1);
    assert_eq!(disabled[0].1, 0);
    for bad in [
        r#"{"enabled":true,"command":"do-not-run"}"#,
        r#"{"enabled":true,"enabled":false}"#,
        r#"{"enabled":"true"}"#,
    ] {
        assert_eq!(put(port, HUMAN, "human", "text.extract", bad).0, 422);
        assert_eq!(settings(&db), disabled);
    }
    assert_eq!(
        put(
            port,
            HUMAN,
            "human",
            "unknown.capability",
            r#"{"enabled":true}"#
        )
        .0,
        404
    );
    assert_eq!(settings(&db), disabled);
    let (code, body) = put(port, HUMAN, "human", "text.extract", r#"{"enabled":true}"#);
    assert_eq!(code, 200);
    assert_eq!(body["capability"]["enabled"], true);
    assert_eq!(settings(&db)[0].1, 1);
    let conn =
        rusqlite::Connection::open_with_flags(&db, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .unwrap();
    for table in ["documents", "jobs", "job_attempts"] {
        let count: i64 = conn
            .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |r| r.get(0))
            .unwrap();
        assert_eq!(count, 0, "changing settings must not create {table}");
    }
}

#[test]
fn legacy_machine_launch_cannot_change_host_policy() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("owned.sqlite");
    let (_core, port) = start(&db, true);
    assert_eq!(
        put(port, HUMAN, "human", "text.extract", r#"{"enabled":false}"#).0,
        403
    );
    assert!(settings(&db).is_empty());
}
