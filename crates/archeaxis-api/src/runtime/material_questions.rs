//! Material questions are independent of accepted-knowledge qualification.
use super::*;
use archeaxis_domain::material_question::{self as material, Material, Selection};
#[derive(Clone, Deserialize, serde::Serialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Body {
    request_id: String,
    material: Material,
    selection: Option<Selection>,
    question: String,
    purpose: String,
    model: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    model_configuration: Option<archeaxis_domain::model_configuration::Resolved>,
    #[serde(
        default,
        deserialize_with = "read_execution_mode",
        skip_serializing_if = "Option::is_none"
    )]
    execution_mode: Option<ExecutionMode>,
    #[serde(default, skip_serializing_if = "is_false")]
    cloud_upload_confirmed: bool,
    #[serde(default, skip_serializing_if = "is_false")]
    cloud_unknown_cost_confirmed: bool,
    max_tokens: u64,
    timeout_s: u64,
    #[serde(default)]
    preview: bool,
    confirmed_plan_sha256: Option<String>,
}
fn is_false(value: &bool) -> bool {
    !*value
}
#[derive(Clone, Copy, PartialEq, Deserialize, serde::Serialize)]
#[serde(rename_all = "snake_case")]
pub(super) enum ExecutionMode {
    Async,
}
fn read_execution_mode<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> Result<Option<ExecutionMode>, D::Error> {
    ExecutionMode::deserialize(deserializer).map(Some)
}
fn admission_ack(plan: &Value, plan_sha: &str) -> Response {
    (StatusCode::ACCEPTED, Json(json!({"schema":"archeaxis.material-question-admission/v1",
        "request_id":plan["request"]["request_id"],"task_id":key(plan["request"]["request_id"].as_str().unwrap()),
        "plan_sha256":plan_sha,"workspace_id":plan["workspace_id"],"restore_epoch":plan["restore_epoch"],"admission_state":"ACCEPTED",
        "execution_state":"RUNNING","answer_published":false,"provider_stop_state":"UNKNOWN"}))).into_response()
}
pub(super) async fn submit(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Body>,
) -> Response {
    if body.preview || body.execution_mode != Some(ExecutionMode::Async) {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "confirmed_async_material_request_required",
        );
    }
    question_inner(runtime, headers, body, true).await
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct ContextBody {
    material: Material,
    selection: Option<Selection>,
}
pub(super) async fn context(
    State(runtime): State<Runtime>,
    Json(body): Json<ContextBody>,
) -> Response {
    match runtime.executor.store().submit_wait(move |conn|material::prepare(conn,&body.material,body.selection.as_ref())).await {
        Ok(Ok((text,proof)))=>Json(json!({"schema":"archeaxis.material-context/v1","text":text,"proof":proof,"network_performed":false})).into_response(),
        Ok(Err(reason))=>failure(StatusCode::UNPROCESSABLE_ENTITY,&reason),
        _=>failure(StatusCode::SERVICE_UNAVAILABLE,"material_read_unavailable"),
    }
}
fn failure(status: StatusCode, reason: &str) -> Response {
    (
        status,
        Json(json!({"reason_code":reason,"answer_published":false})),
    )
        .into_response()
}
fn key(id: &str) -> String {
    format!("material_answer_{}", material::hash(id.as_bytes()))
}
fn identity(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 128
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"_-".contains(&b))
}
fn model_failure(error: &str) -> &'static str {
    match error {
        "no worker is registered for machine.answer" => "material_model_not_configured",
        "machine selection is not verified in local inventory" => "material_model_not_in_inventory",
        "machine worker timed out" | "machine failure: MODEL_CALL_TIMEOUT" => {
            "material_model_timeout"
        }
        "machine failure: MODEL_CALL_FAILED" => "material_model_call_failed",
        "machine failure: NO_FINAL_ANSWER" => "material_no_final_answer",
        "machine worker returned invalid JSON" => "material_model_invalid_response",
        _ => "material_model_unavailable_or_failed",
    }
}
pub(super) async fn question(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Body>,
) -> Response {
    if !body.preview && body.execution_mode.is_some() {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "use_material_async_submission",
        );
    }
    question_inner(runtime, headers, body, false).await
}
async fn question_inner(
    runtime: Runtime,
    headers: HeaderMap,
    mut body: Body,
    asynchronous: bool,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    if !identity(&body.request_id)
        || body.question.trim().is_empty()
        || body.question.contains('\0')
        || body.question.len() > 8192
        || body.purpose.trim().is_empty()
        || body.purpose.len() > 1024
        || !(128..=4096).contains(&body.max_tokens)
        || !(1..=120).contains(&body.timeout_s)
    {
        return failure(StatusCode::UNPROCESSABLE_ENTITY, "material_question_bounds");
    }
    if body.model.as_ref().is_some_and(|m| {
        m.is_empty() || m.len() > 256 || m.trim() != m || m.chars().any(char::is_control)
    }) {
        return failure(StatusCode::UNPROCESSABLE_ENTITY, "invalid_model_selection");
    }
    let preview = body.preview;
    let confirmed = body.confirmed_plan_sha256.take();
    body.preview = false;
    let id = key(&body.request_id);
    if asynchronous {
        // A terminal replay is a historical read. Never rebuild its context or
        // resolve today's profile/restore scope as if this were new permission.
        let query = id.clone();
        let request = serde_json::to_value(&body).unwrap();
        let confirmation = confirmed.clone();
        let previous = runtime
            .executor
            .store()
            .submit_wait(
                move |conn| -> Result<Option<(Value, Option<Value>, bool)>, String> {
                    let terminal = archeaxis_domain::machine::machine_task(conn, &query)
                        .map_err(|_| "material_receipt_unavailable")?
                        .map(|task| {
                            serde_json::from_str::<Value>(&task.conditions)
                                .map_err(|_| "material_receipt_invalid")
                        })
                        .transpose()?;
                    let journal: Option<String> = conn
                        .query_row(
                            "SELECT value FROM workspace_meta WHERE key=?1",
                            [format!("material_request_{query}")],
                            |r| r.get(0),
                        )
                        .optional()
                        .map_err(|_| "material_journal_unavailable")?;
                    let journal = journal
                        .map(|raw| {
                            serde_json::from_str::<Value>(&raw)
                                .map_err(|_| "material_journal_invalid")
                        })
                        .transpose()?;
                    let plan = match (&terminal, &journal) {
                        (Some(receipt), journal) => {
                            if receipt["schema"] != "archeaxis.material-answer/v1"
                                || receipt["task_id"] != query
                                || receipt["request_id"] != request["request_id"]
                                || !matches!(
                                    receipt["outcome"].as_str(),
                                    Some("succeeded" | "failed")
                                )
                                || journal
                                    .as_ref()
                                    .is_some_and(|stored| stored != &receipt["plan"])
                            {
                                return Err("material_receipt_invalid".into());
                            }
                            receipt["plan"].clone()
                        }
                        (None, Some(plan)) => plan.clone(),
                        (None, None) => return Ok(None),
                    };
                    if plan["schema"] != "archeaxis.material-question-plan/v1"
                        || plan["request"] != request
                    {
                        return Err("material_request_id_conflict".into());
                    }
                    let digest = material::hash(plan.to_string().as_bytes());
                    if terminal
                        .as_ref()
                        .is_some_and(|receipt| receipt["plan_sha256"] != digest)
                    {
                        return Err("material_receipt_invalid".into());
                    }
                    if confirmation.as_deref() != Some(digest.as_str()) {
                        return Err("material_plan_confirmation_required".into());
                    }
                    let current = if terminal.is_some() {
                        true
                    } else {
                        let workspace = archeaxis_domain::ui_state::existing_workspace_id(conn)
                            .map_err(|_| "material_workspace_unavailable")?;
                        let epoch = archeaxis_domain::ui_state::machine_execution_epoch(conn)
                            .map_err(|_| "material_epoch_unavailable")?;
                        workspace.as_deref() == plan["workspace_id"].as_str()
                            && plan["restore_epoch"] == epoch
                    };
                    Ok(Some((plan, terminal, current)))
                },
            )
            .await;
        match previous {
            Ok(Ok(Some((_, Some(receipt), _)))) => return Json(receipt).into_response(),
            Ok(Ok(Some((plan, None, current)))) => {
                let owned = current
                    && runtime.machine_active.lock().ok().is_some_and(|entries| {
                        entries
                            .get(&id)
                            .is_some_and(|entry| plan["restore_epoch"] == entry.restore_epoch)
                    });
                return if owned {
                    let digest = material::hash(plan.to_string().as_bytes());
                    admission_ack(&plan, &digest)
                } else {
                    failure(
                        StatusCode::CONFLICT,
                        "material_execution_unknown_retain_request",
                    )
                };
            }
            Ok(Ok(None)) => (),
            Ok(Err(reason)) => {
                return failure(
                    if reason == "material_plan_confirmation_required" {
                        StatusCode::FORBIDDEN
                    } else {
                        StatusCode::CONFLICT
                    },
                    &reason,
                );
            }
            _ => {
                return failure(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "material_status_unavailable",
                );
            }
        }
    }
    let b = body.clone();
    let prepared=runtime.executor.store().submit_wait(move |conn|{

        let configured=archeaxis_domain::model_configuration::read(conn).map_err(|_|"MODEL_CONFIGURATION_UNAVAILABLE")?;
        if configured.revision>0 || b.model_configuration.is_some() {
            let config=b.model_configuration.as_ref().ok_or("MODEL_PURPOSE_BINDING_REQUIRED")?;
            archeaxis_domain::model_configuration::assert_current(conn,config).map_err(|_|"MODEL_CONFIGURATION_CHANGED")?;
            if config.purpose!=archeaxis_domain::model_configuration::Purpose::Material || b.model.as_deref()!=Some(config.profile.model.as_str()) || b.max_tokens>config.profile.max_tokens || b.timeout_s>config.profile.timeout_s {return Err("MODEL_PURPOSE_SELECTION_MISMATCH".into())}
        }
        let (text,proof)=material::prepare(conn,&b.material,b.selection.as_ref())?;
        let epoch=archeaxis_domain::ui_state::machine_execution_epoch(conn).map_err(|_|"material_epoch_unavailable")?;
        let plan=json!({"schema":"archeaxis.material-question-plan/v1","request":b,"context":proof,"destination":"LOCAL_LOOPBACK_ONLY","destination_candidates":["http://127.0.0.1:1234/v1"],"selection_policy":"existing_owned_local_worker_probe","network_scope":"fixed_owned_local_worker","restore_epoch":epoch,"usage":null,"cost":null});
        let mut plan=plan;
        if b.execution_mode==Some(ExecutionMode::Async) {
            plan["workspace_id"]=json!(archeaxis_domain::ui_state::workspace_id(conn).map_err(|_|"material_workspace_unavailable")?);
        }
        if let Some(config)=&b.model_configuration {
            plan["destination_candidates"]=json!([config.profile.endpoint]);
            plan["selection_policy"]=json!("frozen_material_purpose_profile");
            plan["network_scope"]=json!("configured_numeric_loopback_endpoint");
            if config.profile.protocol == "openai-buffered" {
                if b.execution_mode != Some(ExecutionMode::Async) { return Err("material_cloud_requires_async".into()); }
                if !b.cloud_upload_confirmed || !b.cloud_unknown_cost_confirmed { return Err("material_cloud_upload_and_unknown_cost_consent_required".into()); }
                plan["destination"]=json!("PUBLIC_HTTPS");
                plan["network_scope"]=json!("single_confirmed_material_upload");
                plan["cost_status"]=json!("UNKNOWN_EXPLICITLY_ACCEPTED");
            }
        }
        Ok::<_,String>((text,plan))
    }).await;
    let (text, plan) = match prepared {
        Ok(Ok(v)) => v,
        Ok(Err(reason)) => return failure(StatusCode::UNPROCESSABLE_ENTITY, &reason),
        _ => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "material_prepare_unavailable",
            );
        }
    };
    let plan_sha = material::hash(plan.to_string().as_bytes());
    if preview {
        return Json(json!({"schema":"archeaxis.material-question-preview/v1","plan":plan,"plan_sha256":plan_sha})).into_response();
    }
    if confirmed.as_deref() != Some(&plan_sha) {
        return failure(StatusCode::FORBIDDEN, "material_plan_confirmation_required");
    }
    // Exactly one owned model operation; async never waits in an unbounded task queue.
    let guard = if asynchronous {
        match runtime.colearning_admission.clone().try_lock_owned() {
            Ok(guard) => guard,
            Err(_) => {
                return failure(
                    StatusCode::TOO_MANY_REQUESTS,
                    "material_async_capacity_exhausted_not_admitted",
                );
            }
        }
    } else {
        runtime.colearning_admission.clone().lock_owned().await
    };
    let stored_id = id.clone();
    let stored_plan = plan.clone();
    let read_body = body.clone();
    let admission=runtime.executor.store().submit_wait(move |conn|->Result<Option<Value>,String>{
        if let Some(config)=&read_body.model_configuration {archeaxis_domain::model_configuration::assert_current(conn,config).map_err(|_|"MODEL_CONFIGURATION_CHANGED")?;}
        let (_,now)=material::prepare(conn,&read_body.material,read_body.selection.as_ref())?;
        if now!=stored_plan["context"]{return Err("material_changed_before_execution".into())}
        let epoch=archeaxis_domain::ui_state::machine_execution_epoch(conn).map_err(|_|"material_epoch_unavailable")?;
        if stored_plan["restore_epoch"]!=epoch{return Err("material_restore_changed".into())}
        if let Some(task)=archeaxis_domain::machine::machine_task(conn,&stored_id).map_err(|_|"material_receipt_unavailable")?{
            let receipt:Value=serde_json::from_str(&task.conditions).map_err(|_|"material_receipt_invalid")?;
            if receipt["plan"]!=stored_plan{return Err("material_request_id_conflict".into())}return Ok(Some(receipt))
        }
        let tx=conn.savepoint().map_err(|_|"material_journal_unavailable")?;
        super::execution_claim::admit(&tx,&stored_id,&stored_plan).map_err(|_|"material_execution_unknown_or_conflicting")?;
        tx.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value",rusqlite::params![format!("material_request_{stored_id}"),stored_plan.to_string()]).map_err(|_|"material_journal_unavailable")?;
        tx.commit().map_err(|_|"material_journal_unavailable")?;Ok(None)
    }).await;
    match admission {
        Ok(Ok(Some(receipt))) => return Json(receipt).into_response(),
        Ok(Ok(None)) => (),
        Ok(Err(r)) => return failure(StatusCode::CONFLICT, &r),
        _ => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "material_admission_unavailable",
            );
        }
    }
    let lease = match colearning::machine_lease(&runtime, &id, &id).await {
        Ok(l) => l,
        Err(r) => return r,
    };
    if asynchronous {
        let ack = admission_ack(&plan, &plan_sha);
        // From this point the Core task owns admission, cancellation and postchecks.
        // Dropping the submitting HTTP/UI waiter cannot drop the lease.
        tokio::spawn(async move {
            let _ = execute_owned(runtime, body, text, plan, plan_sha, id, lease, guard).await;
        });
        return ack;
    }
    execute_owned(runtime, body, text, plan, plan_sha, id, lease, guard).await
}
#[allow(clippy::too_many_arguments)]
async fn execute_owned(
    runtime: Runtime,
    body: Body,
    text: String,
    plan: Value,
    plan_sha: String,
    id: String,
    lease: super::MachineLease,
    _guard: tokio::sync::OwnedMutexGuard<()>,
) -> Response {
    let execution = if body
        .model_configuration
        .as_ref()
        .is_some_and(|c| c.profile.protocol == "openai-buffered")
    {
        runtime
            .executor
            .material_cloud_answer(text, plan.clone(), lease.cancel.clone())
            .await
    } else {
        runtime
            .executor
            .machine_answer_configured_detailed(
                text,
                body.question.clone(),
                body.max_tokens,
                std::time::Duration::from_secs(body.timeout_s),
                body.model.clone(),
                lease.cancel.clone(),
                body.model_configuration.clone(),
            )
            .await
    };
    if execution.as_ref().err().is_some_and(|e| {
        e.message().contains("cleanup incomplete") || e.message().contains("cleanup_incomplete")
    }) {
        return failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "material_execution_unknown_retain_request",
        );
    }
    // Withdrawal must either cancel this live lease or follow its durable
    // publication; re-enabling cannot revive a withdrawn token in between.
    let _publication = runtime.admission.lock().await;
    let cancelled = lease.close().unwrap_or(true);
    let diagnostics = if cancelled {
        None
    } else {
        execution
            .as_ref()
            .err()
            .and_then(|e| e.diagnostics())
            .cloned()
    };
    let (answer, outcome, reason) = match execution {
        Ok(a)
            if !cancelled
                && a["endpoint"].as_str().is_some_and(|e| {
                    if let Some(config) = &body.model_configuration {
                        e == config.profile.endpoint
                            && a["model"].as_str() == Some(config.profile.model.as_str())
                            && a["protocol"].as_str() == Some(config.profile.protocol.as_str())
                    } else {
                        e == "http://127.0.0.1:1234/v1"
                    }
                }) =>
        {
            (a, "succeeded", None)
        }
        _ if cancelled => (Value::Null, "failed", Some("material_question_cancelled")),
        Err(e) => (Value::Null, "failed", Some(model_failure(e.message()))),
        _ => (
            Value::Null,
            "failed",
            Some("material_destination_unverified"),
        ),
    };
    let mut receipt = json!({"schema":"archeaxis.material-answer/v1","task_id":id,"request_id":body.request_id,"plan":plan,"plan_sha256":plan_sha,"outcome":outcome,"reason_code":reason,"answer":answer,"answer_sha256":answer["answer"].as_str().map(|s|material::hash(s.as_bytes())),"authority":"candidate","grants_knowledge_acceptance":false,"provider_stop_state":if cancelled{"UNKNOWN"}else{"NOT_REQUESTED"}});
    if let Some(diagnostics) = diagnostics {
        receipt["diagnostics"] = diagnostics;
    }
    let saved = runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            if outcome == "succeeded"
                && !archeaxis_store_sqlite::capability_settings::is_enabled(conn, "machine.answer")?
            {
                return Err(rusqlite::Error::InvalidParameterName(
                    "machine_answer_disabled_before_publication".into(),
                ));
            }
            if let Some(config) = &body.model_configuration {
                archeaxis_domain::model_configuration::assert_current(conn, config)?;
            }
            if body.execution_mode == Some(ExecutionMode::Async)
                && receipt["plan"]["workspace_id"]
                    != archeaxis_domain::ui_state::workspace_id(conn).map_err(|_| {
                        rusqlite::Error::InvalidParameterName(
                            "material_workspace_unavailable".into(),
                        )
                    })?
            {
                return Err(rusqlite::Error::InvalidParameterName(
                    "material_workspace_changed".into(),
                ));
            }
            let (_, now) = material::prepare(conn, &body.material, body.selection.as_ref())
                .map_err(|_| {
                    rusqlite::Error::InvalidParameterName("material_postcheck_failed".into())
                })?;
            if now != receipt["plan"]["context"] {
                return Err(rusqlite::Error::InvalidParameterName(
                    "material_postcheck_changed".into(),
                ));
            }
            let epoch =
                archeaxis_domain::ui_state::machine_execution_epoch(conn).map_err(|_| {
                    rusqlite::Error::InvalidParameterName("material_epoch_unavailable".into())
                })?;
            if receipt["plan"]["restore_epoch"] != epoch {
                return Err(rusqlite::Error::InvalidParameterName(
                    "material_restore_changed".into(),
                ));
            }
            let encoded = receipt.to_string();
            let model = receipt["answer"]["model"].as_str().unwrap_or("UNKNOWN");
            archeaxis_domain::machine::record_machine_task(
                conn,
                &archeaxis_domain::machine::MachineTask {
                    task_id: &id,
                    principal: "machine",
                    conditions: &encoded,
                    knowledge_version: None,
                    method_version: Some("material-question/v1"),
                    tool_version: None,
                    model_version: model,
                    scope: "runtime.material.answer",
                    outcome,
                    failure: reason,
                    retest_of: None,
                },
            )?;
            Ok(receipt)
        })
        .await;
    match saved {
        Ok(Ok(r)) => Json(r).into_response(),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "material_result_unknown_retain_request",
        ),
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Cancel {
    request_id: String,
}
pub(super) async fn cancel(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Cancel>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") || !identity(&body.request_id) {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    let requested = runtime
        .machine_active
        .lock()
        .ok()
        .and_then(|entries| {
            entries
                .get(&key(&body.request_id))
                .map(MachineActive::request_cancel)
        })
        .unwrap_or(false);
    Json(json!({"request_id":body.request_id,"cancel_requested":requested,"execution_state":"UNKNOWN","provider_stop_state":"UNKNOWN"})).into_response()
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Status {
    request_id: Option<String>,
}
pub(super) async fn status(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Status>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human")
        || body.request_id.as_ref().is_some_and(|id| !identity(id))
    {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    let result=runtime.executor.store().submit_wait(move |conn|{
        let Some(request_id)=body.request_id else {
            let mut statement=conn.prepare("SELECT value FROM workspace_meta WHERE key LIKE 'material_request_material_answer_%' ORDER BY rowid DESC LIMIT 16")?;
            let items=statement.query_map([],|row|row.get::<_,String>(0))?.collect::<Result<Vec<_>,_>>()?;
            let plans=items.into_iter().map(|raw|serde_json::from_str::<Value>(&raw).map_err(|_|rusqlite::Error::InvalidParameterName("material_journal_invalid".into()))).collect::<Result<Vec<_>,_>>()?;
            return Ok(json!({"schema":"archeaxis.material-question-journal/v1","plans":plans,"limit":16,"scope":"latest_requests_only"}))
        };
        let task=archeaxis_domain::machine::machine_task(conn,&key(&request_id))?;
        if let Some(task)=task{return serde_json::from_str::<Value>(&task.conditions).map_err(|_|rusqlite::Error::InvalidParameterName("material_receipt_invalid".into()))}
        let claim_key=format!("machine_execution_claim_{}",material::hash(key(&request_id).as_bytes()));
        let pending:Option<String>=conn.query_row("SELECT value FROM workspace_meta WHERE key=?1",[claim_key],|r|r.get(0)).optional()?;
        let plan:Option<String>=conn.query_row("SELECT value FROM workspace_meta WHERE key=?1",[format!("material_request_{}",key(&request_id))],|r|r.get(0)).optional()?;
        Ok(json!({"request_id":request_id,"plan":plan.and_then(|p|serde_json::from_str::<Value>(&p).ok()),"execution_state":if pending.is_some(){"UNKNOWN"}else{"NOT_EXECUTED"},"answer_published":false,"provider_stop_state":"UNKNOWN"}))
    }).await;
    match result {
        Ok(Ok(mut receipt)) => {
            if receipt["execution_state"] == "UNKNOWN"
                && receipt["plan"]["request"]["execution_mode"] == "async"
            {
                let owned = runtime.machine_active.lock().ok().is_some_and(|entries| {
                    entries
                        .get(&key(receipt["request_id"].as_str().unwrap_or_default()))
                        .is_some_and(|e| receipt["plan"]["restore_epoch"] == e.restore_epoch)
                });
                if owned {
                    receipt["execution_state"] = json!("RUNNING");
                }
            }
            Json(receipt).into_response()
        }
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "material_status_unavailable",
        ),
    }
}

#[cfg(test)]
mod async_publication_tests {
    use super::*;
    async fn read(runtime: Runtime) -> Value {
        let mut headers = HeaderMap::new();
        headers.insert("x-archeaxis-actor", "human".parse().unwrap());
        let response = status(
            State(runtime),
            headers,
            Json(Status {
                request_id: Some("publication_gap".into()),
            }),
        )
        .await;
        assert_eq!(response.status(), StatusCode::OK);
        serde_json::from_slice(
            &axum::body::to_bytes(response.into_body(), 1000000)
                .await
                .unwrap(),
        )
        .unwrap()
    }
    #[tokio::test]
    async fn closed_live_material_lease_stays_running_until_publication_owner_drops() {
        let dir = tempfile::tempdir().unwrap();
        let executor = Executor::open(
            &dir.path().join("w.sqlite"),
            &dir.path().join("staging"),
            std::path::Path::new("unused-python"),
            std::path::Path::new("unused-worker"),
        )
        .await
        .unwrap();
        let id = key("publication_gap");
        let stored = id.clone();
        executor.store().submit_wait(move|conn| {
            let plan=json!({"request":{"request_id":"publication_gap","execution_mode":"async"},"restore_epoch":"initial"});
            conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",rusqlite::params![format!("material_request_{stored}"),plan.to_string()]).unwrap();
            conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,'{}')",[format!("machine_execution_claim_{}",material::hash(stored.as_bytes()))]).unwrap();
        }).await.unwrap();
        let registry = Arc::new(std::sync::Mutex::new(HashMap::new()));
        let cancel = Cancellation::new();
        registry.lock().unwrap().insert(
            id.clone(),
            super::super::MachineActive {
                attempt: 1,
                restore_epoch: "initial".into(),
                cancel: cancel.clone(),
                accepting: true,
            },
        );
        let runtime = Runtime {
            executor,
            active: Arc::new(Mutex::new(HashMap::new())),
            admission: Arc::new(Mutex::new(())),
            colearning_admission: Arc::new(Mutex::new(())),
            machine_active: registry.clone(),
        };
        let lease = super::super::MachineLease {
            registry,
            key: id,
            attempt: 1,
            cancel,
        };
        assert!(!lease.close().unwrap());
        // Hold the real lease across a controlled postcheck/persistence pause.
        let (release, wait) = tokio::sync::oneshot::channel::<()>();
        let publisher = tokio::spawn(async move {
            let _ = wait.await;
            drop(lease);
        });
        assert_eq!(read(runtime.clone()).await["execution_state"], "RUNNING");
        let mut headers = HeaderMap::new();
        headers.insert("x-archeaxis-actor", "human".parse().unwrap());
        let response = super::cancel(
            State(runtime.clone()),
            headers,
            Json(Cancel {
                request_id: "publication_gap".into(),
            }),
        )
        .await;
        let value: Value = serde_json::from_slice(
            &axum::body::to_bytes(response.into_body(), 1000000)
                .await
                .unwrap(),
        )
        .unwrap();
        assert_eq!(value["cancel_requested"], false);
        assert_eq!(value["provider_stop_state"], "UNKNOWN");
        release.send(()).unwrap();
        publisher.await.unwrap();
        assert_eq!(read(runtime).await["execution_state"], "UNKNOWN");
    }
}
