//! INTEGRATED owned Core/SQLite archive candidate; NOT_EXECUTED before integration.
use archeaxis_domain::{context_grant::{self,Consumption,Operation},document,knowledge};
use archeaxis_archive::{export_workspace,restore_workspace};
use serde_json::{json,Value};
fn grant_editor(kid:&str)->Value {json!({"type":"doc","content":[],"attrs":{"archeaxis_context_grant":{
    "schema":"archeaxis.context-grant/v1","purpose":"owned restore authorization test","consumer":"local-machine",
    "operations":["answer"],"knowledge_id":kid,"provenance":[],"authorization_basis":"SYNTHETIC explicit owner authorization",
    "expires_at":null,"state":"granted"}}})}
fn input(d:&Value)->Consumption {Consumption {document_id:d["document_id"].as_str().unwrap().into(),version:d["version"].as_i64().unwrap(),
    content_sha256:d["content_sha256"].as_str().unwrap().into(),purpose:"owned restore authorization test".into()}}
#[test]
fn every_restore_fences_old_grant_ids_preserves_history_and_requires_new_human_identity() {
    let dir=tempfile::tempdir().unwrap();let db=dir.path().join("original.sqlite");
    let mut conn=archeaxis_store_sqlite::init_workspace(db.to_str().unwrap()).unwrap();
    let kid=knowledge::create_knowledge(&mut conn,"NOTE","SYNTHETIC accepted context","accepted",None,None,"owner").unwrap();
    let original=document::create_optional_with_request(&mut conn,None,None,"original grant",grant_editor(&kid),Some("original-fixture-grant")).unwrap();
    context_grant::consume(&conn,&input(&original),Operation::Answer,&kid,1).unwrap();
    let archive=dir.path().join("archive");export_workspace(db.to_str().unwrap(),archive.to_str().unwrap()).unwrap();
    let archive_doc_bytes=std::fs::read(archive.join("document_versions.jsonl")).unwrap();
    let restored=dir.path().join("restored.sqlite");restore_workspace(archive.to_str().unwrap(),restored.to_str().unwrap()).unwrap();
    let mut after=archeaxis_store_sqlite::init_workspace(restored.to_str().unwrap()).unwrap();
    assert_eq!(document::read(&after,original["document_id"].as_str().unwrap(),Some(1)).unwrap(),original);
    assert!(context_grant::consume(&after,&input(&original),Operation::Answer,&kid,1).is_err());
    assert_eq!(std::fs::read(archive.join("document_versions.jsonl")).unwrap(),archive_doc_bytes);
    let renewed=document::create_optional_with_request(&mut after,None,None,"new explicit human grant",grant_editor(&kid),Some("new-fixture-grant")).unwrap();
    assert_ne!(renewed["document_id"],original["document_id"]);
    context_grant::consume(&after,&input(&renewed),Operation::Answer,&kid,1).unwrap();
    let epoch1:String=after.query_row("SELECT value FROM workspace_meta WHERE key='authorization_restore_fence'",[],|r|r.get(0)).unwrap();
    let second_archive=dir.path().join("second-archive");export_workspace(restored.to_str().unwrap(),second_archive.to_str().unwrap()).unwrap();
    let second_db=dir.path().join("second-restored.sqlite");restore_workspace(second_archive.to_str().unwrap(),second_db.to_str().unwrap()).unwrap();
    let second=archeaxis_store_sqlite::init_workspace(second_db.to_str().unwrap()).unwrap();
    let epoch2:String=second.query_row("SELECT value FROM workspace_meta WHERE key='authorization_restore_fence'",[],|r|r.get(0)).unwrap();
    assert_ne!(epoch1,epoch2);
    assert!(context_grant::consume(&second,&input(&renewed),Operation::Answer,&kid,1).is_err());
    assert_eq!(document::read(&second,renewed["document_id"].as_str().unwrap(),Some(1)).unwrap(),renewed);
    // Replaying an even older archive generates a fresh fence again, never its historical epoch.
    let old_again=dir.path().join("old-again.sqlite");restore_workspace(archive.to_str().unwrap(),old_again.to_str().unwrap()).unwrap();
    let old=archeaxis_store_sqlite::init_workspace(old_again.to_str().unwrap()).unwrap();
    assert!(context_grant::consume(&old,&input(&original),Operation::Answer,&kid,1).is_err());
}
