//! General course candidates: Python validates shape, Core owns canonical bindings and writes.
use super::*;
use archeaxis_domain::course::{self, CourseBinding};
use rusqlite::OptionalExtension;
use sha2::{Digest, Sha256};
use std::time::Duration;
const SCHEMA: &str = "archeaxis.general-course-worker/v1";

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct FromKnowledgeBody {
    knowledge_id: String,
}

// A snapshot is read on Core's serialized connection and compared again before writing.
fn knowledge_snapshot(conn: &rusqlite::Connection, id: &str) -> rusqlite::Result<Option<Value>> {
    conn.query_row("SELECT k.body,k.status,k.anchor_id,k.receipt_hash,a.source_id,a.source_revision,s.sha256,s.original_name,
        EXISTS(SELECT 1 FROM knowledge_supersedes WHERE old_knowledge_id=k.knowledge_id)
        FROM knowledge k LEFT JOIN anchors a ON a.anchor_id=k.anchor_id
        LEFT JOIN sources s ON s.source_id=a.source_id WHERE k.knowledge_id=?1",[id],|r| {
        Ok(json!({"knowledge_id":id,"knowledge_version":id,"body":r.get::<_,String>(0)?,
            "status":r.get::<_,String>(1)?,"anchor_id":r.get::<_,Option<String>>(2)?,"receipt_hash":r.get::<_,String>(3)?,
            "source_id":r.get::<_,Option<String>>(4)?,"source_revision":r.get::<_,Option<String>>(5)?,
            "current_source_revision":r.get::<_,Option<String>>(6)?,"source_name":r.get::<_,Option<String>>(7)?,
            "superseded":r.get::<_,bool>(8)?}))
    }).optional()
}

