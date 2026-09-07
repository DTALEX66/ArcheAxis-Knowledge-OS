//! ArcheAxis vNext local HTTP API (thin projection over the domain crate).
//!
//! Aligns with `packages/contracts/v1/openapi-outline.yaml`. This is a Day-0
//! outline-compatible slice, not the final PR-04 contract (no multipart,
//! no full job orchestration). The standalone process wraps these internal
//! projections with launch authentication; `app` alone is for in-process use.

pub mod launch;
pub mod runtime;

use archeaxis_application::jobs::{self, LossReceipt};
use archeaxis_domain::{ImportOutcome, anchor, knowledge, learning, search, source};
use archeaxis_store_sqlite::{workspace_info_json, writer::{Store, StoreError}};
use axum::{
    Json, Router,
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    routing::{get, post},
};
use rusqlite::Connection;
use serde::Deserialize;

pub type AppState = Store;

/// Resolve the trusted actor for a request. Production requests go through
/// the launch middleware which OVERWRITES this header with the launch-session
/// claim (C02), so a client cannot escalate. In-process projections default to
/// human when the header is absent.
fn request_actor(headers: &HeaderMap) -> Result<&'static str, StatusCode> {
    match headers.get("x-archeaxis-actor").and_then(|v| v.to_str().ok()) {
        Some("machine") => Ok("machine"),
        Some("human") | None => Ok("human"),
        Some(_) => Err(StatusCode::BAD_REQUEST),
    }
}

/// Build the router over the managed single-writer runtime.
pub fn router(state: Store) -> Router {
    projections(state,true)
}

/// Legacy manual receipts are only retained for in-process compatibility tests.
pub fn projections(state: Store, manual_receipts: bool) -> Router {
    let routes=Router::new()
        .route("/api/v1/system/version", get(system_version))
        .route("/api/v1/imports", post(import_source))
        .route("/api/v1/jobs", post(enqueue_job))
        .route("/api/v1/sources/:source_id/anchors", post(create_anchor))
        .route("/api/v1/knowledge-items", post(create_knowledge))
        .route("/api/v1/knowledge-items/:id/qualification", get(knowledge_qualification))
        .route(
            "/api/v1/knowledge-items/:id/review-decisions",
            post(review_decision),
        )
        .route("/api/v1/learning/events", post(record_learning_event))
        .route("/api/v1/learning/events/:item_key", get(learning_history))
        .route("/api/v1/search", get(search_knowledge))
        .route("/api/v1/workspaces/info", get(workspace_info));
    let routes=if manual_receipts {routes.route("/api/v1/jobs/:job_id/receipts",post(job_receipt))}else{routes};
    routes.with_state(state)
}

/// Open an initialized workspace and return its router.
pub fn app(db_path: &str) -> Result<Router, StoreError> {
    Ok(router(Store::open(std::path::Path::new(db_path))?))
}

async fn with_store(state: Store, work: impl FnOnce(&mut Connection) -> axum::response::Response + Send + 'static) -> axum::response::Response {
    match state.submit(work).await {
        Ok(response) => response,
        Err(error) => (StatusCode::SERVICE_UNAVAILABLE, error.to_string()).into_response(),
    }
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
    #[serde(default)]
    origin_kind: Option<String>,
    #[serde(default)]
    origin_ref: Option<String>,
    #[serde(default)]
    origin_name: Option<String>,
    #[serde(default)]
    received_at: Option<String>,
}

const ALLOWED_ORIGIN_KINDS: &[&str] = &["path", "url", "import", "manual"];

