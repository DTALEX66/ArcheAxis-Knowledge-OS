//! Real single-shot text worker execution outside the SQLite owner thread.
//! Explicit local Core configuration, not a user-supplied executable endpoint.
use crate::attempts;
mod derived;
mod dispatch;
mod health;
mod inventory;
mod machine_failure;
use archeaxis_sidecar_protocol::worker::{
    MAX_FRAME_BYTES, Request, Response, decode_hello, decode_response,
};
use archeaxis_store_sqlite::capability_settings;
use archeaxis_store_sqlite::{raw_objects, writer::Store};
pub use machine_failure::MachineFailure;
use machine_failure::{accept_success, remaining_worker_timeout};
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

/// Core根据用途选定的有限回答策略；不得以前端任意字符串放宽材料约束。
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AnswerPolicy {
    Grounded,
    CompanionGeneral,
}
impl AnswerPolicy {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Grounded => "grounded",
            Self::CompanionGeneral => "companion_general",
        }
    }
    pub const fn prompt_version(self) -> &'static str {
        match self {
            Self::Grounded => "archeaxis.vnext/v1 2026-10-02",
            Self::CompanionGeneral => "archeaxis.companion/v1 2026-10-19",
        }
    }
}

#[derive(Clone, Default)]
pub struct Cancellation(Arc<AtomicBool>);
impl Cancellation {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn cancel(&self) {
        self.0.store(true, Ordering::Relaxed);
    }
    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Relaxed)
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
    document_check_config: Option<Arc<DocumentCheckConfig>>,
    document_check_config_error: Option<String>,
    health_slots: Arc<tokio::sync::Semaphore>,
    derived_slots: Arc<tokio::sync::Semaphore>,
}
impl Executor {
    /// Read launch policy only. No network, inventory probe or inference.
    pub fn machine_configuration(&self) -> serde_json::Value {
        let registered = self.worker_for("machine.answer").is_some();
        let explicit = std::env::var_os("ARCHEAXIS_MACHINE_ENDPOINT").is_some();
        serde_json::json!({
            "schema":"archeaxis.machine-configuration/v1",
            "worker_registered":registered,
            "selection_source":if explicit {"EXPLICIT_LAUNCH"} else {"DECLARED_LOCAL_DISCOVERY"},
            "availability":if registered {"CONFIGURED_UNVERIFIED"} else {"UNAVAILABLE"},
            "model_identity":null,
            "destination":"LOCAL_LOOPBACK_ONLY",
            "material_scope":"AUTHORIZED_KNOWLEDGE_AND_EXPLICIT_QUESTION",
            "inference_status":"NOT_EXECUTED",
            "loaded_status":"UNKNOWN",
            "usage":null,"cost":null,
            "network_performed":false,
            "evidence_scope":"LAUNCH_POLICY_ONLY"
        })
    }
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
        store
            .submit_wait(archeaxis_domain::document::recover_interrupted_checks)
            .await
            .map_err(|_| "document check recovery scheduling failed")?
            .map_err(|_| "document check recovery failed")?;
        let mut routes: Vec<(String, PathBuf, bool)> =
            vec![("text.extract".to_string(), default_worker.to_owned(), true)];
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
            document_check_config: None,
            document_check_config_error: None,
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

    async fn assert_machine_enabled(
        &self,
        deadline: Instant,
        cancel: &Cancellation,
    ) -> Result<(), MachineFailure> {
        let enabled = tokio::time::timeout(
            deadline.saturating_duration_since(Instant::now()),
            async {
                // Store繁忙时仍响应取消；丢弃的只是只读请求，不启动worker。
                tokio::select! {
                    biased;
                    _ = async {
                        while !cancel.is_cancelled() {
                            tokio::time::sleep(Duration::from_millis(20)).await;
                        }
                    } => Err(MachineFailure::from("machine worker cancelled")),
                    result = self.store.submit_wait(|conn| {
                        capability_settings::is_enabled(conn, "machine.answer")
                    }) => result
                        .map_err(|_| MachineFailure::from("machine capability settings unavailable"))?
                        .map_err(|_| MachineFailure::from("machine capability settings unavailable")),
                }
            },
        )
        .await
        .map_err(|_| "machine capability admission timed out")??;
        if !enabled {
            return Err("machine.answer capability disabled".into());
        }
        Ok(())
    }

    /// One bounded local-model call. Runtime owns the shared admission lock.
    /// Returns the worker's candidate JSON without interpreting its answer as truth.
    pub async fn machine_answer(
        &self,
        context: String,
        question: String,
        max_tokens: u64,
        timeout: Duration,
    ) -> Result<serde_json::Value, String> {
        self.machine_answer_selected(context, question, max_tokens, timeout, None)
            .await
    }

