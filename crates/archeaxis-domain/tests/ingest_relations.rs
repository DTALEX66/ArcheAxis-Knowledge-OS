//! Synthetic domain boundaries over real CAS/SQLite, not external Vault access.
use archeaxis_domain::{
    document,
    ingest_batches::{self as batches, Member, Register},
    ingest_relations::{self as links, Apply, DocumentBinding, Target},
    relation_projection,
    source::{self, ImportOutcome},
};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::params;
use serde_json::{Value, json};

struct Fixture {
    _dir: tempfile::TempDir,
    path: std::path::PathBuf,
    conn: rusqlite::Connection,
    request: Apply,
    original: Value,
}
impl Fixture {
    fn new(text: &str, paths: &[(&str, &str)]) -> Self {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("workspace.sqlite");
        let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
        let (workspace_id, restore_epoch) = batches::identity(&conn).unwrap();
        let files: Vec<_> = std::iter::once(("notes/start.md", text))
            .chain(paths.iter().copied())
            .collect();
        batches::register(
            &mut conn,
            Register {
                workspace_id: workspace_id.clone(),
                restore_epoch: restore_epoch.clone(),
                batch_id: "batch".into(),
                folder_label: "selected".into(),
                expected_members: files.len() as i64,
                members: files
                    .iter()
                    .enumerate()
                    .map(|(i, (path, text))| Member {
                        ordinal: i as i64,
                        relative_path: (*path).into(),
                        byte_length: text.len() as i64,
                        disposition: "pending".into(),
                    })
                    .collect(),
            },
        )
        .unwrap();
        let mut docs = Vec::new();
        let mut targets = Vec::new();
        let mut source_ids = Vec::new();
        for (i, (path, text)) in files.iter().enumerate() {
            let (id, sha) =
                match source::import_source(&mut conn, text.as_bytes(), path, None).unwrap() {
                    ImportOutcome::Imported { source_id, sha256 }
                    | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
                };
            conn.execute("UPDATE ingest_batch_members SET source_id=?1,source_revision=?2 WHERE batch_id='batch' AND ordinal=?3",params![id,sha,i as i64]).unwrap();
            let doc=document::create_optional(&mut conn,Some(&id),Some(&sha),path,json!({"type":"doc","attrs":{"unrelated":{"keep":true}},"content":[{"type":"paragraph","content":[{"type":"text","text":text}]}]})).unwrap();
            if i > 0 {
                targets.push(Target {
                    ordinal: i as i64,
                    source_id: id.clone(),
                    source_revision: sha.clone(),
                    document: Some(DocumentBinding {
                        document_id: doc["document_id"].as_str().unwrap().into(),
                        version: 1,
                        content_sha256: doc["content_sha256"].as_str().unwrap().into(),
                    }),
                });
            }
            docs.push(doc);
            source_ids.push((id, sha));
        }
        let original = docs.remove(0);
        let request = Apply {
            workspace_id,
            restore_epoch,
            source_id: source_ids[0].0.clone(),
            source_revision: source_ids[0].1.clone(),
            document_id: original["document_id"].as_str().unwrap().into(),
            expected_version: 1,
            content_sha256: original["content_sha256"].as_str().unwrap().into(),
            targets,
        };
        Self {
            _dir: dir,
            path,
            conn,
            request,
            original,
        }
    }
    fn apply(&mut self) -> Result<Value, links::Error> {
        links::apply(&mut self.conn, "batch", 0, self.request.clone())
    }
    fn unchanged(&self) {
        assert_eq!(
            document::read(&self.conn, &self.request.document_id, None).unwrap(),
            self.original
        );
    }
}

