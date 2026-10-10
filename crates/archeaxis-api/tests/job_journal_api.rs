//! INTEGRATED Core/SQLite HTTP journal; no worker/model execution.
use archeaxis_application::executor::Executor;
use axum::{Router, body::Body, http::Request};
use http_body_util::BodyExt;
use serde_json::{Value,json};
use tower::ServiceExt;
use std::path::PathBuf;
async fn call(app:&Router,method:&str,path:&str,body:Value,actor:&str)->(u16,Value){
    call_id(app,method,path,body,actor,"journal_abandoned").await
}
async fn call_id(app:&Router,method:&str,path:&str,body:Value,actor:&str,id:&str)->(u16,Value){
    let reply=app.clone().oneshot(Request::builder().method(method).uri(path).header("content-type","application/json").header("x-archeaxis-actor",actor).header("idempotency-key",id).body(Body::from(body.to_string())).unwrap()).await.unwrap();
    let status=reply.status().as_u16();let bytes=reply.into_body().collect().await.unwrap().to_bytes();
    (status,serde_json::from_slice(&bytes).unwrap_or(Value::Null))
}
#[tokio::test]
async fn journal_restart_and_exact_clearance_never_depend_on_a_client_ack_or_latest_job_state(){
    let dir=tempfile::tempdir().unwrap();
    async fn open(dir:&std::path::Path)->Executor {
        Executor::open(&dir.join("db.sqlite"),&dir.join("staging"),&PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap()),&PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/python-workers/transport/text_ndjson.py")).await.unwrap()
    }
    let executor=open(dir.path()).await;let app=archeaxis_api::runtime::router(executor.clone());
    let (status,source)=call(&app,"POST","/api/v1/imports",json!({"name":"owned.txt","content_base64":"eA=="}),"human").await;
    assert_eq!(status,202,"{source}");
    let (_,basis)=call(&app,"GET","/api/v1/workspace/ui-state",Value::Null,"human").await;
    let entry=json!({"source_id":source["source_id"],"source_revision":source["sha256"],"job_id":"journal_job","request_id":"journal_request","kind":"text","body":{"deadline_ms":60000,"split":false,"words":false},"surface":"manual","mode":"single","origin_restore_epoch":"initial","relative":null});
    let state=json!({"drafts":{},"opened_documents":[],"active_document":null,"page_id":"03","pending_jobs":{"journal_request":entry}});
    let request=json!({"workspace_id":basis["workspace_id"],"restore_epoch":"initial","state_revision":basis["state_revision"],"state":state});
    let (status,saved)=call(&app,"PUT","/api/v1/workspace/ui-state",request.clone(),"human").await;assert_eq!(status,200,"{saved}");
    let mut old_client=request;old_client["state_revision"]=saved["state_revision"].clone();old_client["state"].as_object_mut().unwrap().remove("pending_jobs");
    assert_eq!(call(&app,"PUT","/api/v1/workspace/ui-state",old_client,"human").await.0,422);
    drop(app);drop(executor);tokio::task::yield_now().await;
    let executor=open(dir.path()).await;let app=archeaxis_api::runtime::router(executor.clone());
    assert_eq!(call(&app,"GET","/api/v1/workspace/ui-state",Value::Null,"human").await.1,saved);
    let clear=json!({"workspace_id":saved["workspace_id"],"restore_epoch":"initial","state_revision":saved["state_revision"],"request_id":"journal_request","action":"abandon_unadmitted"});
    assert_eq!(call(&app,"POST","/api/v1/workspace/ui-state/clear-job",clear.clone(),"machine").await.0,403);
    let enqueue=json!({"job_id":"journal_job","input_ref":source["source_id"],"kind":"text"});
    assert_eq!(call(&app,"POST","/api/v1/jobs",enqueue,"human").await.0,202);
    executor.store().submit_wait(|conn|{
        conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('journal_job',1,'journal_request',?1,'running')",[json!({"job_id":"journal_job","request_id":"journal_request","deadline_ms":60000,"parameters":{"split":false,"words":false}}).to_string()])?;Ok::<_,rusqlite::Error>(())
    }).await.unwrap().unwrap();
    assert_eq!(call(&app,"POST","/api/v1/workspace/ui-state/clear-job",clear.clone(),"human").await.0,422);
    let mut terminal=clear.clone();terminal["action"]=json!("terminal");
    assert_eq!(call(&app,"POST","/api/v1/workspace/ui-state/clear-job",terminal.clone(),"human").await.0,422);
    executor.store().submit_wait(|conn|{conn.execute("UPDATE job_attempts SET state='failed',request_json=json_set(request_json,'$.deadline_ms',1)",[])?;Ok::<_,rusqlite::Error>(())}).await.unwrap().unwrap();
    assert_eq!(call(&app,"POST","/api/v1/workspace/ui-state/clear-job",terminal.clone(),"human").await.0,422);
    executor.store().submit_wait(|conn|{conn.execute("UPDATE job_attempts SET request_json=json_set(request_json,'$.deadline_ms',60000)",[])?;Ok::<_,rusqlite::Error>(())}).await.unwrap().unwrap();
    let (status,cleared)=call(&app,"POST","/api/v1/workspace/ui-state/clear-job",terminal,"human").await;assert_eq!(status,200);
    let mut abandoned_entry=entry.clone();abandoned_entry["request_id"]=json!("journal_abandoned");
    let stage=json!({"workspace_id":cleared["workspace_id"],"restore_epoch":"initial","state_revision":cleared["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"03","pending_jobs":{"journal_abandoned":abandoned_entry}}});
    let (status,staged)=call(&app,"PUT","/api/v1/workspace/ui-state",stage,"human").await;assert_eq!(status,200);
    let clear=json!({"workspace_id":staged["workspace_id"],"restore_epoch":"initial","state_revision":staged["state_revision"],"request_id":"journal_abandoned","action":"abandon_unadmitted"});
    executor.store().submit_wait(|conn|archeaxis_store_sqlite::capability_settings::set_enabled(conn,"text.extract",false)).await.unwrap().unwrap();
    let (clear_reply,execute_reply)=tokio::join!(
        call(&app,"POST","/api/v1/workspace/ui-state/clear-job",clear,"human"),
        call(&app,"POST","/api/v1/jobs/journal_job/executions",json!({"deadline_ms":60000,"split":false,"words":false}),"human")
    );
    assert_eq!(clear_reply.0,200);
    assert!(matches!(execute_reply.0,409|410),"same admission lock yields disabled refusal or durable abandonment, never worker execution");
    let claims=executor.store().submit_wait(|conn|conn.query_row("SELECT count(*) FROM job_attempts WHERE request_id='journal_abandoned'",[],|r|r.get::<_,i64>(0))).await.unwrap().unwrap();
    assert_eq!(claims,0,"concurrent disabled execute and abandonment never acquire a durable claim");
    let replay=call_id(&app,"POST","/api/v1/jobs/journal_job/executions",json!({"deadline_ms":60000,"split":false,"words":false}),"human","journal_request").await;
    assert_eq!(replay.0,202,"existing exact ledger replay precedes capability/tombstone admission checks");
    assert_eq!(replay.1["replayed"],true);
    assert_eq!(call_id(&app,"POST","/api/v1/jobs/journal_job/executions",json!({"deadline_ms":1,"split":false,"words":false}),"human","journal_request").await.0,409,"ledger replay cannot replace the original budget");
    assert_eq!(call(&app,"POST","/api/v1/jobs/journal_job/executions",json!({"deadline_ms":60000,"split":false,"words":false}),"human").await.0,410,"late execute must be refused by a durable tombstone before any worker starts");
    drop(app);drop(executor);tokio::task::yield_now().await;
    let executor=open(dir.path()).await;let app=archeaxis_api::runtime::router(executor);
    assert_eq!(call(&app,"POST","/api/v1/jobs/journal_job/executions",json!({"deadline_ms":60000,"split":false,"words":false}),"human").await.0,410,"abandoned identity fence survives restart");
}
