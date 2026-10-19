//! 自建合成资料、真实 Core/HTTP/消费者进程；不代表外部产品或安装资格。
use archeaxis_contracts::project_handoff_preview::Preview;
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

fn proposal(workspace: &str, reference: &ObjectReference) -> Value {
    let now = archeaxis_api::project_observer::now_ms();
    json!({"schema":"archeaxis.project-handoff/v1","protocol":contract::PROTOCOL,
        "idempotency_key":"1".repeat(32),"producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},
        "consumer":{"namespace":"work-lab","instance_id":INSTANCE},"created_at_ms":now,"expires_at_ms":now+30_000,
        "authority":"PREPARATION_ONLY","payload":{"kind":"context","source":{"reference":reference,"selection":{"kind":"whole_object"},"selection_qualification":"UNVERIFIED"},"purpose":"research","authorization_scope":"REFERENCE_METADATA_ONLY"}})
}
fn preview(port: u16, token: &str, value: &Value) -> (u16, Value) {
    let (status, body) = request(
        port,
        token,
        "POST",
        "/api/v1/project-handoff/preview",
        "Content-Type: application/json\r\n",
        &value.to_string(),
    );
    let value: Value = serde_json::from_str(&body).unwrap();
    for forbidden in [
        "private title",
        "PRIVATE BODY",
        HUMAN,
        MACHINE,
        OBSERVER,
        "editor_json",
        "launch_token",
    ] {
        assert!(!body.contains(forbidden));
    }
    (status, value)
}
fn setup() -> (
    tempfile::TempDir,
    std::path::PathBuf,
    String,
    ObjectReference,
    Owned,
    u16,
) {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("synthetic.sqlite");
    let (workspace, reference, _) = seed(&db);
    let (owned, port) = start(
        &db,
        launch(json!([grant(&workspace, &reference.document_id)])),
    );
    (dir, db, workspace, reference, owned, port)
}

fn snapshot_reply(port: u16, token: &str, value: &Value) -> (u16, Value) {
    let (status, body) = request(
        port,
        token,
        "POST",
        "/api/v1/project-handoff/snapshot",
        "Content-Type: application/json\r\n",
        &value.to_string(),
    );
    (status, serde_json::from_str(&body).unwrap())
}

#[test]
fn human_snapshot_is_fixed_raw_hash_checked_and_reads_no_unhashed_projection_or_title() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let mut conn = rusqlite::Connection::open(&db).unwrap();
    // 合成负例：独立projection/blocks及current标题不属于editor原字节身份。
    conn.execute("UPDATE document_versions SET text_projection='UNHASHED WRONG PROJECTION' WHERE document_id=?1", [&reference.document_id]).unwrap();
    conn.execute(
        "UPDATE document_blocks SET text_projection='UNHASHED WRONG BLOCK' WHERE document_id=?1",
        [&reference.document_id],
    )
    .unwrap();
    let input = proposal(&workspace, &reference);
    let before = snapshot(&db);
    let (status, body) = snapshot_reply(port, HUMAN, &input);
    assert_eq!(status, 200);
    let decoded: archeaxis_contracts::project_handoff_preview::Snapshot =
        serde_json::from_value(body.clone()).unwrap();
    assert!(decoded.valid(archeaxis_api::project_observer::now_ms()));
    assert_eq!(body["reference"], serde_json::to_value(&reference).unwrap());
    assert_eq!(body["reference_state"], "CURRENT");
    assert_eq!(body["scope"], "LOCAL_HUMAN_READ_ONLY");
    assert!(
        body["editor_json"]
            .to_string()
            .contains("SYNTHETIC PRIVATE BODY")
    );
    for bad in [
        "UNHASHED WRONG",
        "private title",
        "source_id",
        "text_projection",
        "blocks",
        HUMAN,
        OBSERVER,
    ] {
        assert!(!body.to_string().contains(bad));
    }
    assert_eq!(before, snapshot(&db));
    // 保存新版本由fixture执行，历史snapshot必须仍回原正文，不读v2或当前header。
    archeaxis_domain::document::save(&mut conn,&reference.document_id,1,json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"NEW VERSION NEVER SUBSTITUTE"}]}]})).unwrap();
    let before = snapshot(&db);
    let (status, stale) = snapshot_reply(port, HUMAN, &input);
    assert_eq!(status, 200);
    assert_eq!(stale["reference_state"], "STALE");
    assert_eq!(body["editor_json"], stale["editor_json"]);
    assert_eq!(before, snapshot(&db));
}

