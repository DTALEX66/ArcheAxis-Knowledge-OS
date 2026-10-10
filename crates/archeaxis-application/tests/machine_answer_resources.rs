//! Current Executor resources regression candidates, SYNTHETIC owned Python workers.
//! NOT_EXECUTED until integrated and run by the canonical project launcher.
use archeaxis_application::executor::Executor;
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

const MARKER: &str = "ARCHEAXIS_TEST_PRIVATE_GLOBAL_MARKER";
const SENTINEL: &str = "SYNTHETIC_PRIVATE_NOT_A_CREDENTIAL";
fn python() -> PathBuf {
    std::env::var_os("ARCHEAXIS_PYTHON").expect("use existing canonical declared Python").into()
}
async fn fixture(dir:&Path, body:&str) -> Executor {
    let script=dir.join("machine_resource_fixture.py");
    std::fs::write(&script,format!(
        "import os,sys,json,time\nfrom pathlib import Path\nPath(__file__).with_suffix('.pid').write_text(str(os.getpid()))\n{body}\n"
    )).unwrap();
    Executor::open_routes(&dir.join("db.sqlite"),&dir.join("staging"),&python(),
        &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/python-workers/transport/text_ndjson.py"),
        &[("machine.answer",script)]).await.unwrap()
}
fn owned_pid(dir:&Path)->u32 {
    std::fs::read_to_string(dir.join("machine_resource_fixture.pid"))
        .expect("fixture must prove actual child admission").trim().parse().unwrap()
}

#[cfg(windows)]
fn pid_running(pid:u32)->Result<bool,String> {
    use std::ffi::c_void;
    #[link(name="kernel32")]
    unsafe extern "system" {
        fn OpenProcess(access:u32,inherit:i32,pid:u32)->*mut c_void;
        fn GetExitCodeProcess(process:*mut c_void,code:*mut u32)->i32;
        fn CloseHandle(handle:*mut c_void)->i32;
        fn GetLastError()->u32;
    }
    // Query only the exact fixture PID. No termination/enumeration/ACL change.
    let handle=unsafe {OpenProcess(0x1000,0,pid)};
    if handle.is_null() {
        let error=unsafe {GetLastError()};
        return if error==87 {Ok(false)} else {Err(format!("owned PID probe unavailable ({error})"))};
    }
    let mut code=0;
    let status=unsafe {GetExitCodeProcess(handle,&mut code)};
    unsafe {CloseHandle(handle)};
    if status==0 {Err("owned PID exit state unavailable".into())} else {Ok(code==259)}
}
#[cfg(target_os="linux")]
fn pid_running(pid:u32)->Result<bool,String> {
    // Only this owned PID, no /proc enumeration. Executor already waits/reaps the child.
    match std::fs::metadata(format!("/proc/{pid}/stat")) {
        Ok(_)=>Ok(true),
        Err(error) if error.kind()==std::io::ErrorKind::NotFound=>Ok(false),
        Err(_)=>Err("owned PID probe unavailable".into()),
    }
}
#[cfg(not(any(windows,target_os="linux")))]
fn pid_running(_pid:u32)->Result<bool,String> {Err("owned PID readback unsupported on this platform; NOT_EXECUTED".into())}
fn assert_owned_child_stopped(dir:&Path) {
    let pid=owned_pid(dir);
    assert!(!pid_running(pid).expect("UNKNOWN PID status cannot qualify cleanup"),"owned worker {pid} is still running");
}

