//! Clear a UI execution intent only under the real execution admission/active guards.
use super::*;
use archeaxis_domain::ui_state::{self, ClearMachine, Error};

pub(super) async fn cancel(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<ui_state::MachineStatus>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    let journal_id = request.journal_id.clone();
    let target = runtime
        .executor
        .store()
        .submit_wait(move |conn| ui_state::machine_cancel_target(conn, request))
        .await;
    match target {
        Ok(Ok(Some((key,attempt,restore_epoch)))) => {
            let Ok(entries) = runtime.machine_active.lock() else {
                return (StatusCode::SERVICE_UNAVAILABLE,"machine registry unconfirmed").into_response();
            };
            let requested = entries.get(&key).filter(|entry| entry.attempt == attempt && entry.restore_epoch == restore_epoch && entry.accepting)
                .is_some_and(|entry| {entry.cancel.cancel();true});
            Json(json!({"schema":"archeaxis.machine-cancel-receipt/v1","journal_id":journal_id,"attempt":attempt,
                "cancel_requested":requested,"execution_state":"UNKNOWN","provider_stop_state":"UNKNOWN"})).into_response()
        }
        Ok(Ok(None)) => Json(json!({"schema":"archeaxis.machine-cancel-receipt/v1","journal_id":journal_id,"attempt":null,
            "cancel_requested":false,"execution_state":"UNKNOWN","provider_stop_state":"UNKNOWN"})).into_response(),
        Ok(Err(Error::Conflict)) => (StatusCode::CONFLICT,"journal CAS changed; reread").into_response(),
        Ok(Err(Error::Invalid(reason))) => (StatusCode::UNPROCESSABLE_ENTITY,reason).into_response(),
        _ => (StatusCode::SERVICE_UNAVAILABLE,"machine cancellation unconfirmed").into_response(),
    }
}

pub(super) async fn status(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<ui_state::MachineStatus>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| ui_state::machine_status(conn, request))
        .await
    {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err(Error::Conflict)) => {
            (StatusCode::CONFLICT, "journal CAS changed; reread").into_response()
        }
        Ok(Err(Error::Invalid(reason))) => {
            (StatusCode::UNPROCESSABLE_ENTITY, reason).into_response()
        }
        _ => (
            StatusCode::SERVICE_UNAVAILABLE,
            "machine status unconfirmed",
        )
            .into_response(),
    }
}

pub(super) async fn clear(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<ClearMachine>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    let _admission = runtime.colearning_admission.lock().await;
    let active = runtime.active.lock().await;
    // Fail closed while any worker is in flight. Clearance never cancels a worker.
    if !active.is_empty() {
        return (
            StatusCode::CONFLICT,
            "execution still active; journal retained",
        )
            .into_response();
    }
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| ui_state::clear_machine(conn, request))
        .await
    {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err(Error::Conflict)) => {
            (StatusCode::CONFLICT, "journal CAS changed; reread").into_response()
        }
        Ok(Err(Error::Invalid(reason))) => {
            (StatusCode::UNPROCESSABLE_ENTITY, reason).into_response()
        }
        _ => (StatusCode::SERVICE_UNAVAILABLE, "journal clear unconfirmed").into_response(),
    }
}
