use archeaxis_domain::{ImportOutcome, document, portable_document, source};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn media_document(conn: &mut rusqlite::Connection, raw: &[u8]) -> Value {
    let (id, sha) = match source::import_source(conn, raw, "authored-scan.pdf", None).unwrap() {
        ImportOutcome::Imported { source_id, sha256 }
        | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
    };
    document::create_optional(
        conn,
        Some(&id),
        Some(&sha),
        "Bound original",
        json!({"type":"doc","content":[]}),
    )
    .unwrap()
}

#[test]
fn media_package_preserves_scan_size_and_exact_eight_mib_boundary() {
    for size in [4_564_915, 8 * 1024 * 1024] {
        let dir = tempfile::tempdir().unwrap();
        let mut from = archeaxis_store_sqlite::init_workspace(
            dir.path().join("from.sqlite").to_str().unwrap(),
        )
        .unwrap();
        // The observed scan's byte count, with worst-case four-character JSON bytes.
        let raw = vec![255; size];
        let doc = media_document(&mut from, &raw);
        let package =
            portable_document::export(&from, doc["document_id"].as_str().unwrap()).unwrap();
        assert_eq!(package.objects[0].bytes, raw);
        assert!(serde_json::to_vec(&package).unwrap().len() > 16 * 1024 * 1024);
        let mut to =
            archeaxis_store_sqlite::init_workspace(dir.path().join("to.sqlite").to_str().unwrap())
                .unwrap();
        let imported = portable_document::import(&mut to, package, "bounded-media").unwrap();
        let again =
            portable_document::export(&to, imported["document"]["document_id"].as_str().unwrap())
                .unwrap();
        assert_eq!(again.objects[0].bytes, raw);
        assert_eq!(
            again.objects[0].sha256,
            doc["source_revision"].as_str().unwrap()
        );
    }
}

#[test]
fn media_package_rejects_over_budget_and_corrupt_cas_without_database_changes() {
    for corrupt in [false, true] {
        let dir = tempfile::tempdir().unwrap();
        let mut conn = archeaxis_store_sqlite::init_workspace(
            dir.path().join("source.sqlite").to_str().unwrap(),
        )
        .unwrap();
        let raw = vec![255; if corrupt { 32 } else { 8 * 1024 * 1024 + 1 }];
        let doc = media_document(&mut conn, &raw);
        if corrupt {
            let path = archeaxis_store_sqlite::raw_objects::root(&conn)
                .unwrap()
                .join(doc["source_revision"].as_str().unwrap());
            std::fs::write(path, b"tampered synthetic CAS").unwrap();
        }
        let changes = conn.total_changes();
        let error = portable_document::export(&conn, doc["document_id"].as_str().unwrap())
            .err()
            .unwrap();
        assert!(
            matches!(error, document::Error::Invalid(_)),
            "bounded CAS rejection must be a package error: {error:?}"
        );
        assert_eq!(conn.total_changes(), changes);
        assert_eq!(
            document::read(&conn, doc["document_id"].as_str().unwrap(), None).unwrap(),
            doc
        );
    }
}

