//! End-to-end synthetic checks of the Core-owned grading slice: reservation,
//! durable dispatch intent, receipt admission, restart readback, idempotency,
//! cancellation and withdrawal. No human, model or provider service is used.
//!
//! The optional fixed-worker test runs the retained DeepTutor 1.7.1 grader
//! source in an isolated child process. Without a usable interpreter it skips,
//! and a skip is not evidence.
use archeaxis_domain::{
    document,
    provider_learning::{
        self as learning, Activity, Cancel, Provider, Question, Start, Submission, grade,
    },
    provider_material_grant::Snapshot,
    provider_question,
};
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::Duration,
};

const UPSTREAM_SHA256: &str = "fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f";

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn hex_sha(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn grant(conn: &mut Connection, material: &Value) -> Value {
    document::create_optional(conn,None,None,"SYNTHETIC provider grant",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
            "purpose":"practice","consumer":"deeptutor","operations":["practice"],
            "material":snap(material),"authorization_basis":"SYNTHETIC explicit human authorization",
            "expires_at":null,"state":"granted"}
    }})).unwrap()
}

struct Chain {
    _dir: tempfile::TempDir,
    db: PathBuf,
    conn: Connection,
    request: grade::GradeRequest,
}

/// A synthetic question Document, its two version-bound grants, one DeepTutor
/// 1.7.1 activity and one pending attempt.
fn fixture(correct_answer: &str) -> Chain {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let source = document::create_optional(
        &mut conn,
        None,
        None,
        "SYNTHETIC material",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let question = document::create_optional(&mut conn,None,None,"SYNTHETIC question",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_deeptutor_question":{"schema":"archeaxis.deeptutor-question/v1","source_material":snap(&source),
            "origin":"user_import_unverified","question":{"question_id":"question_1","question":"synthetic?",
            "question_type":"choice","options":{"A":"first","B":"second"},"correct_answer":correct_answer,
            "explanation":"SYNTHETIC_PRIVATE_EXPLANATION"}}
    }})).unwrap();
    let source_grant = grant(&mut conn, &source);
    let question_grant = grant(&mut conn, &question);
    let view = provider_question::read_view(&conn, &snap(&question)).unwrap();
    let activity = Activity {
        activity_id: "activity".into(),
        material: snap(&source),
        provider: Provider {
            id: "deeptutor".into(),
            version: "1.7.1".into(),
        },
        question: Question {
            question_id: "question_1".into(),
            question_version: view["question_version"].as_str().unwrap().into(),
        },
        grant: Some(snap(&source_grant)),
    };
    learning::create(&mut conn, &activity).unwrap();
    learning::start(
        &mut conn,
        "activity",
        &Start {
            attempt_id: "attempt".into(),
        },
    )
    .unwrap();
    Chain {
        _dir: dir,
        db,
        conn,
        request: grade::GradeRequest {
            client_event_id: "event".into(),
            question_document: snap(&question),
            question_grant: snap(&question_grant),
            answer: "A".into(),
        },
    }
}

fn reserved(chain: &mut Chain) -> grade::Prepared {
    match grade::prepare(&mut chain.conn, "activity", "attempt", &chain.request).unwrap() {
        grade::Admission::Ready(prepared) => prepared,
        _ => panic!("expected a new reservation"),
    }
}

/// The fixed worker prints exactly one JSON line. These bytes model its shape
/// for the transaction tests; only the retained-worker test runs the real
/// grader, and it passes the real stdout through unchanged.
fn receipt(prepared: &grade::Prepared, correct: Option<bool>) -> Vec<u8> {
    let mut bytes = serde_json::to_vec(&json!({
        "schema":"archeaxis.deeptutor-practice-grade/v1","request_id":"event",
        "status":"OBSERVED","provider":"deeptutor","adapter_version":"1.7.1",
        "upstream_member_sha256":UPSTREAM_SHA256,
        "input_sha256":hex_sha(prepared.worker_input()),
        "provider_correct":correct,
        "question_binding":"caller_declared_unverified",
        "independent_mastery":"not_established"
    }))
    .unwrap();
    bytes.push(b'\n');
    bytes
}

