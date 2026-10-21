//! SYNTHETIC owned SQLite snapshots; Core migration/Document paths, no fixture credentials.
use archeaxis_domain::{document, template_definition};
use serde_json::json;

#[test]
fn additive_v13_upgrade_preserves_documents_capability_decisions_and_rejects_future_downgrade() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let saved = document::create_optional(
        &mut conn,
        None,
        None,
        "SYNTHETIC old object",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    archeaxis_store_sqlite::capability_settings::set_enabled(&conn, "course.general", false)
        .unwrap();
    // Construct the exact old shape only in this disposable regression fixture.
    conn.execute_batch("ALTER TABLE capability_settings DROP COLUMN state_epoch; ALTER TABLE capability_settings DROP COLUMN definition_version; ALTER TABLE capability_settings DROP COLUMN installed; UPDATE workspace_meta SET value='13' WHERE key='schema_version';").unwrap();
    drop(conn);
    let conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        document::read(&conn, saved["document_id"].as_str().unwrap(), Some(1)).unwrap(),
        saved
    );
    assert!(
        !archeaxis_store_sqlite::capability_settings::is_enabled(&conn, "course.general").unwrap()
    );
    let state = template_definition::record(&conn).unwrap();
    assert_eq!(state["state_epoch"], 0);
    assert_eq!(state["definition"]["version"], 1);
    let tables: i64 = conn
        .query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='table'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    drop(conn);
    let conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        tables,
        conn.query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='table'",
            [],
            |r| r.get::<_, i64>(0)
        )
        .unwrap()
    );
    conn.execute(
        "UPDATE workspace_meta SET value='999' WHERE key='schema_version'",
        [],
    )
    .unwrap();
    drop(conn);
    assert!(archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).is_err());
}

#[test]
fn invalid_t3_pin_cannot_be_null_and_first_addition_to_existing_ordinary_document_is_guarded() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let saved = document::create_optional(
        &mut conn,
        None,
        None,
        "ordinary",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let initial = template_definition::record(&conn).unwrap();
    let request = template_definition::Change {
        expected_epoch: 0,
        action: "uninstall".into(),
        version: 1,
        sha256: initial["definition"]["sha256"].as_str().unwrap().into(),
    };
    template_definition::change(&mut conn, &request).unwrap();
    let mut edited = saved["editor_json"].clone();
    edited["attrs"] = json!({"archeaxis_template":{"schema":"archeaxis.template/v1","template_id":"T3","discipline_id":"math","fields":{},"references":[],"learning_item_key":null}});
    let id = saved["document_id"].as_str().unwrap();
    assert!(document::save(&mut conn, id, 1, edited.clone()).is_err());
    edited["attrs"]["archeaxis_template"]["definition"] = serde_json::Value::Null;
    assert!(document::save(&mut conn, id, 1, edited).is_err());
    assert_eq!(document::read(&conn, id, None).unwrap(), saved);
}

