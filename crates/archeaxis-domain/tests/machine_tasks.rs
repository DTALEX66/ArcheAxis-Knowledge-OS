//! R11: machine task receipts are candidate/measurement records with explicit
//! refusals - a machine-only writer, no rewriting after the fact, and an
//! `unmeasured` outcome that stays visible instead of being rounded up.

use archeaxis_domain::machine::{self, MachineTask};
use archeaxis_store_sqlite::init_workspace;

fn task<'a>(task_id: &'a str, outcome: &'a str, failure: Option<&'a str>) -> MachineTask<'a> {
    MachineTask {
        task_id,
        principal: "machine",
        conditions: "offline; fixed sample",
        knowledge_version: Some("k_abc@1"),
        method_version: Some("method-1"),
        tool_version: Some("tool-1"),
        model_version: "qwen3:8b",
        scope: "one observable extraction task",
        outcome,
        failure,
        retest_of: None,
    }
}

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    (dir, conn)
}

#[test]
fn a_successful_task_records_versions_and_scope() {
    let (_dir, mut conn) = workspace();
    machine::record_machine_task(&mut conn, &task("t-1", "succeeded", None)).unwrap();
    let found = machine::machine_task(&conn, "t-1").unwrap().expect("recorded");
    assert_eq!(found.0, "succeeded");
    assert_eq!(found.1, "qwen3:8b");
    assert_eq!(found.2, "one observable extraction task");
    assert!(found.3.is_none(), "a succeeded task carries no failure note");
    assert_eq!(machine::machine_task_counts(&conn).unwrap(), (1, 0));
}

#[test]
fn an_unmeasured_task_stays_visible_as_unmeasured() {
    let (_dir, mut conn) = workspace();
    machine::record_machine_task(&mut conn, &task("t-2", "unmeasured", None)).unwrap();
    let (total, unmeasured) = machine::machine_task_counts(&conn).unwrap();
    assert_eq!((total, unmeasured), (1, 1), "an unmeasured result must not be counted as verified");
    assert_eq!(machine::machine_task(&conn, "t-2").unwrap().unwrap().0, "unmeasured");
}

#[test]
fn a_failed_task_must_say_why() {
    let (_dir, mut conn) = workspace();
    assert!(
        machine::record_machine_task(&mut conn, &task("t-3", "failed", None)).is_err(),
        "a failure without a reason must be refused"
    );
    machine::record_machine_task(&mut conn, &task("t-3", "failed", Some("extraction returned no text"))).unwrap();
    assert_eq!(
        machine::machine_task(&conn, "t-3").unwrap().unwrap().3.as_deref(),
        Some("extraction returned no text")
    );
}

#[test]
fn refused_receipts_never_land() {
    let (_dir, mut conn) = workspace();

    // Only a machine principal writes machine receipts.
    let mut human = task("t-4", "succeeded", None);
    human.principal = "human";
    assert!(machine::record_machine_task(&mut conn, &human).is_err());

    // Unknown outcomes are refused rather than stored as if they meant something.
    assert!(machine::record_machine_task(&mut conn, &task("t-5", "probably-fine", None)).is_err());

    // A succeeded task cannot carry a failure note.
    assert!(machine::record_machine_task(&mut conn, &task("t-6", "succeeded", Some("oops"))).is_err());

    // A receipt is immutable: the same task id cannot be rewritten.
    machine::record_machine_task(&mut conn, &task("t-7", "succeeded", None)).unwrap();
    assert!(
        machine::record_machine_task(&mut conn, &task("t-7", "failed", Some("changed my mind"))).is_err(),
        "a receipt must not be rewritten after the fact"
    );

    assert_eq!(machine::machine_task_counts(&conn).unwrap(), (1, 0), "only t-7 may exist");
}
