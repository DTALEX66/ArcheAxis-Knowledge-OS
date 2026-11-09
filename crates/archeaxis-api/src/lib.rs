//! ArcheAxis vNext local HTTP API (thin projection over the domain crate).
//!
//! Aligns with `packages/contracts/v1/openapi-outline.yaml`. This is a Day-0
//! outline-compatible slice, not the final PR-04 contract (no multipart,
//! no full job orchestration). The standalone process wraps these internal
//! projections with launch authentication; `app` alone is for in-process use.

mod anchor_resolution;
pub mod ask;
pub mod capabilities;
mod documents;
mod external_context;
mod failure_log;
mod format_qualification;
mod ingest_batches;
mod ingest_relations;
pub mod launch;
mod layout;
mod machine_governance;
mod ocr_locator;
mod pdf_locator;
pub mod project_handoff;
mod project_handoff_preview;
pub mod project_observer;
mod provider_learning;
pub mod runtime;
pub mod session_shutdown;
mod teaching;
mod ui_state;
mod workspace_backup;

use archeaxis_application::container;
use archeaxis_application::jobs::{self, LossReceipt};
use archeaxis_domain::{
    ImportOutcome, anchor, knowledge, learning, machine, object_reference, search, source,
};
use archeaxis_store_sqlite::{
    workspace_info_json,
    writer::{Store, StoreError},
};
use axum::{
    Json, Router,
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    routing::{get, post, put},
};
use rusqlite::{Connection, OptionalExtension};
use serde::Deserialize;

pub type AppState = Store;

/// Resolve the trusted actor for a request. Production requests go through
/// the launch middleware which OVERWRITES this header with the launch-session
/// claim (C02), so a client cannot escalate. In-process projections default to
/// human when the header is absent.
pub(crate) fn request_actor(headers: &HeaderMap) -> Result<&'static str, StatusCode> {
    match headers
        .get("x-archeaxis-actor")
        .and_then(|v| v.to_str().ok())
    {
        Some("machine") => Ok("machine"),
        Some("human") | None => Ok("human"),
        Some(_) => Err(StatusCode::BAD_REQUEST),
    }
}

/// Build the router over the managed single-writer runtime.
pub fn router(state: Store) -> Router {
    projections(state, true)
}

/// Legacy manual receipts are only retained for in-process compatibility tests.
pub fn projections(state: Store, manual_receipts: bool) -> Router {
    projections_base(state.clone(), manual_receipts).merge(
        Router::new()
            .route(
                "/api/v1/documents/:document_id/checks/execute",
                post(documents::execute_check),
            )
            .with_state(state),
    )
}
pub(crate) fn projections_base(state: Store, manual_receipts: bool) -> Router {
    let external_context_routes = Router::new()
        .route(
            "/api/v1/machine/external-context/status",
            get(external_context::status),
        )
        .route(
            "/api/v1/machine/external-context/candidates",
            post(external_context::receive),
        )
        .layer(axum::extract::DefaultBodyLimit::max(65536));
    let ui_routes = Router::new()
        .route(
            "/api/v1/workspace/operation-failures/read",
            post(failure_log::read).layer(axum::extract::DefaultBodyLimit::max(2048)),
        )
        .route(
            "/api/v1/workspace/operation-failures/append",
            post(failure_log::append).layer(axum::extract::DefaultBodyLimit::max(2048)),
        )
        .route(
            "/api/v1/workspace/operation-failures/clear",
            post(failure_log::clear).layer(axum::extract::DefaultBodyLimit::max(2048)),
        )
        .route(
            "/api/v1/workspace/layout",
            get(layout::read).put(layout::write),
        )
        .route("/api/v1/workspace/layout/recover", post(layout::recover))
        .route(
            "/api/v1/workspace/ui-state",
            get(ui_state::read).put(ui_state::write),
        )
        .route(
            "/api/v1/workspace/ui-state/clear-saved",
            post(ui_state::clear_saved),
        )
        .route(
            "/api/v1/workspace/ui-state/recover",
            post(ui_state::recover),
        )
        .layer(axum::extract::DefaultBodyLimit::max(1_100_000));
    let teaching_routes = Router::new()
        .route(
            "/api/v2/teaching/records",
            get(teaching::list).post(teaching::create),
        )
        .route("/api/v2/teaching/records/:id", get(teaching::read))
        .route("/api/v2/teaching/records/:id/export", get(teaching::export))
        .route("/api/v2/teaching/withdrawals", post(teaching::withdraw))
        .route("/api/v2/teaching/imports/preview", post(teaching::preview))
        .route("/api/v2/teaching/imports", post(teaching::import))
        .layer(axum::extract::DefaultBodyLimit::max(8 * 1024 * 1024));
    let routes = Router::new()
        .merge(external_context_routes)
        .route(
            "/api/v1/ingest-batches",
            get(ingest_batches::list)
                .post(ingest_batches::register)
                .layer(axum::extract::DefaultBodyLimit::max(1_100_000)),
        )
        .route(
            "/api/v1/ingest-batches/:batch_id",
            get(ingest_batches::read),
        )
        .route(
            "/api/v1/ingest-batches/:batch_id/imports",
            post(ingest_batches::import)
                .layer(axum::extract::DefaultBodyLimit::max(MAX_IMPORT_JSON_BYTES)),
        )
        .route(
            "/api/v1/ingest-batches/:batch_id/jobs",
            post(ingest_batches::enqueue),
        )
        .route(
            "/api/v1/ingest-batches/:batch_id/members/:ordinal/relations",
            post(ingest_relations::apply).layer(axum::extract::DefaultBodyLimit::max(256 * 1024)),
        )
        .route(
            "/api/v1/project-handoff/preview",
            post(project_handoff_preview::preview)
                .layer(axum::extract::DefaultBodyLimit::max(65_536)),
        )
        .route(
            "/api/v1/project-handoff/snapshot",
            post(project_handoff_preview::snapshot)
                .layer(axum::extract::DefaultBodyLimit::max(65_536)),
        )
        .merge(ui_routes)
        .merge(teaching_routes)
        .route(
            "/api/v1/machine/contexts",
            get(machine_governance::contexts),
        )
        .route("/api/v1/ai/assets", get(machine_governance::assets))
        .route(
            "/api/v1/ai/context-packets",
            post(machine_governance::asset_packet),
        )
        .route(
            "/api/v1/machine/rubrics",
            get(machine_governance::rubrics).post(machine_governance::create_rubric),
        )
        .route(
            "/api/v1/machine/evaluations",
            get(machine_governance::evaluations).post(machine_governance::create_evaluation),
        )
        .route(
            "/api/v1/machine/answers/:task_id/snapshot",
            get(machine_governance::answer_snapshot),
        )
        .route("/api/v1/sources", get(documents::sources))
        .route("/api/v1/sources/:source_id", get(documents::source))
        .route(
            "/api/v1/sources/:source_id/jobs/:job_id/format-qualification",
            get(format_qualification::read),
        )
        .route(
            "/api/v1/sources/:source_id/original",
            get(documents::original),
        )
        .route(
            "/api/v1/documents",
            get(documents::list).post(documents::create),
        )
        .route("/api/v1/documents/:document_id", get(documents::read))
        .route(
            "/api/v1/documents/:document_id/package",
            get(documents::package_export),
        )
        .route(
            "/api/v1/document-packages/import",
            post(documents::package_import).layer(axum::extract::DefaultBodyLimit::max(
                archeaxis_domain::portable_document::MAX_IMPORT_JSON_BYTES,
            )),
        )
        .route(
            "/api/v1/documents/:document_id/relations",
            get(documents::relations),
        )
        .route(
            "/api/v1/documents/:document_id/research-references",
            get(documents::research_references),
        )
        .route(
            "/api/v1/documents/:document_id/collection",
            get(documents::collection),
        )
        .route(
            "/api/v1/documents/:document_id/checks",
            get(documents::checks).post(documents::record_check),
        )
        .route(
            "/api/v1/documents/:document_id/export",
            get(documents::export),
        )
        .route("/api/v1/documents/:document_id/draft", put(documents::save))
        .route(
            "/api/v1/documents/:document_id/versions/:version",
            get(documents::version),
        )
        .route(
            "/api/v1/documents/:document_id/restore",
            post(documents::restore),
        )
        .route("/api/v1/system/version", get(system_version))
        .route(
            "/api/v2/workspace/restore/preview",
            post(workspace_backup::preview),
        )
        .route(
            "/api/v1/workspace/backups",
            get(workspace_backup::list).post(workspace_backup::create),
        )
        .route(
            "/api/v1/imports",
            post(import_source).layer(axum::extract::DefaultBodyLimit::max(MAX_IMPORT_JSON_BYTES)),
        )
        .route("/api/v1/jobs", post(enqueue_job))
        .route(
            "/api/v1/sources/:source_id/anchors",
            get(documents::anchors).post(create_anchor),
        )
        .route(
            "/api/v1/sources/:source_id/anchors/:anchor_id/resolve",
            get(anchor_resolution::resolve),
        )
        .route(
            "/api/v1/sources/:source_id/jobs/:job_id/transform",
            get(source_job_transform),
        )
        .route(
            "/api/v1/knowledge-items/from-transform",
            post(create_knowledge_from_transform),
        )
        .route("/api/v1/knowledge-items", post(create_knowledge))
        .route("/api/v1/knowledge-items/:id/v3", get(knowledge_v3))
        .route(
            "/api/v1/knowledge/:id/review/versioned",
            post(review_versioned),
        )
        .route(
            "/api/v1/knowledge-items/:id/qualification",
            get(knowledge_qualification),
        )
        .route(
            "/api/v1/knowledge-items/:id/review-decisions",
            post(review_decision),
        )
        .route("/api/v1/learning/events", post(record_learning_event))
        .route("/api/v1/learning/reviews", post(record_stateful_review))
        .route(
            "/api/v1/learning/deeptutor/question-view",
            post(provider_learning::question_view),
        )
        .route(
            "/api/v1/learning/provider-activities",
            post(provider_learning::create),
        )
        .route(
            "/api/v1/learning/provider-activities/:activity_id",
            get(provider_learning::read),
        )
        .route(
            "/api/v1/learning/provider-activities/:activity_id/attempts",
            post(provider_learning::start),
        )
        .route(
            "/api/v1/learning/provider-activities/:activity_id/attempts/:attempt_id/submit",
            post(provider_learning::submit),
        )
        .route(
            "/api/v1/learning/provider-activities/:activity_id/attempts/:attempt_id/cancel",
            post(provider_learning::cancel),
        )
        .route("/api/v1/learning/events/:item_key", get(learning_history))
        .route("/api/v1/learning/items", get(learning_items))
        .route(
            "/api/v1/learning/items/:item_key/references",
            post(record_item_reference),
        )
        .route(
            "/api/v1/learning/items/:item_key/assessment",
            get(read_assessment).post(create_assessment),
        )
        .route("/api/v1/learning/items/:item_key/state", get(item_state))
        .route(
            "/api/v1/machine/tasks",
            post(record_machine_task).get(machine_task_list),
        )
        .route("/api/v1/machine/tasks/:task_id", get(machine_task_readback))
        .route("/api/v1/search", get(search_knowledge))
        .route("/api/v1/jobs/:job_id/quality", get(job_quality))
        .route("/api/v1/evidence/anchors", get(evidence_anchors))
        .route("/api/v1/sources/:source_id/members", get(source_members))
        .route("/api/v1/sources/:source_id/pages", get(source_pages))
        .route("/api/v1/sources/:source_id/jobs", get(source_jobs))
        .route("/api/v1/workspaces/info", get(workspace_info));
    let routes = if manual_receipts {
        routes.route("/api/v1/jobs/:job_id/receipts", post(job_receipt))
    } else {
        routes
    };
    routes.with_state(state)
}

/// Open an initialized workspace and return its router.
pub fn app(db_path: &str) -> Result<Router, StoreError> {
    Ok(router(Store::open(std::path::Path::new(db_path))?))
}

async fn with_store(
    state: Store,
    work: impl FnOnce(&mut Connection) -> axum::response::Response + Send + 'static,
) -> axum::response::Response {
    match state.submit(work).await {
        Ok(response) => response,
        Err(error) => (StatusCode::SERVICE_UNAVAILABLE, error.to_string()).into_response(),
    }
}