#[test]
fn media_package_aggregate_and_serialized_limits_reject_before_import_writes() {
    let dir = tempfile::tempdir().unwrap();
    let mut from =
        archeaxis_store_sqlite::init_workspace(dir.path().join("from.sqlite").to_str().unwrap())
            .unwrap();
    let mut to =
        archeaxis_store_sqlite::init_workspace(dir.path().join("to.sqlite").to_str().unwrap())
            .unwrap();
    let raw = vec![255; 4 * 1024 * 1024];
    let doc = media_document(&mut from, &raw);
    let mut package =
        portable_document::export(&from, doc["document_id"].as_str().unwrap()).unwrap();
    let second = vec![254; 4 * 1024 * 1024 + 1];
    let digest = format!("{:x}", Sha256::digest(&second));
    package.document["editor_json"]["attrs"] = json!({"archeaxis_relations":{"schema":"archeaxis.relations/v1","relations":[
        {"id":"second","kind":"related","label":"second original","target":{"kind":"source","source_id":"foreign_second","sha256":digest}}]}});
    package.document["content_sha256"] = json!(format!(
        "{:x}",
        Sha256::digest(package.document["editor_json"].to_string().as_bytes())
    ));
    package.objects.push(portable_document::Object {
        source_id: "foreign_second".into(),
        sha256: digest,
        original_name: "second.pdf".into(),
        bytes: second,
    });
    let changes = to.total_changes();
    assert!(matches!(
        portable_document::import(&mut to, package, "too-many-bytes"),
        Err(document::Error::Invalid(
            "object identity or byte budget invalid"
        ))
    ));
    assert_eq!(to.total_changes(), changes);
    let doc = media_document(&mut from, b"small original");
    let mut package =
        portable_document::export(&from, doc["document_id"].as_str().unwrap()).unwrap();
    package
        .historical_anchors
        .push(json!({"opaque": "x".repeat(40 * 1024 * 1024)}));
    assert!(matches!(
        portable_document::import(&mut to, package, "too-much-json"),
        Err(document::Error::Invalid(
            "serialized package budget exceeded"
        ))
    ));
    assert_eq!(to.total_changes(), changes);
    assert!(document::list(&to).unwrap().is_empty());
}

