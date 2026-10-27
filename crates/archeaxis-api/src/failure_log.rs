//! Human-only safe metadata, submitted exclusively to the Core Store writer.
use crate::AppState;
use archeaxis_domain::failure_log::{self, Append, Clear, Error, Scope};
use axum::{
    Json,
    extract::State,
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use serde_json::json;
fn result(value: Result<serde_json::Value, Error>) -> Response {
    match value {
        Ok(value) => Json(value).into_response(),
        Err(error) => {
            let (status, code) = match error {
                Error::Invalid => (StatusCode::UNPROCESSABLE_ENTITY, "FAILURE_LOG_INVALID"),
                Error::ScopeChanged => (StatusCode::CONFLICT, "FAILURE_LOG_SCOPE_CHANGED"),
                Error::GenerationChanged => {
                    (StatusCode::CONFLICT, "FAILURE_LOG_GENERATION_CHANGED")
                }
                Error::Corrupt => (StatusCode::CONFLICT, "FAILURE_LOG_CORRUPT"),
                Error::Store(_) => (StatusCode::SERVICE_UNAVAILABLE, "FAILURE_LOG_UNAVAILABLE"),
            };
            (status, Json(json!({"error":code}))).into_response()
        }
    }
}
macro_rules! endpoint {
    ($name:ident,$input:ty) => {
        pub(crate) async fn $name(
            State(state): State<AppState>,
            headers: HeaderMap,
            Json(input): Json<$input>,
        ) -> Response {
            if crate::request_actor(&headers) != Ok("human") {
                return StatusCode::FORBIDDEN.into_response();
            }
            crate::with_store(state, move |conn| result(failure_log::$name(conn, input))).await
        }
    };
}
endpoint!(read, Scope);
endpoint!(append, Append);
endpoint!(clear, Clear);
