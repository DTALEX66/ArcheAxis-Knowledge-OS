//! Run the tracked real-Core journey command as a regression test.
//!
//! The command starts the actual `archeaxis-api` binary built for this test run
//! (`CARGO_BIN_EXE_archeaxis-api`), walks the grading journey over real HTTP,
//! restarts the process and checks the duplicate replay. The material is synthetic
//! and no model or network is involved. If no interpreter can be found the test
//! says so and returns: a skip is not evidence.
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn usable(python: &Path) -> bool {
    Command::new(python)
        .args([
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)",
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

/// Pick an interpreter without reading request input. The `.venv` paths are the
/// project's normal local runtimes; PATH fallbacks let a CI runner with only
/// `python3` execute the same journey.
fn interpreter() -> Option<PathBuf> {
    if let Some(path) = std::env::var_os("ARCHEAXIS_PYTHON").map(PathBuf::from) {
        if path.is_file() && usable(&path) {
            return Some(path);
        }
    }
    for candidate in [
        repo().join(".venv/Scripts/python.exe"),
        repo().join(".venv/bin/python"),
        repo().join(".project-local/build/venv/Scripts/python.exe"),
    ] {
        if candidate.is_file() && usable(&candidate) {
            return Some(candidate);
        }
    }
    for name in ["python3", "python"] {
        let candidate = PathBuf::from(name);
        if usable(&candidate) {
            return Some(candidate);
        }
    }
    None
}

fn wait_with_deadline(
    child: &mut std::process::Child,
    deadline: Duration,
) -> std::process::ExitStatus {
    let started = Instant::now();
    loop {
        if let Some(status) = child.try_wait().expect("journey child state") {
            return status;
        }
        if started.elapsed() > deadline {
            let _ = child.kill();
            let _ = child.wait();
            panic!("real-core journey command did not finish within {deadline:?}");
        }
        std::thread::sleep(Duration::from_millis(100));
    }
}

#[test]
fn tracked_real_core_journey_command_passes_against_this_build() {
    let Some(python) = interpreter() else {
        eprintln!("skipping: no usable Python interpreter; this skip is not evidence");
        return;
    };
    let core = PathBuf::from(env!("CARGO_BIN_EXE_archeaxis-api"));
    assert!(core.is_file(), "built Core binary missing: {core:?}");
    let dir = tempfile::tempdir().unwrap();
    let workspace = dir.path().join("journey");
    let receipt = dir.path().join("receipt.json");
    let script = repo().join("scripts/ci/real_core_grading_journey.py");
    let mut child = Command::new(&python)
        .arg("-B")
        .arg(&script)
        .arg("--core-exe")
        .arg(&core)
        .arg("--workspace-dir")
        .arg(&workspace)
        .arg("--python")
        .arg(&python)
        .arg("--receipt")
        .arg(&receipt)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn real-core journey command");
    let status = wait_with_deadline(&mut child, Duration::from_secs(300));
    let output = child.wait_with_output().expect("collect journey output");
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        status.success(),
        "real-core journey failed; stdout tail={}\nstderr tail={}",
        &stdout[stdout.len().saturating_sub(2000)..],
        &stderr[stderr.len().saturating_sub(2000)..]
    );
    let value: Value =
        serde_json::from_str(&std::fs::read_to_string(&receipt).expect("journey receipt"))
            .expect("journey receipt json");
    assert_eq!(value["schema"], "aaos.real-core-process-journey/v1");
    let steps = value["steps"].as_array().expect("steps array");
    assert!(steps.len() >= 10, "unexpected step count: {}", steps.len());
    let grade = steps
        .iter()
        .find(|step| step["step"] == "practice grade")
        .expect("practice grade step");
    assert_eq!(grade["provider_correct"], true);
    assert_eq!(
        grade["upstream_member_sha256"],
        "fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f"
    );
    let disposition = steps
        .iter()
        .find(|step| step["step"] == "disposition after restart")
        .expect("post-restart disposition step");
    assert_eq!(disposition["state"], "COMPLETED");
    // The guards must hold in the real process, where the actor comes from the
    // launch credentials rather than an injected test header.
    for (name, expected) in [
        ("machine credential refused on grading route", 403),
        ("unknown activity refused", 404),
        ("oversize grade body refused", 413),
    ] {
        let step = steps
            .iter()
            .find(|step| step["step"] == name)
            .unwrap_or_else(|| panic!("missing guard step: {name}"));
        assert_eq!(step["status"], expected, "{name}");
    }
    let replay = steps
        .iter()
        .find(|step| step["step"] == "same-event replay after restart")
        .expect("replay step");
    assert_eq!(replay["duplicate"], true);
    assert_eq!(replay["provider_correct"], true);
    // A stale dispatch left by the previous process must be finalized by the
    // restarted Core, and only as UNKNOWN.
    let patched = steps
        .iter()
        .find(|step| step["step"] == "simulate stale dispatch from a previous process")
        .expect("stale dispatch patch step");
    assert_eq!(patched["status"], "PATCHED");
    let finalized = steps
        .iter()
        .find(|step| step["step"] == "startup finalization of stale dispatch")
        .expect("startup finalization step");
    assert_eq!(finalized["state"], "UNKNOWN");
    // A live backup publishes a verified artifact, its list survives a restart and
    // the restore preview verifies the same bytes without restoring.
    let backup = steps
        .iter()
        .find(|step| step["step"] == "live workspace backup")
        .expect("live backup step");
    assert_eq!(backup["status"], 201);
    assert_eq!(backup["verified"], true);
    let listed = steps
        .iter()
        .find(|step| step["step"] == "backup list survives restart")
        .expect("backup list step");
    assert!(listed["backups"].as_u64().unwrap_or(0) >= 1);
    let preview = steps
        .iter()
        .find(|step| step["step"] == "restore preview verifies the backup")
        .expect("restore preview step");
    assert_eq!(preview["verified"], true);
    // The maintenance mode must build an independent database from the artifact and
    // a fresh Core must serve the material from it.
    let restored = steps
        .iter()
        .find(|step| step["step"] == "maintenance restore into an independent database")
        .expect("maintenance restore step");
    assert_eq!(restored["status"], 0);
    assert_eq!(restored["verified"], true);
    let served = steps
        .iter()
        .find(|step| step["step"] == "restored Core serves the material document")
        .expect("restored document step");
    assert_eq!(served["status"], 200);
    // The workspace database is a real Core SQLite file, not an in-memory stub.
    assert!(workspace.join("workspace.sqlite").is_file());
}
