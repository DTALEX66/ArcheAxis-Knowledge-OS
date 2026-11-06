//! DeepTutor's teaching-feedback step as a Core route: run the pinned donor
//! rules worker once over a caller-declared profile snapshot and persist one
//! inert candidate Document. No model, activity, review or mastery is written.
use super::*;
use archeaxis_application::executor::{Cancellation, TeachingFeedbackWorkerError};
use archeaxis_domain::provider_teaching_feedback::{
    self as feedback, TeachingFeedbackGeneration, TeachingFeedbackRequest,
};
use std::time::Duration;

const WORKER_TIMEOUT: Duration = Duration::from_secs(60);

/// A dropped request stops our owned worker. A committed write that wins over a
/// later disconnect leaves an unknown outcome; retry the same create ID.
struct RequestLease {
    cancel: Cancellation,
}
impl Drop for RequestLease {
    fn drop(&mut self) {
        self.cancel.cancel();
    }
}

fn failure(status: StatusCode, reason: &'static str) -> Response {
    (
        status,
        Json(json!({"code":"DEEPTUTOR_TEACHING_FEEDBACK","reason":reason,
            "retryable":status == StatusCode::SERVICE_UNAVAILABLE})),
    )
        .into_response()
}

fn stage_failure(status: StatusCode, reason: &'static str, outcome: Value) -> Response {
    (
        status,
        Json(json!({"code":"DEEPTUTOR_TEACHING_FEEDBACK","reason":reason,
            "retryable":status == StatusCode::SERVICE_UNAVAILABLE,
            "stage":"worker","worker_outcome":outcome})),
    )
        .into_response()
}

fn worker_failure_reason(error: TeachingFeedbackWorkerError) -> &'static str {
    match error {
        TeachingFeedbackWorkerError::InvalidInput => "teaching_feedback_worker_input_invalid",
        TeachingFeedbackWorkerError::Unavailable => "teaching_feedback_worker_unavailable",
        TeachingFeedbackWorkerError::IdentityMismatch => {
            "teaching_feedback_worker_identity_mismatch"
        }
        TeachingFeedbackWorkerError::Cancelled => "teaching_feedback_request_cancelled",
        TeachingFeedbackWorkerError::TimedOut => "teaching_feedback_worker_timed_out",
        TeachingFeedbackWorkerError::CleanupUnknown => "teaching_feedback_worker_cleanup_unknown",
    }
}

fn worker_outcome(value: &Value) -> Value {
    json!({"status":value["document"]["status"],"reason":value["document"]["reason_code"],
        "exit_code":value["exit_code"]})
}

/// Map one worker result to the caller's status. Every named non-success keeps
/// the worker's own status; an exit code outside the declared 0/1/2 is an
/// unrecognized outcome rather than a candidate.
fn worker_status(value: &Value) -> Option<StatusCode> {
    if value["exit_code"] == 0 {
        return None;
    }
    Some(match value["document"]["status"].as_str() {
        Some("UNAVAILABLE") => StatusCode::SERVICE_UNAVAILABLE,
        Some("INVALID_REQUEST" | "REJECTED") => StatusCode::UNPROCESSABLE_ENTITY,
        _ => StatusCode::SERVICE_UNAVAILABLE,
    })
}

fn worker_reason(value: &Value) -> &'static str {
    match value["document"]["status"].as_str() {
        Some("UNAVAILABLE") => "teaching_feedback_worker_upstream_unavailable",
        Some("INVALID_REQUEST") => "teaching_feedback_worker_input_rejected",
        Some("REJECTED") => "teaching_feedback_worker_response_rejected",
        _ => "teaching_feedback_worker_outcome_unrecognized",
    }
}

fn result_response(status: StatusCode, receipt: Value, worker_invoked: bool) -> Response {
    let mut body = receipt;
    body["worker_invoked"] = json!(worker_invoked);
    (status, Json(body)).into_response()
}

/// Prepare, run the donor rules once, persist. A failing worker leaves no
/// Document, and a repeated request reads the stored candidate without rerunning.
pub(super) async fn teaching_feedback(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<TeachingFeedbackRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    if feedback::request_refusal(&request).is_some() {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "invalid_teaching_feedback_request",
        );
    }
    let lease = RequestLease {
        cancel: Cancellation::new(),
    };
    let prepared = runtime
        .executor
        .store()
        .submit_wait({
            let request = request.clone();
            move |conn| feedback::prepare_teaching_feedback(conn, &request)
        })
        .await;
    let pending = match prepared {
        Ok(Ok(feedback::TeachingFeedbackPreparation::Existing(receipt))) => {
            // A repeated request reads the stored candidate; no worker runs again.
            return result_response(StatusCode::OK, receipt, false);
        }
        Ok(Ok(feedback::TeachingFeedbackPreparation::Pending(pending))) => pending,
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return failure(
                StatusCode::CONFLICT,
                "teaching_feedback_profile_unavailable",
            );
        }
        Ok(Err(
            archeaxis_domain::document::Error::Invalid(_)
            | archeaxis_domain::document::Error::Conflict(_),
        )) => {
            return failure(
                StatusCode::CONFLICT,
                "teaching_feedback_profile_not_authorized_or_changed",
            );
        }
        _ => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "teaching_feedback_preparation_failed",
            );
        }
    };
    let outcome = runtime
        .executor
        .run_deeptutor_teaching_feedback(
            pending.frame().to_vec(),
            WORKER_TIMEOUT,
            lease.cancel.clone(),
        )
        .await;
    let outcome = match outcome {
        Ok(value) => value,
        Err(error) => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                worker_failure_reason(error),
            );
        }
    };
    if let Some(status) = worker_status(&outcome) {
        return stage_failure(status, worker_reason(&outcome), worker_outcome(&outcome));
    }
    match outcome["document"]["status"].as_str() {
        Some("UPDATED" | "UNCHANGED") => {}
        _ => {
            return stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "teaching_feedback_worker_not_a_candidate",
                worker_outcome(&outcome),
            );
        }
    }
    if lease.cancel.is_cancelled() {
        return failure(StatusCode::CONFLICT, "teaching_feedback_request_cancelled");
    }
    let cancelled = lease.cancel.clone();
    let generation = TeachingFeedbackGeneration {
        worker_document: outcome["document"].clone(),
    };
    let persisted = runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            if cancelled.is_cancelled() {
                return Err(archeaxis_domain::document::Error::Invalid(
                    "teaching feedback request cancelled",
                ));
            }
            feedback::commit_teaching_feedback(conn, &request, &pending, &generation)
        })
        .await;
    match persisted {
        Ok(Ok(receipt)) => result_response(StatusCode::CREATED, receipt, true),
        Ok(Err(
            archeaxis_domain::document::Error::NotFound
            | archeaxis_domain::document::Error::Invalid(_)
            | archeaxis_domain::document::Error::Conflict(_),
        )) => failure(
            StatusCode::CONFLICT,
            "teaching_feedback_profile_or_request_changed",
        ),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "teaching_feedback_persistence_failed",
        ),
    }
}
