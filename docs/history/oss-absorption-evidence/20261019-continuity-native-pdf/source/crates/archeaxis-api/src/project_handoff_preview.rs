//! 原逻辑project.handoff.preview的本地human入口；无正文/写入/投递/外部连接。
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

fn error(status: StatusCode, code: &'static str) -> Response {
    (
        status,
        Json(
            serde_json::json!({"schema":"archeaxis.project-handoff-preview-error/v1","code":code}),
        ),
    )
        .into_response()
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
