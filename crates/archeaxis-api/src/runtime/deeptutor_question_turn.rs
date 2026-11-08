//! DeepTutor's single-question step as a Core route: capture the donor prompt
//! from the pinned local worker, call the declared local text model, replay the
//! reply through the same worker and persist one inert candidate Document.
use super::*;
use archeaxis_application::executor::{Cancellation, QuestionTurnWorkerError};
use archeaxis_domain::{
    openmaic_outline,
    provider_question_turn::{self as turn, QuestionTurnRequest},
};
use std::time::Duration;

const CAPTURE_TIMEOUT: Duration = Duration::from_secs(60);
const MODEL_TIMEOUT: Duration = Duration::from_secs(120);
const REPLAY_TIMEOUT: Duration = Duration::from_secs(60);

/// A dropped request stops our owned worker. A committed write that wins over
/// a later disconnect leaves an unknown outcome; retry the same create ID.
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
        Json(json!({"code":"DEEPTUTOR_QUESTION_TURN","reason":reason,
            "retryable":status == StatusCode::SERVICE_UNAVAILABLE})),
    )
        .into_response()
}

/// A stage failure named by the stage that produced it and by the worker's or
/// model's own status/reason, never rewritten into a generic message.
fn stage_failure(
    status: StatusCode,
    stage: &'static str,
    reason: &'static str,
    outcome: Value,
) -> Response {
    (
        status,
        Json(json!({"code":"DEEPTUTOR_QUESTION_TURN","reason":reason,
            "retryable":status == StatusCode::SERVICE_UNAVAILABLE,
            "stage":stage,"worker_outcome":outcome})),
    )
        .into_response()
}

fn worker_failure_reason(error: QuestionTurnWorkerError) -> &'static str {
    match error {
        QuestionTurnWorkerError::InvalidInput => "question_turn_worker_input_invalid",
        QuestionTurnWorkerError::Unavailable => "question_turn_worker_unavailable",
        QuestionTurnWorkerError::IdentityMismatch => "question_turn_worker_identity_mismatch",
        QuestionTurnWorkerError::Cancelled => "question_turn_request_cancelled",
        QuestionTurnWorkerError::TimedOut => "question_turn_worker_timed_out",
        QuestionTurnWorkerError::CleanupUnknown => "question_turn_worker_cleanup_unknown",
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
        Some("UNAVAILABLE") => "question_turn_worker_upstream_unavailable",
        Some("INVALID_REQUEST") => "question_turn_worker_input_rejected",
        Some("REJECTED") => "question_turn_worker_response_rejected",
        _ => "question_turn_worker_outcome_unrecognized",
    }
}

fn result_response(status: StatusCode, receipt: Value, worker_invoked: bool) -> Response {
    let mut body = receipt;
    body["worker_invoked"] = json!(worker_invoked);
    (status, Json(body)).into_response()
}