    /// Explicit choices are checked against the fixed local lane; never endpoint input.
    pub async fn machine_answer_selected(
        &self,
        context: String,
        question: String,
        max_tokens: u64,
        timeout: Duration,
        model: Option<String>,
    ) -> Result<serde_json::Value, String> {
        self.machine_answer_cancellable(
            context,
            question,
            max_tokens,
            timeout,
            model,
            Cancellation::new(),
        )
        .await
    }

    pub async fn machine_answer_cancellable(
        &self,
        context: String,
        question: String,
        max_tokens: u64,
        timeout: Duration,
        model: Option<String>,
        cancel: Cancellation,
    ) -> Result<serde_json::Value, String> {
        self.machine_answer_configured(context, question, max_tokens, timeout, model, cancel, None)
            .await
    }

    pub async fn machine_answer_configured(
        &self,
        context: String,
        question: String,
        max_tokens: u64,
        timeout: Duration,
        model: Option<String>,
        cancel: Cancellation,
        configuration: Option<archeaxis_domain::model_configuration::Resolved>,
    ) -> Result<serde_json::Value, String> {
        self.machine_answer_configured_detailed(
            context,
            question,
            max_tokens,
            timeout,
            model,
            cancel,
            configuration,
        )
        .await
        .map_err(|error| error.to_string())
    }

    pub async fn machine_answer_configured_detailed(
        &self,
        context: String,
        question: String,
        max_tokens: u64,
        timeout: Duration,
        model: Option<String>,
        cancel: Cancellation,
        configuration: Option<archeaxis_domain::model_configuration::Resolved>,
    ) -> Result<serde_json::Value, MachineFailure> {
        // 继承调用仍严格依据材料；普通陪伴必须由Core显式选择新策略。
        self.machine_answer_with_policy_detailed(
            context,
            question,
            max_tokens,
            timeout,
            model,
            cancel,
            configuration,
            AnswerPolicy::Grounded,
        )
        .await
    }

