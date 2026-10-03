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
        let checked = if derived_protocol {
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
                Ok(capability.to_string())
            })
        } else {
            handshake(staging, python, worker, capability, allow_site)
        };
        match checked {
            Ok(identity) => ("handshake_ready", Ok(identity)),
            Err(reason) => ("handshake_failed", Err(reason)),
        }
    };
    serde_json::json!({
        "status":observation.0, "checked_at_unix_ms":checked_at,
        "worker_identity":observation.1.as_ref().ok(),
        "reason":observation.1.as_ref().err(),
        "task_executed":false, "timeout_ms":2000,
        "protocol":if derived_protocol { "archeaxis.derived-worker-hello/v1" } else { "NDJSON" },
        "basis":if derived_protocol { "live --hello: protocol and declared capability; a job has to run to verify dependencies, engines and output" } else { "live NDJSON hello: protocol, worker identity and advertised capability; a job has to run to verify engines and output" },
    })
}

fn handshake(
    staging: &Path,
    python: &Path,
    worker: &Path,
    capability: &str,
    allow_site: bool,
) -> Result<String, String> {
    let dir = tempfile::tempdir_in(staging).map_err(|e| e.to_string())?;
    let mut command = Command::new(python);
    command.arg("-B");
    if !allow_site {
        command.arg("-S");
    }
    command
        .arg(worker)
        .arg("--staging-root")
        .arg(dir.path())
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
            Ok(hello.worker.name)
        });
    drop(child);
    let _ = reader.join();
    result
}