pub(super) async fn from_knowledge(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<FromKnowledgeBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "course candidate creation requires a human actor",
        );
    }
    if body.knowledge_id.trim().is_empty() || body.knowledge_id.len() > 256 {
        return error(StatusCode::UNPROCESSABLE_ENTITY, "invalid knowledge ID");
    }
    let id = body.knowledge_id;
    let lookup = id.clone();
    let snapshot = match runtime
        .executor
        .store()
        .submit_wait(move |conn| knowledge_snapshot(conn, &lookup))
        .await
    {
        Ok(Ok(Some(value))) => value,
        Ok(Ok(None)) => return error(StatusCode::NOT_FOUND, "knowledge not found"),
        _ => return error(StatusCode::INTERNAL_SERVER_ERROR, "knowledge read failed"),
    };
    if snapshot["status"] != "accepted"
        || snapshot["superseded"] != false
        || !snapshot["source_id"].is_string()
        || !snapshot["source_revision"].is_string()
        || snapshot["source_revision"] != snapshot["current_source_revision"]
    {
        return error(
            StatusCode::CONFLICT,
            "course requires current anchored accepted knowledge",
        );
    }
    let text = snapshot["body"].as_str().unwrap();
    if text.trim().is_empty() || text.len() > 16384 {
        return error(
            StatusCode::UNPROCESSABLE_ENTITY,
            "knowledge body exceeds course bounds",
        );
    }
    // Source names may contain legacy paths; show just the actual filename, or a body excerpt.
    let source_title = snapshot["source_name"]
        .as_str()
        .unwrap_or("")
        .rsplit(['/', '\\'])
        .next()
        .unwrap_or("")
        .trim();
    let title = if source_title.is_empty() {
        text.trim()
    } else {
        source_title
    }
    .chars()
    .take(80)
    .collect::<String>();
    // Immutable knowledge revision + exact body and renderer contract determine identity.
    // Source metadata is deliberately excluded: rebinding that revision must conflict, never overwrite.
    let seed = json!([
        "from-knowledge/v1",
        "archeaxis.course-manifest/v1",
        "native-lesson",
        "1.0.0",
        id,
        text
    ]);
    let digest = format!("{:x}", Sha256::digest(seed.to_string().as_bytes()));
    let course_id = format!("course-{digest}");
    let component_id = format!("kc-{digest}");
    let artifact_id = format!("lesson-{digest}");
    // Materialize the existing Python contract defaults so validation may normalize JSON
    // without gaining authority to change any Core-selected content or identity.
    let manifest = json!({"schema":"archeaxis.course-manifest/v1","manifest_id":course_id,"title":title,"domain_pack_id":"general","status":"candidate",
        "knowledge_components":[{"schema":"archeaxis.knowledge-component/v1","component_id":component_id,"kind":"concept","title":title,"statement":text,"source_ids":[snapshot["source_id"]],"prerequisite_ids":[]}],
        "learning_objectives":[{"schema":"archeaxis.learning-objective/v1","objective_id":format!("objective-{digest}"),"title":"解释知识并指出来源","statement":"用自己的话解释已选知识并指出来源","knowledge_component_ids":[component_id]}],
        "artifacts":[{"schema":"archeaxis.courseware-artifact/v1","artifact_id":artifact_id,"artifact_type":"lesson","title":title,"domain_pack_id":"general","source_ids":[snapshot["source_id"]],"knowledge_ids":[component_id],"renderer":"native-lesson","renderer_version":"1.0.0","status":"candidate","interactive":false,"derived_only":true,"human_review_required":true}]});
    let validated = match worker(
        &runtime,
        json!({"schema":SCHEMA,"operation":"validate","manifest":manifest}),
        "VALIDATED",
    )
    .await
    {
        Ok(value) => value,
        Err(response) => return response,
    };
    let normalized = validated["manifest"].clone();
    if normalized != manifest {
        return error(
            StatusCode::BAD_GATEWAY,
            "course validator changed Core-generated content or identity",
        );
    }
    let binding = CourseBinding {
        component_id,
        knowledge_id: id.clone(),
        knowledge_version: id.clone(),
        source_id: snapshot["source_id"].as_str().unwrap().into(),
        source_revision: snapshot["source_revision"].as_str().unwrap().into(),
    };
    let suggested = json!({"item_key":format!("course:{course_id}:artifact:{artifact_id}"),"course_id":course_id,"artifact_id":artifact_id,"knowledge_id":id,"knowledge_version":id,"source_id":binding.source_id,"source_revision":binding.source_revision});
    match runtime.executor.store().submit_wait(move |conn| {
        if knowledge_snapshot(conn,&id)?.as_ref()!=Some(&snapshot) {
            return Err(rusqlite::Error::InvalidParameterName("knowledge or source changed during course generation".into()));
        }
        course::create_candidate(conn,&normalized,&[binding])
    }).await {
        Ok(Ok(value))=>(StatusCode::CREATED,Json(json!({"course":value,"suggested_learning_item":suggested,"human_review_required":true}))).into_response(),
        Ok(Err(rusqlite::Error::InvalidParameterName(reason)))=>error(StatusCode::CONFLICT,&reason),
        Ok(Err(failure)) if failure.sqlite_error_code()==Some(rusqlite::ErrorCode::ConstraintViolation)=>error(StatusCode::CONFLICT,"course identity conflicts with existing records"),
        _=>error(StatusCode::INTERNAL_SERVER_ERROR,"course candidate persistence failed"),
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct CreateBody {
    manifest: Value,
    bindings: Vec<Binding>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Binding {
    component_id: String,
    knowledge_id: String,
    knowledge_version: String,
    source_id: String,
    source_revision: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RenderBody {
    artifact_id: String,
}

fn error(status: StatusCode, message: &str) -> Response {
    // The same envelope every other route answers with. This module used to answer `{"error": ...}`,
    // so a client reading `code` found nothing and could not tell a retryable refusal from a
    // permanent one. The code follows from the status, which is already what decides it; the
    // contract accepts that one code may cover several messages and the message disambiguates.
    let code = match status.as_u16() {
        400 | 422 => "AAK-VAL-001",
        404 => "AAK-VAL-004",
        409 => "AAK-CON-002",
        // A failed or absent worker is an execution problem, not a bad request, so 5xx keeps the
        // worker code wherever the status came from.
        500..=599 => "AAK-WORKER-001",
        _ => "AAK-VAL-001",
    };
    (
        status,
        Json(json!({
            "code": code,
            "message": message,
            "retryable": status == StatusCode::SERVICE_UNAVAILABLE,
        })),
    )
        .into_response()
}
async fn worker(runtime: &Runtime, request: Value, expected: &str) -> Result<Value, Response> {
    if let Some(refusal) = crate::capabilities::refusal(&runtime.executor, "course.general").await {
        return Err(refusal);
    }
    let result = runtime
        .executor
        .derived_json("course.general", request, Duration::from_secs(30))
        .await
        .map_err(|reason| error(StatusCode::SERVICE_UNAVAILABLE, &reason))?;
    let doc = &result["document"];
    if doc["schema"] != SCHEMA {
        return Err(error(
            StatusCode::BAD_GATEWAY,
            "invalid course worker schema",
        ));
    }
    if result["exit_code"] != 0 || doc["status"] != expected {
        let status = if doc["status"] == "INVALID_REQUEST" {
            StatusCode::UNPROCESSABLE_ENTITY
        } else {
            StatusCode::SERVICE_UNAVAILABLE
        };
        return Err((status, Json(json!({"worker_outcome":result}))).into_response());
    }
    if doc["derived_only"] != true
        || doc["human_review_required"] != true
        || doc["canonical_bindings_verified"] != false
    {
        return Err(error(
            StatusCode::BAD_GATEWAY,
            "invalid course worker authority claim",
        ));
    }
    Ok(doc.clone())
}

pub(super) async fn create(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<CreateBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "course candidate creation requires a human actor",
        );
    }
    if body.bindings.is_empty() || body.bindings.len() > 128 {
        return error(
            StatusCode::UNPROCESSABLE_ENTITY,
            "course bindings exceed bounds",
        );
    }
    let validated = match worker(
        &runtime,
        json!({"schema":SCHEMA,"operation":"validate","manifest":body.manifest}),
        "VALIDATED",
    )
    .await
    {
        Ok(value) => value,
        Err(response) => return response,
    };
    let manifest = validated["manifest"].clone();
    let bindings = body
        .bindings
        .into_iter()
        .map(|b| CourseBinding {
            component_id: b.component_id,
            knowledge_id: b.knowledge_id,
            knowledge_version: b.knowledge_version,
            source_id: b.source_id,
            source_revision: b.source_revision,
        })
        .collect::<Vec<_>>();
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| course::create_candidate(conn, &manifest, &bindings))
        .await
    {
        Ok(Ok(value)) => (StatusCode::CREATED, Json(value)).into_response(),
        Ok(Err(rusqlite::Error::InvalidParameterName(reason))) => {
            error(StatusCode::CONFLICT, &reason)
        }
        Ok(Err(failure))
            if failure.sqlite_error_code() == Some(rusqlite::ErrorCode::ConstraintViolation) =>
        {
            error(
                StatusCode::CONFLICT,
                "course identity or binding constraint conflicts with existing records",
            )
        }
        _ => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "course candidate persistence failed",
        ),
    }
}