#[test]
fn snapshot_denies_observer_machine_expiry_bad_reference_and_private_input_without_writes() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let input = proposal(&workspace, &reference);
    let before = snapshot(&db);
    for token in [MACHINE, OBSERVER, "invalid"] {
        assert!(matches!(snapshot_reply(port, token, &input).0, 401 | 403));
    }
    for (field, value, status) in [
        ("document_id", json!("missing_document"), 404),
        ("version", json!(999), 404),
        ("content_sha256", json!("f".repeat(64)), 409),
    ] {
        let mut altered = input.clone();
        altered["payload"]["source"]["reference"][field] = value;
        let (actual, body) = snapshot_reply(port, HUMAN, &altered);
        assert_eq!(actual, status);
        assert!(!body.to_string().contains("PRIVATE BODY"));
    }
    for field in ["workspace_id", "restore_epoch"] {
        let mut v = input.clone();
        v["producer"][field] = json!("f".repeat(32));
        assert_eq!(snapshot_reply(port, HUMAN, &v).0, 409);
    }
    let mut expired = input.clone();
    expired["created_at_ms"] = json!(1);
    expired["expires_at_ms"] = json!(2);
    assert_eq!(snapshot_reply(port, HUMAN, &expired).0, 400);
    let mut private = input.clone();
    private["body"] = json!("not permitted");
    assert_eq!(snapshot_reply(port, HUMAN, &private).0, 400);
    assert_eq!(
        request(
            port,
            HUMAN,
            "POST",
            "/api/v1/project-handoff/snapshot?url=invalid",
            "Content-Type: application/json\r\n",
            &input.to_string()
        )
        .0,
        400
    );
    assert_eq!(
        request(
            port,
            HUMAN,
            "POST",
            "/api/v1/project-handoff/snapshot",
            "Content-Type: application/json\r\n",
            &" ".repeat(65_537)
        )
        .0,
        413
    );
    assert_eq!(before, snapshot(&db));
}

#[test]
fn snapshot_rechecks_restore_after_preview_and_rejects_corrupted_stored_editor() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let input = proposal(&workspace, &reference);
    assert_eq!(preview(port, HUMAN, &input).0, 200);
    let mut conn = rusqlite::Connection::open(&db).unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    let before = snapshot(&db);
    assert_eq!(snapshot_reply(port, HUMAN, &input).0, 409);
    assert_eq!(before, snapshot(&db));
    drop(_core);
    // 新建独立合成fixture，不将恢复epoch重设为旧值。
    let (_dir, db, workspace, reference, _core, port) = setup();
    let conn = rusqlite::Connection::open(&db).unwrap();
    conn.execute(
        "UPDATE document_versions SET editor_json='{}' WHERE document_id=?1 AND version=1",
        [&reference.document_id],
    )
    .unwrap();
    let before = snapshot(&db);
    let (status, body) = snapshot_reply(port, HUMAN, &proposal(&workspace, &reference));
    assert_eq!(status, 409);
    assert_eq!(body["code"], "HANDOFF_SNAPSHOT_CONTENT_INVALID");
    assert_eq!(before, snapshot(&db));
}

