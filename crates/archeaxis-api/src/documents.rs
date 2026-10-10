//! Bounded native editing commands over the existing single-writer Store.
use crate::AppState;
use archeaxis_domain::document;
use axum::{
    Json,
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use base64::Engine;
use rusqlite::OptionalExtension;
use serde::Deserialize;
use serde_json::{Value, json};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ExportQuery {
    format: String,
}

pub(crate) async fn export(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Query(query): Query<ExportQuery>,
) -> Response {
    if !matches!(query.format.as_str(), "markdown" | "obsidian") {
        return failure(document::Error::Invalid(
            "format must be markdown or obsidian",
        ));
    }
    crate::with_store(state, move |conn| {
        let snapshot = match document::read(conn,&id,None) {Ok(value)=>value,Err(error)=>return failure(error)};
        let anchors = (|| -> rusqlite::Result<Vec<Value>> {
            let mut stmt=conn.prepare("SELECT anchor_id,source_revision,position FROM anchors WHERE source_id=?1 ORDER BY anchor_id")?;
            stmt.query_map([snapshot["source_id"].as_str()],|r|Ok(json!({"anchor_id":r.get::<_,String>(0)?,"source_revision":r.get::<_,String>(1)?,"position":r.get::<_,String>(2)?})))?.collect()
        })();
        let anchors=match anchors {Ok(value)=>value,Err(error)=>return failure(error.into())};
        let projection=snapshot["text_projection"].as_str().unwrap();
        use sha2::{Digest,Sha256};
        let projection_sha256=format!("{:x}",Sha256::digest(projection.as_bytes()));
        let mut markdown=if query.format=="obsidian" {format!("---\narcheaxis_document: {}\narcheaxis_version: {}\narcheaxis_source_revision: {}\n---\n\n",serde_json::to_string(&id).unwrap(),snapshot["version"],snapshot["source_revision"])} else {String::new()};
        markdown.push_str(projection);
        let source_record=json!({"source_id":snapshot["source_id"],"source_revision":snapshot["source_revision"]});
        markdown.push_str(&format!("\n\n## Source identity\n\n    {}\n\n## Evidence records\n",serde_json::to_string(&source_record).unwrap()));
        for anchor in &anchors { markdown.push_str(&format!("\n    {}\n",serde_json::to_string(anchor).unwrap())); }
        let mut loss=json!([{"code":"markdown_projection","message":"Markdown contains a text projection; structured and unknown nodes are preserved in manifest.json"},{"code":"external_navigation_unavailable","message":"Source identity, revision and anchor positions are preserved as metadata; no external navigation handler is registered, so these records do not provide clickable navigation to original sources"}]);
        let expression = snapshot["editor_json"]["attrs"].get("archeaxis_expression");
        if expression.is_some() {
            loss.as_array_mut().unwrap().push(json!({"code":"expression_media_reference_only","message":"The expression layout and immutable media references are preserved in the snapshot; referenced CAS media bytes are not packaged. Use a verified workspace archive for full recovery."}));
            loss.as_array_mut().unwrap().push(json!({"code":"expression_engine_not_executed","message":"Animation, simulation and spatial metadata are inert declarations; no engine execution is included."}));
        }
        let mut manifest=json!({"schema":"archeaxis-document-export-1","document":snapshot,"anchors":anchors,"projection_sha256":projection_sha256,"loss":loss});
        if let Some(collection)=archeaxis_domain::collection::export_metadata(&snapshot["editor_json"]) {
            manifest["collection_export"]=collection;
        }
        if let Some(expression) = expression {
            let references: Vec<Value> = expression["nodes"].as_array().map(|nodes| nodes.iter().filter_map(|node| node.get("media").filter(|media| !media.is_null()).cloned()).collect()).unwrap_or_default();
            manifest["expression_export"] = json!({"document_id":id,"version":manifest["document"]["version"],"content_sha256":manifest["document"]["content_sha256"],"media_packaging":"reference_only","media_references":references,"engine_execution":"NOT_EXECUTED"});
        }
        Json(json!({"document_id":id,"version":manifest["document"]["version"],"format":query.format,"source_revision":manifest["document"]["source_revision"],"projection_sha256":projection_sha256,"files":[{"path":"document.md","media_type":"text/markdown","content":markdown},{"path":"manifest.json","media_type":"application/json","content":serde_json::to_string_pretty(&manifest).unwrap()}]})).into_response()
    }).await
}

pub(crate) fn failure(error: document::Error) -> Response {
    match error {
        document::Error::Invalid(message) => (StatusCode::BAD_REQUEST,Json(json!({"code":"AAK-DOC-001","message":message}))).into_response(),
        document::Error::NotFound => (StatusCode::NOT_FOUND,Json(json!({"code":"AAK-DOC-002","message":"document or version not found"}))).into_response(),
        document::Error::Conflict(version) => (StatusCode::CONFLICT,Json(json!({"code":"AAK-DOC-003","current_version":version,"message":"saved document version changed"}))).into_response(),
        document::Error::Sql(error) => (StatusCode::INTERNAL_SERVER_ERROR,error.to_string()).into_response(),
    }
}

fn human(headers: &HeaderMap) -> bool {
    crate::request_actor(headers) == Ok("human")
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Create {
    create_request_id: Option<String>,
    source_id: Option<String>,
    source_revision: Option<String>,
    title: String,
    editor_json: Value,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Save {
    expected_version: i64,
    editor_json: Value,
    revision_basis: Option<Value>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Restore {
    expected_version: i64,
    restore_version: i64,
}

pub(crate) async fn create(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<Create>,
) -> Response {
    if !human(&headers) {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| {
        match document::create_optional_with_request(
            conn,
            body.source_id.as_deref(),
            body.source_revision.as_deref(),
            &body.title,
            body.editor_json,
            body.create_request_id.as_deref(),
        ) {
            Ok(value) => (StatusCode::CREATED, Json(value)).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
pub(crate) async fn save(
    State(state): State<AppState>,
    Path(id): Path<String>,
    headers: HeaderMap,
    Json(body): Json<Save>,
) -> Response {
    if !human(&headers) {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| {
        match document::save_with_basis(
            conn,
            &id,
            body.expected_version,
            body.editor_json,
            body.revision_basis,
        ) {
            Ok(value) => Json(value).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
pub(crate) async fn restore(
    State(state): State<AppState>,
    Path(id): Path<String>,
    headers: HeaderMap,
    Json(body): Json<Restore>,
) -> Response {
    if !human(&headers) {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| {
        match document::restore(conn, &id, body.expected_version, body.restore_version) {
            Ok(value) => Json(value).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
pub(crate) async fn read(State(state): State<AppState>, Path(id): Path<String>) -> Response {
    crate::with_store(state, move |conn| match document::read(conn, &id, None) {
        Ok(value) => Json(value).into_response(),
        Err(error) => failure(error),
    })
    .await
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RelationsQuery { version: Option<i64>, cursor: Option<String> }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CollectionQuery { view_id: String, version: Option<i64>, offset: Option<usize>, limit: Option<usize> }
pub(crate) async fn collection(State(state): State<AppState>, Path(id): Path<String>, Query(query):Query<CollectionQuery>) -> Response {
    if query.version.is_some_and(|v|v<1) {return failure(document::Error::Invalid("collection version must be positive"));}
    crate::with_store(state,move|conn|match archeaxis_domain::collection::query(conn,&id,query.version,&query.view_id,query.offset.unwrap_or(0),query.limit.unwrap_or(20)) {
        Ok(value)=>Json(value).into_response(),Err(error)=>failure(error),
    }).await
}
pub(crate) async fn relations(State(state): State<AppState>, Path(id): Path<String>, Query(query):Query<RelationsQuery>) -> Response {
    if query.version.is_some_and(|v|v<1) {return failure(document::Error::Invalid("relation center version must be positive"));}
    crate::with_store(state,move|conn|match archeaxis_domain::relation_projection::query(conn,&id,query.version,query.cursor.as_deref()) {
        Ok(value)=>Json(value).into_response(),Err(error)=>failure(error),
    }).await
}
pub(crate) async fn version(
    State(state): State<AppState>,
    Path((id, version)): Path<(String, i64)>,
) -> Response {
    crate::with_store(state, move |conn| {
        match document::read(conn, &id, Some(version)) {
            Ok(value) => Json(value).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ListQuery { cursor: Option<String> }

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CursorWire { v: u8, watermark_rowid: i64, snapshot_count: i64, after_created_at: String, after_document_id: String }

fn decode_cursor(encoded: &str) -> Result<document::ListCursor, document::Error> {
    let invalid = || document::Error::Invalid("invalid document cursor");
    if encoded.is_empty() || encoded.len()>1024 || !encoded.bytes().all(|b| b.is_ascii_alphanumeric() || b==b'-' || b==b'_') { return Err(invalid()); }
    let bytes = base64::engine::general_purpose::URL_SAFE_NO_PAD.decode(encoded).map_err(|_|invalid())?;
    if bytes.len()>768 { return Err(invalid()); }
    let value: CursorWire = serde_json::from_slice(&bytes).map_err(|_|invalid())?;
    if value.v!=1 || value.watermark_rowid<1 || value.snapshot_count<1
        || value.after_created_at.is_empty() || value.after_created_at.len()>64 || value.after_created_at.chars().any(char::is_control)
        || value.after_document_id.is_empty() || value.after_document_id.len()>128
        || !value.after_document_id.bytes().all(|b|b.is_ascii_alphanumeric() || b==b'-' || b==b'_') { return Err(invalid()); }
    Ok(document::ListCursor {v:value.v,watermark_rowid:value.watermark_rowid,snapshot_count:value.snapshot_count,after_created_at:value.after_created_at,after_document_id:value.after_document_id})
}

pub(crate) async fn list(State(state): State<AppState>, Query(query): Query<ListQuery>) -> Response {
    let cursor = match query.cursor.as_deref().map(decode_cursor).transpose() { Ok(value)=>value, Err(error)=>return failure(error) };
    crate::with_store(state, move |conn| match document::list_page(conn,cursor) {
        Ok((documents,next,count)) => {
            let next_cursor = next.map(|value|base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(serde_json::to_vec(&json!({"v":value.v,"watermark_rowid":value.watermark_rowid,"snapshot_count":value.snapshot_count,"after_created_at":value.after_created_at,"after_document_id":value.after_document_id})).unwrap()));
            Json(json!({"documents":documents,"next_cursor":next_cursor,"snapshot_count":count})).into_response()
        },
        Err(error) => failure(error),
    })
    .await
}

pub(crate) async fn sources(State(state): State<AppState>) -> Response {
    crate::with_store(state,move |conn| {
        let rows = (|| -> rusqlite::Result<Vec<Value>> {
            let mut stmt = conn.prepare("SELECT source_id,sha256,original_name,imported_at FROM sources ORDER BY imported_at DESC,source_id LIMIT 500")?;
            stmt.query_map([],|r|Ok(json!({"source_id":r.get::<_,String>(0)?,"source_revision":r.get::<_,String>(1)?,
                "sha256":r.get::<_,String>(1)?,"original_name":r.get::<_,String>(2)?,"imported_at":r.get::<_,String>(3)?})))?.collect()
        })();
        match rows { Ok(rows)=>Json(json!({"sources":rows})).into_response(),Err(error)=>failure(error.into()) }
    }).await
}

pub(crate) async fn anchors(State(state): State<AppState>, Path(id): Path<String>) -> Response {
    crate::with_store(state,move |conn| {
        let result = (|| -> rusqlite::Result<Vec<Value>> {
            let mut stmt = conn.prepare("SELECT a.anchor_id,a.source_revision,a.position,s.sha256 FROM anchors a JOIN sources s ON s.source_id=a.source_id WHERE a.source_id=?1 ORDER BY a.created_at,a.anchor_id LIMIT 500")?;
            stmt.query_map([&id],|r| {
                let revision:String = r.get(1)?;
                let digest:String = r.get(3)?;
                let position:String = r.get(2)?;
                let locator:Value = serde_json::from_str(&position).unwrap_or(Value::Null);
                Ok(json!({"anchor_id":r.get::<_,String>(0)?,"source_id":id,"source_revision":revision,
                    "position":position,"checksum":locator.get("checksum"),"location_status":if revision!=digest {"revision_mismatch"} else if locator["location_status"]=="located" {"located"} else {"unverified"}}))
            })?.collect()
        })();
        match result { Ok(rows)=>Json(json!({"anchors":rows})).into_response(),Err(error)=>failure(error.into()) }
    }).await
}

pub(crate) async fn original(State(state): State<AppState>, Path(id): Path<String>) -> Response {
    crate::with_store(state, move |conn| {
        let result = (|| -> Result<(String, String, Vec<u8>), document::Error> {
            let row: Option<(String, String)> = conn
                .query_row(
                    "SELECT sha256,original_name FROM sources WHERE source_id=?1",
                    [&id],
                    |r| Ok((r.get(0)?, r.get(1)?)),
                )
                .optional()?;
            let (digest, name) = row.ok_or(document::Error::NotFound)?;
            let bytes = archeaxis_store_sqlite::raw_objects::read(conn, &digest)?;
            Ok((digest, name, bytes))
        })();
        match result {
            Ok((digest, name, bytes)) => {
                let mime = archeaxis_application::attempts::media_type_for_name(&name)
                    .unwrap_or("application/octet-stream");
                Json(
                    json!({"source_id":id,"name":name,"media_type":mime,"sha256":digest,
                    "content_base64":base64::engine::general_purpose::STANDARD.encode(bytes)}),
                )
                .into_response()
            }
            Err(error) => failure(error),
        }
    })
    .await
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CheckQuery {
    version: Option<i64>,
    offset: Option<i64>,
}
pub(crate) async fn checks(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Query(query): Query<CheckQuery>,
) -> Response {
    crate::with_store(state, move |conn| {
        match document::checks_page(conn, &id, query.version, query.offset.unwrap_or(0)) {
            Ok(value) => Json(value).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}
pub(crate) async fn record_check(
    State(state): State<AppState>,
    Path(id): Path<String>,
    headers: HeaderMap,
    Json(body): Json<CheckBody>,
) -> Response {
    let actor = match crate::request_actor(&headers) {
        Ok(actor) => actor,
        Err(status) => return status.into_response(),
    };
    if body.provider_mode == "manual" && actor != "human" {
        return StatusCode::FORBIDDEN.into_response();
    }
    crate::with_store(state, move |conn| {
        match document::record_check(
            conn,
            &id,
            actor,
            document::CheckInput {
                version: body.version,
                dimension: body.dimension,
                provider_mode: body.provider_mode,
                status: body.status,
                source_id: body.source_id,
                source_revision: body.source_revision,
                position: body.position,
                recognition_job_id: body.recognition_job_id,
                recognition_result_sha256: body.recognition_result_sha256,
                basis: body.basis,
                reason: body.reason,
            },
        ) {
            Ok(value) => (StatusCode::CREATED, Json(value)).into_response(),
            Err(error) => failure(error),
        }
    })
    .await
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CheckBody {
    version: i64,
    dimension: String,
    provider_mode: String,
    status: Option<String>,
    source_id: Option<String>,
    source_revision: Option<String>,
    position: Option<Value>,
    recognition_job_id: Option<String>,
    recognition_result_sha256: Option<String>,
    basis: Option<String>,
    reason: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CheckExecuteBody {
    check_id: String,
    expected_content_sha256: String,
    retry_of_task_id: Option<String>,
}
pub(crate) async fn execute_check(
    State(state): State<AppState>,
    Path(id): Path<String>,
    headers: HeaderMap,
    Json(body): Json<CheckExecuteBody>,
) -> Response {
    match crate::request_actor(&headers) {
        Ok("human") => {}
        Ok(_) => return StatusCode::FORBIDDEN.into_response(),
        Err(status) => return status.into_response(),
    }
    crate::with_store(
        state,
        move |conn| match document::execute_check_unconfigured(
            conn,
            &id,
            &body.check_id,
            &body.expected_content_sha256,
            body.retry_of_task_id.as_deref(),
        ) {
            Ok(value) => (StatusCode::CREATED, Json(value)).into_response(),
            Err(error) => failure(error),
        },
    )
    .await
}

pub(crate) async fn execute_runtime_check(
    executor: archeaxis_application::executor::Executor,
    id: String,
    headers: HeaderMap,
    body: CheckExecuteBody,
) -> Response {
    match crate::request_actor(&headers) {
        Ok("human") => {}
        Ok(_) => return StatusCode::FORBIDDEN.into_response(),
        Err(status) => return status.into_response(),
    }
    let Some(config) = executor.document_check_config() else {
        if let Some(reason) = executor.document_check_config_error() {
            let result = executor
                .store()
                .submit_wait(move |conn| {
                    let execution = document::begin_check(
                        conn,
                        &id,
                        &body.check_id,
                        &body.expected_content_sha256,
                        body.retry_of_task_id.as_deref(),
                    )?;
                    let failed = document::failed_check_response(&execution.running, &reason);
                    document::finish_check(
                        conn,
                        &execution.running,
                        &failed,
                        "not_configured",
                        "not_configured",
                    )
                })
                .await;
            return match result {
                Ok(Ok(value)) => (StatusCode::CREATED, Json(value)).into_response(),
                Ok(Err(error)) => failure(error),
                Err(_) => StatusCode::SERVICE_UNAVAILABLE.into_response(),
            };
        }
        return execute_check(
            State(executor.store().clone()),
            Path(id),
            headers,
            Json(body),
        )
        .await;
    };
    let document_id = id.clone();
    let attempt = executor
        .store()
        .submit_wait(move |conn| {
            document::begin_check(
                conn,
                &document_id,
                &body.check_id,
                &body.expected_content_sha256,
                body.retry_of_task_id.as_deref(),
            )
        })
        .await;
    let attempt = match attempt {
        Ok(Ok(value)) => value,
        Ok(Err(error)) => return failure(error),
        Err(_) => return StatusCode::SERVICE_UNAVAILABLE.into_response(),
    };
    let preparation_error = attempt.preparation_error;
    let mut request = json!({"schema":"archeaxis.document-check.request/v1","text":attempt.text,"config":config,"recognition":attempt.recognition,"original":null});
    for key in [
        "attempt_id",
        "request_check_id",
        "document_id",
        "version",
        "content_sha256",
        "dimension",
    ] {
        request[key] = attempt.running[key].clone();
    }
    if let Some((name, digest, bytes)) = attempt.original {
        request["original"] = json!({"media_type":archeaxis_application::attempts::media_type_for_name(&name).unwrap_or("application/octet-stream"),"sha256":digest,"content_base64":base64::engine::general_purpose::STANDARD.encode(bytes)});
    }
    let running = attempt.running;
    let response = if let Some(reason) = preparation_error {
        document::failed_check_response(&running, reason)
    } else {
        match executor.document_check(request).await {
            Ok(value) => value,
            Err(reason) => document::failed_check_response(&running, &reason),
        }
    };
    let result = executor
        .store()
        .submit_wait(move |conn| {
            match document::finish_check(conn, &running, &response, &config.provider, &config.model)
            {
                Ok(value) => Ok(value),
                Err(document::Error::Invalid(_)) => {
                    let failed =
                        document::failed_check_response(&running, "invalid_worker_response");
                    document::finish_check(conn, &running, &failed, &config.provider, &config.model)
                }
                Err(error) => Err(error),
            }
        })
        .await;
    match result {
        Ok(Ok(value)) => (StatusCode::CREATED, Json(value)).into_response(),
        Ok(Err(error)) => failure(error),
        Err(_) => StatusCode::SERVICE_UNAVAILABLE.into_response(),
    }
}
