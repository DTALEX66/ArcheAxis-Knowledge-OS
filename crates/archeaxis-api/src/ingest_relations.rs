//! A finite original-CAS adapter, through the same Store and Document writer.
use crate::AppState;
use axum::{
    Json,
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
pub(crate) async fn apply(
    State(state): State<AppState>,
    Path((batch, ordinal)): Path<(String, i64)>,
    headers: HeaderMap,
    Json(body): Json<archeaxis_domain::ingest_relations::Apply>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(
        state,
        move |conn| match archeaxis_domain::ingest_relations::apply(conn, &batch, ordinal, body) {
            Ok(value) => Json(value).into_response(),
            Err(error) => {
                use archeaxis_domain::{document::Error as DocError, ingest_relations::Error};
                match error {
                    Error::ScopeConflict => (StatusCode::CONFLICT, Json(serde_json::json!({"code":"AAK-INGEST-RELATION-001","message":"workspace/restore identity or complete manifest changed"}))).into_response(),
                    Error::Invalid(m) => crate::documents::failure(DocError::Invalid(m)),
                    Error::NotFound => crate::documents::failure(DocError::NotFound),
                    Error::Conflict(v) => crate::documents::failure(DocError::Conflict(v)),
                    Error::Sql(e) => crate::documents::failure(DocError::Sql(e)),
                }
            },
        },
    )
    .await
}
