//! The four tables the archive used to omit must survive an export/restore round trip.
//!
//! `EXPORT_TABLES` did not name `knowledge_v3_metadata`, `learning_assessments`,
//! `card_references` or `machine_tasks`, so an archive carried neither V3 governance metadata,
//! nor human-learning assessments, nor card references, nor machine receipts, and a restore
//! produced a database that looked complete while those rows were gone. Two of the four were
//! created on demand by the domain rather than by the schema, which is why they were missed:
//! a fresh workspace did not have them at all, so an export did not fail - it simply never
//! saw them.
//!
//! The rows here are created through the domain's own entry points, so the test exercises the
//! real column sets rather than a hand-written insert that might drift from them.

use archeaxis_archive::{EXPORT_TABLES, export_workspace, restore_workspace};
use archeaxis_domain::knowledge::{self, KnowledgeV3Metadata};
use archeaxis_domain::learning;
use archeaxis_domain::machine::{self, MachineTask};
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;

/// The four tables this test exists for.
const PREVIOUSLY_OMITTED: &[&str] = &[
    "knowledge_v3_metadata",
    "learning_assessments",
    "card_references",
    "machine_tasks",
];

fn count(conn: &Connection, table: &str) -> i64 {
    conn.query_row(&format!("SELECT count(*) FROM \"{table}\""), [], |r| {
        r.get(0)
    })
    .unwrap()
}

#[test]
fn the_export_names_every_table_it_must_carry() {
    for table in PREVIOUSLY_OMITTED {
        assert!(
            EXPORT_TABLES.contains(table),
            "{table} is not exported, so an archive silently loses it"
        );
    }
}

#[test]
fn a_fresh_workspace_has_every_exported_table() {
    // The export refuses a table that does not exist, so a table created on demand would make
    // the exported set depend on usage history. Every exported table must exist from
    // initialization.
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("fresh.sqlite");
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    for table in EXPORT_TABLES {
        let exists: i64 = conn
            .query_row(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?1",
                [table],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(
            exists, 1,
            "a fresh workspace is missing exported table {table}"
        );
    }
}

#[test]
fn the_previously_omitted_rows_survive_a_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("seed.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();

    let source_id =
        match source::import_source(&mut conn, b"note bytes", "note.txt", None).unwrap() {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
    let knowledge_id = knowledge::create_knowledge_v3(
        &mut conn,
        "NOTE",
        "a ledger note",
        // The knowledge status vocabulary here is the lowercase internal one the domain
        // checks for, not the contracts' upper-case review status.
        "accepted",
        None,
        None,
        "human",
        Some(&KnowledgeV3Metadata {
            source_type: "personal_note".into(),
            owner: "human".into(),
            support_level: "moderate".into(),
            confidence: Some(0.7),
            risk_level: "low".into(),
            valid_from: None,
            valid_to: None,
            external_evidence: Vec::new(),
            requires_human_review: false,
        }),
    )
    .unwrap();
    learning::record_card_reference(&mut conn, "card-1", &knowledge_id, None).unwrap();
    learning::create_assessment(&mut conn, "card-1", &knowledge_id).unwrap();
    machine::record_machine_task(
        &mut conn,
        &MachineTask {
            task_id: "task-1",
            principal: "machine",
            conditions: "none",
            knowledge_version: None,
            method_version: None,
            tool_version: None,
            model_version: "stub/local-stub",
            scope: "probe",
            outcome: "failed",
            failure: Some("declared stub model"),
            retest_of: None,
        },
    )
    .unwrap();
    let _ = source_id;

    for table in PREVIOUSLY_OMITTED {
        assert_eq!(count(&conn, table), 1, "seed produced no row in {table}");
    }
    drop(conn);

    let archive = dir.path().join("archive");
    let manifest = export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    for table in PREVIOUSLY_OMITTED {
        assert!(
            manifest.tables.contains_key(*table),
            "the manifest does not name {table}"
        );
        assert_eq!(manifest.tables[*table].rows, 1, "{table} was not exported");
    }

    let target = dir.path().join("restored.sqlite");
    restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).unwrap();
    let restored =
        Connection::open_with_flags(&target, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
    for table in PREVIOUSLY_OMITTED {
        assert_eq!(
            count(&restored, table),
            1,
            "{table} did not survive the round trip"
        );
    }

    // the content, not only the row counts
    let owner: String = restored
        .query_row(
            "SELECT owner FROM knowledge_v3_metadata WHERE knowledge_id=?1",
            rusqlite::params![knowledge_id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(owner, "human");
    let failure: String = restored
        .query_row(
            "SELECT failure FROM machine_tasks WHERE task_id='task-1'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(failure, "declared stub model");
    let assessment_item: String = restored
        .query_row(
            "SELECT item_key FROM learning_assessments LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(assessment_item, "card-1");
    let referenced: String = restored
        .query_row(
            "SELECT knowledge_id FROM card_references LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(referenced, knowledge_id);
}
