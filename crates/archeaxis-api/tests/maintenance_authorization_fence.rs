//! Owned SYNTHETIC knowledge/grant; REAL maintenance subprocess, NOT_EXECUTED until canonical integration.
use archeaxis_domain::{
    backup,
    context_grant::{self, Consumption, Operation},
    document, knowledge, source,
};
use archeaxis_store_sqlite::authorization_fence;
use serde_json::{Value, json};
use std::{path::Path, process::Command};
fn invoke(action: &str, db: &Path, artifact: &Path) -> Value {
    let output = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"))
        .arg(format!("--maintenance-{action}"))
        .arg(db)
        .arg(artifact)
        .output()
        .unwrap();
    let receipt: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert!(output.status.success(), "{receipt}");
    receipt
}
fn editor(kid: &str) -> Value {
    json!({"type":"doc","content":[],"attrs":{"archeaxis_context_grant":{
    "schema":"archeaxis.context-grant/v1","purpose":"owned maintenance fence","consumer":"local-machine",
    "operations":["answer"],"knowledge_id":kid,"provenance":[],"authorization_basis":"SYNTHETIC explicit owner grant",
    "expires_at":null,"state":"granted"},"unknown_future":{"bytes":"preserve exactly"}}})
}
fn input(d: &Value) -> Consumption {
    Consumption {
        document_id: d["document_id"].as_str().unwrap().into(),
        version: d["version"].as_i64().unwrap(),
        content_sha256: d["content_sha256"].as_str().unwrap().into(),
        purpose: "owned maintenance fence".into(),
    }
}
#[test]
fn production_maintenance_restore_of_backup_before_revocation_cannot_revive_grant() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let old = dir.path().join("old.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut c,
        "NOTE",
        "SYNTHETIC context",
        "accepted",
        None,
        None,
        "owner",
    )
    .unwrap();
    source::import_source(&mut c, b"owned original CAS bytes", "original.txt", None).unwrap();
    let granted = document::create_optional_with_request(
        &mut c,
        None,
        None,
        "grant",
        editor(&kid),
        Some("maintenance-original-grant"),
    )
    .unwrap();
    context_grant::consume(&c, &input(&granted), Operation::Answer, &kid, 1).unwrap();
    drop(c);
    assert_eq!(invoke("backup", &db, &old)["ok"], true);
    let source_bytes = std::fs::read(&old).unwrap();
    let mut c = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let mut revoked = granted["editor_json"].clone();
    revoked["attrs"]["archeaxis_context_grant"]["state"] = json!("revoked");
    let revoked =
        document::save(&mut c, granted["document_id"].as_str().unwrap(), 1, revoked).unwrap();
    assert!(context_grant::consume(&c, &input(&revoked), Operation::Answer, &kid, 1).is_err());
    drop(c);
    let restored = invoke("restore", &db, &old);
    assert_eq!(restored["ok"], true);
    assert_eq!(restored["authorization_requires_new_grants"], true);
    let mut c = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        document::read(&c, granted["document_id"].as_str().unwrap(), Some(1)).unwrap(),
        granted
    );
    assert!(context_grant::consume(&c, &input(&granted), Operation::Answer, &kid, 1).is_err());
    let frozen =
        rusqlite::Connection::open_with_flags(&old, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .unwrap();
    assert!(
        !backup::verify_counts(&frozen, &c).unwrap(),
        "generic exact verifier must not be weakened"
    );
    assert!(backup::verify_restored_authorization(&frozen, &c).unwrap());
    let epoch: String = c
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [authorization_fence::KEY],
            |r| r.get(0),
        )
        .unwrap();
    let new = document::create_optional_with_request(
        &mut c,
        None,
        None,
        "new human grant",
        editor(&kid),
        Some("maintenance-renewed-grant"),
    )
    .unwrap();
    context_grant::consume(&c, &input(&new), Operation::Answer, &kid, 1).unwrap();
    drop(c);
    drop(frozen);
    // Replaying the same old backup generates a new epoch and does not inherit its permissions.
    assert_eq!(invoke("restore", &db, &old)["ok"], true);
    let c = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    assert!(context_grant::consume(&c, &input(&granted), Operation::Answer, &kid, 1).is_err());
    assert_ne!(
        epoch,
        c.query_row::<String, _, _>(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [authorization_fence::KEY],
            |r| r.get(0)
        )
        .unwrap()
    );
    assert_eq!(std::fs::read(&old).unwrap(), source_bytes);
}
#[test]
fn specialized_verifier_rejects_other_metadata_body_and_wrong_blocked_set() {
    let dir = tempfile::tempdir().unwrap();
    let a = dir.path().join("a.sqlite");
    let b = dir.path().join("b.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(a.to_str().unwrap()).unwrap();
    document::create_optional_with_request(&mut c,None,None,"body",json!({"type":"doc","content":[],"attrs":{"archeaxis_context_grant":{
        "schema":"archeaxis.context-grant/v1","purpose":"candidate","consumer":"local-machine","operations":[],"knowledge_id":null,
        "provenance":[],"authorization_basis":"","expires_at":null,"state":"candidate"}}}),Some("candidate-fence-id")).unwrap();
    let snapshot = dir.path().join("snapshot.sqlite");
    backup::backup(&c, snapshot.to_str().unwrap()).unwrap();
    let src = rusqlite::Connection::open_with_flags(
        &snapshot,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .unwrap();
    let mut dst = archeaxis_store_sqlite::init_workspace(b.to_str().unwrap()).unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut dst).unwrap();
    assert!(backup::finalize_restore_authorization(&src, &mut dst).unwrap());
    let fence: String = dst
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [authorization_fence::KEY],
            |r| r.get(0),
        )
        .unwrap();
    dst.execute("UPDATE workspace_meta SET value=json_set(value,'$.blocked_grant_ids',json('[]')) WHERE key=?1",[authorization_fence::KEY]).unwrap();
    assert!(!backup::verify_restored_authorization(&src, &dst).unwrap());
    dst.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
        rusqlite::params![fence, authorization_fence::KEY],
    )
    .unwrap();
    dst.execute(
        "INSERT INTO workspace_meta VALUES('unrelated_owner_meta','changed')",
        [],
    )
    .unwrap();
    assert!(!backup::verify_restored_authorization(&src, &dst).unwrap());
    dst.execute(
        "DELETE FROM workspace_meta WHERE key='unrelated_owner_meta'",
        [],
    )
    .unwrap();
    dst.execute(
        "UPDATE document_versions SET text_projection='tampered'",
        [],
    )
    .unwrap();
    assert!(!backup::verify_restored_authorization(&src, &dst).unwrap());
}
#[test]
fn invalid_source_restore_rolls_back_exact_original_authorization() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("live.sqlite");
    let bad = dir.path().join("bad.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut c,
        "NOTE",
        "SYNTHETIC owner context",
        "accepted",
        None,
        None,
        "owner",
    )
    .unwrap();
    let original = document::create_optional_with_request(
        &mut c,
        None,
        None,
        "owner grant",
        editor(&kid),
        Some("rollback-original"),
    )
    .unwrap();
    drop(c);
    std::fs::write(&bad, b"invalid SQLite database").unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_archeaxis-api"))
        .arg("--maintenance-restore")
        .arg(&db)
        .arg(&bad)
        .output()
        .unwrap();
    let receipt: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(receipt["ok"], false);
    assert_eq!(receipt["rolled_back"], true);
    let c = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let previous =
        rusqlite::Connection::open(receipt["preserved_previous"].as_str().unwrap()).unwrap();
    assert!(backup::verify_counts(&previous, &c).unwrap());
    assert_eq!(
        document::read(&c, original["document_id"].as_str().unwrap(), None).unwrap(),
        original
    );
    context_grant::consume(&c, &input(&original), Operation::Answer, &kid, 1).unwrap();
}
