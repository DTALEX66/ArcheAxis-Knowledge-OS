//! Human-authorized, offline packet import, not provider connectivity or sessions.
use crate::AppState;
use archeaxis_domain::external_context::{self as domain, Admission, Candidate};
use axum::{
    Json,
    extract::State,
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Import {
    candidate: Candidate,
    material_authorized: bool,
    redaction_confirmed: bool,
}
pub(crate) async fn status() -> Json<serde_json::Value> {
    Json(domain::contract())
}
pub(crate) async fn receive(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<Import>,
) -> Response {
    // Launch middleware binds the actor; packet data never grants machine access.
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| {
        let c = &body.candidate;
        let a = Admission {
            provider_id: &c.source.provider_id,
            project_id: &c.source.project_id,
            auth_scope: "knowledge_candidate:import",
            material_authorized: body.material_authorized,
            redaction_confirmed: body.redaction_confirmed,
        };
        match domain::receive(conn, c, &a) {
            Ok(d) => (StatusCode::CREATED, Json(d)).into_response(),
            Err(e) => crate::documents::failure(e),
        }
    })
    .await
}
