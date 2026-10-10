//! Clear a UI execution intent only under the real execution admission/active guards.
use super::*;
use archeaxis_domain::ui_state::{self, ClearJob, Error};

pub(super) async fn clear(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<ClearJob>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    let _admission = runtime.admission.lock().await;
    let active = runtime.active.lock().await;
    // Fail closed while any worker is in flight. Clearance never cancels a worker.
    if !active.is_empty() {
        return (StatusCode::CONFLICT, "execution still active; journal retained").into_response();
    }
    match runtime.executor.store().submit_wait(move |conn| ui_state::clear_job(conn,request)).await {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err(Error::Conflict)) => (StatusCode::CONFLICT,"journal CAS changed; reread").into_response(),
        Ok(Err(Error::Invalid(reason))) => (StatusCode::UNPROCESSABLE_ENTITY,reason).into_response(),
        _ => (StatusCode::SERVICE_UNAVAILABLE,"journal clear unconfirmed").into_response(),
    }
}
