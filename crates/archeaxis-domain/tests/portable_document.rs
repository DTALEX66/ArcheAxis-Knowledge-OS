use archeaxis_domain::{ImportOutcome, document, portable_document, source};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
fn fixture(conn: &mut rusqlite::Connection) -> Value {
    let bytes = include_bytes!("../../../tests/fixtures/golden/golden-screenshot-ocr.png");
    let (id, sha) = match source::import_source(conn, bytes, "synthetic.png", None).unwrap() {
        ImportOutcome::Imported { source_id, sha256 }
        | ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
    };
    let editor = json!({"type":"doc","attrs":{"future_attribute":{"keep":true},"archeaxis_expression":{"schema":"archeaxis.expression/v1","nodes":[{"id":"pic","type":"media","text":"合成媒体","x":0,"y":0,"width":32,"height":32,"media":{"source_id":id,"sha256":sha,"media_type":"image/png"}}],"edges":[]}},"content":[{"type":"future_widget","attrs":{"opaque":{"keep":[1,2,3]}},"content":[{"type":"text","text":"中文未知节点"}]}]});
    document::create_optional(conn, Some(&id), Some(&sha), "便携合成资料", editor).unwrap()
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
