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
