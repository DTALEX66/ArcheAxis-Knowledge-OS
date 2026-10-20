//! Bounded, input-free observation of the existing worker hello contract.
use super::*;
use std::io::{BufRead, BufReader};

pub(super) fn probe(
    staging: &Path,
    python: &Path,
    worker: &Path,
    capability: &str,
    allow_site: bool,
) -> serde_json::Value {
    let checked_at = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or_default();
    let derived_protocol = derived::supported(capability);
    let public_research_protocol = capability == "research.public";
    let observation = if !file_usable(worker) {
        (
            "worker_missing",
            Err("worker file does not exist".to_string()),
        )
    } else if !file_usable(python) {
        (
            "interpreter_missing",
            Err("interpreter file does not exist".to_string()),
        )
    } else {
        let checked = if public_research_protocol {
            public_research::health(staging, python, worker, allow_site)
        } else if derived_protocol {
            derived::run(
                staging,
                python,
                worker,
                allow_site,
                None,
                Duration::from_secs(2),
            )
            .and_then(|value| {
                let doc = &value["document"];
                if value["exit_code"] != 0
                    || doc["schema"] != "archeaxis.derived-worker-hello/v1"
                    || doc["capability"] != capability
                    || doc["version"] != 1
                {
                    return Err("incompatible derived worker hello".into());
                }
                Ok(serde_json::json!({"worker_identity":capability,"runtime_dependency":null}))
            })
        } else {
            handshake(staging, python, worker, capability, allow_site)
        };
        match checked {
            Ok(identity) => ("handshake_ready", Ok(identity)),
            Err(reason) => (
                match reason.as_str() {
                    "PDF_DEPENDENCY_MISSING" => "dependency_missing",
                    "PDF_DEPENDENCY_VERSION_UNKNOWN" => "dependency_version_unknown",
                    "PDF_DEPENDENCY_IMPORT_FAILED" => "dependency_import_failed",
                    "PDF_DEPENDENCY_UNOBSERVED" => "dependency_unobserved",
                    _ => "handshake_failed",
                },
                Err(reason),
            ),
        }
    };
    serde_json::json!({
        "status":observation.0, "checked_at_unix_ms":checked_at,
        "worker_identity":observation.1.as_ref().ok().map(|v| &v["worker_identity"]),
        "runtime_dependency":observation.1.as_ref().ok().map(|v| &v["runtime_dependency"]),
        "reason":observation.1.as_ref().err(),
        "task_executed":false, "timeout_ms":2000,
        "protocol":if public_research_protocol {public_research::HELLO_SCHEMA} else if derived_protocol { "archeaxis.derived-worker-hello/v1" } else { "NDJSON" },
        "basis":if public_research_protocol {"live --public-research-hello: fixed module/dependency imports, protocol, identity and capability only; no query, network or model call; provider reachability NOT_CHECKED"} else if derived_protocol { "live --hello: protocol and declared capability; a job has to run to verify dependencies, engines and output" } else { "live NDJSON hello: protocol, worker identity and advertised capability; PDF additionally imports its required engine and observes its version; no document executed or output qualified" },
    })
}

fn handshake(
    staging: &Path,
    python: &Path,
    worker: &Path,
    capability: &str,
    allow_site: bool,
) -> Result<serde_json::Value, String> {
    let dir = tempfile::tempdir_in(staging).map_err(|e| e.to_string())?;
    let mut command = Command::new(python);
    command.arg("-B");
    if !allow_site {
        command.arg("-S");
    }
    command.arg(worker).arg("--staging-root").arg(dir.path());
    // Match the real job's declared launch contract, including video's required
    // artifact root. A health probe owns only this temporary directory: no job
    // request or durable workspace artifact location is handed to the worker.
    if crate::attempts::ARTIFACT_ROOT_CAPABILITIES.contains(&capability) {
        let artifacts = dir.path().join("artifacts");
        std::fs::create_dir(&artifacts).map_err(|e| e.to_string())?;
        command.arg("--artifact-root").arg(&artifacts);
    }
    command
        .current_dir(dir.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = OwnedChild(
        command
            .spawn()
            .map_err(|e| format!("worker health spawn: {e}"))?,
    );
    let stdout = child
        .0
        .stdout
        .take()
        .ok_or("worker health stdout unavailable")?;
    let (send, receive) = mpsc::channel();
    let reader = thread::spawn(move || {
        let mut line = Vec::new();
        let result = BufReader::new(stdout)
            .take((MAX_FRAME_BYTES + 1) as u64)
            .read_until(b'\n', &mut line)
            .map_err(|e| e.to_string())
            .and_then(|_| {
                if line.len() > MAX_FRAME_BYTES || !line.ends_with(b"\n") {
                    Err("missing, unterminated or oversized worker hello".into())
                } else {
                    String::from_utf8(line).map_err(|_| "worker hello is not UTF-8".into())
                }
            });
        let _ = send.send(result);
    });
    // Keep stdin open while awaiting hello. No request bytes or user content are sent.
    let result = receive
        .recv_timeout(Duration::from_secs(2))
        .map_err(|_| "worker hello timed out or closed".to_string())
        .and_then(|line| line)
        .and_then(|line| {
            let hello = decode_hello(&line).map_err(str::to_string)?;
            if !KNOWN_WORKER_IDENTITIES.contains(&hello.worker.name.as_str())
                || hello.worker.version != "1"
            {
                return Err("unexpected worker identity".into());
            }
            if !hello.capabilities.iter().any(|c| c == capability) {
                return Err(format!(
                    "worker does not advertise requested capability {capability}"
                ));
            }
            hello.require_runtime_dependency(capability).map_err(str::to_string)?;
            Ok(serde_json::json!({"worker_identity":hello.worker.name,"runtime_dependency":hello.runtime_dependency}))
        });
    // Windows venv launchers may own a second Python process. Close the
    // input-free handshake normally before killing the launcher: EOF lets the
    // actual worker exit and release its staging directory too.
    drop(child.0.stdin.take());
    let exit_deadline = Instant::now() + Duration::from_millis(500);
    while Instant::now() < exit_deadline {
        match child.0.try_wait() {
            Ok(Some(_)) | Err(_) => break,
            Ok(None) => thread::sleep(Duration::from_millis(10)),
        }
    }
    drop(child);
    let _ = reader.join();
    dir.close()
        .map_err(|e| format!("worker health staging cleanup unverified: {e}"))?;
    result
}