#[test]
fn sqlite_backup_13_upgrade_and_14_restore_keep_originals_and_all_old_rows() {
    use archeaxis_domain::{backup, knowledge, learning, source};
    use archeaxis_store_sqlite::raw_objects;
    for version in [13, 14] {
        let dir = tempfile::tempdir().unwrap();
        let original = dir.path().join("source.sqlite");
        let mut c = archeaxis_store_sqlite::init_workspace(original.to_str().unwrap()).unwrap();
        source::import_source(&mut c, b"SYNTHETIC original CAS bytes", "owned.txt", None).unwrap();
        let saved = document::create_optional(
            &mut c,
            None,
            None,
            "owned",
            json!({"type":"doc","content":[]}),
        )
        .unwrap();
        let k = knowledge::create_knowledge(
            &mut c,
            "PERSONAL_DEFINITION",
            "owned knowledge",
            "accepted",
            None,
            None,
            "human",
        )
        .unwrap();
        learning::record_card_reference(&mut c, "owned-card", &k, None).unwrap();
        archeaxis_store_sqlite::capability_settings::set_enabled(&c, "course.general", false)
            .unwrap();
        if version == 13 {
            c.execute_batch("ALTER TABLE capability_settings DROP COLUMN state_epoch;ALTER TABLE capability_settings DROP COLUMN definition_version;ALTER TABLE capability_settings DROP COLUMN installed;UPDATE workspace_meta SET value='13' WHERE key='schema_version';").unwrap();
        } else {
            template_definition::set_enabled(&mut c, false).unwrap();
        }
        let snapshot = dir.path().join("backup.sqlite");
        backup::backup(&c, snapshot.to_str().unwrap()).unwrap();
        let before = std::fs::read(&snapshot).unwrap();
        let source = rusqlite::Connection::open_with_flags(
            &snapshot,
            rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
        )
        .unwrap();
        let mut target = archeaxis_store_sqlite::init_workspace(
            dir.path().join("target.sqlite").to_str().unwrap(),
        )
        .unwrap();
        backup::preview(&snapshot).unwrap();
        backup::restore(snapshot.to_str().unwrap(), &mut target).unwrap();
        assert!(backup::verify_counts(&source, &target).unwrap());
        assert!(backup::finalize_restore_authorization(&source, &mut target).unwrap());
        assert!(backup::verify_restored_authorization(&source, &target).unwrap());
        assert_eq!(
            document::read(&target, saved["document_id"].as_str().unwrap(), Some(1)).unwrap(),
            saved
        );
        let digest: String = target
            .query_row("SELECT sha256 FROM sources", [], |r| r.get(0))
            .unwrap();
        assert_eq!(
            raw_objects::read(&target, &digest).unwrap(),
            b"SYNTHETIC original CAS bytes"
        );
        assert!(
            !archeaxis_store_sqlite::capability_settings::is_enabled(&target, "course.general")
                .unwrap()
        );
        assert_eq!(
            target
                .query_row(
                    "SELECT count(*) FROM card_references WHERE item_key='owned-card'",
                    [],
                    |r| r.get::<_, i64>(0)
                )
                .unwrap(),
            1
        );
        assert_eq!(
            target
                .query_row(
                    "SELECT body FROM knowledge WHERE knowledge_id=?1",
                    [k],
                    |r| r.get::<_, String>(0)
                )
                .unwrap(),
            "owned knowledge"
        );
        assert_eq!(
            target
                .query_row(
                    "SELECT value FROM workspace_meta WHERE key='schema_version'",
                    [],
                    |r| r.get::<_, String>(0)
                )
                .unwrap(),
            "14"
        );
        assert_eq!(std::fs::read(&snapshot).unwrap(), before);
        if version == 13 {
            // Cross-version comparison must not hide changed enabled/timestamp or
            // a lifecycle default that did not come from the migration.
            for sql in [
                "UPDATE capability_settings SET installed=0",
                "UPDATE capability_settings SET changed_at='tampered'",
                "UPDATE capability_settings SET enabled=1",
            ] {
                let before:(i64,String,i64)=target.query_row("SELECT installed,changed_at,enabled FROM capability_settings WHERE capability='course.general'",[],|r|Ok((r.get(0)?,r.get(1)?,r.get(2)?))).unwrap();
                target.execute(sql, []).unwrap();
                assert!(!backup::verify_restored_authorization(&source, &target).unwrap());
                target.execute("UPDATE capability_settings SET installed=?1,changed_at=?2,enabled=?3 WHERE capability='course.general'",rusqlite::params![before.0,before.1,before.2]).unwrap();
            }
            target.execute_batch("ALTER TABLE capability_settings RENAME TO saved_capability_settings;CREATE TABLE capability_settings(capability TEXT PRIMARY KEY,enabled INTEGER NOT NULL,changed_at TEXT NOT NULL,installed INTEGER NOT NULL DEFAULT 1,definition_version INTEGER NOT NULL DEFAULT 1,state_epoch INTEGER NOT NULL DEFAULT 0);INSERT INTO capability_settings SELECT * FROM saved_capability_settings;DROP TABLE saved_capability_settings;").unwrap();
            assert!(!backup::verify_restored_authorization(&source, &target).unwrap());
        }
    }
}

#[test]
fn sqlite_restore_rejects_unknown_schema_and_bad_cas_before_overwriting_target() {
    use archeaxis_domain::{backup, source};
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("source.sqlite").to_str().unwrap())
            .unwrap();
    source::import_source(&mut c, b"owned original", "owned.txt", None).unwrap();
    let snapshot = dir.path().join("backup.sqlite");
    backup::backup(&c, snapshot.to_str().unwrap()).unwrap();
    let mut target =
        archeaxis_store_sqlite::init_workspace(dir.path().join("target.sqlite").to_str().unwrap())
            .unwrap();
    let saved = document::create_optional(
        &mut target,
        None,
        None,
        "target retained",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let archived = rusqlite::Connection::open(&snapshot).unwrap();
    archived
        .execute(
            "UPDATE workspace_meta SET value='999' WHERE key='schema_version'",
            [],
        )
        .unwrap();
    assert!(backup::preview(&snapshot).is_err());
    assert!(backup::restore(snapshot.to_str().unwrap(), &mut target).is_err());
    archived
        .execute(
            "UPDATE workspace_meta SET value='13' WHERE key='schema_version'",
            [],
        )
        .unwrap();
    let digest: String = archived
        .query_row("SELECT sha256 FROM sources", [], |r| r.get(0))
        .unwrap();
    std::fs::write(
        archeaxis_store_sqlite::raw_objects::root(&archived)
            .unwrap()
            .join(digest),
        b"bad digest",
    )
    .unwrap();
    drop(archived);
    assert!(backup::preview(&snapshot).is_err());
    assert!(backup::restore(snapshot.to_str().unwrap(), &mut target).is_err());
    assert_eq!(
        document::read(&target, saved["document_id"].as_str().unwrap(), None).unwrap(),
        saved
    );
}
