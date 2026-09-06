use archeaxis_application::{executor::Executor,jobs};
use archeaxis_domain::source::{self,ImportOutcome};
use axum::{Router,body::Body,http::Request};
use http_body_util::BodyExt;
use tower::ServiceExt;
use std::{path::PathBuf,time::Duration};

async fn setup(dir:&std::path::Path,stalled:bool)->Executor {
    let python=PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap());
    let script=if stalled {let p=dir.join("stalled.py");std::fs::write(&p,"import time\ntime.sleep(30)\n").unwrap();p}
        else{PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/python-workers/transport/text_ndjson.py")};
    let executor=Executor::open(&dir.join("db.sqlite"),&dir.join("staging"),&python,&script).await.unwrap();
    executor.store().submit(|conn|{
        let id=match source::import_source(conn,"中😀\r\n".as_bytes(),"test.txt",None).unwrap(){ImportOutcome::Imported{source_id,..}=>source_id,_=>unreachable!()};
        for job in ["job","other","third"]{jobs::enqueue(conn,job,"text",&id).unwrap();}
    }).await.unwrap();executor
}
async fn call(router:&Router,method:&str,path:&str,key:&str,body:&str)->(u16,serde_json::Value){
    let mut req=Request::builder().method(method).uri(path).header("content-type","application/json");
    if !key.is_empty(){req=req.header("idempotency-key",key);}
    let resp=router.clone().oneshot(req.body(Body::from(body.to_owned())).unwrap()).await.unwrap();
    let status=resp.status().as_u16();let bytes=resp.into_body().collect().await.unwrap().to_bytes();
    (status,serde_json::from_slice(&bytes).unwrap_or_default())
}
async fn terminal(router:&Router,job:&str)->serde_json::Value{
    tokio::time::timeout(Duration::from_secs(6),async{loop{
        let (status,value)=call(router,"GET",&format!("/api/v1/jobs/{job}"),"","").await;
        assert_eq!(status,200);
        if value["state"]!="running"&&value["state"]!="queued"{return value;}
        tokio::time::sleep(Duration::from_millis(10)).await;
    }}).await.unwrap()
}
#[tokio::test]
async fn http_runs_real_worker_and_replays_without_a_second_transform() {
    let dir=tempfile::tempdir().unwrap();let executor=setup(dir.path(),false).await;
    let router=archeaxis_api::runtime::router(executor.clone());
    assert_eq!(call(&router,"POST","/api/v1/jobs/job/receipts","",r#"{"state":"failed","error":"forged receipt"}"#).await.0,404,"runtime exposed legacy receipt injection");
    let path="/api/v1/jobs/job/executions";
    let (status,_)=call(&router,"POST",path,"run-1",r#"{"deadline_ms":5000}"#).await;
    assert_eq!(status,202,"HTTP execution entry missing");
    assert_eq!(terminal(&router,"job").await["state"],"succeeded");
    let (status,output)=call(&router,"GET","/api/v1/jobs/job/outputs/text","","").await;
    assert_eq!(status,200);assert_eq!(output["content"],"中😀\r\n");
    assert_eq!(call(&router,"POST",path,"run-1",r#"{"deadline_ms":5000}"#).await.0,202);
    assert_eq!(call(&router,"POST",path,"run-1",r#"{"deadline_ms":6000}"#).await.0,409);
    assert_eq!(call(&router,"POST","/api/v1/jobs/other/executions","run-1",r#"{"deadline_ms":5000}"#).await.0,409);
    executor.store().submit(|conn|assert_eq!(conn.query_row("SELECT count(*) FROM transforms",[],|r|r.get::<_,i64>(0)).unwrap(),1)).await.unwrap();
    drop(router);drop(executor);tokio::task::yield_now().await;
    let restored=Executor::open(&dir.path().join("db.sqlite"),&dir.path().join("staging"),&PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap()),
        &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/python-workers/transport/text_ndjson.py")).await.unwrap();
    let router=archeaxis_api::runtime::router(restored);
    let replay=call(&router,"POST",path,"run-1",r#"{"deadline_ms":5000}"#).await;
    assert_eq!(replay.0,202);assert_eq!(replay.1["state"],"succeeded");assert_eq!(replay.1["replayed"],true);
}

#[tokio::test]
async fn durable_ack_cancel_retry_and_parallel_budget_are_not_client_lifetime() {
    let dir=tempfile::tempdir().unwrap();let executor=setup(dir.path(),true).await;
    let router=archeaxis_api::runtime::router(executor.clone());
    let (a,b)=tokio::join!(call(&router,"POST","/api/v1/jobs/job/executions","same",r#"{"deadline_ms":5000}"#),call(&router,"POST","/api/v1/jobs/job/executions","same",r#"{"deadline_ms":5000}"#));
    assert_eq!((a.0,b.0),(202,202));
    executor.store().submit(|conn|{
        assert_eq!(conn.query_row("SELECT count(*) FROM job_attempts",[],|r|r.get::<_,i64>(0)).unwrap(),1);
        assert_eq!(jobs::job_state(conn,"job").unwrap().as_deref(),Some("running"));
    }).await.unwrap();
    assert_eq!(call(&router,"POST","/api/v1/jobs/other/executions","other",r#"{"deadline_ms":5000}"#).await.0,202);
    assert_eq!(call(&router,"POST","/api/v1/jobs/third/executions","third",r#"{"deadline_ms":5000}"#).await.0,503);
    assert_eq!(call(&router,"POST","/api/v1/jobs/job/executions/stale/cancel","","").await.0,409);
    assert_eq!(call(&router,"POST","/api/v1/jobs/job/executions/same/cancel","","").await.0,202);
    assert_eq!(terminal(&router,"job").await["state"],"cancelled");
    assert_eq!(call(&router,"GET","/api/v1/jobs/job/outputs/text","","").await.0,404);
    assert_eq!(call(&router,"POST","/api/v1/jobs/job/executions","same",r#"{"deadline_ms":5000}"#).await.1["state"],"cancelled");
    assert_eq!(call(&router,"POST","/api/v1/jobs/job/executions","retry",r#"{"deadline_ms":100}"#).await.0,202);
    assert_eq!(terminal(&router,"job").await["state"],"failed");
    assert_eq!(call(&router,"POST","/api/v1/jobs/other/executions/other/cancel","","").await.0,202);
    terminal(&router,"other").await;
    for (key,body) in [("",r#"{"deadline_ms":100}"#),("valid",r#"{"deadline_ms":0}"#),("valid",r#"{"deadline_ms":10,"script":"elsewhere"}"#)] {
        let invalid=call(&router,"POST","/api/v1/jobs/third/executions",key,body).await;
        assert_eq!(invalid.0,422);assert_eq!(invalid.1["code"],"AAK-VAL-001");
    }
}

#[tokio::test]
async fn disconnected_submitter_does_not_abandon_claimed_http_operation() {
    let dir=tempfile::tempdir().unwrap();let executor=setup(dir.path(),true).await;
    let router=archeaxis_api::runtime::router(executor.clone());let client=router.clone();
    let submitted=tokio::spawn(async move{call(&client,"POST","/api/v1/jobs/job/executions","disconnected",r#"{"deadline_ms":150}"#).await});
    tokio::time::timeout(Duration::from_secs(2),async{loop{
        if executor.store().submit(|c|jobs::job_state(c,"job").unwrap()).await.unwrap().as_deref()==Some("running"){break;}
        tokio::task::yield_now().await;
    }}).await.unwrap();
    submitted.abort();
    assert_eq!(terminal(&router,"job").await["state"],"failed");
}

#[tokio::test]
async fn unrecoverable_terminal_write_is_reported_unavailable_not_reaccepted_running() {
    let dir=tempfile::tempdir().unwrap();let executor=setup(dir.path(),true).await;
    executor.store().submit(|conn|conn.execute_batch("CREATE TRIGGER reject_terminal BEFORE UPDATE OF state ON job_attempts WHEN new.state <> 'running' BEGIN SELECT RAISE(ABORT,'injected terminal write failure'); END;").unwrap()).await.unwrap();
    let router=archeaxis_api::runtime::router(executor);
    let path="/api/v1/jobs/job/executions";
    assert_eq!(call(&router,"POST",path,"disk-fault",r#"{"deadline_ms":100}"#).await.0,202);
    tokio::time::timeout(Duration::from_secs(3),async{loop{
        if call(&router,"GET","/api/v1/jobs/job","","").await.0==503{break;}
        tokio::time::sleep(Duration::from_millis(10)).await;
    }}).await.unwrap();
    assert_eq!(call(&router,"POST",path,"disk-fault",r#"{"deadline_ms":100}"#).await.0,503,"faulted execution pretended to accept replay");
    assert_eq!(call(&router,"POST","/api/v1/jobs/job/executions/disk-fault/cancel","","").await.0,503);
}

#[tokio::test]
async fn waiting_admission_does_not_block_cancellation_of_an_owned_worker() {
    use std::{future::Future,sync::mpsc,task::{Context,Waker}};
    let dir=tempfile::tempdir().unwrap();let executor=setup(dir.path(),true).await;
    let router=archeaxis_api::runtime::router(executor.clone());
    assert_eq!(call(&router,"POST","/api/v1/jobs/job/executions","owned",r#"{"deadline_ms":5000}"#).await.0,202);
    executor.store().submit(|_|()).await.unwrap();
    let (started,ready)=mpsc::channel();let (release,wait)=mpsc::channel();
    let mut blocker=Box::pin(executor.store().submit(move|_|{started.send(()).unwrap();wait.recv_timeout(Duration::from_secs(3)).unwrap();}));
    assert!(blocker.as_mut().poll(&mut Context::from_waker(Waker::noop())).is_pending());ready.recv_timeout(Duration::from_secs(1)).unwrap();
    let mut pending=Box::pin(call(&router,"POST","/api/v1/jobs/other/executions","waiting",r#"{"deadline_ms":100}"#));
    assert!(pending.as_mut().poll(&mut Context::from_waker(Waker::noop())).is_pending());
    tokio::time::sleep(Duration::from_millis(20)).await;
    let cancelled=tokio::time::timeout(Duration::from_millis(100),call(&router,"POST","/api/v1/jobs/job/executions/owned/cancel","","")).await;
    release.send(()).unwrap();blocker.await.unwrap();let _=pending.await;
    assert_eq!(cancelled.expect("admission blocked owner cancellation").0,202);
    assert_eq!(terminal(&router,"job").await["state"],"cancelled");terminal(&router,"other").await;
}