#[tokio::test]
async fn stdout_over_128k_is_rejected_and_direct_owned_child_is_reaped() {
    let dir=tempfile::tempdir().unwrap();
    let executor=fixture(dir.path(),"sys.stdout.write('x'*128001)\nsys.stdout.flush()\ntime.sleep(60)").await;
    let started=Instant::now();
    let error=executor.machine_answer("SYNTHETIC context".into(),"SYNTHETIC question".into(),128,Duration::from_secs(10)).await.unwrap_err();
    assert_eq!(error,"machine worker output exceeds bound");
    assert!(started.elapsed()<Duration::from_secs(10),"overflow must not merely time out");
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn one_second_timeout_proves_actual_owned_pid_is_no_longer_running() {
    let dir=tempfile::tempdir().unwrap();let executor=fixture(dir.path(),"time.sleep(60)").await;
    let started=Instant::now();
    let error=executor.machine_answer("SYNTHETIC context".into(),"SYNTHETIC question".into(),128,Duration::from_secs(1)).await.unwrap_err();
    assert_eq!(error,"machine worker timed out");
    assert!(started.elapsed()<Duration::from_secs(5),"one-second deadline plus cleanup must remain bounded");
    assert_owned_child_stopped(dir.path());
}

#[tokio::test]
async fn invalid_input_and_budget_are_rejected_before_worker_spawn() {
    let dir=tempfile::tempdir().unwrap();
    let executor=fixture(dir.path(),"print(json.dumps({'answer':'unexpected worker','model':'synthetic'}))").await;
    let cases=vec![
        ("x".repeat(128001),"question".to_string(),128,1),
        ("context".to_string(),"x".repeat(8193),128,1),
        ("context".to_string(),"bad\0question".to_string(),128,1),
        (" ".to_string(),"question".to_string(),128,1),
        ("context".to_string()," ".to_string(),128,1),
        ("context".to_string(),"question".to_string(),127,1),
        ("context".to_string(),"question".to_string(),4097,1),
        ("context".to_string(),"question".to_string(),128,0),
        ("context".to_string(),"question".to_string(),128,121),
    ];
    for (context,question,tokens,seconds) in cases {
        assert_eq!(executor.machine_answer(context,question,tokens,Duration::from_secs(seconds)).await.unwrap_err(),"invalid machine answer budget or input");
        assert!(!dir.path().join("machine_resource_fixture.pid").exists(),"rejected input must not run a worker");
    }
}

#[tokio::test]
async fn valid_utf8_context_and_question_round_trip_normally() {
    let dir=tempfile::tempdir().unwrap();let executor=fixture(dir.path(),concat!(
        "context=Path(sys.argv[1]).read_text(encoding='utf-8')\n",
        "question=sys.argv[sys.argv.index('--question')+1]\n",
        "tokens=int(sys.argv[sys.argv.index('--max-tokens')+1])\n",
        "assert context=='事实\\n中😀' and question=='问题😀' and tokens==128\n",
        "print(json.dumps({'answer':'中文候选😀','model':'synthetic/utf8'},ensure_ascii=False))"
    )).await;
    let result=executor.machine_answer("事实\n中😀".into(),"问题😀".into(),128,Duration::from_secs(10)).await.unwrap();
    assert_eq!(result["answer"],"中文候选😀");assert_eq!(result["model"],"synthetic/utf8");
    assert_owned_child_stopped(dir.path());
}

#[test]
fn private_parent_marker_isolated_without_mutating_global_test_environment() {
    // Rust 2024 std::env mutation would be unsafe in a parallel test process.
    // Launch only this same exact test with a synthetic marker instead.
    if std::env::var(MARKER).ok().as_deref()==Some(SENTINEL) {
        tokio::runtime::Builder::new_current_thread().enable_time().build().unwrap()
            .block_on(environment_probe_child());
        return;
    }
    let mut command=std::process::Command::new(std::env::current_exe().unwrap());
    command.args(["--exact","private_parent_marker_isolated_without_mutating_global_test_environment","--nocapture"])
        .env(MARKER,SENTINEL);
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let output=command.output().unwrap();
    assert!(output.status.success(),"isolated environment child failed: {}",String::from_utf8_lossy(&output.stderr));
    // Ensure the exact child test actually ran; an empty test filter is not evidence.
    assert!(String::from_utf8_lossy(&output.stdout).contains("ENVIRONMENT_PROBE_CHILD_EXECUTED"));
}

async fn environment_probe_child() {
    assert_eq!(std::env::var(MARKER).unwrap(),SENTINEL);
    let dir=tempfile::tempdir().unwrap();let staging=dir.path().join("staging");
    let executor=fixture(dir.path(),concat!(
        "keys=['TEMP','TMP','TMPDIR','HOME','USERPROFILE','APPDATA','LOCALAPPDATA']\n",
        "print(json.dumps({'answer':'SYNTHETIC isolated env','model':'synthetic/environment',",
        "'marker':os.environ.get('ARCHEAXIS_TEST_PRIVATE_GLOBAL_MARKER'),",
        "'cwd':os.getcwd(),'roots':{key:os.environ.get(key) for key in keys},",
        "'isolated':sys.flags.isolated,'no_user_site':sys.flags.no_user_site,",
        "'dont_write_bytecode':sys.flags.dont_write_bytecode}))"
    )).await;
    let response:Value=executor.machine_answer("SYNTHETIC env context".into(),"SYNTHETIC question".into(),128,Duration::from_secs(10)).await.unwrap();
    assert!(response["marker"].is_null(),"private synthetic parent marker must not reach worker");
    assert_eq!(response["isolated"],1);assert_eq!(response["no_user_site"],1);assert_eq!(response["dont_write_bytecode"],1);
    let cwd=response["cwd"].as_str().unwrap();
    assert_eq!(Path::new(cwd).parent(),Some(staging.as_path()),"worker must run in a direct owned staging child");
    for key in ["TEMP","TMP","TMPDIR","HOME","USERPROFILE","APPDATA","LOCALAPPDATA"] {
        assert_eq!(response["roots"][key].as_str(),Some(cwd),"{key} must point to the owned staging child");
    }
    assert_owned_child_stopped(dir.path());
    println!("ENVIRONMENT_PROBE_CHILD_EXECUTED");
}
