use super::*;
use archeaxis_domain::character_memory as memory;
fn result<T: serde::Serialize>(
    r: Result<rusqlite::Result<T>, archeaxis_store_sqlite::writer::StoreError>,
) -> Response {
    match r {
        Ok(Ok(v)) => Json(json!(v)).into_response(),
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
            Json(json!({"error":"MEMORY_UNAVAILABLE"})),
        )
            .into_response(),
    }
}
pub async fn get(State(r): State<Runtime>, h: HeaderMap) -> Response {
    if crate::request_actor(&h) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    result(r.executor.store().submit_wait(|c| memory::read(c)).await)
}
pub async fn apply(
    State(r): State<Runtime>,
    h: HeaderMap,
    Json(w): Json<memory::Write>,
) -> Response {
    if crate::request_actor(&h) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    result(
        r.executor
            .store()
            .submit_wait(move |c| memory::apply(c, w))
            .await,
    )
}
pub async fn context(State(r): State<Runtime>) -> Response {
    result(r.executor.store().submit_wait(|c| memory::context(c)).await)
}
pub async fn export(State(r): State<Runtime>, h: HeaderMap) -> Response {
    if crate::request_actor(&h) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    result(r.executor.store().submit_wait(|c|memory::read(c).map(|p|json!({"schema":"archeaxis.memory-export/v1","profile":p,"contains_personal_memory":true,"network_performed":false}))).await)
}
