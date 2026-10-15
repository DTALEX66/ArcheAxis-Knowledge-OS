//! Device preferences use the canonical Store writer and human actor.
use crate::AppState;
use archeaxis_domain::{
    layout::{self, Recover, Snapshot, Write},
    ui_state::Error,
};
use axum::{
    Json,
    extract::{Query, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use serde::Deserialize;
use serde_json::json;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Read {
    device_id: String,
}
fn response(value: Result<Snapshot, Error>) -> Response {
    match value {
        Ok(value) => Json(value).into_response(),
        Err(Error::Conflict) => (
            StatusCode::CONFLICT,
            Json(json!({"error":"LAYOUT_CONFLICT"})),
        )
            .into_response(),
        Err(Error::Invalid(reason)) => (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"error":"LAYOUT_INVALID","reason":reason})),
        )
            .into_response(),
        Err(Error::Store(_)) => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({"error":"LAYOUT_STORE_UNAVAILABLE"})),
        )
            .into_response(),
    }
}
pub(crate) async fn read(
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(input): Query<Read>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| {
        response(layout::read(conn, &input.device_id))
    })
    .await
}
pub(crate) async fn write(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(input): Json<Write>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| response(layout::write(conn, input))).await
}
pub(crate) async fn recover(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(input): Json<Recover>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| response(layout::recover(conn, input))).await
}
