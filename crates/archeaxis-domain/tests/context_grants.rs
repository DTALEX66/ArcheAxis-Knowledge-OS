use archeaxis_domain::{
    context_grant::{self, Consumption, Operation},
    document, knowledge,
};
use archeaxis_store_sqlite::init_workspace;
use serde_json::{Value, json};

fn editor(knowledge_id: Option<&str>, state: &str) -> Value {
    json!({"type":"doc","attrs":{"unknown_payload":{"keep":[1,null,true]},"archeaxis_context_grant":{
        "schema":"archeaxis.context-grant/v1","purpose":"SYNTHETIC project answer","consumer":"local-machine",
        "operations":["answer"],"knowledge_id":knowledge_id,"provenance":[],
        "authorization_basis":"Owner authorizes only local answering from this knowledge","expires_at":2000,"state":state
    }},"content":[{"type":"paragraph","content":[{"type":"text","text":"ordinary saved notes"}]}]})
}
fn input(snapshot: &Value) -> Consumption {
    Consumption {
        document_id: snapshot["document_id"].as_str().unwrap().into(),
        version: snapshot["version"].as_i64().unwrap(),
        content_sha256: snapshot["content_sha256"].as_str().unwrap().into(),
        purpose: "SYNTHETIC project answer".into(),
    }
}

#[test]
fn context_permission_expiry_scope_and_current_knowledge_are_independent() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let id = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "SYNTHETIC knowledge",
        "accepted",
        None,
        None,
        "owner",
    )
    .unwrap();
    let first = document::create_optional(
        &mut conn,
        None,
        None,
        "context",
        editor(Some(&id), "granted"),
    )
    .unwrap();
    let mut request = input(&first);
    let proof = context_grant::consume(&conn, &request, Operation::Answer, &id, 1999).unwrap();
    assert_eq!(proof["current_permission_valid"], true);
    assert!(context_grant::consume(&conn, &request, Operation::Answer, &id, 2000).is_err());
    assert!(context_grant::consume(&conn, &request, Operation::Retest, &id, 1999).is_err());
    request.purpose = "other scope".into();
    assert!(context_grant::consume(&conn, &request, Operation::Answer, &id, 1999).is_err());
    request = input(&first);
    knowledge::review(
        &mut conn,
        &id,
        "deprecated",
        "owner",
        Some("withdraw SYNTHETIC knowledge"),
        None,
    )
    .unwrap();
    assert!(context_grant::consume(&conn, &request, Operation::Answer, &id, 1999).is_err());
    assert_eq!(
        document::read(&conn, &request.document_id, Some(1)).unwrap(),
        first
    );
}

#[test]
fn context_revocation_is_terminal_across_restore_and_restart_but_history_survives() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let id = knowledge::create_knowledge(
        &mut conn,
        "FACTUAL_CLAIM",
        "SYNTHETIC knowledge",
        "accepted",
        None,
        None,
        "owner",
    )
    .unwrap();
    let first = document::create_optional(
        &mut conn,
        None,
        None,
        "context",
        editor(Some(&id), "granted"),
    )
    .unwrap();
    let request = input(&first);
    let revoked = document::save(
        &mut conn,
        &request.document_id,
        1,
        editor(Some(&id), "revoked"),
    )
    .unwrap();
    assert!(context_grant::consume(&conn, &request, Operation::Answer, &id, 1000).is_err());
    assert!(context_grant::consume(&conn, &input(&revoked), Operation::Answer, &id, 1000).is_err());
    assert!(document::restore(&mut conn, &request.document_id, 2, 1).is_err());
    // Metadata removal does not authorize consumption or permit later revival.
    let removed = document::save(
        &mut conn,
        &request.document_id,
        2,
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    assert!(context_grant::consume(&conn, &input(&removed), Operation::Answer, &id, 1000).is_err());
    assert!(
        document::save(
            &mut conn,
            &request.document_id,
            3,
            editor(Some(&id), "granted")
        )
        .is_err()
    );
    drop(conn);
    let conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert!(context_grant::consume(&conn, &request, Operation::Answer, &id, 1000).is_err());
    assert_eq!(
        document::read(&conn, &request.document_id, Some(1)).unwrap(),
        first
    );
    assert_eq!(
        document::read(&conn, &request.document_id, Some(2)).unwrap(),
        revoked
    );
}

#[test]
fn candidate_context_saves_without_authorizing_consume_and_preserves_unknown_notes() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("workspace.sqlite").to_str().unwrap()).unwrap();
    let value = editor(None, "candidate");
    let first = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "context draft",
        value.clone(),
        Some("context-draft-retry"),
    )
    .unwrap();
    assert_eq!(
        document::create_optional_with_request(
            &mut conn,
            None,
            None,
            "context draft",
            value,
            Some("context-draft-retry")
        )
        .unwrap(),
        first
    );
    assert_eq!(
        first["editor_json"]["attrs"]["unknown_payload"],
        json!({"keep":[1,null,true]})
    );
    assert!(
        context_grant::consume(&conn, &input(&first), Operation::Answer, "unknown", 1000).is_err()
    );
    let mut bad = editor(None, "granted");
    assert!(document::create_optional(&mut conn, None, None, "bad", bad.clone()).is_err());
    bad["attrs"]["archeaxis_context_grant"]["consumer"] = json!("private-agent-session");
    assert!(document::create_optional(&mut conn, None, None, "bad", bad).is_err());
}
