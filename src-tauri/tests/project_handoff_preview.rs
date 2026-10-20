//! 本仓真实Core进程+正式native有限桥，合成资料；没有外部产品/OS URI/安装资格。
#[path = "../src/core_bridge.rs"]
mod core_bridge;
use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Write},
    process::{Child, Command, Stdio},
    sync::mpsc,
    time::Duration,
};
const HUMAN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
struct Owned(Child);
impl Drop for Owned {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}
fn start(db: &std::path::Path) -> (Owned, u16) {
    // 必须由canonical runner指明刚构建的owned Core，缺失/错误为失败，绝不skip或使用用户服务。
    let binary = std::env::var_os("BE10_PREVIEW_CORE")
        .expect("BE10_PREVIEW_CORE owned candidate executable required");
    let mut command = Command::new(binary);
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
    writeln!(owned.0.stdin.take().unwrap(),"{}",json!({"protocol":"archeaxis.desktop-launch/v2","actor":"human","launch_token":HUMAN,"machine_token":"b".repeat(64),"session_id":"c".repeat(32)})).unwrap();
    let stdout = owned.0.stdout.take().unwrap();
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            let line = line.unwrap();
            if let Some(port) = line.strip_prefix("archeaxis-api ready on http://127.0.0.1:") {
                let _ = tx.send(port.parse::<u16>().unwrap());
                return;
            }
        }
    });
    let port = rx.recv_timeout(Duration::from_secs(10)).unwrap();
    (owned, port)
}
fn call(port: u16, operation: &str, payload: Value) -> core_bridge::Reply {
    let request: core_bridge::Request =
        serde_json::from_value(json!({"operation":operation,"payload":payload})).unwrap();
    core_bridge::execute(port, HUMAN, request).unwrap()
}
#[test]
fn actual_native_finite_preview_consumes_owned_core_metadata_and_disconnect_never_succeeds() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("native-synthetic.sqlite");
    let (core, port) = start(&db);
    let workspace = call(port, "ui_state_read", json!({})).body["workspace_id"]
        .as_str()
        .unwrap()
        .to_owned();
    let body_text = format!("PRIVATE NATIVE BODY{}", "中".repeat(24_000));
    let document = call(
        port,
        "document_create",
        json!({"body":{"create_request_id":"synthetic-preview-create","source_id":null,"source_revision":null,"title":"PRIVATE NATIVE TITLE","editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":body_text}]}]}}}),
    );
    assert!(matches!(document.status, 200 | 201));
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_millis() as u64;
    let proposal = json!({"schema":"archeaxis.project-handoff/v1","protocol":"archeaxis.project-observer/v1","idempotency_key":"1".repeat(32),"producer":{"namespace":"archeaxis","workspace_id":workspace,"restore_epoch":"initial"},"consumer":{"namespace":"work-lab","instance_id":"2".repeat(32)},"created_at_ms":now,"expires_at_ms":now+30_000,"authority":"PREPARATION_ONLY","payload":{"kind":"context","source":{"reference":{"document_id":document.body["document_id"],"version":document.body["version"],"content_sha256":document.body["content_sha256"]},"selection":{"kind":"whole_object"},"selection_qualification":"UNVERIFIED"},"purpose":"research","authorization_scope":"REFERENCE_METADATA_ONLY"}});
    let reply = call(port, "project_handoff_preview", json!({"body":proposal}));
    assert_eq!(reply.status, 200);
    assert_eq!(reply.body["proposal"], proposal);
    assert_eq!(reply.body["reference_state"], "CURRENT");
    assert_eq!(reply.body["source_authentication"], "UNVERIFIED");
    assert_eq!(reply.body["navigation"], "UNAVAILABLE");
    assert_eq!(reply.body["grants_execution"], false);
    for forbidden in [
        "PRIVATE NATIVE TITLE",
        "PRIVATE NATIVE BODY",
        HUMAN,
        db.to_str().unwrap(),
        "editor_json",
    ] {
        assert!(!reply.body.to_string().contains(forbidden));
    }
    // 正文有限桥须支持超过metadata 64KiB的固定正文，并且不返回当前标题。
    let read = call(port, "project_handoff_snapshot", json!({"body":proposal}));
    assert_eq!(read.status, 200);
    assert!(read.body.to_string().len() > 65_536);
    assert_eq!(read.body["proposal_sha256"], reply.body["proposal_sha256"]);
    assert_eq!(
        read.body["reference"],
        proposal["payload"]["source"]["reference"]
    );
    assert_eq!(
        read.body["editor_json"]["content"][0]["content"][0]["text"],
        body_text
    );
    assert!(read.body.get("title").is_none());
    let changed = call(
        port,
        "document_draft",
        json!({"document_id":document.body["document_id"],"body":{"expected_version":1,"editor_json":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"NEW BODY NEVER SUBSTITUTE"}]}]}}}),
    );
    assert_eq!(changed.status, 200);
    let old = call(port, "project_handoff_snapshot", json!({"body":proposal}));
    assert_eq!(old.status, 200);
    assert_eq!(old.body["reference_state"], "STALE");
    assert_eq!(old.body["editor_json"], read.body["editor_json"]);
    for payload in [
        json!({"body":proposal,"url":"https://invalid.test"}),
        json!({"body":proposal,"token":HUMAN}),
        json!({"body":[]}),
        json!({}),
    ] {
        let request = serde_json::from_value(
            json!({"operation":"project_handoff_preview","payload":payload}),
        )
        .unwrap();
        assert!(
            matches!(core_bridge::execute(0,HUMAN,request),Err(code) if code=="CORE_COMMAND_PREVIEW_PAYLOAD_INVALID")
        );
    }
    let request=serde_json::from_value(json!({"operation":"project_handoff_preview","payload":{"body":{"oversize":"x".repeat(65_536)}}})).unwrap();
    assert!(
        matches!(core_bridge::execute(0,HUMAN,request),Err(code) if code=="CORE_COMMAND_BODY_TOO_LARGE")
    );
    drop(core);
    let request = serde_json::from_value(
        json!({"operation":"project_handoff_preview","payload":{"body":proposal}}),
    )
    .unwrap();
    assert!(
        matches!(core_bridge::execute(port,HUMAN,request),Err(code) if code=="CORE_TRANSPORT_FAILED")
    );
    let request = serde_json::from_value(
        json!({"operation":"project_handoff_snapshot","payload":{"body":proposal}}),
    )
    .unwrap();
    assert!(
        matches!(core_bridge::execute(port,HUMAN,request),Err(code) if code=="CORE_TRANSPORT_FAILED")
    );
}
