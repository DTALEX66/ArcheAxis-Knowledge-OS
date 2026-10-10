//! Versioned manual teaching metadata over the existing canonical single writer.
use crate::{AppState, with_store};
use archeaxis_domain::teaching::{self, ExchangeBundle, TeachingError, TeachingRecord, Withdrawal};
use axum::{
    Json,
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use serde::Deserialize;

fn human(headers: &HeaderMap) -> bool {
    // Production launch middleware overwrites this header from its trusted session.
    // Missing/malformed in-process headers are never silently promoted to human.
    headers
        .get("x-archeaxis-actor")
        .and_then(|v| v.to_str().ok())
        == Some("human")
}
fn denied() -> Response {
    (
        StatusCode::FORBIDDEN,
        Json(serde_json::json!({"error":"teaching action requires a trusted human actor"})),
    )
        .into_response()
}
fn failure(error: TeachingError) -> Response {
    let (status, detail) = match error {
        TeachingError::Invalid(message) => (StatusCode::UNPROCESSABLE_ENTITY, message),
        TeachingError::NotFound(message) => (StatusCode::NOT_FOUND, message),
        TeachingError::Conflict(message) | TeachingError::Withdrawn(message) => {
            (StatusCode::CONFLICT, message)
        }
        TeachingError::Storage(_) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            "teaching workspace operation failed".into(),
        ),
    };
    (status, Json(serde_json::json!({"error":detail}))).into_response()
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ListQuery {
    cursor: Option<String>,
}
pub(crate) async fn list(
    State(state): State<AppState>,
    Query(query): Query<ListQuery>,
) -> Response {
    with_store(state, move |conn| {
        match teaching::list(conn, query.cursor.as_deref()) {
            Ok(page) => Json(page).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
pub(crate) async fn read(State(state): State<AppState>, Path(id): Path<String>) -> Response {
    with_store(state, move |conn| match teaching::get(conn, &id) {
        Ok(Some(item)) => Json(item).into_response(),
        Ok(None) => failure(TeachingError::NotFound("teaching record not found".into())),
        Err(error) => failure(error),
    })
    .await
}
pub(crate) async fn create(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<TeachingRecord>,
) -> Response {
    if !human(&headers) {
        return denied();
    }
    with_store(state, move |conn| match teaching::put(conn, &body) {
        Ok(receipt) => (
            if receipt.duplicate {
                StatusCode::OK
            } else {
                StatusCode::CREATED
            },
            Json(receipt),
        )
            .into_response(),
        Err(error) => failure(error),
    })
    .await
}
pub(crate) async fn withdraw(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<Withdrawal>,
) -> Response {
    if !human(&headers) {
        return denied();
    }
    with_store(state, move |conn| match teaching::withdraw(conn, &body) {
        Ok(receipt) => (
            if receipt.duplicate {
                StatusCode::OK
            } else {
                StatusCode::CREATED
            },
            Json(receipt),
        )
            .into_response(),
        Err(error) => failure(error),
    })
    .await
}
pub(crate) async fn export(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<String>,
) -> Response {
    if !human(&headers) {
        return denied();
    }
    with_store(state, move |conn| {
        match teaching::export_bundle(conn, &id) {
            Ok(bundle) => Json(bundle).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
pub(crate) async fn preview(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<ExchangeBundle>,
) -> Response {
    if !human(&headers) {
        return denied();
    }
    with_store(state, move |conn| {
        match teaching::preview_import(conn, &body) {
            Ok(preview) => Json(preview).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
pub(crate) async fn import(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<ExchangeBundle>,
) -> Response {
    if !human(&headers) {
        return denied();
    }
    with_store(state, move |conn| {
        match teaching::import_bundle(conn, &body) {
            Ok(receipt) => (
                if receipt.duplicate_count == receipt.items.len() {
                    StatusCode::OK
                } else {
                    StatusCode::CREATED
                },
                Json(receipt),
            )
                .into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
