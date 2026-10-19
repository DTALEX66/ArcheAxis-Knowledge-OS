//! 自建合成资料、真实 Core/HTTP/消费者进程；不代表外部产品或安装资格。
use archeaxis_contracts::project_handoff::Handoff;
use archeaxis_contracts::project_observer::{self as contract, ObjectReference};
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
    for secret in [HUMAN, MACHINE, OBSERVER] {
        assert!(!String::from_utf8_lossy(&output.stderr).contains(secret));
    }
    assert!(output.stderr.is_empty());
    (
        output.status.success(),
        serde_json::from_str(&text).unwrap(),
    )
}

fn selected(reference: &ObjectReference) -> Value {
    json!({"reference":reference,"selection":{"kind":"whole_object"},"selection_qualification":"UNVERIFIED"})
}
fn context(reference: &ObjectReference) -> Value {
    json!({"kind":"context","source":selected(reference),"purpose":"learning","authorization_scope":"REFERENCE_METADATA_ONLY"})
}
fn assert_metadata(value: &Value, db: &Path, forbidden: &str) {
    let raw = value.to_string();
    for secret in [
        HUMAN,
        MACHINE,
        OBSERVER,
        "PRIVATE BODY",
        "private title",
        forbidden,
        db.to_str().unwrap(),
        "editor_json",
        "workspace_db",
        "launch_token",
    ] {
        assert!(!raw.contains(secret), "metadata boundary violated");
    }
}
fn prepare_action(key: char, payload: Value) -> Value {
    json!({"operation":"prepare_handoff","key":key.to_string().repeat(32),"payload":payload})
}
fn expect_error(port: u16, workspace: &str, action: Value, code: &str) {
    let (success, value) = adapter(port, workspace, action);
    assert!(!success);
    assert_eq!(
        value,
        json!({"schema":"archeaxis.project-observer-error/v1","code":code})
    );
}

#[test]
fn five_handoff_kinds_are_prepared_by_real_core_and_cli_without_database_writes() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("five-kinds.sqlite");
    let (workspace, reference, forbidden) = seed(&db);
    let (_host, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let before = snapshot(&db);
    let payloads = [
        context(&reference),
        json!({"kind":"task_proposal","target":reference,"context":[selected(&reference)],"goal":"prepare_learning_activity","capability":{"capability_id":"CAP-0060","contribution_point":"learning_activity","manifest_identity":"UNKNOWN"},"execution_authority":"NOT_GRANTED"}),
        json!({"kind":"asset_manifest","assets":[{"reference":reference,"source_reference":reference,"relationship":"ORIGINAL","format":"unknown","format_qualification":"UNVERIFIED","loss":{"state":"UNKNOWN"}}]}),
        json!({"kind":"knowledge_candidate","candidate_id":"candidate_metadata","candidate_revision":1,"claim_sha256":"7".repeat(64),"basis":reference,"evidence":[selected(&reference)],"review_state":"PENDING_HUMAN_REVIEW","evidence_support":"NOT_ASSESSED"}),
    ];
    for (index, payload) in payloads.into_iter().enumerate() {
        let key = char::from(b'1' + index as u8);
        let (success, original) = adapter(port, &workspace, prepare_action(key, payload.clone()));
        assert!(success, "{original}");
        let parsed: Handoff = serde_json::from_value(original.clone()).unwrap();
        assert!(parsed.valid(archeaxis_api::project_observer::now_ms()));
        assert_eq!(original["authority"], "PREPARATION_ONLY");
        assert_eq!(original["payload"], payload);
        assert_eq!(original["producer"]["workspace_id"], workspace);
        assert_eq!(original["consumer"]["instance_id"], INSTANCE);
        assert_metadata(&original, &db, &forbidden);
        for (state, reason) in [
            ("PREPARED", "NONE"),
            ("UNKNOWN", "UNOBSERVED"),
            ("CONFLICT", "IDEMPOTENCY_CONFLICT"),
        ] {
            let (success, receipt) = adapter(
                port,
                &workspace,
                json!({"operation":"prepare_receipt","key":"9".repeat(32),"original":original,"state":state,"reason":reason}),
            );
            assert!(success, "{receipt}");
            let parsed_receipt: Handoff = serde_json::from_value(receipt.clone()).unwrap();
            assert!(archeaxis_api::project_handoff::receipt_matches(
                &parsed_receipt,
                &parsed,
                archeaxis_api::project_observer::now_ms()
            ));
            assert_eq!(receipt["payload"]["state"], state);
            assert_eq!(
                receipt["payload"]["proposal"]["proposal_sha256"],
                archeaxis_api::project_handoff::proposal_fingerprint(&parsed).unwrap()
            );
            assert_metadata(&receipt, &db, &forbidden);
        }
    }
    assert_eq!(
        snapshot(&db),
        before,
        "CLI preparation wrote business tables"
    );
}

