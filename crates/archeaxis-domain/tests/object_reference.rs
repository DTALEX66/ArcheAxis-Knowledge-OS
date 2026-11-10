use archeaxis_domain::{
    document, knowledge,
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
    let current = object_reference::resolve(&conn, &reference).unwrap();
    assert_eq!(current["version_relation"], "current");
    assert_eq!(current["current_version"], 1);
    document::save(&mut conn, &id, 1, json!({"type":"doc","content":[]})).unwrap();
    drop(conn);
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    let resolved = object_reference::resolve(&conn, &reference).unwrap();
    assert_eq!(resolved["content_sha256"], first["content_sha256"]);
    assert_eq!(resolved["reference"]["version"], 1);
    assert_eq!(resolved["version_relation"], "historical");
    assert_eq!(resolved["current_version"], 2);
    let newest = object_reference::resolve(
        &conn,
        &Reference::Document {
            document_id: id.clone(),
            version: 2,
            block_id: None,
        },
    )
    .unwrap();
    assert_eq!(newest["version_relation"], "current");
    assert_eq!(newest["current_version"], 2);
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
                document_id: id.clone(),
                version: 99,
                block_id: None
            }
        )
        .is_err()
    );
    // Simulate an inconsistent stored head in this disposable fixture: a
    // readable future version must not be advertised as current or historical.
    conn.execute(
        "UPDATE documents SET current_version=0 WHERE document_id=?1",
        [&id],
    )
    .unwrap();
    let unconfirmed = object_reference::resolve(&conn, &reference).unwrap();
    assert_eq!(unconfirmed["version_relation"], "unconfirmed");
    assert_eq!(unconfirmed["current_version"], 0);
}
#[test]
fn knowledge_reference_reports_currentness_beside_the_immutable_identity() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "v1",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    let reference = Reference::Knowledge {
        knowledge_id: kid.clone(),
    };
    let resolved = object_reference::resolve(&conn, &reference).unwrap();
    assert_eq!(resolved["identity"], "immutable_knowledge_id");
    assert_eq!(resolved["readable"], true);
    assert_eq!(resolved["currentness"], "current");
    assert_eq!(resolved["superseded_by"], json!(null));
    assert_eq!(resolved["reference"]["knowledge_id"], kid);

    let next = knowledge::review(
        &mut conn,
        &kid,
        "modified",
        "owner",
        Some("fix"),
        Some("v2"),
    )
    .unwrap();
    knowledge::review(&mut conn, &next, "accepted", "owner", None, None).unwrap();
    let historical = object_reference::resolve(&conn, &reference).unwrap();
    assert_eq!(historical["currentness"], "superseded");
    assert_eq!(historical["superseded_by"], json!(next));
    assert_eq!(historical["successor_count"], 1);
    // The successor is current; the old identity is still readable and still
    // points at itself rather than being silently substituted.
    let newest =
        object_reference::resolve(&conn, &Reference::Knowledge { knowledge_id: next }).unwrap();
    assert_eq!(newest["currentness"], "current");
    assert_eq!(newest["status"], "accepted");

    let rejected = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "bad",
        "candidate",
        None,
        None,
        "owner",
    )
    .unwrap();
    knowledge::review(&mut conn, &rejected, "rejected", "owner", None, None).unwrap();
    let refused = object_reference::resolve(
        &conn,
        &Reference::Knowledge {
            knowledge_id: rejected,
        },
    )
    .unwrap();
    assert_eq!(refused["currentness"], "not_current");
    assert_eq!(refused["readable"], true);
    assert_eq!(refused["status"], "rejected");
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
