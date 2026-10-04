//! Real single-shot text worker execution outside the SQLite owner thread.
//! Explicit local Core configuration, not a user-supplied executable endpoint.
use crate::attempts;
mod derived;
mod health;
use archeaxis_sidecar_protocol::worker::{
    MAX_FRAME_BYTES, Request, Response, decode_hello, decode_response,
};
use archeaxis_store_sqlite::capability_settings;
use archeaxis_store_sqlite::{raw_objects, writer::Store};
use std::{
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    thread,
    time::{Duration, Instant},
};

#[derive(Clone, Default)]
pub struct Cancellation(Arc<AtomicBool>);
impl Cancellation {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn cancel(&self) {
        self.0.store(true, Ordering::Relaxed);
    }
}

/// Whether a path exists as a regular file, used to decide if a registered route can actually run.
///
/// R7/G1: a route whose worker or interpreter is missing is not a provider choice, so choosing it
/// over a usable fallback would convert a configuration mistake into a failed job.
fn file_usable(path: &Path) -> bool {
    std::fs::metadata(path)
        .map(|meta| meta.is_file())
        .unwrap_or(false)
}

#[derive(Clone)]
pub struct Executor {
    store: Store,
    staging: PathBuf,
    python: PathBuf,
    worker: PathBuf,
    /// R08: capability -> worker path and whether that route may import the
    /// interpreter's installed packages. The stdlib-only text route keeps the
    /// hardened `-S` launch; engine-backed routes (PDF/OCR) need their engine
    /// from the configured interpreter, so `-S` must not strip it.
    routes: Arc<Vec<(String, PathBuf, bool)>>,
    health_slots: Arc<tokio::sync::Semaphore>,
    derived_slots: Arc<tokio::sync::Semaphore>,
}
impl Executor {
    pub async fn open(
        db: &Path,
        staging: &Path,
        python: &Path,
        worker: &Path,
    ) -> Result<Self, String> {
        Self::open_routes(db, staging, python, worker, &[]).await
    }

    /// Open with additional capability routes. `default_worker` serves
    /// `text.extract`; each extra `(capability, worker)` entry serves one more
    /// route. A job whose capability has no registered worker fails explicitly
    /// instead of being sent to the wrong process.
    pub async fn open_routes(
        db: &Path,
        staging: &Path,
        python: &Path,
        default_worker: &Path,
        extra: &[(&str, PathBuf)],
    ) -> Result<Self, String> {
        let staging = staging_path(staging)?;
        std::fs::create_dir_all(&staging).map_err(|e| e.to_string())?;
        // Opening a new Store takes the workspace OS lock. Startup recovery
        // happens here exactly once, before this executor is returned to callers.
        let store = Store::open(db).map_err(|e| e.to_string())?;
        store
            .submit_wait(attempts::recover_interrupted)
            .await
            .map_err(|e| e.to_string())?
            .map_err(|e| e.to_string())?;
        let mut routes: Vec<(String, PathBuf, bool)> =
            vec![("text.extract".to_string(), default_worker.to_owned(), false)];
        for (capability, path) in extra {
            if capability.trim().is_empty() {
                return Err("route capability must not be empty".into());
            }
            routes.push(((*capability).to_string(), path.clone(), true));
        }
        Ok(Self {
            store,
            staging,
            python: python.to_owned(),
            worker: default_worker.to_owned(),
            routes: Arc::new(routes),
            health_slots: Arc::new(tokio::sync::Semaphore::new(4)),
            derived_slots: Arc::new(tokio::sync::Semaphore::new(4)),
        })
    }

    /// The worker registered for a capability, with its launch policy.
    ///
    /// R7/G1: when more than one route is registered for one capability, the **first usable one**
    /// answers and the later ones are fallbacks. Usable means its worker script and the interpreter
    /// both exist, because registering a route whose files are missing is a configuration mistake
    /// rather than a provider choice, and silently choosing it would turn that mistake into a failed
    /// job. When no registered route is usable the first is returned anyway, so the failure names the
    /// provider the operator declared instead of reporting that nothing was registered.
    fn worker_for(&self, capability: &str) -> Option<(PathBuf, bool)> {
        let candidates: Vec<&(String, PathBuf, bool)> = self
            .routes
            .iter()
            .filter(|(name, _, _)| name == capability)
            .collect();
        let chosen = candidates
            .iter()
            .find(|(_, path, _)| file_usable(path) && file_usable(&self.python))
            .or_else(|| candidates.first())?;
        Some((chosen.1.clone(), chosen.2))
    }

