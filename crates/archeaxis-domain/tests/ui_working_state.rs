use archeaxis_domain::ui_state::{self, ClearSaved, Draft, Error, Recover, RecoveryAction, State, Write};
use rusqlite::Connection;
use serde_json::{Value,json};
use std::collections::BTreeMap;

fn fixture(path: &std::path::Path) -> Connection {
    let conn = Connection::open(path).unwrap();
    conn.execute_batch("CREATE TABLE IF NOT EXISTS workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(document_id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS document_versions(document_id TEXT,version INTEGER,editor_json TEXT);
        INSERT OR IGNORE INTO documents VALUES('doc_a');").unwrap();
    if conn.query_row("SELECT count(*) FROM document_versions",[],|r|r.get::<_,i64>(0)).unwrap() == 0 {
        conn.execute("INSERT INTO document_versions VALUES('doc_a',1,?1)",[body("original").to_string()]).unwrap();
    }
    conn
}
fn body(text: &str) -> Value { json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"block_a"},"content":[{"type":"text","text":text}]}]}) }
fn request(receipt: &Value, text: &str) -> Write {
    Write { workspace_id:receipt["workspace_id"].as_str().unwrap().into(),restore_epoch:receipt["restore_epoch"].as_str().unwrap().into(),state_revision:receipt["state_revision"].as_i64().unwrap(),
        state: State { drafts:BTreeMap::from([("doc_a".into(),Draft {base_version:1,editor_json:body(text)})]),opened_documents:vec!["doc_a".into()],active_document:Some("doc_a".into()),page_id:Some("03".into()),pending_original:None } }
}
#[test]
fn state_survives_reopen_and_stale_cas_cannot_replace_newer_draft() {
    let dir=tempfile::tempdir().unwrap();let path=dir.path().join("db.sqlite");
    let mut conn=fixture(&path);let initial=ui_state::read(&mut conn).unwrap();
    let stale=request(&initial,"late old content");
    let saved=ui_state::write(&mut conn,request(&initial,"new 中文 draft")).unwrap();
    assert!(matches!(ui_state::write(&mut conn,stale),Err(Error::Conflict)));
    drop(conn);let mut conn=fixture(&path);
    let reopened=ui_state::read(&mut conn).unwrap();assert_eq!(reopened,saved);
    assert_eq!(conn.query_row("SELECT count(*) FROM document_versions",[],|r|r.get::<_,i64>(0)).unwrap(),1,"working draft is not a committed document version");
}
#[test]
fn invalid_identity_fields_size_and_unknown_types_are_rejected_without_write() {
    let dir=tempfile::tempdir().unwrap();let mut conn=fixture(&dir.path().join("db.sqlite"));let initial=ui_state::read(&mut conn).unwrap();
    let mut foreign=request(&initial,"x");foreign.workspace_id="foreign".into();assert!(matches!(ui_state::write(&mut conn,foreign),Err(Error::Conflict)));
    let mut absent=request(&initial,"x");absent.state.drafts.get_mut("doc_a").unwrap().base_version=99;assert!(ui_state::write(&mut conn,absent).is_err());
    let mut too_large=request(&initial,"x");too_large.state.drafts.get_mut("doc_a").unwrap().editor_json=body(&"x".repeat(262_144));assert!(ui_state::write(&mut conn,too_large).is_err());
    let mut wrong_type=request(&initial,"x");wrong_type.state.drafts.get_mut("doc_a").unwrap().editor_json=json!("not a document");assert!(ui_state::write(&mut conn,wrong_type).is_err());
    let mut extra=serde_json::to_value(request(&initial,"x")).unwrap();extra["state"]["credentials"]=json!("not accepted");assert!(serde_json::from_value::<Write>(extra).is_err());
    assert_eq!(ui_state::read(&mut conn).unwrap(),initial);
}
#[test]
fn clear_saved_requires_the_real_version_digest_and_never_clears_late_edit() {
    let dir=tempfile::tempdir().unwrap();let mut conn=fixture(&dir.path().join("db.sqlite"));let initial=ui_state::read(&mut conn).unwrap();let saved=ui_state::write(&mut conn,request(&initial,"draft")).unwrap();
    let clear=|v:&Value| ClearSaved { workspace_id:v["workspace_id"].as_str().unwrap().into(),restore_epoch:v["restore_epoch"].as_str().unwrap().into(),state_revision:v["state_revision"].as_i64().unwrap(),document_id:"doc_a".into(),base_version:1,content_sha256:saved["draft_digests"]["doc_a"].as_str().unwrap().into(),saved_version:2 };
    assert!(matches!(ui_state::clear_saved(&mut conn,clear(&saved)),Err(Error::Conflict)),"client ACK cannot invent a committed version");
    conn.execute("INSERT INTO document_versions VALUES('doc_a',2,?1)",[body("draft").to_string()]).unwrap();
    let latest=ui_state::write(&mut conn,request(&saved,"newer unsaved text")).unwrap();
    assert!(matches!(ui_state::clear_saved(&mut conn,clear(&saved)),Err(Error::Conflict)));
    assert!(matches!(ui_state::clear_saved(&mut conn,clear(&latest)),Err(Error::Conflict)),"even current revision cannot clear a different digest");
    let same=ui_state::write(&mut conn,request(&latest,"draft")).unwrap();
    let cleared=ui_state::clear_saved(&mut conn,clear(&same)).unwrap();assert_eq!(cleared["state"]["drafts"],json!({}));assert_eq!(cleared["state"]["active_document"],"doc_a");
}
#[test]
fn restore_quarantines_working_state_until_explicit_human_recovery() {
    let dir=tempfile::tempdir().unwrap();let mut conn=fixture(&dir.path().join("db.sqlite"));let initial=ui_state::read(&mut conn).unwrap();let saved=ui_state::write(&mut conn,request(&initial,"preserved")).unwrap();
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"a".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let preview=ui_state::read(&mut conn).unwrap();assert_eq!(preview["recovery_requires_confirmation"],true);assert_eq!(preview["state"]["drafts"],json!({}));assert_eq!(preview["recovery_candidates"]["drafts"]["doc_a"]["editor_json"],body("preserved"));
    assert!(matches!(ui_state::write(&mut conn,request(&saved,"late pre-restore request")),Err(Error::Conflict)));
    let recovered=ui_state::recover(&mut conn,Recover {workspace_id:preview["workspace_id"].as_str().unwrap().into(),restore_epoch:preview["restore_epoch"].as_str().unwrap().into(),state_revision:preview["state_revision"].as_i64().unwrap(),action:RecoveryAction::Preserve}).unwrap();
    assert_eq!(recovered["recovery_requires_confirmation"],false);assert_eq!(recovered["state"]["drafts"]["doc_a"]["editor_json"],body("preserved"));
    assert_eq!(conn.query_row("SELECT count(*) FROM document_versions",[],|r|r.get::<_,i64>(0)).unwrap(),1,"recovery never writes over committed content");
}

