//! Per-file operation qualification over existing Core receipts, never a format-wide promise.
use crate::AppState;
use axum::{
    Json,
    extract::{Path, State},
    http::StatusCode,
    response::{IntoResponse, Response},
};
use rusqlite::{Connection, OptionalExtension};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn valid_metadata(meta: &Value, kind: &str, schema: &str) -> bool {
    meta["kind"] == kind
        && meta["schema"] == schema
        && meta["byte_length"].as_u64().is_some()
        && meta["sha256"].as_str().is_some_and(|s| {
            s.len() == 64
                && s.bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        })
}

fn usable_receipt(meta: &Value, wire: &str) -> Option<Value> {
    if wire.len() > 262144
        || !valid_metadata(meta, "loss_report", "archeaxis.loss-receipt/v1")
        || meta["byte_length"].as_u64()? != wire.len() as u64
        || meta["sha256"].as_str()? != format!("{:x}", Sha256::digest(wire.as_bytes()))
    {
        return None;
    }
    let receipt: Value = serde_json::from_str(wire).ok()?;
    for field in ["engine", "engine_version"] {
        if !receipt[field]
            .as_str()
            .is_some_and(|s| !s.trim().is_empty())
        {
            return None;
        }
    }
    // Historical PDF receipts used the package name as a fabricated version.
    // Preserve stored execution/output evidence while withholding version-bound qualification.
    if receipt["engine"] == "pymupdf-native-pdf"
        && !receipt["engine_version"]
            .as_str()
            .is_some_and(|s| archeaxis_application::attempts::pdf_engine_version(s))
    {
        return None;
    }
    Some(receipt)
}

pub(crate) async fn read(
    State(state): State<AppState>,
    Path((source, job)): Path<(String, String)>,
) -> Response {
    crate::with_store(state, move |conn| match project(conn, &source, &job) {
        Ok(Some(value)) => Json(value).into_response(),
        Ok(None) => StatusCode::NOT_FOUND.into_response(),
        Err(_) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            "format qualification unavailable",
        )
            .into_response(),
    })
    .await
}

fn project(conn: &Connection, source: &str, job: &str) -> rusqlite::Result<Option<Value>> {
    let row: Option<(String, String, String, String)> = conn.query_row(
        "SELECT s.sha256,j.kind,j.state,s.original_name FROM sources s JOIN jobs j ON j.input_ref=s.source_id WHERE s.source_id=?1 AND j.job_id=?2",
        rusqlite::params![source,job], |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).optional()?;
    let Some((sha, kind, state, name)) = row else {
        return Ok(None);
    };
    let latest: Option<(i64, String)> = conn
        .query_row(
            "SELECT attempt,state FROM job_attempts WHERE job_id=?1 ORDER BY attempt DESC LIMIT 1",
            [job],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    let attempt = latest.as_ref().map(|r| r.0);
    let terminal_success =
        state == "succeeded" && latest.as_ref().is_some_and(|r| r.1 == "succeeded");
    let mut outputs = Vec::new();
    let mut engine = Value::Null;
    let mut engine_version = Value::Null;
    let mut losses = Value::Null;
    let mut text = false;
    let mut usable_loss = false;
    if let Some(attempt) = attempt {
        let mut stmt = conn.prepare("SELECT kind,metadata_json,CASE WHEN kind='loss_report' AND length(CAST(content AS BLOB))<=262144 THEN content ELSE NULL END FROM job_outputs WHERE job_id=?1 AND attempt=?2 ORDER BY kind LIMIT 51")?;
        for result in stmt.query_map(rusqlite::params![job, attempt], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, Option<String>>(2)?,
            ))
        })? {
            let (output_kind, metadata, loss) = result?;
            // Malformed or bounded-out evidence downgrades qualification; it does not
            // erase the separately persisted successful execution state.
            let meta: Value = serde_json::from_str(&metadata).unwrap_or(Value::Null);
            text |= output_kind == "text" && valid_metadata(&meta, "text", "archeaxis.text/v1");
            outputs.push(json!({"kind":output_kind,"sha256":meta["sha256"],"byte_length":meta["byte_length"],"schema":meta["schema"]}));
            if let Some(receipt) = loss.as_deref().and_then(|wire| usable_receipt(&meta, wire)) {
                usable_loss = true;
                engine = receipt["engine"].clone();
                engine_version = receipt["engine_version"].clone();
                losses = receipt["losses"]
                    .as_array()
                    .map(|v| json!(v.len()))
                    .unwrap_or(Value::Null);
            }
        }
    }
    let capped = outputs.len() > 50;
    outputs.truncate(50);
    let evidence_complete = text && usable_loss && !capped;
    let status = if terminal_success && evidence_complete {
        "QUALIFIED"
    } else if state == "failed" {
        "FAILED"
    } else if state == "cancelled" {
        "CANCELLED"
    } else if attempt.is_none() {
        "NOT_EXECUTED"
    } else {
        "UNVERIFIED"
    };
    let capability = archeaxis_application::attempts::route_for_kind(&kind).map(|r| r.0);
    let media_type = archeaxis_application::attempts::resolve_media_type(&kind, &name).ok();
    let operation = |status: &str, scope: &str| json!({"qualification_version":1,"status":status,"scope":scope});
    // Custody is a persisted reference, not a fresh integrity audit. Original export and
    // native-format editing/roundtrip are different operations from a derived text view.
    Ok(Some(json!({
        "schema":"archeaxis.file-format-qualification/v1",
        "qualification_version":1,"core_version":env!("CARGO_PKG_VERSION"),
        "source_id":source,"source_revision":sha,"job_id":job,"job_kind":kind,"job_state":state,
        "attempt":attempt,"attempt_state":latest.as_ref().map(|r|r.1.as_str()),
        "execution_succeeded":terminal_success,"qualification_evidence":if evidence_complete{"COMPLETE"}else{"INCOMPLETE"},
        "capability":capability,"media_type":media_type,"engine":engine,"engine_version":engine_version,
        "operations":{
            "store":operation("RECORDED","ORIGINAL_CAS_REFERENCE; integrity audit not performed"),
            "preview":operation(status,"DERIVED_TEXT_PROJECTION; native visual fidelity unqualified"),
            "extract":operation(status,"DECLARED_JOB_CAPABILITY_ONLY; quality and loss independent"),
            "edit":operation("UNVERIFIED","SOURCE_NATIVE_EDIT; derived document editing is separate"),
            "export":operation("AVAILABLE","ORIGINAL_BYTES_ONLY; use source original endpoint"),
            "roundtrip":operation("UNVERIFIED","NATIVE_FORMAT_EDIT_EXPORT_REIMPORT")},
        "outputs":outputs,"outputs_capped":capped,
        "loss":{"status":if !terminal_success || losses.is_null(){"unknown"}else if losses==json!(0){"none_reported"}else{"reported"},
            "reported_count":losses,"receipt_ref":if outputs.iter().any(|v|v["kind"]=="loss_report"){Some(format!("/api/v1/jobs/{job}/outputs/loss_report"))}else{None}},
        "execution_ref":format!("/api/v1/jobs/{job}/execution-status"),
        "original_ref":format!("/api/v1/sources/{source}/original"),
        "evidence_scope":"PERSISTED_CORE_EXECUTION; no corpus-wide, installed, visual or Owner qualification"
    })))
}
