use archeaxis_application::{executor::{Executor,Cancellation},jobs};
use archeaxis_domain::source::{self,ImportOutcome};
use std::path::{Path,PathBuf};

fn python()->PathBuf {std::env::var_os("ARCHEAXIS_PYTHON").expect("use project dev.py launcher").into()}
fn worker()->PathBuf {PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap().join("services/python-workers/transport/text_ndjson.py")}
async fn prepare(dir:&Path,script:&Path) -> Executor {
    let executor=Executor::open(&dir.join("db.sqlite"),&dir.join("staging"),&python(),script).await.unwrap();
    executor.store().submit(|conn| {
        let source=match source::import_source(conn,"中😀\r\n".as_bytes(),"test.txt",None).unwrap() {
            ImportOutcome::Imported{source_id,..}=>source_id,_=>unreachable!()};
        jobs::enqueue(conn,"job","text",&source).unwrap();
    }).await.unwrap();
    executor
}
#[tokio::test]
async fn actual_executor_preserves_three_outputs_across_owned_store_restart() {
    let dir=tempfile::tempdir().unwrap();
    let executor=prepare(dir.path(),&worker()).await;
    executor.execute("job","run-1",5000,&Cancellation::new()).await.unwrap();
    drop(executor);
    let executor=Executor::open(&dir.path().join("db.sqlite"),&dir.path().join("staging"),&python(),&worker()).await.unwrap();
    executor.store().submit(|conn| {
        assert_eq!(jobs::job_state(conn,"job").unwrap().as_deref(),Some("succeeded"));
        assert_eq!(conn.query_row("SELECT count(*) FROM job_outputs",[],|r|r.get::<_,i64>(0)).unwrap(),3);
        assert_eq!(conn.query_row("SELECT content FROM job_outputs WHERE kind='text'",[],|r|r.get::<_,String>(0)).unwrap(),"中😀\r\n");
    }).await.unwrap();
}

#[tokio::test]
async fn accepted_worker_keeps_ownership_when_terminal_writer_queue_is_full() {
    use std::{future::Future,pin::Pin,sync::mpsc,task::{Context,Poll,Waker},time::Duration};
    fn poll_once<T>(future:Pin<&mut impl Future<Output=T>>)->Poll<T>{future.poll(&mut Context::from_waker(Waker::noop()))}
    let dir=tempfile::tempdir().unwrap();let release_worker=dir.path().join("release-worker");let worker_done=dir.path().join("worker-done");
    let script=dir.path().join("gated.py");
    std::fs::write(&script,format!("import pathlib,time,runpy\ngate=pathlib.Path({})\nwhile not gate.exists(): time.sleep(.005)\ntry: runpy.run_path({},run_name='__main__')\nfinally: pathlib.Path({}).touch()\n",
        serde_json::to_string(&release_worker).unwrap(),serde_json::to_string(&worker()).unwrap(),serde_json::to_string(&worker_done).unwrap())).unwrap();
    let executor=prepare(dir.path(),&script).await;
    let task=executor.start("job","pressure",5000,&Cancellation::new()).await.unwrap();
    // First ensure CAS read was queued before stopping the writer.
    executor.store().submit(|_|()).await.unwrap();
    let (started,ready)=mpsc::channel();let (release,wait)=mpsc::channel();
    let mut blocker=Box::pin(executor.store().submit(move|_|{started.send(()).unwrap();wait.recv_timeout(Duration::from_secs(5)).unwrap();}));
    assert!(poll_once(blocker.as_mut()).is_pending());ready.recv_timeout(Duration::from_secs(2)).unwrap();
    let mut pending=Vec::new();
    for _ in 0..64 {let mut request=Box::pin(executor.store().submit(|_|()));assert!(poll_once(request.as_mut()).is_pending());pending.push(request);}
    assert!(matches!(executor.store().submit(|_|()).await,Err(archeaxis_store_sqlite::writer::StoreError::Busy)));
    std::fs::write(&release_worker,[]).unwrap();
    tokio::time::timeout(Duration::from_secs(3),async{while !worker_done.exists(){tokio::time::sleep(Duration::from_millis(5)).await;}}).await.unwrap();
    tokio::time::sleep(Duration::from_millis(50)).await;
    release.send(()).unwrap();blocker.await.unwrap();for request in pending{request.await.unwrap();}
    assert!(task.await.unwrap().is_ok(),"accepted attempt lost ownership on transient queue pressure");
    assert_eq!(executor.store().submit(|conn|jobs::job_state(conn,"job").unwrap()).await.unwrap().as_deref(),Some("succeeded"));
}
#[tokio::test]
async fn stalled_or_cancelled_process_does_not_block_the_writer_or_commit_success() {
    let dir=tempfile::tempdir().unwrap();
    let script=dir.path().join("stalled.py");
    std::fs::write(&script,"import time\ntime.sleep(30)\n").unwrap();
    let executor=prepare(dir.path(),&script).await;
    let cancel=Cancellation::new();
    let run=executor.execute("job","timeout",150,&cancel);
    let side=async {
        tokio::time::sleep(std::time::Duration::from_millis(40)).await;
        tokio::time::timeout(std::time::Duration::from_millis(100),executor.store().submit(|conn|jobs::job_state(conn,"job").unwrap())).await.unwrap().unwrap()
    };
    let (result,state)=tokio::join!(run,side);
    assert!(result.is_err()); assert_eq!(state.as_deref(),Some("running"));
    let cancel=Cancellation::new(); cancel.cancel();
    assert!(executor.execute("job","cancel",5000,&cancel).await.is_err());
    executor.store().submit(|conn| {
        assert_eq!(jobs::job_state(conn,"job").unwrap().as_deref(),Some("cancelled"));
        assert_eq!(conn.query_row("SELECT count(*) FROM transforms",[],|r|r.get::<_,i64>(0)).unwrap(),0);
    }).await.unwrap();
}
#[tokio::test]
async fn startup_recovers_an_interrupted_attempt_before_new_work() {
    let dir=tempfile::tempdir().unwrap();
    let executor=prepare(dir.path(),&worker()).await;
    executor.store().submit(|conn|archeaxis_application::attempts::claim(conn,"job","interrupted",5000).unwrap()).await.unwrap();
    drop(executor);
    let executor=Executor::open(&dir.path().join("db.sqlite"),&dir.path().join("staging"),&python(),&worker()).await.unwrap();
    executor.execute("job","retry",5000,&Cancellation::new()).await.unwrap();
    executor.store().submit(|conn| {
        assert_eq!(conn.query_row("SELECT MAX(attempt) FROM job_attempts",[],|r|r.get::<_,i64>(0)).unwrap(),2);
        assert_eq!(conn.query_row("SELECT state FROM job_attempts WHERE attempt=1",[],|r|r.get::<_,String>(0)).unwrap(),"failed");
    }).await.unwrap();
}