    pub async fn machine_answer_with_policy_detailed(
        &self,
        context: String,
        question: String,
        max_tokens: u64,
        timeout: Duration,
        model: Option<String>,
        cancel: Cancellation,
        configuration: Option<archeaxis_domain::model_configuration::Resolved>,
        policy: AnswerPolicy,
    ) -> Result<serde_json::Value, MachineFailure> {
        if let Some(c) = &configuration {
            if c.profile.credential_ref.is_some() {
                return Err("LOCAL_CREDENTIAL_NOT_SUPPORTED".into());
            }
            if model.as_deref() != Some(c.profile.model.as_str())
                || max_tokens > c.profile.max_tokens
                || timeout.as_secs() > c.profile.timeout_s
            {
                return Err("MODEL_PURPOSE_BUDGET_MISMATCH".into());
            }
            let pinned = c.clone();
            self.store
                .submit_wait(move |conn| {
                    archeaxis_domain::model_configuration::assert_current(conn, &pinned)
                })
                .await
                .map_err(|_| "MODEL_CONFIGURATION_UNAVAILABLE")?
                .map_err(|_| "MODEL_CONFIGURATION_CHANGED")?;
        }
        const MAX_CONTEXT: usize = 128_000;
        // Keep the existing --question argv protocol inside Windows command-line bounds.
        const MAX_QUESTION: usize = 8_192;
        const MAX_OUTPUT: usize = 128_000;
        const MAX_STDERR: usize = 8_192;
        if context.trim().is_empty()
            || question.trim().is_empty()
            || context.len() > MAX_CONTEXT
            || question.len() > MAX_QUESTION
            || question.contains('\0')
            || !(128..=4096).contains(&max_tokens)
            || timeout < Duration::from_secs(1)
            || timeout > Duration::from_secs(120)
            || model.as_ref().is_some_and(|m| {
                m.trim().is_empty()
                    || m != m.trim()
                    || m.len() > 256
                    || m.chars().any(char::is_control)
            })
        {
            return Err("invalid machine answer budget or input".into());
        }
        let started = Instant::now();
        let deadline = started + timeout;
        if cancel.is_cancelled() {
            return Err("machine worker cancelled".into());
        }
        // 模型为空只表示沿用启动配置，不能绕过能力启停；设置读失败时拒绝执行。
        self.assert_machine_enabled(deadline, &cancel).await?;
        if let Some(selected) = &model {
            let inventory = tokio::time::timeout(
                deadline.saturating_duration_since(Instant::now()),
                self.machine_inventory_configured(
                    configuration.as_ref().map(|c| c.profile.clone()),
                ),
            )
            .await
            .map_err(|_| "machine selection verification timed out")?;
            if inventory["status"] != "READ_VERIFIED"
                || !inventory["model_choices"]
                    .as_array()
                    .is_some_and(|choices| {
                        choices
                            .iter()
                            .any(|choice| choice.as_str() == Some(selected.as_str()))
                    })
            {
                return Err("machine selection is not verified in local inventory".into());
            }
            // 库存探测可能等待；期间被禁用后，不再准入新的回答worker。
            self.assert_machine_enabled(deadline, &cancel).await?;
        }
        let worker = self
            .worker_for("machine.answer")
            .map(|(path, _)| path)
            .ok_or("no worker is registered for machine.answer")?;
        let python = self.python.clone();
        let staging = self.staging.clone();
        tokio::task::spawn_blocking(move || -> Result<serde_json::Value, MachineFailure> {
            if cancel.is_cancelled() {
                return Err("machine worker cancelled".into());
            }
            if Instant::now() >= deadline {
                return Err(MachineFailure::timed_out(
                    model.as_deref(),
                    max_tokens,
                    timeout,
                    started.elapsed(),
                ));
            }
            let dir = tempfile::tempdir_in(&staging).map_err(|_| "machine staging unavailable")?;
            let context_path = dir.path().join("context.txt");
            std::fs::write(&context_path, context.as_bytes())
                .map_err(|_| "machine context staging failed")?;
            let mut command = Command::new(&python);
            // Local lane overrides are product launch policy, never HTTP input.
            // No credentials, user Python startup, proxy or home configuration inherited.
            command.env_clear();
            for key in [
                "SystemRoot",
                "WINDIR",
                "SYSTEMDRIVE",
                "ARCHEAXIS_MACHINE_ENDPOINT",
                "ARCHEAXIS_MACHINE_MODEL",
                "ARCHEAXIS_MACHINE_PROTOCOL",
            ] {
                if let Some(value) = std::env::var_os(key) {
                    command.env(key, value);
                }
            }
            if let Some(c) = &configuration {
                command.env("ARCHEAXIS_MACHINE_ENDPOINT", &c.profile.endpoint);
                command.env("ARCHEAXIS_MACHINE_MODEL", &c.profile.model);
                command.env("ARCHEAXIS_MACHINE_PROTOCOL", &c.profile.protocol);
            }
            for key in [
                "TEMP",
                "TMP",
                "TMPDIR",
                "HOME",
                "USERPROFILE",
                "APPDATA",
                "LOCALAPPDATA",
            ] {
                command.env(key, dir.path());
            }
            command.env("NO_PROXY", "127.0.0.1,localhost,::1");
            if let Some(selected) = &model {
                command
                    .arg("-I")
                    .arg("-B")
                    .arg("-X")
                    .arg("utf8")
                    .arg(&worker)
                    .arg(&context_path)
                    .arg("--model")
                    .arg(selected);
            } else {
                command
                    .arg("-I")
                    .arg("-B")
                    .arg("-X")
                    .arg("utf8")
                    .arg(&worker)
                    .arg(&context_path);
            }
            command
                .arg("--question")
                .arg(&question)
                .arg("--max-tokens")
                .arg(max_tokens.to_string())
                .arg("--answer-policy")
                .arg(policy.as_str())
                .arg("--prompt-version")
                .arg(policy.prompt_version())
                .current_dir(dir.path())
                .stdin(Stdio::null())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            // 暂存与命令准备也消耗预算；已过期就不启动新的worker。
            if cancel.is_cancelled() {
                return Err("machine worker cancelled".into());
            }
            let worker_timeout =
                remaining_worker_timeout(Instant::now(), deadline).ok_or_else(|| {
                    MachineFailure::timed_out(
                        model.as_deref(),
                        max_tokens,
                        timeout,
                        started.elapsed(),
                    )
                })?;
            command.arg("--timeout-s").arg(worker_timeout.to_string());
            let mut child = OwnedChild(command.spawn().map_err(|_| "machine worker spawn failed")?);
            let stdout = child.0.stdout.take().ok_or("machine stdout unavailable")?;
            let stderr = child.0.stderr.take().ok_or("machine stderr unavailable")?;
            // Concurrent readers avoid pipe-buffer deadlock. Each stops at limit+1;
            // overflow is reported before waiting for process exit.
            fn bounded_reader(
                stream: impl Read + Send + 'static,
                limit: usize,
                tx: mpsc::Sender<(bool, Result<Vec<u8>, &'static str>)>,
                is_stdout: bool,
            ) -> thread::JoinHandle<()> {
                thread::spawn(move || {
                    let mut bytes = Vec::new();
                    let result = stream
                        .take((limit + 1) as u64)
                        .read_to_end(&mut bytes)
                        .map_err(|_| "machine pipe read failed")
                        .and_then(|_| {
                            if bytes.len() > limit {
                                Err("machine worker output exceeds bound")
                            } else {
                                Ok(bytes)
                            }
                        });
                    let _ = tx.send((is_stdout, result));
                })
            }
            let (send, receive) = mpsc::channel();
            let reader = bounded_reader(stdout, MAX_OUTPUT, send.clone(), true);
            let err_reader = bounded_reader(stderr, MAX_STDERR, send, false);
            let result = (|| -> Result<serde_json::Value, MachineFailure> {
                let mut out = None;
                let mut errors_finished = false;
                let mut exit_status = None;
                let mut drain_deadline = None;
                loop {
                    if cancel.is_cancelled() {
                        return Err("machine worker cancelled".into());
                    }
                    if Instant::now() >= deadline {
                        return Err(MachineFailure::timed_out(
                            model.as_deref(),
                            max_tokens,
                            timeout,
                            started.elapsed(),
                        ));
                    }
                    while let Ok((is_stdout, result)) = receive.try_recv() {
                        let bytes = result?;
                        if is_stdout {
                            out = Some(bytes);
                        } else {
                            // Never echo model SDK stderr or context into API errors.
                            drop(bytes);
                            errors_finished = true;
                        }
                    }
                    if exit_status.is_none() {
                        exit_status = child
                            .0
                            .try_wait()
                            .map_err(|_| "machine status unavailable")?;
                    }
                    if let Some(status) = exit_status {
                        let drain = *drain_deadline
                            .get_or_insert_with(|| Instant::now() + Duration::from_secs(1));
                        if errors_finished && out.is_some() {
                            if !status.success() {
                                return Err(MachineFailure::from_worker(out.as_ref().unwrap()));
                            }
                            break;
                        }
                        if Instant::now() >= drain {
                            return Err("machine worker pipe drain unavailable".into());
                        }
                    }
                    if Instant::now() >= deadline {
                        return Err(MachineFailure::timed_out(
                            model.as_deref(),
                            max_tokens,
                            timeout,
                            started.elapsed(),
                        ));
                    }
                    thread::sleep(Duration::from_millis(10));
                }
                let value: serde_json::Value = serde_json::from_slice(&out.unwrap())
                    .map_err(|_| "machine worker returned invalid JSON")?;
                accept_success(
                    value,
                    model.as_deref(),
                    max_tokens,
                    started,
                    timeout,
                    Instant::now(),
                )
            })();
            // No orphaned direct child on timeout/overflow/pipe error.
            let cleanup_failed = match child.0.try_wait() {
                Ok(Some(_)) => false,
                Ok(None) | Err(_) => {
                    let killed = child.0.kill().is_ok();
                    let waited = child.0.wait().is_ok();
                    !killed || !waited
                }
            };
            // A descendant may retain an inherited pipe after our child exits.
            // Cancel only our own reader threads' blocking I/O on Windows.
            #[cfg(windows)]
            {
                use std::os::windows::io::AsRawHandle;
                #[link(name = "kernel32")]
                unsafe extern "system" {
                    fn CancelSynchronousIo(thread: *mut std::ffi::c_void) -> i32;
                }
                for task in [&reader, &err_reader] {
                    if !task.is_finished() {
                        unsafe {
                            CancelSynchronousIo(task.as_raw_handle());
                        }
                    }
                }
            }
            let cleanup_deadline = Instant::now() + Duration::from_secs(1);
            while (!reader.is_finished() || !err_reader.is_finished())
                && Instant::now() < cleanup_deadline
            {
                thread::sleep(Duration::from_millis(10));
            }
            let incomplete = !reader.is_finished() || !err_reader.is_finished();
            for task in [reader, err_reader] {
                if task.is_finished() {
                    let _ = task.join();
                }
            }
            if cleanup_failed || incomplete {
                return Err("machine worker cleanup incomplete".into());
            }
            if cancel.is_cancelled() {
                return Err("machine worker cancelled".into());
            }
            result
        })
        .await
        .map_err(|_| "machine answer task failed")?
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
        self.execute_splitting(job_id, request_id, deadline_ms, cancel, false, false)
            .await
    }
    /// `execute` for a recording that is transcribed by splitting it into bounded windows.
    pub async fn execute_splitting(
        &self,
        job_id: &str,
        request_id: &str,
        deadline_ms: u64,
        cancel: &Cancellation,
        split: bool,
        words: bool,
    ) -> Result<(), String> {
        self.start_splitting(job_id, request_id, deadline_ms, cancel, split, words)
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
        self.start_splitting(job_id, request_id, deadline_ms, cancel, false, false)
            .await
    }
    /// `start` for a split transcription. The staging directory is Core-owned and derived here, so
    /// a caller says only whether the recording should be split.
    pub async fn start_splitting(
        &self,
        job_id: &str,
        request_id: &str,
        deadline_ms: u64,
        cancel: &Cancellation,
        split: bool,
        words: bool,
    ) -> Result<tokio::task::JoinHandle<Result<(), String>>, String> {
        // Accepted jobs outlive a disconnected HTTP/UI waiter. Explicit owner
        // cancellation still propagates through the shared cancellation handle.
        let owned = self.clone();
        let job = job_id.to_owned();
        let request = request_id.to_owned();
        let cancel = cancel.clone();
        let split = split.then(|| attempts::Split {
            root: self.staging.clone(),
        });
        let (ack, accepted) = tokio::sync::oneshot::channel();
        let task = tokio::spawn(async move {
            owned
                .execute_owned(&job, &request, deadline_ms, &cancel, ack, split, words)
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
        split: Option<attempts::Split>,
        words: bool,
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
            .submit_wait(move |conn| {
                attempts::claim_split(conn, &job, &id, deadline_ms, split, words)
            })
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
                let artifact_root = if matches!(
                    req.capability.as_str(),
                    "archive.inventory" | "media.video" | "text.extract" | "office.structure",
                ) {
                    crate::container::attempt_root(&self.staging, &req.job_id, req.attempt)
                } else {
                    self.staging.clone()
                };
                let staging = self.staging.clone();
                let python = self.python.clone();
                let request = serde_json::to_string(&req).map_err(|e| e.to_string())?;
                let req_copy: Request =
                    serde_json::from_str(&request).map_err(|e| e.to_string())?;
                let cancel = cancel.clone();
                tokio::task::spawn_blocking(move || {
                    run_worker(
                        &staging,
                        &artifact_root,
                        &python,
                        &worker,
                        &req_copy,
                        &input,
                        &cancel,
                        allow_site,
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
                let artifact_root = if matches!(
                    req.capability.as_str(),
                    "archive.inventory" | "media.video" | "text.extract" | "office.structure",
                ) {
                    crate::container::attempt_root(&self.staging, &req.job_id, req.attempt)
                } else {
                    self.staging.clone()
                };
                self.store.submit_wait(move|conn|{
                    // Cancellation competes with completion at the writer boundary;
                    // once completion is committed it cannot be rolled back by cancel.
                    if cancel.0.load(Ordering::Relaxed){
                        attempts::terminate(conn,&req,"cancelled","owner cancelled before commit").map_err(|e|e.to_string())?;
                        return Err("owner cancelled before commit".into());
                    }
                    let finished = if req.capability == "media.video" { attempts::finish_with_artifacts(conn,&req,&response,&bytes,&artifact_root) } else { attempts::finish(conn,&req,&response,&bytes) };
                    match finished {
                        Ok(())=>{
                            if matches!(req.capability.as_str(), "archive.inventory" | "text.extract" | "office.structure") {
                                if let Err(error) = crate::container::expand_members(conn, &artifact_root, &req.job_id) {
                                    let reason = error.to_string();
                                    let task = archeaxis_domain::machine::MachineTask {
                                        task_id: &format!("{}-members-{}", req.job_id, req.attempt),
                                        principal: "machine",
                                        conditions: "archive inventory saved but member expansion failed",
                                        knowledge_version: None,
                                        method_version: Some("container.expand_members/v1"),
                                        tool_version: Some("core"),
                                        model_version: "not-a-model: deterministic core chaining",
                                        scope: &req.job_id,
                                        outcome: "failed",
                                        failure: Some(&reason),
                                        retest_of: None,
                                    };
                                    archeaxis_domain::machine::record_machine_task(conn, &task)
                                        .map_err(|error| format!("{reason}; expansion failure receipt unavailable: {error}"))?;
                                    return Err(format!("archive inventory saved; member expansion failed: {reason}"));
                                }
                            }
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
    "python-worker-video-ndjson",
    // F10: the diarization route's identity, so a job can reach the worker that names its own gap.
    "python-worker-diarize-ndjson",
    // F04: the content-detection route's identity.
    "python-worker-detect-ndjson",
    // G4: the machine answer route. Registered so a launch may declare it; whether a Core job route
    // drives it is a separate question, and the capability registry answers that rather than this
    // list, which only says which identities are recognised at all.
    "python-worker-machine-answer-ndjson",
];

fn worker_input_limit(capability: &str) -> usize {
    if matches!(
        capability,
        "media.transcribe" | "media.video" | "media.diarize"
    ) {
        64 * 1024 * 1024
    } else {
        16 * 1024 * 1024
    }
}

fn run_worker(
    staging: &Path,
    artifact_root: &Path,
    python: &Path,
    worker: &Path,
    req: &Request,
    input: &[u8],
    cancel: &Cancellation,
    allow_site: bool,
) -> Result<(Response, Vec<Vec<u8>>), Failure> {
    let deadline = Instant::now() + Duration::from_millis(req.deadline_ms);
    check(deadline, cancel)?;
    if input.len() > worker_input_limit(&req.capability) {
        return Err(Failure::Failed(
            "worker input exceeds capability byte budget".into(),
        ));
    }
    std::fs::create_dir_all(staging)?;
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
        command.arg("--artifact-root").arg(artifact_root);
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
        hello
            .require_runtime_dependency(&req.capability)
            .map_err(|e| Failure::Failed(e.into()))?;
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
        if req.capability == "pdf.extract" {
            let receipt = response
                .outputs
                .iter()
                .zip(&payloads)
                .find(|(output, _)| output.kind == "loss_report")
                .and_then(|(_, wire)| serde_json::from_slice::<serde_json::Value>(wire).ok())
                .ok_or_else(|| Failure::Failed("PDF_RUNTIME_RECEIPT_MISSING".into()))?;
            let dependency = hello.runtime_dependency.as_ref().unwrap();
            if receipt["engine"] != "pymupdf-native-pdf"
                || receipt["engine_version"].as_str() != dependency.version.as_deref()
                || receipt["params"]["runtime_dependency"]
                    != serde_json::to_value(dependency).unwrap()
            {
                return Err(Failure::Failed(
                    "PDF_RUNTIME_RECEIPT_IDENTITY_MISMATCH".into(),
                ));
            }
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

/// Explicit product-owned cloud policy. Never comes from an HTTP execution body.
#[derive(Clone, serde::Deserialize, serde::Serialize)]
#[serde(deny_unknown_fields)]
pub struct DocumentCheckConfig {
    pub provider: String,
    pub model: String,
    pub endpoint: Option<String>,
    pub max_tokens: u64,
    pub timeout_seconds: u64,
    pub search_limit: u64,
}
impl DocumentCheckConfig {
    pub fn validate(&self) -> Result<(), &'static str> {
        if self.provider.is_empty()
            || self.provider.len() > 64
            || !self
                .provider
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'_')
            || self.model.len() > 256
            || !self.model.starts_with(&format!("{}/", self.provider))
            || self
                .model
                .split_once('/')
                .is_none_or(|(_, name)| name.trim().is_empty())
            || !(128..=4096).contains(&self.max_tokens)
            || !(1..=120).contains(&self.timeout_seconds)
            || !(1..=3).contains(&self.search_limit)
        {
            return Err("invalid document check configuration");
        }
        if self.endpoint.as_ref().is_some_and(|endpoint| {
            !endpoint.starts_with("https://")
                || endpoint.len() > 2048
                || endpoint.contains(['@', '?', '#'])
                || endpoint.chars().any(char::is_whitespace)
        }) {
            return Err("invalid document check endpoint");
        }
        Ok(())
    }
}

impl Executor {
    pub fn with_document_check_config(
        mut self,
        config: Option<DocumentCheckConfig>,
    ) -> Result<Self, String> {
        if config
            .as_ref()
            .is_some_and(|value| value.validate().is_err())
        {
            self.document_check_config = None;
            self.document_check_config_error = Some("invalid_config".into());
            return Ok(self);
        }
        self.document_check_config = config.map(Arc::new);
        Ok(self)
    }
    pub fn with_document_check_config_error(
        mut self,
        error: Option<String>,
    ) -> Result<Self, String> {
        if error
            .as_deref()
            .is_some_and(|value| value != "invalid_config")
            || (error.is_some() && self.document_check_config.is_some())
        {
            return Err("invalid document check error contract".into());
        }
        if error.is_some() {
            self.document_check_config_error = error;
        }
        Ok(self)
    }
    pub fn document_check_config_error(&self) -> Option<String> {
        self.document_check_config_error.clone()
    }
    pub fn document_check_config(&self) -> Option<DocumentCheckConfig> {
        self.document_check_config
            .as_ref()
            .map(|v| v.as_ref().clone())
    }
    /// Reuse the launch-owned machine worker and product interpreter. All I/O is bounded.
    pub async fn document_check(
        &self,
        request: serde_json::Value,
    ) -> Result<serde_json::Value, String> {
        let config = self.document_check_config().ok_or("not_configured")?;
        config.validate().map_err(str::to_owned)?;
        if request["config"] != serde_json::to_value(&config).map_err(|_| "invalid_config")? {
            return Err("config_identity_mismatch".into());
        }
        let worker = self
            .worker_for("machine.answer")
            .map(|(path, _)| path)
            .ok_or("worker_not_configured")?;
        let python = self.python.clone();
        let mut wire_request = request.clone();
        wire_request
            .as_object_mut()
            .ok_or("invalid_request")?
            .remove("egress_sha256");
        let bytes = serde_json::to_vec(&wire_request).map_err(|_| "invalid_request")?;
        if bytes.len() > 512000 {
            return Err("input_exceeds_bound".into());
        }
        let permit = self
            .derived_slots
            .clone()
            .acquire_owned()
            .await
            .map_err(|_| "execution_unavailable")?;
        let pending_request = request.clone();
        self.store
            .submit_wait(move |conn| {
                archeaxis_domain::document::check_egress_before_worker(conn, &pending_request)
            })
            .await
            .map_err(|_| "execution_unavailable".to_owned())?
            .map_err(|error| match error {
                archeaxis_domain::document::Error::Invalid(reason)
                    if matches!(
                        reason,
                        "local_only"
                            | "egress_withdrawn"
                            | "confirmed_plan_changed"
                            | "attempt_already_terminal"
                    ) =>
                {
                    reason.to_owned()
                }
                _ => "egress_revalidation_failed".to_owned(),
            })?;
        let check_store = self.store.clone();
        let dispatch_staging = self.staging.clone();
        let runtime = tokio::runtime::Handle::current();
        tokio::task::spawn_blocking(move || {
            let _permit = permit;
            let deadline = Instant::now() + Duration::from_secs(config.timeout_seconds + 20);
            let revalidate = || -> Result<(), String> {
                let pending = request.clone();
                runtime
                    .block_on(check_store.submit_wait(move |conn| {
                        archeaxis_domain::document::check_egress_before_worker(conn, &pending)
                    }))
                    .map_err(|_| "execution_unavailable".to_owned())?
                    .map_err(|error| match error {
                        archeaxis_domain::document::Error::Invalid("egress_withdrawn") => {
                            "egress_withdrawn".to_owned()
                        }
                        _ => "egress_revalidation_failed".to_owned(),
                    })
            };
            revalidate()?;
            let dispatch_directory =
                tempfile::tempdir_in(&dispatch_staging).map_err(|_| "dispatch_unavailable")?;
            let mut dispatch_sequence = dispatch::State::default();
            let mut command = Command::new(&python);
            command
                .env(
                    "ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_DIR",
                    dispatch_directory.path(),
                )
                .env(
                    "ARCHEAXIS_DOCUMENT_CHECK_DISPATCH_HASH",
                    request["egress_sha256"]
                        .as_str()
                        .ok_or("dispatch_identity_missing")?,
                )
                .arg("-B")
                .arg(worker)
                .arg("--document-check")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            let mut child = OwnedChild(command.spawn().map_err(|_| "worker_start_failed")?);
            let mut input = child.0.stdin.take().ok_or("worker_stdin_missing")?;
            let mut output = child.0.stdout.take().ok_or("worker_stdout_missing")?;
            let mut errors = child.0.stderr.take().ok_or("worker_stderr_missing")?;
            let (send, receive) = mpsc::channel();
            let reader = thread::spawn(move || {
                let mut bytes = Vec::new();
                let result = output
                    .by_ref()
                    .take(128001)
                    .read_to_end(&mut bytes)
                    .map_err(|_| "worker_read_failed");
                let _ = send.send(result.map(|_| bytes));
            });
            // Drain without logging secret-bearing SDK stderr; no unbounded allocation.
            let err_reader = thread::spawn(move || {
                let _ = std::io::copy(&mut errors, &mut std::io::sink());
            });
            let (written_send, written_receive) = mpsc::channel();
            let ready_directory = dispatch_directory.path().to_owned();
            let ready_hash = request["egress_sha256"]
                .as_str()
                .ok_or("dispatch_identity_missing")?
                .to_owned();
            let ready_store = check_store.clone();
            let ready_runtime = runtime.clone();
            let ready_request = request.clone();
            let ready_cancelled = Arc::new(AtomicBool::new(false));
            let writer_cancelled = ready_cancelled.clone();
            let writer = thread::spawn(move || {
                let result = dispatch::wait_ready(&ready_directory, &ready_hash, &writer_cancelled)
                    .and_then(|_| {
                        if writer_cancelled.load(Ordering::Acquire) {
                            return Err("dispatch_cancelled".into());
                        }
                        ready_runtime
                            .block_on(ready_store.submit_wait(move |conn| {
                                archeaxis_domain::document::check_egress_before_worker(
                                    conn,
                                    &ready_request,
                                )
                            }))
                            .map_err(|_| "execution_unavailable".to_owned())?
                            .map_err(|_| "egress_revalidation_failed".to_owned())
                    })
                    .and_then(|_| dispatch::write_material(&mut input, &bytes, &writer_cancelled));
                drop(input);
                let _ = written_send.send(result);
            });
            let result = (|| -> Result<serde_json::Value, String> {
                loop {
                    revalidate()?;
                    dispatch::decide(
                        dispatch_directory.path(),
                        &mut dispatch_sequence,
                        &request,
                        &revalidate,
                    )?;
                    if Instant::now() >= deadline {
                        return Err("worker_timeout".into());
                    }
                    match written_receive.recv_timeout(
                        Duration::from_millis(50)
                            .min(deadline.saturating_duration_since(Instant::now())),
                    ) {
                        Ok(result) => {
                            result?;
                            break;
                        }
                        Err(mpsc::RecvTimeoutError::Timeout) => continue,
                        Err(mpsc::RecvTimeoutError::Disconnected) => {
                            return Err("worker_write_failed".into());
                        }
                    }
                }
                let bytes = loop {
                    revalidate()?;
                    dispatch::decide(
                        dispatch_directory.path(),
                        &mut dispatch_sequence,
                        &request,
                        &revalidate,
                    )?;
                    if Instant::now() >= deadline {
                        return Err("worker_timeout".into());
                    }
                    match receive.recv_timeout(
                        Duration::from_millis(50)
                            .min(deadline.saturating_duration_since(Instant::now())),
                    ) {
                        Ok(result) => break result.map_err(str::to_owned)?,
                        Err(mpsc::RecvTimeoutError::Timeout) => continue,
                        Err(mpsc::RecvTimeoutError::Disconnected) => {
                            return Err("worker_read_failed".into());
                        }
                    }
                };
                revalidate()?;
                if bytes.len() > 128000 {
                    return Err("output_exceeds_bound".into());
                }
                let value: serde_json::Value =
                    serde_json::from_slice(&bytes).map_err(|_| "invalid_worker_response")?;
                if !["succeeded", "failed"].contains(&value["outcome"].as_str().unwrap_or("")) {
                    return Err("invalid_worker_response".into());
                }
                if value["outcome"] == "succeeded" {
                    dispatch_sequence.require_success_dispatch()?;
                }
                loop {
                    revalidate()?;
                    match child.0.try_wait().map_err(|_| "worker_wait_failed")? {
                        Some(status) => {
                            if (value["outcome"] == "succeeded") != status.success() {
                                return Err("worker_exit_outcome_mismatch".into());
                            }
                            break;
                        }
                        None if Instant::now() < deadline => {
                            thread::sleep(Duration::from_millis(20))
                        }
                        _ => return Err("worker_timeout".into()),
                    }
                }
                Ok(value)
            })();
            ready_cancelled.store(true, Ordering::Release);
            if child.0.try_wait().ok().flatten().is_none() {
                let _ = child.0.kill();
                let _ = child.0.wait();
            }
            // Cancel our own blocking pipe I/O; a descendant retaining a pipe cannot
            // make cleanup join forever. No shared process or global setting is changed.
            #[cfg(windows)]
            {
                use std::os::windows::io::AsRawHandle;
                #[link(name = "kernel32")]
                unsafe extern "system" {
                    fn CancelSynchronousIo(thread: *mut std::ffi::c_void) -> i32;
                }
                for task in [&reader, &writer, &err_reader] {
                    if !task.is_finished() {
                        unsafe {
                            CancelSynchronousIo(task.as_raw_handle());
                        }
                    }
                }
            }
            let cleanup_deadline = Instant::now() + Duration::from_secs(1);
            while (!reader.is_finished() || !writer.is_finished() || !err_reader.is_finished())
                && Instant::now() < cleanup_deadline
            {
                thread::sleep(Duration::from_millis(10));
            }
            let incomplete =
                !reader.is_finished() || !writer.is_finished() || !err_reader.is_finished();
            for task in [reader, writer, err_reader] {
                if task.is_finished() {
                    let _ = task.join();
                }
            }
            if incomplete {
                return Err("worker_cleanup_incomplete".into());
            }

            result
        })
        .await
        .map_err(|_| "worker_task_failed".to_string())?
    }
}

#[cfg(test)]
mod media_input_budget_tests {
    #[test]
    fn only_execution_media_capabilities_receive_the_larger_budget() {
        assert_eq!(
            super::worker_input_limit("media.transcribe"),
            64 * 1024 * 1024
        );
        assert_eq!(super::worker_input_limit("media.video"), 64 * 1024 * 1024);
        assert_eq!(super::worker_input_limit("media.diarize"), 64 * 1024 * 1024);
        for capability in [
            "text.extract",
            "media.probe",
            "image.ocr",
            "office.structure",
            "unknown",
        ] {
            assert_eq!(super::worker_input_limit(capability), 16 * 1024 * 1024);
        }
        assert_eq!(
            archeaxis_sidecar_protocol::worker::MAX_FRAME_BYTES,
            1024 * 1024
        );
    }
}
