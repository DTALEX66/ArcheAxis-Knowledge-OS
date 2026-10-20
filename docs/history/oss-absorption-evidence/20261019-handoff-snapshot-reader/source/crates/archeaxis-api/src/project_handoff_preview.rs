//! 本地human预览及显式固定正文读取；无写入、投递或外部连接。
use crate::{AppState, project_handoff::proposal_fingerprint, project_observer::now_ms};
use archeaxis_contracts::{
    project_handoff::{AuthorizationScope, Handoff, Payload, Unverified},
    project_handoff_preview::{Preview, ReferenceState, SCHEMA},
    project_observer::NavigationState,
};
use archeaxis_domain::ui_state::existing_workspace_id;
use archeaxis_store_sqlite::authorization_fence;
use axum::{
    Json,
    body::Bytes,
    extract::State,
    http::{HeaderMap, StatusCode, Uri},
    response::{IntoResponse, Response},
};
use rusqlite::OptionalExtension;
use sha2::{Digest, Sha256};

fn error(status: StatusCode, code: &'static str) -> Response {
    (
        status,
        Json(
            serde_json::json!({"schema":"archeaxis.project-handoff-preview-error/v1","code":code}),
        ),
    )
        .into_response()
}

/// 同一读取快照内重核恢复身份和原字节，不复用预览时点作为正文授权。
pub(crate) async fn snapshot(
    State(store): State<AppState>,
    uri: Uri,
    headers: HeaderMap,
    bytes: Bytes,
) -> Response {
    use archeaxis_contracts::project_handoff_preview::{SNAPSHOT_SCHEMA, Snapshot, SnapshotScope};
    if crate::request_actor(&headers) != Ok("human") {
        return error(StatusCode::FORBIDDEN, "HANDOFF_SNAPSHOT_HUMAN_REQUIRED");
    }
    if uri.query().is_some() || bytes.len() > 65_536 {
        return error(StatusCode::BAD_REQUEST, "HANDOFF_SNAPSHOT_INVALID_INPUT");
    }
    let proposal: Handoff = match serde_json::from_slice(&bytes) {
        Ok(value) => value,
        Err(_) => return error(StatusCode::BAD_REQUEST, "HANDOFF_SNAPSHOT_INVALID_INPUT"),
    };
    if !proposal.valid(now_ms()) || !matches!(proposal.payload, Payload::Context { .. }) {
        return error(StatusCode::BAD_REQUEST, "HANDOFF_SNAPSHOT_INVALID_INPUT");
    }
    let result = store.submit(move |conn| -> Result<Snapshot, (&'static str, StatusCode)> {
        let unavailable = || ("HANDOFF_SNAPSHOT_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE);
        let tx = conn.transaction().map_err(|_| unavailable())?;
        let workspace = existing_workspace_id(&tx).map_err(|_| unavailable())?.ok_or_else(unavailable)?;
        let epoch = authorization_fence::authorization_epoch(&tx).map_err(|_| unavailable())?.unwrap_or_else(|| "initial".into());
        if proposal.producer.workspace_id != workspace || proposal.producer.restore_epoch != epoch {
            return Err(("HANDOFF_SNAPSHOT_IDENTITY_MISMATCH", StatusCode::CONFLICT));
        }
        let Payload::Context { source, .. } = &proposal.payload else { unreachable!() };
        let reference = &source.reference;
        let version = i64::try_from(reference.version).map_err(|_| ("HANDOFF_SNAPSHOT_INVALID_INPUT", StatusCode::BAD_REQUEST))?;
        // 先在同事务检查长度，再读取原始UTF-8。拒绝超限，绝不截断或换最新版。
        let length: Option<i64> = tx.query_row(
            "SELECT length(CAST(v.editor_json AS BLOB)) FROM documents d JOIN document_versions v ON v.document_id=d.document_id WHERE d.document_id=?1 AND v.version=?2",
            rusqlite::params![reference.document_id,version], |row| row.get(0)).optional().map_err(|_| unavailable())?;
        let Some(length) = length else { return Err(("HANDOFF_SNAPSHOT_NOT_FOUND", StatusCode::NOT_FOUND)); };
        if !(0..=8 * 1024 * 1024).contains(&length) {
            return Err(("HANDOFF_SNAPSHOT_TOO_LARGE", StatusCode::PAYLOAD_TOO_LARGE));
        }
        let (current, raw, stored_hash): (i64, String, String) = tx.query_row(
            "SELECT d.current_version,v.editor_json,v.content_sha256 FROM documents d JOIN document_versions v ON v.document_id=d.document_id WHERE d.document_id=?1 AND v.version=?2",
            rusqlite::params![reference.document_id,version], |row| Ok((row.get(0)?,row.get(1)?,row.get(2)?))).map_err(|_| unavailable())?;
        if current <= 0 || format!("{:x}", Sha256::digest(raw.as_bytes())) != stored_hash {
            return Err(("HANDOFF_SNAPSHOT_CONTENT_INVALID", StatusCode::CONFLICT));
        }
        if stored_hash != reference.content_sha256 {
            return Err(("HANDOFF_SNAPSHOT_REFERENCE_MISMATCH", StatusCode::CONFLICT));
        }
        // 不返回未被上述原字节hash覆盖的current title、projection或blocks。
        let editor_json: serde_json::Value = serde_json::from_str(&raw).map_err(|_| unavailable())?;
        if !editor_json.is_object() || editor_json["type"] != "doc" {
            return Err(("HANDOFF_SNAPSHOT_CONTENT_INVALID", StatusCode::CONFLICT));
        }
        let checked_at_ms = now_ms();
        let value = Snapshot {
            schema: SNAPSHOT_SCHEMA.into(), checked_at_ms, expires_at_ms: proposal.expires_at_ms,
            proposal_sha256: proposal_fingerprint(&proposal).map_err(|_| unavailable())?,
            producer: proposal.producer.clone(), reference: reference.clone(),
            reference_state: if current == version { ReferenceState::Current } else { ReferenceState::Stale },
            source_authentication: Unverified::Unverified, selection_qualification: Unverified::Unverified,
            scope: SnapshotScope::LocalHumanReadOnly, editor_json,
            grants_execution: false, grants_knowledge_acceptance: false,
        };
        if !value.valid(checked_at_ms) {
            return Err(("HANDOFF_SNAPSHOT_EXPIRED", StatusCode::CONFLICT));
        }
        tx.commit().map_err(|_| unavailable())?;
        Ok(value)
    }).await;
    match result {
        Ok(Ok(value)) if !value.valid(now_ms()) => {
            error(StatusCode::CONFLICT, "HANDOFF_SNAPSHOT_EXPIRED")
        }
        Ok(Ok(value)) => match serde_json::to_vec(&value) {
            Ok(bytes) if bytes.len() <= 24 * 1024 * 1024 && !value.valid(now_ms()) => {
                error(StatusCode::CONFLICT, "HANDOFF_SNAPSHOT_EXPIRED")
            }
            Ok(bytes) if bytes.len() <= 24 * 1024 * 1024 => (
                [(axum::http::header::CONTENT_TYPE, "application/json")],
                bytes,
            )
                .into_response(),
            Ok(_) => error(StatusCode::PAYLOAD_TOO_LARGE, "HANDOFF_SNAPSHOT_TOO_LARGE"),
            Err(_) => error(
                StatusCode::SERVICE_UNAVAILABLE,
                "HANDOFF_SNAPSHOT_UNAVAILABLE",
            ),
        },
        Ok(Err((code, status))) => error(status, code),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "HANDOFF_SNAPSHOT_UNAVAILABLE",
        ),
    }
}
pub(crate) async fn preview(
    State(store): State<AppState>,
    uri: Uri,
    headers: HeaderMap,
    bytes: Bytes,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(StatusCode::FORBIDDEN, "HANDOFF_PREVIEW_HUMAN_REQUIRED");
    }
    if uri.query().is_some() || bytes.len() > 65_536 {
        return error(StatusCode::BAD_REQUEST, "HANDOFF_PREVIEW_INVALID_INPUT");
    }
    let proposal: Handoff = match serde_json::from_slice(&bytes) {
        Ok(value) => value,
        Err(_) => return error(StatusCode::BAD_REQUEST, "HANDOFF_PREVIEW_INVALID_INPUT"),
    };
    if !proposal.valid(now_ms()) || !matches!(proposal.payload, Payload::Context { .. }) {
        return error(StatusCode::BAD_REQUEST, "HANDOFF_PREVIEW_INVALID_INPUT");
    }
    let result = store.submit(move |conn| -> Result<Preview, (&'static str, StatusCode)> {
        let unavailable = || ("HANDOFF_PREVIEW_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE);
        let tx = conn.transaction().map_err(|_| unavailable())?;
        // 仅查询已有身份；不调用首次初始化可能写入的workspace_id helper。
        let workspace = existing_workspace_id(&tx).map_err(|_| unavailable())?.ok_or_else(unavailable)?;
        let epoch = authorization_fence::authorization_epoch(&tx).map_err(|_| unavailable())?.unwrap_or_else(|| "initial".into());
        if proposal.producer.workspace_id != workspace || proposal.producer.restore_epoch != epoch {
            return Err(("HANDOFF_PREVIEW_IDENTITY_MISMATCH", StatusCode::CONFLICT));
        }
        let Payload::Context { source, .. } = &proposal.payload else { unreachable!() };
        let current: Option<(i64, String)> = tx.query_row(
            "SELECT d.current_version,v.content_sha256 FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version WHERE d.document_id=?1",
            [&source.reference.document_id], |row| Ok((row.get(0)?,row.get(1)?))).optional().map_err(|_| unavailable())?;
        if current.as_ref().is_some_and(|(version,hash)| *version <= 0 || !archeaxis_contracts::project_observer::hex(hash,64)) {
            return Err(unavailable());
        }
        let reference_state = match current {
            None => ReferenceState::NotFound,
            Some((version, hash)) if version as u64 == source.reference.version && hash == source.reference.content_sha256 => ReferenceState::Current,
            Some(_) => ReferenceState::Stale,
        };
        // 接收的consumer仅原提案声明；没有观察到外部身份或正文选区，不升级其资格。
        let fingerprint = proposal_fingerprint(&proposal).map_err(|_| ("HANDOFF_PREVIEW_INVALID_INPUT", StatusCode::BAD_REQUEST))?;
        tx.commit().map_err(|_| unavailable())?;
        let checked_at_ms = now_ms();
        let value = Preview {schema: SCHEMA.into(), checked_at_ms, expires_at_ms: proposal.expires_at_ms,
            proposal, proposal_sha256: fingerprint, reference_state, source_authentication: Unverified::Unverified,
            authority: AuthorizationScope::ReferenceMetadataOnly, navigation: NavigationState::Unavailable,
            grants_execution: false, grants_knowledge_acceptance: false};
        if !value.valid(checked_at_ms) {
            return Err(("HANDOFF_PREVIEW_EXPIRED", StatusCode::CONFLICT));
        }
        Ok(value)
    }).await;
    match result {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err((code, status))) => error(status, code),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "HANDOFF_PREVIEW_UNAVAILABLE",
        ),
    }
}
