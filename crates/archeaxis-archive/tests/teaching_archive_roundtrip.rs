use archeaxis_archive::{ArchiveManifest, export_workspace, restore_workspace};
use archeaxis_domain::{anchor, knowledge, source, teaching::*};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use sha2::{Digest, Sha256};
use std::path::Path;

// Real historical exporters: 7c5a9a0f (v10), 6776eaec (v11).
// This fixture is SYNTHETIC from those wire contracts, not an archived production backup.
const HISTORICAL_28: &[&str] = &[
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
];
fn n(c: &Connection, t: &str) -> i64 {
    c.query_row(&format!("SELECT count(*) FROM {t}"), [], |r| r.get(0))
        .unwrap()
}
fn rewrite(m: &mut ArchiveManifest, p: &Path, t: &str, s: &str) {
    std::fs::write(p.join(format!("{t}.jsonl")), s).unwrap();
    let f = m.tables.get_mut(t).unwrap();
    f.rows = s.lines().count() as u64;
    f.sha256 = hex::encode(Sha256::digest(s.as_bytes()));
}
fn seal(m: &mut ArchiveManifest, p: &Path) {
    let mut h = Sha256::new();
    h.update(m.schema_version.to_le_bytes());
    for (t, f) in &m.tables {
        h.update(t.as_bytes());
        h.update(f.rows.to_le_bytes());
        h.update(f.sha256.as_bytes());
    }
    for (d, b) in &m.raw_objects {
        h.update(d.as_bytes());
        h.update(b.to_le_bytes());
    }
    m.manifest_sha256 = hex::encode(h.finalize());
    std::fs::write(p.join("manifest.json"), serde_json::to_vec(m).unwrap()).unwrap();
}
fn seed(c: &mut Connection) -> String {
    let sid = match source::import_source(c, b"evidence bytes", "note.md", None).unwrap() {
        source::ImportOutcome::Imported { source_id, .. } => source_id,
        _ => panic!("source"),
    };
    let rev: String = c
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&sid],
            |r| r.get(0),
        )
        .unwrap();
    let aid = anchor::add_anchor(c, &sid, &rev, r#"{"line":1}"#).unwrap();
    let kid = knowledge::create_knowledge(
        c,
        "FACTUAL_CLAIM",
        "Original",
        "accepted",
        None,
        Some(&aid),
        "human",
    )
    .unwrap();
    c.execute("INSERT INTO documents(document_id,source_id,source_revision,title,current_version) VALUES('doc',?1,?2,'Document',1)",rusqlite::params![sid,rev]).unwrap();
    c.execute("INSERT INTO document_versions(document_id,version,editor_json,text_projection,content_sha256,revision_basis) VALUES('doc',1,'{}','原稿',?1,'source')",[hex::encode(Sha256::digest("原稿".as_bytes()))]).unwrap();
    c.execute("INSERT INTO document_checks(check_id,document_id,version,dimension,receipt_json) VALUES('check', 'doc',1,'recognition_fidelity','{\"status\":\"review\"}')",[]).unwrap();
    kid
}
fn row(k: RecordKind, id: &str, p: Option<&str>, kid: &str) -> TeachingRecord {
    TeachingRecord {
        schema: RECORD_SCHEMA.into(),
        record_id: id.into(),
        kind: k,
        knowledge_id: kid.into(),
        knowledge_version: kid.into(),
        course_id: None,
        parent_id: p.map(str::to_owned),
        purpose: "Teaching".into(),
        scope: RecordScope::ManualExchange,
        privacy: RecordPrivacy::AuthorizedExport,
        content: "原文\r\n😀 <script>inert</script>".into(),
        feedback_class: None,
        assessment_id: None,
        rubric_version: None,
        assisted: false,
        producer_kind: ProducerKind::HumanAuthored,
    }
}
#[test]
fn schema12_roundtrip_preserves_checks_withdrawals_topology_and_triggers() {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("source.sqlite");
    let a = d.path().join("archive");
    let dest = d.path().join("restored.sqlite");
    let mut c = init_workspace(db.to_str().unwrap()).unwrap();
    let kid = seed(&mut c);
    // Reverse lexical order proves insertion order, not record ID sorting, controls self-FK restoration.
    let rows = [
        row(RecordKind::Observation, "z-root", None, &kid),
        row(RecordKind::Requirement, "y-req", Some("z-root"), &kid),
        row(RecordKind::Proposal, "x-proposal", Some("y-req"), &kid),
        row(RecordKind::Delivery, "a-delivery", Some("x-proposal"), &kid),
        row(RecordKind::TeachBack, "0-child", Some("a-delivery"), &kid),
    ];
    for r in &rows {
        put(&mut c, r).unwrap();
    }
    let wd = Withdrawal {
        schema: WITHDRAWAL_SCHEMA.into(),
        withdrawal_id: "withdrawal".into(),
        record_id: "z-root".into(),
        reason: "Human revoked exchange".into(),
    };
    withdraw(&mut c, &wd).unwrap();
    let before: Vec<(String, String, String)> = c
        .prepare("SELECT record_id,record_json,content_sha256 FROM teaching_records ORDER BY rowid")
        .unwrap()
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .unwrap()
        .map(Result::unwrap)
        .collect();
    drop(c);
    let m = export_workspace(db.to_str().unwrap(), a.to_str().unwrap()).unwrap();
    assert_eq!(m.schema_version, 12);
    assert_eq!(m.tables["document_checks"].rows, 1);
    assert_eq!(m.tables["teaching_records"].rows, 5);
    assert_eq!(m.tables["teaching_withdrawals"].rows, 1);
    restore_workspace(a.to_str().unwrap(), dest.to_str().unwrap()).unwrap();
    let mut c = init_workspace(dest.to_str().unwrap()).unwrap(); // repeated init must leave triggers/data intact
    let after: Vec<(String, String, String)> = c
        .prepare("SELECT record_id,record_json,content_sha256 FROM teaching_records ORDER BY rowid")
        .unwrap()
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))
        .unwrap()
        .map(Result::unwrap)
        .collect();
    assert_eq!(before, after);
    assert_eq!(n(&c, "document_checks"), 1);
    assert_eq!(n(&c, "teaching_withdrawals"), 1);
    for r in &rows {
        assert!(get(&c, &r.record_id).unwrap().unwrap().withdrawn);
        assert!(put(&mut c, r).unwrap().duplicate);
    }
    assert!(export_bundle(&c, "0-child").is_err());
    assert!(
        put(
            &mut c,
            &row(RecordKind::TeachBack, "new-child", Some("a-delivery"), &kid)
        )
        .is_err()
    );
    assert!(withdraw(&mut c, &wd).unwrap().duplicate);
    for table in ["teaching_records", "teaching_withdrawals"] {
        assert!(c.execute(&format!("DELETE FROM {table}"), []).is_err());
        assert!(
            c.execute(&format!("UPDATE {table} SET content_sha256='bad'"), [])
                .is_err()
        );
    }
    assert_eq!(n(&c, "teaching_records"), 5);
    assert_eq!(
        c.query_row(
            "SELECT receipt_json FROM document_checks WHERE check_id='check'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        "{\"status\":\"review\"}"
    );
}
fn historic(version: i64) {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("seed.sqlite");
    let a = d.path().join("archive");
    let dest = d.path().join("target.sqlite");
    let mut c = init_workspace(db.to_str().unwrap()).unwrap();
    seed(&mut c);
    drop(c);
    let mut m = export_workspace(db.to_str().unwrap(), a.to_str().unwrap()).unwrap();
    m.tables.retain(|t, _| HISTORICAL_28.contains(&t.as_str()));
    assert_eq!(m.tables.len(), 28);
    // Write a new fixture tree to omit extra files, rather than deleting any source archive.
    let reduced = d.path().join("historical");
    std::fs::create_dir(&reduced).unwrap();
    for t in HISTORICAL_28 {
        std::fs::copy(
            a.join(format!("{t}.jsonl")),
            reduced.join(format!("{t}.jsonl")),
        )
        .unwrap();
    }
    std::fs::create_dir(reduced.join("objects")).unwrap();
    for digest in m.raw_objects.keys() {
        std::fs::copy(
            a.join("objects").join(digest),
            reduced.join("objects").join(digest),
        )
        .unwrap();
    }
    m.schema_version = version;
    rewrite(
        &mut m,
        &reduced,
        "workspace_meta",
        &format!("{{\"key\":\"schema_version\",\"value\":\"{version}\"}}\n"),
    );
    if version == 10 {
        let s = std::fs::read_to_string(reduced.join("document_versions.jsonl")).unwrap();
        let mut rewritten = String::new();
        for line in s.lines() {
            let mut v: serde_json::Value = serde_json::from_str(line).unwrap();
            v.as_object_mut().unwrap().remove("revision_basis");
            rewritten.push_str(&serde_json::to_string(&v).unwrap());
            rewritten.push('\n');
        }
        rewrite(&mut m, &reduced, "document_versions", &rewritten);
    }
    seal(&mut m, &reduced);
    let receipt = restore_workspace(reduced.to_str().unwrap(), dest.to_str().unwrap()).unwrap();
    assert_eq!(receipt.schema_version, version);
    let c = init_workspace(dest.to_str().unwrap()).unwrap();
    assert_eq!(n(&c, "documents"), 1);
    assert_eq!(n(&c, "document_versions"), 1);
    assert_eq!(n(&c, "document_checks"), 0);
    assert_eq!(n(&c, "teaching_records"), 0);
    assert_eq!(n(&c, "teaching_withdrawals"), 0);
    assert_eq!(
        c.query_row(
            "SELECT value FROM workspace_meta WHERE key='schema_version'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        "12"
    );
    let basis: Option<String> = c
        .query_row("SELECT revision_basis FROM document_versions", [], |r| {
            r.get(0)
        })
        .unwrap();
    assert_eq!(
        basis,
        if version == 10 {
            None
        } else {
            Some("source".into())
        }
    );
    let triggers: i64 = c
        .query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'teaching_%'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(triggers, 4);
}
#[test]
fn historical_v10_contract_restores_with_nullable_added_basis() {
    historic(10)
}
#[test]
fn historical_v11_contract_restores_without_inventing_omitted_checks() {
    historic(11)
}
#[test]
fn current12_missing_table_or_future_version_never_publishes_target() {
    for future in [false, true] {
        let d = tempfile::tempdir().unwrap();
        let db = d.path().join("seed.sqlite");
        let a = d.path().join("archive");
        let dest = d.path().join("must-not-exist.sqlite");
        let mut c = init_workspace(db.to_str().unwrap()).unwrap();
        seed(&mut c);
        drop(c);
        let mut m = export_workspace(db.to_str().unwrap(), a.to_str().unwrap()).unwrap();
        if future {
            m.schema_version = 13;
            rewrite(
                &mut m,
                &a,
                "workspace_meta",
                "{\"key\":\"schema_version\",\"value\":\"13\"}\n",
            );
        } else {
            m.tables.remove("teaching_withdrawals");
        }
        seal(&mut m, &a);
        assert!(restore_workspace(a.to_str().unwrap(), dest.to_str().unwrap()).is_err());
        assert!(!dest.exists());
    }
}
#[test]
fn correctly_rehashed_teaching_fk_break_never_publishes_partial_database() {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("seed.sqlite");
    let a = d.path().join("archive");
    let dest = d.path().join("must-not-exist.sqlite");
    let mut c = init_workspace(db.to_str().unwrap()).unwrap();
    let kid = seed(&mut c);
    put(&mut c, &row(RecordKind::Observation, "root", None, &kid)).unwrap();
    drop(c);
    let mut m = export_workspace(db.to_str().unwrap(), a.to_str().unwrap()).unwrap();
    let s = std::fs::read_to_string(a.join("teaching_records.jsonl")).unwrap();
    let mut v: serde_json::Value = serde_json::from_str(s.trim()).unwrap();
    v["parent_id"] = "absent-parent".into();
    rewrite(&mut m, &a, "teaching_records", &(v.to_string() + "\n"));
    seal(&mut m, &a);
    assert!(restore_workspace(a.to_str().unwrap(), dest.to_str().unwrap()).is_err());
    assert!(!dest.exists());
    // Sealed integrity does not substitute for relational integrity.
    assert!(a.join("manifest.json").is_file());
}
