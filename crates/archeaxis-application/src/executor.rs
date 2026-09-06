//! Real single-shot text worker execution outside the SQLite owner thread.
//! Explicit local Core configuration, not a user-supplied executable endpoint.
use crate::attempts;
use archeaxis_sidecar_protocol::worker::{Request,Response,decode_hello,decode_response,MAX_FRAME_BYTES};
use archeaxis_store_sqlite::{writer::Store,raw_objects};
use std::{io::{Read,Write},path::{Path,PathBuf},process::{Child,Command,Stdio},
    sync::{Arc,atomic::{AtomicBool,Ordering},mpsc},thread,time::{Duration,Instant}};

#[derive(Clone,Default)]
pub struct Cancellation(Arc<AtomicBool>);
impl Cancellation {pub fn new()->Self{Self::default()} pub fn cancel(&self){self.0.store(true,Ordering::Relaxed);}}

#[derive(Clone)]
pub struct Executor {store:Store,staging:PathBuf,python:PathBuf,worker:PathBuf}
impl Executor {
    pub async fn open(db:&Path,staging:&Path,python:&Path,worker:&Path)->Result<Self,String> {
        let staging=staging_path(staging)?;
        std::fs::create_dir_all(&staging).map_err(|e|e.to_string())?;
        // Opening a new Store takes the workspace OS lock. Startup recovery
        // happens here exactly once, before this executor is returned to callers.
        let store=Store::open(db).map_err(|e|e.to_string())?;
        store.submit_wait(attempts::recover_interrupted).await.map_err(|e|e.to_string())?.map_err(|e|e.to_string())?;
        Ok(Self{store,staging,python:python.to_owned(),worker:worker.to_owned()})
    }
    pub fn store(&self)->&Store{&self.store}

    pub async fn execute(&self,job_id:&str,request_id:&str,deadline_ms:u64,cancel:&Cancellation)->Result<(),String> {
        self.start(job_id,request_id,deadline_ms,cancel).await?.await.map_err(|e|format!("execution task failed: {e}"))?
    }
    /// Returns only after durable claim; dropping the caller never abandons work.
    pub async fn start(&self,job_id:&str,request_id:&str,deadline_ms:u64,cancel:&Cancellation)->Result<tokio::task::JoinHandle<Result<(),String>>,String> {
        // Accepted jobs outlive a disconnected HTTP/UI waiter. Explicit owner
        // cancellation still propagates through the shared cancellation handle.
        let owned=self.clone();let job=job_id.to_owned();let request=request_id.to_owned();let cancel=cancel.clone();
        let (ack,accepted)=tokio::sync::oneshot::channel();
        let task=tokio::spawn(async move{owned.execute_owned(&job,&request,deadline_ms,&cancel,ack).await});
        match accepted.await {
            Ok(())=>Ok(task),
            Err(_)=>Err(task.await.map_err(|e|format!("execution task failed: {e}"))?.err().unwrap_or_else(||"claim was not acknowledged".into())),
        }
    }
    async fn execute_owned(&self,job_id:&str,request_id:&str,deadline_ms:u64,cancel:&Cancellation,ack:tokio::sync::oneshot::Sender<()>)->Result<(),String> {
        // Keep the one write to the child's pipe small enough to fit its initial
        // buffer. Configuration and IDs are Core-owned, not shell commands.
        if job_id.len()>200 || request_id.len()>200 || deadline_ms>300_000 {return Err("invalid task identity or execution budget".into());}
        let job=job_id.to_owned(); let id=request_id.to_owned();
        let req=self.store.submit_wait(move|conn|attempts::claim(conn,&job,&id,deadline_ms)).await.map_err(|e|e.to_string())?.map_err(|e|e.to_string())?;
        let _=ack.send(());
        let digest=req.inputs[0].sha256.clone();
        let input=self.store.submit_wait(move|conn|raw_objects::read(conn,&digest)).await.map_err(|e|e.to_string())?;
        let result=match input {
            Ok(input)=>{
                let staging=self.staging.clone();let python=self.python.clone();let worker=self.worker.clone();
                let request=serde_json::to_string(&req).map_err(|e|e.to_string())?;
                let req_copy:Request=serde_json::from_str(&request).map_err(|e|e.to_string())?;
                let cancel=cancel.clone();
                tokio::task::spawn_blocking(move||run_worker(&staging,&python,&worker,&req_copy,&input,&cancel)).await
                    .unwrap_or_else(|_|Err(Failure::Failed("worker execution thread failed".into())))
            }
            Err(e)=>Err(Failure::Failed(format!("source validation: {e}"))),
        };
        match result {
            Ok((response,bytes))=>{
                let cancel=cancel.clone();
                self.store.submit_wait(move|conn|{
                    // Cancellation competes with completion at the writer boundary;
                    // once completion is committed it cannot be rolled back by cancel.
                    if cancel.0.load(Ordering::Relaxed){
                        attempts::terminate(conn,&req,"cancelled","owner cancelled before commit").map_err(|e|e.to_string())?;
                        return Err("owner cancelled before commit".into());
                    }
                    match attempts::finish(conn,&req,&response,&bytes){
                        Ok(())=>Ok(()),
                        Err(error)=>{
                            let detail=error.to_string();
                            if let Err(storage)=attempts::terminate(conn,&req,"failed",&detail){
                                return Err(format!("{detail}; terminal state not recorded: {storage}"));
                            }
                            Err(detail)
                        }
                    }
                }).await.map_err(|e|e.to_string())?
            }
            Err(error)=>{
                let state=match error{Failure::Cancelled=>"cancelled",Failure::Rejected(_)=>"rejected",_=>"failed"};
                let message=error.message();let stored=message.clone();
                self.store.submit_wait(move|conn|attempts::terminate(conn,&req,state,&stored)).await.map_err(|e|e.to_string())?.map_err(|e|e.to_string())?;
                Err(message)
            }
        }
    }
}

