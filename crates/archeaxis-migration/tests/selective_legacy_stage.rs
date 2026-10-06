//! Owner ruling 2026-10-06: merge what the mainline can express, drop the rest by name.
//!
//! The fixture mirrors the real Cognitive-OS library shape: human intake cards, machine
//! lessons, content rows, legacy bookkeeping, a full-text shadow table and an empty table.
//! What is asserted: legal types and owners, human review still required, every exported
//! table named exactly once with an action and a reason, idempotent re-runs, and no write
//! to the legacy database.

use archeaxis_migration::{export_jsonl, stage_legacy_library_selectively};
use rusqlite::Connection;

fn make_legacy(dir: &std::path::Path) -> String {
    let db = dir.join("cognitive_os_legacy.sqlite");
    let conn = Connection::open(&db).unwrap();
    conn.execute_batch(
        "CREATE TABLE ir_intake_cards(id TEXT PRIMARY KEY, title TEXT, why TEXT,
             what_to_absorb_json TEXT, what_not_to_absorb_json TEXT, source_ids_json TEXT,
             risk_level TEXT, target_repo TEXT, created_at TEXT);
         CREATE TABLE machine_lessons(id TEXT PRIMARY KEY, pattern TEXT, lesson_type TEXT,
             future_constraint TEXT, evidence_trace_id TEXT, created_at TEXT);
         CREATE TABLE core_objects(id TEXT PRIMARY KEY, object_type TEXT, content TEXT,
             source TEXT, metadata_json TEXT, created_at TEXT);
         CREATE TABLE schema_migrations(version INTEGER, name TEXT, applied_at TEXT);
         CREATE TABLE core_objects_fts_data(id INTEGER, block BLOB);
         CREATE TABLE episodic_memory(id TEXT PRIMARY KEY, content TEXT);",
    )
    .unwrap();
    conn.execute(
        "INSERT INTO ir_intake_cards VALUES('intake_1','考霸学习法 - 目标设定模块',
         '以目标设定为核心，可吸收为学习方法知识',
         '[\"目标设定原则\",\"每日计划执行\"]','[\"具体课程广告\"]','[]','low','ArcheAxis',
         '2026-08-13 13:50:37')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO ir_intake_cards VALUES('intake_2','','','','','','','',NULL)",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO machine_lessons VALUES('lesson_1','pipeline failed','failure',
         'require attributable non-dry-run tool evidence','trace_1','2026-08-12T18:02:31')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO core_objects VALUES('obj_1','document','人生的意义 伊格尔顿',
         'ingest-samples/oxford-meaning.pdf','{}','2026-08-12T18:02:04')",
        [],
    )
    .unwrap();
    conn.execute(
        "INSERT INTO schema_migrations VALUES(2,'taskpack_contract_v1','2026-08-12 17:45:57')",
        [],
    )
    .unwrap();
    conn.execute("INSERT INTO core_objects_fts_data VALUES(1, x'00')", [])
        .unwrap();
    drop(conn);
    db.to_str().unwrap().to_string()
}

fn knowledge_rows(db: &str) -> Vec<(String, String, String, String)> {
    let conn = Connection::open(db).unwrap();
    let mut statement = conn
        .prepare("SELECT knowledge_id, knowledge_type, status, created_by FROM knowledge ORDER BY knowledge_id")
        .unwrap();
    statement
        .query_map([], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
        })
        .unwrap()
        .collect::<Result<Vec<_>, _>>()
        .unwrap()
}

fn metadata_rows(db: &str) -> Vec<(String, String, String, i64)> {
    let conn = Connection::open(db).unwrap();
    let mut statement = conn
        .prepare(
            "SELECT m.source_type, m.owner, m.support_level, m.requires_human_review
             FROM knowledge_v3_metadata m JOIN knowledge k ON k.knowledge_id=m.knowledge_id
             ORDER BY m.knowledge_id",
        )
        .unwrap();
    statement
        .query_map([], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
        })
        .unwrap()
        .collect::<Result<Vec<_>, _>>()
        .unwrap()
}

