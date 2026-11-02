//! Synthetic archive continuity and restoration fence; no provider invocation.
use archeaxis_archive::{ArchiveManifest, export_workspace, restore_workspace};
use archeaxis_domain::{
    document,
    provider_learning::{self as learning, Activity, Provider, Question, Start, Submission},
    provider_material_grant::Snapshot,
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;

fn snapshot(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}
fn seal(m: &mut ArchiveManifest, dir: &Path) {
    let mut h = Sha256::new();
    h.update(m.schema_version.to_le_bytes());
    for (name, file) in &m.tables {
        h.update(name.as_bytes());
        h.update(file.rows.to_le_bytes());
        h.update(file.sha256.as_bytes());
    }
    for (name, size) in &m.raw_objects {
        h.update(name.as_bytes());
        h.update(size.to_le_bytes());
    }
    m.manifest_sha256 = hex::encode(h.finalize());
    std::fs::write(dir.join("manifest.json"), serde_json::to_vec(m).unwrap()).unwrap();
}
fn doc(c: &mut rusqlite::Connection) -> Value {
    document::create_optional(
        c,
        None,
        None,
        "SYNTHETIC",
        json!({"type":"doc","content":[]}),
    )
    .unwrap()
}
fn activity(source: &Value, provider: &str, g: Option<&Value>) -> Activity {
    Activity {
        activity_id: format!("activity_{provider}"),
        material: snapshot(source),
        provider: Provider {
            id: provider.into(),
            version: (if provider == "deeptutor" {
                "1.7.1"
            } else {
                "1.3.0"
            })
            .into(),
        },
        question: Question {
            question_id: "q1".into(),
            question_version: "unverified_v1".into(),
        },
        grant: g.map(snapshot),
    }
}

#[test]
fn current_archive_preserves_observations_and_fences_unfinished_authorization() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("source.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let source = doc(&mut c);
    let local = activity(&source, "openmaic", None);
    learning::create(&mut c, &local).unwrap();
    learning::start(
        &mut c,
        &local.activity_id,
        &Start {
            attempt_id: "completed".into(),
        },
    )
    .unwrap();
    learning::submit(
        &mut c,
        &local.activity_id,
        "completed",
        &Submission {
            client_event_id: "event".into(),
            answer: "SYNTHETIC".into(),
            provider_correct: None,
            self_report: true,
            rating: None,
        },
    )
    .unwrap();
    let g=document::create_optional(&mut c,None,None,"grant",json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snapshot(&source),"authorization_basis":"SYNTHETIC human permission","expires_at":null,"state":"granted"}}})).unwrap();
    let remote = activity(&source, "deeptutor", Some(&g));
    learning::create(&mut c, &remote).unwrap();
    learning::start(
        &mut c,
        &remote.activity_id,
        &Start {
            attempt_id: "pending".into(),
        },
    )
    .unwrap();
    drop(c);
    let archive = dir.path().join("archive");
    let target = dir.path().join("restored.sqlite");
    let m = export_workspace(path.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    assert_eq!(m.tables["learning_provider_activities"].rows, 2);
    assert_eq!(m.tables["learning_provider_attempts"].rows, 2);
    restore_workspace(archive.to_str().unwrap(), target.to_str().unwrap()).unwrap();
    let mut restored = archeaxis_store_sqlite::init_workspace(target.to_str().unwrap()).unwrap();
    let history = learning::read(&restored, &local.activity_id, None).unwrap();
    assert_eq!(history["attempts"][0]["result"]["answer"], "SYNTHETIC");
    assert_eq!(
        learning::read(&restored, &remote.activity_id, None).unwrap()["attempts"][0]["state"],
        "pending"
    );
    assert!(
        learning::start(
            &mut restored,
            &remote.activity_id,
            &Start {
                attempt_id: "pending".into()
            }
        )
        .is_err()
    );
    assert!(
        learning::start(
            &mut restored,
            &remote.activity_id,
            &Start {
                attempt_id: "fresh".into()
            }
        )
        .is_err()
    );
    assert_eq!(
        restored
            .query_row("SELECT count(*) FROM learning_provider_attempts", [], |r| r
                .get::<_, i64>(0))
            .unwrap(),
        2
    );
}

#[test]
fn v14_archive_restores_old_objects_with_empty_new_tables_and_rejects_future_layout() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("source.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let original = doc(&mut c);
    drop(c);
    let archive = dir.path().join("archive");
    let mut m = export_workspace(path.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    let future_a = m.tables.remove("learning_provider_activities").unwrap();
    let future_b = m.tables.remove("learning_provider_attempts").unwrap();
    m.schema_version = 14;
    let metadata = archive.join("workspace_meta.jsonl");
    let old = std::fs::read_to_string(&metadata).unwrap();
    let mut rewritten = String::new();
    for line in old.lines() {
        let mut row: Value = serde_json::from_str(line).unwrap();
        if row["key"] == "schema_version" {
            row["value"] = json!("14");
        }
        rewritten.push_str(&row.to_string());
        rewritten.push('\n');
    }
    std::fs::write(&metadata, &rewritten).unwrap();
    m.tables.get_mut("workspace_meta").unwrap().sha256 =
        hex::encode(Sha256::digest(rewritten.as_bytes()));
    seal(&mut m, &archive);
    let restored = dir.path().join("restored.sqlite");
    restore_workspace(archive.to_str().unwrap(), restored.to_str().unwrap()).unwrap();
    let c = archeaxis_store_sqlite::init_workspace(restored.to_str().unwrap()).unwrap();
    assert_eq!(
        document::read(&c, original["document_id"].as_str().unwrap(), Some(1)).unwrap(),
        original
    );
    for table in ["learning_provider_activities", "learning_provider_attempts"] {
        assert_eq!(
            c.query_row(&format!("SELECT count(*) FROM {table}"), [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }
    m.tables
        .insert("learning_provider_activities".into(), future_a);
    m.tables
        .insert("learning_provider_attempts".into(), future_b);
    seal(&mut m, &archive);
    let invalid = dir.path().join("rejected.sqlite");
    assert!(restore_workspace(archive.to_str().unwrap(), invalid.to_str().unwrap()).is_err());
    assert!(!invalid.exists());
}