enum Failure {Cancelled,Timeout,Failed(String),Rejected(String)}
impl Failure {
    fn message(&self)->String{match self {Self::Cancelled=>"owner cancelled worker".into(),Self::Timeout=>"worker execution deadline exceeded".into(),Self::Failed(s)|Self::Rejected(s)=>s.clone()}}
}
impl From<std::io::Error> for Failure {fn from(e:std::io::Error)->Self{Self::Failed(e.to_string())}}
fn check(deadline:Instant,cancel:&Cancellation)->Result<(),Failure>{
    if cancel.0.load(Ordering::Relaxed){Err(Failure::Cancelled)}else if Instant::now()>=deadline{Err(Failure::Timeout)}else{Ok(())}
}
struct OwnedChild(Child);
impl Drop for OwnedChild {fn drop(&mut self){let _=self.0.kill();let _=self.0.wait();}}

fn staging_path(path:&Path)->Result<PathBuf,String>{
    let text=path.to_string_lossy().replace('\\',"/").to_ascii_lowercase();
    if text.starts_with("e:") || text.starts_with("//") || !path.is_absolute()
        || path.components().any(|p|matches!(p,std::path::Component::ParentDir)) {return Err("invalid staging path".into());}
    let mut part=PathBuf::new();
    for component in path.components(){part.push(component);raw_objects::reject_links(&part).map_err(|e|e.to_string())?;}
    Ok(path.to_owned())
}

