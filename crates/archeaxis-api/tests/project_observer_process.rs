//! 自建合成资料、真实 Core/HTTP/消费者进程；不代表外部产品或安装资格。
use archeaxis_contracts::project_observer::{
    self as contract, ObjectReference, ObjectState, Payload, ReadResponse,
};
use serde_json::{Value, json};
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpStream,
    path::Path,
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::Duration,
};
const HUMAN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const MACHINE: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const OBSERVER: &str = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
const INSTANCE: &str = "dddddddddddddddddddddddddddddddd";
struct Owned(Child);
impl Drop for Owned {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}
fn seed(db: &Path) -> (String, ObjectReference, String) {
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let workspace = archeaxis_domain::ui_state::workspace_id(&conn).unwrap();
    let doc = archeaxis_domain::document::create_optional(&mut conn, None, None, "SYNTHETIC private title", json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"SYNTHETIC PRIVATE BODY NEVER EXPORT"}]}]})).unwrap();
    let other = archeaxis_domain::document::create_optional(
        &mut conn,
        None,
        None,
        "not admitted",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    (
        workspace,
        ObjectReference {
            document_id: doc["document_id"].as_str().unwrap().into(),
            version: 1,
            content_sha256: doc["content_sha256"].as_str().unwrap().into(),
        },
        other["document_id"].as_str().unwrap().into(),
    )
}
fn grant(workspace: &str, id: &str) -> Value {
    json!({"token":OBSERVER,"consumer":{"namespace":"work-lab","instance_id":INSTANCE},"producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},"expires_at_ms":archeaxis_api::project_observer::now_ms()+60_000,"document_ids":[id]})
}
fn launch(grants: Value) -> Value {
    json!({"protocol":"archeaxis.desktop-launch/v3","actor":"human","launch_token":HUMAN,"machine_token":MACHINE,"session_id":"e".repeat(32),"observer_grants":grants})
}
fn start(db: &Path, document: Value) -> (Owned, u16) {
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
    let mut owned = Owned(command.spawn().unwrap());
    writeln!(owned.0.stdin.take().unwrap(), "{document}").unwrap();
    let stdout = owned.0.stdout.take().unwrap();
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            if tx.send(line.unwrap()).is_err() {
                break;
            }
        }
    });
    let line = rx
        .recv_timeout(Duration::from_secs(8))
        .expect("owned Core bounded readiness");
    for secret in [HUMAN, MACHINE, OBSERVER] {
        assert!(!line.contains(secret));
    }
    let port = line
        .split("127.0.0.1:")
        .nth(1)
        .unwrap()
        .split_whitespace()
        .next()
        .unwrap()
        .parse()
        .unwrap();
    (owned, port)
}
fn request(
    port: u16,
    token: &str,
    method: &str,
    path: &str,
    extra: &str,
    body: &str,
) -> (u16, String) {
    let mut socket = TcpStream::connect(("127.0.0.1", port)).unwrap();
    socket
        .set_read_timeout(Some(Duration::from_secs(4)))
        .unwrap();
    write!(socket,"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\nx-archeaxis-launch-token: {token}\r\nx-archeaxis-observer-protocol: {}\r\nx-archeaxis-observer-namespace: work-lab\r\nx-archeaxis-observer-instance: {INSTANCE}\r\nContent-Length: {}\r\n{extra}\r\n{body}",contract::PROTOCOL,body.len()).unwrap();
    let mut raw = String::new();
    socket.read_to_string(&mut raw).unwrap();
    for secret in [HUMAN, MACHINE, OBSERVER] {
        assert!(!raw.contains(secret));
    }
    (
        raw.split_whitespace().nth(1).unwrap().parse().unwrap(),
        raw.split_once("\r\n\r\n").unwrap().1.into(),
    )
}
fn snapshot(db: &Path) -> Vec<(String, Vec<Vec<String>>)> {
    let conn =
        rusqlite::Connection::open_with_flags(db, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .unwrap();
    let mut statement = conn
        .prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        .unwrap();
    let names: Vec<String> = statement
        .query_map([], |row| row.get(0))
        .unwrap()
        .map(Result::unwrap)
        .collect();
    names
        .into_iter()
        .map(|name| {
            let mut statement = conn
                .prepare(&format!("SELECT * FROM \"{}\"", name.replace('"', "\"\"")))
                .unwrap();
            let count = statement.column_count();
            let mut rows: Vec<Vec<String>> = statement
                .query_map([], |row| {
                    Ok((0..count)
                        .map(|i| format!("{:?}", row.get_ref(i).unwrap()))
                        .collect())
                })
                .unwrap()
                .map(Result::unwrap)
                .collect();
            rows.sort();
            (name, rows)
        })
        .collect()
}
fn adapter(port: u16, workspace: &str, action: Value) -> (bool, Value) {
    let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-project-observer"));
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = command.spawn().unwrap();
    let input = json!({"admission":{"port":port,"token":OBSERVER,"producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":INSTANCE}},"action":action});
    writeln!(child.stdin.take().unwrap(), "{input}").unwrap();
    let output = child.wait_with_output().unwrap();
    let text = String::from_utf8(output.stdout).unwrap();
    for secret in [HUMAN, MACHINE, OBSERVER] {
        assert!(!text.contains(secret));
    }
    assert!(output.stderr.is_empty());
    (
        output.status.success(),
        serde_json::from_str(&text).unwrap(),
    )
}
#[test]
fn real_adapter_two_independent_workspaces_reads_metadata_without_writes_or_acceptance() {
    let dir = tempfile::tempdir().unwrap();
    let a = dir.path().join("producer.sqlite");
    let b = dir.path().join("consumer.sqlite");
    let (workspace, reference, forbidden) = seed(&a);
    let (other_workspace, _, _) = seed(&b);
    assert_ne!(workspace, other_workspace);
    let (_producer, port) = start(
        &a,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let (consumer_host, _) = start(
        &b,
        json!({"protocol":"archeaxis.desktop-launch/v2","actor":"human","launch_token":"f".repeat(64),"machine_token":"9".repeat(64),"session_id":INSTANCE}),
    );
    let before_a = snapshot(&a);
    let before_b = snapshot(&b);
    for action in [
        json!({"operation":"handshake"}),
        json!({"operation":"objects"}),
        json!({"operation":"status","reference":reference}),
    ] {
        let (success, response) = adapter(port, &workspace, action);
        assert!(success, "{response}");
        let parsed: ReadResponse = serde_json::from_value(response.clone()).unwrap();
        assert!(parsed.valid(archeaxis_api::project_observer::now_ms()));
        let raw = response.to_string();
        for forbidden_value in [
            "PRIVATE BODY",
            "private title",
            forbidden.as_str(),
            a.to_str().unwrap(),
            "editor_json",
            "workspace_db",
            "launch_token",
        ] {
            assert!(!raw.contains(forbidden_value), "{raw}");
        }
        match parsed.payload {
            Payload::Handshake {
                grants_execution,
                grants_knowledge_acceptance,
                ..
            } => {
                assert!(!grants_execution);
                assert!(!grants_knowledge_acceptance);
            }
            Payload::Objects { objects, .. } => assert_eq!(objects, vec![reference.clone()]),
            Payload::ObjectStatus {
                reference: echoed,
                state,
                ..
            } => {
                assert_eq!(echoed, reference);
                assert_eq!(state, ObjectState::Current);
            }
        }
    }
    assert_eq!(snapshot(&a), before_a);
    assert_eq!(snapshot(&b), before_b);
    drop(consumer_host); // 另一产品缺失不阻断 producer，也不需要共享业务 DB。
    assert!(adapter(port, &workspace, json!({"operation":"objects"})).0);
    assert_eq!(snapshot(&a), before_a);
    assert_eq!(snapshot(&b), before_b);
}
#[test]
fn observer_cannot_reach_mutations_private_reads_or_forge_identity_and_old_roles_survive() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("roles.sqlite");
    let (workspace, reference, forbidden) = seed(&db);
    let (_producer, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let before = snapshot(&db);
    for (method, path) in [
        ("POST", "/api/v1/documents"),
        ("PUT", "/api/v1/documents/anything/draft"),
        ("POST", "/api/v1/jobs/anything/execute"),
        ("POST", "/api/v1/jobs/anything/cancel"),
        ("PUT", "/api/v1/model-configuration"),
        ("POST", "/api/v1/conversation/requests"),
        ("POST", "/api/v1/character-memory"),
        ("POST", "/api/v1/knowledge-items"),
        ("GET", "/api/v1/system/version"),
        ("GET", "/api/v1/documents"),
        ("GET", "/api/v1/sources/anything/original"),
        ("GET", "/api/v1/workspace/ui-state"),
        ("GET", "/unknown"),
        ("POST", "/api/v1/project-observer/handshake"),
    ] {
        assert_eq!(
            request(
                port,
                OBSERVER,
                method,
                path,
                "Content-Type: application/json\r\n",
                "{}"
            )
            .0,
            403,
            "{method} {path}"
        );
    }
    let path = "/api/v1/project-observer/handshake";
    for extra in [
        "x-archeaxis-actor: human\r\n",
        "Origin: http://localhost\r\n",
        "x-archeaxis-observer-namespace: design-lab\r\n",
        "x-archeaxis-observer-instance: ffffffffffffffffffffffffffffffff\r\n",
    ] {
        assert_eq!(request(port, OBSERVER, "GET", path, extra, "").0, 403);
    }
    assert_eq!(
        request(
            port,
            OBSERVER,
            "GET",
            path,
            "x-archeaxis-observer-protocol: unknown\r\n",
            ""
        )
        .0,
        409
    );
    assert_eq!(
        request(
            port,
            OBSERVER,
            "GET",
            path,
            &format!("x-archeaxis-launch-token: {HUMAN}\r\n"),
            ""
        )
        .0,
        401
    );
    assert_eq!(request(port, "0", "GET", path, "", "").0, 401);
    assert_eq!(
        request(
            port,
            OBSERVER,
            "GET",
            &format!(
                "/api/v1/project-observer/objects/{forbidden}?version=1&content_sha256={}",
                "a".repeat(64)
            ),
            "",
            ""
        )
        .0,
        403
    );
    for path in [
        "/api/v1/project-observer/handshake?url=http://evil",
        "/api/v1/project-observer/objects?limit=999",
        "/api/v1/project-observer/objects/%2e%2e?version=1&content_sha256=foo",
    ] {
        assert!(request(port, OBSERVER, "GET", path, "", "").0 >= 400);
    }
    for token in [HUMAN, MACHINE] {
        let (code, raw) = request(
            port,
            token,
            "GET",
            "/api/v1/system/version",
            "x-archeaxis-actor: human\r\n",
            "",
        );
        assert_eq!(code, 200);
        let body: Value = serde_json::from_str(&raw).unwrap();
        assert_eq!(
            body["actor"],
            if token == HUMAN { "human" } else { "machine" }
        );
        assert_eq!(request(port, token, "GET", path, "", "").0, 404);
    }
    assert_eq!(snapshot(&db), before);
}
#[test]
fn observer_empty_store_does_not_initialize_identity_and_wrong_workspace_is_not_current() {
    let dir = tempfile::tempdir().unwrap();
    let empty = dir.path().join("empty.sqlite");
    let (_host, port) = start(&empty, launch(json!([grant(&"1".repeat(32), "doc_1")])));
    let before = snapshot(&empty);
    let (code, raw) = request(
        port,
        OBSERVER,
        "GET",
        "/api/v1/project-observer/handshake",
        "",
        "",
    );
    assert_eq!(code, 503);
    assert!(raw.contains("OBSERVER_IDENTITY_UNAVAILABLE"));
    assert_eq!(snapshot(&empty), before);
    let seeded = dir.path().join("seeded.sqlite");
    let (_, reference, _) = seed(&seeded);
    let (_host, port) = start(
        &seeded,
        launch(json!([grant(&"1".repeat(32), &reference.document_id)])),
    );
    let before = snapshot(&seeded);
    assert_eq!(
        request(
            port,
            OBSERVER,
            "GET",
            "/api/v1/project-observer/handshake",
            "",
            ""
        )
        .0,
        409
    );
    assert_eq!(snapshot(&seeded), before);
}
#[test]
fn revision_change_is_stale_restore_fence_rejects_old_admission_and_disconnect_is_not_success() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("revisions.sqlite");
    let (workspace, reference, _) = seed(&db);
    let (host, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let body=json!({"expected_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"synthetic updated version"}]}]}}).to_string();
    assert_eq!(
        request(
            port,
            HUMAN,
            "PUT",
            &format!("/api/v1/documents/{}/draft", reference.document_id),
            "Content-Type: application/json\r\n",
            &body
        )
        .0,
        200
    );
    let (success, response) = adapter(
        port,
        &workspace,
        json!({"operation":"status","reference":reference}),
    );
    assert!(success);
    let parsed: ReadResponse = serde_json::from_value(response).unwrap();
    assert!(matches!(
        parsed.payload,
        Payload::ObjectStatus {
            state: ObjectState::Stale,
            ..
        }
    ));
    drop(host);
    let (success, response) = adapter(port, &workspace, json!({"operation":"objects"}));
    assert!(!success);
    assert_eq!(response["code"], "OBSERVER_UNAVAILABLE");
    let mut conn = rusqlite::Connection::open(&db).unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    drop(conn);
    let (_restarted, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let (success, response) = adapter(port, &workspace, json!({"operation":"objects"}));
    assert!(!success);
    assert_eq!(response["code"], "OBSERVER_INCOMPATIBLE");
}
#[test]
fn malformed_or_colliding_bootstrap_grants_fail_before_opening_a_workspace() {
    let dir = tempfile::tempdir().unwrap();
    let base = launch(json!([grant(&"1".repeat(32), "doc_1")]));
    let mut invalid = Vec::new();
    for token in [HUMAN, MACHINE, "short"] {
        let mut value = base.clone();
        value["observer_grants"][0]["token"] = json!(token);
        invalid.push(value);
    }
    for grants in [
        Value::Null,
        json!([]),
        json!([
            grant(&"1".repeat(32), "doc_1"),
            grant(&"1".repeat(32), "doc_1")
        ]),
    ] {
        let mut value = base.clone();
        value["observer_grants"] = grants;
        invalid.push(value);
    }
    for (field, value) in [
        ("expires_at_ms", json!(1)),
        ("document_ids", json!(["../escape"])),
        (
            "consumer",
            json!({"namespace":"human","instance_id":INSTANCE}),
        ),
        ("unknown", json!(true)),
    ] {
        let mut entry = base.clone();
        entry["observer_grants"][0][field] = value;
        invalid.push(entry);
    }
    let mut legacy = base.clone();
    legacy["protocol"] = json!("archeaxis.desktop-launch/v2");
    invalid.push(legacy);
    for (index, document) in invalid.into_iter().enumerate() {
        let db = dir.path().join(format!("invalid_{index}.sqlite"));
        let mut command = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
        command
            .arg(&db)
            .arg("0")
            .stdin(Stdio::piped())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        let mut owned = Owned(command.spawn().unwrap());
        writeln!(owned.0.stdin.take().unwrap(), "{document}").unwrap();
        let deadline = std::time::Instant::now() + Duration::from_secs(8);
        loop {
            if let Some(status) = owned.0.try_wait().unwrap() {
                assert!(!status.success());
                break;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "invalid launch remained alive"
            );
            std::thread::sleep(Duration::from_millis(20));
        }
        assert!(!db.exists(), "invalid bootstrap opened database");
    }
}

#[test]
fn an_admitted_live_observer_expires_and_cannot_turn_cached_success_into_a_new_read() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("expiry.sqlite");
    let (workspace, reference, _) = seed(&db);
    let mut entry = grant(&workspace, &reference.document_id);
    let expiry = archeaxis_api::project_observer::now_ms() + 2_000;
    entry["expires_at_ms"] = json!(expiry);
    let (_host, port) = start(&db, launch(json!([entry])));
    assert_eq!(
        request(
            port,
            OBSERVER,
            "GET",
            "/api/v1/project-observer/handshake",
            "",
            ""
        )
        .0,
        200
    );
    let before = snapshot(&db);
    while archeaxis_api::project_observer::now_ms() <= expiry {
        std::thread::sleep(Duration::from_millis(25));
    }
    let (code, raw) = request(
        port,
        OBSERVER,
        "GET",
        "/api/v1/project-observer/handshake",
        "",
        "",
    );
    assert_eq!(code, 403);
    assert!(raw.contains("OBSERVER_GRANT_EXPIRED"));
    assert_eq!(snapshot(&db), before);
}