async fn system_version(State(state): State<AppState>) -> axum::response::Response {
    with_store(state, |conn| {
        let sqlite_version: String =
            match conn.query_row("SELECT sqlite_version()", [], |r| r.get(0)) {
                Ok(value) => value,
                Err(error) => {
                    return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response();
                }
            };
        Json(serde_json::json!({
            "runtime": "archeaxis-api",
            "contract": "0.1.0-outline",
            "schema_version": archeaxis_store_sqlite::SCHEMA_VERSION,
            "sqlite_version":sqlite_version,
        }))
        .into_response()
    })
    .await
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

const MAX_IMPORT_BYTES: usize = 64 * 1024 * 1024;
const MAX_IMPORT_JSON_BYTES: usize = 90 * 1024 * 1024;
const MAX_IMPORT_BASE64_BYTES: usize = ((MAX_IMPORT_BYTES + 2) / 3) * 4;

fn decode_import_content(encoded: &str) -> Result<Vec<u8>, StatusCode> {
    // Reject oversized strings before decoding/allocation. Exact decoded length
    // is checked too because the final base64 quantum can contain extra bytes.
    if encoded.len() > MAX_IMPORT_BASE64_BYTES {
        return Err(StatusCode::PAYLOAD_TOO_LARGE);
    }
    let bytes = base64_decode(encoded).ok_or(StatusCode::BAD_REQUEST)?;
    if bytes.len() > MAX_IMPORT_BYTES {
        return Err(StatusCode::PAYLOAD_TOO_LARGE);
    }
    Ok(bytes)
}

const ALLOWED_ORIGIN_KINDS: &[&str] = &["path", "url", "import", "manual"];

async fn import_source(
    State(state): State<AppState>,
    Json(body): Json<ImportBody>,
) -> impl IntoResponse {
    let bytes = match decode_import_content(&body.content_base64) {
        Ok(bytes) => bytes,
        Err(status) => return (status, "invalid or oversized content_base64").into_response(),
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
    })
    .await
}

/// R09: one knowledge reference with its identity and its use status separated.
///
/// "The row exists" is not "this revision is still a current basis". A consumer
/// re-reading an item must see the revision it was built from, whether that
/// revision is current, superseded or no longer active, without the successor
/// being substituted into the historical reference.
fn reference_view(conn: &Connection, knowledge_id: &str) -> serde_json::Value {
    match knowledge::currentness(conn, knowledge_id) {
        Ok(Some(view)) => serde_json::json!({
            "knowledge_id": knowledge_id,
            "active": view.active,
            "status": view.status,
            "currentness": view.currentness,
            "superseded_by": view.superseded_by,
            "successor_count": view.successor_count,
            "valid_to": view.valid_to,
        }),
        Ok(None) => serde_json::json!({
            "knowledge_id": knowledge_id,
            "active": false,
            "currentness": "unavailable",
        }),
        Err(error) => serde_json::json!({
            "knowledge_id": knowledge_id,
            "active": false,
            "currentness": "unavailable",
            "read_error": error.to_string(),
        }),
    }
}

async fn learning_history(
    State(state): State<AppState>,
    Path(item_key): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        match learning::events_for_item(conn, &item_key) {
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
                // R09: report what this learning item was built from, annotated with
                // whether that revision is still current. A consumer re-reading the
                // item must not silently keep using a superseded revision.
                let references: Vec<serde_json::Value> =
                    match learning::references_for_card(conn, &item_key) {
                        Ok(found) => found
                            .into_iter()
                            .map(|(knowledge_id, _)| reference_view(conn, &knowledge_id))
                            .collect(),
                        Err(e) => {
                            return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
                                .into_response();
                        }
                    };
                (
                    StatusCode::OK,
                    Json(serde_json::json!({
                        "item_key": item_key,
                        "events": rows,
                        "count": rows.len(),
                        "references": references,
                    })),
                )
                    .into_response()
            }
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        }
    })
    .await
}

/// Read-only queue projection for desktop clients. The latest event is the
/// only source for each item's deadline; no learner or machine status is
/// inferred here.
async fn learning_items(State(state): State<AppState>) -> impl IntoResponse {
    with_store(state, |conn| {
        let rows = learning::item_keys_with_latest_review(conn).and_then(|items| {
            items
                .into_iter()
                .map(|(item_key, next_review)| {
                    let display_title = learning::item_display_title(conn, &item_key)?;
                    Ok(serde_json::json!({
                        "item_key": item_key,
                        "next_review": next_review,
                        "display_title": display_title,
                    }))
                })
                .collect::<rusqlite::Result<Vec<serde_json::Value>>>()
        });
        match rows {
            Ok(rows) => {
                let count = rows.len();
                (
                    StatusCode::OK,
                    Json(serde_json::json!({
                        "items": rows,
                        "count": count,
                    })),
                )
                    .into_response()
            }
            Err(error) => (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        }
    })
    .await
}

/// R10: the two sides of an item's state, kept separate.
///
/// The learner side is what this Core actually recorded for the human (events,
/// streak, next review, and which revisions the item was built from). The machine
/// side is *not* inferred from learner activity: machine capability receipts are
/// written by the machine loop, so until such a receipt exists this view says so
/// instead of presenting learner progress as machine competence.
fn latest_review_projection(events: &[(i64, String, String, Option<String>)]) -> serde_json::Value {
    let Some((event_id, kind, raw_outcome, next_review)) = events.last() else {
        return serde_json::Value::Null;
    };
    let outcome = serde_json::from_str::<serde_json::Value>(raw_outcome)
        .unwrap_or_else(|_| serde_json::Value::Object(serde_json::Map::new()));
    let schedule = outcome.get("schedule");
    let state = learning::precise_fsrs_state_from_outcome(raw_outcome).unwrap_or_else(|| {
        schedule
            .and_then(|value| value.get("state"))
            .cloned()
            .unwrap_or(serde_json::Value::Null)
    });
    let projection =
        learning::precise_fsrs_projection_from_outcome(raw_outcome).unwrap_or_else(|| {
            outcome
                .get("mastery_projection")
                .cloned()
                .unwrap_or(serde_json::Value::Null)
        });
    serde_json::json!({
        "event_id": event_id,
        "kind": kind,
        "next_review": next_review,
        "assessment_id": outcome.get("assessment_id").cloned().unwrap_or(serde_json::Value::Null),
        "answer": outcome.get("answer").cloned().unwrap_or(serde_json::Value::Null),
        "schedule_authority": schedule.and_then(|value| value.get("authority")).cloned().unwrap_or(serde_json::Value::Null),
        "schedule_state": state,
        "mastery_projection": projection,
    })
}

async fn item_state(
    State(state): State<AppState>,
    Path(item_key): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        let events = match learning::events_for_item(conn, &item_key) {
            Ok(rows) => rows,
            Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        };
        let references = match learning::references_for_card(conn, &item_key) {
            Ok(found) => found
                .into_iter()
                .map(|(knowledge_id, _)| reference_view(conn, &knowledge_id))
                .collect::<Vec<_>>(),
            Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        };
        let assessment = match learning::assessment_for_item_key(conn, &item_key) {
            Ok(value) => value,
            Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        };
        let assessment_id = assessment.as_ref().map(|value| value.assessment_id.as_str());
        let streak = match learning::correct_streak_for_assessment(conn, &item_key, assessment_id) {
            Ok(value) => value,
            Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        };
        let scoped_events = match assessment_id {
            Some(id) => match learning::events_for_assessment(conn, &item_key, id) {
                Ok(value) => value,
                Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
            },
            None => events.clone(),
        };
        let latest_review = latest_review_projection(&events);
        let scoped_review = latest_review_projection(&scoped_events);
        let assessment_progress = assessment.as_ref().map(|value| serde_json::json!({
            "assessment_id": value.assessment_id, "knowledge_id": value.knowledge_id,
            "knowledge_version": value.knowledge_version, "event_count": scoped_events.len(),
            "correct_streak": streak, "latest_review": scoped_review,
        })).unwrap_or(serde_json::Value::Null);
        let assessment = assessment.as_ref().map(|value| assessment_json(conn, value))
            .unwrap_or(serde_json::Value::Null);
        let unscheduled = events.iter().filter(|(_, _, _, next)| next.is_none()).count();
        let scheduled = events.len() - unscheduled;
        (
            StatusCode::OK,
            Json(serde_json::json!({
                "item_key": item_key,
                "learner": {
                    "event_count": events.len(),
                    "correct_streak": streak,
                    "correct_streak_scope": if assessment_id.is_some() { "assessment" } else { "legacy_item" },
                    "aggregate_scope": "item_history",
                    "scheduled_events": scheduled,
                    "unscheduled_events": unscheduled,
                    "next_review": scoped_review.get("next_review").cloned().unwrap_or(serde_json::Value::Null),
                    "assessment": assessment,
                    "assessment_progress": assessment_progress,
                    "latest_review": latest_review,
                    "references": references,
                    "recording": "a human records learning outcomes through the learning-events endpoint; an unavailable schedule is stored as unscheduled rather than invented",
                },
                "machine": {
                    "status": "not_recorded",
                    "note": "machine capability receipts are written by the machine loop; learner progress is never presented as machine competence",
                },
            })),
        )
            .into_response()
    })
    .await
}

/// R11: the machine side of the loop records what it ran.
///
/// A machine principal may only *record* a task receipt here - it cannot accept
/// knowledge, and a human principal must not write machine receipts either, so the
/// two sides stay distinguishable. The receipt is a candidate/measurement fact and
/// never a claim that weights were trained.
#[derive(Deserialize)]
struct MachineTaskBody {
    task_id: String,
    conditions: String,
    model_version: String,
    scope: String,
    outcome: String,
    #[serde(default)]
    knowledge_version: Option<String>,
    #[serde(default)]
    method_version: Option<String>,
    #[serde(default)]
    tool_version: Option<String>,
    #[serde(default)]
    failure: Option<String>,
    #[serde(default)]
    retest_of: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct MachineTaskPageQuery {
    cursor: Option<String>,
    limit: Option<usize>,
}

async fn machine_task_list(
    State(state): State<AppState>,
    Query(query): Query<MachineTaskPageQuery>,
) -> impl IntoResponse {
    let limit = query.limit.unwrap_or(20);
    if !(1..=100).contains(&limit)
        || query
            .cursor
            .as_ref()
            .is_some_and(|s| s.is_empty() || s.len() > 256)
    {
        return (StatusCode::BAD_REQUEST, "invalid receipt page bounds").into_response();
    }
    with_store(state, move |conn| {
        match machine::machine_task_page(conn, query.cursor.as_deref(), limit) {
            Ok(page) => axum::Json(page).into_response(),
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        }
    })
    .await
}

async fn record_machine_task(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<MachineTaskBody>,
) -> impl IntoResponse {
    if body.scope.starts_with("runtime.") {
        return (
            StatusCode::FORBIDDEN,
            "runtime receipt scopes are Core-owned",
        )
            .into_response();
    }
    if request_actor(&headers).unwrap_or("human") != "machine" {
        return (
            StatusCode::FORBIDDEN,
            "machine task receipts are written by a machine principal only",
        )
            .into_response();
    }
    with_store(state, move |conn| {
        let task = machine::MachineTask {
            task_id: &body.task_id,
            principal: "machine",
            conditions: &body.conditions,
            knowledge_version: body.knowledge_version.as_deref(),
            method_version: body.method_version.as_deref(),
            tool_version: body.tool_version.as_deref(),
            model_version: &body.model_version,
            scope: &body.scope,
            outcome: &body.outcome,
            failure: body.failure.as_deref(),
            retest_of: body.retest_of.as_deref(),
        };
        match machine::record_machine_task(conn, &task) {
            Ok(()) => (
                StatusCode::CREATED,
                Json(serde_json::json!({"task_id": body.task_id, "outcome": body.outcome})),
            )
                .into_response(),
            Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
        }
    })
    .await
}

/// R11: read a machine receipt back. Available to any principal: a receipt is
/// evidence about the machine side and never grants authority.
async fn machine_task_readback(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| match machine::machine_task(conn, &task_id) {
        Ok(Some(receipt)) => (
            StatusCode::OK,
            Json(serde_json::json!({
                "task_id": task_id,
                "conditions": receipt.conditions,
                "knowledge_version": receipt.knowledge_version,
                "method_version": receipt.method_version,
                "tool_version": receipt.tool_version,
                "model_version": receipt.model_version,
                "scope": receipt.scope,
                "outcome": receipt.outcome,
                "failure": receipt.failure,
                "retest_of": receipt.retest_of,
                "note": "a task receipt is a measurement fact, not a claim that weights were trained",
            })),
        )
            .into_response(),
        Ok(None) => (StatusCode::NOT_FOUND, "unknown machine task").into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    })
    .await
}

#[derive(Deserialize)]
struct ItemReferenceBody {
    knowledge_id: String,
}

