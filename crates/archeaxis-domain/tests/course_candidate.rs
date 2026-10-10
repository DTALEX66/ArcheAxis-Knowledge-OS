use archeaxis_domain::{
    anchor, backup,
    course::{self, CourseBinding},
    knowledge,
    source::{self, ImportOutcome},
};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::{Value, json};

fn fixture(conn: &mut Connection) -> (Value, Vec<CourseBinding>) {
    let source_id =
        match source::import_source(conn, b"An anchor locates evidence.", "course.md", None)
            .unwrap()
        {
            ImportOutcome::Imported { source_id, .. } => source_id,
            _ => unreachable!(),
        };
    let revision: String = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&source_id],
            |r| r.get(0),
        )
        .unwrap();
    let anchor_id = anchor::add_anchor(conn, &source_id, &revision, r#"{"line":1}"#).unwrap();
    let kid = knowledge::create_knowledge(
        conn,
        "FACTUAL_CLAIM",
        "An anchor locates evidence.",
        "accepted",
        None,
        Some(&anchor_id),
        "human",
    )
    .unwrap();
    let manifest = json!({"schema":"archeaxis.course-manifest/v1","manifest_id":"course-1","title":"Evidence",
        "domain_pack_id":"general","status":"candidate","knowledge_components":[{"component_id":"kc-1",
        "kind":"fact","title":"Anchor","statement":"An anchor locates evidence.","source_ids":[source_id],"prerequisite_ids":[]}],
        "learning_objectives":[{"objective_id":"obj-1","title":"Find evidence","statement":"Locate an anchor.","knowledge_component_ids":["kc-1"]}],
        "artifacts":[{"schema":"archeaxis.courseware-artifact/v1","artifact_id":"lesson-1","artifact_type":"lesson","title":"Evidence lesson",
        "domain_pack_id":"general","source_ids":[source_id],"knowledge_ids":["kc-1"],"renderer":"native-lesson","renderer_version":"1.0.0",
        "status":"candidate","interactive":false,"derived_only":true,"human_review_required":true}]});
    (
        manifest,
        vec![CourseBinding {
            component_id: "kc-1".into(),
            knowledge_id: kid.clone(),
            knowledge_version: kid,
            source_id,
            source_revision: revision,
        }],
    )
}
fn count(conn: &Connection) -> i64 {
    conn.query_row("SELECT count(*) FROM general_courses", [], |r| r.get(0))
        .unwrap()
}

#[test]
fn atomic_idempotent_course_survives_restart_and_reports_stale_history() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("live.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let (m, b) = fixture(&mut conn);
    let first = course::create_candidate(&mut conn, &m, &b).unwrap();
    assert_eq!(first["stale"], false);
    assert_eq!(course::create_candidate(&mut conn, &m, &b).unwrap(), first);
    let mut conflicting = m.clone();
    conflicting["title"] = json!("different");
    assert!(course::create_candidate(&mut conn, &conflicting, &b).is_err());
    assert_eq!(count(&conn), 1);
    drop(conn);
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        course::read_candidate(&conn, "course-1").unwrap().unwrap(),
        first
    );
    conn.execute(
        "UPDATE knowledge SET status='deprecated' WHERE knowledge_id=?1",
        [&b[0].knowledge_id],
    )
    .unwrap();
    let stale = course::create_candidate(&mut conn, &m, &b).unwrap();
    assert_eq!(stale["stale"], true);
    assert_eq!(stale["manifest"], m);
    assert_eq!(
        stale["bindings"][0]["knowledge_version"],
        b[0].knowledge_version
    );
}

#[test]
fn invalid_binding_and_cross_course_artifact_collision_leave_no_half_course() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("live.sqlite").to_str().unwrap()).unwrap();
    let (m, b) = fixture(&mut conn);
    for field in ["version", "source"] {
        let mut bad = b.clone();
        if field == "version" {
            bad[0].knowledge_version = "other".into();
        } else {
            bad[0].source_revision = "wrong".into();
        }
        assert!(course::create_candidate(&mut conn, &m, &bad).is_err());
        assert_eq!(count(&conn), 0);
    }
    course::create_candidate(&mut conn, &m, &b).unwrap();
    let mut other = m.clone();
    other["manifest_id"] = json!("course-2");
    assert!(course::create_candidate(&mut conn, &other, &b).is_err());
    assert_eq!(count(&conn), 1);
    assert!(course::read_candidate(&conn, "course-2").unwrap().is_none());
}

#[test]
fn unclosed_sources_components_and_unreviewed_artifacts_are_rejected() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("live.sqlite").to_str().unwrap()).unwrap();
    let (m, b) = fixture(&mut conn);
    for case in ["source", "component", "review", "duplicate", "verified"] {
        let mut bad = m.clone();
        match case {
            "source" => bad["artifacts"][0]["source_ids"] = json!(["invented"]),
            "component" => {
                bad["learning_objectives"][0]["knowledge_component_ids"] = json!(["invented"])
            }
            "review" => bad["artifacts"][0]["human_review_required"] = json!(false),
            "duplicate" => {
                let a = bad["artifacts"][0].clone();
                bad["artifacts"].as_array_mut().unwrap().push(a);
            }
            _ => bad["verified"] = json!(true),
        }
        assert!(course::create_candidate(&mut conn, &bad, &b).is_err());
        assert_eq!(count(&conn), 0);
    }
    conn.execute("UPDATE knowledge SET anchor_id=NULL", [])
        .unwrap();
    assert!(course::create_candidate(&mut conn, &m, &b).is_err());
}

#[test]
fn v8_migration_and_online_backup_restore_preserve_candidate() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("live.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let (m, b) = fixture(&mut conn);
    // Synthetic v8 course-shape fixture: later document/teaching tables cannot
    // remain in a database labelled v8. Preserve the actual source/knowledge.
    conn.execute_batch("DROP TABLE teaching_withdrawals;DROP TABLE teaching_records;
        DROP TABLE document_blocks;DROP TABLE document_checks;DROP TABLE document_versions;DROP TABLE documents;
        DROP TABLE general_course_bindings;DROP TABLE general_course_artifacts;DROP TABLE general_courses;
        UPDATE workspace_meta SET value='8' WHERE key='schema_version';").unwrap();
    let later_tables: i64 = conn.query_row(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('teaching_records','teaching_withdrawals','documents','document_versions','document_checks','document_blocks')",
        [], |row| row.get(0),
    ).unwrap();
    assert_eq!(later_tables, 0);
    drop(conn);
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let later_objects: i64 = conn.query_row(
        "SELECT count(*) FROM sqlite_master WHERE name IN ('teaching_records','teaching_withdrawals','documents','document_versions','document_checks','document_blocks','teaching_records_no_update','teaching_records_no_delete','teaching_withdrawals_no_update','teaching_withdrawals_no_delete')",
        [], |row| row.get(0),
    ).unwrap();
    assert_eq!(later_objects, 10);
    let first = course::create_candidate(&mut conn, &m, &b).unwrap();
    let snapshot = dir.path().join("backup.sqlite");
    backup::backup(&conn, snapshot.to_str().unwrap()).unwrap();
    conn.execute_batch("DELETE FROM general_course_bindings;DELETE FROM general_course_artifacts;DELETE FROM general_courses;").unwrap();
    backup::restore(snapshot.to_str().unwrap(), &mut conn).unwrap();
    assert_eq!(
        course::read_candidate(&conn, "course-1").unwrap().unwrap(),
        first
    );
}
