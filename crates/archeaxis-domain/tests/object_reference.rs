use archeaxis_domain::{
    document,
    object_reference::{self, Reference},
    source,
};
use archeaxis_store_sqlite::init_workspace;
use serde_json::json;
#[test]
fn document_and_block_references_pin_history_after_restart() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let first=document::create_optional(&mut conn,None,None,"原文",json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"original"},"content":[{"type":"text","text":"v1"}]}]})).unwrap();
    let id = first["document_id"].as_str().unwrap().to_owned();
    let reference = Reference::Document {
        document_id: id.clone(),
        version: 1,
        block_id: Some("original".into()),
    };
    document::save(&mut conn, &id, 1, json!({"type":"doc","content":[]})).unwrap();
    drop(conn);
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    let resolved = object_reference::resolve(&conn, &reference).unwrap();
    assert_eq!(resolved["content_sha256"], first["content_sha256"]);
    assert!(
        object_reference::validate(
            &conn,
            &Reference::Document {
                document_id: id.clone(),
                version: 2,
                block_id: Some("original".into())
            }
        )
        .is_err()
    );
    assert!(
        object_reference::validate(
            &conn,
            &Reference::Document {
                document_id: id,
                version: 99,
                block_id: None
            }
        )
        .is_err()
    );
}
#[test]
fn source_hash_and_absent_object_fail_closed() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let imported =
        source::import_source(&mut conn, "证据".as_bytes(), "material.txt", None).unwrap();
    let record: (String, String) = conn
        .query_row("SELECT source_id,sha256 FROM sources", [], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })
        .unwrap();
    let _ = imported;
    assert!(
        object_reference::validate(
            &conn,
            &Reference::Source {
                source_id: record.0.clone(),
                sha256: record.1
            }
        )
        .is_ok()
    );
    assert!(
        object_reference::validate(
            &conn,
            &Reference::Source {
                source_id: record.0,
                sha256: "0".repeat(64)
            }
        )
        .is_err()
    );
    assert!(
        object_reference::validate(
            &conn,
            &Reference::Knowledge {
                knowledge_id: "missing".into()
            }
        )
        .is_err()
    );
    assert!(
        serde_json::from_value::<Reference>(
            json!({"kind":"document","document_id":"doc","version":1,"url":"https://example.com"})
        )
        .is_err()
    );
}