/// R09: record the knowledge revision a learning item was created from. The
/// reference is immutable once recorded, so a later revision only changes the
/// annotation a consumer sees - never the history.
async fn record_item_reference(
    State(state): State<AppState>,
    Path(item_key): Path<String>,
    Json(body): Json<ItemReferenceBody>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        match learning::record_card_reference(conn, &item_key, &body.knowledge_id, None) {
            Ok(()) => (
                StatusCode::CREATED,
                Json(serde_json::json!({"item_key": item_key, "knowledge_id": body.knowledge_id})),
            )
                .into_response(),
            Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
        }
    })
    .await
}
#[derive(Deserialize)]
struct LearningEventBody {
    item_key: String,
    #[serde(default = "default_learning_kind")]
    kind: String,
    correct: bool,
    // EVENT-01: every submission must carry a persistent producer-side event
    // key; retries reuse the key and receive the original receipt. Kept
    // Option so the machine-actor guard (403) wins over the key check (400).
    #[serde(default)]
    client_event_id: Option<String>,
    // R05: the persisted FSRS card state for this item, when the caller keeps it.
    // Present -> the reusable scheduler decides the interval. Absent -> the
    // caller is explicitly on the placeholder ladder path.
    #[serde(default)]
    schedule_state: Option<serde_json::Value>,
    // Optional review instant, so a replayed submission stays reproducible.
    #[serde(default)]
    now: Option<String>,
}

fn default_learning_kind() -> String {
    "review".to_string()
}

/// Stateful FSRS entry. Clients report a review, never the authoritative card.
/// The legacy /events contract remains available for old keyed receipts.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StatefulReviewBody {
    item_key: String,
    client_event_id: String,
    correct: bool,
    rating: Option<u8>,
    now: Option<String>,
    /// Optional v2 learning evidence. Legacy clients remain valid; newer
    /// clients can bind an answer to the exact question/knowledge exposure.
    answer: Option<String>,
    #[serde(default)]
    assessment_id: Option<String>,
    question_version: Option<String>,
    knowledge_version: Option<String>,
    exposure_id: Option<String>,
    assist_strategy: Option<String>,
    rating_version: Option<String>,
    correction_id: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AssessmentBody {
    knowledge_id: String,
}

fn checked_review_schedule(
    connection: &Connection,
    answer: Result<
        archeaxis_application::scheduler::Schedule,
        archeaxis_application::scheduler::SchedulerError,
    >,
) -> rusqlite::Result<learning::ReviewSchedule> {
    let unavailable = || learning::ReviewSchedule {
        schedule_json: serde_json::json!({"authority":"unavailable"}).to_string(),
        next_review: None,
        next_review_days: learning::SCHEDULE_UNAVAILABLE,
    };
    let schedule = match answer {
        Ok(schedule) => learning::ReviewSchedule {
            schedule_json: serde_json::json!({"authority":"fsrs","state":schedule.card_state})
                .to_string(),
            next_review: Some(schedule.due),
            next_review_days: schedule.next_review_days,
        },
        Err(_) => unavailable(),
    };
    Ok(
        if learning::review_schedule_is_valid(connection, &schedule)? {
            schedule
        } else {
            unavailable()
        },
    )
}

#[cfg(test)]
mod stateful_schedule_failures {
    use super::*;
    use archeaxis_application::scheduler::{Schedule, SchedulerError};

    fn valid() -> Schedule {
        let due = "2026-09-02T00:10:00+00:00";
        Schedule {
            authority: "fsrs".into(),
            next_review_days: 0,
            due: due.into(),
            state: "learning".into(),
            card_state: serde_json::json!({"state":"learning","step":1,"stability":2.3065,"difficulty":2.1,
                "due":due,"last_review":"2026-09-02T00:00:00+00:00"}),
            replay_receipt: None,
        }
    }

    #[test]
    fn malformed_or_missing_scheduler_keeps_review_and_prior_state() {
        for case in ["missing", "null-parameter", "unknown-state", "invalid-date"] {
            let dir = tempfile::tempdir().unwrap();
            let mut conn = archeaxis_store_sqlite::init_workspace(
                dir.path().join("review.sqlite").to_str().unwrap(),
            )
            .unwrap();
            learning::record_review_with_state(
                &mut conn,
                "card",
                "review",
                true,
                "prior",
                "first",
                |c| checked_review_schedule(c, Ok(valid())),
            )
            .unwrap();
            let prior = learning::latest_fsrs_state_json(&conn, "card").unwrap();
            let mut broken = valid();
            match case {
                "null-parameter" => broken.card_state["stability"] = serde_json::Value::Null,
                "unknown-state" => broken.card_state["state"] = serde_json::json!("imaginary"),
                "invalid-date" => broken.card_state["due"] = serde_json::json!("12:00"),
                _ => {}
            }
            let answer = if case == "missing" {
                Err(SchedulerError::Unavailable("fixture".into()))
            } else {
                Ok(broken)
            };
            let receipt = learning::record_review_with_state(
                &mut conn,
                "card",
                "review",
                true,
                "failed",
                "second",
                |c| checked_review_schedule(c, answer),
            )
            .unwrap();
            assert_eq!(
                receipt.next_review_days,
                learning::SCHEDULE_UNAVAILABLE,
                "{case}"
            );
            assert!(receipt.next_review.is_none());
            assert_eq!(
                learning::latest_fsrs_state_json(&conn, "card").unwrap(),
                prior
            );
            let retry = learning::record_review_with_state(
                &mut conn,
                "card",
                "review",
                true,
                "failed",
                "second",
                |_| panic!("retry must not reschedule"),
            )
            .unwrap();
            assert_eq!(retry.outcome_json, receipt.outcome_json);
            assert_eq!(learning::count_learning(&conn).unwrap(), 2);
        }
    }

    #[test]
    fn real_scheduler_timeout_keeps_review_and_releases_transaction_for_next_review() {
        use std::time::{Duration, Instant};
        let dir = tempfile::tempdir().unwrap();
        let worker = dir.path().join("stalled.py");
        std::fs::write(&worker, "import time; time.sleep(10)").unwrap();
        let python = std::env::var_os("ARCHEAXIS_PYTHON").expect("run through dev.py");
        let client = archeaxis_application::scheduler::SchedulerClient::new(python, worker);
        let mut conn = archeaxis_store_sqlite::init_workspace(
            dir.path().join("review.sqlite").to_str().unwrap(),
        )
        .unwrap();
        let started = Instant::now();
        let failed = learning::record_review_with_state(
            &mut conn,
            "card",
            "review",
            true,
            "timed-out",
            "first",
            |c| {
                checked_review_schedule(
                    c,
                    client.review_with_timeout("{}", Duration::from_millis(700)),
                )
            },
        )
        .unwrap();
        assert!(started.elapsed() < Duration::from_secs(3));
        assert_eq!(failed.next_review_days, learning::SCHEDULE_UNAVAILABLE);
        let next = learning::record_review_with_state(
            &mut conn,
            "card",
            "review",
            true,
            "next",
            "second",
            |c| checked_review_schedule(c, Ok(valid())),
        )
        .unwrap();
        assert!(next.next_review.is_some());
        assert_eq!(learning::count_learning(&conn).unwrap(), 2);
    }
}

fn assessment_json(conn: &Connection, value: &learning::AssessmentRecord) -> serde_json::Value {
    serde_json::json!({"assessment_id": value.assessment_id, "item_key": value.item_key,
        "knowledge_id": value.knowledge_id, "knowledge_version": value.knowledge_version,
        "knowledge_state": reference_view(conn, &value.knowledge_id),
        "question": value.question, "content": value.content,
        "source_id": value.source_id, "anchor_id": value.anchor_id, "created_at": value.created_at})
}

async fn create_assessment(
    State(state): State<AppState>,
    Path(item_key): Path<String>,
    Json(body): Json<AssessmentBody>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        match learning::create_assessment(conn, &item_key, &body.knowledge_id) {
            Ok(value) => (StatusCode::CREATED, Json(assessment_json(conn, &value))).into_response(),
            Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
        }
    })
    .await
}

async fn read_assessment(
    State(state): State<AppState>,
    Path(item_key): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        match learning::assessment_for_item_key(conn, &item_key) {
            Ok(Some(value)) => {
                (StatusCode::OK, Json(assessment_json(conn, &value))).into_response()
            }
            Ok(None) => (StatusCode::NOT_FOUND, "assessment not found").into_response(),
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        }
    })
    .await
}

fn stateful_review_response(receipt: learning::ReviewReceipt) -> axum::response::Response {
    let mut outcome: serde_json::Value = match serde_json::from_str(&receipt.outcome_json) {
        Ok(value) => value,
        Err(_) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                "stored review is invalid",
            )
                .into_response();
        }
    };
    if let Some(card) = learning::precise_fsrs_state_from_outcome(&receipt.outcome_json) {
        outcome["schedule"]["state"] = card;
    }
    if let Some(projection) = learning::precise_fsrs_projection_from_outcome(&receipt.outcome_json)
    {
        outcome["mastery_projection"] = projection;
    }
    let mut response = serde_json::json!({"event_id":receipt.event_id,"streak_after":receipt.streak_after,
        "next_review_days":receipt.next_review_days,"next_review":receipt.next_review,
        "duplicate":receipt.duplicate,"schedule_authority":outcome["schedule"]["authority"],
        "schedule_state":outcome["schedule"]["state"], "answer":outcome["answer"],
        "review_evidence":outcome["review_evidence"], "mastery_projection":outcome["mastery_projection"]});
    if let Some(recovery) = outcome["schedule"].get("recovery") {
        response["schedule_recovery"] = recovery.clone();
    }
    (
        if receipt.duplicate {
            StatusCode::OK
        } else {
            StatusCode::CREATED
        },
        Json(response),
    )
        .into_response()
}

enum StatefulReviewPreparation {
    Replay(learning::ReviewReceipt),
    Invalid(&'static str),
    Schedule(learning::ReviewScheduleBasis, String),
}

fn replay_digest(entries: &[learning::PendingScheduleReview]) -> String {
    use sha2::{Digest, Sha256};
    let mut digest = Sha256::new();
    digest.update(b"archeaxis.fsrs-replay/v1\0");
    for entry in entries {
        digest.update((entry.event_id as u64).to_le_bytes());
        digest.update([entry.rating]);
        digest.update((entry.reviewed_at.len() as u32).to_le_bytes());
        digest.update(entry.reviewed_at.as_bytes());
    }
    format!("{:x}", digest.finalize())
}

async fn validated_recovery_card(
    state: &AppState,
    scheduled: archeaxis_application::scheduler::Schedule,
) -> Result<serde_json::Value, &'static str> {
    let card = scheduled.card_state.clone();
    let checked = state
        .clone()
        .submit_wait(move |conn| checked_review_schedule(conn, Ok(scheduled)))
        .await;
    let Ok(Ok(checked)) = checked else {
        return Err("recovery_validation_unavailable");
    };
    if checked.next_review.is_none() {
        return Err("invalid_recovered_card");
    }
    Ok(card)
}

/// Reapply only observations whose rating and exact effective time were retained.
/// All subprocesses share one 20s budget. A batch is accepted only with the
/// worker's matching receipt; older workers fall back to single reviews.
async fn schedule_with_recovery(
    state: &AppState,
    item_key: &str,
    basis: &learning::ReviewScheduleBasis,
    rating: u8,
    instant: &str,
) -> (
    Result<
        archeaxis_application::scheduler::Schedule,
        archeaxis_application::scheduler::SchedulerError,
    >,
    Option<&'static str>,
) {
    use archeaxis_application::scheduler::{SchedulerClient, SchedulerError};
    let failure = |reason: &'static str| {
        (
            Err(SchedulerError::Unavailable(reason.into())),
            Some(reason),
        )
    };
    if let Some(reason) = basis.recovery_issue {
        return failure(reason);
    }
    let mut card: serde_json::Value = match basis.previous_state.as_ref() {
        Some(value) => match learning::parse_fsrs_card(value) {
            Ok(value) => value,
            Err(_) => return failure("invalid_previous_card"),
        },
        None => serde_json::json!({}),
    };
    let client = match SchedulerClient::from_env() {
        Ok(client) => client,
        Err(_) => return failure("scheduler_unavailable"),
    };
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(20);
    for chunk in basis.pending.chunks(128) {
        if chunk.len() > 1 {
            let (last, replay) = chunk.split_last().expect("nonempty chunk");
            let history: Vec<_> = replay
                .iter()
                .map(|entry| {
                    serde_json::json!({
                "event_id":entry.event_id,"rating":entry.rating,"now":entry.reviewed_at})
                })
                .collect();
            let request = serde_json::json!({"item_key":item_key,"rating":last.rating,
                "state":card,"now":last.reviewed_at,"replay":history})
            .to_string();
            let remaining = deadline.saturating_duration_since(std::time::Instant::now());
            if remaining.is_zero() {
                return failure("recovery_time_budget_exhausted");
            }
            if let Ok(scheduled) = client.review_with_timeout(&request, remaining) {
                let receipt_ok = scheduled.replay_receipt.as_ref().is_some_and(|receipt| {
                    receipt.schema == "archeaxis.fsrs-replay/v1"
                        && receipt.count == replay.len()
                        && receipt.sha256 == replay_digest(replay)
                });
                if receipt_ok {
                    card = match validated_recovery_card(state, scheduled).await {
                        Ok(card) => card,
                        Err(reason) => return failure(reason),
                    };
                    continue;
                }
            }
            // A pre-batch worker may ignore or reject the extension; never use
            // its unproved result. Recompute this chunk one observation at a time.
        }
        for pending in chunk {
            let remaining = deadline.saturating_duration_since(std::time::Instant::now());
            if remaining.is_zero() {
                return failure("recovery_time_budget_exhausted");
            }
            let request = serde_json::json!({"item_key":item_key,"rating":pending.rating,
                "state":card,"now":pending.reviewed_at})
            .to_string();
            let scheduled = match client.review_with_timeout(&request, remaining) {
                Ok(value) => value,
                Err(_) => return failure("scheduler_unavailable_during_recovery"),
            };
            card = match validated_recovery_card(state, scheduled).await {
                Ok(card) => card,
                Err(reason) => return failure(reason),
            };
        }
    }
    let remaining = deadline.saturating_duration_since(std::time::Instant::now());
    if remaining.is_zero() {
        return failure("recovery_time_budget_exhausted");
    }
    let request =
        serde_json::json!({"item_key":item_key,"rating":rating,"state":card,"now":instant})
            .to_string();
    match client.review_with_timeout(&request, remaining) {
        Ok(schedule) => (Ok(schedule), None),
        Err(_) => failure("scheduler_unavailable"),
    }
}