async fn import_source(
    State(state): State<AppState>,
    Json(body): Json<ImportBody>,
) -> impl IntoResponse {
    let bytes = match base64_decode(&body.content_base64) {
        Some(b) => b,
        None => return (StatusCode::BAD_REQUEST, "invalid content_base64").into_response(),
    };
    let origin_kind = body.origin_kind;
    let origin_ref = body.origin_ref;
    let origin_name = body.origin_name;
    let received_at = body.received_at;
    match (&origin_kind, &origin_ref) {
        (Some(kind), Some(_)) if !ALLOWED_ORIGIN_KINDS.contains(&kind.as_str()) => {
            return (
                StatusCode::BAD_REQUEST,
                format!("unknown origin_kind '{kind}' (allowed: path|url|import|manual)"),
            )
                .into_response();
        }
        (Some(_), Some(_)) | (None, None) => {}
        _ => {
            return (
                StatusCode::BAD_REQUEST,
                "origin_kind and origin_ref must be provided together".into_response(),
            )
                .into_response();
        }
    }
    with_store(state, move |conn| {
    let origin = match (origin_kind.as_deref(), origin_ref.as_deref()) {
        (Some(kind), Some(origin_ref)) => Some(source::OriginInfo {
            kind,
            origin_ref,
            original_name: origin_name.as_deref(),
            received_at: received_at.as_deref(),
        }),
        _ => None,
    };
    match source::import_source_with_origin(conn, &bytes, &body.name, None, origin) {
        Ok(ImportOutcome::Imported { source_id, sha256 }) => (
            StatusCode::ACCEPTED,
            Json(serde_json::json!({"source_id": source_id, "sha256": sha256, "duplicate": false})),
        )
            .into_response(),
        Ok(ImportOutcome::Duplicate { source_id, sha256 }) => (
            StatusCode::ACCEPTED,
            Json(serde_json::json!({"source_id": source_id, "sha256": sha256, "duplicate": true})),
        )
            .into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
    }).await
}


async fn learning_history(
    State(state): State<AppState>,
    Path(item_key): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| match learning::events_for_item(conn, &item_key) {
        Ok(events) => {
            let rows: Vec<serde_json::Value> = events
                .into_iter()
                .map(|(event_id, kind, outcome, next_review)| {
                    serde_json::json!({
                        "event_id": event_id,
                        "kind": kind,
                        "outcome": outcome,
                        "next_review": next_review,
                    })
                })
                .collect();
            (
                StatusCode::OK,
                Json(serde_json::json!({"item_key": item_key, "events": rows, "count": rows.len()})),
            )
                .into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    })
    .await
}#[derive(Deserialize)]
struct LearningEventBody {
    item_key: String,
    #[serde(default = "default_learning_kind")]
    kind: String,
    correct: bool,
    #[serde(default)]
    client_event_id: Option<String>,
}

fn default_learning_kind() -> String {
    "review".to_string()
}

async fn record_learning_event(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<LearningEventBody>,
) -> impl IntoResponse {
    if body.item_key.trim().is_empty() {
        return (StatusCode::BAD_REQUEST, "item_key must be non-empty").into_response();
    }
    // C02: learning outcomes are human review events; machine principals must
    // not fabricate human learning history.
    if request_actor(&headers).unwrap_or("human") == "machine" {
        return (StatusCode::FORBIDDEN, "machine principal cannot record human learning outcomes")
            .into_response();
    }
    with_store(state, move |conn| match learning::record_review_keyed(
        conn,
        &body.item_key,
        &body.kind,
        body.correct,
        body.client_event_id.as_deref(),
    ) {
        Ok((event_id, streak_after, next_review_days)) => {
            let duplicate = next_review_days == -1;
            let status = if duplicate { StatusCode::OK } else { StatusCode::CREATED };
            (
                status,
                Json(serde_json::json!({
                    "event_id": event_id,
                    "streak_after": streak_after,
                    "next_review_days": if duplicate { serde_json::Value::Null } else { serde_json::json!(next_review_days) },
                    "duplicate": duplicate,
                })),
            )
                .into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    })
    .await
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
    with_store(state, move |conn| {
    match anchor::add_anchor(conn, &source_id, &body.revision, &body.position) {
        Ok(id) => (
            StatusCode::CREATED,
            Json(serde_json::json!({"anchor_id": id})),
        )
            .into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
    }).await
}

async fn knowledge_qualification(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| match knowledge::knowledge_status(conn, &id) {
        Ok(Some(_)) => (
            StatusCode::OK,
            Json(serde_json::json!({
                "knowledge_id": id,
                "exists": true,
                "active": knowledge::is_knowledge_active(conn, &id).unwrap_or(false),
            })),
        )
            .into_response(),
        Ok(None) => (StatusCode::NOT_FOUND, "knowledge not found").into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    })
    .await
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
    headers: HeaderMap,
    Json(body): Json<KnowledgeBody>,
) -> impl IntoResponse {
    // C02: actor comes from the trusted header (set by the launch middleware
    // from the launch-session claim), never from the request body.
    let actor = match request_actor(&headers) {
        Ok(actor) => actor,
        Err(status) => return (status, "unknown actor").into_response(),
    };
    let actor_ok = match actor {
        "human" => matches!(body.status.as_str(), "candidate" | "accepted"),
        _ => body.status == "candidate" && !body.created_by.trim().is_empty(),
    };
    if !actor_ok {
        return (
            StatusCode::BAD_REQUEST,
            "actor/status mismatch: machine content must start as candidate and cannot self-accept; use a review action for acceptance".to_string(),
        )
            .into_response();
    }
    with_store(state, move |conn| {
    match knowledge::create_knowledge(
        conn,
        &body.knowledge_type,
        &body.body,
        &body.status,
        None,
        None,
        &body.created_by,
    ) {
        Ok(id) => (
            StatusCode::CREATED,
            Json(serde_json::json!({"knowledge_id": id})),
        )
            .into_response(),
        Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
    }
    }).await
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
    headers: HeaderMap,
    Path(id): Path<String>,
    Json(body): Json<ReviewBody>,
) -> impl IntoResponse {
    // C02: acceptance/rejection/deprecation are human review actions; a
    // machine actor must not self-review its own proposals.
    if request_actor(&headers).unwrap_or("human") == "machine"
        && matches!(body.action.as_str(), "accepted" | "rejected" | "deprecated")
    {
        return (
            StatusCode::FORBIDDEN,
            "machine principal cannot perform human review actions",
        )
            .into_response();
    }
    with_store(state, move |conn| {
    match knowledge::review(
        conn,
        &id,
        &body.action,
        &body.reviewer,
        body.note.as_deref(),
        None,
    ) {
        Ok(kid) => (
            StatusCode::OK,
            Json(serde_json::json!({"knowledge_id": kid})),
        )
            .into_response(),
        Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
    }
    }).await
}

#[derive(Deserialize)]
struct SearchQuery {
    q: String,
    #[serde(default)]
    active_only: bool,
}

async fn search_knowledge(
    State(state): State<AppState>,
    Query(query): Query<SearchQuery>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
    match search::search(conn, &query.q, 20) {
        Ok(rows) => {
            let mut items: Vec<serde_json::Value> = rows
                .into_iter()
                .map(|(id, status, head)| {
                    let active = knowledge::is_knowledge_active(conn, &id).unwrap_or(false);
                    serde_json::json!({"knowledge_id": id, "status": status, "head": head, "active": active})
                })
                .collect();
            if query.active_only {
                items.retain(|item| item["active"] == true);
            }
            Json(serde_json::json!({"count": items.len(), "items": items})).into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
    }).await
}

async fn workspace_info(State(state): State<AppState>) -> impl IntoResponse {
    with_store(state, move |conn| {
    match workspace_info_json(conn) {
        Ok(s) => {
            let v: serde_json::Value = serde_json::from_str(&s).unwrap_or(serde_json::json!({}));
            Json(v).into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
    }).await
}

fn base64_decode(s: &str) -> Option<Vec<u8>> {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.decode(s).ok()
}

// 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞?worker job endpoints (worker-protocol slice) 闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾婚柟鍓х帛閻撳啴鏌涜箛鎿冩Ц濞存粓绠栧娲礃閹绘帒杈呴梺绋款儐閹瑰洭寮诲澶婄濠㈣泛锕ｆ竟鏇㈡⒒娴ｇ鏆遍柛妯荤矒瀹曟垿骞樼紒妯煎帗闂佺绻愰ˇ顖涚妤ｅ啯鈷戦柛鎰絻鐢劑鏌涚€ｎ偅宕岄柡灞界Ч瀹曟寰勬繝浣割棜闂傚倷绀侀崯鍧楀储濠婂牆纾?
#[derive(Deserialize)]
struct EnqueueBody {
    job_id: String,
    kind: String,
    input_ref: String,
}

async fn enqueue_job(
    State(state): State<AppState>,
    Json(body): Json<EnqueueBody>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
    match jobs::enqueue(conn, &body.job_id, &body.kind, &body.input_ref) {
        Ok(()) => match jobs::job_state(conn, &body.job_id) {
            Ok(Some(actual)) => (StatusCode::ACCEPTED,
                Json(serde_json::json!({"job_id": body.job_id, "state": actual}))).into_response(),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, "job readback failed").into_response(),
        },
        Err(e) => job_error_response(e),
    }
    }).await
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ReceiptBody {
    #[serde(default = "default_state")]
    state: String, // succeeded | failed (canonical job-status vocabulary)
    #[serde(default)]
    engine: Option<String>,
    #[serde(default)]
    text: Option<String>,
    #[serde(default)]
    loss_receipt: Option<LossReceipt>,
    #[serde(default)]
    error: Option<String>,
}

fn job_error_response(error: jobs::JobError) -> axum::response::Response {
    let status = match &error {
        jobs::JobError::NotFound => StatusCode::NOT_FOUND,
        jobs::JobError::Conflict | jobs::JobError::InvalidState => StatusCode::CONFLICT,
        jobs::JobError::Sql(_) => StatusCode::INTERNAL_SERVER_ERROR,
        jobs::JobError::InvalidReceipt(_) => StatusCode::BAD_REQUEST,
    };
    (status, error.to_string()).into_response()
}

fn default_state() -> String {
    jobs::STATE_COMPLETED.to_string()
}

async fn job_receipt(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
    Json(body): Json<ReceiptBody>,
) -> impl IntoResponse {
    if body.state != jobs::STATE_COMPLETED && body.state != jobs::STATE_FAILED {
        return (StatusCode::BAD_REQUEST, "invalid terminal job state").into_response();
    }
    if body.state == jobs::STATE_COMPLETED && (body.engine.is_none() || body.text.is_none()) {
        return (StatusCode::BAD_REQUEST, "successful receipt requires engine and text").into_response();
    }
    if body.state == jobs::STATE_COMPLETED && body.error.is_some() {
        return (StatusCode::BAD_REQUEST, "successful receipt cannot contain an error").into_response();
    }
    if body.state == jobs::STATE_FAILED && (body.text.is_some() || body.loss_receipt.is_some() || body.engine.is_some()) {
        return (StatusCode::BAD_REQUEST, "failed receipt cannot publish output").into_response();
    }
    with_store(state, move |conn| {
    let out = if body.state == "failed" {
        jobs::fail(
            conn,
            &job_id,
            body.error.as_deref().unwrap_or("unspecified"),
        )
    } else {
        jobs::complete(
            conn,
            &job_id,
            body.engine.as_deref().unwrap_or("worker"),
            body.text.as_deref().unwrap_or(""),
            body.loss_receipt.as_ref(),
        )
    };
    match out {
        Ok(()) => (
            StatusCode::OK,
            Json(serde_json::json!({"job_id": job_id, "state": body.state})),
        )
            .into_response(),
        Err(e) => job_error_response(e),
    }
    }).await
}