#[test]
fn observed_grade_is_persisted_once_and_readable_after_restart() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    let early =
        grade::complete_observed(&mut chain.conn, &prepared, &receipt(&prepared, Some(true)));
    assert!(
        matches!(early, Err(learning::Error::Conflict(_))),
        "a reservation without a durable dispatch intent must not publish a result"
    );

    let mut fresh = fixture("A");
    let prepared = reserved(&mut fresh);
    grade::begin_dispatch(&mut fresh.conn, &prepared, Duration::from_secs(30)).unwrap();
    let first =
        grade::complete_observed(&mut fresh.conn, &prepared, &receipt(&prepared, Some(true)))
            .unwrap();
    assert_eq!(first["provider_correct"], json!(true));
    assert_eq!(first["duplicate"], false);
    assert_eq!(
        first["provider_result_verification"],
        "local_upstream_worker_observation"
    );
    assert_eq!(first["independent_mastery"], "not_established");
    assert_eq!(
        first["question_binding"],
        "question_document_content_bound_origin_unverified"
    );
    // The receipt echoes the caller's own answer (they supplied it) but never
    // the question's key or its private explanation.
    assert_eq!(first["answer"], json!("A"));
    assert!(first.get("correct_answer").is_none());
    assert!(!first.to_string().contains("SYNTHETIC_PRIVATE_EXPLANATION"));

    // The same event is a read-only history receipt, not a second execution.
    let again =
        grade::complete_observed(&mut fresh.conn, &prepared, &receipt(&prepared, Some(true)))
            .unwrap();
    assert_eq!(again["duplicate"], true);
    match grade::prepare(&mut fresh.conn, "activity", "attempt", &fresh.request).unwrap() {
        grade::Admission::Completed(value) => assert_eq!(value["duplicate"], true),
        _ => panic!("a committed result must be replayed as history"),
    }

    // Restart: a fresh connection to the same database still verifies and
    // returns the stored evidence.
    let db = fresh.db.clone();
    fresh.conn.close().unwrap();
    let reopened = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let history = learning::read(&reopened, "activity", None).unwrap();
    assert_eq!(history["attempts"][0]["state"], "submitted");
    assert_eq!(
        history["attempts"][0]["result"]["provider_correct"],
        json!(true)
    );
    assert_eq!(
        history["attempts"][0]["grade_evidence"]["upstream_member_sha256"],
        json!(UPSTREAM_SHA256)
    );
    assert_eq!(history["provider_result_verification"], "per_attempt");
    assert_eq!(history["independent_mastery"], "not_established");
}

#[test]
fn unscored_observation_is_submitted_as_null_not_a_failure() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(30)).unwrap();
    let receipt =
        grade::complete_observed(&mut chain.conn, &prepared, &receipt(&prepared, None)).unwrap();
    assert!(receipt["provider_correct"].is_null());
    assert_eq!(receipt["duplicate"], false);
    let history = learning::read(&chain.conn, "activity", None).unwrap();
    assert_eq!(history["attempts"][0]["state"], "submitted");
    assert!(history["attempts"][0]["result"]["provider_correct"].is_null());
    assert_eq!(
        learning::submit(
            &mut chain.conn,
            "activity",
            "attempt",
            &Submission {
                client_event_id: "event".into(),
                answer: "A".into(),
                provider_correct: None,
                self_report: false,
                rating: None,
            },
        )
        .unwrap()["duplicate"],
        true
    );
}