fn invalid_stateful_review_input(
    conn: &Connection,
    item_key: &str,
    now: Option<&str>,
    assessment_id: Option<&str>,
    knowledge_version: Option<&str>,
) -> rusqlite::Result<Option<&'static str>> {
    if let Some(now) = now {
        if !learning::valid_review_timestamp(conn, now)? {
            return Ok(Some("now must be an ISO timestamp with timezone"));
        }
    }
    if let Some(assessment_id) = assessment_id {
        let Some(assessment) = learning::assessment_for_item(conn, assessment_id, item_key)? else {
            return Ok(Some("assessment does not match item"));
        };
        if knowledge_version.is_some_and(|v| v != assessment.knowledge_version) {
            return Ok(Some("knowledge_version does not match assessment"));
        }
    }
    Ok(None)
}

async fn record_stateful_review(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<StatefulReviewBody>,
) -> impl IntoResponse {
    match request_actor(&headers) {
        Ok("human") => {}
        Ok(_) => {
            return (
                StatusCode::FORBIDDEN,
                "machine principal cannot record human reviews",
            )
                .into_response();
        }
        Err(status) => return (status, "invalid actor").into_response(),
    }
    let rating = body.rating.unwrap_or(if body.correct { 3 } else { 1 });
    if body.item_key.trim().is_empty()
        || body.client_event_id.trim().is_empty()
        || !(1..=4).contains(&rating)
        || (rating == 1) == body.correct
    {
        return (
            StatusCode::BAD_REQUEST,
            "item, event key and consistent rating/outcome are required",
        )
            .into_response();
    }
    if body
        .answer
        .as_deref()
        .is_some_and(|answer| answer.trim().is_empty())
    {
        return (StatusCode::BAD_REQUEST, "answer must not be empty").into_response();
    }
    let assessment_id = body
        .assessment_id
        .clone()
        .filter(|value| !value.trim().is_empty());
    // Preserve schedule-only legacy clients. The M0 first-use path carries an
    // answer and must bind it to a Core-owned assessment; old clients that
    // submit only a rating remain valid for the pre-Assessment queue.
    if body.answer.is_some() && assessment_id.is_none() {
        return (
            StatusCode::BAD_REQUEST,
            "assessment_id is required when answer is submitted",
        )
            .into_response();
    }
    let canonical = serde_json::json!({"item_key":body.item_key,"correct":body.correct,
        "rating":rating,"now":body.now,"answer":body.answer,
        "assessment_id":assessment_id,
        "question_version":body.question_version,"knowledge_version":body.knowledge_version,
        "exposure_id":body.exposure_id,"assist_strategy":body.assist_strategy,
        "rating_version":body.rating_version,"correction_id":body.correction_id})
    .to_string();
    // Phase 1 (short writer read): snapshot the FSRS card and the effective review instant, then
    // release the writer. The scheduler may wait up to 20s, and must not hold the single canonical
    // writer while it does, so a slow schedule cannot block document saves or other reads.
    let snapshot_key = body.item_key.clone();
    let snapshot_now = body.now.clone();
    let snapshot_assessment = assessment_id.clone();
    let snapshot_event = body.client_event_id.clone();
    let snapshot_request = canonical.clone();
    let snapshot_correct = body.correct;
    let snapshot_knowledge_version = body.knowledge_version.clone();
    let (basis, instant) = match state
        .clone()
        .submit_wait(move |conn| -> rusqlite::Result<StatefulReviewPreparation> {
            if let Some(receipt) = learning::existing_stateful_review(conn, &snapshot_key, "review",
                snapshot_correct, &snapshot_event, &snapshot_request)? {
                return Ok(StatefulReviewPreparation::Replay(receipt));
            }
            if snapshot_assessment.is_none() && learning::assessment_for_item_key(conn, &snapshot_key)?.is_some() {
                return Err(rusqlite::Error::InvalidParameterName(
                    "assessment binding conflict: this item requires an assessment_id for a new review".into(),
                ));
            }
            if let Some(message) = invalid_stateful_review_input(
                conn,
                &snapshot_key,
                snapshot_now.as_deref(),
                snapshot_assessment.as_deref(),
                snapshot_knowledge_version.as_deref(),
            )? {
                return Ok(StatefulReviewPreparation::Invalid(message));
            }
            let previous = learning::review_schedule_basis(
                conn,
                &snapshot_key,
                snapshot_assessment.as_deref(),
            )?;
            let instant = match snapshot_now.as_ref() {
                Some(now) => now.clone(),
                None => conn.query_row("SELECT strftime('%Y-%m-%dT%H:%M:%fZ','now')", [], |r| {
                    r.get::<_, String>(0)
                })?,
            };
            Ok(StatefulReviewPreparation::Schedule(previous, instant))
        })
        .await
    {
        Ok(Ok(StatefulReviewPreparation::Replay(receipt))) => return stateful_review_response(receipt),
        Ok(Ok(StatefulReviewPreparation::Invalid(message))) => return (StatusCode::BAD_REQUEST, message).into_response(),
        Ok(Ok(StatefulReviewPreparation::Schedule(previous, instant))) => (previous, instant),
        Ok(Err(rusqlite::Error::InvalidParameterName(message))) if message.starts_with("event_key conflict:") || message.starts_with("assessment binding conflict:") =>
            return (StatusCode::CONFLICT, message).into_response(),
        Ok(Err(e)) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        Err(e) => return (StatusCode::SERVICE_UNAVAILABLE, e.to_string()).into_response(),
    };

    // Phase 2 (off the writer): reconstruct recoverable outage reviews before
    // scheduling the new observation, without rewriting their receipts.
    let (schedule_result, recovery_issue) =
        schedule_with_recovery(&state, &body.item_key, &basis, rating, &instant).await;
    let worker_returned_card = schedule_result.is_ok();
    let previous_fsrs_state = basis.previous_state;
    let previous_event_id = basis.latest_event_id;
    let recovered_count = basis.pending.len();
    let recovered_through = basis.pending.last().map(|value| value.event_id);
    let guard_item = body.item_key.clone();
    let guard_assessment = assessment_id.clone();

    // Phase 3 (short writer transaction): validate the request, guard that the card the schedule was
    // computed from is unchanged, and record. Only the fast DB validation of the precomputed
    // schedule happens here; the slow FSRS subprocess already completed outside the writer.
    with_store(state, move |conn| {
        match invalid_stateful_review_input(
            conn,
            &body.item_key,
            body.now.as_deref(),
            assessment_id.as_deref(),
            body.knowledge_version.as_deref(),
        ) {
            Ok(None) => {}
            Ok(Some(message)) => return (StatusCode::BAD_REQUEST, message).into_response(),
            Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        }
        let result = learning::record_review_with_state_and_answer(
            conn,
            &body.item_key,
            "review",
            body.correct,
            &body.client_event_id,
            &canonical,
            body.answer.as_deref(),
            assessment_id.as_deref(),
            Some(previous_fsrs_state),
            move |connection| {
                if learning::latest_review_event_id(connection, &guard_item, guard_assessment.as_deref())?
                    != previous_event_id
                {
                    return Err(rusqlite::Error::InvalidParameterName(
                        "schedule basis conflict: review history moved during scheduling".into(),
                    ));
                }
                let mut schedule = checked_review_schedule(connection, schedule_result)?;
                let mut details: serde_json::Value = serde_json::from_str(&schedule.schedule_json)
                    .map_err(|_| rusqlite::Error::InvalidParameterName("invalid schedule JSON".into()))?;
                if let Some(card) = learning::precise_fsrs_state_from_schedule(&schedule.schedule_json) {
                    details["state"] = card;
                }
                if schedule.next_review.is_none() {
                    details["reviewed_at"] = serde_json::json!(instant);
                    if let Some(reason) = recovery_issue.or(worker_returned_card.then_some("invalid_scheduler_card")) {
                        details["recovery"] = serde_json::json!({"state":"incomplete", "reason":reason,
                            "replayable_count":recovered_count});
                    }
                } else if recovered_count > 0 {
                    details["recovery"] = serde_json::json!({"state":"replayed", "count":recovered_count,
                        "through_event_id":recovered_through});
                }
                schedule.schedule_json = details.to_string();
                Ok(schedule)
            },
        );
        match result {
            Ok(receipt) => stateful_review_response(receipt),
            Err(rusqlite::Error::InvalidParameterName(message))
                if message.starts_with("event_key conflict:")
                    || message.starts_with("schedule basis conflict:")
                    || message.starts_with("assessment binding conflict:") =>
            {
                (StatusCode::CONFLICT, message).into_response()
            }
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        }
    })
    .await
}

fn http_learning_event_response(
    receipt: learning::HttpLearningEventReceipt,
) -> axum::response::Response {
    (if receipt.duplicate { StatusCode::OK } else { StatusCode::CREATED },
     Json(serde_json::json!({"event_id": receipt.event_id, "streak_after": receipt.streak_after,
        "next_review_days": receipt.next_review_days, "duplicate": receipt.duplicate,
        "schedule_authority": receipt.schedule_authority, "idempotency_scope": receipt.idempotency_scope}))).into_response()
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
        return (
            StatusCode::FORBIDDEN,
            "machine principal cannot record human learning outcomes",
        )
            .into_response();
    }
    match body.client_event_id.as_deref().map(str::trim) {
        Some(k) if !k.is_empty() => {}
        _ => return (StatusCode::BAD_REQUEST, "client_event_id must be non-empty").into_response(),
    }
    let canonical = serde_json::json!({
        "item_key": body.item_key, "kind": body.kind, "correct": body.correct,
        "client_event_id": body.client_event_id, "schedule_state": body.schedule_state, "now": body.now,
    }).to_string();
    let lookup_item = body.item_key.clone();
    let lookup_kind = body.kind.clone();
    let lookup_key = body.client_event_id.clone().unwrap_or_default();
    let lookup_request = canonical.clone();
    let lookup_correct = body.correct;
    match state
        .clone()
        .submit_wait(
            move |conn| -> rusqlite::Result<Option<learning::HttpLearningEventReceipt>> {
                let existing = learning::existing_http_learning_event(
                    conn,
                    &lookup_item,
                    &lookup_kind,
                    lookup_correct,
                    &lookup_key,
                    &lookup_request,
                )?;
                if existing.is_none()
                    && lookup_kind == "review"
                    && learning::assessment_for_item_key(conn, &lookup_item)?.is_some()
                {
                    return Err(rusqlite::Error::InvalidParameterName(
                        "assessment binding conflict: use the assessment-bound reviews endpoint"
                            .into(),
                    ));
                }
                Ok(existing)
            },
        )
        .await
    {
        Ok(Ok(Some(receipt))) => return http_learning_event_response(receipt),
        Ok(Ok(None)) => {}
        Ok(Err(rusqlite::Error::InvalidParameterName(message)))
            if message.starts_with("event_key conflict:")
                || message.starts_with("assessment binding conflict:") =>
        {
            return (StatusCode::CONFLICT, message).into_response();
        }
        Ok(Err(error)) => {
            return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response();
        }
        Err(error) => return (StatusCode::SERVICE_UNAVAILABLE, error.to_string()).into_response(),
    }
    // R05: after the read-only replay check, resolve the scheduling authority
    // before the write transaction.
    // - caller supplied the persisted card state -> ask the reused FSRS worker
    //   (authority "fsrs"), or record the review as explicitly unscheduled
    //   (authority "unavailable") when that scheduler cannot answer;
    // - no card state -> the placeholder ladder, reported as such so no caller
    //   can mistake it for real FSRS scheduling.
    let schedule = match body.schedule_state.clone() {
        None => learning::ScheduleSource::Ladder,
        Some(card_state) => {
            let mut request = serde_json::json!({
                "item_key": body.item_key,
                "correct": body.correct,
                "state": card_state,
            });
            if let Some(now) = body.now.as_deref() {
                request["now"] = serde_json::json!(now);
            }
            let answer = archeaxis_application::scheduler::SchedulerClient::from_env()
                .and_then(|client| client.review(&request.to_string()));
            match answer {
                Ok(schedule) if schedule.next_review_days >= 0 => {
                    learning::ScheduleSource::Explicit(Some(schedule.next_review_days))
                }
                _ => learning::ScheduleSource::Explicit(None),
            }
        }
    };
    let outcome = move |conn: &mut rusqlite::Connection| {
        learning::record_http_learning_event(
            conn,
            &body.item_key,
            &body.kind,
            body.correct,
            body.client_event_id.as_deref().unwrap_or(""),
            &canonical,
            schedule,
        )
    };
    with_store(state, move |conn| match outcome(conn) {
        Ok(receipt) => http_learning_event_response(receipt),
        Err(rusqlite::Error::InvalidParameterName(message))
            if message.starts_with("event_key conflict:")
                || message.starts_with("assessment binding conflict:") =>
        {
            (StatusCode::CONFLICT, message).into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    })
    .await
}

