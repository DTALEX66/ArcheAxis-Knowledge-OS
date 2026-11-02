//! Private practice import and practice grading: the Core owns the input
//! snapshot, the dispatch intent and every write.
use super::*;
use archeaxis_application::executor::{
    Cancellation, PracticeGradeWorkerError, PracticeImportCancellation, PracticeImportWorkerError,
};
use archeaxis_domain::{
    document,
    provider_learning::{self as learning, grade},
    provider_question::{self, PracticeImportRequest},
};
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
    (
        status,
        Json(json!({"code":"DEEPTUTOR_PRACTICE_IMPORT", "reason":reason})),
    )
        .into_response()
}

fn worker_failure_reason(error: PracticeImportWorkerError) -> &'static str {
    match error {
        PracticeImportWorkerError::InvalidInput => "practice_worker_input_invalid",
        PracticeImportWorkerError::Unavailable => "practice_worker_unavailable",
        PracticeImportWorkerError::IdentityMismatch => "practice_worker_identity_mismatch",
        PracticeImportWorkerError::Rejected => "practice_worker_rejected",
        PracticeImportWorkerError::Cancelled => "practice_request_cancelled",
        PracticeImportWorkerError::TimedOut => "practice_worker_timed_out",
        PracticeImportWorkerError::CleanupUnknown => "practice_worker_cleanup_unknown",
    }
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
    let plan = match runtime
        .executor
        .store()
        .submit_wait(move |conn| provider_question::prepare_practice_import(conn, &request))
        .await
    {
        Ok(Ok(plan)) => plan,
        Ok(Err(document::Error::NotFound)) => {
            return failure(StatusCode::NOT_FOUND, "source_or_material_unavailable");
        }
        Ok(Err(document::Error::Invalid(_) | document::Error::Conflict(_))) => {
            return failure(
                StatusCode::CONFLICT,
                "invalid_or_changed_source_or_material",
            );
        }
        _ => {
            return failure(
                StatusCode::INTERNAL_SERVER_ERROR,
                "practice_preparation_failed",
            );
        }
    };
    let frame = plan.worker_frame().to_vec();
    let reply = match runtime
        .executor
        .run_deeptutor_practice_import(frame, Duration::from_secs(60), lease.cancel.clone())
        .await
    {
        Ok(reply) => reply,
        Err(error) => {
            return failure(
                StatusCode::SERVICE_UNAVAILABLE,
                worker_failure_reason(error),
            );
        }
    };
    let cancelled = lease.cancel.clone();
    let result = runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            if !cancelled.begin_commit() {
                return Err(document::Error::Invalid("practice request cancelled"));
            }
            provider_question::finish_practice_import(conn, &plan, &reply)
        })
        .await;
    match result {
        Ok(Ok(view)) => Json(view).into_response(),
        Ok(Err(
            document::Error::NotFound | document::Error::Invalid(_) | document::Error::Conflict(_),
        )) => failure(
            StatusCode::CONFLICT,
            "practice_source_material_or_request_changed",
        ),
        _ => failure(
            StatusCode::INTERNAL_SERVER_ERROR,
            "practice_persistence_failed",
        ),
    }
}

/// The grading budget also bounds how long the remaining grants must cover.
const PRACTICE_GRADE_TIMEOUT: Duration = Duration::from_secs(60);

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PracticeGradeBody {
    activity_id: String,
    attempt_id: String,
    request: grade::GradeRequest,
}

fn grade_failure(status: StatusCode, reason: &'static str) -> Response {
    (
        status,
        Json(json!({"code":"DEEPTUTOR_PRACTICE_GRADE","reason":reason})),
    )
        .into_response()
}

fn grade_worker_reason(error: PracticeGradeWorkerError) -> &'static str {
    match error {
        PracticeGradeWorkerError::InvalidInput => "practice_grade_input_invalid",
        PracticeGradeWorkerError::Unavailable => "practice_grade_worker_unavailable",
        PracticeGradeWorkerError::IdentityMismatch => "practice_grade_worker_identity_mismatch",
        PracticeGradeWorkerError::Rejected => "practice_grade_worker_rejected",
        PracticeGradeWorkerError::Cancelled => "practice_request_cancelled",
        PracticeGradeWorkerError::TimedOut => "practice_grade_worker_timed_out",
        PracticeGradeWorkerError::CleanupUnknown => "practice_grade_worker_cleanup_unknown",
    }
}

/// A dropped HTTP request stops our owned worker. The durable reservation is
/// then left DISPATCHED, so re-posting the same event is a read-only UNKNOWN
/// instead of a second launch.
struct GradeLease {
    cancel: Cancellation,
}
impl Drop for GradeLease {
    fn drop(&mut self) {
        self.cancel.cancel();
    }
}

