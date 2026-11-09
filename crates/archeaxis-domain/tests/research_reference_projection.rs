use archeaxis_domain::{document, knowledge, research};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::{Connection, params};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

// A legacy/imported snapshot can contain metadata that current writes reject.
// Seed only an isolated synthetic workspace and preserve its actual digest.
fn replace_fixture_editor(conn: &Connection, id: &str, editor: &Value) {
    let raw = editor.to_string();
    let digest = hex::encode(Sha256::digest(raw.as_bytes()));
    conn.execute("UPDATE document_versions SET editor_json=?1,content_sha256=?2 WHERE document_id=?3 AND version=1",
        params![raw, digest, id]).unwrap();
}

fn research_editor(reference: Value) -> Value {
    json!({"type":"doc","content":[],"attrs":{"archeaxis_research":{
        "schema":"archeaxis.research/v1","question":"synthetic",
        "materials":[{"id":"material","note":"synthetic","reference":reference}],
        "hypotheses":[],"methods":[],"experiments":[],"counterevidence":[],
        "conclusions":[],"unresolved":[]}}})
}

#[test]
fn unavailable_and_unsupported_historical_references_remain_read_only() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("research.sqlite").to_str().unwrap()).unwrap();
    let target = document::create_optional(
        &mut conn,
        None,
        None,
        "target",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let reference =
        json!({"kind":"document","document_id":target["document_id"],"version":1,"block_id":null});
    let editor = research_editor(reference.clone());
    let doc = document::create_optional(&mut conn, None, None, "research", editor.clone()).unwrap();
    let id = doc["document_id"].as_str().unwrap();
    let absent =
        research::reference_projection(&conn, target["document_id"].as_str().unwrap(), None)
            .unwrap();
    assert_eq!(absent["metadata_status"], "absent");
    assert!(absent["references"].as_array().unwrap().is_empty());
    let current = research::reference_projection(&conn, id, Some(1)).unwrap();
    assert_eq!(current["references"][0]["status"], "resolved");
    assert_eq!(
        current["references"][0]["object"]["version_relation"],
        "current"
    );
    assert_eq!(current["references"][0]["version_relation"], "current");
    let target_id = target["document_id"].as_str().unwrap();
    conn.execute(
        "UPDATE documents SET current_version=0 WHERE document_id=?1",
        [target_id],
    )
    .unwrap();
    let inconsistent = research::reference_projection(&conn, id, Some(1)).unwrap();
    assert_eq!(
        inconsistent["references"][0]["version_relation"],
        "unconfirmed"
    );
    assert_eq!(inconsistent["references"][0]["current_version"], 0);
    conn.execute(
        "UPDATE documents SET current_version=1 WHERE document_id=?1",
        [target_id],
    )
    .unwrap();

    let mut missing = editor.clone();
    missing["attrs"]["archeaxis_research"]["materials"][0]["reference"]["document_id"] =
        json!("missing-document");
    replace_fixture_editor(&conn, id, &missing);
    let unavailable = research::reference_projection(&conn, id, Some(1)).unwrap();
    assert_eq!(unavailable["metadata_status"], "supported");
    assert_eq!(unavailable["references"][0]["status"], "unavailable");
    assert!(unavailable["references"][0]["object"].is_null());
    assert_eq!(
        unavailable["references"][0]["reference"]["document_id"],
        "missing-document"
    );

    let mut unknown = missing.clone();
    unknown["attrs"]["archeaxis_research"]["schema"] = json!("archeaxis.research/v99");
    replace_fixture_editor(&conn, id, &unknown);
    let projection = research::reference_projection(&conn, id, Some(1)).unwrap();
    assert_eq!(projection["metadata_status"], "unsupported");
    assert!(projection["references"].as_array().unwrap().is_empty());
    let stored: String = conn
        .query_row(
            "SELECT editor_json FROM document_versions WHERE document_id=?1 AND version=1",
            [id],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(stored, unknown.to_string());

    let mut excessive = editor;
    excessive["attrs"]["archeaxis_research"]["hypotheses"] = json!([{
        "id":"too-many", "text":"synthetic", "references":vec![reference; 256]
    }]);
    replace_fixture_editor(&conn, id, &excessive);
    let projection = research::reference_projection(&conn, id, Some(1)).unwrap();
    assert_eq!(projection["metadata_status"], "unsupported");
    assert!(projection["references"].as_array().unwrap().is_empty());
}

#[test]
fn database_failure_is_not_reported_as_a_missing_reference() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("unavailable.sqlite").to_str().unwrap()).unwrap();
    let knowledge_id = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "synthetic",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    let doc = document::create_optional(
        &mut conn,
        None,
        None,
        "research",
        research_editor(json!({
            "kind":"knowledge", "knowledge_id":knowledge_id
        })),
    )
    .unwrap();
    conn.execute("DROP TABLE knowledge_supersedes", []).unwrap();
    let result =
        research::reference_projection(&conn, doc["document_id"].as_str().unwrap(), Some(1));
    assert!(matches!(result, Err(document::Error::Sql(_))));
}
