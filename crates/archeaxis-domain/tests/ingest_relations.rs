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
        Self::at("notes/start.md", text, paths)
    }
    fn at(source_path: &str, text: &str, paths: &[(&str, &str)]) -> Self {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("workspace.sqlite");
        let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
        let (workspace_id, restore_epoch) = batches::identity(&conn).unwrap();
        let files: Vec<_> = std::iter::once((source_path, text))
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
            fragment_bindings: vec![],
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
fn contained_parent_links_resolve_original_four_member_batch() {
    let text = "[[target]] and ![[../assets/evidence.svg]]\n`[[ghost]]`\n```md\n[[ghost]]\n```";
    let mut f = Fixture::at(
        "notes/index.md",
        text,
        &[
            ("notes/target.md", "Target note"),
            ("notes/assets-only.md", "[Evidence](../assets/evidence.svg)"),
            ("assets/evidence.svg", "<svg/>"),
        ],
    );
    let asset = f.request.targets[2].clone();
    let expected =
        json!({"kind":"source","source_id":asset.source_id,"sha256":asset.source_revision});
    let r = f.apply().unwrap();
    assert_eq!(
        r["added_relations"], 2,
        "contained parent wiki embed was lost: {r}"
    );
    assert_eq!(
        r["links"].as_array().unwrap().len(),
        2,
        "code ghosts must not become links"
    );
    assert_eq!(r["links"][1]["target"], "../assets/evidence.svg");
    assert_eq!(r["links"][1]["status"], "resolved_reference");
    assert_eq!(r["links"][1]["reason"], "embed_rendering_not_supported");
    assert_eq!(
        r["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"][1]["target"],
        expected
    );
    assert_eq!(
        r["document"]["editor_json"]["content"],
        f.original["editor_json"]["content"]
    );
    let other = f.request.targets[1].clone();
    let binding = other.document.unwrap();
    let other = Apply {
        source_id: other.source_id,
        source_revision: other.source_revision,
        document_id: binding.document_id,
        expected_version: binding.version,
        content_sha256: binding.content_sha256,
        targets: vec![asset],
        ..f.request.clone()
    };
    let markdown = links::apply(&mut f.conn, "batch", 2, other).unwrap();
    assert_eq!(markdown["added_relations"], 1);
    assert_eq!(markdown["links"][0]["target"], "../assets/evidence.svg");
    assert_eq!(
        markdown["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"][0]["target"],
        expected
    );
    f.request.expected_version = r["document"]["version"].as_i64().unwrap();
    f.request.content_sha256 = r["document"]["content_sha256"].as_str().unwrap().into();
    let repeat = f.apply().unwrap();
    assert_eq!(repeat["added_relations"], 0);
    assert_eq!(repeat["document"], r["document"]);
}

#[test]
fn dot_segments_are_relative_to_the_member_parent_not_a_root_shadow() {
    for target in ["./asset.svg", "sub/../asset.svg", "./sub/../asset.svg"] {
        let mut f = Fixture::new(
            &format!("![[{target}]]"),
            &[
                ("asset.svg", "wrong root asset"),
                ("notes/asset.svg", "correct relative asset"),
            ],
        );
        let r = f.apply().unwrap();
        assert_eq!(r["added_relations"], 1, "{target}: {r}");
        assert_eq!(r["links"][0]["target"], target);
        assert_eq!(
            r["links"][0]["target_ordinal"], 2,
            "root shadow misbound: {r}"
        );
        assert_eq!(
            r["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"][0]["target"],
            json!({"kind":"source","source_id":f.request.targets[1].source_id,"sha256":f.request.targets[1].source_revision})
        );
    }
}

#[test]
fn parent_normalization_never_escapes_decodes_or_guesses_a_binding() {
    for (target, reason) in [
        ("../../assets/evidence.svg", "unsafe_or_unsupported_target"),
        (
            "../../notes/../assets/evidence.svg",
            "unsafe_or_unsupported_target",
        ),
        ("/assets/evidence.svg", "unsafe_or_unsupported_target"),
        (
            "//server/assets/evidence.svg",
            "external_reference_not_followed",
        ),
        ("C:/assets/evidence.svg", "external_reference_not_followed"),
        (
            "file:///assets/evidence.svg",
            "external_reference_not_followed",
        ),
        (
            "https://example.invalid/evidence.svg",
            "external_reference_not_followed",
        ),
        ("../assets/%65vidence.svg", "unsafe_or_unsupported_target"),
        ("%2e%2e/assets/evidence.svg", "unsafe_or_unsupported_target"),
        (
            "%252e%252e/assets/evidence.svg",
            "unsafe_or_unsupported_target",
        ),
        (r"..\assets\evidence.svg", "unsafe_or_unsupported_target"),
        (
            "../assets/evidence.svg?download=1",
            "unsafe_or_unsupported_target",
        ),
        (
            "../assets/evidence.svg#section",
            "fragment_resolution_not_supported",
        ),
    ] {
        let mut f = Fixture::new(
            &format!("![[{target}]]"),
            &[("assets/evidence.svg", "<svg/>")],
        );
        let r = f.apply().unwrap();
        assert_eq!(r["added_relations"], 0, "{target}: {r}");
        assert_eq!(r["links"][0]["reason"], reason, "{target}: {r}");
        f.unchanged();
    }
    let mut f = Fixture::new(
        "![[../assets/evidence.svg]]",
        &[
            ("assets/evidence.svg", "first"),
            ("assets/Evidence.svg", "second"),
        ],
    );
    let r = f.apply().unwrap();
    assert_eq!(r["added_relations"], 0);
    assert_eq!(r["links"][0]["reason"], "ambiguous_target");
    f.unchanged();

    let mut f = Fixture::new(
        "![[../assets/evidence.svg]]",
        &[("assets/evidence.svg", "<svg/>")],
    );
    f.request.targets.clear();
    let r = f.apply().unwrap();
    assert_eq!(r["added_relations"], 0);
    assert_eq!(r["links"][0]["target_ordinal"], 1);
    assert_eq!(r["links"][0]["reason"], "target_binding_required");
    f.unchanged();

    for text in [
        "![[./../assets/./evidence.svg]]",
        "![[sub/../../assets/evidence.svg]]",
        "[Evidence](./../assets/./evidence.svg)",
    ] {
        let mut f = Fixture::new(text, &[("assets/evidence.svg", "<svg/>")]);
        let r = f.apply().unwrap();
        assert_eq!(
            r["added_relations"], 1,
            "contained dot path rejected: {text}: {r}"
        );
        assert_eq!(r["links"][0]["target_ordinal"], 1);
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

fn fragment_fixture() -> Fixture {
    let mut f = Fixture::new(
        "[[peer#Heading]] [[peer#^named]] [[peer#unknown]]",
        &[("peer.md", "# Heading\nOriginal paragraph ^named")],
    );
    let target = f.request.targets[0].document.as_ref().unwrap();
    let block =
        document::read(&f.conn, &target.document_id, Some(1)).unwrap()["blocks"][0]["block_id"]
            .as_str()
            .unwrap()
            .to_owned();
    f.request.fragment_bindings = vec![
        links::FragmentBinding {
            link_ordinal: 0,
            target_ordinal: 1,
            fragment: "Heading".into(),
            fragment_is_block: false,
            block_id: block.clone(),
        },
        links::FragmentBinding {
            link_ordinal: 1,
            target_ordinal: 1,
            fragment: "named".into(),
            fragment_is_block: true,
            block_id: block,
        },
    ];
    f
}

#[test]
fn fragments_keep_pinned_blocks_backlinks_reopen_restore_and_portable_boundary() {
    let mut f = fragment_fixture();
    let peer = f.request.targets[0].document.clone().unwrap();
    let receipt = f.apply().unwrap();
    assert_eq!(receipt["added_relations"], 2);
    assert_eq!(
        receipt["links"][2]["reason"],
        "fragment_resolution_not_supported"
    );
    let relations =
        &receipt["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"];
    for r in relations.as_array().unwrap() {
        assert_eq!(r["target"]["version"], 1);
        assert_eq!(
            r["target"]["block_id"],
            f.request.fragment_bindings[0].block_id
        );
        assert!(
            r["label"]
                .as_str()
                .unwrap()
                .contains("human-selected block")
        );
    }
    let projection = relation_projection::query(&f.conn, &peer.document_id, Some(1), None).unwrap();
    assert_eq!(projection["edges"].as_array().unwrap().len(), 2);
    let fixed = archeaxis_domain::object_reference::Reference::Document {
        document_id: peer.document_id.clone(),
        version: 1,
        block_id: Some(f.request.fragment_bindings[0].block_id.clone()),
    };
    archeaxis_domain::object_reference::resolve(&f.conn, &fixed).unwrap();
    document::save(
        &mut f.conn,
        &peer.document_id,
        1,
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    assert!(
        relation_projection::query(&f.conn, &peer.document_id, Some(2), None).unwrap()["edges"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    assert_eq!(
        relation_projection::query(&f.conn, &peer.document_id, Some(1), None).unwrap()["edges"],
        projection["edges"]
    );
    assert!(matches!(f.apply(), Err(links::Error::Conflict(2))));
    f.request.expected_version = 2;
    f.request.content_sha256 = receipt["document"]["content_sha256"]
        .as_str()
        .unwrap()
        .into();
    assert_eq!(f.apply().unwrap()["added_relations"], 0);
    let package =
        archeaxis_domain::portable_document::export(&f.conn, &f.request.document_id).unwrap();
    let destination = f._dir.path().join("portable.sqlite");
    let mut destination = init_workspace(destination.to_str().unwrap()).unwrap();
    assert!(
        archeaxis_domain::portable_document::import(&mut destination, package, "fragment-import")
            .is_err()
    );
    assert_eq!(
        destination
            .query_row("SELECT COUNT(*) FROM documents", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        0
    );
    let backup = f._dir.path().join("fragment-backup.sqlite");
    archeaxis_domain::backup::backup(&f.conn, backup.to_str().unwrap()).unwrap();
    let restored_path = f._dir.path().join("restored.sqlite");
    let mut restored = init_workspace(restored_path.to_str().unwrap()).unwrap();
    archeaxis_domain::backup::restore(backup.to_str().unwrap(), &mut restored).unwrap();
    archeaxis_domain::backup::finalize_restore_authorization(&f.conn, &mut restored).unwrap();
    assert!(matches!(
        links::apply(&mut restored, "batch", 0, f.request.clone()),
        Err(links::Error::ScopeConflict)
    ));
    drop(restored);
    let restored = init_workspace(restored_path.to_str().unwrap()).unwrap();
    assert_eq!(
        document::read(&restored, &f.request.document_id, None).unwrap(),
        receipt["document"]
    );
    archeaxis_domain::object_reference::resolve(&restored, &fixed).unwrap();
    assert_eq!(
        relation_projection::query(&restored, &peer.document_id, Some(1), None).unwrap()["edges"],
        projection["edges"]
    );
    drop(f.conn);
    f.conn = init_workspace(f.path.to_str().unwrap()).unwrap();
    assert_eq!(f.apply().unwrap()["document"], receipt["document"]);
}

#[test]
fn explicit_fragments_never_bypass_original_or_pinned_identity() {
    for case in 0..13 {
        let mut f = fragment_fixture();
        match case {
            0 => f.request.fragment_bindings[0].link_ordinal = 99,
            1 => f.request.fragment_bindings[0].target_ordinal = 0,
            2 => f.request.fragment_bindings[0].fragment = "different".into(),
            3 => f.request.fragment_bindings[0].fragment_is_block = true,
            4 => f.request.fragment_bindings[0].block_id = "missing".into(),
            5 => f.request.fragment_bindings[0].block_id = "../outside".into(),
            6 => f
                .request
                .fragment_bindings
                .push(f.request.fragment_bindings[0].clone()),
            7 => f.request.targets[0].document.as_mut().unwrap().version = 99,
            8 => {
                f.request.targets[0]
                    .document
                    .as_mut()
                    .unwrap()
                    .content_sha256 = "0".repeat(64)
            }
            9 => f.request.targets[0].document = None,
            10 => f.request.fragment_bindings[0].fragment = "".into(),
            11 => {
                f.request.fragment_bindings[0].link_ordinal = 2;
                f.request.fragment_bindings[0].fragment = "unknown".into();
            }
            _ => f.request.fragment_bindings = vec![f.request.fragment_bindings[0].clone(); 257],
        }
        assert!(f.apply().is_err(), "case {case}");
        f.unchanged();
    }
}

#[test]
fn fragment_definitions_are_exact_unique_and_never_code_or_slugs() {
    use archeaxis_domain::vault::unique_fragment_definition as defined;
    assert!(defined("# 中文标题\ncontent ^block-1", "中文标题", false));
    assert!(defined("# 中文标题\ncontent ^block-1", "block-1", true));
    for text in [
        "# Heading\n# Heading",
        "```md\n# Heading\n```",
        "    # Heading",
        "Heading\n===",
        "# **Heading**",
        "# Heading `code`",
        "# heading",
    ] {
        assert!(!defined(text, "Heading", false), "{text}");
    }
    for text in [
        "`^block`",
        "```\ntext ^block\n```",
        "text ^block\nother ^block",
        "text^block",
        "text ^block extra",
    ] {
        assert!(!defined(text, "block", true), "{text}");
    }
}

#[test]
fn fragment_review_unicode_code_cannot_move_heading_offsets() {
    assert!(!archeaxis_domain::vault::unique_fragment_definition(
        "`a\n中`# Heading",
        "Heading",
        false
    ));
}

#[test]
fn fragment_review_code_prefix_does_not_hide_duplicate_blocks() {
    use archeaxis_domain::vault::unique_fragment_definition as defined;
    assert!(defined("`abc` ^named", "named", true));
    assert!(defined("`中文` ^named", "named", true));
    assert!(defined("中文 `code` ^named  \r\n", "named", true));
    assert!(!defined("text ^named\n`abc` ^named", "named", true));
    assert!(!defined("`中文` ^named\nother ^named", "named", true));
    assert!(!defined("`中文\ntext ^named\n`", "named", true));
}

#[test]
fn fragment_review_block_marker_must_end_the_original_line() {
    assert!(!archeaxis_domain::vault::unique_fragment_definition(
        "text ^named `abc`",
        "named",
        true
    ));
}

#[test]
fn fragment_review_unsupported_html_and_quote_contexts_are_rejected() {
    use archeaxis_domain::vault::unique_fragment_definition as defined;
    for (text, fragment, block) in [
        ("<!--\n# Heading\n-->", "Heading", false),
        ("<!--\ntext ^named\n-->", "named", true),
        ("> ~~~\n> text ^named\n> ~~~", "named", true),
        ("> ```\n> text ^named\n> ```", "named", true),
        ("<div>\n# Heading\n</div>", "Heading", false),
        ("- item\n# Heading", "Heading", false),
        ("1. item\ntext ^named", "named", true),
    ] {
        assert!(!defined(text, fragment, block), "{text}");
    }
    assert!(defined("`<html>`\n# Heading", "Heading", false));
    assert!(defined(
        "```\n> quote\n<!-- html -->\n```\n# Heading",
        "Heading",
        false
    ));
}

#[test]
fn fragment_review_list_markers_accept_space_tab_and_line_end_only() {
    use archeaxis_domain::vault::unique_fragment_definition as defined;
    let mut accepted = Vec::new();
    for marker in ["-", "+", "*", "1.", "1)", "123456789."] {
        for suffix in [" item", "\titem", "", "\r"] {
            let prefix = format!("{marker}{suffix}");
            for (target, fragment, block) in [
                ("# Heading", "Heading", false),
                ("text ^named", "named", true),
            ] {
                let text = format!("{prefix}\n{target}");
                if defined(&text, fragment, block) {
                    accepted.push(text);
                }
            }
        }
    }
    assert!(
        accepted.is_empty(),
        "unsupported list contexts accepted: {accepted:?}"
    );
    for text in ["-text", "+text", "*text", "1.x", "1)x", "1234567890. item"] {
        assert!(
            defined(&format!("{text}\n# Heading"), "Heading", false),
            "ordinary text rejected: {text}"
        );
    }
}