#[test]
fn stale_unlisted_and_invalid_contracts_are_never_prepared_as_current() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("rejected.sqlite");
    let (workspace, reference, forbidden) = seed(&db);
    let (_host, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let before = snapshot(&db);
    for changed in [
        ObjectReference {
            document_id: forbidden,
            ..reference.clone()
        },
        ObjectReference {
            version: 2,
            ..reference.clone()
        },
        ObjectReference {
            content_sha256: "0".repeat(64),
            ..reference.clone()
        },
    ] {
        expect_error(
            port,
            &workspace,
            prepare_action('1', context(&changed)),
            "HANDOFF_REFERENCE_NOT_CURRENT",
        );
    }
    let invalid = json!({"kind":"task_proposal","target":reference,"context":[selected(&reference)],"goal":"prepare_learning_activity","capability":{"capability_id":"CAP-0020","contribution_point":"learning_activity","manifest_identity":"UNKNOWN"},"execution_authority":"NOT_GRANTED"});
    expect_error(
        port,
        &workspace,
        prepare_action('1', invalid),
        "HANDOFF_INVALID_PROPOSAL",
    );
    expect_error(
        port,
        &workspace,
        prepare_action(
            '1',
            json!({"kind":"receipt","proposal":{"idempotency_key":"2".repeat(32),"proposal_sha256":"3".repeat(64),"kind":"context"},"state":"PREPARED","reason":"NONE"}),
        ),
        "HANDOFF_ORIGINAL_REQUIRED",
    );
    assert_eq!(snapshot(&db), before);
    // 仅测试fixture的human写入，用于制造真实版本冲突；CLI依旧只有Observer凭据。
    let body = json!({"expected_version":1,"editor_json":{"type":"doc","content":[]}}).to_string();
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
    let after_fixture_update = snapshot(&db);
    expect_error(
        port,
        &workspace,
        prepare_action('1', context(&reference)),
        "HANDOFF_REFERENCE_NOT_CURRENT",
    );
    assert_eq!(snapshot(&db), after_fixture_update);
}

#[test]
fn receipts_require_original_identity_freshness_and_consistent_state() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("receipt.sqlite");
    let (workspace, reference, _) = seed(&db);
    let (_host, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let before = snapshot(&db);
    let (success, original) = adapter(port, &workspace, prepare_action('1', context(&reference)));
    assert!(success);
    let action = |value: Value, state: &str, reason: &str| json!({"operation":"prepare_receipt","key":"2".repeat(32),"original":value,"state":state,"reason":reason});
    let mut wrong = original.clone();
    wrong["producer"]["workspace_id"] = json!("0".repeat(32));
    expect_error(
        port,
        &workspace,
        action(wrong, "PREPARED", "NONE"),
        "HANDOFF_IDENTITY_MISMATCH",
    );
    expect_error(
        port,
        &workspace,
        action(original.clone(), "UNKNOWN", "NONE"),
        "HANDOFF_INVALID_PROPOSAL",
    );
    let mut expired = original.clone();
    let now = archeaxis_api::project_observer::now_ms();
    expired["created_at_ms"] = json!(now - 1000);
    expired["expires_at_ms"] = json!(now - 1);
    expect_error(
        port,
        &workspace,
        action(expired.clone(), "PREPARED", "NONE"),
        "HANDOFF_INVALID_PROPOSAL",
    );
    let (success, unknown) = adapter(port, &workspace, action(expired, "UNKNOWN", "UNOBSERVED"));
    assert!(success);
    assert_eq!(unknown["payload"]["state"], "UNKNOWN");
    assert_eq!(unknown["authority"], "PREPARATION_ONLY");
    assert_eq!(snapshot(&db), before);
}

#[test]
fn a_disconnected_core_cannot_prepare_from_a_callers_cached_original() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("disconnect.sqlite");
    let (workspace, reference, _) = seed(&db);
    let (host, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let (success, original) = adapter(port, &workspace, prepare_action('1', context(&reference)));
    assert!(success);
    drop(host);
    let before = snapshot(&db);
    expect_error(
        port,
        &workspace,
        prepare_action('2', context(&reference)),
        "OBSERVER_UNAVAILABLE",
    );
    expect_error(
        port,
        &workspace,
        json!({"operation":"prepare_receipt","key":"2".repeat(32),"original":original,"state":"UNKNOWN","reason":"DISCONNECTED"}),
        "OBSERVER_UNAVAILABLE",
    );
    assert_eq!(snapshot(&db), before);
}