#[test]
fn unclear_outcome_is_unknown_never_relaunched_and_cancellation_stays_terminal() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::abandon_unknown(&mut chain.conn, &prepared).unwrap();
    match grade::prepare(&mut chain.conn, "activity", "attempt", &chain.request).unwrap() {
        grade::Admission::Unknown => (),
        _ => panic!("an unclear reservation was offered for a second launch"),
    }
    assert!(
        grade::complete_observed(&mut chain.conn, &prepared, &receipt(&prepared, Some(true)))
            .is_err()
    );
    // A new attempt is a new identity, so the human can continue.
    learning::start(
        &mut chain.conn,
        "activity",
        &Start {
            attempt_id: "attempt2".into(),
        },
    )
    .unwrap();
    let mut second = chain.request.clone();
    second.client_event_id = "event2".into();
    match grade::prepare(&mut chain.conn, "activity", "attempt2", &second).unwrap() {
        grade::Admission::Ready(_) => (),
        _ => panic!("a new attempt over an unclear reservation must be admissible"),
    }
    // Cancellation is a human terminal decision and blocks a later grade.
    learning::cancel(
        &mut chain.conn,
        "activity",
        "attempt2",
        &Cancel {
            client_cancel_id: "cancel".into(),
        },
    )
    .unwrap();
    assert!(matches!(
        grade::prepare(&mut chain.conn, "activity", "attempt2", &second),
        Err(learning::Error::Conflict(_))
    ));
}

#[test]
fn withdrawal_after_dispatch_refuses_publication() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(30)).unwrap();
    let grant_id = chain.request.question_grant.document_id.clone();
    let current: Value = chain
        .conn
        .query_row(
            "SELECT editor_json FROM document_versions WHERE document_id=?1 AND version=(SELECT MAX(version) FROM document_versions WHERE document_id=?1)",
            [&grant_id],
            |row| row.get::<_, String>(0),
        )
        .map(|text| serde_json::from_str(&text).unwrap())
        .unwrap();
    let mut revoked = current;
    revoked["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
    let version: i64 = chain
        .conn
        .query_row(
            "SELECT MAX(version) FROM document_versions WHERE document_id=?1",
            [&grant_id],
            |row| row.get(0),
        )
        .unwrap();
    document::save(&mut chain.conn, &grant_id, version, revoked).unwrap();
    assert!(
        grade::complete_observed(&mut chain.conn, &prepared, &receipt(&prepared, Some(true)))
            .is_err()
    );
    assert_eq!(
        learning::read(&chain.conn, "activity", None).unwrap()["attempts"][0]["state"],
        "pending"
    );
}

/// The retained grader source, selected without any request input and run in a
/// child process whose environment is cleared to the OS minimum.
fn repository_python() -> Option<PathBuf> {
    let repo = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    [
        std::env::var_os("ARCHEAXIS_PYTHON").map(PathBuf::from),
        Some(repo.join(".venv/Scripts/python.exe")),
        Some(repo.join(".project-local/build/venv/Scripts/python.exe")),
    ]
    .into_iter()
    .flatten()
    .find(|path| path.is_file())
}

fn run_retained_worker(prepared: &grade::Prepared) -> Option<std::process::Output> {
    let Some(python) = repository_python() else {
        eprintln!("skipping: no usable Python interpreter; this skip is not evidence");
        return None;
    };
    let repo = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let worker = repo
        .join("services/learning-providers/deeptutor/grade_worker.py")
        .canonicalize()
        .ok()?;
    let mut child = Command::new(python)
        .arg("-I")
        .arg("-B")
        .arg("-S")
        .arg(&worker)
        .env_clear()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("the retained fixed worker must start");
    let mut stdin = child.stdin.take().unwrap();
    stdin.write_all(prepared.worker_input()).unwrap();
    drop(stdin);
    let output = child.wait_with_output().unwrap();
    Some(output)
}

#[test]
fn retained_worker_objective_receipt_is_committed() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(30)).unwrap();
    let Some(output) = run_retained_worker(&prepared) else {
        return;
    };
    assert!(
        output.status.success(),
        "fixed worker exit: {:?}",
        output.status.code()
    );
    assert!(output.stderr.is_empty(), "worker wrote to stderr");
    let value = grade::complete_observed(&mut chain.conn, &prepared, &output.stdout).unwrap();
    assert_eq!(value["provider_correct"], json!(true));
    assert_eq!(
        value["provider_result_verification"],
        "local_upstream_worker_observation"
    );
}

