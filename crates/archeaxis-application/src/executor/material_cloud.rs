//! Material-only cloud bridge. Secrets stay inside the owned worker.
use super::*;
impl Executor {
    pub async fn material_cloud_answer(
        &self,
        context: String,
        plan: serde_json::Value,
        cancel: Cancellation,
    ) -> Result<serde_json::Value, MachineFailure> {
        let request = &plan["request"];
        let configuration: archeaxis_domain::model_configuration::Resolved =
            serde_json::from_value(request["model_configuration"].clone())
                .map_err(|_| "MATERIAL_CLOUD_INVALID_PLAN")?;
        if configuration.purpose != archeaxis_domain::model_configuration::Purpose::Material
            || configuration.profile.protocol != "openai-buffered"
            || request["cloud_upload_confirmed"] != true
            || request["cloud_unknown_cost_confirmed"] != true
            || plan["destination"] != "PUBLIC_HTTPS"
        {
            return Err("MATERIAL_CLOUD_CONSENT_REQUIRED".into());
        }
        let pinned = configuration.clone();
        let frozen = plan.clone();
        self.store
            .submit_wait(move |conn| -> Result<(), String> {
                archeaxis_domain::model_configuration::assert_current(conn, &pinned)
                    .map_err(|_| "MODEL_CONFIGURATION_CHANGED")?;
                let request_id = frozen["request"]["request_id"]
                    .as_str()
                    .ok_or("material_request_invalid")?;
                let key = format!(
                    "material_request_material_answer_{}",
                    archeaxis_domain::material_question::hash(request_id.as_bytes())
                );
                let journal: String = conn
                    .query_row(
                        "SELECT value FROM workspace_meta WHERE key=?1",
                        [key],
                        |r| r.get(0),
                    )
                    .map_err(|_| "material_cloud_not_admitted")?;
                if serde_json::from_str::<serde_json::Value>(&journal)
                    .map_err(|_| "material_cloud_journal_invalid")?
                    != frozen
                {
                    return Err("material_cloud_journal_changed".into());
                }

                let material = serde_json::from_value(frozen["request"]["material"].clone())
                    .map_err(|_| "material_invalid")?;
                let selection: Option<archeaxis_domain::material_question::Selection> =
                    serde_json::from_value(frozen["request"]["selection"].clone())
                        .map_err(|_| "material_invalid")?;
                let (_, proof) = archeaxis_domain::material_question::prepare(
                    conn,
                    &material,
                    selection.as_ref(),
                )?;
                if proof != frozen["context"]
                    || archeaxis_domain::ui_state::machine_execution_epoch(conn)
                        .map_err(|_| "material_epoch_unavailable")?
                        != frozen["restore_epoch"]
                {
                    return Err("material_cloud_fence_changed".into());
                }
                Ok(())
            })
            .await
            .map_err(|_| "material_cloud_fence_unavailable")??;
        let model = Some(configuration.profile.model.clone());
        let max_tokens = request["max_tokens"]
            .as_u64()
            .ok_or("material_cloud_budget_invalid")?;
        let timeout = Duration::from_secs(
            request["timeout_s"]
                .as_u64()
                .filter(|v| (1..=60).contains(v))
                .ok_or("material_cloud_budget_invalid")?,
        );
        let started = Instant::now();
        let deadline = started + timeout;
        self.assert_machine_enabled(deadline, &cancel).await?;
        let frame = serde_json::to_vec(&serde_json::json!({"plan":plan,"context":context}))
            .map_err(|_| "material_cloud_frame_invalid")?;
        if frame.len() > 200000 {
            return Err("material_cloud_frame_limit".into());
        }
        let worker = self
            .worker_for("machine.answer")
            .ok_or("no worker is registered for machine.answer")?
            .0
            .with_file_name("material_cloud_worker.py");
        let python = self.python.clone();
        let staging = self.staging.clone();
        const MAX_OUTPUT: usize = 128000;
        const MAX_STDERR: usize = 8192;
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
            let mut command = Command::new(&python);
            // Local lane overrides are product launch policy, never HTTP input.
            // No credentials, user Python startup, proxy or home configuration inherited.
            command.env_clear();
            for key in ["SystemRoot", "WINDIR", "SYSTEMDRIVE"] {
                if let Some(value) = std::env::var_os(key) {
                    command.env(key, value);
                }
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
            command
                .arg("-I")
                .arg("-B")
                .arg("-X")
                .arg("utf8")
                .arg(&worker)
                .current_dir(dir.path())
                .stdin(Stdio::piped())
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
            let _ = worker_timeout;
            let mut child = OwnedChild(command.spawn().map_err(|_| "machine worker spawn failed")?);
            let mut stdin = child.0.stdin.take().ok_or("cloud stdin unavailable")?;
            let input_writer = thread::spawn(move || {
                let _ = stdin.write_all(&frame);
            });
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
                for task in [&reader, &err_reader, &input_writer] {
                    if !task.is_finished() {
                        unsafe {
                            CancelSynchronousIo(task.as_raw_handle());
                        }
                    }
                }
            }
            let cleanup_deadline = Instant::now() + Duration::from_secs(1);
            while (!reader.is_finished()
                || !err_reader.is_finished()
                || !input_writer.is_finished())
                && Instant::now() < cleanup_deadline
            {
                thread::sleep(Duration::from_millis(10));
            }
            let incomplete =
                !reader.is_finished() || !err_reader.is_finished() || !input_writer.is_finished();
            for task in [reader, err_reader, input_writer] {
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
}