#[test]
fn original_provenance_preserves_edited_body_manual_relations_and_reopen() {
    let mut f = Fixture::new(
        "[[peer]] and ![attachment](../image.svg)",
        &[("notes/peer.md", "A"), ("image.svg", "<svg/>")],
    );
    let manual = json!({"id":"handwritten","kind":"supports","label":"Manual decision","target":{"kind":"source","source_id":f.request.source_id,"sha256":f.request.source_revision}});
    let mut edited = f.original["editor_json"].clone();
    edited["content"][0]["content"][0]["text"] = json!("Edited body has no links");
    edited["attrs"]["archeaxis_relations"] =
        json!({"schema":"archeaxis.relations/v1","relations":[manual.clone()]});
    let edited = document::save(&mut f.conn, &f.request.document_id, 1, edited).unwrap();
    f.request.expected_version = 2;
    f.request.content_sha256 = edited["content_sha256"].as_str().unwrap().into();
    let receipt = f.apply().unwrap();
    let saved = &receipt["document"];
    assert_eq!(
        saved["editor_json"]["content"],
        edited["editor_json"]["content"]
    );
    assert_eq!(
        saved["editor_json"]["attrs"]["unrelated"],
        json!({"keep":true})
    );
    assert_eq!(
        saved["editor_json"]["attrs"]["archeaxis_relations"]["relations"][0],
        manual
    );
    assert_eq!(receipt["input_kind"], "immutable_original_markdown");
    assert_eq!(receipt["added_relations"], 2);
    assert!(
        saved["editor_json"]["attrs"]["archeaxis_relations"]["relations"][1]["label"]
            .as_str()
            .unwrap()
            .contains(&f.request.source_revision)
    );
    let graph = relation_projection::query(&f.conn, &f.request.document_id, None, None).unwrap();
    assert_eq!(graph["edges"].as_array().unwrap().len(), 3);
    let peer = f.request.targets[0].document.clone().unwrap();
    document::save(
        &mut f.conn,
        &peer.document_id,
        1,
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    assert!(
        relation_projection::query(&f.conn, &peer.document_id, None, None).unwrap()["edges"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    assert_eq!(
        relation_projection::query(&f.conn, &peer.document_id, Some(1), None).unwrap()["edges"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    f.request.expected_version = saved["version"].as_i64().unwrap();
    f.request.content_sha256 = saved["content_sha256"].as_str().unwrap().into();
    drop(f.conn);
    f.conn = init_workspace(f.path.to_str().unwrap()).unwrap();
    let repeated = f.apply().unwrap();
    assert_eq!(repeated["added_relations"], 0);
    assert_eq!(repeated["document"], *saved);
    assert_eq!(
        relation_projection::query(&f.conn, &f.request.document_id, None, None).unwrap()["edges"],
        graph["edges"]
    );
}

#[test]
fn real_backup_restore_preserves_relations_but_refuses_old_scope() {
    let mut f = Fixture::new(
        "[[peer]] ![[asset.svg]]",
        &[("peer.md", "Peer"), ("asset.svg", "<svg/>")],
    );
    let receipt = f.apply().unwrap();
    f.request.expected_version = receipt["document"]["version"].as_i64().unwrap();
    f.request.content_sha256 = receipt["document"]["content_sha256"]
        .as_str()
        .unwrap()
        .into();
    let graph = relation_projection::query(&f.conn, &f.request.document_id, None, None).unwrap();
    let backup = f._dir.path().join("backup.sqlite");
    archeaxis_domain::backup::backup(&f.conn, backup.to_str().unwrap()).unwrap();
    let mut restored =
        init_workspace(f._dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    archeaxis_domain::backup::restore(backup.to_str().unwrap(), &mut restored).unwrap();
    assert!(
        archeaxis_domain::backup::finalize_restore_authorization(&f.conn, &mut restored).unwrap()
    );
    assert_eq!(
        relation_projection::query(&restored, &f.request.document_id, None, None).unwrap()["edges"],
        graph["edges"]
    );
    assert!(matches!(
        links::apply(&mut restored, "batch", 0, f.request.clone()),
        Err(links::Error::ScopeConflict)
    ));
    assert_eq!(
        document::read(&restored, &f.request.document_id, None).unwrap(),
        receipt["document"]
    );
    let (workspace, epoch) = batches::identity(&restored).unwrap();
    assert_ne!(epoch, f.request.restore_epoch);
    f.request.workspace_id = workspace;
    f.request.restore_epoch = epoch;
    let replay = links::apply(&mut restored, "batch", 0, f.request.clone()).unwrap();
    assert_eq!(replay["added_relations"], 0);
    assert_eq!(replay["document"], receipt["document"]);
}

#[test]
fn scope_identity_version_and_all_target_bindings_fail_before_append() {
    for case in 0..10 {
        let mut f = Fixture::new("[[peer]]", &[("peer.md", "Peer")]);
        match case {
            0 => f.request.workspace_id = "other".into(),
            1 => f.request.restore_epoch = "old".into(),
            2 => f.request.source_revision = "0".repeat(64),
            3 => f.request.content_sha256 = "0".repeat(64),
            4 => f.request.expected_version = 2,
            5 => f.request.targets[0].ordinal = 99,
            6 => f.request.targets[0].source_id = f.request.source_id.clone(),
            7 => {
                f.request.targets[0]
                    .document
                    .as_mut()
                    .unwrap()
                    .content_sha256 = "0".repeat(64)
            }
            8 => {
                let tx = f.conn.transaction().unwrap();
                archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
                tx.commit().unwrap();
            }
            _ => {
                f.conn
                    .execute(
                        "UPDATE ingest_batches SET expected_members=3 WHERE batch_id='batch'",
                        [],
                    )
                    .unwrap();
            }
        }
        assert!(f.apply().is_err(), "case {case}");
        f.unchanged();
    }
    let mut f = Fixture::new("[[peer]]", &[("peer.md", "Peer")]);
    let mut wrong = f.request.targets[0].clone();
    wrong.ordinal = 99;
    f.request.targets.push(wrong);
    assert!(f.apply().is_err());
    f.unchanged();
}

#[test]
fn code_escapes_external_ambiguous_missing_and_fragments_are_not_invented_edges() {
    let text = "`[[peer]]` and `` [[peer]] ``\n\\[[peer]]\n```md\n[[peer]]\n```\n~~~\n[[peer]]\n~~~\n    [[peer]]\n[[same]] [[missing]] [[peer#heading]] [[peer#^block]] [web](https://example.invalid) [run](javascript:bad) [data](data:bad) [[../../escape]] [[C:/secret]] [[peer]]\n```\n[[peer]]";
    let mut f = Fixture::new(
        text,
        &[
            ("peer.md", "Peer"),
            ("one/same.md", "same bytes"),
            ("two/same.md", "same bytes"),
        ],
    );
    let r = f.apply().unwrap();
    assert_eq!(r["added_relations"], 1, "{r}");
    let reasons: Vec<_> = r["links"]
        .as_array()
        .unwrap()
        .iter()
        .filter_map(|l| l["reason"].as_str())
        .collect();
    for expected in [
        "ambiguous_target",
        "missing_target",
        "fragment_resolution_not_supported",
        "external_reference_not_followed",
        "unsafe_or_unsupported_target",
    ] {
        assert!(reasons.contains(&expected), "{r}");
    }
    let mut f = Fixture::new("[[PEER]]", &[("peer.md", "p1"), ("Peer.md", "p2")]);
    let r = f.apply().unwrap();
    assert_eq!(r["added_relations"], 0);
    assert_eq!(r["links"][0]["reason"], "ambiguous_target");
    f.unchanged();
}

#[test]
fn existing_note_jobs_must_be_successful_and_source_bound() {
    for (state, source_ok) in [
        ("queued", true),
        ("running", true),
        ("failed", true),
        ("cancelled", true),
        ("succeeded", false),
    ] {
        let mut f = Fixture::new("[[peer]]", &[("peer.md", "Peer")]);
        f.conn
            .execute(
                "INSERT INTO jobs(job_id,kind,state,input_ref) VALUES('job','text',?1,?2)",
                params![
                    state,
                    if source_ok {
                        f.request.source_id.as_str()
                    } else {
                        "wrong-source"
                    }
                ],
            )
            .unwrap();
        f.conn
            .execute(
                "UPDATE ingest_batch_members SET job_id='job' WHERE batch_id='batch' AND ordinal=0",
                [],
            )
            .unwrap();
        assert!(f.apply().is_err());
        f.unchanged();
    }
}

#[test]
fn stable_id_collision_and_combined_relation_budget_never_overwrite_user_data() {
    let mut f = Fixture::new("[[peer]]", &[("peer.md", "Peer")]);
    let first = f.apply().unwrap();
    let saved = &first["document"];
    let mut edited = saved["editor_json"].clone();
    edited["attrs"]["archeaxis_relations"]["relations"][0]["label"] = json!("Human correction");
    let changed = document::save(&mut f.conn, &f.request.document_id, 2, edited).unwrap();
    f.request.expected_version = 3;
    f.request.content_sha256 = changed["content_sha256"].as_str().unwrap().into();
    assert!(f.apply().is_err());
    assert_eq!(
        document::read(&f.conn, &f.request.document_id, None).unwrap(),
        changed
    );
    let mut f = Fixture::new("[[peer]]", &[("peer.md", "Peer")]);
    let mut edited = f.original["editor_json"].clone();
    let manual:Vec<_>=(0..256).map(|i|json!({"id":format!("manual_{i}"),"kind":"related","label":"Manual","target":{"kind":"source","source_id":f.request.source_id,"sha256":f.request.source_revision}})).collect();
    edited["attrs"]["archeaxis_relations"] =
        json!({"schema":"archeaxis.relations/v1","relations":manual});
    let changed = document::save(&mut f.conn, &f.request.document_id, 1, edited).unwrap();
    f.request.expected_version = 2;
    f.request.content_sha256 = changed["content_sha256"].as_str().unwrap().into();
    assert!(f.apply().is_err());
    assert_eq!(
        document::read(&f.conn, &f.request.document_id, None).unwrap(),
        changed
    );
}

#[test]
fn markdown_delimiters_never_bind_a_truncated_or_label_target() {
    for (text, wrong, right) in [
        (
            "[x](peer(old).md)",
            "notes/peer(old.md",
            "notes/peer(old).md",
        ),
        (
            r"[x\](wrong.md)](right.md)",
            "notes/wrong.md",
            "notes/right.md",
        ),
    ] {
        let mut f = Fixture::new(text, &[(wrong, "wrong bytes"), (right, "right bytes")]);
        let correct = f.request.targets[1]
            .document
            .as_ref()
            .unwrap()
            .document_id
            .clone();
        let r = f.apply().unwrap();
        assert_eq!(r["added_relations"], 1, "{text}: {r}");
        let target =
            &r["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"][0]["target"];
        assert_eq!(target["document_id"], correct, "{text}: {r}");
    }
    for text in [
        r#"[x](peer.md "title")"#,
        r"[x](peer\(old\).md)",
        "[x](<peer.md>)",
    ] {
        let destination = text
            .strip_prefix("[x](")
            .unwrap()
            .strip_suffix(')')
            .unwrap();
        let candidate = if destination.contains('\\') {
            "notes/peer(old).md".to_owned()
        } else {
            format!("notes/{destination}")
        };
        let mut f = Fixture::new(text, &[(candidate.as_str(), "must not be guessed")]);
        let r = f.apply().unwrap();
        assert_eq!(r["added_relations"], 0, "{text}: {r}");
        assert_eq!(
            r["links"][0]["reason"], "unsafe_or_unsupported_target",
            "{r}"
        );
        f.unchanged();
    }
}