/// Grade one human answer through the fixed DeepTutor 1.7.1 practice grader.
///
/// The Core reserves the exact client event and attempt together, records the
/// durable dispatch intent after rechecking both material grants, the attempt
/// and the restore epoch, runs the hash-pinned private worker, then persists the
/// observed result in a fresh transaction that rechecks all of those again. A
/// `provider_correct: null` receipt is stored as an unscored observation, not a
/// failure to retry; an unclear worker outcome is recorded UNKNOWN and never
/// relaunched automatically. The result is not an independent mastery claim.
pub(super) async fn grade_practice(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<PracticeGradeBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return grade_failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    let lease = GradeLease {
        cancel: Cancellation::new(),
    };
    let PracticeGradeBody {
        activity_id,
        attempt_id,
        request,
    } = body;
    let store = runtime.executor.store().clone();
    let prepared = {
        let activity = activity_id.clone();
        let attempt = attempt_id.clone();
        let request = request.clone();
        match store
            .submit_wait(move |conn| grade::prepare(conn, &activity, &attempt, &request))
            .await
        {
            Ok(Ok(grade::Admission::Ready(prepared))) => prepared,
            // A committed result is a history read, never a second execution.
            Ok(Ok(grade::Admission::Completed(receipt))) => {
                return Json(receipt).into_response();
            }
            Ok(Ok(grade::Admission::Unknown)) => {
                return grade_failure(StatusCode::CONFLICT, "practice_grade_outcome_unknown");
            }
            Ok(Err(learning::Error::Invalid(_))) => {
                return grade_failure(StatusCode::UNPROCESSABLE_ENTITY, "invalid_grade_request");
            }
            Ok(Err(learning::Error::NotFound)) => {
                return grade_failure(StatusCode::NOT_FOUND, "practice_object_not_found");
            }
            Ok(Err(learning::Error::Conflict(_))) => {
                return grade_failure(StatusCode::CONFLICT, "practice_grade_conflict");
            }
            _ => {
                return grade_failure(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "practice_grade_preparation_failed",
                );
            }
        }
    };
    if lease.cancel.is_cancelled() {
        return grade_failure(StatusCode::CONFLICT, "practice_request_cancelled");
    }
    // Durable dispatch intent. Recovery of a reservation whose dispatch is not
    // certain is read-only UNKNOWN, so this step is the last point that may
    // decide to write bytes.
    let (prepared, dispatched) = match store
        .submit_wait(move |conn| {
            let outcome = grade::begin_dispatch(conn, &prepared, PRACTICE_GRADE_TIMEOUT);
            (prepared, outcome)
        })
        .await
    {
        Ok(state) => state,
        Err(_) => {
            return grade_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "practice_grade_preparation_failed",
            );
        }
    };
    if dispatched.is_err() {
        return grade_failure(
            StatusCode::CONFLICT,
            "practice_grade_not_authorized_or_changed",
        );
    }
    let input = prepared.worker_input().to_vec();
    match runtime
        .executor
        .run_deeptutor_practice_grade(input, PRACTICE_GRADE_TIMEOUT, lease.cancel.clone())
        .await
    {
        Ok(receipt) => {
            if lease.cancel.is_cancelled() {
                let _ = store
                    .submit_wait(move |conn| grade::abandon_unknown(conn, &prepared))
                    .await;
                return grade_failure(StatusCode::CONFLICT, "practice_request_cancelled");
            }
            let persisted = store
                .submit_wait(move |conn| grade::complete_observed(conn, &prepared, &receipt))
                .await;
            match persisted {
                Ok(Ok(value)) => {
                    let status = if value["duplicate"] == true {
                        StatusCode::OK
                    } else {
                        StatusCode::CREATED
                    };
                    (status, Json(value)).into_response()
                }
                // A withdrawal, restore or cancellation that won the completion
                // transaction refuses the observed result rather than publishing it.
                Ok(Err(_)) => grade_failure(StatusCode::CONFLICT, "practice_grade_result_refused"),
                Err(_) => grade_failure(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "practice_grade_persistence_failed",
                ),
            }
        }
        Err(error) => {
            // The worker's outcome is unclear. Record UNKNOWN so the same event
            // can never be launched twice, and never invent a grade.
            let _ = store
                .submit_wait(move |conn| grade::abandon_unknown(conn, &prepared))
                .await;
            grade_failure(StatusCode::SERVICE_UNAVAILABLE, grade_worker_reason(error))
        }
    }
}
