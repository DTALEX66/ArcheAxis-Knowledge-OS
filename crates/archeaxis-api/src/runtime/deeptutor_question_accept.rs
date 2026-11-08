//! Human acceptance of a generated DeepTutor question candidate. Core turns one
//! current question-turn Document into an ordinary graded-question Document only
//! when the caller supplies the answer key explicitly.
use super::*;
use archeaxis_domain::provider_question::{self as question, AcceptRequest};

fn failure(status: StatusCode, reason: &'static str) -> Response {
    (
        status,
        Json(json!({"code":"DEEPTUTOR_QUESTION_ACCEPT","reason":reason,
            "retryable":false})),
    )
        .into_response()
}

/// The domain's refusal text is a fixed internal phrase, never caller content,
/// so it can name which rule refused the acceptance.
fn invalid(message: &'static str) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({"code":"DEEPTUTOR_QUESTION_ACCEPT",
            "reason":"question_candidate_not_acceptable","retryable":false,
            "detail":message})),
    )
        .into_response()
}

/// Accept one candidate as a graded question. The same create ID reads the
/// accepted Document instead of asking again.
pub(super) async fn accept_candidate(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(request): Json<AcceptRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return failure(StatusCode::FORBIDDEN, "human_actor_required");
    }
    if question::accept_request_refusal(&request).is_some() {
        return failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "invalid_question_acceptance_request",
        );
    }
    let accepted = runtime
        .executor
        .store()
        .submit_wait({
            let request = request.clone();
            move |conn| question::accept_question_candidate(conn, &request)
        })
        .await;
    match accepted {
        Ok(Ok(receipt)) => (StatusCode::CREATED, Json(receipt)).into_response(),
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            failure(StatusCode::NOT_FOUND, "question_candidate_not_found")
        }
        Ok(Err(archeaxis_domain::document::Error::Invalid(message))) => invalid(message),
        Ok(Err(archeaxis_domain::document::Error::Conflict(_))) => {
            failure(StatusCode::CONFLICT, "question_candidate_not_acceptable")
        }
        _ => failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "question_acceptance_failed",
        ),
    }
}
