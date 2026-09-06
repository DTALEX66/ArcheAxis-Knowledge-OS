//! Real process boundaries: no unauthenticated listener and no credentials in argv.
use std::{io::{BufRead, BufReader, Read, Write}, net::TcpStream,
    process::{Child, Command, Stdio}, sync::mpsc, time::{Duration, Instant}};

const TOKEN: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const SESSION: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
struct Owned(Child);
impl Drop for Owned { fn drop(&mut self) { let _=self.0.kill(); let _=self.0.wait(); } }
fn spawn(db:&std::path::Path)->Owned {
    let mut command=Command::new(env!("CARGO_BIN_EXE_archeaxis-api"));
    command.arg(db).arg("0").stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(windows)] { use std::os::windows::process::CommandExt; command.creation_flags(0x08000000); }
    Owned(command.spawn().unwrap())
}
fn ready(child:&mut Owned)->u16 {
    let stdout=child.0.stdout.take().unwrap(); let (send,receive)=mpsc::channel();
    std::thread::spawn(move||{for line in BufReader::new(stdout).lines(){
        if send.send(line.unwrap()).is_err(){break;}
    }});
    let line=receive.recv_timeout(Duration::from_secs(8)).expect("bounded readiness");
    assert!(!line.contains(TOKEN));
    line.split("127.0.0.1:").nth(1).unwrap().split_whitespace().next().unwrap().parse().unwrap()
}
fn http(port:u16,method:&str,path:&str,headers:&str)->(u16,String) {http_body(port,method,path,headers,"")}
fn http_body(port:u16,method:&str,path:&str,headers:&str,body:&str)->(u16,String) {
    let mut socket=TcpStream::connect(("127.0.0.1",port)).unwrap();
    socket.set_read_timeout(Some(Duration::from_secs(3))).unwrap();
    write!(socket,"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\nContent-Length: {}\r\n{headers}\r\n{body}",body.len()).unwrap();
    let mut response=String::new();socket.read_to_string(&mut response).unwrap();
    assert!(!response.contains(TOKEN));
    (response.split_whitespace().nth(1).unwrap().parse().unwrap(),response.split("\r\n\r\n").nth(1).unwrap_or("").into())
}
#[test]
fn configured_process_exposes_actual_worker_execution_not_just_in_process_router() {
    let dir=tempfile::tempdir().unwrap();let db=dir.path().join("runtime.sqlite");
    let python=std::env::var("ARCHEAXIS_PYTHON").unwrap();
    let script=std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().join("services/python-workers/transport/text_ndjson.py");
    let mut child=spawn(&db);
    writeln!(child.0.stdin.take().unwrap(),"{}",serde_json::json!({"launch_token":TOKEN,"session_id":SESSION,
        "text_worker":{"python":python,"script":script,"staging":dir.path().join("staging")}})).unwrap();
    let port=ready(&mut child);
    let headers=format!("x-archeaxis-launch-token: {TOKEN}\r\nContent-Type: application/json\r\n");
    let (code,body)=http_body(port,"POST","/api/v1/imports",&headers,r#"{"name":"real.txt","content_base64":"aGVsbG8="}"#);
    assert_eq!(code,202);let source=serde_json::from_str::<serde_json::Value>(&body).unwrap()["source_id"].as_str().unwrap().to_owned();
    assert_eq!(http_body(port,"POST","/api/v1/jobs",&headers,&serde_json::json!({"job_id":"process-job","kind":"text","input_ref":source}).to_string()).0,202);
    assert_eq!(http_body(port,"POST","/api/v1/jobs/process-job/executions",&format!("{headers}idempotency-key: process-attempt\r\n"),r#"{"deadline_ms":5000}"#).0,202);
    let deadline=Instant::now()+Duration::from_secs(6);
    loop {
        let (code,body)=http(port,"GET","/api/v1/jobs/process-job",&headers);assert_eq!(code,200);
        let state=serde_json::from_str::<serde_json::Value>(&body).unwrap();
        if state["state"]=="succeeded"{break;}
        assert_eq!(state["state"],"running");assert!(Instant::now()<deadline);std::thread::sleep(Duration::from_millis(10));
    }
    let (code,body)=http(port,"GET","/api/v1/jobs/process-job/outputs/text",&headers);assert_eq!(code,200);
    assert_eq!(serde_json::from_str::<serde_json::Value>(&body).unwrap()["content"],"hello");
}
#[test]
fn process_requires_launch_auth_for_reads_writes_and_unknown_routes() {
    let dir=tempfile::tempdir().unwrap();let db=dir.path().join("core with spaces.sqlite");
    let mut child=spawn(&db);
    writeln!(child.0.stdin.take().unwrap(),"{}",serde_json::json!({"launch_token":TOKEN,"session_id":SESSION})).unwrap();
    let port=ready(&mut child);
    for (method,path) in [("GET","/api/v1/system/version"),("GET","/api/v1/workspaces/info"),("POST","/api/v1/imports"),("POST","/api/v1/jobs"),("GET","/unknown")] {
        for headers in ["", "x-archeaxis-launch-token: wrong\r\n", "x-archeaxis-scopes: owner\r\n"] {
            let (status,body)=http(port,method,path,headers);
            assert_eq!(status,401,"unprotected {method} {path}");
            assert_eq!(serde_json::from_str::<serde_json::Value>(&body).unwrap()["code"],"AAK-AUTH-001");
        }
    }
    let headers=format!("x-archeaxis-launch-token: {TOKEN}\r\n");
    let (status,body)=http(port,"GET","/api/v1/system/version",&headers);
    assert_eq!(status,200);
    let version:serde_json::Value=serde_json::from_str(&body).unwrap();
    assert_eq!(version["session_id"],SESSION);assert_eq!(version["runtime"],"archeaxis-api");
    assert_eq!(std::fs::canonicalize(version["workspace_db"].as_str().unwrap()).unwrap(),db.canonicalize().unwrap());
    assert_eq!(http(port,"GET","/api/v1/workspaces/info",&headers).0,200);
    assert_eq!(http(port,"GET","/api/v1/system/version",&format!("{headers}Origin: https://example.invalid\r\n")).0,403);
    assert_eq!(http(port,"GET","/api/v1/system/version",&format!("{headers}{headers}")).0,401);
    drop(child);
    let next_token="c".repeat(64);
    let mut restarted=spawn(&db);
    writeln!(restarted.0.stdin.take().unwrap(),"{}",serde_json::json!({"launch_token":next_token,"session_id":"d".repeat(32)})).unwrap();
    let next_port=ready(&mut restarted);
    assert_eq!(http(next_port,"GET","/api/v1/system/version",&headers).0,401,"old credential survived restart");
    assert_eq!(http(next_port,"GET","/api/v1/system/version",&format!("x-archeaxis-launch-token: {next_token}\r\n")).0,200);
}
#[test]
fn invalid_or_unclosed_bootstrap_never_creates_workspace_and_exits_bounded() {
    for bootstrap in [Some(""),Some("{}"),Some("not json"),Some("oversize"),None] {
        let dir=tempfile::tempdir().unwrap();let db=dir.path().join("not-created.sqlite");let mut child=spawn(&db);
        if let Some(value)=bootstrap {
            let mut pipe=child.0.stdin.take().unwrap();
            if value=="oversize" {let _=pipe.write_all(&vec![b'x';5000]);} else {let _=pipe.write_all(value.as_bytes());}
        }
        let deadline=Instant::now()+Duration::from_secs(7);
        let status=loop {if let Some(status)=child.0.try_wait().unwrap(){break status;}
            assert!(Instant::now()<deadline,"invalid bootstrap left process running");std::thread::sleep(Duration::from_millis(10));};
        assert!(!status.success());assert!(!db.exists());
    }
}
