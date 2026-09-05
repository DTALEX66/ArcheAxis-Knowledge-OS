//! Application layer test: bootstrap handshake + job orchestration flow.
use archeaxis_application::jobs::{self, LossReceipt, STATE_COMPLETED, STATE_FAILED, STATE_QUEUED};
use archeaxis_application::bootstrap;

#[test]
fn handshake_identity() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("app.sqlite");
    let (conn, hs) = bootstrap(db.to_str().unwrap()).unwrap();
    assert_eq!(hs.runtime, "archeaxis-application");
    assert_eq!(hs.contract, "0.1.0-outline");
    assert!(hs.workspace_ready);
    assert_eq!(hs.schema_version, archeaxis_store_sqlite::SCHEMA_VERSION);
    drop(conn);
}

#[test]
fn job_orchestration_flow() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("app.sqlite");
    let (mut conn, _hs) = bootstrap(db.to_str().unwrap()).unwrap();

    // import a source first (job input_ref = source_id)
    use archeaxis_domain::source;
    let out = source::import_source(&mut conn, b"progress notebook text", "p.txt", None).unwrap();
    let sid = match out {
        source::ImportOutcome::Imported { source_id, .. } => source_id,
        _ => panic!("expected import"),
    };

    // enqueue a transform job for the worker
    jobs::enqueue(&mut conn, "job-1", "transform", &sid).unwrap();
    assert_eq!(jobs::job_state(&conn, "job-1").unwrap().unwrap(), STATE_QUEUED);

    // worker completes with receipt (idempotent re-run keeps single transform row)
    let loss = LossReceipt {
        engine: "python-worker".into(),
        engine_version: "0.1.0".into(),
        params: serde_json::json!({"extractor": "legacy-behavior-oracle"}),
        loss_note: Some("header stripped".into()),
    };
    jobs::complete(&mut conn, "job-1", "python-worker", "progress notebook text (clean)", Some(&loss)).unwrap();
    assert_eq!(jobs::job_state(&conn, "job-1").unwrap().unwrap(), STATE_COMPLETED);

    // text is persisted as a transform receipt by the Rust core
    let text = archeaxis_domain::source::source_text(&conn, &sid).unwrap().unwrap();
    assert!(text.contains("clean"));

    // failed job records an explicit error, never fake success
    jobs::enqueue(&mut conn, "job-2", "ocr", &sid).unwrap();
    jobs::fail(&mut conn, "job-2", "engine unavailable").unwrap();
    assert_eq!(jobs::job_state(&conn, "job-2").unwrap().unwrap(), STATE_FAILED);
}