    /// Ask a local model one question about one context, through the worker boundary.
    ///
    /// G4 needs a Core route that accepts a **question**, and the job protocol cannot carry one: a
    /// route in the worker transport is validated with `parameters` empty. Rather than inventing a
    /// second model client inside the Core, this runs the machine answer worker as a process, which
    /// keeps the one boundary the project already has for every capability that calls an engine.
    ///
    /// The worker is asked for JSON on stdout, and its own words are returned rather than rephrased,
    /// so a receipt field cannot drift from what the worker actually decided.
    pub async fn machine_answer(
        &self,
        context: String,
        question: String,
        max_tokens: u64,
        timeout: Duration,
    ) -> Result<serde_json::Value, String> {
        let worker = self
            .worker_for("machine.answer")
            .map(|(path, _)| path)
            .ok_or_else(|| "no worker is registered for machine.answer".to_string())?;
        let python = self.python.clone();

        // Blocking process work belongs off the async runtime; the call can take a model's own latency.
        tokio::task::spawn_blocking(move || -> Result<serde_json::Value, String> {
            let dir = tempfile::tempdir().map_err(|e| format!("temp dir: {e}"))?;
            let context_path = dir.path().join("context.txt");
            std::fs::write(&context_path, context.as_bytes())
                .map_err(|e| format!("writing the context: {e}"))?;

            let mut command = Command::new(&python);
            command.arg("-B");
            command.arg(&worker);
            command.arg(&context_path);
            command.arg("--question").arg(&question);
            command.arg("--max-tokens").arg(max_tokens.to_string());
            command.stdout(Stdio::piped()).stderr(Stdio::piped());

            let mut child = command
                .spawn()
                .map_err(|e| format!("starting the machine answer worker: {e}"))?;
            // A model call has its own latency, so the wait is bounded by the caller's timeout rather
            // than left open; a hung worker must not hold the request forever.
            let started = std::time::Instant::now();
            loop {
                match child.try_wait() {
                    Ok(Some(_)) => break,
                    Ok(None) if started.elapsed() < timeout => {
                        std::thread::sleep(Duration::from_millis(50))
                    }
                    Ok(None) => {
                        let _ = child.kill();
                        return Err(format!(
                            "the machine answer worker exceeded {} s",
                            timeout.as_secs()
                        ));
                    }
                    Err(e) => return Err(format!("waiting for the machine answer worker: {e}")),
                }
            }
            let output = child
                .wait_with_output()
                .map_err(|e| format!("reading the machine answer worker: {e}"))?;
            let stdout = String::from_utf8_lossy(&output.stdout);
            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                return Err(format!(
                    "the machine answer worker failed: {}",
                    stderr.trim().lines().last().unwrap_or("no reason reported")
                ));
            }
            serde_json::from_str(stdout.trim())
                .map_err(|e| format!("the machine answer worker did not answer with JSON: {e}"))
        })
        .await
        .map_err(|e| format!("machine answer task failed: {e}"))?
    }

    /// The routes registered for one capability, in registration order, each marked with whether it
    /// is usable. The first element is the default; any later element is a fallback candidate.
    pub fn providers_for(&self, capability: &str) -> Vec<(&Path, bool)> {
        self.routes
            .iter()
            .filter(|(name, _, _)| name == capability)
            .map(|(_, path, _)| {
                (
                    path.as_path(),
                    file_usable(path) && file_usable(&self.python),
                )
            })
            .collect()
    }
    pub fn store(&self) -> &Store {
        &self.store
    }

    /// The interpreter the routes were opened with. A capability record reports whether the
    /// runtime it would need is present, which needs this path.
    pub fn python_path(&self) -> &Path {
        &self.python
    }

    /// Observe the existing NDJSON hello without submitting a task or selecting a
    /// replacement. Health is handshake evidence, not engine or inference success.
    pub async fn provider_health(
        &self,
        capability: &str,
        worker: &Path,
        allow_site: bool,
    ) -> serde_json::Value {
        let permit = self.health_slots.clone().acquire_owned().await;
        let permit = match permit {
            Ok(permit) => permit,
            Err(_) => {
                return serde_json::json!({"status":"handshake_failed","reason":"health probe unavailable","task_executed":false});
            }
        };
        let python = self.python.clone();
        let staging = self.staging.clone();
        let worker = worker.to_owned();
        let capability = capability.to_owned();
        tokio::task::spawn_blocking(move || {
            let _permit = permit;
            health::probe(&staging,&python,&worker,&capability,allow_site)
        }).await.unwrap_or_else(|_| serde_json::json!({
            "status":"handshake_failed","reason":"health probe task failed","task_executed":false
        }))
    }

    /// The capability this job would need **if** this workspace has disabled it, so a caller can
    /// say why the job will not start.
    ///
    /// This is a reporting aid, not the enforcement point: the refusal that actually stops a
    /// disabled capability is inside the claim transaction, which is what guarantees no attempt row
    /// is written. `None` therefore means "nothing is known to be disabled", which includes the
    /// cases where the job does not exist or its kind has no route - those are reported by the claim
    /// itself, with their own reasons.
    pub async fn disabled_capability_for(&self, job_id: &str) -> Option<String> {
        let owned = job_id.to_owned();
        let kind = self
            .store
            .submit_wait(move |conn: &mut rusqlite::Connection| {
                use rusqlite::OptionalExtension;
                conn.query_row("SELECT kind FROM jobs WHERE job_id=?1", [&owned], |row| {
                    row.get::<_, String>(0)
                })
                .optional()
            })
            .await
            .ok()?
            .ok()??;
        let capability = crate::attempts::route_for_kind(&kind)?.0.to_string();
        let named = capability.clone();
        let disabled = self
            .store
            .submit_wait(move |conn: &mut rusqlite::Connection| {
                capability_settings::is_enabled(conn, &named)
            })
            .await
            .ok()?
            .ok()?;
        (!disabled).then_some(capability)
    }

    /// The capabilities this executor will actually serve, in registration order.
    ///
    /// R7/G1: a registry has to describe what the Core registered rather than what a checkout
    /// happens to contain, and the launch is what declares routes. This exposes that set read-only
    /// so a capability surface can report it without a second source of truth. The boolean is
    /// whether the route may import the interpreter's installed packages.
    pub fn registered_routes(&self) -> Vec<(&str, &Path, bool)> {
        self.routes
            .iter()
            .map(|(capability, worker, site_packages)| {
                (capability.as_str(), worker.as_path(), *site_packages)
            })
            .collect()
    }

    pub async fn execute(
        &self,
        job_id: &str,
        request_id: &str,
        deadline_ms: u64,
        cancel: &Cancellation,
    ) -> Result<(), String> {
        self.start(job_id, request_id, deadline_ms, cancel)
            .await?
            .await
            .map_err(|e| format!("execution task failed: {e}"))?
    }
    /// Returns only after durable claim; dropping the caller never abandons work.
    pub async fn start(
        &self,
        job_id: &str,
        request_id: &str,
        deadline_ms: u64,
        cancel: &Cancellation,
    ) -> Result<tokio::task::JoinHandle<Result<(), String>>, String> {
        // Accepted jobs outlive a disconnected HTTP/UI waiter. Explicit owner
        // cancellation still propagates through the shared cancellation handle.
        let owned = self.clone();
        let job = job_id.to_owned();
        let request = request_id.to_owned();
        let cancel = cancel.clone();
        let (ack, accepted) = tokio::sync::oneshot::channel();
        let task = tokio::spawn(async move {
            owned
                .execute_owned(&job, &request, deadline_ms, &cancel, ack)
                .await
        });
        match accepted.await {
            Ok(()) => Ok(task),
            Err(_) => Err(task
                .await
                .map_err(|e| format!("execution task failed: {e}"))?
                .err()
                .unwrap_or_else(|| "claim was not acknowledged".into())),
        }
    }
    async fn execute_owned(
        &self,
        job_id: &str,
        request_id: &str,
        deadline_ms: u64,
        cancel: &Cancellation,
        ack: tokio::sync::oneshot::Sender<()>,
    ) -> Result<(), String> {
        // Keep the one write to the child's pipe small enough to fit its initial
        // buffer. Configuration and IDs are Core-owned, not shell commands.
        if job_id.len() > 200 || request_id.len() > 200 || deadline_ms > 300_000 {
            return Err("invalid task identity or execution budget".into());
        }
        let job = job_id.to_owned();
        let id = request_id.to_owned();
        let req = self
            .store
            .submit_wait(move |conn| attempts::claim(conn, &job, &id, deadline_ms))
            .await
            .map_err(|e| e.to_string())?
            .map_err(|e| e.to_string())?;
        let _ = ack.send(());
        let digest = req.inputs[0].sha256.clone();
        let input = self
            .store
            .submit_wait(move |conn| raw_objects::read(conn, &digest))
            .await
            .map_err(|e| e.to_string())?;
        let result = match input {
            Ok(input) => {
                // R08: dispatch by the capability the claimed request carries.
                let (worker, allow_site) = match self.worker_for(&req.capability) {
                    Some(route) => route,
                    None => {
                        return Err(format!(
                            "no worker registered for capability {}",
                            req.capability
                        ));
                    }
                };
                let staging = self.staging.clone();
                let python = self.python.clone();
                let request = serde_json::to_string(&req).map_err(|e| e.to_string())?;
                let req_copy: Request =
                    serde_json::from_str(&request).map_err(|e| e.to_string())?;
                let cancel = cancel.clone();
                tokio::task::spawn_blocking(move || {
                    run_worker(
                        &staging, &python, &worker, &req_copy, &input, &cancel, allow_site,
                    )
                })
                .await
                .unwrap_or_else(|_| Err(Failure::Failed("worker execution thread failed".into())))
            }
            Err(e) => Err(Failure::Failed(format!("source validation: {e}"))),
        };
        match result {
            Ok((response, bytes)) => {
                let cancel = cancel.clone();
                let artifact_root = self.staging.clone();
                self.store.submit_wait(move|conn|{
                    // Cancellation competes with completion at the writer boundary;
                    // once completion is committed it cannot be rolled back by cancel.
                    if cancel.0.load(Ordering::Relaxed){
                        attempts::terminate(conn,&req,"cancelled","owner cancelled before commit").map_err(|e|e.to_string())?;
                        return Err("owner cancelled before commit".into());
                    }
                    match attempts::finish(conn,&req,&response,&bytes){
                        Ok(())=>{
                            // R15/F06: a route that declares follow-up work gets it in the
                            // same commit, so a completed PDF job never leaves its declared
                            // pages unqueued. A chaining failure is recorded as a machine
                            // receipt with its reason instead of failing the job: the
                            // extraction and the declaration really did happen.
                            if attempts::CHAINED_AFTER_SUCCESS.contains(&req.capability.as_str()){
                                if let Err(error)=crate::ocr::enqueue_pages(conn,&artifact_root,&req.job_id){
                                    let reason=error.to_string();
                                    let task=archeaxis_domain::machine::MachineTask{
                                        task_id:&format!("{}-ocr-chain",req.job_id),
                                        principal:"machine",
                                        conditions:"automatic OCR chaining after a PDF job that declared text-less pages",
                                        knowledge_version:None,
                                        method_version:Some("ocr.enqueue_pages/v1"),
                                        tool_version:Some("pymupdf"),
                                        model_version:"not-a-model: deterministic core chaining",
                                        scope:&req.job_id,
                                        outcome:"failed",
                                        failure:Some(&reason),
                                        retest_of:None,
                                    };
                                    let _=archeaxis_domain::machine::record_machine_task(conn,&task);
                                }
                            }
                            Ok(())
                        }
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
            Err(error) => {
                let state = match error {
                    Failure::Cancelled => "cancelled",
                    Failure::Rejected(_) => "rejected",
                    _ => "failed",
                };
                let message = error.message();
                let stored = message.clone();
                self.store
                    .submit_wait(move |conn| attempts::terminate(conn, &req, state, &stored))
                    .await
                    .map_err(|e| e.to_string())?
                    .map_err(|e| e.to_string())?;
                Err(message)
            }
        }
    }
}

enum Failure {
    Cancelled,
    Timeout,
    Failed(String),
    Rejected(String),
}
impl Failure {
    fn message(&self) -> String {
        match self {
            Self::Cancelled => "owner cancelled worker".into(),
            Self::Timeout => "worker execution deadline exceeded".into(),
            Self::Failed(s) | Self::Rejected(s) => s.clone(),
        }
    }
}
impl From<std::io::Error> for Failure {
    fn from(e: std::io::Error) -> Self {
        Self::Failed(e.to_string())
    }
}
fn check(deadline: Instant, cancel: &Cancellation) -> Result<(), Failure> {
    if cancel.0.load(Ordering::Relaxed) {
        Err(Failure::Cancelled)
    } else if Instant::now() >= deadline {
        Err(Failure::Timeout)
    } else {
        Ok(())
    }
}
struct OwnedChild(Child);
impl Drop for OwnedChild {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn staging_path(path: &Path) -> Result<PathBuf, String> {
    let text = path
        .to_string_lossy()
        .replace('\\', "/")
        .to_ascii_lowercase();
    if text.starts_with("e:")
        || text.starts_with("//")
        || !path.is_absolute()
        || path
            .components()
            .any(|p| matches!(p, std::path::Component::ParentDir))
    {
        return Err("invalid staging path".into());
    }
    let mut part = PathBuf::new();
    for component in path.components() {
        part.push(component);
        raw_objects::reject_links(&part).map_err(|e| e.to_string())?;
    }
    Ok(path.to_owned())
}

fn frame(
    receiver: &mpsc::Receiver<Result<String, String>>,
    deadline: Instant,
    cancel: &Cancellation,
) -> Result<String, Failure> {
    loop {
        check(deadline, cancel)?;
        match receiver.recv_timeout(Duration::from_millis(10)) {
            Ok(Ok(line)) => return Ok(line),
            Ok(Err(error)) => return Err(Failure::Failed(error)),
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                return Err(Failure::Failed(
                    "worker closed stdout before response".into(),
                ));
            }
            Err(mpsc::RecvTimeoutError::Timeout) => (),
        }
    }
}
/// R08: the controlled set of worker identities the Core will drive. Each route
/// keeps its own identity; the shared job loop, attempt bookkeeping and error
/// vocabulary are the same for all of them.
pub const KNOWN_WORKER_IDENTITIES: &[&str] = &[
    "python-worker-text-ndjson",
    "python-worker-pdf-ndjson",
    "python-worker-ocr-ndjson",
    "python-worker-archive-ndjson",
    "python-worker-media-ndjson",
    "python-worker-office-ndjson",
    "python-worker-canvas-ndjson",
    "python-worker-subtitles-ndjson",
    "python-worker-html-ndjson",
    "python-worker-caption-ndjson",
    // the ASR route's identity; a route with no identity here is refused with
    // "unexpected worker identity" before it can serve anything
    "python-worker-transcribe-ndjson",
    // G4: the machine answer route. Registered so a launch may declare it; whether a Core job route
    // drives it is a separate question, and the capability registry answers that rather than this
    // list, which only says which identities are recognised at all.
    "python-worker-machine-answer-ndjson",
];

fn run_worker(
    staging: &Path,
    python: &Path,
    worker: &Path,
    req: &Request,
    input: &[u8],
    cancel: &Cancellation,
    allow_site: bool,
) -> Result<(Response, Vec<Vec<u8>>), Failure> {
    let deadline = Instant::now() + Duration::from_millis(req.deadline_ms);
    check(deadline, cancel)?;
    if input.len() > 16 * 1024 * 1024 {
        return Err(Failure::Failed("text input exceeds 16 MiB".into()));
    }
    let dir = tempfile::tempdir_in(staging)?;
    std::fs::create_dir(dir.path().join("input"))?;
    std::fs::write(dir.path().join("input").join(&req.inputs[0].sha256), input)?;
    let mut command = Command::new(python);
    command.arg("-B");
    if !allow_site {
        // Hardened launch for stdlib-only routes: no user site-packages.
        command.arg("-S");
    }
    command.arg(worker).arg("--staging-root").arg(dir.path());
    // R15/F06: the attempt directory is temporary, so a worker that produces durable
    // transfer files (rendered PDF pages for the OCR route) is told where to put them;
    // the Core verifies those files later by digest. Only the routes that declare it
    // receive the flag, so every other launch shape stays unchanged.
    if crate::attempts::ARTIFACT_ROOT_CAPABILITIES.contains(&req.capability.as_str()) {
        command.arg("--artifact-root").arg(staging);
    }
    command
        .current_dir(dir.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = OwnedChild(command.spawn()?);
    let mut stdout = child.0.stdout.take().unwrap();
    let mut stderr = child.0.stderr.take().unwrap();
    let (send, receive) = mpsc::channel();
    let reader = thread::spawn(move || {
        let mut pending = Vec::new();
        let mut chunk = [0u8; 1024];
        let mut frames = 0;
        loop {
            match stdout.read(&mut chunk) {
                Ok(0) => {
                    if !pending.is_empty() {
                        let _ = send.send(Err("unterminated worker frame".into()));
                    }
                    break;
                }
                Ok(n) => {
                    for byte in &chunk[..n] {
                        if *byte == b'\n' {
                            frames += 1;
                            if frames > 2 {
                                let _ = send.send(Err("excess worker frames".into()));
                                return;
                            }
                            let value = String::from_utf8(std::mem::take(&mut pending))
                                .map_err(|_| "worker stdout is not UTF-8".into());
                            if send.send(value).is_err() {
                                return;
                            }
                        } else {
                            pending.push(*byte);
                            if pending.len() > MAX_FRAME_BYTES {
                                let _ = send.send(Err("worker frame exceeds limit".into()));
                                return;
                            }
                        }
                    }
                }
                Err(e) => {
                    let _ = send.send(Err(e.to_string()));
                    break;
                }
            }
        }
    });
    let (err_send, err_receive) = mpsc::channel();
    let err_reader = thread::spawn(move || {
        let mut tail = Vec::new();
        let mut chunk = [0u8; 1024];
        while let Ok(n) = stderr.read(&mut chunk) {
            if n == 0 {
                break;
            }
            tail.extend_from_slice(&chunk[..n]);
            if tail.len() > 8192 {
                tail.drain(..tail.len() - 8192);
            }
        }
        let _ = err_send.send(String::from_utf8_lossy(&tail).to_string());
    });
    let outcome = (|| {
        let hello = decode_hello(&frame(&receive, deadline, cancel)?)
            .map_err(|e| Failure::Failed(e.into()))?;
        // R08: every extraction route reaches the Core through this same loop, so
        // the identity check accepts the controlled set of known worker
        // identities instead of pinning the text worker. Which capability a
        // worker may actually serve is enforced by the worker's own advertised
        // list (defence in depth), not by this identity gate.
        if !KNOWN_WORKER_IDENTITIES.contains(&hello.worker.name.as_str())
            || hello.worker.version != "1"
        {
            return Err(Failure::Failed("unexpected worker identity".into()));
        }
        // R08: the handshake no longer pins one capability, so the job's own
        // capability must be advertised by this worker. A route worker handed a
        // foreign capability fails here with an explicit reason.
        if !hello.capabilities.iter().any(|c| c == &req.capability) {
            return Err(Failure::Failed(format!(
                "worker does not advertise the requested capability {}",
                req.capability
            )));
        }
        let mut stdin = child.0.stdin.take().unwrap();
        writeln!(
            stdin,
            "{}",
            serde_json::to_string(req).map_err(|e| Failure::Failed(e.to_string()))?
        )?;
        drop(stdin);
        let response = decode_response(&frame(&receive, deadline, cancel)?, req)
            .map_err(|e| Failure::Failed(e.into()))?;
        let status = loop {
            check(deadline, cancel)?;
            if let Some(status) = child.0.try_wait()? {
                break status;
            }
            thread::sleep(Duration::from_millis(10));
        };
        // A valid success frame is not enough: EOF, no extra frames and normal exit.
        loop {
            check(deadline, cancel)?;
            match receive.recv_timeout(Duration::from_millis(10)) {
                Ok(_) => return Err(Failure::Failed("unexpected trailing worker output".into())),
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
                Err(mpsc::RecvTimeoutError::Timeout) => (),
            }
        }
        if response.status == "rejected" {
            return Err(Failure::Rejected(
                serde_json::to_string(&response).unwrap_or_else(|_| "worker rejected".into()),
            ));
        }
        if !status.success() || response.status != "succeeded" {
            return Err(Failure::Failed(
                serde_json::to_string(&response).unwrap_or_else(|_| "worker failed".into()),
            ));
        }
        let mut payloads = Vec::new();
        for output in &response.outputs {
            check(deadline, cancel)?;
            payloads.push(
                raw_objects::read_staged(
                    &dir.path().join("output").join(&output.sha256),
                    16 * 1024 * 1024,
                )
                .map_err(|e| Failure::Failed(format!("invalid staged output: {e}")))?,
            );
        }
        Ok((response, payloads))
    })();
    // Only this direct, stdlib-only text child is owned. Descendant process-tree
    // resource control is required before enabling OCR/media workers here.
    drop(child);
    let _ = reader.join();
    let _ = err_reader.join();
    let stderr = err_receive.try_recv().unwrap_or_default();
    match outcome {
        Ok((mut response, payloads)) => {
            if !stderr.trim().is_empty() {
                response.warnings.push(format!(
                    "worker stderr tail (<=8192 raw bytes; lossy UTF-8): {stderr}"
                ));
            }
            Ok((response, payloads))
        }
        Err(Failure::Failed(message)) if !stderr.trim().is_empty() => {
            Err(Failure::Failed(format!("{message}; stderr tail: {stderr}")))
        }
        other => other,
    }
}
