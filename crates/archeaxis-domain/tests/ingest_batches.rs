//! Additive upgrade and independent identity fences; no browser or worker.
use archeaxis_domain::ingest_batches::{self as batches, Member, Register};
use archeaxis_store_sqlite::init_workspace;
fn manifest(conn: &rusqlite::Connection) -> Register {
    let (workspace_id, restore_epoch) = batches::identity(conn).unwrap();
    Register {
        workspace_id,
        restore_epoch,
        batch_id: "durable".into(),
        folder_label: "folder".into(),
        expected_members: 1,
        members: vec![Member {
            ordinal: 0,
            relative_path: "a.md".into(),
            byte_length: 1,
            disposition: "pending".into(),
        }],
    }
}
#[test]
fn additive_upgrade_preserves_sources_and_batch_reopen() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("upgrade.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    archeaxis_domain::source::import_source(&mut conn, b"x", "a.md", None).unwrap();
    // Construct the previous additive schema by removing only the newly introduced tables.
    conn.execute_batch(
        "DROP TABLE ingest_batch_members; DROP TABLE ingest_batches;
        UPDATE workspace_meta SET value='12' WHERE key='schema_version';",
    )
    .unwrap();
    drop(conn);
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        conn.query_row::<String, _, _>(
            "SELECT value FROM workspace_meta WHERE key='schema_version'",
            [],
            |r| r.get(0)
        )
        .unwrap(),
        "13"
    );
    assert_eq!(
        conn.query_row::<i64, _, _>("SELECT count(*) FROM sources", [], |r| r.get(0))
            .unwrap(),
        1
    );
    let body = manifest(&conn);
    batches::register(&mut conn, body).unwrap();
    drop(conn);
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        batches::read(&conn, "durable", None, 200).unwrap()["members"][0]["relative_path"],
        "a.md"
    );
}
#[test]
fn changed_authorization_epoch_and_other_workspace_refuse_frozen_registration() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("fence.sqlite").to_str().unwrap()).unwrap();
    let old = manifest(&conn);
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    assert!(matches!(
        batches::register(&mut conn, old),
        Err(batches::Error::Conflict)
    ));
    let mut body = manifest(&conn);
    body.workspace_id = "another-workspace".into();
    assert!(matches!(
        batches::register(&mut conn, body),
        Err(batches::Error::Conflict)
    ));
    assert_eq!(
        batches::list(&conn, None, 200).unwrap()["batches"],
        serde_json::json!([])
    );
}

#[test]
fn selected_excluded_root_cannot_be_registered_as_ordinary_relative_members() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn =
        init_workspace(dir.path().join("excluded-root.sqlite").to_str().unwrap()).unwrap();
    for root in [
        "node_modules",
        ".venv",
        ".project-local",
        "build",
        "target",
        "NODE_MODULES",
        ".VENV",
        ".PROJECT-LOCAL",
        "BUILD",
        "TARGET",
        ".hg",
        ".svn",
        "__pycache__",
        "venv",
        ".cache",
        "dist",
        ".hidden-folder",
    ] {
        let mut body = manifest(&conn);
        body.folder_label = root.into();
        body.members[0].relative_path = "package/index.md".into();
        assert!(
            matches!(
                batches::register(&mut conn, body),
                Err(batches::Error::Invalid(_))
            ),
            "the selected root {root} must be refused before manifest publication"
        );
        assert_eq!(
            conn.query_row::<i64, _, _>("SELECT count(*) FROM ingest_batches", [], |r| r.get(0))
                .unwrap(),
            0
        );
        assert_eq!(
            conn.query_row::<i64, _, _>("SELECT count(*) FROM ingest_batch_members", [], |r| r
                .get(0))
                .unwrap(),
            0
        );
        assert_eq!(
            conn.query_row::<i64, _, _>("SELECT count(*) FROM sources", [], |r| r.get(0))
                .unwrap(),
            0
        );
        assert_eq!(
            conn.query_row::<i64, _, _>("SELECT count(*) FROM jobs", [], |r| r.get(0))
                .unwrap(),
            0
        );
    }
    let mut ordinary = manifest(&conn);
    ordinary.folder_label = "My node_modules notes".into();
    assert!(
        batches::register(&mut conn, ordinary).unwrap()["complete"]
            .as_bool()
            .unwrap()
    );
}

#[test]
fn earlier_excluded_root_manifest_remains_readable_but_cannot_publish_more_member_work() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn =
        init_workspace(dir.path().join("earlier-root.sqlite").to_str().unwrap()).unwrap();
    let body = manifest(&conn);
    batches::register(&mut conn, body).unwrap();
    // Model persisted pre-fix batches in the real upgraded Store, not replacement tables.
    for root in [".project-local", ".hidden-folder"] {
        conn.execute(
            "UPDATE ingest_batches SET folder_label=?1 WHERE batch_id='durable'",
            [root],
        )
        .unwrap();
        assert_eq!(
            batches::read(&conn, "durable", None, 200).unwrap()["folder_label"],
            root
        );
        assert!(matches!(
            batches::executable_member(&conn, "durable", 0),
            Err(batches::Error::Invalid(_))
        ));
    }
    assert_eq!(
        conn.query_row::<i64, _, _>("SELECT count(*) FROM ingest_batches", [], |r| r.get(0))
            .unwrap(),
        1
    );
    assert_eq!(
        conn.query_row::<i64, _, _>("SELECT count(*) FROM ingest_batch_members", [], |r| r
            .get(0))
            .unwrap(),
        1
    );
}
