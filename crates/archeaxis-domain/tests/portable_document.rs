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
