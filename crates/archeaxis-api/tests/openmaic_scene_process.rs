//! Reopen a persisted OpenMAIC scene v2 candidate through a real Core process.
//!
//! The candidate is seeded with the domain writers exactly like the in-process
//! runtime test, then the actual `archeaxis-api` binary serves the human read-back
//! over HTTP. The process is restarted on the same workspace and must return the
//! same candidate without invoking a worker, while a machine credential is refused.
//! No Node, model or network is used.
use archeaxis_domain::course::{self, OpenMaicPreparation};
use archeaxis_domain::document;
use archeaxis_store_sqlite::init_workspace;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::time::{Duration, Instant};

const ROUTE: &str = "/api/v1/courses/openmaic/scenes";
const LAUNCH_TOKEN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const MACHINE_TOKEN: &str = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn canonicalize(path: PathBuf) -> PathBuf {
    path.canonicalize().expect("pinned worker present")
}

/// Strip the Windows verbatim prefix that `canonicalize` returns.
fn plain(path: PathBuf) -> PathBuf {
    #[cfg(windows)]
    {
        let text = path.to_string_lossy();
        if let Some(rest) = text.strip_prefix(r"\\?\") {
            return PathBuf::from(rest);
        }
    }
    path
}

fn request(source: &Value) -> Value {
    json!({"schema":"archeaxis.openmaic-scene-build/v1", "request_id":"req_1", "attempt":1,
        "source":{"document_id":source["document_id"],"version":source["version"],"content_sha256":source["content_sha256"]},
        "stage_id":"stage_1","scene_id":"scene_1", "outline":{"id":"outline_1","type":"quiz",
        "title":"Synthetic title","description":"Synthetic description","keyPoints":[],"order":0},
        "content":{"questions":[{"id":"q1","question":"Synthetic?","answer":"SYNTHETIC_PRIVATE_ANSWER"}]}, "actions":[]})
}

fn synthetic_worker(request: &Value) -> Value {
    let mut frame = serde_json::to_vec(request).unwrap();
    frame.push(b'\n');
    json!({"schema":"archeaxis.openmaic-scene-build-result/v1", "status":"CANDIDATE",
        "request_id":request["request_id"],"attempt":request["attempt"],"input_sha256":format!("{:x}", Sha256::digest(&frame)),
        "source":request["source"],"source_binding":"client_declared_unverified","provider":"openmaic",
        "provider_version":"1.3.0","generation_version":"0.3.28","authority_effect":"candidate_only",
        "model_call":"NOT_INVOKED","canonical_bindings_verified":false,"human_review_required":true,
        "active_content_executed":false,"rendering_authorized":false,"retry_bytes_stable":false,
        "scene":{"id":request["scene_id"],"stageId":request["stage_id"],"outlineId":request["outline"]["id"],
            "type":"quiz","title":request["outline"]["title"],"order":request["outline"]["order"],
            "content":{"type":"quiz","questions":request["content"]["questions"]},"actions":request["actions"]}})
}

