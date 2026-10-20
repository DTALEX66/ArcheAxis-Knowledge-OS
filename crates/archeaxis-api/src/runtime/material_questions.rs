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
    max_tokens: u64,
    timeout_s: u64,
    #[serde(default)]
    preview: bool,
    confirmed_plan_sha256: Option<String>,
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
    Json(mut body): Json<Body>,
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
        if let Some(config)=&b.model_configuration {
            plan["destination_candidates"]=json!([config.profile.endpoint]);
            plan["selection_policy"]=json!("frozen_material_purpose_profile");
            plan["network_scope"]=json!("configured_numeric_loopback_endpoint");
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
    let _guard = runtime.colearning_admission.lock().await;
    let id = key(&body.request_id);
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
    let execution = runtime
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
        .await;
    if execution.as_ref().err().is_some_and(|e| {
        e.message().contains("cleanup incomplete") || e.message().contains("cleanup_incomplete")
    }) {
        return failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "material_execution_unknown_retain_request",
        );
    }
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
            entries.get(&key(&body.request_id)).map(|e| {
                if e.accepting {
                    e.cancel.cancel();
                    true
                } else {
                    false
                }
            })
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
        Ok(Ok(receipt)) => Json(receipt).into_response(),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "material_status_unavailable",
        ),
    }
}
