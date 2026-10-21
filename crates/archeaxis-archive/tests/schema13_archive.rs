//! Authored schema fixtures exercise the real archive writer and restorer.
use archeaxis_archive::{ArchiveManifest, export_workspace, restore_workspace};
use archeaxis_domain::source::{ImportOutcome, import_source};
use archeaxis_store_sqlite::{SCHEMA_VERSION, init_workspace};
use rusqlite::{Connection, params};
use sha2::{Digest, Sha256};
use std::path::Path;

const ADDED: [&str; 3] = [
    "ingest_batches",
    "ingest_batch_members",
    "public_research_runs",
];
// Independently pinned v12 exporter layout, not a slice of the current inventory.
const V12: &[&str] = &[
    "workspace_meta",
    "sources",
    "transforms",
    "anchors",
    "knowledge",
    "review_events",
    "learning_events",
    "jobs",
    "job_attempts",
    "job_outputs",
    "canvas_projections",
    "canvas_projection_nodes",
    "canvas_projection_edges",
    "source_origins",
    "learning_event_keys",
    "knowledge_supersedes",
    "knowledge_v3_metadata",
    "learning_assessments",
    "card_references",
    "machine_tasks",
    "capability_settings",
    "vault_links",
    "general_courses",
    "general_course_artifacts",
    "general_course_bindings",
    "documents",
    "document_versions",
    "document_blocks",
    "document_checks",
    "teaching_records",
    "teaching_withdrawals",
];

fn seed(db: &Path) {
    let mut c = init_workspace(db.to_str().unwrap()).unwrap();
    let bytes = b"Authored source for archive continuity.\n";
    let sid = match import_source(&mut c, bytes, "note.md", None).unwrap() {
        ImportOutcome::Imported { source_id, .. } => source_id,
        _ => panic!("fresh source required"),
    };
    let digest = hex::encode(Sha256::digest(bytes));
    c.execute("INSERT INTO ingest_batches(batch_id,folder_label,expected_members) VALUES('batch','notes',1)", []).unwrap();
    c.execute("INSERT INTO ingest_batch_members(batch_id,ordinal,relative_path,byte_length,disposition,source_id,source_revision) VALUES('batch',0,'note.md',?1,'pending',?2,?3)", params![bytes.len() as i64, sid, digest]).unwrap();
    // Storage qualification only: this authored receipt is not a public-network run.
    c.execute(r#"INSERT INTO public_research_runs(request_id,workspace_id,restore_epoch,request_json,state,receipt_json) VALUES('research','authored-workspace','initial','{"query":"authored"}','complete','{"authored":true}')"#, []).unwrap();
}

fn seal(m: &mut ArchiveManifest, dir: &Path) {
    let mut hash = Sha256::new();
    hash.update(m.schema_version.to_le_bytes());
    for (name, file) in &m.tables {
        hash.update(name.as_bytes());
        hash.update(file.rows.to_le_bytes());
        hash.update(file.sha256.as_bytes());
    }
    for (digest, size) in &m.raw_objects {
        hash.update(digest.as_bytes());
        hash.update(size.to_le_bytes());
    }
    m.manifest_sha256 = hex::encode(hash.finalize());
    std::fs::write(dir.join("manifest.json"), serde_json::to_vec(m).unwrap()).unwrap();
}

fn rows(c: &Connection, table: &str) -> String {
    let mut stmt = c
        .prepare(&format!("SELECT * FROM {table} ORDER BY rowid"))
        .unwrap();
    let count = stmt.column_count();
    let values: Vec<Vec<rusqlite::types::Value>> = stmt
        .query_map([], |row| (0..count).map(|i| row.get(i)).collect())
        .unwrap()
        .map(Result::unwrap)
        .collect();
    format!("{values:?}")
}

#[test]
fn current_archive_preserves_batch_and_research_rows_and_originals() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source.sqlite");
    let archive = dir.path().join("archive");
    let target = dir.path().join("restored.sqlite");
    seed(&db);
    let manifest = export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    assert_eq!(manifest.schema_version, SCHEMA_VERSION);
    for table in ADDED {
        assert_eq!(
            manifest.tables.get(table).map(|f| f.rows),
            Some(1),
            "missing {table}"
        );
    }
    let old = init_workspace(db.to_str().unwrap()).unwrap();
    let original: Vec<_> = ADDED.iter().map(|table| rows(&old, table)).collect();
    drop(old);
    restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).unwrap();
    for _ in 0..2 {
        let restored = init_workspace(target.to_str().unwrap()).unwrap();
        for (table, expected) in ADDED.iter().zip(&original) {
            assert_eq!(&rows(&restored, table), expected, "changed {table}");
        }
        let digest: String = restored
            .query_row("SELECT sha256 FROM sources", [], |r| r.get(0))
            .unwrap();
        assert_eq!(
            archeaxis_store_sqlite::raw_objects::read(&restored, &digest).unwrap(),
            b"Authored source for archive continuity.\n"
        );
    }
    let collision = std::fs::read(&target).unwrap();
    assert!(restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).is_err());
    assert_eq!(std::fs::read(&target).unwrap(), collision);
}

#[test]
fn fixed_v12_layout_restores_without_inventing_new_batch_or_research_rows() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("source.sqlite");
    let archive = dir.path().join("current");
    let historical = dir.path().join("historical12");
    let target = dir.path().join("restored.sqlite");
    seed(&db);
    let mut m = export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    std::fs::create_dir(&historical).unwrap();
    m.tables.retain(|name, _| V12.contains(&name.as_str()));
    assert_eq!(m.tables.len(), 31);
    for table in V12 {
        std::fs::copy(
            archive.join(format!("{table}.jsonl")),
            historical.join(format!("{table}.jsonl")),
        )
        .unwrap();
    }
    std::fs::create_dir(historical.join("objects")).unwrap();
    for digest in m.raw_objects.keys() {
        std::fs::copy(
            archive.join("objects").join(digest),
            historical.join("objects").join(digest),
        )
        .unwrap();
    }
    m.schema_version = 12;
    let metadata = "{\"key\":\"schema_version\",\"value\":\"12\"}\n";
    std::fs::write(historical.join("workspace_meta.jsonl"), metadata).unwrap();
    let file = m.tables.get_mut("workspace_meta").unwrap();
    file.rows = 1;
    file.sha256 = hex::encode(Sha256::digest(metadata));
    seal(&mut m, &historical);
    let receipt =
        restore_workspace(historical.to_str().unwrap(), target.to_str().unwrap()).unwrap();
    assert_eq!(receipt.schema_version, 12);
    let c = init_workspace(target.to_str().unwrap()).unwrap();
    for table in ADDED {
        assert_eq!(rows(&c, table), "[]");
    }
    assert_eq!(
        c.query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        SCHEMA_VERSION.to_string()
    );
    assert_eq!(
        c.query_row("SELECT count(*) FROM sources", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        1
    );
}

#[test]
fn current_missing_any_new_table_and_v12_with_new_tables_fail_before_publication() {
    for removed in ADDED.into_iter().map(Some).chain([None]) {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("source.sqlite");
        let archive = dir.path().join("archive");
        let target = dir.path().join("must-not-exist.sqlite");
        seed(&db);
        let mut m = export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
        if let Some(table) = removed {
            assert!(
                m.tables.remove(table).is_some(),
                "current export omitted {table}"
            );
        } else {
            m.schema_version = 12;
        }
        seal(&mut m, &archive);
        assert!(restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).is_err());
        assert!(!target.exists());
        assert!(!dir.path().join("must-not-exist.sqlite.objects").exists());
    }
}