#[test]
fn retained_worker_undecidable_question_is_committed_as_unscored() {
    // An answer key that names no current option is exactly the case in which
    // the retained grader returns None instead of guessing.
    let mut chain = fixture("NOT_AN_OPTION");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(30)).unwrap();
    let Some(output) = run_retained_worker(&prepared) else {
        return;
    };
    assert!(
        output.status.success(),
        "fixed worker exit: {:?}",
        output.status.code()
    );
    let value = grade::complete_observed(&mut chain.conn, &prepared, &output.stdout).unwrap();
    assert!(value["provider_correct"].is_null());
    assert_eq!(
        value["question_binding"],
        "question_document_content_bound_origin_unverified"
    );
    assert_eq!(value["independent_mastery"], "not_established");
}

#[test]
fn dispatch_second_and_disposition_survive_restart() {
    let mut chain = fixture("B");
    let prepared = reserved(&mut chain);
    let reserved_state = grade::disposition(&chain.conn, "activity", "attempt")
        .unwrap()
        .unwrap();
    assert_eq!(reserved_state["state"], "RESERVED");
    assert!(reserved_state["dispatched_at_unix"].is_null());
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(60)).unwrap();
    let dispatched = grade::disposition(&chain.conn, "activity", "attempt")
        .unwrap()
        .unwrap();
    assert_eq!(dispatched["state"], "DISPATCHED");
    assert!(dispatched["dispatched_at_unix"].as_u64().unwrap() > 0);
    drop(chain.conn);
    let conn = archeaxis_store_sqlite::init_workspace(chain.db.to_str().unwrap()).unwrap();
    let reopened = grade::disposition(&conn, "activity", "attempt")
        .unwrap()
        .unwrap();
    assert_eq!(reopened, dispatched);
}

#[test]
fn reconcile_only_finalizes_a_dispatch_whose_window_closed() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(60)).unwrap();
    assert_eq!(
        grade::reconcile_stale_dispatch(
            &mut chain.conn,
            "activity",
            "attempt",
            "event",
            Duration::from_secs(3600),
        )
        .unwrap(),
        grade::Reconciled::NotStale
    );
    assert_eq!(
        grade::reconcile_stale_dispatch(
            &mut chain.conn,
            "activity",
            "attempt",
            "event",
            Duration::from_secs(0),
        )
        .unwrap(),
        grade::Reconciled::Abandoned
    );
    let unknown = grade::disposition(&chain.conn, "activity", "attempt")
        .unwrap()
        .unwrap();
    assert_eq!(unknown["state"], "UNKNOWN");
    // Terminal: repeating the reconciliation neither relaunches nor changes the claim.
    assert_eq!(
        grade::reconcile_stale_dispatch(
            &mut chain.conn,
            "activity",
            "attempt",
            "event",
            Duration::from_secs(0),
        )
        .unwrap(),
        grade::Reconciled::NotDispatched
    );
    // The same event is only re-admitted as a read-only UNKNOWN, never a second launch.
    assert!(matches!(
        grade::prepare(&mut chain.conn, "activity", "attempt", &chain.request).unwrap(),
        grade::Admission::Unknown
    ));
}

#[test]
fn reconcile_refuses_a_dispatch_without_a_recorded_second() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(60)).unwrap();
    // A claim written without the dispatch second cannot be proven stale.
    let key: String = chain
        .conn
        .query_row(
            "SELECT key FROM workspace_meta WHERE key LIKE 'provider_grade_dispatch_%'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    chain
        .conn
        .execute("DELETE FROM workspace_meta WHERE key=?1", [&key])
        .unwrap();
    assert_eq!(
        grade::reconcile_stale_dispatch(
            &mut chain.conn,
            "activity",
            "attempt",
            "event",
            Duration::from_secs(0),
        )
        .unwrap(),
        grade::Reconciled::NoDispatchTime
    );
    assert_eq!(
        grade::disposition(&chain.conn, "activity", "attempt")
            .unwrap()
            .unwrap()["state"],
        "DISPATCHED"
    );
    // A reservation that was never dispatched has nothing to reconcile.
    let mut reserved_only = fixture("A");
    let _prepared = reserved(&mut reserved_only);
    assert_eq!(
        grade::reconcile_stale_dispatch(
            &mut reserved_only.conn,
            "activity",
            "attempt",
            "event",
            Duration::from_secs(0),
        )
        .unwrap(),
        grade::Reconciled::NotDispatched
    );
}