#[test]
fn useful_tables_merge_and_every_other_table_is_named() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let out = dir.path().join("export").to_str().unwrap().to_string();

    export_jsonl(&db, &out).unwrap();
    let staging = dir.path().join("staging.sqlite");
    let result = stage_legacy_library_selectively(&out, staging.to_str().unwrap()).unwrap();

    assert_eq!(result.intake_cards_seen, 2);
    assert_eq!(
        result.intake_cards_staged, 1,
        "the untitled card carries nothing"
    );
    assert_eq!(result.lessons_seen, 1);
    assert_eq!(result.lessons_staged, 1);
    assert_eq!(result.row_errors, 1);

    let knowledge = knowledge_rows(staging.to_str().unwrap());
    assert_eq!(
        knowledge.len(),
        2,
        "only the merged rows reach the mainline shape"
    );
    assert!(
        knowledge
            .iter()
            .all(|(_, _, status, _)| status == "candidate"),
        "imported legacy content is never auto-accepted: {knowledge:?}"
    );
    let types: Vec<&str> = knowledge
        .iter()
        .map(|(_, kind, _, _)| kind.as_str())
        .collect();
    assert!(types.contains(&"PERSONAL_DEFINITION") && types.contains(&"OBSERVATION"));

    let metadata = metadata_rows(staging.to_str().unwrap());
    assert_eq!(metadata.len(), 2);
    assert!(
        metadata.iter().all(|(_, _, _, review)| *review == 1),
        "legacy imports always require human review: {metadata:?}"
    );
    assert!(
        metadata
            .iter()
            .any(|(source, owner, support, _)| source == "imported_legacy"
                && owner == "human"
                && support == "none")
    );
    assert!(
        metadata
            .iter()
            .any(|(source, owner, _, _)| source == "machine_candidate" && owner == "machine")
    );

    // Every exported table gets exactly one disposition, and no table is unaccounted for.
    let exported = super_tables(&out);
    let named: Vec<&str> = result
        .dispositions
        .iter()
        .map(|d| d.table.as_str())
        .collect();
    assert_eq!(named.len(), result.dispositions.len());
    for table in &exported {
        assert!(
            named.contains(&table.as_str()),
            "{table} has no disposition"
        );
    }
    assert_eq!(named.len(), exported.len() + result_unreadable(&out));
    for entry in &result.dispositions {
        assert!(
            matches!(entry.action.as_str(), "merged" | "discarded" | "not_merged"),
            "{entry:?}"
        );
        assert!(!entry.reason.is_empty(), "{entry:?}");
    }
    let action = |name: &str| {
        result
            .dispositions
            .iter()
            .find(|d| d.table == name)
            .map(|d| d.action.clone())
            .unwrap()
    };
    assert_eq!(action("ir_intake_cards"), "merged");
    assert_eq!(action("machine_lessons"), "merged");
    assert_eq!(action("core_objects"), "not_merged");
    assert_eq!(action("episodic_memory"), "discarded", "0 rows");
    assert_eq!(action("schema_migrations"), "discarded");
    assert_eq!(action("core_objects_fts_data"), "discarded");

    // Re-running replays the same rows instead of duplicating them.
    let again = stage_legacy_library_selectively(&out, staging.to_str().unwrap()).unwrap();
    assert_eq!(again.intake_cards_staged, 0);
    assert_eq!(again.lessons_staged, 0);
    assert_eq!(again.reused, 2);
    assert_eq!(knowledge_rows(staging.to_str().unwrap()).len(), 2);
}

#[test]
fn tampered_export_is_rejected_before_any_staging_write() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let out = dir.path().join("export").to_str().unwrap().to_string();
    export_jsonl(&db, &out).unwrap();
    let cards = std::path::Path::new(&out).join("ir_intake_cards.jsonl");
    let mut bytes = std::fs::read(&cards).unwrap();
    bytes[0] ^= 0xFF;
    std::fs::write(&cards, bytes).unwrap();
    let staging = dir.path().join("staging.sqlite");
    assert!(stage_legacy_library_selectively(&out, staging.to_str().unwrap()).is_err());
    assert!(
        !staging.exists(),
        "a rejected export must not create a staging database"
    );
}

#[test]
fn the_legacy_library_bytes_are_untouched() {
    let dir = tempfile::tempdir().unwrap();
    let db = make_legacy(dir.path());
    let before = std::fs::read(&db).unwrap();
    let out = dir.path().join("export").to_str().unwrap().to_string();
    export_jsonl(&db, &out).unwrap();
    let staging = dir.path().join("staging.sqlite");
    stage_legacy_library_selectively(&out, staging.to_str().unwrap()).unwrap();
    assert_eq!(before, std::fs::read(&db).unwrap());
}

/// Table names the export manifest recorded.
fn super_tables(export_dir: &str) -> Vec<String> {
    manifest(export_dir).tables.keys().cloned().collect()
}

fn result_unreadable(export_dir: &str) -> usize {
    manifest(export_dir).unqueried_tables.len()
}

fn manifest(export_dir: &str) -> archeaxis_migration::ExportManifest {
    let raw =
        std::fs::read_to_string(std::path::Path::new(export_dir).join("export-manifest.json"))
            .unwrap();
    serde_json::from_str(&raw).unwrap()
}