#[test]
fn source_relation_packages_original_bytes_and_remaps_foreign_identity() {
    let dir = tempfile::tempdir().unwrap();
    let mut a = archeaxis_store_sqlite::init_workspace(
        dir.path().join("relation-a.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let raw = b"Public authored attachment";
    let (id, sha) = match source::import_source(&mut a, raw, "same-name.txt", None).unwrap() {
        ImportOutcome::Imported { source_id, sha256 }
        | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
    };
    let doc = document::create_optional(&mut a,None,None,"Relations",json!({"type":"doc","content":[],"attrs":{
        "opaque_future":{"source_id":"not-a-dependency","sha256":"not-a-hash"},
        "archeaxis_relations":{"schema":"archeaxis.relations/v1","relations":[{"id":"attachment","kind":"related","label":"Original attachment","target":{"kind":"source","source_id":id,"sha256":sha}}]}}})).unwrap();
    let mut package = portable_document::export(&a, doc["document_id"].as_str().unwrap()).unwrap();
    assert_eq!(
        package.objects.len(),
        1,
        "canonical Source relations must carry their original CAS bytes"
    );
    assert_eq!(package.objects[0].bytes, raw);
    package.objects[0].source_id = "foreign_attachment".into();
    package.document["editor_json"]["attrs"]["archeaxis_relations"]["relations"][0]["target"]["source_id"] =
        json!("foreign_attachment");
    package.document["content_sha256"] = json!(hex::encode(Sha256::digest(
        package.document["editor_json"].to_string().as_bytes()
    )));
    let mut b = archeaxis_store_sqlite::init_workspace(
        dir.path().join("relation-b.sqlite").to_str().unwrap(),
    )
    .unwrap();
    source::import_source(&mut b, b"different bytes", "same-name.txt", None).unwrap();
    let imported = portable_document::import(&mut b, package, "relation-import").unwrap();
    let target = &imported["document"]["editor_json"]["attrs"]["archeaxis_relations"]["relations"]
        [0]["target"];
    assert_ne!(target["source_id"], "foreign_attachment");
    assert_eq!(target["sha256"], sha);
    assert_eq!(
        archeaxis_store_sqlite::raw_objects::read(&b, &sha).unwrap(),
        raw
    );
    assert_eq!(
        archeaxis_domain::object_reference::resolve(
            &b,
            &serde_json::from_value(target.clone()).unwrap()
        )
        .unwrap()["reference"],
        *target
    );
}

#[test]
fn unbundled_document_relation_is_refused_even_when_destination_has_that_id() {
    let dir = tempfile::tempdir().unwrap();
    let mut a = archeaxis_store_sqlite::init_workspace(
        dir.path().join("foreign-a.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let target = document::create_optional_with_request(
        &mut a,
        None,
        None,
        "A",
        json!({"type":"doc","content":[]}),
        Some("same-id"),
    )
    .unwrap();
    let doc=document::create_optional(&mut a,None,None,"Linked",json!({"type":"doc","content":[],"attrs":{"archeaxis_relations":{"schema":"archeaxis.relations/v1","relations":[{"id":"peer","kind":"related","label":"Foreign peer","target":{"kind":"document","document_id":target["document_id"],"version":1,"block_id":null}}]}}})).unwrap();
    let package = portable_document::export(&a, doc["document_id"].as_str().unwrap()).unwrap();
    let mut b = archeaxis_store_sqlite::init_workspace(
        dir.path().join("foreign-b.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let unrelated = document::create_optional_with_request(
        &mut b,
        None,
        None,
        "B unrelated",
        json!({"type":"doc","content":[]}),
        Some("same-id"),
    )
    .unwrap();
    assert_eq!(unrelated["document_id"], target["document_id"]);
    assert!(
        portable_document::import(&mut b, package, "foreign-peer").is_err(),
        "foreign relation must never attach to a local coincident ID"
    );
    assert_eq!(document::list(&b).unwrap().len(), 1);
}
fn fixture(conn: &mut rusqlite::Connection) -> Value {
    let bytes = include_bytes!("../../../tests/fixtures/golden/golden-screenshot-ocr.png");
    let (id, sha) = match source::import_source(conn, bytes, "synthetic.png", None).unwrap() {
        ImportOutcome::Imported { source_id, sha256 }
        | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
    };
    let editor = json!({"type":"doc","attrs":{"future_attribute":{"keep":true},"archeaxis_expression":{"schema":"archeaxis.expression/v1","nodes":[{"id":"pic","type":"media","text":"合成媒体","x":0,"y":0,"width":32,"height":32,"media":{"source_id":id,"sha256":sha,"media_type":"image/png"}}],"edges":[]}},"content":[{"type":"future_widget","attrs":{"opaque":{"keep":[1,2,3]}},"content":[{"type":"text","text":"中文未知节点"}]}]});
    document::create_optional(conn, Some(&id), Some(&sha), "便携合成资料", editor).unwrap()
}

fn historical_source_after_edit(replace: bool) {
    let dir = tempfile::tempdir().unwrap();
    let workspace = |name: &str| {
        archeaxis_store_sqlite::init_workspace(dir.path().join(name).to_str().unwrap()).unwrap()
    };
    let mut a = workspace("a.sqlite");
    let raw = b"Historical authored source";
    let hash = |bytes: &[u8]| hex::encode(Sha256::digest(bytes));
    let (source_id, digest) =
        match source::import_source(&mut a, raw, "historical.txt", None).unwrap() {
            ImportOutcome::Imported { source_id, sha256 }
            | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
        };
    let position = json!({"type":"text","start":0,"end":raw.len(),
        "checksum":hash(raw),"location_status":"located"})
    .to_string();
    let anchor =
        archeaxis_domain::anchor::add_anchor(&mut a, &source_id, &digest, &position).unwrap();
    let citation = json!({"schema":"archeaxis.research-citation/v1","anchor_id":anchor,
        "source_sha256":digest,"anchor_position_sha256":hash(position.as_bytes()),
        "quote":std::str::from_utf8(raw).unwrap(),"quote_sha256":hash(raw),"read_snapshot_sha256":digest});
    let editor = json!({"type":"doc","content":[],"attrs":{"archeaxis_research":{
        "schema":"archeaxis.research/v1","question":"Synthetic historical evidence",
        "materials":[{"id":"old","note":"Public authored fixture",
            "reference":{"kind":"source","source_id":source_id,"sha256":digest},"citation":citation}],
        "hypotheses":[],"methods":[],"experiments":[],"counterevidence":[],"conclusions":[],"unresolved":[]}}});
    let original = document::create_optional(&mut a, None, None, "History", editor).unwrap();
    let mut package =
        portable_document::export(&a, original["document_id"].as_str().unwrap()).unwrap();
    // A foreign producer may use another Source ID for these same immutable bytes.
    // The old locator identity stays historical; only explicit mapping resolves it.
    let foreign = "foreign_historical_source";
    package.objects[0].source_id = foreign.into();
    package.document["editor_json"]["attrs"]["archeaxis_research"]["materials"][0]["reference"]["source_id"] =
        json!(foreign);
    package.document["content_sha256"] =
        json!(hash(package.document["editor_json"].to_string().as_bytes()));
    package.historical_anchors[0]["source_id"] = json!(foreign);
    package
        .historical_anchors
        .push(json!({"kind":"opaque_future_metadata",
        "source_id":"never_read_this_unrelated_source","sha256":hash(b"not a dependency")}));
    let mut b = workspace("b.sqlite");
    let imported = portable_document::import(&mut b, package, "history_a_b").unwrap();
    let id = imported["document"]["document_id"].as_str().unwrap();
    let mut edited = imported["document"]["editor_json"].clone();
    edited["attrs"]["archeaxis_research"]["materials"] = json!([]);
    if replace {
        let (new_id, new_sha) =
            match source::import_source(&mut b, b"Replacement authored source", "new.txt", None)
                .unwrap()
            {
                ImportOutcome::Imported { source_id, sha256 }
                | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
            };
        edited["attrs"]["archeaxis_research"]["materials"] = json!([{
            "id":"new","note":"New source replaces every old active reference",
            "reference":{"kind":"source","source_id":new_id,"sha256":new_sha}}]);
    }
    let saved = document::save(&mut b, id, 1, edited.clone()).unwrap();
    assert!(saved["revision_basis"].is_null());
    let exported = portable_document::export(&b, id).unwrap();
    assert_eq!(exported.document["editor_json"], edited);
    let old = exported
        .objects
        .iter()
        .find(|object| object.sha256 == digest);
    assert!(
        old.is_some(),
        "historical quote lost its original after all active references changed"
    );
    assert_eq!(old.unwrap().bytes, raw);
    assert_eq!(exported.objects.len(), if replace { 2 } else { 1 });
    let encoded = serde_json::to_value(&exported).unwrap();
    let mut incomplete = encoded.clone();
    incomplete["objects"]
        .as_array_mut()
        .unwrap()
        .retain(|object| object["sha256"] != digest);
    let mut c = workspace("c.sqlite");
    assert!(
        portable_document::import(
            &mut c,
            serde_json::from_value(incomplete).unwrap(),
            "incomplete"
        )
        .is_err()
    );
    let mut wrong_hash = encoded.clone();
    wrong_hash["historical_anchors"][0]["citation"]["source_sha256"] =
        json!(hash(b"wrong history"));
    assert!(
        portable_document::import(
            &mut c,
            serde_json::from_value(wrong_hash).unwrap(),
            "wrong_history"
        )
        .is_err()
    );
    if replace {
        let mut conflict = encoded.clone();
        conflict["historical_anchors"][0]["source_id"] =
            edited["attrs"]["archeaxis_research"]["materials"][0]["reference"]["source_id"].clone();
        assert!(
            portable_document::import(
                &mut c,
                serde_json::from_value(conflict).unwrap(),
                "conflicting_history"
            )
            .is_err()
        );
    }
    assert!(document::list(&c).unwrap().is_empty());
    assert_eq!(
        c.query_row::<i64, _, _>("SELECT count(*) FROM sources", [], |r| r.get(0))
            .unwrap(),
        0
    );
    let result = portable_document::import(&mut c, exported, "history_b_c").unwrap();
    assert_eq!(result["document"]["editor_json"], edited);
    assert_eq!(result["historical_anchors"], imported["historical_anchors"]);
    assert_eq!(
        archeaxis_store_sqlite::raw_objects::read(&c, &digest).unwrap(),
        raw
    );
    assert_eq!(result["anchor_registration"], "NOT_EXECUTED");
    assert_eq!(result["knowledge_admission"], "NOT_EXECUTED");
    assert_eq!(
        c.query_row::<i64, _, _>("SELECT count(*) FROM anchors", [], |r| r.get(0))
            .unwrap(),
        0
    );
    assert_eq!(
        c.query_row::<i64, _, _>("SELECT count(*) FROM knowledge", [], |r| r.get(0))
            .unwrap(),
        0
    );
    let forwarded =
        portable_document::export(&c, result["document"]["document_id"].as_str().unwrap()).unwrap();
    assert_eq!(
        serde_json::to_value(&forwarded.objects).unwrap(),
        encoded["objects"]
    );
}

#[test]
fn historical_source_closure_survives_deleting_all_active_refs() {
    historical_source_after_edit(false);
}

#[test]
fn historical_source_closure_survives_replacing_all_active_refs() {
    historical_source_after_edit(true);
}

#[test]
fn source_media_unknown_nodes_restart_and_retry_are_preserved() {
    let dir = tempfile::tempdir().unwrap();
    let mut source =
        archeaxis_store_sqlite::init_workspace(dir.path().join("from.sqlite").to_str().unwrap())
            .unwrap();
    let original = fixture(&mut source);
    let package =
        portable_document::export(&source, original["document_id"].as_str().unwrap()).unwrap();
    let encoded = serde_json::to_value(package).unwrap();
    let db = dir.path().join("to.sqlite");
    let mut target = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let receipt = portable_document::import(
        &mut target,
        serde_json::from_value(encoded.clone()).unwrap(),
        "same_request",
    )
    .unwrap();
    assert_eq!(receipt["document"]["editor_json"], original["editor_json"]);
    assert_eq!(receipt["knowledge_admission"], "NOT_EXECUTED");
    assert_ne!(receipt["document"]["document_id"], original["document_id"]);
    drop(target);
    let mut target = archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let replay = portable_document::import(
        &mut target,
        serde_json::from_value(encoded.clone()).unwrap(),
        "same_request",
    )
    .unwrap();
    assert_eq!(replay, receipt);
    let media = archeaxis_store_sqlite::raw_objects::read(
        &target,
        original["source_revision"].as_str().unwrap(),
    )
    .unwrap();
    assert_eq!(
        media,
        include_bytes!("../../../tests/fixtures/golden/golden-screenshot-ocr.png")
    );
    assert_eq!(document::list(&target).unwrap().len(), 1);
    let mut changed = encoded;
    changed["document"]["title"] = json!("changed");
    assert!(
        portable_document::import(
            &mut target,
            serde_json::from_value(changed).unwrap(),
            "same_request"
        )
        .is_err()
    );
    assert_eq!(document::list(&target).unwrap().len(), 1);
}
#[test]
fn damaged_media_and_invalid_editor_leave_no_registered_partial_state() {
    let dir = tempfile::tempdir().unwrap();
    let mut source =
        archeaxis_store_sqlite::init_workspace(dir.path().join("from.sqlite").to_str().unwrap())
            .unwrap();
    let original = fixture(&mut source);
    let encoded = serde_json::to_value(
        portable_document::export(&source, original["document_id"].as_str().unwrap()).unwrap(),
    )
    .unwrap();
    let mut target =
        archeaxis_store_sqlite::init_workspace(dir.path().join("to.sqlite").to_str().unwrap())
            .unwrap();
    let mut damaged = encoded.clone();
    damaged["objects"][0]["bytes"][0] = json!(0);
    assert!(
        portable_document::import(
            &mut target,
            serde_json::from_value(damaged).unwrap(),
            "damaged"
        )
        .is_err()
    );
    for namespace in [
        "archeaxis_context_grant",
        "archeaxis_asset_context_grant",
        "archeaxis_ai_asset",
        "archeaxis_machine_evaluation",
        "archeaxis_machine_rubric",
    ] {
        let mut grant = encoded.clone();
        grant["document"]["editor_json"]["attrs"][namespace] = json!({"state":"active"});
        grant["document"]["content_sha256"] = json!(hex::encode(Sha256::digest(
            grant["document"]["editor_json"].to_string().as_bytes()
        )));
        assert!(
            portable_document::import(&mut target, serde_json::from_value(grant).unwrap(), "grant")
                .is_err()
        );
    }
    let mut incomplete = encoded.clone();
    incomplete["objects"] = json!([]);
    assert!(
        portable_document::import(
            &mut target,
            serde_json::from_value(incomplete).unwrap(),
            "missing"
        )
        .is_err()
    );
    let mut invalid = encoded;
    invalid["document"]["editor_json"]["attrs"]["archeaxis_expression"]["nodes"][0]["x"] =
        json!(999999);
    invalid["document"]["content_sha256"] = json!(hex::encode(Sha256::digest(
        invalid["document"]["editor_json"].to_string().as_bytes()
    )));
    assert!(
        portable_document::import(
            &mut target,
            serde_json::from_value(invalid).unwrap(),
            "invalid"
        )
        .is_err()
    );
    assert!(document::list(&target).unwrap().is_empty());
    let count: i64 = target
        .query_row("SELECT count(*) FROM sources", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 0);
    let count: i64 = target
        .query_row("SELECT count(*) FROM knowledge", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 0);
}

#[test]
fn research_sources_raw_response_and_historical_quote_travel_together_without_admission() {
    let dir = tempfile::tempdir().unwrap();
    let mut from = archeaxis_store_sqlite::init_workspace(
        dir.path().join("research-from.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let mut references = Vec::new();
    for (name, bytes) in [
        ("derived.txt", b"Synthetic derived excerpt".as_slice()),
        ("raw.json", b"{\"original\":true}".as_slice()),
    ] {
        let (source_id, sha256) = match source::import_source(&mut from, bytes, name, None).unwrap()
        {
            ImportOutcome::Imported { source_id, sha256 }
            | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
        };
        references.push(json!({"kind":"source","source_id":source_id,"sha256":sha256}));
    }
    let quote = "Synthetic derived excerpt";
    let hash = |value: &[u8]| hex::encode(Sha256::digest(value));
    let position=json!({"type":"text","start":0,"end":quote.len(),"checksum":hash(quote.as_bytes()),"location_status":"located"}).to_string();
    let anchor = archeaxis_domain::anchor::add_anchor(
        &mut from,
        references[0]["source_id"].as_str().unwrap(),
        references[0]["sha256"].as_str().unwrap(),
        &position,
    )
    .unwrap();
    let citation = json!({"schema":"archeaxis.research-citation/v1","anchor_id":anchor,"source_sha256":references[0]["sha256"],"anchor_position_sha256":hash(position.as_bytes()),"quote":quote,"quote_sha256":hash(quote.as_bytes()),"read_snapshot_sha256":references[0]["sha256"]});
    let editor = json!({"type":"doc","content":[],"attrs":{"archeaxis_research":{"schema":"archeaxis.research/v1","question":"Public evidence comparison",
        "materials":[{"id":"derived","note":"Derived; unverified","reference":references[0],"citation":citation},{"id":"raw","note":"Raw upstream response","reference":references[1]}],
        "hypotheses":[],"methods":[],"experiments":[],"counterevidence":[{"id":"uncertain","text":"Unverified author comparison","references":references}],"conclusions":[],"unresolved":[]}}});
    let original = document::create_optional(&mut from, None, None, "Research", editor).unwrap();
    let package =
        portable_document::export(&from, original["document_id"].as_str().unwrap()).unwrap();
    assert_eq!(
        package.objects.len(),
        2,
        "research references must include both derived and raw originals"
    );
    let encoded = serde_json::to_value(package).unwrap();
    let encoded_objects = encoded["objects"].clone();
    let path = dir.path().join("research-to.sqlite");
    let mut to = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let mut missing = encoded.clone();
    missing["objects"].as_array_mut().unwrap().pop();
    assert!(
        portable_document::import(
            &mut to,
            serde_json::from_value(missing).unwrap(),
            "missing_research"
        )
        .is_err()
    );
    assert_eq!(
        to.query_row::<i64, _, _>("SELECT count(*) FROM sources", [], |r| r.get(0))
            .unwrap(),
        0
    );
    let imported = portable_document::import(
        &mut to,
        serde_json::from_value(encoded.clone()).unwrap(),
        "research_package",
    )
    .unwrap();
    let value = &imported["document"]["editor_json"]["attrs"]["archeaxis_research"];
    assert_eq!(value["question"], "Public evidence comparison");
    assert_eq!(
        value["counterevidence"][0]["text"],
        "Unverified author comparison"
    );
    assert!(
        value["materials"][0].get("citation").is_none(),
        "old anchor is historical; do not register trusted current location"
    );
    assert!(
        imported["historical_anchors"]
            .as_array()
            .unwrap()
            .iter()
            .any(|record| record["citation"] == citation)
    );
    assert_eq!(imported["anchor_registration"], "NOT_EXECUTED");
    for (i, bytes) in [
        b"Synthetic derived excerpt".as_slice(),
        b"{\"original\":true}".as_slice(),
    ]
    .iter()
    .enumerate()
    {
        assert_eq!(
            archeaxis_store_sqlite::raw_objects::read(
                &to,
                references[i]["sha256"].as_str().unwrap()
            )
            .unwrap(),
            *bytes
        );
    }
    assert_eq!(
        to.query_row::<i64, _, _>("SELECT count(*) FROM anchors", [], |r| r.get(0))
            .unwrap(),
        0
    );
    assert_eq!(
        to.query_row::<i64, _, _>("SELECT count(*) FROM knowledge", [], |r| r.get(0))
            .unwrap(),
        0
    );
    drop(to);
    let mut to = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        portable_document::import(
            &mut to,
            serde_json::from_value(encoded).unwrap(),
            "research_package"
        )
        .unwrap(),
        imported
    );
    // A -> B -> C must retain historical quotations even though B deliberately
    // has no active anchor registration for A's identities.
    let second_package =
        portable_document::export(&to, imported["document"]["document_id"].as_str().unwrap())
            .unwrap();
    assert_eq!(
        serde_json::to_value(&second_package.objects).unwrap(),
        encoded_objects
    );
    assert_eq!(
        serde_json::to_value(&second_package.historical_anchors).unwrap(),
        imported["historical_anchors"]
    );
    let mut third = archeaxis_store_sqlite::init_workspace(
        dir.path().join("research-third.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let third_import =
        portable_document::import(&mut third, second_package, "second_research_package").unwrap();
    assert_eq!(
        third_import["historical_anchors"],
        imported["historical_anchors"]
    );
    assert_eq!(third_import["anchor_registration"], "NOT_EXECUTED");
    assert_eq!(third_import["knowledge_admission"], "NOT_EXECUTED");
    assert!(
        third_import["document"]["editor_json"]["attrs"]["archeaxis_research"]["materials"][0]
            .get("citation")
            .is_none()
    );
    assert_eq!(
        third
            .query_row::<i64, _, _>("SELECT count(*) FROM anchors", [], |r| r.get(0))
            .unwrap(),
        0
    );
    assert_eq!(
        third
            .query_row::<i64, _, _>("SELECT count(*) FROM knowledge", [], |r| r.get(0))
            .unwrap(),
        0
    );
    // An ordinary B save must not make A's historical quote disappear from the
    // next exchange. Ordinary saves deliberately do not inherit authorization basis.
    let imported_id = imported["document"]["document_id"].as_str().unwrap();
    let mut edited = imported["document"]["editor_json"].clone();
    edited["attrs"]["archeaxis_research"]["question"] = json!("Edited question in B");
    let saved = document::save(&mut to, imported_id, 1, edited.clone()).unwrap();
    assert_eq!(saved["version"], 2);
    assert!(
        saved["revision_basis"].is_null(),
        "ordinary save semantics stay unchanged"
    );
    let edited_package = portable_document::export(&to, imported_id).unwrap();
    assert_eq!(edited_package.document["editor_json"], edited);
    assert_eq!(
        serde_json::to_value(&edited_package.objects).unwrap(),
        encoded_objects
    );
    assert_eq!(
        serde_json::to_value(&edited_package.historical_anchors).unwrap(),
        imported["historical_anchors"]
    );
    let mut edited_third = archeaxis_store_sqlite::init_workspace(
        dir.path()
            .join("research-edited-third.sqlite")
            .to_str()
            .unwrap(),
    )
    .unwrap();
    let edited_import =
        portable_document::import(&mut edited_third, edited_package, "edited_research_package")
            .unwrap();
    assert_eq!(edited_import["document"]["editor_json"], edited);
    assert_eq!(
        edited_import["historical_anchors"],
        imported["historical_anchors"]
    );
    assert_eq!(edited_import["anchor_registration"], "NOT_EXECUTED");
    assert_eq!(edited_import["knowledge_admission"], "NOT_EXECUTED");
    assert_eq!(
        edited_third
            .query_row::<i64, _, _>("SELECT count(*) FROM anchors", [], |r| r.get(0))
            .unwrap(),
        0
    );
    assert_eq!(
        edited_third
            .query_row::<i64, _, _>("SELECT count(*) FROM knowledge", [], |r| r.get(0))
            .unwrap(),
        0
    );
    for (index, expected) in [
        b"Synthetic derived excerpt".as_slice(),
        b"{\"original\":true}".as_slice(),
    ]
    .iter()
    .enumerate()
    {
        assert_eq!(
            archeaxis_store_sqlite::raw_objects::read(
                &edited_third,
                references[index]["sha256"].as_str().unwrap()
            )
            .unwrap(),
            *expected
        );
    }
    assert_eq!(
        document::read(&from, original["document_id"].as_str().unwrap(), None).unwrap(),
        original
    );
}

#[test]
fn research_package_rejects_cross_workspace_document_alias_before_importing_objects() {
    let dir = tempfile::tempdir().unwrap();
    let mut from =
        archeaxis_store_sqlite::init_workspace(dir.path().join("alias-a.sqlite").to_str().unwrap())
            .unwrap();
    let mut to =
        archeaxis_store_sqlite::init_workspace(dir.path().join("alias-b.sqlite").to_str().unwrap())
            .unwrap();
    let text = |value| json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":value}]}]});
    let a = document::create_optional_with_request(
        &mut from,
        None,
        None,
        "A evidence",
        text("Original evidence A"),
        Some("shared_request"),
    )
    .unwrap();
    let b = document::create_optional_with_request(
        &mut to,
        None,
        None,
        "B unrelated",
        text("Different content B"),
        Some("shared_request"),
    )
    .unwrap();
    assert_eq!(a["document_id"], b["document_id"]);
    assert_ne!(a["content_sha256"], b["content_sha256"]);
    let source_doc = fixture(&mut from);
    let editor = json!({"type":"doc","content":[],"attrs":{"archeaxis_research":{"schema":"archeaxis.research/v1","question":"Pinned evidence in workspace A",
        "materials":[{"id":"document","note":"Original document A","reference":{"kind":"document","document_id":a["document_id"],"version":1,"block_id":null}},
                     {"id":"source","note":"Original source","reference":{"kind":"source","source_id":source_doc["source_id"],"sha256":source_doc["source_revision"]}}],
        "hypotheses":[],"methods":[],"experiments":[],"counterevidence":[],"conclusions":[],"unresolved":[]}}});
    let research = document::create_optional(&mut from, None, None, "Research", editor).unwrap();
    let package =
        portable_document::export(&from, research["document_id"].as_str().unwrap()).unwrap();
    assert_eq!(package.objects.len(), 1);
    let outcome = portable_document::import(&mut to, package, "must_not_alias");
    assert!(
        outcome.is_err(),
        "an unrelated same-ID document cannot silently replace imported evidence"
    );
    assert_eq!(
        document::read(&to, b["document_id"].as_str().unwrap(), None).unwrap(),
        b
    );
    assert_eq!(document::list(&to).unwrap().len(), 1);
    assert_eq!(
        to.query_row::<i64, _, _>("SELECT count(*) FROM sources", [], |r| r.get(0))
            .unwrap(),
        0
    );
}