fn age_recorded_dispatch(conn: &rusqlite::Connection, seconds_ago: u64) {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let key: String = conn
        .query_row(
            "SELECT key FROM workspace_meta WHERE key LIKE 'provider_grade_dispatch_%'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
        rusqlite::params![(now - seconds_ago).to_string(), key],
    )
    .unwrap();
}

#[test]
fn restart_finalization_leaves_a_fresh_dispatch_alone() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(60)).unwrap();
    let result =
        grade::abandon_dispatched_after_restart(&mut chain.conn, Duration::from_secs(150)).unwrap();
    assert_eq!(
        result,
        grade::RestartFinalization {
            abandoned: 0,
            skipped: 0,
            recent: 1,
        }
    );
    assert_eq!(
        grade::disposition(&chain.conn, "activity", "attempt")
            .unwrap()
            .unwrap()["state"],
        "DISPATCHED"
    );
}

#[test]
fn restart_finalization_abandons_only_an_aged_dispatch_once() {
    let mut chain = fixture("A");
    let prepared = reserved(&mut chain);
    grade::begin_dispatch(&mut chain.conn, &prepared, Duration::from_secs(60)).unwrap();
    age_recorded_dispatch(&chain.conn, 1_000);
    let result =
        grade::abandon_dispatched_after_restart(&mut chain.conn, Duration::from_secs(150)).unwrap();
    assert_eq!(result.abandoned, 1);
    assert_eq!(result.recent, 0);
    assert_eq!(
        grade::disposition(&chain.conn, "activity", "attempt")
            .unwrap()
            .unwrap()["state"],
        "UNKNOWN"
    );
    // The same event stays a read-only UNKNOWN, never a second launch.
    assert!(matches!(
        grade::prepare(&mut chain.conn, "activity", "attempt", &chain.request).unwrap(),
        grade::Admission::Unknown
    ));
    // Repeating the restart pass is a no-op.
    let again =
        grade::abandon_dispatched_after_restart(&mut chain.conn, Duration::from_secs(150)).unwrap();
    assert_eq!(again, grade::RestartFinalization::default());
}

#[test]
fn restart_finalization_skips_damaged_or_undispatched_claims() {
    // A reserved claim was never dispatched; a restart cannot finalize it.
    let mut reserved_only = fixture("A");
    let _prepared = reserved(&mut reserved_only);
    let reserved_result =
        grade::abandon_dispatched_after_restart(&mut reserved_only.conn, Duration::from_secs(0))
            .unwrap();
    assert_eq!(reserved_result, grade::RestartFinalization::default());
    assert_eq!(
        grade::disposition(&reserved_only.conn, "activity", "attempt")
            .unwrap()
            .unwrap()["state"],
        "RESERVED"
    );

    // A dispatched claim whose event index is missing cannot prove its identity, so
    // the restart pass counts it as skipped and leaves the claim untouched.
    let mut damaged = fixture("A");
    let prepared = reserved(&mut damaged);
    grade::begin_dispatch(&mut damaged.conn, &prepared, Duration::from_secs(60)).unwrap();
    age_recorded_dispatch(&damaged.conn, 1_000);
    damaged
        .conn
        .execute(
            "DELETE FROM workspace_meta WHERE key LIKE 'provider_grade_event_%'",
            [],
        )
        .unwrap();
    let damaged_result =
        grade::abandon_dispatched_after_restart(&mut damaged.conn, Duration::from_secs(150))
            .unwrap();
    assert_eq!(damaged_result.abandoned, 0);
    assert_eq!(damaged_result.skipped, 1);
    // The readback is fail-closed on a damaged pair rather than trusting its state.
    assert!(grade::disposition(&damaged.conn, "activity", "attempt").is_err());
    // The claim itself was not rewritten by the restart pass.
    let state: String = damaged
        .conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key LIKE 'provider_grade_attempt_%'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert!(state.contains("\"state\":\"DISPATCHED\""));
}
