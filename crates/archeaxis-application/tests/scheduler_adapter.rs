//! R05 regression: the Core-side adapter asks the reused FSRS scheduler and
//! never invents an interval when the scheduler is unusable.

use archeaxis_application::scheduler::{SchedulerClient, SchedulerError};
use std::path::PathBuf;

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
