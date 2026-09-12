use archeaxis_application::{bootstrap, jobs};
use archeaxis_domain::source::{self, ImportOutcome};
use rusqlite::Connection;

fn fixture() -> (tempfile::TempDir, Connection, String) {
    let dir = tempfile::tempdir().unwrap();
    let (mut conn, _) = bootstrap(dir.path().join("jobs.sqlite").to_str().unwrap()).unwrap();
    let sid = match source::import_source(&mut conn, b"original", "file.txt", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } => source_id,
        _ => unreachable!(),
    };
    jobs::enqueue(&mut conn, "job", "text", &sid).unwrap();
    (dir, conn, sid)
}

fn full_receipt() -> serde_json::Value {
    serde_json::json!({"engine":"engine", "engine_version":"1", "params":{},
        "loss_note":"BOM stripped; line anchors capped", "losses":["BOM stripped", "line anchors capped"],
        "covered":5000, "total":5001, "coverage":5000.0/5001.0})
}

#[test]
fn complete_retains_full_coverage_after_reopen_and_binds_it_to_replay() {
    let (dir, mut conn, _) = fixture();
    let receipt = full_receipt();
    let loss: jobs::LossReceipt = serde_json::from_value(receipt.clone()).unwrap();
    jobs::complete(&mut conn, "job", "engine", "derived", Some(&loss)).unwrap();
    drop(conn);
    let (mut conn, _) = bootstrap(dir.path().join("jobs.sqlite").to_str().unwrap()).unwrap();
    let stored: String = conn.query_row("SELECT loss_receipt FROM jobs WHERE job_id='job'", [], |r| r.get(0)).unwrap();
    assert_eq!(serde_json::from_str::<serde_json::Value>(&stored).unwrap(), receipt);
    jobs::complete(&mut conn, "job", "engine", "derived", Some(&loss)).unwrap();
    let mut changed = receipt;
    changed["covered"] = serde_json::json!(5001);
    changed["coverage"] = serde_json::json!(1.0);
    let changed = serde_json::from_value(changed).unwrap();
    assert!(matches!(jobs::complete(&mut conn, "job", "engine", "derived", Some(&changed)), Err(jobs::JobError::Conflict)));
}

#[test]
fn complete_rejects_incoherent_coverage_before_any_write() {
    for change in [serde_json::json!({"covered":5002}), serde_json::json!({"coverage":1.0}),
        serde_json::json!({"total":0}), serde_json::json!({"engine_version":""}),
        serde_json::json!({"params":[]})] {
        let (_dir, mut conn, _) = fixture();
        let mut value = full_receipt();
        value.as_object_mut().unwrap().extend(change.as_object().unwrap().clone());
        let loss = serde_json::from_value::<jobs::LossReceipt>(value);
        assert!(loss.is_err() || jobs::complete(&mut conn, "job", "engine", "derived", Some(&loss.unwrap())).is_err());
        assert_eq!(jobs::job_state(&conn, "job").unwrap().as_deref(), Some("queued"));
        assert_eq!(conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get::<_, i64>(0)).unwrap(), 0);
    }
}

#[test]
fn receipt_unknown_fields_are_not_silently_dropped() {
    let mut value = full_receipt();
    value["covergae"] = serde_json::json!(1.0);
    assert!(serde_json::from_value::<jobs::LossReceipt>(value).is_err());
}

#[test]
fn receipt_null_or_missing_fields_cannot_evade_schema() {
    for field in ["covered", "total", "coverage", "losses"] {
        let mut value = full_receipt();
        value[field] = serde_json::Value::Null;
        assert!(serde_json::from_value::<jobs::LossReceipt>(value).is_err(), "null {field}");
    }
    let mut value = full_receipt();
    value.as_object_mut().unwrap().remove("loss_note");
    assert!(serde_json::from_value::<jobs::LossReceipt>(value).is_err());
}

#[test]
fn legacy_receipt_wire_shape_and_zero_coverage_are_preserved() {
    let value = serde_json::json!({"engine":"engine","engine_version":"1","params":{},"loss_note":null});
    let receipt: jobs::LossReceipt = serde_json::from_value(value.clone()).unwrap();
    assert_eq!(serde_json::to_value(receipt).unwrap(), value);
    let mut zero = value;
    zero.as_object_mut().unwrap().extend(serde_json::json!({"covered":0,"total":0,"coverage":1.0}).as_object().unwrap().clone());
    let receipt = serde_json::from_value(zero).unwrap();
    let (_dir, mut conn, _) = fixture();
    jobs::complete(&mut conn, "job", "engine", "", Some(&receipt)).unwrap();
}

#[test]
fn mathematical_integer_counts_accept_json_decimal_and_exponent_notation() {
    let loss: jobs::LossReceipt = serde_json::from_str(r#"{"engine":"engine","engine_version":"1","params":{},"loss_note":null,"covered":1.0,"total":1e0,"coverage":1}"#).unwrap();
    let (_dir, mut conn, _) = fixture();
    jobs::complete(&mut conn, "job", "engine", "x", Some(&loss)).unwrap();
}

#[test]
fn old_four_field_digest_replays_without_duplicate_transform() {
    use sha2::{Digest, Sha256};
    let legacy_bytes = br#"["engine","derived",{"engine":"engine","engine_version":"1","params":{},"loss_note":null}]"#;
    let value = serde_json::json!({"engine":"engine","engine_version":"1","params":{},"loss_note":null});
    let loss = serde_json::from_value(value).unwrap();
    let (_dir, mut conn, _) = fixture();
    jobs::complete(&mut conn, "job", "engine", "derived", Some(&loss)).unwrap();
    conn.execute("UPDATE jobs SET completion_digest=?1 WHERE job_id='job'", [hex::encode(Sha256::digest(legacy_bytes))]).unwrap();
    jobs::complete(&mut conn, "job", "engine", "derived", Some(&loss)).unwrap();
    assert_eq!(conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get::<_, i64>(0)).unwrap(), 1);
}