/// Capture, model, replay, persist. Every failing stage leaves no Document.
pub(super) async fn question_turn(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<QuestionTurnRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    if turn::request_refusal(&request).is_some() {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "invalid_question_turn_request",
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
            move |conn| turn::prepare_question_turn(conn, &request)
        })
        .await;
    let pending = match prepared {
        Ok(Ok(turn::QuestionTurnPreparation::Existing(receipt))) => {
            // A repeated request reads the stored candidate; no prompt, model or
            // worker runs again.
            return result_response(StatusCode::OK, receipt, false);
        }
        Ok(Ok(turn::QuestionTurnPreparation::Pending(pending))) => pending,
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return failure(StatusCode::CONFLICT, "question_turn_material_unavailable");
        }
        Ok(Err(
            archeaxis_domain::document::Error::Invalid(_)
            | archeaxis_domain::document::Error::Conflict(_),
        )) => {
            return failure(
                StatusCode::CONFLICT,
                "question_turn_material_not_authorized_or_changed",
            );
        }
        _ => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "question_turn_preparation_failed",
            );
        }
    };
    // Stage 1: capture the donor prompt. The capture carries no reply.
    let capture = runtime
        .executor
        .run_deeptutor_question_turn(
            pending.capture_frame().to_vec(),
            CAPTURE_TIMEOUT,
            lease.cancel.clone(),
        )
        .await;
    let capture = match capture {
        Ok(value) => value,
        Err(error) => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                worker_failure_reason(error),
            );
        }
    };
    if let Some(status) = worker_status(&capture) {
        return stage_failure(
            status,
            "capture",
            worker_reason(&capture),
            worker_outcome(&capture),
        );
    }
    if capture["document"]["status"] != "CAPTURED" {
        return stage_failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "capture",
            "question_turn_capture_outcome_unrecognized",
            worker_outcome(&capture),
        );
    }
    let binding = match turn::capture_binding(&request.create_request_id, &capture["document"]) {
        Ok(value) => value,
        Err(_) => {
            return stage_failure(
                StatusCode::BAD_GATEWAY,
                "capture",
                "question_turn_capture_binding_invalid",
                worker_outcome(&capture),
            );
        }
    };
    // Stage 2: the one declared local text model, through the same worker and
    // hardened loopback-only transport as the outline route.
    let model = runtime
        .executor
        .derived_json(
            openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
            turn::model_request(&binding, &request.model),
            MODEL_TIMEOUT,
        )
        .await;
    let model = match model {
        Ok(value) => value,
        Err(reason) => {
            return stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "local_model",
                "question_turn_local_model_capability_unavailable",
                json!({"reason":reason}),
            );
        }
    };
    let model_outcome = worker_outcome(&model);
    if model["exit_code"] != 0 || model["document"]["status"] != "REPLY" {
        let status = match model["document"]["status"].as_str() {
            Some("MODEL_REJECTED" | "INVALID_MODEL_OUTPUT") => StatusCode::UNPROCESSABLE_ENTITY,
            Some("MODEL_TIMEOUT" | "NO_FINAL_ANSWER") => StatusCode::GATEWAY_TIMEOUT,
            _ => StatusCode::SERVICE_UNAVAILABLE,
        };
        return stage_failure(
            status,
            "local_model",
            "question_turn_local_model_failed",
            model_outcome,
        );
    }
    let Some(content) =
        openmaic_outline::openmaic_outline_new_model_content(&model["document"]).map(str::to_owned)
    else {
        return stage_failure(
            StatusCode::BAD_GATEWAY,
            "local_model",
            "question_turn_local_model_receipt_inconsistent",
            model_outcome,
        );
    };
    let prompt_sha256 = binding["prompt_sha256"]
        .as_str()
        .unwrap_or_default()
        .to_owned();
    // Stage 3: replay the model text through the real donor worker.
    let replay_frame = match pending.replay_frame(&prompt_sha256, &content) {
        Ok(value) => value,
        Err(_) => {
            return stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "replay",
                "question_turn_replay_frame_unusable",
                model_outcome,
            );
        }
    };
    let replay = runtime
        .executor
        .run_deeptutor_question_turn(replay_frame, REPLAY_TIMEOUT, lease.cancel.clone())
        .await;
    let replay = match replay {
        Ok(value) => value,
        Err(error) => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                worker_failure_reason(error),
            );
        }
    };
    if let Some(status) = worker_status(&replay) {
        return stage_failure(
            status,
            "replay",
            worker_reason(&replay),
            worker_outcome(&replay),
        );
    }
    if replay["document"]["status"] != "CANDIDATE" {
        // Every named replay outcome keeps its own status and reason.
        return stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "replay",
            "question_turn_replay_not_a_candidate",
            worker_outcome(&replay),
        );
    }
    let generation = turn::QuestionTurnGeneration {
        capture_document: capture["document"].clone(),
        model_reply: model["document"].clone(),
        replay_document: replay["document"].clone(),
    };
    if lease.cancel.is_cancelled() {
        return failure(StatusCode::CONFLICT, "question_turn_request_cancelled");
    }
    let cancelled = lease.cancel.clone();
    let persisted = runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            if cancelled.is_cancelled() {
                return Err(archeaxis_domain::document::Error::Invalid(
                    "question turn request cancelled",
                ));
            }
            turn::commit_question_turn(conn, &request, &pending, &generation)
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
            "question_turn_material_or_request_changed",
        ),
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "question_turn_persistence_failed",
        ),
    }
}
