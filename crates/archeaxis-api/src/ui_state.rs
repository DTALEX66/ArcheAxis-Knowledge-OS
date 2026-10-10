//! Human-only Core working-state endpoints; every operation is submitted to the Store writer.
use crate::AppState;
use archeaxis_domain::ui_state::{self, ClearSaved, Error, Recover, Write};
use axum::{Json, extract::State, http::{HeaderMap, StatusCode}, response::{IntoResponse, Response}};
use serde_json::json;

fn human(headers: &HeaderMap) -> bool { crate::request_actor(headers) == Ok("human") }
fn result(conn: &mut rusqlite::Connection, value: Result<serde_json::Value, Error>) -> Response {
    match value {
        Ok(body) => Json(body).into_response(),
        Err(Error::Invalid(reason)) => (StatusCode::UNPROCESSABLE_ENTITY,Json(json!({"error":"UI_STATE_INVALID","reason":reason}))).into_response(),
        Err(Error::Store(_)) => (StatusCode::SERVICE_UNAVAILABLE,Json(json!({"error":"UI_STATE_STORE_UNAVAILABLE"}))).into_response(),
        Err(Error::Conflict) => {
            let current = ui_state::read(conn);
            match current {
                Ok(value) => (StatusCode::CONFLICT,Json(json!({"error":"UI_STATE_CONFLICT","workspace_id":value["workspace_id"],"restore_epoch":value["restore_epoch"],"state_revision":value["state_revision"]}))).into_response(),
                Err(_) => (StatusCode::SERVICE_UNAVAILABLE,Json(json!({"error":"UI_STATE_READBACK_UNAVAILABLE"}))).into_response(),
            }
        }
    }
}
pub(crate) async fn read(State(state): State<AppState>, headers: HeaderMap) -> Response {
    if !human(&headers) { return StatusCode::FORBIDDEN.into_response(); }
    crate::with_store(state, move |conn| { let value = ui_state::read(conn); result(conn,value) }).await
}
pub(crate) async fn write(State(state): State<AppState>, headers: HeaderMap, Json(input): Json<Write>) -> Response {
    if !human(&headers) { return StatusCode::FORBIDDEN.into_response(); }
    crate::with_store(state, move |conn| { let value = ui_state::write(conn,input); result(conn,value) }).await
}
pub(crate) async fn clear_saved(State(state): State<AppState>, headers: HeaderMap, Json(input): Json<ClearSaved>) -> Response {
    if !human(&headers) { return StatusCode::FORBIDDEN.into_response(); }
    crate::with_store(state, move |conn| { let value = ui_state::clear_saved(conn,input); result(conn,value) }).await
}
pub(crate) async fn recover(State(state): State<AppState>, headers: HeaderMap, Json(input): Json<Recover>) -> Response {
    if !human(&headers) { return StatusCode::FORBIDDEN.into_response(); }
    crate::with_store(state, move |conn| { let value = ui_state::recover(conn,input); result(conn,value) }).await
}