async fn load(runtime: &Runtime, id: String) -> Result<Value, Response> {
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| course::read_candidate(conn, &id))
        .await
    {
        Ok(Ok(Some(value))) => Ok(value),
        Ok(Ok(None)) => Err(error(StatusCode::NOT_FOUND, "course candidate not found")),
        _ => Err(error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "course candidate read failed",
        )),
    }
}
pub(super) async fn read(State(runtime): State<Runtime>, Path(id): Path<String>) -> Response {
    match load(&runtime, id).await {
        Ok(value) => Json(value).into_response(),
        Err(response) => response,
    }
}
pub(super) async fn render(
    State(runtime): State<Runtime>,
    Path(id): Path<String>,
    Json(body): Json<RenderBody>,
) -> Response {
    let course = match load(&runtime, id.clone()).await {
        Ok(value) => value,
        Err(response) => return response,
    };
    if course["stale"] != false {
        return error(StatusCode::CONFLICT, "course canonical bindings are stale");
    }
    let artifact = course["manifest"]["artifacts"]
        .as_array()
        .and_then(|items| {
            items
                .iter()
                .find(|item| item["artifact_id"] == body.artifact_id)
        })
        .cloned();
    let Some(artifact) = artifact else {
        return error(StatusCode::NOT_FOUND, "stored course artifact not found");
    };
    let derived=match worker(&runtime,json!({"schema":SCHEMA,"operation":"render","manifest":course["manifest"],"artifact":artifact}),"DERIVED").await {
        Ok(value)=>value,Err(response)=>return response
    };
    if derived["manifest"] != course["manifest"] || derived["artifact"] != artifact {
        return error(
            StatusCode::BAD_GATEWAY,
            "renderer changed stored course identity",
        );
    }
    // A source may change while the read-only worker is running. Recheck before returning a current projection.
    let latest = match load(&runtime, id).await {
        Ok(value) => value,
        Err(response) => return response,
    };
    if latest["stale"] != false || latest["manifest"] != course["manifest"] {
        return error(StatusCode::CONFLICT, "course changed during rendering");
    }
    Json(json!({"course":latest,"render":derived,"derived_only":true,"canonical_bindings_verified":true,"human_review_required":true})).into_response()
}
