//! 专用 Observer admission 的有限只读投影，不经过 human/machine 路由。
pub mod client;
use archeaxis_contracts::project_observer::{
    self as contract, ConsumerIdentity, ObjectReference, ObjectState, Payload, ProducerIdentity,
    ReadResponse,
};
use archeaxis_domain::ui_state::existing_workspace_id;
use archeaxis_store_sqlite::{authorization_fence, writer::Store};
use axum::{
    Json,
    extract::Request,
    http::{HeaderMap, Method, StatusCode},
    response::{IntoResponse, Response},
};
use rusqlite::OptionalExtension;
use serde::Deserialize;
use std::{
    collections::HashSet,
    time::{SystemTime, UNIX_EPOCH},
};

pub fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

/// 仅由受信父进程 stdin 提供；不实现 Debug/Serialize，避免凭据进入回执。
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ObserverGrant {
    pub(crate) token: String,
    consumer: ConsumerIdentity,
    producer: ProducerIdentity,
    expires_at_ms: u64,
    document_ids: Vec<String>,
}
impl ObserverGrant {
    pub(crate) fn valid(&self, now: u64) -> bool {
        contract::hex(&self.token, 64)
            && self.producer.valid()
            && contract::hex(&self.consumer.instance_id, 32)
            && self.expires_at_ms > now
            && self.expires_at_ms - now <= 86_400_000
            && !self.document_ids.is_empty()
            && self.document_ids.len() <= contract::MAX_OBJECTS
            && self.document_ids.iter().all(|s| contract::object_id(s))
            && {
                let mut seen = HashSet::new();
                self.document_ids.iter().all(|s| seen.insert(s))
            }
    }
}
fn error(status: StatusCode, code: &'static str) -> Response {
    (
        status,
        Json(serde_json::json!({"schema":"archeaxis.project-observer-error/v1","code":code})),
    )
        .into_response()
}
fn header<'a>(headers: &'a HeaderMap, key: &str) -> Option<&'a str> {
    let mut values = headers.get_all(key).iter();
    let value = values.next()?.to_str().ok()?;
    if values.next().is_some() {
        None
    } else {
        Some(value)
    }
}
enum Read {
    Handshake,
    Objects,
    Status(ObjectReference),
}
fn selected_read(request: &Request) -> Result<Read, Response> {
    if request.method() != Method::GET {
        return Err(error(StatusCode::FORBIDDEN, "OBSERVER_READ_ONLY"));
    }
    let path = request.uri().path();
    if path != "/api/v1/project-observer/handshake"
        && path != "/api/v1/project-observer/objects"
        && !path.starts_with("/api/v1/project-observer/objects/")
    {
        return Err(error(StatusCode::FORBIDDEN, "OBSERVER_PORT_NOT_ADMITTED"));
    }
    if request.headers().contains_key("transfer-encoding")
        || (request.headers().contains_key("content-length")
            && header(request.headers(), "content-length") != Some("0"))
    {
        return Err(error(
            StatusCode::BAD_REQUEST,
            "OBSERVER_EMPTY_BODY_REQUIRED",
        ));
    }
    if path == "/api/v1/project-observer/handshake" && request.uri().query().is_none() {
        return Ok(Read::Handshake);
    }
    if path == "/api/v1/project-observer/objects" && request.uri().query().is_none() {
        return Ok(Read::Objects);
    }
    if let Some(id) = path.strip_prefix("/api/v1/project-observer/objects/") {
        if !contract::object_id(id) {
            return Err(error(StatusCode::BAD_REQUEST, "OBSERVER_INVALID_REFERENCE"));
        }
        let mut version = None;
        let mut digest = None;
        for field in request.uri().query().unwrap_or("").split('&') {
            let Some((key, value)) = field.split_once('=') else {
                return Err(error(StatusCode::BAD_REQUEST, "OBSERVER_INVALID_REFERENCE"));
            };
            match key {
                "version"
                    if version.is_none()
                        && !value.is_empty()
                        && value.bytes().all(|b| b.is_ascii_digit()) =>
                {
                    version = value.parse::<u64>().ok();
                }
                "content_sha256" if digest.is_none() => {
                    digest = Some(value.to_owned());
                }
                _ => return Err(error(StatusCode::BAD_REQUEST, "OBSERVER_INVALID_REFERENCE")),
            }
        }
        if let (Some(version), Some(content_sha256)) = (version, digest) {
            let reference = ObjectReference {
                document_id: id.into(),
                version,
                content_sha256,
            };
            if reference.valid() {
                return Ok(Read::Status(reference));
            }
        }
        return Err(error(StatusCode::BAD_REQUEST, "OBSERVER_INVALID_REFERENCE"));
    }
    Err(error(StatusCode::FORBIDDEN, "OBSERVER_PORT_NOT_ADMITTED"))
}
pub(crate) async fn serve(store: Store, grant: ObserverGrant, request: Request) -> Response {
    let now = now_ms();
    if !grant.valid(now) {
        return error(StatusCode::FORBIDDEN, "OBSERVER_GRANT_EXPIRED");
    }
    let headers = request.headers();
    if headers.contains_key("origin") || headers.contains_key("x-archeaxis-actor") {
        return error(StatusCode::FORBIDDEN, "OBSERVER_SELF_REPORTED_ROLE");
    }
    if header(headers, "x-archeaxis-observer-protocol") != Some(contract::PROTOCOL) {
        return error(StatusCode::CONFLICT, "OBSERVER_PROTOCOL_UNSUPPORTED");
    }
    if header(headers, "x-archeaxis-observer-namespace") != Some(grant.consumer.namespace.as_str())
        || header(headers, "x-archeaxis-observer-instance")
            != Some(grant.consumer.instance_id.as_str())
    {
        return error(StatusCode::FORBIDDEN, "OBSERVER_CONSUMER_MISMATCH");
    }
    let read = match selected_read(&request) {
        Ok(read) => read,
        Err(response) => return response,
    };
    if let Read::Status(reference) = &read {
        if !grant.document_ids.contains(&reference.document_id) {
            return error(StatusCode::FORBIDDEN, "OBSERVER_OBJECT_NOT_ADMITTED");
        }
    }
    let result = store.submit(move |conn| -> Result<ReadResponse, (&'static str, StatusCode)> {
        // DEFERRED read transaction: no schema/identity initialization and no write helper.
        let tx = conn.transaction().map_err(|_| ("OBSERVER_STORE_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE))?;
        let workspace_id = existing_workspace_id(&tx).map_err(|_| ("OBSERVER_IDENTITY_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE))?
            .ok_or(("OBSERVER_IDENTITY_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE))?;
        let epoch = authorization_fence::authorization_epoch(&tx).map_err(|_| ("OBSERVER_IDENTITY_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE))?.unwrap_or_else(|| "initial".into());
        if workspace_id != grant.producer.workspace_id || epoch != grant.producer.restore_epoch {
            return Err(("OBSERVER_WORKSPACE_CHANGED", StatusCode::CONFLICT));
        }
        let mut references = Vec::new();
        match &read {
            Read::Handshake => {},
            Read::Objects | Read::Status(_) => {
                let ids = match &read { Read::Status(reference) => vec![reference.document_id.clone()], _ => grant.document_ids.clone() };
                for id in ids {
                    let value: Option<(i64, String)> = tx.query_row(
                        "SELECT d.current_version,v.content_sha256 FROM documents d JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version WHERE d.document_id=?1",
                        [&id], |row| Ok((row.get(0)?, row.get(1)?))).optional()
                        .map_err(|_| ("OBSERVER_STORE_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE))?;
                    if let Some((version, content_sha256)) = value {
                        let reference = ObjectReference { document_id: id, version: version as u64, content_sha256 };
                        if !reference.valid() { return Err(("OBSERVER_INVALID_STORED_REFERENCE", StatusCode::SERVICE_UNAVAILABLE)); }
                        references.push(reference);
                    }
                }
            }
        }
        let payload = match read {
            Read::Handshake => Payload::Handshake { operations: ["handshake", "objects.read", "object.status"].into_iter().map(str::to_owned).collect(), authority: "REFERENCE_ONLY".into(), grants_execution: false, grants_knowledge_acceptance: false },
            Read::Objects => Payload::Objects { objects: references, navigation: contract::NavigationState::Unavailable },
            Read::Status(reference) => {
                let current = references.first().ok_or(("OBSERVER_OBJECT_NOT_FOUND", StatusCode::NOT_FOUND))?;
                let state = if current == &reference { ObjectState::Current } else { ObjectState::Stale };
                Payload::ObjectStatus { reference, state, navigation: contract::NavigationState::Unavailable }
            }
        };
        tx.commit().map_err(|_| ("OBSERVER_STORE_UNAVAILABLE", StatusCode::SERVICE_UNAVAILABLE))?;
        let checked_at_ms = now_ms();
        if checked_at_ms >= grant.expires_at_ms { return Err(("OBSERVER_GRANT_EXPIRED", StatusCode::FORBIDDEN)); }
        Ok(ReadResponse { schema: contract::SCHEMA.into(), protocol: contract::PROTOCOL.into(), producer: grant.producer,
            consumer: grant.consumer, checked_at_ms, expires_at_ms: grant.expires_at_ms.min(checked_at_ms.saturating_add(contract::FRESHNESS_MS)), payload })
    }).await;
    match result {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err((code, status))) => error(status, code),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OBSERVER_STORE_UNAVAILABLE",
        ),
    }
}
