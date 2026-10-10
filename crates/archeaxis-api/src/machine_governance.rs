//! Finite product-context and human machine-evaluation commands.
use crate::AppState;
use archeaxis_domain::machine_evaluation::{self, EvaluationRequest, Rubric};
use axum::{
    Json,
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use serde::Deserialize;
use serde_json::json;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PageQuery {
    cursor: Option<String>,
}
async fn list(state: AppState, query: PageQuery, namespace: &'static str) -> Response {
    if query.cursor.as_ref().is_some_and(|s| {
        s.is_empty()
            || s.len() > 256
            || !s
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.'))
    }) {
        return (StatusCode::BAD_REQUEST, "invalid machine document cursor").into_response();
    }
    crate::with_store(state,move |conn| {
        let read = (|| -> rusqlite::Result<_> {
            let mut stmt=conn.prepare("SELECT d.document_id,d.title,d.current_version,v.content_sha256
                FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version
                WHERE json_type(v.editor_json,?1) IS NOT NULL AND (?2 IS NULL OR d.document_id>?2)
                ORDER BY d.document_id LIMIT 21")?;
            let mut rows=stmt.query_map(rusqlite::params![format!("$.attrs.{namespace}"),query.cursor],|r|
                Ok(json!({"document_id":r.get::<_,String>(0)?,"title":r.get::<_,String>(1)?,"version":r.get::<_,i64>(2)?,"content_sha256":r.get::<_,String>(3)?})))?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            let more=rows.len()>20;rows.truncate(20);
            let cursor=if more {rows.last().map(|row|row["document_id"].clone())} else {None};
            Ok(json!({"items":rows,"next_cursor":cursor}))
        })();
        match read {Ok(page)=>Json(page).into_response(),Err(e)=>crate::documents::failure(e.into())}
    }).await
}
pub(crate) async fn contexts(
    State(state): State<AppState>,
    Query(query): Query<PageQuery>,
) -> Response {
    list(state, query, "archeaxis_context_grant").await
}
pub(crate) async fn rubrics(
    State(state): State<AppState>,
    Query(query): Query<PageQuery>,
) -> Response {
    list(state, query, machine_evaluation::RUBRIC_NAMESPACE).await
}
pub(crate) async fn evaluations(
    State(state): State<AppState>,
    Query(query): Query<PageQuery>,
) -> Response {
    list(state, query, machine_evaluation::EVALUATION_NAMESPACE).await
}
pub(crate) async fn create_rubric(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<Rubric>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| {
        match machine_evaluation::create_rubric(conn, "human", &body) {
            Ok(document) => (StatusCode::CREATED, Json(document)).into_response(),
            Err(e) => crate::documents::failure(e),
        }
    })
    .await
}
pub(crate) async fn create_evaluation(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<EvaluationRequest>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(
        state,
        move |conn| match machine_evaluation::create_evaluation(conn, "human", &body) {
            Ok(document) => (StatusCode::CREATED, Json(document)).into_response(),
            Err(e) => crate::documents::failure(e),
        },
    )
    .await
}
pub(crate) async fn answer_snapshot(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Response {
    crate::with_store(
        state,
        move |conn| match machine_evaluation::answer_snapshot(conn, &id) {
            Ok(snapshot) => Json(snapshot).into_response(),
            Err(e) => crate::documents::failure(e),
        },
    )
    .await
}

pub(crate) async fn assets(
    State(state): State<AppState>,
    Query(query): Query<PageQuery>,
) -> Response {
    list(state, query, archeaxis_domain::ai_asset::NAMESPACE).await
}
pub(crate) async fn asset_packet(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<archeaxis_domain::asset_context_grant::PacketRequest>,
) -> Response {
    use archeaxis_domain::{
        asset_context_grant::{self, Consumer},
        document::Error,
    };
    let consumer = match crate::request_actor(&headers) {
        Ok("human") => Consumer::ManualContextPacket,
        Ok("machine") => Consumer::LocalMachine,
        _ => return StatusCode::FORBIDDEN.into_response(),
    };
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(u64::MAX);
    crate::with_store(
        state,
        move |conn| match asset_context_grant::prepare_packet(conn, &body, consumer, now) {
            Ok(packet) => Json(packet).into_response(),
            Err(Error::Invalid(
                "client request identity already has a different frozen packet",
            )) => StatusCode::CONFLICT.into_response(),
            Err(Error::Invalid(_)) | Err(Error::NotFound) => StatusCode::FORBIDDEN.into_response(),
            Err(other) => crate::documents::failure(other),
        },
    )
    .await
}
