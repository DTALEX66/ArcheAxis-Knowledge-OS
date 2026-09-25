//! DP-NF-05: the machine task -> knowledge binding must not survive a revision.
//!
//! The neighbouring suites already pin the surrounding rules: `machine_tasks.rs`
//! refuses a binding to a *candidate* (never accepted) revision, a missing id, a
//! retest of an id that was never recorded and a retest of a task that did not
//! fail. What none of them exercise is the revision *lifecycle*: a knowledge id
//! that WAS accepted and current when receipts were recorded against it, and is
//! then superseded by a human `modified` review.
//!
//! Such a revision stays `status='accepted'` forever (REVISION-01: a review never
//! rewrites the reviewed body or status), so the status test alone cannot catch
//! it; only `knowledge::is_knowledge_active` can (X09). This test drives that
//! boundary: a machine must not open a new task against the superseded revision,
//! must bind the retest to the corrected successor instead, and the whole chain
//! must still read back after a store reopen.
//!
//! Synthetic only: fixed strings, a temporary database, no model call.

use archeaxis_domain::{
    knowledge,
    machine::{self, MachineTask},
};
use archeaxis_store_sqlite::init_workspace;

fn stored_task<'a>(
    task_id: &'a str,
    outcome: &'a str,
    failure: Option<&'a str>,
    knowledge_version: Option<&'a str>,
) -> MachineTask<'a> {
    MachineTask {
        task_id,
        principal: "machine",
        conditions: "offline; fixed synthetic sample",
        knowledge_version,
        method_version: Some("method-1"),
        tool_version: Some("tool-1"),
        model_version: "synthetic-model",
        scope: "one observable extraction task",
        outcome,
        failure,
        retest_of: None,
    }
}

#[test]
fn a_superseded_revision_cannot_be_bound_and_the_retest_follows_the_successor() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("machine_loop_restart.sqlite");
    let db_path = db.to_str().unwrap();

    let (original, successor);
    {
        let mut conn = init_workspace(db_path).unwrap();

        let accepted = knowledge::create_knowledge(
            &mut conn,
            "FACTUAL_CLAIM",
            "synthetic fact v1",
            "accepted",
            None,
            None,
            "owner",
        )
        .unwrap();

        // A measurement runs against the revision while it is current, and fails.
        machine::record_machine_task(
            &mut conn,
            &stored_task("task-b", "failed", Some("synthetic worker error"), Some(&accepted)),
        )
        .unwrap();

        // A human correction supersedes it; the correction becomes the current
        // accepted revision.
        let corrected = knowledge::review(
            &mut conn,
            &accepted,
            "modified",
            "owner",
            Some("human applied a corrected body"),
            Some("synthetic fact v2 corrected"),
        )
        .unwrap();
        knowledge::review(&mut conn, &corrected, "accepted", "owner", None, None).unwrap();

        // The successor is the current revision and may be bound. The retest of
        // the failed task B is bound to the corrected revision, not to the one B
        // measured.
        let mut retest = stored_task("task-a", "succeeded", None, Some(&corrected));
        retest.retest_of = Some("task-b");
        machine::record_machine_task(&mut conn, &retest).unwrap();

        // The original row is still `accepted`; it is no longer *active*.
        assert_eq!(
            knowledge::knowledge_status(&conn, &accepted).unwrap().as_deref(),
            Some("accepted"),
            "REVISION-01: a modified review never rewrites the reviewed row's status"
        );
        assert!(
            !knowledge::is_knowledge_active(&conn, &accepted).unwrap(),
            "after a supersede the original revision must no longer count as current"
        );
        assert!(knowledge::is_knowledge_active(&conn, &corrected).unwrap());

        // Gap under audit: a task opened against the superseded revision is
        // refused even though its status is still 'accepted'.
        let stale = stored_task("task-stale", "succeeded", None, Some(&accepted));
        assert!(
            machine::record_machine_task(&mut conn, &stale).is_err(),
            "a new task must not bind to the superseded revision"
        );

        // Neither may a retest be pinned back onto it: retest_of names the failed
        // task, while the knowledge binding must follow the corrected successor.
        let mut retest_via_stale =
            stored_task("task-stale-retest", "succeeded", None, Some(&accepted));
        retest_via_stale.retest_of = Some("task-b");
        assert!(
            machine::record_machine_task(&mut conn, &retest_via_stale).is_err(),
            "a retest must bind the corrected revision, not the superseded one"
        );

        original = accepted;
        successor = corrected;
    }

    // Cold restart: reopen the same file. The binding rules must be the same.
    let mut conn = init_workspace(db_path).unwrap();

    // The retest chain written before the restart is intact.
    let retest = machine::machine_task(&conn, "task-a").unwrap().expect("task-a recorded");
    assert_eq!(retest.knowledge_version.as_deref(), Some(successor.as_str()));
    assert_eq!(retest.retest_of.as_deref(), Some("task-b"));
    assert_eq!(retest.outcome, "succeeded");
    assert_eq!(retest.conditions, "offline; fixed synthetic sample");

    let predecessor = machine::machine_task(&conn, "task-b").unwrap().expect("task-b recorded");
    assert_eq!(predecessor.outcome, "failed");
    assert_eq!(predecessor.failure.as_deref(), Some("synthetic worker error"));

    // Nothing from the refused attempts landed.
    assert!(
        machine::machine_task(&conn, "task-stale").unwrap().is_none(),
        "a refused receipt must not land"
    );
    assert!(machine::machine_task(&conn, "task-stale-retest").unwrap().is_none());
    assert_eq!(machine::machine_task_counts(&conn).unwrap(), (2, 0));

    // After the restart the superseded revision is still refused and the
    // successor is still bindable.
    let stale_after_restart =
        stored_task("task-after-restart", "unmeasured", None, Some(&original));
    assert!(
        machine::record_machine_task(&mut conn, &stale_after_restart).is_err(),
        "the refusal must not be an in-process accident"
    );
    let mut current_after_restart =
        stored_task("task-current-after-restart", "succeeded", None, Some(&successor));
    current_after_restart.retest_of = Some("task-b");
    machine::record_machine_task(&mut conn, &current_after_restart).unwrap();
    assert_eq!(machine::machine_task_counts(&conn).unwrap(), (3, 0));
}
