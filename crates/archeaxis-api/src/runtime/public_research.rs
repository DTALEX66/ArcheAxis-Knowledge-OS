//! Explicit public terms only. HTTP intent never includes a document or arbitrary URL.
use super::*;
use archeaxis_domain::public_research::{self as research, Begin, Request};

fn failure(status: StatusCode, reason: &str) -> Response {
    (
        status,
        Json(json!({"reason_code":reason,"knowledge_admission":"not_executed"})),
    )
        .into_response()
}
fn key(id: &str) -> String {
    format!("public_research_{id}")
}

pub(super) async fn search(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<Request>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    if let Err(reason) = request.validate() {
        return failure(StatusCode::UNPROCESSABLE_ENTITY, &reason);
    }
    // Serialize only durable admission, never hold this guard while performing network I/O.
    let guard = runtime.admission.lock().await;
    let frozen = request.clone();
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| research::begin(conn, &frozen))
        .await
    {
        Ok(Ok(Begin::Cached(receipt))) => return Json(receipt).into_response(),
        Ok(Ok(Begin::Started)) => (),
        Ok(Err(reason)) => return failure(StatusCode::CONFLICT, &reason),
        _ => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "public_query_admission_unavailable",
            );
        }
    }
    let cancel = Cancellation::new();
    let registry_key = key(&request.request_id);
    {
        let Ok(mut entries) = runtime.machine_active.lock() else {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "public_query_registry_unknown",
            );
        };
        if entries.contains_key(&registry_key) {
            return failure(StatusCode::CONFLICT, "public_query_registry_conflict");
        }
        entries.insert(
            registry_key.clone(),
            MachineActive {
                attempt: 1,
                restore_epoch: request.restore_epoch.clone(),
                cancel: cancel.clone(),
                accepting: true,
            },
        );
    }
    let lease = MachineLease {
        registry: runtime.machine_active.clone(),
        key: registry_key,
        attempt: 1,
        cancel,
    };
    drop(guard);
    let execution = runtime
        .executor
        .public_research(request.worker_request(), lease.cancel.clone())
        .await;
    if execution.as_ref().err().is_some_and(|reason| {
        matches!(
            reason.as_str(),
            "public_research_cleanup_failed" | "public_research_task_failed"
        )
    }) {
        return failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "public_query_result_unknown_retain_request",
        );
    }
    let cancelled = lease.close().unwrap_or(true);
    let saved = runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            if cancelled {
                return research::fail(conn, &request, "public_query_cancelled", true);
            }
            let enabled =
                archeaxis_store_sqlite::capability_settings::is_enabled(conn, "research.public")
                    .map_err(|_| "public_research_settings_unavailable".to_owned())?;
            if !enabled {
                return research::fail(conn, &request, "public_research_disabled", false);
            }
            match execution {
                Ok(value) => match research::publish(conn, &request, value) {
                    Ok(receipt) => Ok(receipt),
                    Err(reason) => {
                        // Preserve rejection as a durable failure only under the original current fence.
                        research::fail(conn, &request, &reason, false)
                    }
                },
                // Executor emits finite safe codes, never stderr/query/body text.
                Err(reason) => research::fail(conn, &request, &reason, false),
            }
        })
        .await;
    match saved {
        Ok(Ok(receipt)) => Json(receipt).into_response(),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "public_query_result_unknown_retain_request",
        ),
    }
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Scope {
    workspace_id: String,
    restore_epoch: String,
}
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Target {
    workspace_id: String,
    restore_epoch: String,
    request_id: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Selection {
    workspace_id: String,
    restore_epoch: String,
    request_id: String,
    family: String,
    hit_id: String,
}

pub(super) async fn read(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Target>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            research::assert_workspace(conn, &body.workspace_id, &body.restore_epoch)?;
            research::read(conn, &body.request_id)?
                .ok_or_else(|| "public_query_not_found".to_owned())
        })
        .await
    {
        Ok(Ok(receipt)) => Json(receipt).into_response(),
        Ok(Err(reason)) => failure(StatusCode::CONFLICT, &reason),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "public_query_read_unavailable",
        ),
    }
}
pub(super) async fn list(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Scope>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            research::assert_workspace(conn, &body.workspace_id, &body.restore_epoch)?;
            research::list(conn)
        })
        .await
    {
        Ok(Ok(journal)) => Json(journal).into_response(),
        Ok(Err(reason)) => failure(StatusCode::CONFLICT, &reason),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "public_query_read_unavailable",
        ),
    }
}
pub(super) async fn cancel(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Target>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    let current = body.clone();
    match runtime.executor.store().submit_wait(move|conn| {
        research::assert_workspace(conn,&current.workspace_id,&current.restore_epoch)?;
        let receipt=research::read(conn,&current.request_id)?.ok_or("public_query_not_found")?;
        // Historical receipts remain readable; old epochs never cancel a newer request.
        if receipt["workspace_id"]!=current.workspace_id || receipt["restore_epoch"]!=current.restore_epoch {
            return Err("public_query_execution_epoch_changed".into());
        }
        Ok::<_,String>(receipt["state"]=="unknown")
    }).await {
        Ok(Ok(true))=>(),
        Ok(Ok(false))=>return Json(json!({"schema":"archeaxis.public-research-cancel/v1","request_id":body.request_id,"cancel_requested":false,"execution_state":"unknown","provider_stop_state":"unknown"})).into_response(),
        Ok(Err(reason))=>return failure(StatusCode::CONFLICT,&reason),
        _=>return failure(StatusCode::SERVICE_UNAVAILABLE,"public_query_cancel_unavailable"),
    }
    let Ok(entries) = runtime.machine_active.lock() else {
        return failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "public_query_registry_unknown",
        );
    };
    let requested = entries
        .get(&key(&body.request_id))
        .filter(|entry| entry.restore_epoch == body.restore_epoch)
        .is_some_and(MachineActive::request_cancel);
    Json(json!({"schema":"archeaxis.public-research-cancel/v1","request_id":body.request_id,"cancel_requested":requested,"execution_state":"unknown","provider_stop_state":"unknown"})).into_response()
}
pub(super) async fn materialize(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Selection>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_authorization_required");
    }
    if body.hit_id.len() > 256
        || body.hit_id.is_empty()
        || !["encyclopedia", "community", "research"].contains(&body.family.as_str())
    {
        return failure(StatusCode::UNPROCESSABLE_ENTITY, "public_selection_bounds");
    }
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            // Fresh actor scope after restore is mandatory; selecting historical material never restarts its query.
            research::assert_workspace(conn, &body.workspace_id, &body.restore_epoch)?;
            research::materialize(conn, &body.request_id, &body.family, &body.hit_id)
        })
        .await
    {
        Ok(Ok(selection)) => Json(selection).into_response(),
        Ok(Err(reason)) => failure(StatusCode::CONFLICT, &reason),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "public_selection_write_unavailable",
        ),
    }
}
