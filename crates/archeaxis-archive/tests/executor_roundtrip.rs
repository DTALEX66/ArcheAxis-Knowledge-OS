//! Real executor-produced outputs, archive restore and same-attempt replay.
use archeaxis_application::{executor::{Executor,Cancellation},attempts,jobs};
use archeaxis_domain::source::{self,ImportOutcome};
use std::path::PathBuf;
use rusqlite::Connection;

fn outputs(conn:&Connection)->Vec<(String,String)>{
    conn.prepare("SELECT metadata_json,content FROM job_outputs ORDER BY kind").unwrap()
        .query_map([],|r|Ok((r.get(0)?,r.get(1)?))).unwrap().collect::<Result<_,_>>().unwrap()
}
#[tokio::test]
async fn real_worker_output_archive_restores_exact_bytes_and_idempotency() {
    let dir=tempfile::tempdir().unwrap(); let db=dir.path().join("live.sqlite");
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap();
    let worker=root.join("services/python-workers/transport/text_ndjson.py");
    let python:PathBuf=std::env::var_os("ARCHEAXIS_PYTHON").expect("use project dev.py").into();
    let executor=Executor::open(&db,&dir.path().join("staging"),&python,&worker).await.unwrap();
    executor.store().submit(|conn|{
        let sid=match source::import_source(conn,"原文😀\r\n复习\u{2028}".as_bytes(),"notes.md",None).unwrap(){
            ImportOutcome::Imported{source_id,..}=>source_id,_=>unreachable!()};
        jobs::enqueue(conn,"job","text",&sid).unwrap();
    }).await.unwrap();
    executor.execute("job","archive-attempt",5000,&Cancellation::new()).await.unwrap();
    let before=executor.store().submit(|conn|outputs(conn)).await.unwrap();
    assert_eq!(before.len(),3);
    drop(executor);
    let archive=dir.path().join("archive");
    archeaxis_archive::export_workspace(db.to_str().unwrap(),archive.to_str().unwrap()).unwrap();
    let restored=dir.path().join("restored.sqlite");
    archeaxis_archive::restore_workspace(archive.to_str().unwrap(),restored.to_str().unwrap()).unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(restored.to_str().unwrap()).unwrap();
    assert_eq!(outputs(&conn),before);
    let (request,response):(String,String)=conn.query_row("SELECT request_json,response_json FROM job_attempts",[],|r|Ok((r.get(0)?,r.get(1)?))).unwrap();
    let payloads:Vec<Vec<u8>>=conn.prepare("SELECT content FROM job_outputs ORDER BY CASE kind WHEN 'text' THEN 1 WHEN 'document_structure' THEN 2 ELSE 3 END").unwrap()
        .query_map([],|r|r.get::<_,String>(0)).unwrap().map(|s|s.unwrap().into_bytes()).collect();
    attempts::finish(&mut conn,&serde_json::from_str(&request).unwrap(),&serde_json::from_str(&response).unwrap(),&payloads).unwrap();
    assert_eq!(conn.query_row("SELECT count(*) FROM transforms",[],|r|r.get::<_,i64>(0)).unwrap(),1);
    assert_eq!(outputs(&conn),before);
}
