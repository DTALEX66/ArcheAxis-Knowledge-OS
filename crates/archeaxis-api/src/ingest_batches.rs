//! Finite batch API, all persistence through the existing Store writer.
use crate::AppState;
use archeaxis_domain::ingest_batches as domain;
use axum::{
    Json,
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
};
use base64::Engine;
use rusqlite::params;
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};

fn response(value: Result<serde_json::Value, domain::Error>) -> Response {
    match value {
        Ok(value) => Json(value).into_response(),
        Err(domain::Error::Invalid(message)) => (StatusCode::BAD_REQUEST, message).into_response(),
        Err(domain::Error::Conflict) => {
            (StatusCode::CONFLICT, "batch identity or manifest conflict").into_response()
        }
        Err(domain::Error::NotFound) => {
            (StatusCode::NOT_FOUND, "batch or member not found").into_response()
        }
        Err(domain::Error::Sql(_)) => {
            (StatusCode::INTERNAL_SERVER_ERROR, "batch storage failure").into_response()
        }
    }
}
pub(crate) async fn register(
    State(state): State<AppState>,
    Json(body): Json<domain::Register>,
) -> Response {
    crate::with_store(state, move |conn| response(domain::register(conn, body))).await
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Page {
    after_ordinal: Option<i64>,
    #[serde(default = "page_limit")]
    limit: i64,
}
fn page_limit() -> i64 {
    200
}
pub(crate) async fn read(
    State(state): State<AppState>,
    Path(batch): Path<String>,
    Query(page): Query<Page>,
) -> Response {
    crate::with_store(state, move |conn| {
        response(domain::read(conn, &batch, page.after_ordinal, page.limit))
    })
    .await
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct List {
    cursor: Option<String>,
    #[serde(default = "page_limit")]
    limit: i64,
}
pub(crate) async fn list(State(state): State<AppState>, Query(page): Query<List>) -> Response {
    crate::with_store(state, move |conn| {
        response(domain::list(conn, page.cursor.as_deref(), page.limit))
    })
    .await
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Import {
    workspace_id: String,
    restore_epoch: String,
    ordinal: i64,
    expected_sha256: String,
    content_base64: String,
}
pub(crate) async fn import(
    State(state): State<AppState>,
    Path(batch): Path<String>,
    Json(body): Json<Import>,
) -> Response {
    crate::with_store(state,move|conn|{
        let result=(||{
            let tx=conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
            domain::guard(&tx,&body.workspace_id,&body.restore_epoch)?;
            let member=domain::executable_member(&tx,&batch,body.ordinal)?;
            let bytes=base64::engine::general_purpose::STANDARD.decode(&body.content_base64)
                .map_err(|_|domain::Error::Invalid("invalid base64"))?;
            let digest=format!("{:x}",Sha256::digest(&bytes));
            if bytes.len() as i64 != member.byte_length || digest!=body.expected_sha256 {
                return Err(domain::Error::Invalid("member bytes do not match declared length and digest"));
            }
            if member.revision.as_ref().is_some_and(|old|old!=&digest){return Err(domain::Error::Conflict);}
            // Encode UTF-8 bytes as encodeURIComponent does, preserving existing origin identity.
            let encoded=member.path.bytes().map(|b|{
                if b.is_ascii_alphanumeric() || b"-_.!~*'()".contains(&b) {(b as char).to_string()}
                else {format!("%{b:02X}")}
            }).collect::<String>();
            let origin=format!("{batch}:{encoded}");
            let outcome=archeaxis_domain::source::import_source_tx(&tx,&bytes,&member.path,
                Some(archeaxis_domain::source::OriginInfo{kind:"path",origin_ref:&origin,
                    original_name:Some(&member.path),received_at:None}))?;
            use archeaxis_domain::source::ImportOutcome;
            let (source_id,sha256,duplicate)=match outcome{
                ImportOutcome::Imported{source_id,sha256}=>(source_id,sha256,false),
                ImportOutcome::Duplicate{source_id,sha256}=>(source_id,sha256,true),
            };
            if member.source_id.as_ref().is_some_and(|old|old!=&source_id){return Err(domain::Error::Conflict);}
            tx.execute("UPDATE ingest_batch_members SET source_id=?1,source_revision=?2 WHERE batch_id=?3 AND ordinal=?4",
                params![source_id,sha256,batch,body.ordinal])?;
            tx.commit()?;
            Ok(json!({"schema":"archeaxis.ingest-member-import/v1","batch_id":batch,"ordinal":body.ordinal,
                "source_id":source_id,"sha256":sha256,"duplicate":duplicate}))
        })();
        match result{Ok(value)=>(StatusCode::ACCEPTED,Json(value)).into_response(),Err(error)=>response(Err(error))}
    }).await
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Enqueue {
    workspace_id: String,
    restore_epoch: String,
    ordinal: i64,
    source_id: String,
    source_revision: String,
    kind: String,
}
pub(crate) async fn enqueue(
    State(state): State<AppState>,
    Path(batch): Path<String>,
    Json(body): Json<Enqueue>,
) -> Response {
    crate::with_store(state,move|conn|{
        let result=(||{
            let tx=conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
            domain::guard(&tx,&body.workspace_id,&body.restore_epoch)?;
            let member=domain::executable_member(&tx,&batch,body.ordinal)?;
            if member.source_id.as_deref()!=Some(body.source_id.as_str())
                || member.revision.as_deref()!=Some(body.source_revision.as_str()){return Err(domain::Error::Conflict);}
            archeaxis_application::attempts::resolve_media_type(&body.kind,&member.path)
                .map_err(|_|domain::Error::Invalid("unsupported conversion for member"))?;
            let job_id=format!("folder-{}-{}",body.kind,body.source_revision);
            if member.job_id.as_ref().is_some_and(|old|old!=&job_id){return Err(domain::Error::Conflict);}
            archeaxis_application::jobs::enqueue_tx(&tx,&job_id,&body.kind,&body.source_id)
                .map_err(|error|match error{
                    archeaxis_application::jobs::JobError::Sql(error)=>domain::Error::Sql(error),
                    _=>domain::Error::Conflict,
                })?;
            tx.execute("UPDATE ingest_batch_members SET job_id=?1 WHERE batch_id=?2 AND ordinal=?3",
                params![job_id,batch,body.ordinal])?;
            let state:String=tx.query_row("SELECT state FROM jobs WHERE job_id=?1",[&job_id],|r|r.get(0))?;
            tx.commit()?;
            Ok(json!({"schema":"archeaxis.ingest-member-job/v1","batch_id":batch,"ordinal":body.ordinal,
                "job_id":job_id,"state":state}))
        })();
        match result{Ok(value)=>(StatusCode::ACCEPTED,Json(value)).into_response(),Err(error)=>response(Err(error))}
    }).await
}