// A located time anchor verifies a cue's provenance, not recognition accuracy.
fn verify_time_anchor(
    conn: &rusqlite::Connection,
    source: &str,
    revision: &str,
    position: &serde_json::Value,
    checksum: &str,
) -> Option<bool> {
    use sha2::{Digest, Sha256};
    let job = position["job_id"].as_str()?;
    let attempt = i64::try_from(position["attempt"].as_u64()?).ok()?;
    let index = usize::try_from(position["cue_index"].as_u64()?).ok()?;
    let start = position["start_ms"].as_u64()?;
    let end = position["end_ms"].as_u64()?;
    let expected = position["result_sha256"].as_str()?;
    let (input, kind, job_state, state, wire, metadata, content, latest): (
        String,
        String,
        String,
        String,
        String,
        String,
        String,
        i64,
    ) = conn
        .query_row(
            "SELECT j.input_ref,j.kind,j.state,a.state,a.request_json,o.metadata_json,o.content,
         (SELECT MAX(attempt) FROM job_attempts WHERE job_id=j.job_id)
         FROM jobs j JOIN job_attempts a ON a.job_id=j.job_id
         JOIN job_outputs o ON o.job_id=a.job_id AND o.attempt=a.attempt AND o.kind='loss_report'
         WHERE j.job_id=?1 AND a.attempt=?2",
            rusqlite::params![job, attempt],
            |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    r.get(2)?,
                    r.get(3)?,
                    r.get(4)?,
                    r.get(5)?,
                    r.get(6)?,
                    r.get(7)?,
                ))
            },
        )
        .ok()?;
    if input != source
        || !matches!(kind.as_str(), "transcribe" | "video" | "subtitles")
        || job_state != "succeeded"
        || state != "succeeded"
        || latest != attempt
    {
        return Some(false);
    }
    let request: serde_json::Value = serde_json::from_str(&wire).ok()?;
    let meta: serde_json::Value = serde_json::from_str(&metadata).ok()?;
    let loss: serde_json::Value = serde_json::from_str(&content).ok()?;
    let hash = format!("{:x}", Sha256::digest(content.as_bytes()));
    if request["capability"]
        != (if kind == "video" {
            "media.video"
        } else if kind == "subtitles" {
            "subtitles.structure"
        } else {
            "media.transcribe"
        })
        || request["job_id"] != job
        || request["attempt"] != attempt
        || request["inputs"][0]["sha256"] != revision
        || meta["kind"] != "loss_report"
        || meta["sha256"] != hash
        || expected != hash
        || meta["byte_length"].as_u64()? != content.len() as u64
    {
        return Some(false);
    }
    if kind == "subtitles" {
        // Subtitle times verify the derived file declaration, never original ASR accuracy.
        let cue = loss["params"]["worker_structure"].as_array()?.get(index)?;
        let offset = cue["offset_ms"].as_u64()?;
        let duration = cue["duration_ms"].as_u64()?;
        let finish = offset.checked_add(duration)?;
        let (text, text_metadata): (String, String) = conn.query_row(
            "SELECT content,metadata_json FROM job_outputs WHERE job_id=?1 AND attempt=?2 AND kind='text'",
            rusqlite::params![job, attempt], |r| Ok((r.get(0)?, r.get(1)?)),
        ).ok()?;
        let text_meta: serde_json::Value = serde_json::from_str(&text_metadata).ok()?;
        if text_meta["kind"] != "text"
            || text_meta["sha256"] != format!("{:x}", Sha256::digest(text.as_bytes()))
            || text_meta["byte_length"].as_u64()? != text.len() as u64
        {
            return Some(false);
        }
        let first = usize::try_from(cue["char_start"].as_u64()?).ok()?;
        let last = usize::try_from(cue["char_end"].as_u64()?).ok()?;
        let chars: Vec<char> = text.chars().collect();
        let quote: String = chars.get(first..last)?.iter().collect();
        return Some(
            cue["kind"] == "cue"
                && !quote.is_empty()
                && start < end
                && offset == start
                && finish == end
                && format!("{:x}", Sha256::digest(quote.as_bytes())) == checksum,
        );
    }
    let output = &loss["params"]["worker_output"];
    let cue = output["cues"].as_array()?.get(index)?;
    let text = cue["text"].as_str()?;
    Some(
        start < end
            && end <= output["duration_ms"].as_u64()?
            && cue["start_ms"].as_u64()? == start
            && cue["end_ms"].as_u64()? == end
            && format!("{:x}", Sha256::digest(text.as_bytes())) == checksum,
    )
}

fn verify_epub_anchor(
    conn: &rusqlite::Connection,
    source: &str,
    revision: &str,
    position: &serde_json::Value,
    checksum: &str,
) -> Option<bool> {
    use sha2::{Digest, Sha256};
    let job = position["job_id"].as_str()?;
    let attempt = i64::try_from(position["attempt"].as_u64()?).ok()?;
    let chapter = position["chapter"].as_u64()?;
    let paragraph = position["paragraph"].as_u64()?;
    let member_path = position["path"].as_str()?;
    let expected = position["result_sha256"].as_str()?;
    let (input, kind, job_state, state, wire, metadata, content, latest): (
        String,
        String,
        String,
        String,
        String,
        String,
        String,
        i64,
    ) = conn
        .query_row(
            "SELECT j.input_ref,j.kind,j.state,a.state,a.request_json,o.metadata_json,o.content,
         (SELECT MAX(attempt) FROM job_attempts WHERE job_id=j.job_id)
         FROM jobs j JOIN job_attempts a ON a.job_id=j.job_id
         JOIN job_outputs o ON o.job_id=a.job_id AND o.attempt=a.attempt AND o.kind='loss_report'
         WHERE j.job_id=?1 AND a.attempt=?2",
            rusqlite::params![job, attempt],
            |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    r.get(2)?,
                    r.get(3)?,
                    r.get(4)?,
                    r.get(5)?,
                    r.get(6)?,
                    r.get(7)?,
                ))
            },
        )
        .ok()?;
    if input != source
        || kind != "text"
        || job_state != "succeeded"
        || state != "succeeded"
        || latest != attempt
    {
        return Some(false);
    }
    let request: serde_json::Value = serde_json::from_str(&wire).ok()?;
    let meta: serde_json::Value = serde_json::from_str(&metadata).ok()?;
    let loss: serde_json::Value = serde_json::from_str(&content).ok()?;
    let hash = format!("{:x}", Sha256::digest(content.as_bytes()));
    if request["capability"] != "text.extract"
        || request["job_id"] != job
        || request["attempt"] != attempt
        || request["inputs"][0]["sha256"] != revision
        || request["inputs"][0]["media_type"] != "application/epub+zip"
        || meta["kind"] != "loss_report"
        || meta["sha256"] != hash
        || expected != hash
        || meta["byte_length"].as_u64()? != content.len() as u64
    {
        return Some(false);
    }
    let output = &loss["params"]["format"];
    if output["format"] != "epub" || output["parsed"] != true || chapter == 0 || paragraph == 0 {
        return Some(false);
    }
    let locations = output["locations"].as_array()?;
    let matching: Vec<_> = locations
        .iter()
        .filter(|location| {
            location["kind"] == "epub_chapter_paragraph"
                && location["chapter"].as_u64() == Some(chapter)
                && location["paragraph"].as_u64() == Some(paragraph)
                && location["path"].as_str() == Some(member_path)
        })
        .collect();
    if matching.len() != 1 {
        return Some(false);
    }
    let text = matching[0]["value"].as_str()?;
    Some(!text.is_empty() && format!("{:x}", Sha256::digest(text.as_bytes())) == checksum)
}

/// R15/F07-F09/F12: an anchor that names the location the worker described.
///
/// A route's canonical line anchors are the addressing level the Core validates, and a worker's
/// own structure - which paragraph, which sheet row, which slide - was until now a reported fact
/// inside the loss receipt, which is what "a heading is a fact rather than an addressing level"
/// meant. This makes that description a locator that can be checked: the same attempt must be the
/// latest succeeded one for this source and revision, the receipt must name this kind and path
/// exactly once, and the text at the span it records must hash to the checksum being claimed.
///
/// What is deliberately NOT claimed: the span is the worker's own, so the anchor proves where this
/// text sits in this projection revision, not an independently derived page number.
fn verify_structure_anchor(
    conn: &rusqlite::Connection,
    source: &str,
    revision: &str,
    position: &serde_json::Value,
    checksum: &str,
) -> Option<bool> {
    use sha2::{Digest, Sha256};
    let job = position["job_id"].as_str()?;
    let attempt = i64::try_from(position["attempt"].as_u64()?).ok()?;
    let kind = position["kind"].as_str()?;
    let claimed: Vec<&str> = position["path"]
        .as_array()?
        .iter()
        .filter_map(|v| v.as_str())
        .collect();
    if claimed.is_empty() || claimed.len() != position["path"].as_array()?.len() {
        return Some(false);
    }
    let row: (String, String, String, String, Option<String>, Option<String>, i64) = conn
        .query_row(
            "SELECT j.input_ref,j.state,a.state,o.content,
                    (SELECT content FROM job_outputs WHERE job_id=j.job_id AND attempt=a.attempt AND kind='text'),
                    (SELECT content FROM job_outputs WHERE job_id=j.job_id AND attempt=a.attempt AND kind='document_structure'),
                    (SELECT COUNT(*) FROM job_attempts WHERE job_id=j.job_id AND attempt>?2)
             FROM jobs j JOIN job_attempts a ON a.job_id=j.job_id
             JOIN job_outputs o ON o.job_id=a.job_id AND o.attempt=a.attempt AND o.kind='loss_report'
             WHERE j.job_id=?1 AND a.attempt=?2",
            rusqlite::params![job, attempt],
            |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    r.get(2)?,
                    r.get(3)?,
                    r.get(4)?,
                    r.get(5)?,
                    r.get(6)?,
                ))
            },
        )
        .ok()?;
    let (input, job_state, attempt_state, loss_content, text, structure, later) = row;
    if input != source || job_state != "succeeded" || attempt_state != "succeeded" || later != 0 {
        return Some(false);
    }
    // the projection the structure was derived from, and the canonical anchors of the same attempt
    let text = text?;
    let structure: serde_json::Value = serde_json::from_str(&structure?).ok()?;
    if !structure.is_array() {
        return Some(false);
    }
    let wire: String = conn
        .query_row(
            "SELECT request_json FROM job_attempts WHERE job_id=?1 AND attempt=?2",
            rusqlite::params![job, attempt],
            |r| r.get(0),
        )
        .ok()?;
    let request: serde_json::Value = serde_json::from_str(&wire).ok()?;
    if request["job_id"] != job
        || request["attempt"] != serde_json::json!(attempt)
        || request["inputs"][0]["sha256"] != revision
        || request["capability"].as_str().unwrap_or("").is_empty()
    {
        return Some(false);
    }
    let loss: serde_json::Value = serde_json::from_str(&loss_content).ok()?;
    let entries = loss["params"]["worker_structure"].as_array()?;
    let matching: Vec<&serde_json::Value> = entries
        .iter()
        .filter(|entry| {
            entry["kind"].as_str() == Some(kind)
                && entry["path"].as_array().is_some_and(|path| {
                    path.iter()
                        .filter_map(|v| v.as_str())
                        .eq(claimed.iter().copied())
                })
        })
        .collect();
    if matching.len() != 1 {
        return Some(false);
    }
    let start = usize::try_from(matching[0]["char_start"].as_u64()?).ok()?;
    let end = usize::try_from(matching[0]["char_end"].as_u64()?).ok()?;
    if end <= start {
        return Some(false);
    }
    // A worker counts characters in its own projection (Python semantics), not bytes, so slicing
    // this text by byte offsets would land mid-codepoint on any non-Latin document and refuse a
    // location that really was read. Slice the way they counted.
    let excerpt: String = text.chars().skip(start).take(end - start).collect();
    Some(
        excerpt.chars().count() == end - start
            && !excerpt.trim().is_empty()
            && format!("{:x}", Sha256::digest(excerpt.as_bytes())) == checksum,
    )
}