#[test]
fn duplicate_completion_is_durable_and_conflicting_content_is_rejected() {
    let (dir, mut conn, _) = fixture();
    jobs::complete(&mut conn, "job", "engine", "derived", None).unwrap();
    drop(conn);
    let (mut conn, _) = bootstrap(dir.path().join("jobs.sqlite").to_str().unwrap()).unwrap();
    jobs::complete(&mut conn, "job", "engine", "derived", None).unwrap();
    assert!(jobs::complete(&mut conn, "job", "engine", "different", None).is_err());
    let count: i64 = conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 1);
}

#[test]
fn insert_failure_never_marks_job_completed() {
    let (_dir, mut conn, _) = fixture();
    conn.execute_batch("CREATE TRIGGER reject_transform BEFORE INSERT ON transforms BEGIN SELECT RAISE(ABORT, 'injected failure'); END;").unwrap();
    assert!(jobs::complete(&mut conn, "job", "engine", "derived", None).is_err());
    assert_eq!(jobs::job_state(&conn, "job").unwrap().as_deref(), Some(jobs::STATE_QUEUED));
    let count: i64 = conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
}

#[test]
fn enqueue_conflict_and_missing_jobs_are_errors() {
    let (_dir, mut conn, sid) = fixture();
    jobs::enqueue(&mut conn, "job", "text", &sid).unwrap();
    assert!(jobs::enqueue(&mut conn, "job", "ocr", &sid).is_err());
    assert!(jobs::complete(&mut conn, "missing", "engine", "text", None).is_err());
    assert!(jobs::fail(&mut conn, "missing", "oops").is_err());
}

#[test]
fn terminal_results_cannot_be_overwritten() {
    let (_dir, mut conn, sid) = fixture();
    jobs::complete(&mut conn, "job", "engine", "derived", None).unwrap();
    assert!(jobs::fail(&mut conn, "job", "late failure").is_err());
    jobs::enqueue(&mut conn, "failed", "text", &sid).unwrap();
    jobs::fail(&mut conn, "failed", "failure \"quoted\"\nline").unwrap();
    let receipt: String = conn.query_row("SELECT loss_receipt FROM jobs WHERE job_id='failed'", [], |r| r.get(0)).unwrap();
    let value: serde_json::Value = serde_json::from_str(&receipt).unwrap();
    assert_eq!(value["error"], "failure \"quoted\"\nline");
    assert!(jobs::complete(&mut conn, "failed", "engine", "late", None).is_err());
}

#[test]
fn succeeded_state_matches_contract() {
    assert_eq!(jobs::STATE_COMPLETED, archeaxis_contracts::JOB_SUCCEEDED);
}

#[test]
fn job_update_failure_also_rolls_back_inserted_transform() {
    let (_dir, mut conn, _) = fixture();
    conn.execute_batch("CREATE TRIGGER reject_completion BEFORE UPDATE ON jobs BEGIN SELECT RAISE(ABORT, 'injected update failure'); END;").unwrap();
    assert!(jobs::complete(&mut conn, "job", "engine", "derived", None).is_err());
    let count: i64 = conn.query_row("SELECT count(*) FROM transforms", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
    assert_eq!(jobs::job_state(&conn, "job").unwrap().as_deref(), Some(jobs::STATE_QUEUED));
}

#[test]
fn future_and_unrelated_databases_are_unchanged_on_rejection() {
    let (dir, conn, _) = fixture();
    conn.execute("UPDATE workspace_meta SET value='999' WHERE key='schema_version'", []).unwrap();
    drop(conn);
    let path = dir.path().join("jobs.sqlite");
    let before = std::fs::read(&path).unwrap();
    assert!(bootstrap(path.to_str().unwrap()).is_err());
    assert_eq!(std::fs::read(path).unwrap(), before);
    let legacy = dir.path().join("legacy.sqlite");
    let conn = Connection::open(&legacy).unwrap();
    conn.execute("CREATE TABLE legacy_user_data(body TEXT)", []).unwrap();
    drop(conn);
    let before = std::fs::read(&legacy).unwrap();
    assert!(bootstrap(legacy.to_str().unwrap()).is_err());
    assert_eq!(std::fs::read(legacy).unwrap(), before);
}

#[test]
fn concurrent_open_migrates_v1_once_and_preserves_existing_jobs() {
    let (dir, conn, _) = fixture();
    conn.execute_batch("ALTER TABLE jobs DROP COLUMN completion_digest;
        ALTER TABLE jobs DROP COLUMN transform_id;
        UPDATE workspace_meta SET value='1' WHERE key='schema_version';
        UPDATE jobs SET state='completed';").unwrap();
    drop(conn);
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(4));
    let handles: Vec<_> = (0..4).map(|_| {
        let barrier = barrier.clone();
        let path = dir.path().join("jobs.sqlite");
        std::thread::spawn(move || {
            barrier.wait();
            bootstrap(path.to_str().unwrap()).map(|_| ())
        })
    }).collect();
    for handle in handles { handle.join().unwrap().unwrap(); }
    let (conn, _) = bootstrap(dir.path().join("jobs.sqlite").to_str().unwrap()).unwrap();
    assert_eq!(jobs::job_state(&conn, "job").unwrap().as_deref(), Some(jobs::STATE_COMPLETED));
    let version: String = conn.query_row("SELECT value FROM workspace_meta WHERE key='schema_version'", [], |r| r.get(0)).unwrap();
    assert_eq!(version, archeaxis_store_sqlite::SCHEMA_VERSION.to_string());
}