#[test]
fn pending_original_request_is_preserved_before_any_document_exists_and_is_frozen() {
    let dir=tempfile::tempdir().unwrap();let path=dir.path().join("db.sqlite");let mut conn=fixture(&path);let initial=ui_state::read(&mut conn).unwrap();
    let mut pending=request(&initial,"existing draft");pending.state.pending_original=Some(ui_state::OriginalAttempt {create_request_id:"create_fixed_1".into(),title:"new note".into(),editor_json:body("frozen creation body")});
    let stored=ui_state::write(&mut conn,pending).unwrap();assert!(stored["pending_document_id"].as_str().unwrap().starts_with("doc_req_"));
    let mut changed=request(&stored,"existing draft");changed.state.pending_original=Some(ui_state::OriginalAttempt {create_request_id:"create_fixed_1".into(),title:"changed".into(),editor_json:body("modified after UNKNOWN")});
    assert!(ui_state::write(&mut conn,changed).is_err());
    drop(conn);let mut conn=fixture(&path);assert_eq!(ui_state::read(&mut conn).unwrap(),stored);
}

#[test]
fn restoring_a_backup_that_predates_ui_identity_rejects_the_old_session() {
    let dir=tempfile::tempdir().unwrap();let mut conn=fixture(&dir.path().join("db.sqlite"));let original=ui_state::read(&mut conn).unwrap();
    // Models the meta state in an older backup, not a write to a live product DB.
    conn.execute("DELETE FROM workspace_meta WHERE key IN ('ui_workspace_identity_v1','ui_working_state_v1')",[]).unwrap();
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"b".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let restored=ui_state::read(&mut conn).unwrap();assert_ne!(restored["workspace_id"],original["workspace_id"]);assert_eq!(restored["state"]["drafts"],json!({}));
    assert!(matches!(ui_state::write(&mut conn,request(&original,"late old session")),Err(Error::Conflict)));
}
