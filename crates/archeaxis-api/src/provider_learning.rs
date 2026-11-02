//! Finite, Core-owned practice observations; no provider invocation occurs here.
use crate::{AppState, request_actor, with_store};
use archeaxis_domain::provider_learning::{self as learning, Activity, Cancel, Start, Submission};
use archeaxis_domain::{document, provider_material_grant::Snapshot, provider_question};
use axum::{
    Json,
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use serde::Deserialize;
use serde_json::{Value, json};

fn allowed(headers: &HeaderMap) -> Result<(), Response> {
    match request_actor(headers) {
        Ok("human") => Ok(()),
        Ok(_) => Err((
            StatusCode::FORBIDDEN,
            Json(json!({"reason":"human_actor_required"})),
        )
            .into_response()),
        Err(status) => Err((status, Json(json!({"reason":"invalid_actor"}))).into_response()),
    }
}
fn result(value: std::result::Result<Value, learning::Error>) -> Response {
    match value {
        Ok(body) => {
            let status = if body["duplicate"] == true {
                StatusCode::OK
            } else {
                StatusCode::CREATED
            };
            (status, Json(body)).into_response()
        }
        Err(learning::Error::Invalid(reason)) => (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"reason":reason})),
        )
            .into_response(),
        Err(learning::Error::NotFound) => (
            StatusCode::NOT_FOUND,
            Json(json!({"reason":"practice_object_not_found"})),
        )
            .into_response(),
        Err(learning::Error::Conflict(reason)) => {
            (StatusCode::CONFLICT, Json(json!({"reason":reason}))).into_response()
        }
        Err(learning::Error::Storage(_)) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"reason":"practice_storage_unavailable"})),
        )
            .into_response(),
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct QuestionView {
    question_document: Snapshot,
}

/// Local candidate projection only; it neither authorizes nor invokes DeepTutor.
pub(crate) async fn question_view(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<QuestionView>,
) -> Response {
    if let Err(response) = allowed(&headers) {
        return response;
    }
    with_store(state, move |conn| {
        match provider_question::read_view(conn, &body.question_document) {
            Ok(value) => Json(value).into_response(),
            Err(document::Error::NotFound) => (
                StatusCode::NOT_FOUND,
                Json(json!({"reason":"question_document_not_found"})),
            )
                .into_response(),
            Err(document::Error::Invalid(_)) | Err(document::Error::Conflict(_)) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(json!({"reason":"question_candidate_unavailable"})),
            )
                .into_response(),
            Err(document::Error::Sql(_)) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"reason":"question_storage_unavailable"})),
            )
                .into_response(),
        }
    })
    .await
}
pub(crate) async fn create(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<Activity>,
) -> Response {
    if let Err(response) = allowed(&headers) {
        return response;
    }
    with_store(state, move |conn| result(learning::create(conn, &body))).await
}
pub(crate) async fn start(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<String>,
    Json(body): Json<Start>,
) -> Response {
    if let Err(response) = allowed(&headers) {
        return response;
    }
    with_store(state, move |conn| result(learning::start(conn, &id, &body))).await
}
pub(crate) async fn submit(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path((activity, id)): Path<(String, String)>,
    Json(body): Json<Submission>,
) -> Response {
    if let Err(response) = allowed(&headers) {
        return response;
    }
    with_store(state, move |conn| {
        result(learning::submit(conn, &activity, &id, &body))
    })
    .await
}
pub(crate) async fn cancel(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path((activity, id)): Path<(String, String)>,
    Json(body): Json<Cancel>,
) -> Response {
    if let Err(response) = allowed(&headers) {
        return response;
    }
    with_store(state, move |conn| {
        result(learning::cancel(conn, &activity, &id, &body))
    })
    .await
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct HistoryQuery {
    after_attempt_id: Option<String>,
}
pub(crate) async fn read(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<String>,
    Query(query): Query<HistoryQuery>,
) -> Response {
    if let Err(response) = allowed(&headers) {
        return response;
    }
    with_store(state, move |conn| {
        match learning::read(conn, &id, query.after_attempt_id.as_deref()) {
            Ok(mut body) => {
                attach_grade_dispositions(conn, &id, &mut body);
                Json(body).into_response()
            }
            Err(error) => result(Err(error)),
        }
    })
    .await
}

/// Attach the durable grading disposition to each attempt that has one.
///
/// This is a read-only projection of Core-owned metadata: the attempt and its
/// ordinary result stay untouched, and an attempt without a grading claim gets no
/// field. It never launches, retries or changes a claim.
fn attach_grade_dispositions(conn: &rusqlite::Connection, activity_id: &str, body: &mut Value) {
    let Some(attempts) = body.get_mut("attempts").and_then(Value::as_array_mut) else {
        return;
    };
    for attempt in attempts.iter_mut() {
        let Some(attempt_id) = attempt
            .get("attempt_id")
            .and_then(Value::as_str)
            .map(str::to_owned)
        else {
            continue;
        };
        if let Ok(Some(grade_disposition)) =
            learning::grade::disposition(conn, activity_id, &attempt_id)
        {
            if let Some(object) = attempt.as_object_mut() {
                object.insert("grade_disposition".into(), grade_disposition);
            }
        }
    }
}