fn frame(receiver:&mpsc::Receiver<Result<String,String>>,deadline:Instant,cancel:&Cancellation)->Result<String,Failure>{
    loop {check(deadline,cancel)?;match receiver.recv_timeout(Duration::from_millis(10)){
        Ok(Ok(line))=>return Ok(line),Ok(Err(error))=>return Err(Failure::Failed(error)),
        Err(mpsc::RecvTimeoutError::Disconnected)=>return Err(Failure::Failed("worker closed stdout before response".into())),
        Err(mpsc::RecvTimeoutError::Timeout)=>(),
    }}
}
fn run_worker(staging:&Path,python:&Path,worker:&Path,req:&Request,input:&[u8],cancel:&Cancellation)->Result<(Response,Vec<Vec<u8>>),Failure>{
    let deadline=Instant::now()+Duration::from_millis(req.deadline_ms);
    check(deadline,cancel)?;
    if input.len()>16*1024*1024 {return Err(Failure::Failed("text input exceeds 16 MiB".into()));}
    let dir=tempfile::tempdir_in(staging)?;
    std::fs::create_dir(dir.path().join("input"))?;
    std::fs::write(dir.path().join("input").join(&req.inputs[0].sha256),input)?;
    let mut command=Command::new(python);
    command.arg("-B").arg("-S").arg(worker).arg("--staging-root").arg(dir.path())
        .current_dir(dir.path()).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)]{use std::os::windows::process::CommandExt;command.creation_flags(0x08000000);}
    let mut child=OwnedChild(command.spawn()?);
    let mut stdout=child.0.stdout.take().unwrap();let mut stderr=child.0.stderr.take().unwrap();
    let (send,receive)=mpsc::channel();
    let reader=thread::spawn(move||{
        let mut pending=Vec::new();let mut chunk=[0u8;1024];let mut frames=0;
        loop {match stdout.read(&mut chunk){
            Ok(0)=>{if !pending.is_empty(){let _=send.send(Err("unterminated worker frame".into()));}break;}
            Ok(n)=>for byte in &chunk[..n]{
                if *byte==b'\n'{
                    frames+=1;if frames>2 {let _=send.send(Err("excess worker frames".into()));return;}
                    let value=String::from_utf8(std::mem::take(&mut pending)).map_err(|_|"worker stdout is not UTF-8".into());
                    if send.send(value).is_err(){return;}
                }else{pending.push(*byte);if pending.len()>MAX_FRAME_BYTES{let _=send.send(Err("worker frame exceeds limit".into()));return;}}
            },
            Err(e)=>{let _=send.send(Err(e.to_string()));break;}
        }}
    });
    let (err_send,err_receive)=mpsc::channel();
    let err_reader=thread::spawn(move||{
        let mut tail=Vec::new();let mut chunk=[0u8;1024];
        while let Ok(n)=stderr.read(&mut chunk){if n==0{break;}tail.extend_from_slice(&chunk[..n]);
            if tail.len()>8192{tail.drain(..tail.len()-8192);}}
        let _=err_send.send(String::from_utf8_lossy(&tail).to_string());
    });
    let outcome=(||{
        let hello=decode_hello(&frame(&receive,deadline,cancel)?).map_err(|e|Failure::Failed(e.into()))?;
        if hello.worker.name!="python-worker-text-ndjson" || hello.worker.version!="1"{return Err(Failure::Failed("unexpected worker identity".into()));}
        let mut stdin=child.0.stdin.take().unwrap();
        writeln!(stdin,"{}",serde_json::to_string(req).map_err(|e|Failure::Failed(e.to_string()))?)?;
        drop(stdin);
        let response=decode_response(&frame(&receive,deadline,cancel)?,req).map_err(|e|Failure::Failed(e.into()))?;
        let status=loop{check(deadline,cancel)?;if let Some(status)=child.0.try_wait()?{break status;}thread::sleep(Duration::from_millis(10));};
        // A valid success frame is not enough: EOF, no extra frames and normal exit.
        loop{check(deadline,cancel)?;match receive.recv_timeout(Duration::from_millis(10)){
            Ok(_)=>return Err(Failure::Failed("unexpected trailing worker output".into())),
            Err(mpsc::RecvTimeoutError::Disconnected)=>break,Err(mpsc::RecvTimeoutError::Timeout)=>(),
        }}
        if response.status=="rejected"{return Err(Failure::Rejected(serde_json::to_string(&response).unwrap_or_else(|_|"worker rejected".into())));}
        if !status.success() || response.status!="succeeded"{return Err(Failure::Failed(serde_json::to_string(&response).unwrap_or_else(|_|"worker failed".into())));}
        let mut payloads=Vec::new();
        for output in &response.outputs{
            check(deadline,cancel)?;
            payloads.push(raw_objects::read_staged(&dir.path().join("output").join(&output.sha256),16*1024*1024)
                .map_err(|e|Failure::Failed(format!("invalid staged output: {e}")))?);
        }
        Ok((response,payloads))
    })();
    // Only this direct, stdlib-only text child is owned. Descendant process-tree
    // resource control is required before enabling OCR/media workers here.
    drop(child);
    let _=reader.join();let _=err_reader.join();
    let stderr=err_receive.try_recv().unwrap_or_default();
    match outcome {
        Ok((mut response,payloads))=>{
            if !stderr.trim().is_empty(){response.warnings.push(format!("worker stderr tail (<=8192 raw bytes; lossy UTF-8): {stderr}"));}
            Ok((response,payloads))
        }
        Err(Failure::Failed(message)) if !stderr.trim().is_empty()=>Err(Failure::Failed(format!("{message}; stderr tail: {stderr}"))),
        other=>other,
    }
}