#[test]
fn snapshot_rejects_oversized_stored_body_without_truncation_or_business_writes() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let conn = rusqlite::Connection::open(&db).unwrap();
    conn.execute(
        "UPDATE document_versions SET editor_json=?1 WHERE document_id=?2 AND version=1",
        rusqlite::params!["x".repeat(8 * 1024 * 1024 + 1), reference.document_id],
    )
    .unwrap();
    let before = snapshot(&db);
    let (status, body) = snapshot_reply(port, HUMAN, &proposal(&workspace, &reference));
    assert_eq!(status, 413);
    assert_eq!(body["code"], "HANDOFF_SNAPSHOT_TOO_LARGE");
    assert_eq!(before, snapshot(&db));
}
#[test]
fn human_preview_reads_real_fixed_metadata_and_leaves_all_business_tables_unchanged() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let before = snapshot(&db);
    for purpose in ["learning", "research", "conversion", "visualization"] {
        for selection in [
            json!({"kind":"whole_object"}),
            json!({"kind":"text_range","block_id":"unverified_block","start_utf16":1,"end_utf16":3}),
            json!({"kind":"page_range","first_page":1,"last_page":2}),
            json!({"kind":"time_range","start_ms":1,"end_ms":2}),
        ] {
            let mut input = proposal(&workspace, &reference);
            input["payload"]["purpose"] = json!(purpose);
            input["payload"]["source"]["selection"] = selection;
            let (status, value) = preview(port, HUMAN, &input);
            assert_eq!(status, 200);
            let decoded: Preview = serde_json::from_value(value.clone()).unwrap();
            assert!(decoded.valid(archeaxis_api::project_observer::now_ms()));
            assert_eq!(value["proposal"], input);
            assert_eq!(value["reference_state"], "CURRENT");
            assert_eq!(value["source_authentication"], "UNVERIFIED");
            assert_eq!(value["navigation"], "UNAVAILABLE");
            assert_eq!(
                value["proposal"]["payload"]["source"]["selection_qualification"],
                "UNVERIFIED"
            );
            assert_eq!(value["grants_execution"], false);
            assert_eq!(value["grants_knowledge_acceptance"], false);
            let original = serde_json::from_value(input).unwrap();
            assert_eq!(
                value["proposal_sha256"],
                archeaxis_api::project_handoff::proposal_fingerprint(&original).unwrap()
            );
        }
    }
    assert_eq!(before, snapshot(&db));
}
#[test]
fn preview_rejects_machine_observer_credentials_and_keeps_local_api_independent() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let before = snapshot(&db);
    let input = proposal(&workspace, &reference);
    for token in [MACHINE, OBSERVER, "invalid"] {
        let (status, _) = preview(port, token, &input);
        assert!(matches!(status, 401 | 403));
    }
    assert_eq!(
        request(port, HUMAN, "GET", "/api/v1/documents", "", "").0,
        200
    );
    assert_eq!(before, snapshot(&db));
    // 不配置observer grant也可独立执行本地human预览；没有外部服务依赖。
    drop(_core);
    let (_core, port) = start(
        &db,
        json!({"protocol":"archeaxis.desktop-launch/v2","actor":"human","launch_token":HUMAN,"machine_token":MACHINE,"session_id":"e".repeat(32)}),
    );
    assert_eq!(preview(port, HUMAN, &input).0, 200);
}
#[test]
fn workspace_restore_epoch_expiry_and_future_context_fail_closed_without_writes() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let before = snapshot(&db);
    for field in ["workspace_id", "restore_epoch"] {
        let mut input = proposal(&workspace, &reference);
        input["producer"][field] = json!("f".repeat(32));
        let (status, value) = preview(port, HUMAN, &input);
        assert_eq!(status, 409);
        assert_eq!(value["code"], "HANDOFF_PREVIEW_IDENTITY_MISMATCH");
    }
    for future in [false, true] {
        let mut input = proposal(&workspace, &reference);
        let now = archeaxis_api::project_observer::now_ms();
        input["created_at_ms"] = json!(if future { now + 30_000 } else { now - 60_000 });
        input["expires_at_ms"] = json!(if future { now + 60_000 } else { now - 30_000 });
        assert_eq!(preview(port, HUMAN, &input).0, 400);
    }
    assert_eq!(before, snapshot(&db));
    // 只修改自建合成workspace的恢复fence作为真实失效负例，预览本身仍只读。
    let conn = rusqlite::Connection::open(&db).unwrap();
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",rusqlite::params![archeaxis_store_sqlite::authorization_fence::KEY,json!({"schema":archeaxis_store_sqlite::authorization_fence::SCHEMA,"epoch":"2".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    drop(conn);
    let after_restore = snapshot(&db);
    let input = proposal(&workspace, &reference);
    assert_eq!(preview(port, HUMAN, &input).0, 409);
    assert_eq!(after_restore, snapshot(&db));
}
#[test]
fn stale_hash_version_missing_and_repeated_preview_are_explicit_and_read_only() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let before = snapshot(&db);
    let input = proposal(&workspace, &reference);
    for _ in 0..2 {
        assert_eq!(preview(port, HUMAN, &input).1["reference_state"], "CURRENT");
    }
    for field in ["version", "content_sha256", "document_id"] {
        let mut value = input.clone();
        value["payload"]["source"]["reference"][field] = match field {
            "version" => json!(2),
            "content_sha256" => json!("0".repeat(64)),
            _ => json!("missing"),
        };
        let (status, out) = preview(port, HUMAN, &value);
        assert_eq!(status, 200);
        assert_eq!(
            out["reference_state"],
            if field == "document_id" {
                "NOT_FOUND"
            } else {
                "STALE"
            }
        );
        assert_eq!(out["proposal"], value);
    }
    assert_eq!(before, snapshot(&db));
}
#[test]
fn untrusted_json_fields_non_context_query_and_oversize_never_echo_input() {
    let (_dir, db, workspace, reference, _core, port) = setup();
    let before = snapshot(&db);
    let original = proposal(&workspace, &reference);
    let mut unknown = original.clone();
    unknown["token"] = json!("PRIVATE BODY NEVER ECHO");
    assert_eq!(preview(port, HUMAN, &unknown).0, 400);
    let cases: Value = serde_json::from_str(include_str!(
        "../../../packages/contracts/v2/project-handoff.cases.json"
    ))
    .unwrap();
    let valid_task = cases
        .as_array()
        .unwrap()
        .iter()
        .find(|case| case["name"] == "valid_task")
        .unwrap();
    let mut candidate = original.clone();
    candidate["payload"] = valid_task["value"]["payload"].clone();
    let task: archeaxis_contracts::project_handoff::Handoff =
        serde_json::from_value(candidate.clone()).unwrap();
    assert!(task.valid(archeaxis_api::project_observer::now_ms()));
    assert_eq!(preview(port, HUMAN, &candidate).0, 400);
    for text in [
        original.to_string().replacen(
            "\"schema\":",
            "\"schema\":\"PRIVATE BODY NEVER ECHO\",\"schema\":",
            1,
        ),
        "{".into(),
    ] {
        let (status, body) = request(
            port,
            HUMAN,
            "POST",
            "/api/v1/project-handoff/preview",
            "Content-Type: application/json\r\n",
            &text,
        );
        assert_eq!(status, 400);
        assert!(!body.contains("PRIVATE BODY"));
        assert_eq!(
            serde_json::from_str::<Value>(&body).unwrap()["code"],
            "HANDOFF_PREVIEW_INVALID_INPUT"
        );
    }
    assert_eq!(
        request(
            port,
            HUMAN,
            "POST",
            "/api/v1/project-handoff/preview?url=https://invalid.test",
            "Content-Type: application/json\r\n",
            &original.to_string()
        )
        .0,
        400
    );
    assert_eq!(
        request(
            port,
            HUMAN,
            "POST",
            "/api/v1/project-handoff/preview",
            "Content-Type: application/json\r\n",
            &" ".repeat(65_537)
        )
        .0,
        413
    );
    assert_eq!(before, snapshot(&db));
}
