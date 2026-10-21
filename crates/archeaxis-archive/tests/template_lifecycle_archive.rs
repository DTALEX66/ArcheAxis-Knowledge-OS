//! SYNTHETIC schema-13 wire fixture and real schema-14 export/restore.
use archeaxis_archive::{ArchiveManifest, export_workspace, restore_workspace};
use archeaxis_domain::{document, knowledge, learning, source, template_definition};
use archeaxis_store_sqlite::init_workspace;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, path::Path};

fn rows(conn: &rusqlite::Connection, table: &str) -> Vec<Vec<rusqlite::types::Value>> {
    let mut s = conn
        .prepare(&format!("SELECT * FROM {table} ORDER BY rowid"))
        .unwrap();
    let count = s.column_count();
    s.query_map([], |r| (0..count).map(|i| r.get(i)).collect())
        .unwrap()
        .map(Result::unwrap)
        .collect()
}
fn seal(manifest: &mut ArchiveManifest, dir: &Path) {
    let mut digest = Sha256::new();
    digest.update(manifest.schema_version.to_le_bytes());
    for (name, file) in &manifest.tables {
        digest.update(name.as_bytes());
        digest.update(file.rows.to_le_bytes());
        digest.update(file.sha256.as_bytes());
    }
    for (hash, size) in &manifest.raw_objects {
        digest.update(hash.as_bytes());
        digest.update(size.to_le_bytes());
    }
    manifest.manifest_sha256 = hex::encode(digest.finalize());
    std::fs::write(
        dir.join("manifest.json"),
        serde_json::to_vec(manifest).unwrap(),
    )
    .unwrap();
}
#[test]
fn current14_lifecycle_and_authored13_wire_preserve_documents_knowledge_learning_and_original_cas()
{
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("db.sqlite");
    let mut c = init_workspace(db.to_str().unwrap()).unwrap();
    source::import_source(&mut c, b"SYNTHETIC original bytes\n", "owned.txt", None).unwrap();
    document::create_optional(&mut c,None,None,"owned",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"owned body"}]}]})).unwrap();
    let kid = knowledge::create_knowledge(
        &mut c,
        "PERSONAL_DEFINITION",
        "SYNTHETIC owned",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    learning::record_card_reference(&mut c, "owned-learning", &kid, None).unwrap();
    let before: BTreeMap<_, _> = [
        "sources",
        "documents",
        "document_versions",
        "document_blocks",
        "knowledge",
        "card_references",
        "learning_events",
    ]
    .map(|t| (t, rows(&c, t)))
    .into_iter()
    .collect();
    let state = template_definition::record(&c).unwrap();
    template_definition::change(
        &mut c,
        &template_definition::Change {
            expected_epoch: 0,
            action: "uninstall".into(),
            version: 1,
            sha256: state["definition"]["sha256"].as_str().unwrap().into(),
        },
    )
    .unwrap();
    let removed = template_definition::record(&c).unwrap();
    drop(c);
    let archive = dir.path().join("v14");
    let mut manifest = export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    assert_eq!(manifest.schema_version, 14);
    let objects = manifest.raw_objects.clone();
    let restored = dir.path().join("restored14.sqlite");
    restore_workspace(archive.to_str().unwrap(), restored.to_str().unwrap()).unwrap();
    for pass in 0..2 {
        let c = init_workspace(restored.to_str().unwrap()).unwrap();
        assert_eq!(template_definition::record(&c).unwrap(), removed);
        for (table, expected) in &before {
            assert_eq!(&rows(&c, table), expected, "{table} pass {pass}");
        }
    }
    let exported = dir.path().join("roundtrip14");
    assert_eq!(
        export_workspace(restored.to_str().unwrap(), exported.to_str().unwrap())
            .unwrap()
            .raw_objects,
        objects
    );
    for hash in objects.keys() {
        assert_eq!(
            std::fs::read(archive.join("objects").join(hash)).unwrap(),
            std::fs::read(exported.join("objects").join(hash)).unwrap()
        );
    }
    // Authored legacy wire: only old columns, exact schema 13 metadata and the
    // unchanged 34-table set. This is not a claim of a shipped-13 runtime run.
    for table in ["workspace_meta", "capability_settings"] {
        let path = archive.join(format!("{table}.jsonl"));
        let old = std::fs::read_to_string(&path).unwrap();
        let mut lines = String::new();
        for line in old.lines() {
            let mut row: Value = serde_json::from_str(line).unwrap();
            if table == "workspace_meta" && row["key"] == "schema_version" {
                row["value"] = json!("13");
            }
            if table == "capability_settings" {
                for key in ["installed", "definition_version", "state_epoch"] {
                    row.as_object_mut().unwrap().remove(key);
                }
            }
            lines.push_str(&row.to_string());
            lines.push('\n');
        }
        std::fs::write(&path, &lines).unwrap();
        manifest.tables.get_mut(table).unwrap().sha256 =
            hex::encode(Sha256::digest(lines.as_bytes()));
    }
    manifest.schema_version = 13;
    seal(&mut manifest, &archive);
    let upgraded = dir.path().join("upgraded13.sqlite");
    restore_workspace(archive.to_str().unwrap(), upgraded.to_str().unwrap()).unwrap();
    let c = init_workspace(upgraded.to_str().unwrap()).unwrap();
    for (table, expected) in &before {
        assert_eq!(&rows(&c, table), expected, "upgrade {table}");
    }
    let current = template_definition::record(&c).unwrap();
    assert_eq!(current["enabled"], false);
    assert_eq!(current["installed"], true);
    assert_eq!(current["state_epoch"], 0);
    drop(c);
    let check = dir.path().join("upgraded-export");
    assert_eq!(
        export_workspace(upgraded.to_str().unwrap(), check.to_str().unwrap())
            .unwrap()
            .raw_objects,
        objects
    );
    // Fail before publication for bad manifest/table/CAS, future schema, and
    // an old manifest that attempts to supply non-default v14 lifecycle state.
    for (version, folder) in [(13, &archive), (14, &exported)] {
        let manifest_path = folder.join("manifest.json");
        let original = std::fs::read(&manifest_path).unwrap();
        let valid: ArchiveManifest = serde_json::from_slice(&original).unwrap();
        for bad in ["manifest", "table", "cas", "schema", "lifecycle"] {
            if bad == "lifecycle" && version == 14 {
                continue;
            }
            let mut changed = valid.clone();
            let file = match bad {
                "table" => folder.join("documents.jsonl"),
                "cas" => folder.join("objects").join(objects.keys().next().unwrap()),
                "lifecycle" => folder.join("capability_settings.jsonl"),
                _ => manifest_path.clone(),
            };
            let bytes = std::fs::read(&file).unwrap();
            match bad {
                "manifest" => {
                    changed.manifest_sha256 = "0".repeat(64);
                    std::fs::write(&manifest_path, serde_json::to_vec(&changed).unwrap()).unwrap();
                }
                "table" | "cas" => std::fs::write(&file, b"tampered").unwrap(),
                "schema" => {
                    changed.schema_version = 999;
                    seal(&mut changed, folder);
                }
                _ => {
                    let mut row: Value = serde_json::from_slice(&bytes).unwrap();
                    row["installed"] = json!(0);
                    let text = format!("{row}\n");
                    std::fs::write(&file, &text).unwrap();
                    changed
                        .tables
                        .get_mut("capability_settings")
                        .unwrap()
                        .sha256 = hex::encode(Sha256::digest(text.as_bytes()));
                    seal(&mut changed, folder);
                }
            }
            let rejected = dir.path().join(format!("reject-{version}-{bad}.sqlite"));
            assert!(
                restore_workspace(folder.to_str().unwrap(), rejected.to_str().unwrap()).is_err(),
                "{version} {bad}"
            );
            assert!(
                !rejected.exists(),
                "failed restore published {version} {bad}"
            );
            std::fs::write(&file, bytes).unwrap();
            std::fs::write(&manifest_path, &original).unwrap();
        }
    }
}