#[test]
fn input_cannot_smuggle_url_body_credentials_or_execution_and_argv_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("strict-input.sqlite");
    let (workspace, reference, _) = seed(&db);
    let (_host, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let before = snapshot(&db);
    for (key, value) in [
        ("url", json!("https://SYNTHETIC_PRIVATE_VALUE.invalid")),
        ("command", json!("SYNTHETIC_PRIVATE_VALUE")),
        ("snapshot", json!({"token":"SYNTHETIC_PRIVATE_VALUE"})),
    ] {
        let mut action = prepare_action('1', context(&reference));
        action[key] = value;
        expect_error(port, &workspace, action, "OBSERVER_INVALID_ADMISSION");
    }
    let mut payload = context(&reference);
    payload["body"] = json!("SYNTHETIC_PRIVATE_VALUE");
    expect_error(
        port,
        &workspace,
        prepare_action('1', payload),
        "OBSERVER_INVALID_ADMISSION",
    );
    let mut payload = context(&reference);
    payload["authorization_scope"] = json!("EXECUTE");
    expect_error(
        port,
        &workspace,
        prepare_action('1', payload),
        "OBSERVER_INVALID_ADMISSION",
    );
    let output = Command::new(env!("CARGO_BIN_EXE_archeaxis-project-observer"))
        .arg("SYNTHETIC_PRIVATE_VALUE")
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert_eq!(
        String::from_utf8(output.stderr).unwrap().trim(),
        "OBSERVER_STDIN_ONLY"
    );
    assert_eq!(snapshot(&db), before);
}

#[test]
fn malformed_auth_and_wrong_token_identity_fail_without_echo_or_writes() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("auth-input.sqlite");
    let (workspace, reference, _) = seed(&db);
    let (_host, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    let before = snapshot(&db);
    let input = json!({"admission":{"port":port,"token":OBSERVER,"producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":INSTANCE}},"action":prepare_action('1',context(&reference))});
    let mut attempts: Vec<(Vec<u8>, &str)> = Vec::new();
    let mut wrong = input.clone();
    wrong["admission"]["token"] = json!("8".repeat(64));
    attempts.push((serde_json::to_vec(&wrong).unwrap(), "OBSERVER_REJECTED"));
    let mut wrong = input.clone();
    wrong["admission"]["consumer"]["instance_id"] = json!("8".repeat(32));
    attempts.push((serde_json::to_vec(&wrong).unwrap(), "OBSERVER_REJECTED"));
    let mut wrong = input.clone();
    wrong["admission"]["producer"]["workspace_id"] = json!("8".repeat(32));
    attempts.push((
        serde_json::to_vec(&wrong).unwrap(),
        "OBSERVER_INVALID_RESPONSE",
    ));
    let mut wrong = input.clone();
    wrong["auth"] = json!({"token":OBSERVER,"secret":"SYNTHETIC_PRIVATE_VALUE"});
    attempts.push((
        serde_json::to_vec(&wrong).unwrap(),
        "OBSERVER_INVALID_ADMISSION",
    ));
    attempts.push((
        format!("{{\"admission\":\"{OBSERVER}\"}}").into_bytes(),
        "OBSERVER_INVALID_ADMISSION",
    ));
    attempts.push((
        b"SYNTHETIC_PRIVATE_VALUE".repeat(3200),
        "OBSERVER_INVALID_ADMISSION",
    ));
    for (raw, code) in attempts {
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
        // 超限输入允许CLI提前关管道；不能因测试writer的BrokenPipe掩盖产品结果。
        let _ = child.stdin.take().unwrap().write_all(&raw);
        let output = child.wait_with_output().unwrap();
        assert!(!output.status.success());
        let stdout = String::from_utf8(output.stdout).unwrap();
        let stderr = String::from_utf8(output.stderr).unwrap();
        for secret in [HUMAN, MACHINE, OBSERVER, "SYNTHETIC_PRIVATE_VALUE"] {
            assert!(!stdout.contains(secret) && !stderr.contains(secret));
        }
        assert!(stderr.is_empty());
        assert_eq!(
            serde_json::from_str::<Value>(&stdout).unwrap(),
            json!({"schema":"archeaxis.project-observer-error/v1","code":code})
        );
    }
    assert_eq!(snapshot(&db), before);
}
