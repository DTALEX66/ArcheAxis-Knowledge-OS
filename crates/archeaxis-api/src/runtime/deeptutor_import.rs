//! Private practice import: the Core owns both the input snapshot and the write.
use super::*;
use archeaxis_application::executor::PracticeImportCancellation;
use archeaxis_domain::{document, provider_question::{self, PracticeImportRequest}};
use std::time::Duration;

/// A committed write that wins over a later disconnect can leave an unknown
/// outcome; retry with the same create_request_id to discover it.
struct RequestLease {
    cancel: PracticeImportCancellation,
}
impl Drop for RequestLease {
    fn drop(&mut self) {
        self.cancel.cancel();
    }
}

fn failure(status: StatusCode, reason: &'static str) -> Response {
    (status, Json(json!({"code":"DEEPTUTOR_PRACTICE_IMPORT", "reason":reason}))).into_response()
}

pub(super) async fn import_practice(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<PracticeImportRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    let lease = RequestLease {
        cancel: PracticeImportCancellation::new(),
    };
    let plan = match runtime.executor.store().submit_wait(move |conn| {
        provider_question::prepare_practice_import(conn, &request)
    }).await {
        Ok(Ok(plan)) => plan,
        Ok(Err(document::Error::NotFound)) => return failure(StatusCode::NOT_FOUND, "source_or_material_unavailable"),
        Ok(Err(document::Error::Invalid(_) | document::Error::Conflict(_))) => {
            return failure(StatusCode::CONFLICT, "invalid_or_changed_source_or_material");
        }
        _ => return failure(StatusCode::INTERNAL_SERVER_ERROR, "practice_preparation_failed"),
    };
    let frame = plan.worker_frame().to_vec();
    let reply = match runtime.executor.run_deeptutor_practice_import(
        frame, Duration::from_secs(60), lease.cancel.clone(),
    ).await {
        Ok(reply) => reply,
        Err(_) => return failure(StatusCode::SERVICE_UNAVAILABLE, "practice_worker_unavailable_or_result_unknown"),
    };
    let cancelled = lease.cancel.clone();
    let result = runtime.executor.store().submit_wait(move |conn| {
        if !cancelled.begin_commit() { return Err(document::Error::Invalid("practice request cancelled")); }
        provider_question::finish_practice_import(conn, &plan, &reply)
    }).await;
    match result {
        Ok(Ok(view)) => Json(view).into_response(),
        Ok(Err(document::Error::NotFound | document::Error::Invalid(_) | document::Error::Conflict(_))) => {
            failure(StatusCode::CONFLICT, "practice_source_material_or_request_changed")
        }
        _ => failure(StatusCode::INTERNAL_SERVER_ERROR, "practice_persistence_failed"),
    }
}
