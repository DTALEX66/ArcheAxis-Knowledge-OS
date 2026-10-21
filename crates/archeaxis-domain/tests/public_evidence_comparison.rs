//! Existing Research DTO compatibility, not an external retrieval or quality verdict.
use archeaxis_domain::{anchor, document, portable_document, source};
use archeaxis_store_sqlite::{init_workspace, raw_objects};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn hash(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn import(conn: &mut rusqlite::Connection, bytes: &[u8], name: &str) -> Value {
    let outcome = source::import_source(conn, bytes, name, None).unwrap();
    let (source_id, sha256) = match outcome {
        source::ImportOutcome::Imported { source_id, sha256 }
        | source::ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256),
    };
    json!({"kind":"source","source_id":source_id,"sha256":sha256})
}

#[test]
fn authored_comparison_refs_quote_and_originals_survive_save_reopen_and_portable_exchange() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("comparison.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let raw_bytes = br#"{"synthetic":true,"title":"Metadata only"}"#;
    let snapshot = "AAOS synthetic derived metadata\r\n作者资料😀\n不是原API字节";
    let raw = import(&mut conn, raw_bytes, "synthetic-api.json");
    let derived = import(&mut conn, snapshot.as_bytes(), "synthetic-derived.txt");
    // SYNTHETIC historical Core locator. The UI's actual API consumer additionally
    // calls anchor_create (CAS validation) and anchor_resolve; this test uses the
    // domain interface to verify the exact accepted persistence/portable shape.
    let position = json!({"type":"text","start":0,"end":snapshot.len(),
        "checksum":hash(snapshot.as_bytes()),"location_status":"located"})
    .to_string();
    let anchor_id = anchor::add_anchor(
        &mut conn,
        derived["source_id"].as_str().unwrap(),
        derived["sha256"].as_str().unwrap(),
        &position,
    )
    .unwrap();
    let citation = json!({"schema":"archeaxis.research-citation/v1","anchor_id":anchor_id,
        "source_sha256":derived["sha256"],"anchor_position_sha256":hash(position.as_bytes()),
        "quote":snapshot,"quote_sha256":hash(snapshot.as_bytes()),"read_snapshot_sha256":derived["sha256"]});
    let long_query = "界".repeat(400);
    let research = json!({"schema":"archeaxis.research/v1","question":"Human-authored claim",
        "materials":[{"id":"derived_material","note":"Derived metadata; not verified","reference":derived,"citation":citation},
                     {"id":"raw_material","note":"Original API bytes; not article full text","reference":raw}],
        "hypotheses":[],"methods":[],"experiments":[],"counterevidence":[],"conclusions":[],
        "unresolved":[{"id":"authored_judgment","text":format!("作者判断：支持（未核验，未知识采用）; 来源独立性：UNKNOWN; 主题：{long_query}"),"references":[derived,raw]}]});
    let body = json!([{"type":"paragraph","content":[{"type":"text","text":"Keep human body"}]}]);
    let editor = json!({"type":"doc","content":body,"attrs":{"manual":{"preserve":[1,"two"]},
        "archeaxis_research":research,
        "archeaxis_relations":{"schema":"archeaxis.relations/v1","relations":[{"id":"authored_support","kind":"supports","label":"Author judgment; independence UNKNOWN; not truth","target":derived}]}}});
    let first = document::create_optional(&mut conn, None, None, "Comparison", editor).unwrap();
    let id = first["document_id"].as_str().unwrap();
    let mut edited = first["editor_json"].clone();
    edited["attrs"]["archeaxis_research"]["question"] = json!("Human correction, still unverified");
    let second = document::save(&mut conn, id, 1, edited.clone()).unwrap();
    assert!(document::save(&mut conn, id, 1, edited).is_err());
    assert_eq!(
        second["editor_json"]["content"],
        first["editor_json"]["content"]
    );
    assert_eq!(
        second["editor_json"]["attrs"]["manual"],
        first["editor_json"]["attrs"]["manual"]
    );
    drop(conn);
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(document::read(&conn, id, None).unwrap(), second);
    assert_eq!(document::read(&conn, id, Some(1)).unwrap(), first);
    assert!(
        second["editor_json"]["attrs"]["archeaxis_research"]["unresolved"][0]["text"]
            .as_str()
            .unwrap()
            .contains(&long_query)
    );
    let package = portable_document::export(&conn, id).unwrap();
    assert_eq!(package.objects.len(), 2);
    for (reference, expected) in [
        (&raw, raw_bytes.as_slice()),
        (&derived, snapshot.as_bytes()),
    ] {
        let object = package
            .objects
            .iter()
            .find(|o| o.sha256 == reference["sha256"].as_str().unwrap())
            .unwrap();
        assert_eq!(object.bytes, expected);
    }
    let encoded = serde_json::to_value(package).unwrap();
    let to_path = dir.path().join("comparison-import.sqlite");
    let mut to = init_workspace(to_path.to_str().unwrap()).unwrap();
    let mut incomplete = encoded.clone();
    incomplete["objects"].as_array_mut().unwrap().pop();
    assert!(
        portable_document::import(
            &mut to,
            serde_json::from_value(incomplete).unwrap(),
            "missing"
        )
        .is_err()
    );
    assert_eq!(document::list(&to).unwrap().len(), 0);
    assert_eq!(
        to.query_row::<i64, _, _>("SELECT count(*) FROM sources", [], |r| r.get(0))
            .unwrap(),
        0
    );
    let imported = portable_document::import(
        &mut to,
        serde_json::from_value(encoded.clone()).unwrap(),
        "comparison",
    )
    .unwrap();
    let target = &imported["document"]["editor_json"];
    assert_eq!(target["content"], second["editor_json"]["content"]);
    assert!(
        target["attrs"]["archeaxis_research"]["materials"][0]
            .get("citation")
            .is_none()
    );
    assert!(
        imported["historical_anchors"]
            .as_array()
            .unwrap()
            .iter()
            .any(|a| a["citation"] == citation)
    );
    assert_eq!(
        target["attrs"]["archeaxis_research"]["unresolved"][0]["references"]
            .as_array()
            .unwrap()
            .len(),
        2
    );
    for (reference, expected) in [
        (&raw, raw_bytes.as_slice()),
        (&derived, snapshot.as_bytes()),
    ] {
        assert_eq!(
            raw_objects::read(&to, reference["sha256"].as_str().unwrap()).unwrap(),
            expected
        );
    }
    assert_eq!(imported["anchor_registration"], "NOT_EXECUTED");
    assert_eq!(imported["knowledge_admission"], "NOT_EXECUTED");
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
    let mut to = init_workspace(to_path.to_str().unwrap()).unwrap();
    assert_eq!(
        portable_document::import(
            &mut to,
            serde_json::from_value(encoded).unwrap(),
            "comparison"
        )
        .unwrap(),
        imported
    );
    assert_eq!(document::read(&conn, id, None).unwrap(), second);
    // Wrong quote/position identities never create an additional version.
    for field in ["quote_sha256", "anchor_position_sha256", "source_sha256"] {
        let mut bad = second["editor_json"].clone();
        bad["attrs"]["archeaxis_research"]["materials"][0]["citation"][field] =
            json!("0".repeat(64));
        assert!(document::save(&mut conn, id, 2, bad).is_err());
        assert_eq!(document::read(&conn, id, None).unwrap(), second);
    }
}