#[tokio::test]
async fn corrupted_outputs_end_failed_and_rejected_results_are_not_retryable() {
    for corrupt in [true,false] {
        let dir=tempfile::tempdir().unwrap(); let script=dir.path().join("fault.py");
        let actual=serde_json::to_string(worker().to_str().unwrap()).unwrap();
        let tail=if corrupt {"m['main']()\nfrom pathlib import Path\nfor p in (Path(sys.argv[-1])/'output').iterdir(): p.write_bytes(b'bad')\n"}
            else {"def reject(*a): raise m['Rejected']('unsupported fixture')\nm['main'].__globals__['execute']=reject\nm['main']()\n"};
        std::fs::write(&script,format!("import runpy,sys\nm=runpy.run_path({actual},run_name='fixture')\n{tail}")).unwrap();
        let executor=prepare(dir.path(),&script).await;
        assert!(executor.execute("job","fault",5000,&Cancellation::new()).await.is_err());
        let expected=if corrupt{"failed"}else{"rejected"};
        executor.store().submit(move|conn|{
            assert_eq!(jobs::job_state(conn,"job").unwrap().as_deref(),Some(expected));
            assert_eq!(conn.query_row("SELECT count(*) FROM job_outputs",[],|r|r.get::<_,i64>(0)).unwrap(),0);
            if !corrupt {assert!(archeaxis_application::attempts::claim(conn,"job","forbidden-retry",5000).is_err());}
        }).await.unwrap();
    }
}

#[tokio::test]
async fn lost_caller_does_not_abandon_an_accepted_durable_job() {
    let dir=tempfile::tempdir().unwrap(); let script=dir.path().join("delayed.py");
    let actual=serde_json::to_string(worker().to_str().unwrap()).unwrap();
    std::fs::write(&script,format!("import runpy,time\ntime.sleep(0.2)\nrunpy.run_path({actual},run_name='__main__')\n")).unwrap();
    let executor=std::sync::Arc::new(prepare(dir.path(),&script).await);
    let owned=executor.clone();
    let caller=tokio::spawn(async move{owned.execute("job","lost-caller",5000,&Cancellation::new()).await});
    let deadline=std::time::Instant::now()+std::time::Duration::from_secs(3);
    loop {
        let state=executor.store().submit(|conn|jobs::job_state(conn,"job").unwrap()).await.unwrap();
        if state.as_deref()==Some("running"){break;}
        assert!(std::time::Instant::now()<deadline); tokio::task::yield_now().await;
    }
    caller.abort();
    loop {
        let state=executor.store().submit(|conn|jobs::job_state(conn,"job").unwrap()).await.unwrap();
        if state.as_deref()==Some("succeeded"){break;}
        assert!(std::time::Instant::now()<deadline,"lost caller left job {state:?}");
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }
}

#[tokio::test]
async fn nonzero_exit_extra_frames_and_stderr_flood_are_not_false_clean_success() {
    for (tail,succeeded) in [("m['main']()\nsys.exit(7)\n",false),
        ("m['main']()\nprint('{}')\n",false),
        ("print('x'*1100000)\n",false),
        ("m['main']()\nsys.stderr.write('diagnostic ' * 10000)\n",true)] {
        let dir=tempfile::tempdir().unwrap();let script=dir.path().join("wire-fault.py");
        let actual=serde_json::to_string(worker().to_str().unwrap()).unwrap();
        std::fs::write(&script,format!("import runpy,sys\nm=runpy.run_path({actual},run_name='fixture')\n{tail}")).unwrap();
        let executor=prepare(dir.path(),&script).await;
        let result=executor.execute("job","wire",5000,&Cancellation::new()).await;
        assert_eq!(result.is_ok(),succeeded,"{result:?}");
        executor.store().submit(move|conn| {
            let count=conn.query_row("SELECT count(*) FROM job_outputs",[],|r|r.get::<_,i64>(0)).unwrap();
            assert_eq!(count,if succeeded{3}else{0});
            if succeeded {
                let response:String=conn.query_row("SELECT response_json FROM job_attempts",[],|r|r.get(0)).unwrap();
                let value:serde_json::Value=serde_json::from_str(&response).unwrap();
                let warning=value["warnings"].as_array().unwrap().last().unwrap().as_str().unwrap();
                assert!(warning.contains("diagnostic"));assert!(warning.len()<8400);
            }
        }).await.unwrap();
    }
}