/// R15/F01/F13: the same locator for the families that report positions in `params.format.locations`
/// - the JSON and XML paths, mail parts and headers, ODF headings, cells and pages, RTF paragraphs
/// and Python symbols. Those routes report a value rather than a span, so the check is on the
/// value: it must appear in the projection this attempt wrote, and it must hash to the checksum.
///
/// A location that the receipt names more than once under one kind and path is refused rather than
/// resolved by picking one, because picking silently is how two different things become one claim.
fn verify_format_location_anchor(
    conn: &rusqlite::Connection,
    source: &str,
    revision: &str,
    position: &serde_json::Value,
    checksum: &str,
) -> Option<bool> {
    use sha2::{Digest, Sha256};
    let job = position["job_id"].as_str()?;
    let attempt = i64::try_from(position["attempt"].as_u64()?).ok()?;
    let kind = position["kind"].as_str()?;
    let path = position["path"].as_str()?;
    let (input, job_state, attempt_state, loss, text, later): (
        String,
        String,
        String,
        String,
        Option<String>,
        i64,
    ) = conn
        .query_row(
            "SELECT j.input_ref,j.state,a.state,o.content,
                    (SELECT content FROM job_outputs WHERE job_id=j.job_id AND attempt=a.attempt AND kind='text'),
                    (SELECT COUNT(*) FROM job_attempts WHERE job_id=j.job_id AND attempt>?2)
             FROM jobs j JOIN job_attempts a ON a.job_id=j.job_id
             JOIN job_outputs o ON o.job_id=a.job_id AND o.attempt=a.attempt AND o.kind='loss_report'
             WHERE j.job_id=?1 AND a.attempt=?2",
            rusqlite::params![job, attempt],
            |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    r.get(2)?,
                    r.get(3)?,
                    r.get(4)?,
                    r.get(5)?,
                ))
            },
        )
        .ok()?;
    if input != source || job_state != "succeeded" || attempt_state != "succeeded" || later != 0 {
        return Some(false);
    }
    let text = text?;
    let wire: String = conn
        .query_row(
            "SELECT request_json FROM job_attempts WHERE job_id=?1 AND attempt=?2",
            rusqlite::params![job, attempt],
            |r| r.get(0),
        )
        .ok()?;
    let request: serde_json::Value = serde_json::from_str(&wire).ok()?;
    if request["job_id"] != job
        || request["attempt"] != serde_json::json!(attempt)
        || request["inputs"][0]["sha256"] != revision
        || request["capability"].as_str().unwrap_or("").is_empty()
    {
        return Some(false);
    }
    let loss: serde_json::Value = serde_json::from_str(&loss).ok()?;
    let entries = loss["params"]["format"]["locations"].as_array()?;
    // Several families reuse one path for many locations - every import in a Python source is
    // `/symbols/import`, for instance - so an optional `where` of reported fields can narrow the
    // match. It compares what the receipt said, field for field; it invents no new discriminator.
    let where_ = position
        .get("where")
        .cloned()
        .unwrap_or_else(|| serde_json::Value::Object(Default::default()));
    let where_map = where_.as_object()?;
    let matching: Vec<&serde_json::Value> = entries
        .iter()
        .filter(|entry| {
            entry["kind"].as_str() == Some(kind)
                && entry["path"].as_str() == Some(path)
                && where_map
                    .iter()
                    .all(|(field, value)| entry.get(field) == Some(value))
        })
        .collect();
    if matching.len() != 1 {
        return Some(false);
    }
    let value = matching[0]["value"].as_str()?;
    if value.trim().is_empty() || !text.contains(value) {
        return Some(false);
    }
    Some(format!("{:x}", Sha256::digest(value.as_bytes())) == checksum)
}

/// Shared by anchor creation and independent read-time resolution. Verification establishes
/// locator provenance only; it never grants recognition accuracy or business approval.
fn verify_anchor_location(
    conn: &Connection,
    source_id: &str,
    revision: &str,
    position: &serde_json::Value,
    checksum: &str,
) -> Option<bool> {
    use sha2::{Digest, Sha256};
    if position["type"] == "pdf_line" {
        return pdf_locator::verify(conn, source_id, revision, position, checksum);
    }
    if position["type"] == "ocr_line" {
        return ocr_locator::verify(conn, source_id, revision, position, checksum);
    }
    if position["type"] == "time" {
        return verify_time_anchor(conn, source_id, revision, position, checksum);
    }
    if position["type"] == "epub" {
        return verify_epub_anchor(conn, source_id, revision, position, checksum);
    }
    if position["type"] == "worker_structure" {
        return verify_structure_anchor(conn, source_id, revision, position, checksum);
    }
    if position["type"] == "format_location" {
        return verify_format_location_anchor(conn, source_id, revision, position, checksum);
    }
    if position["type"] != "text" {
        return None;
    }
    let start = usize::try_from(position["start"].as_u64()?).ok()?;
    let end = usize::try_from(position["end"].as_u64()?).ok()?;
    let bytes =
        archeaxis_store_sqlite::raw_objects::read_bounded(conn, revision, 4 * 1024 * 1024).ok()?;
    let text = std::str::from_utf8(&bytes).ok()?;
    let excerpt = text.get(start..end)?;
    Some(format!("{:x}", Sha256::digest(excerpt.as_bytes())) == checksum)
}

#[derive(Deserialize)]
struct AnchorBody {
    revision: String,
    position: String,
    checksum: Option<String>,
}

async fn create_anchor(
    State(state): State<AppState>,
    Path(source_id): Path<String>,
    headers: HeaderMap,
    Json(body): Json<AnchorBody>,
) -> impl IntoResponse {
    if request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    if body.position.len() > 16 * 1024
        || serde_json::from_str::<serde_json::Value>(&body.position)
            .ok()
            .is_none_or(|v| !v.is_object())
    {
        return (
            StatusCode::BAD_REQUEST,
            "position must be a bounded JSON locator object",
        )
            .into_response();
    }
    with_store(state, move |conn| {
        let revision: rusqlite::Result<Option<String>> = conn
            .query_row(
                "SELECT sha256 FROM sources WHERE source_id=?1",
                [&source_id],
                |r| r.get(0),
            )
            .optional();
        match revision {
            Ok(Some(revision)) if revision == body.revision => {}
            Ok(Some(_)) => {
                return (
                    StatusCode::BAD_REQUEST,
                    "anchor revision must identify the immutable original",
                )
                    .into_response();
            }
            Ok(None) => return StatusCode::NOT_FOUND.into_response(),
            Err(error) => {
                return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response();
            }
        }
        let mut position: serde_json::Value = serde_json::from_str(&body.position).unwrap();
        let mut location_status = "unverified";
        if let Some(checksum) = body.checksum {
            let validation = verify_anchor_location(
                conn, &source_id, &body.revision, &position, &checksum,
            );
            if validation != Some(true) {
                return (
                    StatusCode::BAD_REQUEST,
                    "locator/checksum does not match the immutable source, a verified ASR cue, an \
                     epub paragraph, or the worker structure named by this attempt",
                )
                    .into_response();
            }
            position["checksum"] = serde_json::json!(checksum);
            location_status = "located";
        }
        position["location_status"] = serde_json::json!(location_status);
        match anchor::add_anchor(conn, &source_id, &body.revision, &position.to_string()) {
            Ok(id) => (
                StatusCode::CREATED,
                Json(serde_json::json!({"anchor_id": id,"source_id":source_id,"source_revision":body.revision,"position":position.to_string(),"checksum":position.get("checksum"),"location_status":location_status})),
            )
                .into_response(),
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        }
    })
    .await
}

async fn source_job_transform(
    State(state): State<AppState>,
    Path((source_id, job_id)): Path<(String, String)>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        // Every extraction route stores its projection in `transforms.text` - the PDF
        // worker's extracted text, the OCR reading, a subtitle's cue text, an archive's
        // inventory listing - so this route reads whichever one the job produced. It used to
        // filter `j.kind='text'`, which answered `404` for a succeeded PDF, OCR, Office,
        // HTML, canvas, subtitle, archive, media or ASR job that had a perfectly readable
        // projection; nothing asserted that refusal, which is how a text-only filter
        // survived under a route the contract lists as source-bound transform readback.
        let projection: rusqlite::Result<Option<(i64, String, String)>> = conn
            .query_row(
                "SELECT t.transform_id, s.sha256, t.text
             FROM jobs j JOIN sources s ON s.source_id=j.input_ref
             JOIN transforms t ON t.transform_id=j.transform_id AND t.source_id=s.source_id
             WHERE j.job_id=?1 AND j.input_ref=?2 AND j.state='succeeded'",
                rusqlite::params![job_id, source_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .optional();
        match projection {
            Ok(Some((transform_id, raw_sha256, content))) => (
                StatusCode::OK,
                Json(serde_json::json!({
                    "source_id": source_id,
                    "job_id": job_id,
                    "transform_id": transform_id,
                    "raw_sha256": raw_sha256,
                    "content": content,
                })),
            )
                .into_response(),
            Ok(None) => (
                StatusCode::NOT_FOUND,
                "succeeded source-bound transform not found",
            )
                .into_response(),
            Err(error) => (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        }
    })
    .await
}

/// Read the persisted Evidence anchor projection without exposing source bodies.
/// The Core remains the sole writer; this route only joins the canonical anchor
/// and source hashes for the desktop Evidence Center.
async fn evidence_anchors(State(state): State<AppState>) -> impl IntoResponse {
    with_store(state, |conn| {
        let mut statement = match conn.prepare(
            "SELECT a.anchor_id, a.source_id, s.sha256, a.source_revision, a.position, a.created_at, s.original_name,
                    (SELECT k.knowledge_id FROM knowledge k WHERE k.anchor_id = a.anchor_id ORDER BY k.rowid DESC LIMIT 1),
                    (SELECT k.status FROM knowledge k WHERE k.anchor_id = a.anchor_id ORDER BY k.rowid DESC LIMIT 1)
             FROM anchors a JOIN sources s ON s.source_id = a.source_id
             ORDER BY a.created_at ASC, a.anchor_id ASC",
        ) {
            Ok(statement) => statement,
            Err(error) => {
                return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response();
            }
        };
        let rows = match statement.query_map([], |row| {
            // A bare positional anchor stores an opaque locator, while an anchor created from
            // a transform stores the quoted selection inside that locator. The quote and the
            // source's own file name are surfaced as their own fields so a reader does not have
            // to parse the locator or resolve an id, and the quote stays null when there is none.
            let position = row.get::<_, String>(4)?;
            let quote = serde_json::from_str::<serde_json::Value>(&position)
                .ok()
                .and_then(|value| value.get("quote").and_then(|quote| quote.as_str()).map(str::to_string));
            Ok(serde_json::json!({
                "anchor_id": row.get::<_, String>(0)?,
                "source_id": row.get::<_, String>(1)?,
                "raw_sha256": row.get::<_, String>(2)?,
                "source_revision": row.get::<_, String>(3)?,
                "position": position,
                "created_at": row.get::<_, String>(5)?,
                "source_name": row.get::<_, String>(6)?,
                "quote": quote,
                // The knowledge this anchor is attached to, when a review candidate cites it, so a
                // reader can go from "this is the quoted evidence" to "review it" without a search.
                // Null for a bare positional anchor that no knowledge row references.
                "knowledge_id": row.get::<_, Option<String>>(7)?,
                "knowledge_status": row.get::<_, Option<String>>(8)?,
            }))
        }) {
            Ok(rows) => rows,
            Err(error) => {
                return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response();
            }
        };
        let mut items = Vec::new();
        for row in rows {
            match row {
                Ok(item) => items.push(item),
                Err(error) => {
                    return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response();
                }
            }
        }
        (StatusCode::OK, Json(serde_json::json!({"items": items}))).into_response()
    })
    .await
}

/// R15/F15: what is inside a container, and which parts could be read.
///
/// The relation is the one recorded at import time (an `import` origin whose reference
/// names the container), so this endpoint answers a question about provenance rather
/// than inventing a second store of relations. A member whose name resolved to no route
/// appears with `readable: false` and no job: it is kept, and it is visible. A member that is
/// itself a container past the Core's nesting budget appears with `nesting_limited: true`,
/// because its route exists and only its own expansion stopped.
async fn source_members(
    State(state): State<AppState>,
    Path(source_id): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        let exists: bool = conn
            .query_row(
                "SELECT EXISTS(SELECT 1 FROM sources WHERE source_id=?1)",
                [&source_id],
                |row| row.get(0),
            )
            .unwrap_or(false);
        if !exists {
            return (StatusCode::NOT_FOUND, "source not found").into_response();
        }
        match container::members_of(conn, &source_id) {
            Ok(members) => {
                let readable = members.iter().filter(|member| member.readable).count();
                // A kept member with no job is either unread or stopped by the nesting budget;
                // calling both "custody only" would claim a route does not exist when it does.
                let mut rows = Vec::with_capacity(members.len());
                let mut nesting_limited = 0usize;
                for member in members {
                    let stopped = !member.readable
                        && member.job_id.is_none()
                        && matches!(
                            container::member_lane(conn, &source_id, &member.member),
                            Ok(container::MemberLane::NestingLimited)
                        );
                    if stopped {
                        nesting_limited += 1;
                    }
                    rows.push(serde_json::json!({
                        "source_id": member.source_id,
                        "member": member.member,
                        "origin_ref": member.origin_ref,
                        "original_name": member.original_name,
                        "sha256": member.sha256,
                        "readable": member.readable,
                        "job_id": member.job_id,
                        "nesting_limited": stopped,
                    }));
                }
                (
                    StatusCode::OK,
                    Json(serde_json::json!({
                        "container_source_id": source_id,
                        "member_count": rows.len(),
                        "readable_count": readable,
                        "custody_only_count": rows.len() - readable - nesting_limited,
                        "nesting_limited_count": nesting_limited,
                        "members": rows,
                        "note": "these are the members imported from this container, not its whole inventory: \
                                 members beyond the extraction caps, encrypted members and unreadable ones are \
                                 reported by the archive job's own receipt, and readable means a transform exists \
                                 rather than that the content was understood. A member with nesting_limited true is \
                                 itself a container whose own expansion stopped at the nesting budget, so it is \
                                 kept and queued work was not created for it"
                    })),
                )
                    .into_response()
            }
            Err(error) => (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        }
    })
    .await
}

