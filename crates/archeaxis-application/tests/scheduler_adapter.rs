//! R05 regression: the Core-side adapter asks the reused FSRS scheduler and
//! never invents an interval when the scheduler is unusable.

use archeaxis_application::scheduler::{SchedulerClient, SchedulerError};
use std::path::PathBuf;
use std::time::{Duration, Instant};

fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("run cargo via the project wrapper so ARCHEAXIS_PYTHON is set")
        .into()
}

fn worker() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join(archeaxis_application::scheduler::WORKER_RELATIVE_PATH)
}

/// A card with high stability: the reused FSRS scheduler pushes it far past the
/// 14-day ceiling of the temporary ladder, so the value itself identifies the
/// authority that answered.
const MATURE_REQUEST: &str = r#"{
  "item_key": "card-1",
  "rating": 3,
  "state": {"state": "review", "stability": 42.0, "difficulty": 5.0,
            "due": "2026-09-01T00:00:00+00:00",
            "last_review": "2026-08-03T00:00:00+00:00", "step": 0},
  "now": "2026-09-02T00:00:00+00:00"
}"#;

#[test]
fn adapter_returns_fsrs_scheduling_not_the_ladder() {
    let client = SchedulerClient::new(python(), worker());
    let schedule = client.review(MATURE_REQUEST).expect("scheduler must answer");
    assert_eq!(schedule.authority, "fsrs");
    assert!(
        schedule.next_review_days > 14,
        "the placeholder ladder caps at 14 days, so {} means the ladder answered",
        schedule.next_review_days
    );
    assert!(schedule.due.starts_with("2026-"), "unexpected due date {}", schedule.due);
    assert!(!schedule.state.is_empty());
}

#[test]
fn identical_requests_are_reproducible() {
    let client = SchedulerClient::new(python(), worker());
    let first = client.review(MATURE_REQUEST).unwrap();
    let second = client.review(MATURE_REQUEST).unwrap();
    assert_eq!(first, second, "a replayed review must produce the same schedule");
}

#[test]
fn unusable_request_is_rejected_without_an_interval() {
    let client = SchedulerClient::new(python(), worker());
    let err = client.review(r#"{"item_key":"card-1"}"#).unwrap_err();
    assert!(matches!(err, SchedulerError::Rejected(_)), "unexpected {err:?}");
}

#[test]
fn missing_interpreter_reports_unavailable_instead_of_a_default_interval() {
    let client = SchedulerClient::new(PathBuf::from("Z:/definitely/missing/python.exe"), worker());
    let err = client.review(MATURE_REQUEST).unwrap_err();
    assert!(matches!(err, SchedulerError::Unavailable(_)), "unexpected {err:?}");
    assert!(err.to_string().contains("unavailable"));
}

#[test]
fn missing_worker_script_reports_unavailable() {
    let client = SchedulerClient::new(python(), PathBuf::from("Z:/definitely/missing/worker.py"));
    let err = client.review(MATURE_REQUEST).unwrap_err();
    assert!(matches!(err, SchedulerError::Unavailable(_)), "unexpected {err:?}");
}

#[test]
fn stalled_or_flooding_workers_fail_bounded_and_next_review_still_works() {
    let dir = tempfile::tempdir().unwrap();
    for (name, script, request, expected) in [
        ("silent", "import time; time.sleep(10)", MATURE_REQUEST.to_owned(), "deadline"),
        ("partial", "import sys,time; sys.stdout.write('{'); sys.stdout.flush(); time.sleep(10)", MATURE_REQUEST.to_owned(), "deadline"),
        ("stderr", "import sys,time; sys.stderr.write('x'*100000); sys.stderr.flush(); time.sleep(10)", MATURE_REQUEST.to_owned(), "stderr"),
        ("stdout", "import sys,time; sys.stdout.write('x'*100000); sys.stdout.flush(); time.sleep(10)", MATURE_REQUEST.to_owned(), "stdout"),
        ("stdin", "import time; time.sleep(10)", "x".repeat(16_000), "deadline"),
        ("exit", "import os,sys,time; sys.stdin.read(); print('{}',flush=True); os.close(1); os.close(2); time.sleep(10)", MATURE_REQUEST.to_owned(), "deadline"),
    ] {
        let path = dir.path().join(format!("{name}.py"));
        std::fs::write(&path, script).unwrap();
        let started = Instant::now();
        let error = SchedulerClient::new(python(), path)
            .review_with_timeout(&request, Duration::from_millis(700)).unwrap_err();
        assert!(started.elapsed() < Duration::from_secs(3), "{name} exceeded deadline: {error}");
        assert!(error.to_string().contains(expected), "{name}: {error}");
    }
    assert_eq!(SchedulerClient::new(python(), worker()).review(MATURE_REQUEST).unwrap().authority, "fsrs");
}

#[test]
fn oversized_input_is_rejected_before_starting_worker() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("not-started.py");
    let marker = script.with_extension("started");
    std::fs::write(&script, "from pathlib import Path; Path(__file__).with_suffix('.started').touch()").unwrap();
    let error = SchedulerClient::new(python(), script).review(&"x".repeat(65_537)).unwrap_err();
    assert!(error.to_string().contains("request exceeds"));
    assert!(!marker.exists());
}

#[cfg(windows)]
#[test]
fn timeout_reaps_the_owned_windows_process() {
    use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle, RawHandle};
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn OpenProcess(access: u32, inherit: i32, pid: u32) -> RawHandle;
        fn WaitForSingleObject(handle: RawHandle, milliseconds: u32) -> u32;
    }
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("owned.py");
    let pid_path = script.with_extension("pid");
    std::fs::write(&script, "import os,time\nfrom pathlib import Path\nPath(__file__).with_suffix('.pid').write_text(str(os.getpid()))\ntime.sleep(10)\n").unwrap();
    let client = SchedulerClient::new(python(), script);
    let task = std::thread::spawn(move || client.review_with_timeout(MATURE_REQUEST, Duration::from_millis(1500)));
    let observe_until = Instant::now() + Duration::from_secs(1);
    let pid = loop {
        if let Ok(text) = std::fs::read_to_string(&pid_path) {
            if let Ok(pid) = text.parse::<u32>() { break pid; }
        }
        assert!(Instant::now() < observe_until, "owned worker did not announce its PID");
        std::thread::sleep(Duration::from_millis(5));
    };
    let raw = unsafe { OpenProcess(0x00100000, 0, pid) }; // SYNCHRONIZE only
    assert!(!raw.is_null());
    let handle = unsafe { OwnedHandle::from_raw_handle(raw) };
    assert_eq!(unsafe { WaitForSingleObject(handle.as_raw_handle(), 0) }, 258);
    assert!(task.join().unwrap().unwrap_err().to_string().contains("deadline"));
    // CPython's Windows venv redirector owns a separate interpreter in a
    // kill-on-close job. Waiting for the redirector does not synchronously
    // signal that interpreter's handle. Observe the real worker's exit with
    // a bounded wait, well before its 10-second natural sleep would end.
    // A leaked worker still fails; neither PID disappearance nor a successful
    // launcher exit is accepted as evidence of interpreter termination.
    assert_eq!(unsafe { WaitForSingleObject(handle.as_raw_handle(), 1000) }, 0,
        "owned interpreter remained alive after bounded cleanup");
}
