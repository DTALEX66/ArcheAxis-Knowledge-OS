//! Independent, read-only anchor revalidation. Stored positions remain historical evidence.
use axum::{
    Json,
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
};
use rusqlite::OptionalExtension;
use serde_json::{Value, json};

use crate::{AppState, request_actor, verify_anchor_location, with_store};

fn verify_transform_selection(
    conn: &rusqlite::Connection,
    source_id: &str,
    locator: &Value,
) -> rusqlite::Result<bool> {
    let (Some(job), Some(transform), Some(start), Some(end), Some(quote)) = (
        locator["job_id"].as_str(),
        locator["transform_id"].as_i64(),
        locator["selection_start_utf16"].as_u64(),
        locator["selection_end_utf16"].as_u64(),
        locator["quote"].as_str(),
    ) else {
        return Ok(false);
    };
    let (Ok(start), Ok(end)) = (usize::try_from(start), usize::try_from(end)) else {
        return Ok(false);
    };
    if job.is_empty() || transform <= 0 || start >= end || quote.is_empty() {
        return Ok(false);
    }
    let text: Option<String> = conn
        .query_row(
            "SELECT t.text FROM jobs j JOIN transforms t
             ON t.transform_id=j.transform_id AND t.source_id=j.input_ref
             WHERE j.job_id=?1 AND j.input_ref=?2 AND j.transform_id=?3
             AND j.state='succeeded'",
            rusqlite::params![job, source_id, transform],
            |row| row.get(0),
        )
        .optional()?;
    let Some(text) = text else {
        return Ok(false);
    };
    // These offsets belong to the persisted transform, never to raw source bytes.
    let utf16: Vec<u16> = text.encode_utf16().collect();
    let Some(selected) = utf16.get(start..end) else {
        return Ok(false);
    };
    Ok(String::from_utf16(selected).is_ok_and(|value| value == quote))
}

/// GET /sources/:source_id/anchors/:anchor_id/resolve. Launch authentication applies
/// equally to human and machine readers; this endpoint performs no mutation.
pub(crate) async fn resolve(
    State(state): State<AppState>,
    Path((source_id, anchor_id)): Path<(String, String)>,
    headers: HeaderMap,
) -> impl IntoResponse {
    if let Err(status) = request_actor(&headers) {
        return status.into_response();
    }
    with_store(state, move |conn| {
        let result = (|| -> rusqlite::Result<(StatusCode, Value)> {
            let source_revision: Option<String> = conn
                .query_row(
                    "SELECT sha256 FROM sources WHERE source_id=?1",
                    [&source_id],
                    |row| row.get(0),
                )
                .optional()?;
            let stored: Option<(String, String)> = conn.query_row(
                "SELECT source_revision,position FROM anchors WHERE source_id=?1 AND anchor_id=?2",
                rusqlite::params![source_id, anchor_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            ).optional()?;
            let response =
                |status: &str, reason: &str, revision: Option<&str>, position: Option<&str>| {
                    json!({
                        "source_id": source_id, "anchor_id": anchor_id,
                        "status": status, "reason": reason,
                        "source_revision": revision, "current_source_revision": source_revision,
                        "position": position,
                        "scope": "locator_provenance_only",
                    })
                };
            if source_revision.is_none() {
                return Ok((
                    StatusCode::NOT_FOUND,
                    response("MISSING", "source_not_found", None, None),
                ));
            }
            let Some((revision, position)) = stored else {
                return Ok((
                    StatusCode::NOT_FOUND,
                    response("MISSING", "anchor_not_found_for_source", None, None),
                ));
            };
            let outcome = |status: &str, reason: &str| {
                (
                    StatusCode::OK,
                    response(status, reason, Some(&revision), Some(&position)),
                )
            };
            if source_revision.as_deref() != Some(revision.as_str()) {
                return Ok(outcome("STALE", "source_revision_changed"));
            }
            let locator: Value = match serde_json::from_str(&position) {
                Ok(Value::Object(map)) => Value::Object(map),
                _ => return Ok(outcome("UNSUPPORTED", "malformed_stored_locator")),
            };
            if locator["schema"] == "archeaxis.transform-text-selection/v1" {
                return Ok(if verify_transform_selection(conn, &source_id, &locator)? {
                    outcome("CURRENT", "transform_selection_revalidated")
                } else {
                    outcome("STALE", "transform_selection_no_longer_valid")
                });
            }
            let kind = locator["type"].as_str().unwrap_or("");
            if !matches!(
                kind,
                "text"
                    | "time"
                    | "epub"
                    | "worker_structure"
                    | "format_location"
                    | "pdf_line"
                    | "ocr_line"
            ) {
                return Ok(outcome("UNSUPPORTED", "locator_type_not_supported"));
            }
            let Some(checksum) = locator["checksum"].as_str() else {
                return Ok(outcome("UNSUPPORTED", "stored_locator_has_no_checksum"));
            };
            if kind != "text" {
                let (Some(job), Some(attempt)) =
                    (locator["job_id"].as_str(), locator["attempt"].as_i64())
                else {
                    return Ok(outcome("UNSUPPORTED", "locator_has_no_job_attempt"));
                };
                let latest: Option<i64> = conn.query_row(
                    "SELECT MAX(attempt) FROM job_attempts WHERE job_id=?1",
                    [job],
                    |row| row.get(0),
                )?;
                let exists: bool = conn.query_row(
                    "SELECT EXISTS(SELECT 1 FROM job_attempts WHERE job_id=?1 AND attempt=?2)",
                    rusqlite::params![job, attempt],
                    |row| row.get(0),
                )?;
                if !exists {
                    return Ok(outcome("MISSING", "job_attempt_not_found"));
                }
                if latest.is_some_and(|value| value > attempt) {
                    return Ok(outcome("STALE", "job_attempt_superseded"));
                }
            }
            if verify_anchor_location(conn, &source_id, &revision, &locator, checksum) == Some(true)
            {
                Ok(outcome("CURRENT", "locator_revalidated"))
            } else {
                Ok(outcome("STALE", "locator_no_longer_valid"))
            }
        })();
        match result {
            Ok((status, body)) => (status, Json(body)).into_response(),
            Err(_) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({
                    "error": "anchor_resolution_failed",
                })),
            )
                .into_response(),
        }
    })
    .await
}