/// Seed the source document and one committed scene candidate with the same domain
/// writers the in-process runtime test uses. The Core must not be running: it takes
/// the workspace OS lock while it serves.
fn seed(workspace: &Path) -> Value {
    let mut conn = init_workspace(workspace.to_str().unwrap()).unwrap();
    let source = document::create_optional(
        &mut conn,
        None,
        None,
        "synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let request = request(&source);
    let pending = match course::prepare_openmaic_scene(&mut conn, "client_1", &request).unwrap() {
        OpenMaicPreparation::Pending(value) => value,
        _ => panic!("a fresh request must not exist"),
    };
    course::commit_openmaic_scene(
        &mut conn,
        "client_1",
        &request,
        &pending,
        &synthetic_worker(&request),
    )
    .unwrap();
    request
}

struct Core {
    child: Child,
    port: u16,
}

impl Core {
    fn launch(
        binary: &Path,
        workspace: &Path,
        staging: &Path,
        node: Option<(&Path, &str, &Path)>,
    ) -> Self {
        let openmaic_node = match node {
            Some((executable, sha256, script)) => json!({
                "executable": executable,
                "executable_sha256": sha256,
                "script": script
            }),
            None => Value::Null,
        };
        let launch = json!({
            "launch_token": LAUNCH_TOKEN,
            "session_id": "c".repeat(32),
            "actor": "human",
            "protocol": "archeaxis.desktop-launch/v2",
            "machine_token": MACHINE_TOKEN,
            "text_worker": {
                "python": std::env::current_exe().unwrap(),
                "script": std::env::current_exe().unwrap(),
                "staging": staging,
                "routes": []
            },
            "openmaic_node_worker": openmaic_node,
            "document_check_config": null,
            "document_check_config_error": null
        });
        let mut child = Command::new(binary)
            .arg(workspace)
            .arg("0")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .expect("spawn Core");
        child
            .stdin
            .as_mut()
            .unwrap()
            .write_all(launch.to_string().as_bytes())
            .expect("write launch document");
        drop(child.stdin.take());
        let (sender, receiver) = mpsc::channel();
        let stdout = child.stdout.take().unwrap();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if sender.send(line).is_err() {
                    return;
                }
            }
        });
        let stderr = child.stderr.take().unwrap();
        std::thread::spawn(move || {
            let _ = std::io::copy(&mut BufReader::new(stderr), &mut std::io::sink());
        });
        let deadline = Instant::now() + Duration::from_secs(60);
        while Instant::now() < deadline {
            match receiver.recv_timeout(Duration::from_millis(500)) {
                Ok(line) => {
                    let port = line
                        .strip_prefix("archeaxis-api ready on http://")
                        .and_then(|url| url.rsplit(':').next())
                        .and_then(|port| port.parse().ok());
                    if let Some(port) = port {
                        return Self { child, port };
                    }
                }
                Err(mpsc::RecvTimeoutError::Timeout) => {
                    if child.try_wait().ok().flatten().is_some() {
                        panic!("Core exited before becoming ready");
                    }
                }
                Err(mpsc::RecvTimeoutError::Disconnected) => panic!("Core closed stdout"),
            }
        }
        let _ = child.kill();
        panic!("Core did not become ready within 60s");
    }

    fn call(&self, token: &str, body: &Value) -> (u16, Value) {
        let payload = body.to_string();
        let request = format!(
            "POST {ROUTE} HTTP/1.1\r\nHost: 127.0.0.1\r\ncontent-type: application/json\r\n\
             x-archeaxis-launch-token: {token}\r\ncontent-length: {len}\r\n\
             connection: close\r\n\r\n{payload}",
            len = payload.len()
        );
        let mut stream = TcpStream::connect(("127.0.0.1", self.port)).expect("connect Core");
        stream
            .set_read_timeout(Some(Duration::from_secs(90)))
            .unwrap();
        stream
            .set_write_timeout(Some(Duration::from_secs(90)))
            .unwrap();
        stream.write_all(request.as_bytes()).unwrap();
        let mut response = Vec::new();
        stream.read_to_end(&mut response).unwrap();
        let split = response
            .windows(4)
            .position(|window| window == b"\r\n\r\n")
            .expect("response headers");
        let head = String::from_utf8_lossy(&response[..split]).to_string();
        let status: u16 = head
            .lines()
            .next()
            .and_then(|line| line.split_whitespace().nth(1))
            .and_then(|code| code.parse().ok())
            .expect("response status");
        let body = serde_json::from_slice(&response[split + 4..]).unwrap_or(Value::Null);
        (status, body)
    }

    fn stop(mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl Drop for Core {
    /// A panicking assertion must not leave the Core process alive holding inherited
    /// handles; every test exit path kills and reaps it.
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn assert_candidate(body: &Value) {
    assert_eq!(body["worker_invoked"], false, "{body}");
    assert_eq!(
        body["contract_version"],
        "archeaxis.openmaic-scene-document/v2"
    );
    assert_eq!(body["rendering_authorized"], false);
    assert_eq!(body["candidate_document_status"], "current");
    assert_eq!(body["source_snapshot_status"], "current");
    assert_eq!(body["projection"]["derived_by"], "core");
    assert_eq!(
        body["projection"]["report"]["omitted"],
        json!(["outline.description", "outline.keyPoints"])
    );
    assert_eq!(body["render"]["status"], "RECORDED");
    assert_eq!(body["render"]["report"]["playable"], false);
    // The human read-back keeps the candidate content for review; it must not claim
    // answer secrecy. The machine denial is the response that must stay free of it.
    assert_eq!(body["answer_secrecy"], "not_established");
}

#[test]
fn a_persisted_openmaic_scene_is_served_by_a_real_process_across_restart() {
    let binary = PathBuf::from(env!("CARGO_BIN_EXE_archeaxis-api"));
    assert!(binary.is_file(), "built Core binary missing: {binary:?}");
    let dir = tempfile::tempdir().unwrap();
    let workspace = dir.path().join("workspace.sqlite");
    let staging = dir.path().join("staging");
    std::fs::create_dir_all(&staging).unwrap();
    let request = seed(&workspace);
    let body = json!({"create_request_id":"client_1","request":request});

    let core = Core::launch(&binary, &workspace, &staging, None);
    let (status, denied) = core.call(MACHINE_TOKEN, &body);
    assert_eq!(status, 403, "{denied}");
    assert!(denied["refusal"].is_null());
    assert!(!denied.to_string().contains("SYNTHETIC_PRIVATE_ANSWER"));
    let (status, first) = core.call(LAUNCH_TOKEN, &body);
    assert_eq!(status, 200, "{first}");
    assert_candidate(&first);
    core.stop();

    let core = Core::launch(&binary, &workspace, &staging, None);
    let (status, reopened) = core.call(LAUNCH_TOKEN, &body);
    assert_eq!(status, 200, "{reopened}");
    assert_candidate(&reopened);
    assert_eq!(reopened["document"], first["document"]);
    core.stop();

    assert!(workspace.is_file());
}

fn slide_request(source: &Value, create_request_id: &str, scene_id: &str) -> Value {
    json!({"create_request_id": create_request_id, "request": {
        "schema":"archeaxis.openmaic-scene-build/v1", "request_id": format!("req_{scene_id}"),
        "attempt":1,
        "source":{"document_id":source["document_id"],"version":source["version"],
            "content_sha256":source["content_sha256"]},
        "stage_id":"stage_1","scene_id":scene_id,
        "outline":{"id":format!("outline_{scene_id}"),"type":"slide",
            "title":"Synthetic title","description":"","keyPoints":[],"order":0},
        "content":{"elements":[{"id":"text1","type":"text","content":"<p>synthetic</p>"}],
            "background":{"type":"solid","color":"#ffffff"}},
        "actions":[]}})
}

/// Only the source document is seeded; the Node worker must create the scenes.
fn seed_source(workspace: &Path) -> Value {
    let mut conn = init_workspace(workspace.to_str().unwrap()).unwrap();
    document::create_optional(
        &mut conn,
        None,
        None,
        "synthetic material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap()
}

/// The real process must build two independent scenes through the pinned Node
/// worker, and a restart without Node must read both persisted candidates back.
#[test]
fn two_scenes_build_with_node_and_reopen_without_it() {
    let node = match std::env::var_os("ARCHEAXIS_TEST_NODE") {
        Some(value) => PathBuf::from(value),
        None => {
            eprintln!("skipping: ARCHEAXIS_TEST_NODE not set; this skip is not evidence");
            return;
        }
    };
    let sha = match std::env::var("ARCHEAXIS_TEST_NODE_SHA256") {
        Ok(value) => value,
        Err(_) => {
            eprintln!("skipping: ARCHEAXIS_TEST_NODE_SHA256 not set; this skip is not evidence");
            return;
        }
    };
    // The launch profile refuses paths carrying parent components, so resolve the
    // repository-relative script before handing it to Core.
    // canonicalize() yields a verbatim `\\?\D:\...` path on Windows, which the
    // launch profile refuses; hand Core the plain absolute form instead.
    let script = plain(canonicalize(
        repo().join("services/learning-providers/openmaic/scene-build-worker.mjs"),
    ));
    assert!(script.is_file(), "pinned worker missing: {script:?}");
    let binary = PathBuf::from(env!("CARGO_BIN_EXE_archeaxis-api"));
    assert!(binary.is_file(), "built Core binary missing: {binary:?}");
    let dir = tempfile::tempdir().unwrap();
    let workspace = dir.path().join("workspace.sqlite");
    let staging = dir.path().join("staging");
    std::fs::create_dir_all(&staging).unwrap();
    let source = seed_source(&workspace);
    let first_body = slide_request(&source, "node_a", "scene_a");
    let second_body = slide_request(&source, "node_b", "scene_b");

    let core = Core::launch(&binary, &workspace, &staging, Some((&node, &sha, &script)));
    let (status, first) = core.call(LAUNCH_TOKEN, &first_body);
    assert_eq!(status, 200, "{first}");
    assert_eq!(first["worker_invoked"], true, "{first}");
    let (status, second) = core.call(LAUNCH_TOKEN, &second_body);
    assert_eq!(status, 200, "{second}");
    assert_eq!(second["worker_invoked"], true, "{second}");
    assert_ne!(
        first["document"]["document_id"], second["document"]["document_id"],
        "two scenes must persist as independent documents"
    );
    core.stop();

    let core = Core::launch(&binary, &workspace, &staging, None);
    let (status, first_again) = core.call(LAUNCH_TOKEN, &first_body);
    assert_eq!(status, 200, "{first_again}");
    assert_eq!(first_again["worker_invoked"], false, "{first_again}");
    assert_eq!(first_again["document"], first["document"]);
    let (status, second_again) = core.call(LAUNCH_TOKEN, &second_body);
    assert_eq!(status, 200, "{second_again}");
    assert_eq!(second_again["worker_invoked"], false, "{second_again}");
    assert_eq!(second_again["document"], second["document"]);
    core.stop();
}
