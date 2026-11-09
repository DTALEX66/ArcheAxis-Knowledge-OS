use archeaxis_domain::learning::{self, ScheduleSource};

#[test]
fn archive_preserves_new_request_identity_and_older_limited_receipts() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let request = r#"{"item_key":"new-card","now":"2026-09-02T00:00:00Z"}"#;
    let original = {
        let mut conn = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
        learning::record_http_learning_event(
            &mut conn,
            "new-card",
            "review",
            true,
            "new-key",
            request,
            ScheduleSource::Explicit(None),
        )
        .unwrap();
        learning::record_review_scheduled(
            &mut conn,
            "old-card",
            "review",
            true,
            "old-key",
            Some(37),
        )
        .unwrap();
        let mut stmt = conn
            .prepare("SELECT event_key,payload_hash FROM learning_event_keys ORDER BY event_key")
            .unwrap();
        stmt.query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .unwrap()
        .collect::<Result<Vec<_>, _>>()
        .unwrap()
    };
    let archive = dir.path().join("archive");
    archeaxis_archive::export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    let restored_db = dir.path().join("restored.sqlite");
    archeaxis_archive::restore_workspace(archive.to_str().unwrap(), restored_db.to_str().unwrap())
        .unwrap();
    let conn = archeaxis_store_sqlite::init_workspace(restored_db.to_str().unwrap()).unwrap();
    let restored = {
        let mut stmt = conn
            .prepare("SELECT event_key,payload_hash FROM learning_event_keys ORDER BY event_key")
            .unwrap();
        stmt.query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .unwrap()
        .collect::<Result<Vec<_>, _>>()
        .unwrap()
    };
    assert_eq!(restored, original);
    let new = learning::existing_http_learning_event(
        &conn, "new-card", "review", true, "new-key", request,
    )
    .unwrap()
    .unwrap();
    assert_eq!(new.schedule_authority, "unavailable");
    assert_eq!(new.next_review_days, learning::SCHEDULE_UNAVAILABLE);
    assert_eq!(new.idempotency_scope, "full_request");
    assert!(
        learning::existing_http_learning_event(
            &conn, "new-card", "review", true, "new-key", "changed"
        )
        .is_err()
    );
    let old = learning::existing_http_learning_event(
        &conn,
        "old-card",
        "review",
        true,
        "old-key",
        "unrecorded",
    )
    .unwrap()
    .unwrap();
    assert_eq!(old.schedule_authority, "legacy_unverified");
    assert_eq!(old.next_review_days, 37);
    assert_eq!(old.idempotency_scope, "legacy_item_kind_outcome");
}