/// Read the pages a PDF was rendered into, each with the text its own OCR job produced.
///
/// R15/F06: the render and the OCR job are two chained steps, so this answers from the
/// relation recorded when the page was imported. A page whose OCR has not produced text is
/// reported with `recognised` false and no text - absence is stated, never filled in.
async fn source_pages(
    State(state): State<AppState>,
    Path(source_id): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        let exists: bool = conn
            .query_row(
                "SELECT EXISTS(SELECT 1 FROM sources WHERE source_id=?1)",
                [&source_id],
                |row| row.get(0),
            )
            .unwrap_or(false);
        if !exists {
            return (StatusCode::NOT_FOUND, "source not found").into_response();
        }
        match archeaxis_application::ocr::pages_of(conn, &source_id) {
            Ok(pages) => {
                let read = pages.iter().filter(|page| page.recognised).count();
                (
                    StatusCode::OK,
                    Json(serde_json::json!({
                        "pdf_source_id": source_id,
                        "page_count": pages.len(),
                        "recognised_count": read,
                        "pages": pages
                            .into_iter()
                            .map(|page| {
                                serde_json::json!({
                                    "page": page.page,
                                    "source_id": page.source_id,
                                    "origin_ref": page.origin_ref,
                                    "original_name": page.original_name,
                                    "sha256": page.sha256,
                                    "recognised": page.recognised,
                                    "text": page.text,
                                    "job_id": page.job_id,
                                })
                            })
                            .collect::<Vec<_>>(),
                        "note": "only the pages this source was rendered into are listed: a PDF whose own \
                                 text layer was readable chains nothing, and recognised means the OCR route \
                                 produced text for that page, not that the reading is correct"
                    })),
                )
                    .into_response()
            }
            Err(error) => (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        }
    })
    .await
}

/// Read the durable jobs associated with one source. This is a projection of Core
/// job truth; it deliberately does not infer a default job or expose output content.
async fn source_jobs(
    State(state): State<AppState>,
    Path(source_id): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        let exists: bool = match conn.query_row(
            "SELECT EXISTS(SELECT 1 FROM sources WHERE source_id=?1)",
            [&source_id],
            |row| row.get(0),
        ) {
            Ok(exists) => exists,
            Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        };
        if !exists {
            return (StatusCode::NOT_FOUND, "source not found").into_response();
        }

        let mut statement = match conn.prepare(
            "SELECT j.job_id,j.kind,j.state,j.input_ref,j.created_at,j.completed_at,a.attempt,a.error
             FROM jobs j
             LEFT JOIN job_attempts a ON a.job_id=j.job_id
                 AND a.attempt=(SELECT MAX(latest.attempt) FROM job_attempts latest WHERE latest.job_id=j.job_id)
             WHERE j.input_ref=?1
             ORDER BY j.completed_at DESC,j.created_at DESC,j.job_id ASC LIMIT 51",
        ) {
            Ok(statement) => statement,
            Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        };
        let rows = match statement.query_map([&source_id], |row| {
            Ok(serde_json::json!({
                "job_id": row.get::<_, String>(0)?,
                "kind": row.get::<_, String>(1)?,
                "state": row.get::<_, String>(2)?,
                "input_ref": row.get::<_, Option<String>>(3)?,
                "created_at": row.get::<_, String>(4)?,
                "completed_at": row.get::<_, Option<String>>(5)?,
                "attempt": row.get::<_, Option<i64>>(6)?,
                "error": row.get::<_, Option<String>>(7)?,
            }))
        }) {
            Ok(rows) => rows,
            Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        };
        let mut jobs = Vec::new();
        for row in rows {
            match row {
                Ok(job) => jobs.push(job),
                Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
            }
        }
        let jobs_capped = jobs.len() > 50;
        jobs.truncate(50);
        (StatusCode::OK, Json(serde_json::json!({"source_id": source_id, "jobs": jobs, "jobs_capped": jobs_capped}))).into_response()
    }).await
}

async fn knowledge_qualification(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        // One resolver for every consumer: the identity is immutable, so the
        // qualification projection reports currentness/limits beside it instead of
        // letting "exists" stand in for "still a current basis".
        let reference = object_reference::Reference::Knowledge {
            knowledge_id: id.clone(),
        };
        match object_reference::resolve(conn, &reference) {
            Ok(value) => (
                StatusCode::OK,
                Json(serde_json::json!({
                    "knowledge_id": id,
                    "exists": true,
                    "active": value["active"],
                    "status": value["status"],
                    "currentness": value["currentness"],
                    "superseded_by": value["superseded_by"],
                    "successor_count": value["successor_count"],
                    "valid_to": value["valid_to"],
                })),
            )
                .into_response(),
            Err(archeaxis_domain::document::Error::NotFound) => {
                (StatusCode::NOT_FOUND, "knowledge not found").into_response()
            }
            Err(archeaxis_domain::document::Error::Invalid(message)) => {
                (StatusCode::BAD_REQUEST, message).into_response()
            }
            Err(archeaxis_domain::document::Error::Sql(error)) => {
                (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response()
            }
            Err(archeaxis_domain::document::Error::Conflict(_)) => {
                (StatusCode::CONFLICT, "knowledge qualification conflict").into_response()
            }
        }
    })
    .await
}

fn v3_source_type(knowledge_type: &str, created_by: &str) -> &'static str {
    if created_by.contains("machine")
        || created_by.contains("python")
        || created_by.contains("worker")
    {
        return "machine_candidate";
    }
    match knowledge_type {
        "PERSONAL_DEFINITION" => "personal_definition",
        "PERSONAL_EXPERIENCE" => "personal_experience",
        "PROJECT_OBSERVATION" | "OBSERVATION" => "project_observation",
        "AUTHORITATIVE_REFERENCE" => "authoritative_reference",
        "EXTERNAL_DOCUMENT" => "external_document",
        "RESEARCH_RESULT" => "research_result",
        _ => "derived_inference",
    }
}

fn v3_owner(created_by: &str, source_type: &str) -> &'static str {
    if source_type == "machine_candidate"
        || created_by.contains("machine")
        || created_by.contains("python")
        || created_by.contains("worker")
    {
        "machine"
    } else if created_by == "owner" || created_by == "human" {
        "human"
    } else {
        "system"
    }
}

fn v3_status(status: &str, has_successor: bool) -> &'static str {
    match status {
        "candidate" => "candidate",
        "accepted" => "accepted",
        "rejected" => "rejected",
        "deprecated" if has_successor => "superseded",
        "deprecated" => "rejected",
        _ => "candidate",
    }
}

fn v3_relation_ids(
    conn: &Connection,
    sql: &str,
    knowledge_id: &str,
) -> rusqlite::Result<Vec<String>> {
    let mut statement = conn.prepare(sql)?;
    let rows = statement.query_map([knowledge_id], |row| row.get::<_, String>(0))?;
    rows.collect()
}

async fn knowledge_v3(State(state): State<AppState>, Path(id): Path<String>) -> impl IntoResponse {
    with_store(state, move |conn| {
        let row = match conn
            .query_row(
                "SELECT knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, created_at
                 FROM knowledge WHERE knowledge_id=?1",
                [&id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, Option<String>>(4)?,
                        row.get::<_, Option<String>>(5)?,
                        row.get::<_, String>(6)?,
                        row.get::<_, String>(7)?,
                    ))
                },
            )
            .optional()
        {
            Ok(Some(value)) => value,
            Ok(None) => return (StatusCode::NOT_FOUND, "knowledge not found").into_response(),
            Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        };
        let (knowledge_id, knowledge_type, body, status, evidence_status, anchor_id, created_by, created_at) = row;
        let metadata = match conn.query_row(
                "SELECT source_type, owner, support_level, confidence, risk_level,
                        valid_from, valid_to, external_evidence, requires_human_review
                 FROM knowledge_v3_metadata WHERE knowledge_id=?1",
                [&knowledge_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, Option<f64>>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, Option<String>>(5)?,
                        row.get::<_, Option<String>>(6)?,
                        row.get::<_, String>(7)?,
                        row.get::<_, bool>(8)?,
                    ))
                },
            ).optional() {
            Ok(value) => value,
            Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        };
        let source_type = metadata
            .as_ref()
            .map(|value| value.0.as_str())
            .unwrap_or_else(|| v3_source_type(&knowledge_type, &created_by));
        let owner = metadata
            .as_ref()
            .map(|value| value.1.as_str())
            .unwrap_or_else(|| v3_owner(&created_by, source_type));
        let supersedes = match v3_relation_ids(
            conn,
            "SELECT old_knowledge_id FROM knowledge_supersedes WHERE new_knowledge_id=?1 ORDER BY created_at, rowid",
            &knowledge_id,
        ) {
            Ok(values) => values,
            Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        };
        let superseded_by = match v3_relation_ids(
            conn,
            "SELECT new_knowledge_id FROM knowledge_supersedes WHERE old_knowledge_id=?1 ORDER BY created_at, rowid",
            &knowledge_id,
        ) {
            Ok(values) => values,
            Err(error) => return (StatusCode::INTERNAL_SERVER_ERROR, error.to_string()).into_response(),
        };
        let has_successor = !superseded_by.is_empty();
        let source_id = match anchor_id.as_deref() {
            Some(anchor) => conn
                .query_row("SELECT source_id FROM anchors WHERE anchor_id=?1", [anchor], |row| row.get::<_, String>(0))
                .optional()
                .unwrap_or(None),
            None => None,
        };
        let updated_at = conn
            .query_row(
                "SELECT COALESCE(MAX(created_at), ?1) FROM review_events WHERE knowledge_id=?2",
                rusqlite::params![created_at, knowledge_id],
                |row| row.get::<_, String>(0),
            )
            .unwrap_or_else(|_| created_at.clone());
        let (support_level, confidence, risk_level, valid_from, valid_to, external_evidence, requires_human_review) =
            if let Some((_, _, support, confidence, risk, from, to, evidence, review)) = metadata.as_ref() {
                let evidence = serde_json::from_str::<Vec<String>>(&evidence).unwrap_or_default();
                (support.clone(), *confidence, risk.clone(), from.clone(), to.clone(), evidence, *review)
            } else {
                (
                    if evidence_status.is_some() { "weak".to_string() } else { "none".to_string() },
                    None,
                    "low".to_string(),
                    None,
                    None,
                    evidence_status
                        .filter(|value| !value.trim().is_empty())
                        .map(|value| vec![value])
                        .unwrap_or_default(),
                    owner == "machine" || status == "candidate",
                )
            };
        (
            StatusCode::OK,
            Json(serde_json::json!({
                "schema_version": "3.0.0",
                "source_type": source_type,
                "owner": owner,
                "status": v3_status(&status, has_successor),
                "support_level": support_level,
                "confidence": confidence,
                "risk_level": risk_level,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "supersedes": supersedes,
                "superseded_by": superseded_by,
                "external_evidence": external_evidence,
                "requires_human_review": requires_human_review,
                "knowledge_id": knowledge_id,
                "source_id": source_id,
                "anchor_id": anchor_id,
                "title": knowledge_type,
                "body": body,
                "created_at": created_at,
                "updated_at": updated_at,
                "version": knowledge::review_version(conn,&knowledge_id).unwrap_or_default(),
            })),
        )
            .into_response()
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
    #[serde(default)]
    v3: Option<KnowledgeV3Body>,
}

