//! ArcheAxis vNext local HTTP API (thin projection over the domain crate).
//!
//! Aligns with `packages/contracts/v1/openapi-outline.yaml`. This is a Day-0
//! outline-compatible slice, not the final PR-04 contract (no multipart,
//! no job orchestration, no launch-token auth yet).

use std::sync::{Arc, Mutex};

use archeaxis_domain::{anchor, knowledge, search, source, ImportOutcome};
use archeaxis_store_sqlite::{init_workspace, workspace_info_json};
use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use rusqlite::Connection;
use serde::Deserialize;

pub type AppState = Arc<Mutex<Connection>>;

/// Build the router over an existing (initialized) connection.
pub fn router(conn: Connection) -> Router {
    let state: AppState = Arc::new(Mutex::new(conn));
    Router::new()
        .route("/api/v1/system/version", get(system_version))
        .route("/api/v1/imports", post(import_source))
        .route("/api/v1/sources/:source_id/anchors", post(create_anchor))
        .route("/api/v1/knowledge-items", post(create_knowledge))
        .route("/api/v1/knowledge-items/:id/review-decisions", post(review_decision))
        .route("/api/v1/search", get(search_knowledge))
        .route("/api/v1/workspaces/info", get(workspace_info))
        .with_state(state)
}

/// Open an initialized workspace and return its router.
pub fn app(db_path: &str) -> Result<Router, rusqlite::Error> {
    let conn = init_workspace(db_path)?;
    Ok(router(conn))
}

async fn system_version() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "runtime": "archeaxis-api",
        "contract": "0.1.0-outline",
        "schema_version": archeaxis_store_sqlite::SCHEMA_VERSION,
    }))
}

#[derive(Deserialize)]
struct ImportBody {
    name: String,
    #[serde(default)]
    content_base64: String,
}

async fn import_source(
    State(state): State<AppState>,
    Json(body): Json<ImportBody>,
) -> impl IntoResponse {
    let bytes = match base64_decode(&body.content_base64) {
        Some(b) => b,
        None => return (StatusCode::BAD_REQUEST, "invalid content_base64").into_response(),
    };
    let mut conn = state.lock().unwrap();
    match source::import_source(&mut conn, &bytes, &body.name, None) {
        Ok(ImportOutcome::Imported { source_id, sha256 }) => (
            StatusCode::ACCEPTED,
            Json(serde_json::json!({"source_id": source_id, "sha256": sha256, "duplicate": false})),
        ).into_response(),
        Ok(ImportOutcome::Duplicate { source_id, sha256 }) => (
            StatusCode::ACCEPTED,
            Json(serde_json::json!({"source_id": source_id, "sha256": sha256, "duplicate": true})),
        ).into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

#[derive(Deserialize)]
struct AnchorBody {
    revision: String,
    position: String,
}

async fn create_anchor(
    State(state): State<AppState>,
    Path(source_id): Path<String>,
    Json(body): Json<AnchorBody>,
) -> impl IntoResponse {
    let mut conn = state.lock().unwrap();
    match anchor::add_anchor(&mut conn, &source_id, &body.revision, &body.position) {
        Ok(id) => (StatusCode::CREATED, Json(serde_json::json!({"anchor_id": id}))).into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

#[derive(Deserialize)]
struct KnowledgeBody {
    knowledge_type: String,
    body: String,
    #[serde(default = "default_status")]
    status: String,
    #[serde(default)]
    created_by: String,
}

fn default_status() -> String {
    "candidate".to_string()
}

async fn create_knowledge(
    State(state): State<AppState>,
    Json(body): Json<KnowledgeBody>,
) -> impl IntoResponse {
    let mut conn = state.lock().unwrap();
    match knowledge::create_knowledge(
        &mut conn, &body.knowledge_type, &body.body, &body.status, None, None, &body.created_by,
    ) {
        Ok(id) => (StatusCode::CREATED, Json(serde_json::json!({"knowledge_id": id}))).into_response(),
        Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
    }
}

#[derive(Deserialize)]
struct ReviewBody {
    action: String,
    reviewer: String,
    #[serde(default)]
    note: Option<String>,
}

async fn review_decision(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(body): Json<ReviewBody>,
) -> impl IntoResponse {
    let mut conn = state.lock().unwrap();
    match knowledge::review(&mut conn, &id, &body.action, &body.reviewer, body.note.as_deref(), None) {
        Ok(kid) => (StatusCode::OK, Json(serde_json::json!({"knowledge_id": kid}))).into_response(),
        Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
    }
}

#[derive(Deserialize)]
struct SearchQuery {
    q: String,
}

async fn search_knowledge(
    State(state): State<AppState>,
    Query(query): Query<SearchQuery>,
) -> impl IntoResponse {
    let conn = state.lock().unwrap();
    match search::search(&conn, &query.q, 20) {
        Ok(rows) => {
            let items: Vec<serde_json::Value> = rows
                .into_iter()
                .map(|(id, status, head)| serde_json::json!({"knowledge_id": id, "status": status, "head": head}))
                .collect();
            Json(serde_json::json!({"count": items.len(), "items": items})).into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

async fn workspace_info(State(state): State<AppState>) -> impl IntoResponse {
    let conn = state.lock().unwrap();
    match workspace_info_json(&conn) {
        Ok(s) => {
            let v: serde_json::Value = serde_json::from_str(&s).unwrap_or(serde_json::json!({}));
            Json(v).into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

fn base64_decode(s: &str) -> Option<Vec<u8>> {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.decode(s).ok()
}
