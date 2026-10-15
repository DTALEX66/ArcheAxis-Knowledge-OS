use super::*;
use archeaxis_domain::model_configuration::{self as config, Configuration, Lane, Purpose};
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Put {
    pub expected_revision: u64,
    pub configuration: Configuration,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Resolve {
    pub purpose: Purpose,
    pub lane: Lane,
}
fn response<T: serde::Serialize>(
    result: Result<rusqlite::Result<T>, archeaxis_store_sqlite::writer::StoreError>,
) -> Response {
    match result {
        Ok(Ok(value)) => Json(json!(value)).into_response(),
        Ok(Err(rusqlite::Error::InvalidParameterName(code))) => (
            if code.ends_with("CONFLICT") {
                StatusCode::CONFLICT
            } else {
                StatusCode::UNPROCESSABLE_ENTITY
            },
            Json(json!({"error":code})),
        )
            .into_response(),
        _ => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error":"MODEL_CONFIGURATION_UNAVAILABLE"})),
        )
            .into_response(),
    }
}
pub async fn get(State(runtime): State<Runtime>) -> Response {
    response(
        runtime
            .executor
            .store()
            .submit_wait(|c| config::read(c))
            .await,
    )
}
pub async fn put(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<Put>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    response(
        runtime
            .executor
            .store()
            .submit_wait(move |c| config::put(c, body.expected_revision, body.configuration))
            .await,
    )
}
pub async fn resolve(State(runtime): State<Runtime>, Json(body): Json<Resolve>) -> Response {
    response(
        runtime
            .executor
            .store()
            .submit_wait(move |c| config::resolve(c, body.purpose, body.lane))
            .await,
    )
}