#[derive(Deserialize)]
struct KnowledgeFromTransformBody {
    knowledge_type: String,
    body: String,
    source_id: String,
    job_id: String,
    transform_id: i64,
    selection_start_utf16: usize,
    selection_end_utf16: usize,
    quote: String,
}

#[derive(Deserialize)]
struct KnowledgeV3Body {
    source_type: String,
    owner: String,
    #[serde(default = "default_support_level")]
    support_level: String,
    #[serde(default)]
    confidence: Option<f64>,
    #[serde(default = "default_risk_level")]
    risk_level: String,
    #[serde(default)]
    valid_from: Option<String>,
    #[serde(default)]
    valid_to: Option<String>,
    #[serde(default)]
    external_evidence: Vec<String>,
    #[serde(default = "default_requires_human_review")]
    requires_human_review: bool,
}

fn default_support_level() -> String {
    "none".to_string()
}
fn default_risk_level() -> String {
    "low".to_string()
}
fn default_requires_human_review() -> bool {
    true
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
    if let Some(v3) = &body.v3 {
        if (actor == "machine" && v3.owner != "machine")
            || (actor == "human" && v3.owner == "machine")
        {
            return (
                StatusCode::BAD_REQUEST,
                "V3 owner must match the trusted request actor",
            )
                .into_response();
        }
    }
    with_store(state, move |conn| {
        let metadata = body.v3.map(|v3| knowledge::KnowledgeV3Metadata {
            source_type: v3.source_type,
            owner: v3.owner,
            support_level: v3.support_level,
            confidence: v3.confidence,
            risk_level: v3.risk_level,
            valid_from: v3.valid_from,
            valid_to: v3.valid_to,
            external_evidence: v3.external_evidence,
            requires_human_review: v3.requires_human_review,
        });
        match knowledge::create_knowledge_v3(
            conn,
            &body.knowledge_type,
            &body.body,
            &body.status,
            None,
            None,
            &body.created_by,
            metadata.as_ref(),
        ) {
            Ok(id) => (
                StatusCode::CREATED,
                Json(serde_json::json!({"knowledge_id": id})),
            )
                .into_response(),
            Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
        }
    })
    .await
}

async fn create_knowledge_from_transform(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<KnowledgeFromTransformBody>,
) -> impl IntoResponse {
    match request_actor(&headers) {
        Ok("human") => {}
        Ok(_) => {
            return (
                StatusCode::FORBIDDEN,
                "source-bound Candidate creation requires a human actor",
            )
                .into_response();
        }
        Err(status) => return (status, "unknown actor").into_response(),
    }
    if body.body.trim().is_empty() {
        return (StatusCode::BAD_REQUEST, "Candidate body must not be empty").into_response();
    }
    let metadata = knowledge::KnowledgeV3Metadata {
        source_type: v3_source_type(&body.knowledge_type, "human").to_string(),
        owner: "human".to_string(),
        support_level: "none".to_string(),
        confidence: None,
        risk_level: "low".to_string(),
        valid_from: None,
        valid_to: None,
        external_evidence: Vec::new(),
        requires_human_review: true,
    };
    with_store(
        state,
        move |conn| match knowledge::create_knowledge_v3_from_transform(
            conn,
            &body.knowledge_type,
            &body.body,
            "human",
            &body.source_id,
            &body.job_id,
            body.transform_id,
            body.selection_start_utf16,
            body.selection_end_utf16,
            &body.quote,
            &metadata,
        ) {
            Ok((knowledge_id, anchor_id, raw_sha256)) => (
                StatusCode::CREATED,
                Json(serde_json::json!({
                    "knowledge_id": knowledge_id,
                    "anchor_id": anchor_id,
                    "source_id": body.source_id,
                    "job_id": body.job_id,
                    "transform_id": body.transform_id,
                    "raw_sha256": raw_sha256,
                    "status": "candidate",
                    "requires_human_review": true,
                })),
            )
                .into_response(),
            Err(error) => (StatusCode::BAD_REQUEST, error.to_string()).into_response(),
        },
    )
    .await
}

#[derive(Deserialize)]
struct ReviewBody {
    action: String,
    reviewer: String,
    #[serde(default)]
    note: Option<String>,
    // C06: a modified review may carry the corrected content so the supersede
    // successor is created with the new version, not a clone of the old body.
    #[serde(default)]
    new_body: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct VersionedReviewBody {
    action: String,
    reviewer: String,
    expected_version: String,
    note: Option<String>,
    new_body: Option<String>,
}
async fn review_versioned(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<String>,
    Json(body): Json<VersionedReviewBody>,
) -> axum::response::Response {
    if request_actor(&headers) != Ok("human") {
        return StatusCode::FORBIDDEN.into_response();
    }
    with_store(state, move |conn| {
        match knowledge::review_checked(conn,&id,&body.action,&body.reviewer,body.note.as_deref(),body.new_body.as_deref(),Some(&body.expected_version)) {
            Ok(kid)=>Json(serde_json::json!({"knowledge_id":kid,"version":knowledge::review_version(conn,&kid).unwrap_or_default()})).into_response(),
            Err(rusqlite::Error::InvalidParameterName(message)) if message.starts_with("review_version_conflict:") => (StatusCode::CONFLICT,Json(serde_json::json!({"code":"AAK-REV-409","current_version":message.trim_start_matches("review_version_conflict:")}))).into_response(),
            Err(rusqlite::Error::QueryReturnedNoRows)=>StatusCode::NOT_FOUND.into_response(),
            Err(error)=>(StatusCode::BAD_REQUEST,error.to_string()).into_response(),
        }
    }).await
}

async fn review_decision(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<String>,
    Json(body): Json<ReviewBody>,
) -> impl IntoResponse {
    // C02/C06: acceptance/rejection/deprecation/modification are human review
    // actions; a machine actor must not self-review its own proposals (it may
    // only propose candidates and read qualification).
    if request_actor(&headers).unwrap_or("human") == "machine"
        && matches!(
            body.action.as_str(),
            "accepted" | "rejected" | "deprecated" | "modified"
        )
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
            body.new_body.as_deref(),
        ) {
            Ok(kid) => (
                StatusCode::OK,
                Json(serde_json::json!({"knowledge_id": kid})),
            )
                .into_response(),
            Err(e) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),
        }
    })
    .await
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
                        // R09: a search hit is not automatically a current basis. Report the
                        // separated currentness view next to the excerpt and the persisted status.
                        let mut item = reference_view(conn, &id);
                        if let Some(fields) = item.as_object_mut() {
                            fields.insert("status".into(), serde_json::json!(status));
                            fields.insert("head".into(), serde_json::json!(head));
                        }
                        item
                    })
                    .collect();
                if query.active_only {
                    items.retain(|item| item["active"] == true);
                }
                // R08: extracted text is retrievable too, attributed to the original
                // file and the engine that produced it - without claiming the text is
                // knowledge (see domain::search::search_transforms).
                let transforms: Vec<serde_json::Value> =
                    match search::search_transforms(conn, &query.q, 20) {
                        Ok(rows) => rows
                            .into_iter()
                            .map(|(transform_id, source_id, engine, head)| {
                                serde_json::json!({
                                    "transform_id": transform_id,
                                    "source_id": source_id,
                                    "engine": engine,
                                    "head": head,
                                })
                            })
                            .collect(),
                        Err(e) => {
                            return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
                                .into_response();
                        }
                    };
                let documents = match archeaxis_domain::document::search(conn, &query.q) {
                    Ok(rows) => rows,
                    Err(e) => return documents::failure(e),
                };
                Json(serde_json::json!({
                    "count": items.len(),
                    "items": items,
                    "document_count": documents.len(),
                    "documents": documents,
                    "transform_count": transforms.len(),
                    "transforms": transforms,
                }))
                .into_response()
            }
            Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        }
    })
    .await
}

/// R08: quality facts for one job - engine, coverage, loss and region counts.
///
/// Facts only: no accuracy figure is produced, and a recogniser's confidence is
/// never presented as accuracy.
async fn job_quality(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
) -> impl IntoResponse {
    with_store(state, move |conn| {
        let row = conn.query_row(
            "SELECT state, engine, loss_receipt FROM jobs WHERE job_id=?1",
            [&job_id],
            |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, Option<String>>(1)?,
                    r.get::<_, Option<String>>(2)?,
                ))
            },
        );
        let (job_state, engine, receipt) = match row {
            Ok(values) => values,
            Err(rusqlite::Error::QueryReturnedNoRows) => {
                return (StatusCode::NOT_FOUND, "unknown job").into_response();
            }
            Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        };
        let receipt: serde_json::Value = receipt
            .as_deref()
            .and_then(|raw| serde_json::from_str(raw).ok())
            .unwrap_or(serde_json::Value::Null);
        let params = receipt.get("params").cloned().unwrap_or(serde_json::Value::Null);
        let region_count = params
            .get("regions")
            .and_then(|value| value.as_array())
            .map(|regions| regions.len())
            .unwrap_or(0);
        let loss_count = receipt
            .get("losses")
            .and_then(|value| value.as_array())
            .map(|losses| losses.len())
            .unwrap_or(0);
        Json(serde_json::json!({
            "job_id": job_id,
            "state": job_state,
            "engine": engine,
            "engine_version": receipt.get("engine_version").cloned().unwrap_or(serde_json::Value::Null),
            "coverage": receipt.get("coverage").cloned().unwrap_or(serde_json::Value::Null),
            "covered": receipt.get("covered").cloned().unwrap_or(serde_json::Value::Null),
            "total": receipt.get("total").cloned().unwrap_or(serde_json::Value::Null),
            "loss_count": loss_count,
            "region_count": region_count,
            "pages": params.get("pages").cloned().unwrap_or(serde_json::Value::Null),
            "core_artifact_adoption": params.get("core_artifact_adoption").cloned().unwrap_or(serde_json::Value::Null),
            "note": "facts only; model or recogniser confidence is not accuracy",
        }))
        .into_response()
    })
    .await
}

async fn workspace_info(State(state): State<AppState>) -> impl IntoResponse {
    with_store(state, move |conn| match workspace_info_json(conn) {
        Ok(s) => {
            let v: serde_json::Value = serde_json::from_str(&s).unwrap_or(serde_json::json!({}));
            Json(v).into_response()
        }
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    })
    .await
}

fn base64_decode(s: &str) -> Option<Vec<u8>> {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.decode(s).ok()
}

// worker job endpoints (worker-protocol slice): durable enqueue + terminal receipt.
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
                Ok(Some(actual)) => (
                    StatusCode::ACCEPTED,
                    Json(serde_json::json!({"job_id": body.job_id, "state": actual})),
                )
                    .into_response(),
                _ => (StatusCode::INTERNAL_SERVER_ERROR, "job readback failed").into_response(),
            },
            Err(e) => job_error_response(e),
        }
    })
    .await
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
        jobs::JobError::MediaTypeNotAccepted { .. } => StatusCode::BAD_REQUEST,
        jobs::JobError::UnverifiableInput { .. } => StatusCode::BAD_REQUEST,
        // R7/G1: a disabled capability is a conflict with the workspace's own settings, not a
        // malformed request, and the body names the capability so an operator knows what to change.
        jobs::JobError::CapabilityDisabled { .. } => StatusCode::CONFLICT,
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
        return (
            StatusCode::BAD_REQUEST,
            "successful receipt requires engine and text",
        )
            .into_response();
    }
    if body.state == jobs::STATE_COMPLETED && body.error.is_some() {
        return (
            StatusCode::BAD_REQUEST,
            "successful receipt cannot contain an error",
        )
            .into_response();
    }
    if body.state == jobs::STATE_FAILED
        && (body.text.is_some() || body.loss_receipt.is_some() || body.engine.is_some())
    {
        return (
            StatusCode::BAD_REQUEST,
            "failed receipt cannot publish output",
        )
            .into_response();
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
    })
    .await
}

#[cfg(test)]
mod import_byte_budget_tests {
    use super::*;
    use base64::Engine;
    #[test]
    fn overbudget_rejection_covers_encoded_length_and_last_quantum() {
        assert_eq!(
            decode_import_content(&"!".repeat(MAX_IMPORT_BASE64_BYTES + 1)).unwrap_err(),
            StatusCode::PAYLOAD_TOO_LARGE
        );
        let encoded =
            base64::engine::general_purpose::STANDARD.encode(vec![0u8; MAX_IMPORT_BYTES + 1]);
        assert_eq!(encoded.len(), MAX_IMPORT_BASE64_BYTES);
        assert_eq!(
            decode_import_content(&encoded).unwrap_err(),
            StatusCode::PAYLOAD_TOO_LARGE
        );
        assert_eq!(
            decode_import_content("!").unwrap_err(),
            StatusCode::BAD_REQUEST
        );
    }
}
