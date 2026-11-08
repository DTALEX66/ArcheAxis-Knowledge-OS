//! General course candidates: Python validates shape, Core owns canonical bindings and writes.
use super::*;
use archeaxis_application::executor::{OpenMaicInteractiveStage, OpenMaicSlideStage};
use archeaxis_domain::course::{self, CourseBinding};
use archeaxis_domain::openmaic_interactive;
use archeaxis_domain::openmaic_interactive_outline;
use archeaxis_domain::openmaic_outline;
use archeaxis_domain::openmaic_quiz;
use archeaxis_domain::openmaic_quiz_actions;
use archeaxis_domain::openmaic_slide;
use archeaxis_domain::openmaic_slide_actions;
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

/// Request an inert, source-version-bound OpenMAIC scene candidate. The
/// request, the worker reply and the resulting Document can contain answers;
/// only a human caller receives it and none is placed in generic job output.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct OpenMaicSceneBody {
    create_request_id: String,
    request: Value,
}

/// The persisted candidate as a client reads it. `contract_version`, `projection`
/// and `render` are Core-derived: a legacy v1 candidate says the reports were never
/// recorded, so a caller cannot read an empty field as "lossless" or "playable".
fn openmaic_receipt_response(receipt: &Value, worker_invoked: bool) -> Response {
    Json(json!({"schema":"archeaxis.openmaic-scene-persistence/v1",
        "worker_invoked":worker_invoked,"document":receipt["document"],
        "candidate_document_status":receipt["candidate_document_status"],
        "source_snapshot_status":receipt["source_snapshot_status"],
        "source_derivation":"client_declared_unverified","human_review_required":true,
        "rendering_authorized":false,"answer_secrecy":"not_established",
        "contract_version":receipt["contract_version"],
        "projection":receipt["projection"],"render":receipt["render"]}))
    .into_response()
}

/// A refusal this slice can name precisely: an unknown request version, a scene
/// kind it cannot build, or an unknown scene content version. Anything else stays
/// a normal validation conflict.
fn openmaic_refusal_response(refusal: &Value) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({"code":"AAK-VAL-001",
        "message":"this offline slide/quiz slice cannot build the declared OpenMAIC scene",
        "retryable":false,"refusal":refusal,
        "supported_scene_types":["slide","quiz"],
        "supported_scene_versions":[1]})),
    )
        .into_response()
}

pub(super) async fn create_openmaic_scene(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<OpenMaicSceneBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "OpenMAIC scene creation requires a human actor",
        );
    }
    let create_request_id = body.create_request_id;
    let request = body.request;
    if let Some(refusal) = course::openmaic_refusal(&request) {
        return openmaic_refusal_response(&refusal);
    }
    // Capture the admission generation before the potentially queued Core
    // preparation. A disable/re-enable while preparation is waiting must not
    // let that older request dispatch under the newer generation. An existing
    // candidate remains readable without a configured or enabled provider.
    let admission = runtime.executor.openmaic_admission_generation().await;
    let lookup_id = create_request_id.clone();
    let lookup_request = request.clone();
    let prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| course::prepare_openmaic_scene(conn, &lookup_id, &lookup_request))
        .await
    {
        Ok(Ok(prepared)) => prepared,
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return error(
                StatusCode::NOT_FOUND,
                "OpenMAIC source document is unavailable",
            );
        }
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_))) => {
            return error(
                StatusCode::CONFLICT,
                "OpenMAIC request or source snapshot is invalid or changed",
            );
        }
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC preparation failed",
            );
        }
    };
    let pending = match prepared {
        course::OpenMaicPreparation::Existing(receipt) => {
            return openmaic_receipt_response(&receipt, false);
        }
        course::OpenMaicPreparation::Pending(pending) => pending,
    };
    let generation = match admission {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC provider unavailable or disabled",
            );
        }
    };
    let result = match runtime
        .executor
        .openmaic_scene_with_generation(generation, request.clone(), Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC worker did not produce a candidate",
            );
        }
    };
    if result["exit_code"] != 0 || result["document"]["status"] != "CANDIDATE" {
        return error(
            StatusCode::UNPROCESSABLE_ENTITY,
            "OpenMAIC worker did not produce a candidate",
        );
    }
    let worker_document = result["document"].clone();
    let committed = runtime
        .executor
        .commit_openmaic_if_current(generation, move |conn| {
            course::commit_openmaic_scene(
                conn,
                &create_request_id,
                &request,
                &pending,
                &worker_document,
            )
        })
        .await;
    match committed {
        Ok(Ok(receipt)) => openmaic_receipt_response(&receipt, true),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_))) => error(
            StatusCode::CONFLICT,
            "OpenMAIC request, source, capability or workspace changed",
        ),
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            error(StatusCode::CONFLICT, "OpenMAIC source document changed")
        }
        Ok(Err(_)) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC candidate persistence failed",
        ),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC capability unavailable or withdrawn",
        ),
    }
}

/// Request an inert OpenMAIC outline candidate from a caller-declared model
/// reply. No model or network is invoked; the request and reply are stored as a
/// bounded ordinary Document that requires human review and grants no rendering.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct OpenMaicOutlineBody {
    create_request_id: String,
    request: Value,
}

fn openmaic_outline_receipt_response(receipt: &Value, worker_invoked: bool) -> Response {
    Json(json!({"schema":"archeaxis.openmaic-outline-persistence/v1",
        "worker_invoked":worker_invoked,"document":receipt["document"],
        "candidate_document_status":receipt["candidate_document_status"],
        "response_origin":"client_declared_unverified","model_call":"NOT_INVOKED",
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,
        "outline_count":receipt["outline_count"],"outlines":receipt["outlines"]}))
    .into_response()
}

/// Early refusals this slice can name precisely: an unknown request version, an
/// unexpected field set, an out-of-bounds requirement/source, or an unsupported
/// reply shape.
fn openmaic_outline_refusal_response(refusal: &Value) -> Response {
    (
        StatusCode::UNPROCESSABLE_ENTITY,
        Json(json!({"code":"AAK-VAL-001",
        "message":"this offline outline replay slice cannot accept the declared OpenMAIC request",
        "retryable":false,"refusal":refusal,
        "supported_request_schema":openmaic_outline::OPENMAIC_OUTLINE_REQUEST_SCHEMA,
        "supported_outline_types":["slide","quiz","interactive"]})),
    )
        .into_response()
}

pub(super) async fn create_openmaic_outline(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<OpenMaicOutlineBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "OpenMAIC outline creation requires a human actor",
        );
    }
    let create_request_id = body.create_request_id;
    let request = body.request;
    if let Some(refusal) = openmaic_outline::openmaic_outline_refusal(&request) {
        return openmaic_outline_refusal_response(&refusal);
    }
    // Capture the admission generation before the potentially queued Core
    // preparation, exactly like the scene route. An existing candidate stays
    // readable without a configured or enabled provider.
    let admission = runtime.executor.openmaic_admission_generation().await;
    let lookup_id = create_request_id.clone();
    let lookup_request = request.clone();
    let prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            openmaic_outline::prepare_openmaic_outline(conn, &lookup_id, &lookup_request)
        })
        .await
    {
        Ok(Ok(prepared)) => prepared,
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return error(
                StatusCode::CONFLICT,
                "OpenMAIC outline request or candidate identity changed",
            );
        }
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC outline preparation failed",
            );
        }
    };
    let pending = match prepared {
        openmaic_outline::OpenMaicOutlinePreparation::Existing(receipt) => {
            return openmaic_outline_receipt_response(&receipt, false);
        }
        openmaic_outline::OpenMaicOutlinePreparation::Pending(pending) => pending,
    };
    if runtime.executor.openmaic_outline_script().is_none() {
        return error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC outline provider unavailable or disabled",
        );
    }
    let generation = match admission {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC outline provider unavailable or disabled",
            );
        }
    };
    let result = match runtime
        .executor
        .openmaic_outline_with_generation(generation, request.clone(), Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC outline worker did not produce a candidate",
            );
        }
    };
    if result["exit_code"] != 0 || result["document"]["status"] != "CANDIDATE" {
        let document = &result["document"];
        // The worker's declared outcome is preserved verbatim: the caller sees
        // the status and reason it reported, not a generic failure message.
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"code":"AAK-VAL-001",
            "message":"OpenMAIC outline worker did not produce a candidate",
            "retryable":false,"worker_outcome":{
                "status":document["status"],"reason":document["reason"],
                "exit_code":result["exit_code"],
                "response_origin_verification":document["response_origin_verification"],
                "model_call":document["model_call"]}})),
        )
            .into_response();
    }
    let worker_document = result["document"].clone();
    let committed = runtime
        .executor
        .commit_openmaic_if_current(generation, move |conn| {
            openmaic_outline::commit_openmaic_outline(
                conn,
                &create_request_id,
                &request,
                &pending,
                &worker_document,
            )
        })
        .await;
    match committed {
        Ok(Ok(receipt)) => openmaic_outline_receipt_response(&receipt, true),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => error(
            StatusCode::CONFLICT,
            "OpenMAIC outline request, capability or workspace changed",
        ),
        Ok(Err(_)) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC outline candidate persistence failed",
        ),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC outline capability unavailable or withdrawn",
        ),
    }
}

/// Request one inert outline candidate from a **local** model instead of a
/// caller-declared reply. Core captures the donor prompts, calls the declared
/// local model, replays the reply through the same Node worker, and persists
/// only a `CANDIDATE`. No cloud fallback exists and no failure writes anything.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct OpenMaicOutlineGenerateBody {
    create_request_id: String,
    requirement: String,
    source_text: String,
    model: Option<String>,
}

fn openmaic_outline_generate_request(body: &OpenMaicOutlineGenerateBody) -> Value {
    json!({"schema":openmaic_outline::OPENMAIC_OUTLINE_GENERATE_REQUEST_SCHEMA,
        "create_request_id":&body.create_request_id,
        "requirement":&body.requirement,
        "source_text":&body.source_text,
        "model":body.model.clone().map(Value::String).unwrap_or(Value::Null)})
}

fn openmaic_outline_generate_response(receipt: &Value, worker_invoked: bool) -> Response {
    Json(
        json!({"schema":"archeaxis.openmaic-outline-generate-persistence/v1",
        "worker_invoked":worker_invoked,"document":receipt["document"],
        "candidate_document_status":receipt["candidate_document_status"],
        "generation_route":"local_model","model_call":"INVOKED",
        "model":receipt["model"],"model_observed":receipt["model_observed"],
        "model_reply_sha256":receipt["model_reply_sha256"],
        "prompt_binding":receipt["prompt_binding"],
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,
        "outline_count":receipt["outline_count"],"outlines":receipt["outlines"]}),
    )
    .into_response()
}

fn openmaic_interactive_outline_generate_request(body: &OpenMaicOutlineGenerateBody) -> Value {
    json!({"schema":openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_SCHEMA,
        "create_request_id":&body.create_request_id,
        "requirement":&body.requirement,
        "source_text":&body.source_text,
        "model":body.model.clone().map(Value::String).unwrap_or(Value::Null)})
}

fn openmaic_interactive_outline_generate_response(
    receipt: &Value,
    worker_invoked: bool,
) -> Response {
    Json(
        json!({"schema":"archeaxis.openmaic-interactive-outline-generate-persistence/v1",
        "worker_invoked":worker_invoked,"document":receipt["document"],
        "candidate_document_status":receipt["candidate_document_status"],
        "generation_route":openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_GENERATION_ROUTE,
        "model_call":"INVOKED",
        "model":receipt["model"],"model_observed":receipt["model_observed"],
        "model_reply_sha256":receipt["model_reply_sha256"],
        "prompt_binding":receipt["prompt_binding"],
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,
        "outline_count":receipt["outline_count"],"outlines":receipt["outlines"]}),
    )
    .into_response()
}

/// A stage failure named by the stage that produced it and by the worker's own
/// status/reason, never rewritten into a generic message.
fn openmaic_stage_failure(
    status: StatusCode,
    stage: &str,
    message: &str,
    outcome: Value,
) -> Response {
    let code = if status == StatusCode::UNPROCESSABLE_ENTITY {
        "AAK-VAL-001"
    } else {
        // A failed or absent provider is an execution problem, not a bad request.
        "AAK-WORKER-001"
    };
    (
        status,
        Json(json!({"code":code,"message":message,
            "retryable":status == StatusCode::SERVICE_UNAVAILABLE,
            "stage":stage,"worker_outcome":outcome})),
    )
        .into_response()
}

/// The bounded rule detail a worker records with a refusal: rule names, the
/// entry position and the offending field names. Model bytes stay in the worker,
/// so a caller can act on the reason without the route echoing reply content.
fn openmaic_stage_rules(values: Option<&Vec<Value>>, limit: usize) -> Vec<Value> {
    let mut names = Vec::new();
    if let Some(items) = values {
        for item in items.iter().take(limit) {
            if let Some(name) = item.as_str() {
                names.push(Value::from(name));
            }
        }
    }
    names
}

fn openmaic_stage_diagnostics(document: &Value) -> Value {
    const LIMIT: usize = 8;
    const FIELD_LIMIT: usize = 16;
    let differences = document["differences"]
        .as_array()
        .map(|items| {
            items
                .iter()
                .take(LIMIT)
                .map(|item| {
                    json!({
                        "kind": item["kind"],
                        "outline_index": item["outline_index"],
                        "fields": openmaic_stage_rules(item["fields"].as_array(), FIELD_LIMIT)
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    json!({
        "differences": differences,
        "transformations": openmaic_stage_rules(document["transformations"].as_array(), LIMIT)
    })
}

/// The worker's declared outcome plus the bounded rule names behind it.
fn openmaic_stage_outcome(result: &Value) -> Value {
    let document = &result["document"];
    let diagnostics = openmaic_stage_diagnostics(document);
    let mut outcome = json!({"status":document["status"],"reason":document["reason"],
        "error_code":document["error_code"],
        "exit_code":result["exit_code"],
        "differences":diagnostics["differences"],
        "transformations":diagnostics["transformations"]});
    if let Some(observation) = super::model_observation::project(document) {
        outcome["model_observation"] = observation;
    }
    outcome
}

/// An unusable worker receipt must not be recorded as a successful REPLY in
/// the optional narration stage, even if the worker claimed that status.
fn openmaic_unusable_model_outcome(result: &Value) -> (String, Value) {
    let status = result["document"]["status"]
        .as_str()
        .unwrap_or("INVALID_MODEL_OUTPUT");
    if status == "REPLY" {
        return (
            "INVALID_MODEL_OUTPUT".to_owned(),
            json!("MODEL_RECEIPT_INCONSISTENT"),
        );
    }
    (status.to_owned(), result["document"]["reason"].clone())
}

#[cfg(test)]
mod model_outcome_tests {
    use super::*;

    #[test]
    fn invalid_reply_claim_does_not_make_optional_actions_look_successful() {
        let claimed = json!({"document":{"status":"REPLY","reason":null}});
        assert_eq!(
            openmaic_unusable_model_outcome(&claimed),
            (
                "INVALID_MODEL_OUTPUT".to_owned(),
                json!("MODEL_RECEIPT_INCONSISTENT")
            )
        );
        let named = json!({"document":{"status":"INVALID_MODEL_OUTPUT","reason":"MODEL_NONSTOP"}});
        assert_eq!(
            openmaic_unusable_model_outcome(&named),
            ("INVALID_MODEL_OUTPUT".to_owned(), json!("MODEL_NONSTOP"))
        );
    }
}

pub(super) async fn generate_openmaic_outline(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<OpenMaicOutlineGenerateBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "OpenMAIC outline generation requires a human actor",
        );
    }
    let request = openmaic_outline_generate_request(&body);
    let create_request_id = body.create_request_id;
    if let Some(refusal) = openmaic_outline::openmaic_outline_generate_refusal(&request) {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"code":"AAK-VAL-001",
            "message":"this local-model outline route cannot accept the declared request",
            "retryable":false,"refusal":refusal,
            "supported_request_schema":openmaic_outline::OPENMAIC_OUTLINE_GENERATE_REQUEST_SCHEMA})),
        )
            .into_response();
    }
    // Capture the admission generation before the potentially queued Core
    // preparation, exactly like the replay route.
    let admission = runtime.executor.openmaic_admission_generation().await;
    let lookup_id = create_request_id.clone();
    let lookup_request = request.clone();
    let prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            openmaic_outline::prepare_openmaic_outline_generation(conn, &lookup_id, &lookup_request)
        })
        .await
    {
        Ok(Ok(prepared)) => prepared,
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return error(
                StatusCode::CONFLICT,
                "OpenMAIC outline request or candidate identity changed",
            );
        }
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC outline preparation failed",
            );
        }
    };
    let pending = match prepared {
        openmaic_outline::OpenMaicOutlineGenerationPreparation::Existing(receipt) => {
            // A repeated request reads the stored candidate; no prompt, model or
            // worker runs again.
            return openmaic_outline_generate_response(&receipt, false);
        }
        openmaic_outline::OpenMaicOutlineGenerationPreparation::Pending(pending) => pending,
    };
    if runtime.executor.openmaic_outline_script().is_none() {
        return error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC outline provider unavailable or disabled",
        );
    }
    let generation = match admission {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC outline provider unavailable or disabled",
            );
        }
    };
    // Stage 1: capture the donor prompts. The capture carries no reply.
    let capture = runtime
        .executor
        .openmaic_outline_with_generation(
            generation,
            openmaic_outline::openmaic_outline_capture_request(&request),
            Duration::from_secs(30),
        )
        .await;
    let capture = match capture {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "capture",
                "OpenMAIC outline worker unavailable at the capture stage",
                Value::Null,
            );
        }
    };
    let capture_outcome = openmaic_stage_outcome(&capture);
    if capture["exit_code"] != 0 || capture["document"]["status"] != "PROMPT_CAPTURED" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "capture",
            "OpenMAIC outline capture did not produce a prompt binding",
            capture_outcome,
        );
    }
    let binding = match openmaic_outline::openmaic_outline_capture_binding(
        &create_request_id,
        &capture["document"],
    ) {
        Ok(binding) => binding,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "capture",
                "OpenMAIC outline capture receipt is inconsistent",
                capture_outcome,
            );
        }
    };
    // Stage 2: the local model. An unregistered or disabled capability is an
    // unavailability that names itself, never a fabricated reply.
    let model_request =
        openmaic_outline::openmaic_outline_model_request(&binding, &request["model"]);
    let model = runtime
        .executor
        .derived_json(
            openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
            model_request,
            Duration::from_secs(120),
        )
        .await;
    let model = match model {
        Ok(value) => value,
        Err(reason) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "local_model",
                &format!("local model capability unavailable: {reason}"),
                Value::Null,
            );
        }
    };
    let model_outcome = openmaic_stage_outcome(&model);
    if model["exit_code"] != 0 || model["document"]["status"] != "REPLY" {
        let named = model["document"]["status"].as_str().unwrap_or("");
        let status = match named {
            "INVALID_MODEL_OUTPUT" | "MODEL_REJECTED" => StatusCode::UNPROCESSABLE_ENTITY,
            "MODEL_TIMEOUT" | "NO_FINAL_ANSWER" => StatusCode::GATEWAY_TIMEOUT,
            // Unavailable, or an outcome this slice cannot read.
            _ => StatusCode::SERVICE_UNAVAILABLE,
        };
        return openmaic_stage_failure(
            status,
            "local_model",
            "the local model did not produce a usable reply",
            model_outcome,
        );
    }
    let Some(content) =
        openmaic_outline::openmaic_outline_new_model_content(&model["document"]).map(str::to_owned)
    else {
        return openmaic_stage_failure(
            StatusCode::BAD_GATEWAY,
            "local_model",
            "local model receipt is inconsistent",
            model_outcome,
        );
    };
    // Stage 3: replay the model text through the real outline worker.
    let replay_request =
        openmaic_outline::openmaic_outline_replay_request(&request, &binding, &content);
    let replay = runtime
        .executor
        .openmaic_outline_with_generation(generation, replay_request, Duration::from_secs(30))
        .await;
    let replay = match replay {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "replay",
                "OpenMAIC outline worker unavailable at the replay stage",
                Value::Null,
            );
        }
    };
    let replay_outcome = openmaic_stage_outcome(&replay);
    if replay["exit_code"] != 0 || replay["document"]["status"] != "CANDIDATE" {
        // Every named replay outcome (`BINDING_MISMATCH`, `INVALID_RESPONSE`,
        // `UPSTREAM_FAILURE`, ...) keeps its own status and reason.
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "replay",
            "OpenMAIC outline replay did not produce a candidate",
            replay_outcome,
        );
    }
    let stage = openmaic_outline::OpenMaicLocalGeneration {
        binding,
        model_reply: model["document"].clone(),
        replay_document: replay["document"].clone(),
    };
    let committed = runtime
        .executor
        .commit_openmaic_if_current(generation, move |conn| {
            openmaic_outline::commit_openmaic_outline_generation(
                conn,
                &create_request_id,
                &request,
                &pending,
                &stage,
            )
        })
        .await;
    match committed {
        Ok(Ok(receipt)) => openmaic_outline_generate_response(&receipt, true),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => error(
            StatusCode::CONFLICT,
            "OpenMAIC outline request, capability or workspace changed",
        ),
        Ok(Err(_)) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC outline candidate persistence failed",
        ),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC outline capability unavailable or withdrawn",
        ),
    }
}

/// Local-model generation of interactive outlines: capture the donor
/// `interactive-outlines` prompt, call the declared local model, replay the reply
/// through the same adapter and persist one inert outline candidate Document.
/// Only a replayed `CANDIDATE` is stored; no failure writes a partial candidate.
pub(super) async fn generate_openmaic_interactive_outline(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<OpenMaicOutlineGenerateBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "OpenMAIC interactive outline generation requires a human actor",
        );
    }
    let request = openmaic_interactive_outline_generate_request(&body);
    let create_request_id = body.create_request_id;
    if let Some(refusal) =
        openmaic_interactive_outline::openmaic_interactive_outline_refusal(&request)
    {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"code":"AAK-VAL-001",
            "message":"this interactive outline route cannot accept the declared request",
            "retryable":false,"refusal":refusal,
            "supported_request_schema":openmaic_interactive_outline::OPENMAIC_INTERACTIVE_OUTLINE_REQUEST_SCHEMA})),
        )
            .into_response();
    }
    // Capture the admission generation before the potentially queued Core
    // preparation, exactly like the standard outline route.
    let admission = runtime.executor.openmaic_admission_generation().await;
    let lookup_id = create_request_id.clone();
    let lookup_request = request.clone();
    let prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            openmaic_interactive_outline::prepare_openmaic_interactive_outline(
                conn,
                &lookup_id,
                &lookup_request,
            )
        })
        .await
    {
        Ok(Ok(prepared)) => prepared,
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return error(
                StatusCode::CONFLICT,
                "OpenMAIC interactive outline request or candidate identity changed",
            );
        }
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC interactive outline preparation failed",
            );
        }
    };
    let pending = match prepared {
        openmaic_interactive_outline::OpenMaicInteractiveOutlinePreparation::Existing(receipt) => {
            // A repeated request reads the stored candidate; no prompt, model or
            // worker runs again.
            return openmaic_interactive_outline_generate_response(&receipt, false);
        }
        openmaic_interactive_outline::OpenMaicInteractiveOutlinePreparation::Pending(pending) => {
            pending
        }
    };
    if runtime
        .executor
        .openmaic_interactive_outline_script()
        .is_none()
    {
        return openmaic_stage_failure(
            StatusCode::SERVICE_UNAVAILABLE,
            "interactive_outline",
            "OpenMAIC interactive outline provider unavailable or disabled",
            Value::Null,
        );
    }
    let generation = match admission {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC interactive outline provider unavailable or disabled",
            );
        }
    };
    // Stage 1: render the donor interactive-outlines prompt. It carries no reply.
    let capture = match runtime
        .executor
        .openmaic_interactive_outline_with_generation(
            generation,
            openmaic_interactive_outline::openmaic_interactive_outline_capture_request(&request),
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "interactive_outline",
                "OpenMAIC interactive outline worker unavailable at the capture stage",
                Value::Null,
            );
        }
    };
    let capture_outcome = openmaic_stage_outcome(&capture);
    if capture["exit_code"] != 0 || capture["document"]["status"] != "PROMPT_CAPTURED" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "interactive_outline",
            "OpenMAIC interactive outline capture did not produce a prompt binding",
            capture_outcome,
        );
    }
    let binding = match openmaic_interactive_outline::openmaic_interactive_outline_capture_binding(
        &create_request_id,
        &capture["document"],
    ) {
        Ok(binding) => binding,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "interactive_outline",
                "OpenMAIC interactive outline capture receipt is inconsistent",
                capture_outcome,
            );
        }
    };
    // Stage 2: the declared local model, through the same capability as the
    // standard outline route. An unavailable capability names itself.
    let model_request = openmaic_interactive_outline::openmaic_interactive_outline_model_request(
        &binding,
        &request["model"],
    );
    let model = match runtime
        .executor
        .derived_json(
            openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
            model_request,
            Duration::from_secs(120),
        )
        .await
    {
        Ok(value) => value,
        Err(reason) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "local_model",
                &format!("local model capability unavailable: {reason}"),
                Value::Null,
            );
        }
    };
    let model_outcome = openmaic_stage_outcome(&model);
    if model["exit_code"] != 0 || model["document"]["status"] != "REPLY" {
        let named = model["document"]["status"].as_str().unwrap_or("");
        let status = match named {
            "INVALID_MODEL_OUTPUT" | "MODEL_REJECTED" => StatusCode::UNPROCESSABLE_ENTITY,
            "MODEL_TIMEOUT" | "NO_FINAL_ANSWER" => StatusCode::GATEWAY_TIMEOUT,
            _ => StatusCode::SERVICE_UNAVAILABLE,
        };
        return openmaic_stage_failure(
            status,
            "local_model",
            "the local model did not produce a usable interactive outline reply",
            model_outcome,
        );
    }
    let Some(content) =
        openmaic_outline::openmaic_outline_new_model_content(&model["document"]).map(str::to_owned)
    else {
        return openmaic_stage_failure(
            StatusCode::BAD_GATEWAY,
            "local_model",
            "local model receipt is inconsistent",
            model_outcome,
        );
    };
    // Stage 3: replay the model text through the real interactive-outline worker.
    let replay_request = openmaic_interactive_outline::openmaic_interactive_outline_replay_request(
        &request, &binding, &content,
    );
    let replay = match runtime
        .executor
        .openmaic_interactive_outline_with_generation(
            generation,
            replay_request,
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "interactive_outline",
                "OpenMAIC interactive outline worker unavailable at the replay stage",
                Value::Null,
            );
        }
    };
    let replay_outcome = openmaic_stage_outcome(&replay);
    if replay["exit_code"] != 0 || replay["document"]["status"] != "CANDIDATE" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "interactive_outline",
            "OpenMAIC interactive outline replay did not produce a candidate",
            replay_outcome,
        );
    }
    let stage = openmaic_interactive_outline::OpenMaicInteractiveOutlineGeneration {
        binding,
        model_reply: model["document"].clone(),
        replay_document: replay["document"].clone(),
    };
    let committed = runtime
        .executor
        .commit_openmaic_if_current(generation, move |conn| {
            openmaic_interactive_outline::commit_openmaic_interactive_outline_generation(
                conn,
                &create_request_id,
                &request,
                &pending,
                &stage,
            )
        })
        .await;
    match committed {
        Ok(Ok(receipt)) => openmaic_interactive_outline_generate_response(&receipt, true),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => error(
            StatusCode::CONFLICT,
            "OpenMAIC interactive outline request, capability or workspace changed",
        ),
        Ok(Err(_)) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC interactive outline candidate persistence failed",
        ),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC interactive outline capability unavailable or withdrawn",
        ),
    }
}

/// Turn one persisted `slide` outline into a scene candidate through the donor
/// slide prompt/reply/normalize adapters and the declared local model. Only the
/// existing scene candidate Document is written, and only after every stage
/// produced an admitted candidate; there is no cloud fallback and no partial write.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct OpenMaicSlideCandidateBody {
    create_request_id: String,
    outline_document_id: String,
    outline_index: i64,
    source: Value,
    model: Option<String>,
}

fn openmaic_slide_request(body: &OpenMaicSlideCandidateBody) -> Value {
    json!({"schema":openmaic_slide::OPENMAIC_SLIDE_REQUEST_SCHEMA,
        "create_request_id":&body.create_request_id,
        "outline_document_id":&body.outline_document_id,
        "outline_index":body.outline_index,
        "source":&body.source,
        "model":body.model.clone().map(Value::String).unwrap_or(Value::Null)})
}

fn openmaic_slide_receipt_response(receipt: &Value, worker_invoked: bool) -> Response {
    Json(json!({"schema":"archeaxis.openmaic-slide-persistence/v1",
        "scene_route":"slide",
        "worker_invoked":worker_invoked,"document":receipt["document"],
        "candidate_document_status":receipt["candidate_document_status"],
        "source_snapshot_status":receipt["source_snapshot_status"],
        "generation_route":receipt["generation_route"],
        "model_call":receipt["model_call"],"model":receipt["model"],
        "model_observed":receipt["model_observed"],
        "model_reply_sha256":receipt["model_reply_sha256"],
        "model_finish_reason":receipt["model_finish_reason"],
        "prompt_binding":receipt["prompt_binding"],
        "outline_document_id":receipt["outline_document_id"],
        "outline_index":receipt["outline_index"],"outline_id":receipt["outline_id"],
        "reply":receipt["reply"],"normalize":receipt["normalize"],
        "actions_stage":receipt["actions_stage"],
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,
        "contract_version":receipt["contract_version"],
        "projection":receipt["projection"],"render":receipt["render"]}))
    .into_response()
}

/// The quiz chain reuses the same response envelope; `scene_route` names the
/// dispatched chain and the donor replay summary replaces the slide stages.
fn openmaic_quiz_receipt_response(receipt: &Value, worker_invoked: bool) -> Response {
    Json(json!({"schema":"archeaxis.openmaic-quiz-persistence/v1",
        "scene_route":"quiz",
        "worker_invoked":worker_invoked,"document":receipt["document"],
        "candidate_document_status":receipt["candidate_document_status"],
        "source_snapshot_status":receipt["source_snapshot_status"],
        "generation_route":receipt["generation_route"],
        "model_call":receipt["model_call"],"model":receipt["model"],
        "model_observed":receipt["model_observed"],
        "model_reply_sha256":receipt["model_reply_sha256"],
        "model_finish_reason":receipt["model_finish_reason"],
        "prompt_binding":receipt["prompt_binding"],
        "outline_document_id":receipt["outline_document_id"],
        "outline_index":receipt["outline_index"],"outline_id":receipt["outline_id"],
        "replay":receipt["replay"],
        "actions_stage":receipt["actions_stage"],
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,
        "contract_version":receipt["contract_version"],
        "projection":receipt["projection"],"render":receipt["render"]}))
    .into_response()
}

/// One named refusal from a domain read or write. A conflict is answered as `409`
/// and every content refusal as `422`, with the reason kept verbatim.
fn openmaic_slide_error(failure: archeaxis_domain::document::Error) -> Response {
    use archeaxis_domain::document::Error as Failure;
    match failure {
        Failure::NotFound => error(
            StatusCode::NOT_FOUND,
            "OpenMAIC outline or source document is unavailable",
        ),
        Failure::Conflict(_) => error(
            StatusCode::CONFLICT,
            "OpenMAIC slide request conflicts with an existing candidate",
        ),
        Failure::Invalid(reason) => {
            let conflict = matches!(
                reason,
                "SLIDE_REQUEST_CONFLICT"
                    | "SLIDE_REQUEST_CHANGED"
                    | "SLIDE_WORKSPACE_CHANGED"
                    | "OUTLINE_DOCUMENT_CHANGED"
                    | "SOURCE_SNAPSHOT_NOT_CURRENT"
            );
            let status = if conflict {
                StatusCode::CONFLICT
            } else {
                StatusCode::UNPROCESSABLE_ENTITY
            };
            let code = if conflict {
                "AAK-CON-002"
            } else {
                "AAK-VAL-001"
            };
            (
                status,
                Json(json!({"code":code,
                    "message":"this outline-slide route refused the request",
                    "retryable":false,"refusal":{"reason":reason}})),
            )
                .into_response()
        }
        Failure::Sql(_) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC slide store operation failed",
        ),
    }
}

/// One named refusal from a domain read or write. A conflict is answered as `409`
/// and every content refusal as `422`, with the reason kept verbatim. This maps
/// the quiz chain's own conflict reasons too; the shape is the same as the slide
/// chain because both write the same scene candidate.
fn openmaic_quiz_error(failure: archeaxis_domain::document::Error) -> Response {
    use archeaxis_domain::document::Error as Failure;
    match failure {
        Failure::NotFound => error(
            StatusCode::NOT_FOUND,
            "OpenMAIC outline or source document is unavailable",
        ),
        Failure::Conflict(_) => error(
            StatusCode::CONFLICT,
            "OpenMAIC quiz request conflicts with an existing candidate",
        ),
        Failure::Invalid(reason) => {
            let conflict = matches!(
                reason,
                "QUIZ_REQUEST_CONFLICT"
                    | "QUIZ_REQUEST_CHANGED"
                    | "QUIZ_WORKSPACE_CHANGED"
                    | "OUTLINE_DOCUMENT_CHANGED"
                    | "SOURCE_SNAPSHOT_NOT_CURRENT"
            );
            let status = if conflict {
                StatusCode::CONFLICT
            } else {
                StatusCode::UNPROCESSABLE_ENTITY
            };
            let code = if conflict {
                "AAK-CON-002"
            } else {
                "AAK-VAL-001"
            };
            (
                status,
                Json(json!({"code":code,
                    "message":"this outline-quiz route refused the request",
                    "retryable":false,"refusal":{"reason":reason}})),
            )
                .into_response()
        }
        Failure::Sql(_) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC quiz store operation failed",
        ),
    }
}

/// The interactive chain reuses the same response envelope; `scene_route` names
/// the dispatched chain and the widget/normalize summary replaces the slide stages.
fn openmaic_interactive_receipt_response(receipt: &Value, worker_invoked: bool) -> Response {
    Json(
        json!({"schema":"archeaxis.openmaic-interactive-persistence/v1",
        "scene_route":"interactive",
        "worker_invoked":worker_invoked,"document":receipt["document"],
        "candidate_document_status":receipt["candidate_document_status"],
        "source_snapshot_status":receipt["source_snapshot_status"],
        "generation_route":receipt["generation_route"],
        "model_call":receipt["model_call"],"model":receipt["model"],
        "model_observed":receipt["model_observed"],
        "model_reply_sha256":receipt["model_reply_sha256"],
        "model_finish_reason":receipt["model_finish_reason"],
        "widget_type":receipt["widget_type"],
        "prompt_binding":receipt["prompt_binding"],
        "outline_document_id":receipt["outline_document_id"],
        "outline_index":receipt["outline_index"],"outline_id":receipt["outline_id"],
        "normalize":receipt["normalize"],
        "html_execution":"NOT_PERFORMED",
        "response_origin":"LOCAL_MODEL_UNVERIFIED",
        "human_review_required":true,"active_content_executed":false,
        "rendering_authorized":false,
        "contract_version":receipt["contract_version"],
        "projection":receipt["projection"],"render":receipt["render"]}),
    )
    .into_response()
}

/// One named refusal from a domain read or write. A conflict is answered as `409`
/// and every content refusal as `422`, with the reason kept verbatim.
fn openmaic_interactive_error(failure: archeaxis_domain::document::Error) -> Response {
    use archeaxis_domain::document::Error as Failure;
    match failure {
        Failure::NotFound => error(
            StatusCode::NOT_FOUND,
            "OpenMAIC outline or source document is unavailable",
        ),
        Failure::Conflict(_) => error(
            StatusCode::CONFLICT,
            "OpenMAIC interactive request conflicts with an existing candidate",
        ),
        Failure::Invalid(reason) => {
            let conflict = matches!(
                reason,
                "INTERACTIVE_REQUEST_CONFLICT"
                    | "INTERACTIVE_REQUEST_CHANGED"
                    | "INTERACTIVE_WORKSPACE_CHANGED"
                    | "OUTLINE_DOCUMENT_CHANGED"
                    | "SOURCE_SNAPSHOT_NOT_CURRENT"
            );
            let status = if conflict {
                StatusCode::CONFLICT
            } else {
                StatusCode::UNPROCESSABLE_ENTITY
            };
            let code = if conflict {
                "AAK-CON-002"
            } else {
                "AAK-VAL-001"
            };
            (
                status,
                Json(json!({"code":code,
                    "message":"this outline-interactive route refused the request",
                    "retryable":false,"refusal":{"reason":reason}})),
            )
                .into_response()
        }
        Failure::Sql(_) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC interactive store operation failed",
        ),
    }
}

/// The first fixed adapter this chain needs that the launch does not provide.
fn openmaic_slide_script_gap(runtime: &Runtime) -> Option<&'static str> {
    for (stage, label) in [
        (OpenMaicSlideStage::Prompt, "slide_prompt"),
        (OpenMaicSlideStage::Reply, "slide_reply"),
        (OpenMaicSlideStage::Normalize, "slide_normalize"),
    ] {
        if runtime.executor.openmaic_slide_script(stage).is_none() {
            return Some(label);
        }
    }
    if runtime.executor.openmaic_slide_actions_script().is_none() {
        return Some("slide_actions");
    }
    if runtime.executor.openmaic_node_paths().is_none() {
        return Some("scene_build");
    }
    None
}

/// The quiz chain needs its content and action adapters plus the existing scene
/// builder. A missing action adapter names that stage instead of dropping it.
fn openmaic_quiz_script_gap(runtime: &Runtime) -> Option<&'static str> {
    if runtime.executor.openmaic_quiz_script().is_none() {
        return Some("quiz_replay");
    }
    if runtime.executor.openmaic_quiz_actions_script().is_none() {
        return Some("quiz_actions");
    }
    if runtime.executor.openmaic_node_paths().is_none() {
        return Some("scene_build");
    }
    None
}

/// One route, two chains: the persisted outline's `type` selects the donor
/// adapters. The request and response envelopes are shared; only the chain-specific
/// stage summary and `scene_route` differ.
pub(super) async fn generate_openmaic_scene_from_outline(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<OpenMaicSlideCandidateBody>,
) -> Response {
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "OpenMAIC scene generation requires a human actor",
        );
    }
    let request = openmaic_slide_request(&body);
    let create_request_id = body.create_request_id.clone();
    if let Some(refusal) = openmaic_slide::openmaic_slide_refusal(&request) {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"code":"AAK-VAL-001",
            "message":"this outline-scene generation route cannot accept the declared request",
            "retryable":false,"refusal":refusal,
            "supported_request_schema":openmaic_slide::OPENMAIC_SLIDE_REQUEST_SCHEMA})),
        )
            .into_response();
    }
    // The persisted outline candidate is read once; no model is asked for the
    // outline title, description or key points again.
    let lookup_document = body.outline_document_id.clone();
    let lookup_index = body.outline_index;
    let selection = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            openmaic_slide::read_outline_candidate(conn, &lookup_document, lookup_index)
        })
        .await
    {
        Ok(Ok(value)) => value,
        Ok(Err(failure)) => return openmaic_slide_error(failure),
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC outline candidate read failed",
            );
        }
    };
    // Capture the admission generation before either chain's potentially queued
    // Core preparation. A disable/re-enable while preparation is waiting must not
    // let that older request dispatch under the newer generation. An existing
    // candidate stays readable without a configured or enabled provider.
    let admission = runtime.executor.openmaic_admission_generation().await;
    match selection["outline"]["type"].as_str() {
        Some("slide") => {
            openmaic_slide_chain(runtime, create_request_id, request, selection, admission).await
        }
        Some("quiz") => {
            openmaic_quiz_chain(runtime, create_request_id, request, selection, admission).await
        }
        Some("interactive") => {
            openmaic_interactive_chain(runtime, create_request_id, request, selection, admission)
                .await
        }
        other => (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(json!({"code":"AAK-VAL-001",
            "message":"this route builds only slide, quiz and interactive outlines",
            "retryable":false,"refusal":{"reason":"UNSUPPORTED_OUTLINE_TYPE",
            "declared":other,"supported":["slide","quiz","interactive"]}})),
        )
            .into_response(),
    }
}

async fn openmaic_slide_chain(
    runtime: Runtime,
    create_request_id: String,
    request: Value,
    selection: Value,
    admission: Result<u64, String>,
) -> Response {
    let prepare_id = create_request_id.clone();
    let prepare_request = request.clone();
    let prepare_selection = selection.clone();
    let prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            openmaic_slide::prepare_openmaic_slide_candidate(
                conn,
                &prepare_id,
                &prepare_request,
                &prepare_selection,
            )
        })
        .await
    {
        Ok(Ok(value)) => value,
        Ok(Err(failure)) => return openmaic_slide_error(failure),
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC slide preparation failed",
            );
        }
    };
    let pending = match prepared {
        openmaic_slide::OpenMaicSlidePreparation::Existing(receipt) => {
            // A repeated request reads the stored candidate; no prompt, model or
            // worker runs again.
            return openmaic_slide_receipt_response(&receipt, false);
        }
        openmaic_slide::OpenMaicSlidePreparation::Pending(pending) => pending,
    };
    // An existing candidate stays readable without a configured or enabled provider;
    // a fresh chain needs every fixed adapter up front, so a missing one is named
    // before the model is called rather than after.
    if let Some(stage) = openmaic_slide_script_gap(&runtime) {
        return openmaic_stage_failure(
            StatusCode::SERVICE_UNAVAILABLE,
            stage,
            "OpenMAIC slide chain unavailable: a fixed sibling script is missing",
            Value::Null,
        );
    }
    let generation = match admission {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC provider unavailable or disabled",
            );
        }
    };
    // Stage 1: the donor slide prompt.
    let prompt_request = match openmaic_slide::openmaic_slide_prompt_request(&selection) {
        Ok(value) => value,
        Err(failure) => return openmaic_slide_error(failure),
    };
    let prompt = match runtime
        .executor
        .openmaic_slide_with_generation(
            OpenMaicSlideStage::Prompt,
            generation,
            prompt_request,
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "slide_prompt",
                "OpenMAIC slide prompt worker unavailable",
                Value::Null,
            );
        }
    };
    let prompt_outcome = openmaic_stage_outcome(&prompt);
    if prompt["exit_code"] != 0 || prompt["document"]["status"] != "BUILT" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "slide_prompt",
            "OpenMAIC slide prompt did not build the donor prompts",
            prompt_outcome,
        );
    }
    let binding = match openmaic_slide::openmaic_slide_prompt_binding(&prompt["document"]) {
        Ok(value) => value,
        Err(archeaxis_domain::document::Error::Invalid(reason)) => {
            let mut outcome = prompt_outcome.clone();
            outcome["receipt_refusal"] = json!(reason);
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "slide_prompt",
                "OpenMAIC slide prompt receipt is inconsistent",
                outcome,
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "slide_prompt",
                "OpenMAIC slide prompt receipt is inconsistent",
                prompt_outcome,
            );
        }
    };
    // Stage 2: the declared local model, through the same capability and worker as
    // the outline route. An unregistered or disabled capability is an unavailability.
    let model_request =
        openmaic_outline::openmaic_outline_model_request(&binding, &request["model"]);
    let model = match runtime
        .executor
        .derived_json(
            openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
            model_request,
            Duration::from_secs(120),
        )
        .await
    {
        Ok(value) => value,
        Err(reason) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "local_model",
                &format!("local model capability unavailable: {reason}"),
                Value::Null,
            );
        }
    };
    let model_outcome = openmaic_stage_outcome(&model);
    if model["exit_code"] != 0 || model["document"]["status"] != "REPLY" {
        let named = model["document"]["status"].as_str().unwrap_or("");
        let status = match named {
            "INVALID_MODEL_OUTPUT" | "MODEL_REJECTED" => StatusCode::UNPROCESSABLE_ENTITY,
            "MODEL_TIMEOUT" | "NO_FINAL_ANSWER" => StatusCode::GATEWAY_TIMEOUT,
            _ => StatusCode::SERVICE_UNAVAILABLE,
        };
        return openmaic_stage_failure(
            status,
            "local_model",
            "the local model did not produce a usable slide reply",
            model_outcome,
        );
    }
    let Some(content) =
        openmaic_outline::openmaic_outline_new_model_content(&model["document"]).map(str::to_owned)
    else {
        return openmaic_stage_failure(
            StatusCode::BAD_GATEWAY,
            "local_model",
            "local model receipt is inconsistent",
            model_outcome,
        );
    };
    // Stage 3: the donor reply adapter. A quarantined or rejected reply keeps the
    // worker's own status and reason; Core never repairs or invents content.
    let reply_request = match openmaic_slide::openmaic_slide_reply_request(&content) {
        Ok(value) => value,
        Err(archeaxis_domain::document::Error::Invalid(reason)) => {
            return openmaic_stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "slide_reply",
                "the local model reply exceeds the donor reply budget",
                json!({"status":"MODEL_REPLY_EXCEEDS_BOUND","reason":reason,
                    "exit_code":model["exit_code"]}),
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "slide_reply",
                "the local model reply cannot be replayed",
                model_outcome,
            );
        }
    };
    let reply = match runtime
        .executor
        .openmaic_slide_with_generation(
            OpenMaicSlideStage::Reply,
            generation,
            reply_request,
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "slide_reply",
                "OpenMAIC slide reply worker unavailable",
                Value::Null,
            );
        }
    };
    let reply_outcome = openmaic_stage_outcome(&reply);
    let normalized_reply = match openmaic_slide::openmaic_slide_reply_candidate(&reply["document"])
    {
        Ok(Some(value)) => value,
        Ok(None) => {
            return openmaic_stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "slide_reply",
                "the donor reply adapter did not admit the model text",
                reply_outcome,
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "slide_reply",
                "OpenMAIC slide reply receipt is inconsistent",
                reply_outcome,
            );
        }
    };
    // Stage 4: the donor normalize adapter over the Core-built scene envelope.
    let scene = match openmaic_slide::openmaic_slide_scene_request(
        &create_request_id,
        &selection,
        &normalized_reply,
    ) {
        Ok(value) => value,
        Err(failure) => return openmaic_slide_error(failure),
    };
    let normalize_request =
        match openmaic_slide::openmaic_slide_normalize_request(&create_request_id, &scene) {
            Ok(value) => value,
            Err(failure) => return openmaic_slide_error(failure),
        };
    let normalize = match runtime
        .executor
        .openmaic_slide_with_generation(
            OpenMaicSlideStage::Normalize,
            generation,
            normalize_request,
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "slide_normalize",
                "OpenMAIC slide normalize worker unavailable",
                Value::Null,
            );
        }
    };
    let normalize_outcome = openmaic_stage_outcome(&normalize);
    let normalized_scene =
        match openmaic_slide::openmaic_slide_normalized_scene(&normalize["document"]) {
            Ok(Some(value)) => value,
            Ok(None) => {
                return openmaic_stage_failure(
                    StatusCode::UNPROCESSABLE_ENTITY,
                    "slide_normalize",
                    "the donor normalize adapter did not admit the scene",
                    normalize_outcome,
                );
            }
            Err(_) => {
                return openmaic_stage_failure(
                    StatusCode::BAD_GATEWAY,
                    "slide_normalize",
                    "OpenMAIC slide normalize receipt is inconsistent",
                    normalize_outcome,
                );
            }
        };
    // Stage 5: the donor's slide-action prompt over the normalized elements.
    // Best effort by design: a refused narration leaves the slide complete with
    // an empty action list, and the stage record names exactly what happened.
    let element_ids = openmaic_slide::openmaic_slide_element_ids(&normalized_scene);
    let actions_request = match openmaic_slide_actions::openmaic_slide_actions_capture_request(
        &create_request_id,
        &selection,
        &normalized_scene,
    ) {
        Ok(value) => value,
        Err(failure) => return openmaic_slide_error(failure),
    };
    let actions_capture = match runtime
        .executor
        .openmaic_slide_actions_with_generation(
            generation,
            actions_request,
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "slide_actions",
                "OpenMAIC slide-action worker unavailable",
                Value::Null,
            );
        }
    };
    let actions_outcome = openmaic_stage_outcome(&actions_capture);
    let empty_actions = json!({"actions":[]});
    let (actions, actions_stage) = if actions_capture["exit_code"] == 0
        && actions_capture["document"]["status"] == "PROMPT_CAPTURED"
    {
        let binding = match openmaic_slide_actions::openmaic_slide_actions_capture_binding(
            &create_request_id,
            &actions_capture["document"],
        ) {
            Ok(value) => value,
            Err(_) => {
                return openmaic_stage_failure(
                    StatusCode::BAD_GATEWAY,
                    "slide_actions",
                    "OpenMAIC slide-action prompt receipt is inconsistent",
                    actions_outcome,
                );
            }
        };
        let actions_model_request =
            openmaic_outline::openmaic_outline_model_request(&binding, &request["model"]);
        let actions_model = runtime
            .executor
            .derived_json(
                openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
                actions_model_request,
                Duration::from_secs(120),
            )
            .await;
        match actions_model {
            Err(reason) => (
                empty_actions.clone(),
                openmaic_slide_actions::openmaic_slide_actions_stage(
                    "MODEL_UNAVAILABLE",
                    &json!(reason),
                    Some(&binding),
                    None,
                    0,
                    false,
                ),
            ),
            Ok(actions_model) => {
                let content = if actions_model["exit_code"] == 0
                    && actions_model["document"]["status"] == "REPLY"
                {
                    openmaic_outline::openmaic_outline_new_model_content(&actions_model["document"])
                        .map(str::to_owned)
                } else {
                    None
                };
                match content {
                    None => {
                        let (status, reason) = openmaic_unusable_model_outcome(&actions_model);
                        (
                            empty_actions.clone(),
                            openmaic_slide_actions::openmaic_slide_actions_stage(
                                &status,
                                &reason,
                                Some(&binding),
                                None,
                                0,
                                true,
                            ),
                        )
                    }
                    Some(content) => {
                        let actions_replay_request =
                            match openmaic_slide_actions::openmaic_slide_actions_replay_request(
                                &create_request_id,
                                &selection,
                                &normalized_scene,
                                &binding,
                                &content,
                            ) {
                                Ok(value) => value,
                                Err(failure) => return openmaic_slide_error(failure),
                            };
                        let actions_replay = match runtime
                            .executor
                            .openmaic_slide_actions_with_generation(
                                generation,
                                actions_replay_request,
                                Duration::from_secs(30),
                            )
                            .await
                        {
                            Ok(value) => value,
                            Err(_) => {
                                return openmaic_stage_failure(
                                    StatusCode::SERVICE_UNAVAILABLE,
                                    "slide_actions",
                                    "OpenMAIC slide-action replay worker unavailable",
                                    Value::Null,
                                );
                            }
                        };
                        match openmaic_slide_actions::openmaic_slide_actions_candidate(
                            &actions_replay["document"],
                            &element_ids,
                        ) {
                            Ok(Some(admitted)) => {
                                let count = admitted["actions"].as_array().map_or(0, Vec::len);
                                (
                                    admitted,
                                    openmaic_slide_actions::openmaic_slide_actions_stage(
                                        "CANDIDATE",
                                        &Value::Null,
                                        Some(&binding),
                                        Some(&actions_replay["document"]),
                                        count,
                                        true,
                                    ),
                                )
                            }
                            Ok(None) => {
                                let status = actions_replay["document"]["status"]
                                    .as_str()
                                    .unwrap_or("NOT_ADMITTED")
                                    .to_owned();
                                let reason = actions_replay["document"]["reason"].clone();
                                (
                                    empty_actions.clone(),
                                    openmaic_slide_actions::openmaic_slide_actions_stage(
                                        &status,
                                        &reason,
                                        Some(&binding),
                                        Some(&actions_replay["document"]),
                                        0,
                                        true,
                                    ),
                                )
                            }
                            Err(_) => (
                                empty_actions.clone(),
                                openmaic_slide_actions::openmaic_slide_actions_stage(
                                    "RECEIPT_INVALID",
                                    &json!("SLIDE_ACTIONS_REPLAY_RECEIPT_INVALID"),
                                    Some(&binding),
                                    None,
                                    0,
                                    true,
                                ),
                            ),
                        }
                    }
                }
            }
        }
    } else {
        let status = actions_capture["document"]["status"]
            .as_str()
            .unwrap_or("NOT_ADMITTED")
            .to_owned();
        let reason = actions_capture["document"]["reason"].clone();
        (
            empty_actions.clone(),
            openmaic_slide_actions::openmaic_slide_actions_stage(
                &status, &reason, None, None, 0, false,
            ),
        )
    };
    // Stage 6: the existing scene builder and the existing v2 candidate writer.
    let scene_request = match openmaic_slide::openmaic_slide_scene_build_request_with_actions(
        &create_request_id,
        &selection,
        &normalized_scene,
        &request["source"],
        &actions,
    ) {
        Ok(value) => value,
        Err(failure) => return openmaic_slide_error(failure),
    };
    let scene_prepare_id = create_request_id.clone();
    let scene_prepare_request = scene_request.clone();
    let scene_prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            course::prepare_openmaic_scene(conn, &scene_prepare_id, &scene_prepare_request)
        })
        .await
    {
        Ok(Ok(value)) => value,
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return error(
                StatusCode::NOT_FOUND,
                "OpenMAIC source document is unavailable",
            );
        }
        Ok(Err(_)) => {
            return error(
                StatusCode::CONFLICT,
                "OpenMAIC slide request or source snapshot is invalid or changed",
            );
        }
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC scene preparation failed",
            );
        }
    };
    let scene_pending = match scene_prepared {
        course::OpenMaicPreparation::Existing(_) => {
            return error(
                StatusCode::CONFLICT,
                "this create request ID already owns a scene candidate without the outline-slide record",
            );
        }
        course::OpenMaicPreparation::Pending(pending) => pending,
    };
    let scene_build = match runtime
        .executor
        .openmaic_scene_with_generation(generation, scene_request.clone(), Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "scene_build",
                "OpenMAIC scene builder unavailable",
                Value::Null,
            );
        }
    };
    let scene_outcome = openmaic_stage_outcome(&scene_build);
    if scene_build["exit_code"] != 0 || scene_build["document"]["status"] != "CANDIDATE" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "scene_build",
            "OpenMAIC scene builder did not produce a candidate",
            scene_outcome,
        );
    }
    let record = openmaic_slide::openmaic_slide_record_with_actions(
        &create_request_id,
        &openmaic_slide::openmaic_slide_request_sha256(&request, &selection),
        &selection,
        &openmaic_slide::openmaic_slide_prompt_record(&binding),
        &model["document"],
        &reply["document"],
        &normalize["document"],
        &actions_stage,
    );
    let generation_chain = openmaic_slide::OpenMaicSlideGeneration {
        scene_request: scene_request.clone(),
        record,
    };
    let commit_id = create_request_id.clone();
    let commit_request = request.clone();
    let worker_document = scene_build["document"].clone();
    let committed = runtime
        .executor
        .commit_openmaic_if_current(generation, move |conn| {
            openmaic_slide::commit_openmaic_slide_candidate(
                conn,
                &commit_id,
                &commit_request,
                &pending,
                &scene_pending,
                &worker_document,
                &generation_chain,
            )
        })
        .await;
    match committed {
        Ok(Ok(receipt)) => openmaic_slide_receipt_response(&receipt, true),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => error(
            StatusCode::CONFLICT,
            "OpenMAIC slide request, capability or workspace changed",
        ),
        Ok(Err(_)) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC slide candidate persistence failed",
        ),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC slide capability unavailable or withdrawn",
        ),
    }
}

/// Outline-to-quiz generation: capture the donor quiz prompt, call the declared
/// local model, replay the model text through the same donor adapter, then build
/// the scene through the existing fixed builder. Only an admitted replay
/// candidate is persisted; no failure writes a partial candidate.
async fn openmaic_quiz_chain(
    runtime: Runtime,
    create_request_id: String,
    request: Value,
    selection: Value,
    admission: Result<u64, String>,
) -> Response {
    let prepare_id = create_request_id.clone();
    let prepare_request = request.clone();
    let prepare_selection = selection.clone();
    let prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            openmaic_quiz::prepare_openmaic_quiz_candidate(
                conn,
                &prepare_id,
                &prepare_request,
                &prepare_selection,
            )
        })
        .await
    {
        Ok(Ok(value)) => value,
        Ok(Err(failure)) => return openmaic_quiz_error(failure),
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC quiz preparation failed",
            );
        }
    };
    let pending = match prepared {
        openmaic_quiz::OpenMaicQuizPreparation::Existing(receipt) => {
            // A repeated request reads the stored candidate; no prompt, model or
            // worker runs again.
            return openmaic_quiz_receipt_response(&receipt, false);
        }
        openmaic_quiz::OpenMaicQuizPreparation::Pending(pending) => pending,
    };
    if let Some(stage) = openmaic_quiz_script_gap(&runtime) {
        return openmaic_stage_failure(
            StatusCode::SERVICE_UNAVAILABLE,
            stage,
            "OpenMAIC quiz chain unavailable: a fixed sibling script is missing",
            Value::Null,
        );
    }
    let generation = match admission {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC provider unavailable or disabled",
            );
        }
    };
    // Stage 1: the donor quiz prompt capture. It carries no reply, so the worker
    // can only produce the prompt binding.
    let capture_request =
        match openmaic_quiz::openmaic_quiz_capture_request(&create_request_id, &selection) {
            Ok(value) => value,
            Err(failure) => return openmaic_quiz_error(failure),
        };
    let capture = match runtime
        .executor
        .openmaic_quiz_with_generation(generation, capture_request, Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "quiz_capture",
                "OpenMAIC quiz prompt worker unavailable",
                Value::Null,
            );
        }
    };
    let capture_outcome = openmaic_stage_outcome(&capture);
    if capture["exit_code"] != 0 || capture["document"]["status"] != "PROMPT_CAPTURED" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "quiz_capture",
            "OpenMAIC quiz prompt did not produce a binding",
            capture_outcome,
        );
    }
    let binding = match openmaic_quiz::openmaic_quiz_capture_binding(
        &create_request_id,
        &capture["document"],
    ) {
        Ok(value) => value,
        Err(archeaxis_domain::document::Error::Invalid(reason)) => {
            let mut outcome = capture_outcome.clone();
            outcome["receipt_refusal"] = json!(reason);
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "quiz_capture",
                "OpenMAIC quiz prompt receipt is inconsistent",
                outcome,
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "quiz_capture",
                "OpenMAIC quiz prompt receipt is inconsistent",
                capture_outcome,
            );
        }
    };
    // Stage 2: the declared local model, through the same capability and worker
    // as the outline route.
    let model_request =
        openmaic_outline::openmaic_outline_model_request(&binding, &request["model"]);
    let model = match runtime
        .executor
        .derived_json(
            openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
            model_request,
            Duration::from_secs(120),
        )
        .await
    {
        Ok(value) => value,
        Err(reason) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "local_model",
                &format!("local model capability unavailable: {reason}"),
                Value::Null,
            );
        }
    };
    let model_outcome = openmaic_stage_outcome(&model);
    if model["exit_code"] != 0 || model["document"]["status"] != "REPLY" {
        let named = model["document"]["status"].as_str().unwrap_or("");
        let status = match named {
            "INVALID_MODEL_OUTPUT" | "MODEL_REJECTED" => StatusCode::UNPROCESSABLE_ENTITY,
            "MODEL_TIMEOUT" | "NO_FINAL_ANSWER" => StatusCode::GATEWAY_TIMEOUT,
            _ => StatusCode::SERVICE_UNAVAILABLE,
        };
        return openmaic_stage_failure(
            status,
            "local_model",
            "the local model did not produce a usable quiz reply",
            model_outcome,
        );
    }
    let Some(content) =
        openmaic_outline::openmaic_outline_new_model_content(&model["document"]).map(str::to_owned)
    else {
        return openmaic_stage_failure(
            StatusCode::BAD_GATEWAY,
            "local_model",
            "local model receipt is inconsistent",
            model_outcome,
        );
    };
    // Stage 3: the donor quiz adapter. A quarantined, repaired-but-unsupported or
    // otherwise non-candidate reply keeps the worker's own status and reason.
    let replay_request = match openmaic_quiz::openmaic_quiz_replay_request(
        &create_request_id,
        &selection,
        &binding,
        &content,
    ) {
        Ok(value) => value,
        Err(archeaxis_domain::document::Error::Invalid(reason)) => {
            return openmaic_stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "quiz_replay",
                "the local model reply exceeds the donor reply budget",
                json!({"status":"MODEL_REPLY_EXCEEDS_BOUND","reason":reason,
                    "exit_code":model["exit_code"]}),
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "quiz_replay",
                "the local model reply cannot be replayed",
                model_outcome,
            );
        }
    };
    let replay = match runtime
        .executor
        .openmaic_quiz_with_generation(generation, replay_request, Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "quiz_replay",
                "OpenMAIC quiz replay worker unavailable",
                Value::Null,
            );
        }
    };
    let replay_outcome = openmaic_stage_outcome(&replay);
    let questions = match openmaic_quiz::openmaic_quiz_replay_candidate(&replay["document"]) {
        Ok(Some(value)) => value,
        Ok(None) => {
            return openmaic_stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "quiz_replay",
                "the donor quiz adapter did not admit the model reply",
                replay_outcome,
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "quiz_replay",
                "OpenMAIC quiz replay receipt is inconsistent",
                replay_outcome,
            );
        }
    };
    // Stage 4: the donor's quiz-action prompt. This narration stage is best
    // effort by design: a refused or unusable reply leaves the quiz candidate
    // complete with an empty action list, and the stored stage record names
    // exactly what happened so the omission is never silent.
    let actions_request = match openmaic_quiz_actions::openmaic_quiz_actions_capture_request(
        &create_request_id,
        &selection,
        &questions,
    ) {
        Ok(value) => value,
        Err(failure) => return openmaic_quiz_error(failure),
    };
    let actions_capture = match runtime
        .executor
        .openmaic_quiz_actions_with_generation(generation, actions_request, Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "quiz_actions",
                "OpenMAIC quiz-action worker unavailable",
                Value::Null,
            );
        }
    };
    let actions_outcome = openmaic_stage_outcome(&actions_capture);
    let empty_actions = json!({"actions":[]});
    let (actions, actions_stage) = if actions_capture["exit_code"] == 0
        && actions_capture["document"]["status"] == "PROMPT_CAPTURED"
    {
        let binding = match openmaic_quiz_actions::openmaic_quiz_actions_capture_binding(
            &create_request_id,
            &actions_capture["document"],
        ) {
            Ok(value) => value,
            Err(_) => {
                return openmaic_stage_failure(
                    StatusCode::BAD_GATEWAY,
                    "quiz_actions",
                    "OpenMAIC quiz-action prompt receipt is inconsistent",
                    actions_outcome,
                );
            }
        };
        let actions_model_request =
            openmaic_outline::openmaic_outline_model_request(&binding, &request["model"]);
        let actions_model = runtime
            .executor
            .derived_json(
                openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
                actions_model_request,
                Duration::from_secs(120),
            )
            .await;
        match actions_model {
            Err(reason) => (
                empty_actions.clone(),
                openmaic_quiz_actions::openmaic_quiz_actions_stage(
                    "MODEL_UNAVAILABLE",
                    &json!(reason),
                    Some(&binding),
                    None,
                    0,
                    false,
                ),
            ),
            Ok(actions_model) => {
                let content = if actions_model["exit_code"] == 0
                    && actions_model["document"]["status"] == "REPLY"
                {
                    openmaic_outline::openmaic_outline_new_model_content(&actions_model["document"])
                        .map(str::to_owned)
                } else {
                    None
                };
                match content {
                    None => {
                        let (status, reason) = openmaic_unusable_model_outcome(&actions_model);
                        (
                            empty_actions.clone(),
                            openmaic_quiz_actions::openmaic_quiz_actions_stage(
                                &status,
                                &reason,
                                Some(&binding),
                                None,
                                0,
                                true,
                            ),
                        )
                    }
                    Some(content) => {
                        let actions_replay_request =
                            match openmaic_quiz_actions::openmaic_quiz_actions_replay_request(
                                &create_request_id,
                                &selection,
                                &questions,
                                &binding,
                                &content,
                            ) {
                                Ok(value) => value,
                                Err(failure) => return openmaic_quiz_error(failure),
                            };
                        let actions_replay = match runtime
                            .executor
                            .openmaic_quiz_actions_with_generation(
                                generation,
                                actions_replay_request,
                                Duration::from_secs(30),
                            )
                            .await
                        {
                            Ok(value) => value,
                            Err(_) => {
                                return openmaic_stage_failure(
                                    StatusCode::SERVICE_UNAVAILABLE,
                                    "quiz_actions",
                                    "OpenMAIC quiz-action replay worker unavailable",
                                    Value::Null,
                                );
                            }
                        };
                        match openmaic_quiz_actions::openmaic_quiz_actions_candidate(
                            &actions_replay["document"],
                        ) {
                            Ok(Some(admitted)) => {
                                let count = admitted["actions"].as_array().map_or(0, Vec::len);
                                (
                                    admitted,
                                    openmaic_quiz_actions::openmaic_quiz_actions_stage(
                                        "CANDIDATE",
                                        &Value::Null,
                                        Some(&binding),
                                        Some(&actions_replay["document"]),
                                        count,
                                        true,
                                    ),
                                )
                            }
                            Ok(None) => {
                                let status = actions_replay["document"]["status"]
                                    .as_str()
                                    .unwrap_or("NOT_ADMITTED")
                                    .to_owned();
                                let reason = actions_replay["document"]["reason"].clone();
                                (
                                    empty_actions.clone(),
                                    openmaic_quiz_actions::openmaic_quiz_actions_stage(
                                        &status,
                                        &reason,
                                        Some(&binding),
                                        Some(&actions_replay["document"]),
                                        0,
                                        true,
                                    ),
                                )
                            }
                            Err(_) => (
                                empty_actions.clone(),
                                openmaic_quiz_actions::openmaic_quiz_actions_stage(
                                    "RECEIPT_INVALID",
                                    &json!("QUIZ_ACTIONS_REPLAY_RECEIPT_INVALID"),
                                    Some(&binding),
                                    None,
                                    0,
                                    true,
                                ),
                            ),
                        }
                    }
                }
            }
        }
    } else {
        let status = actions_capture["document"]["status"]
            .as_str()
            .unwrap_or("NOT_ADMITTED")
            .to_owned();
        let reason = actions_capture["document"]["reason"].clone();
        (
            empty_actions.clone(),
            openmaic_quiz_actions::openmaic_quiz_actions_stage(
                &status, &reason, None, None, 0, false,
            ),
        )
    };
    // Stage 5: the existing scene builder and the existing v2 candidate writer.
    let scene_request = match openmaic_quiz::openmaic_quiz_scene_build_request_with_actions(
        &create_request_id,
        &selection,
        &questions,
        &request["source"],
        &actions,
    ) {
        Ok(value) => value,
        Err(failure) => return openmaic_quiz_error(failure),
    };
    let scene_prepare_id = create_request_id.clone();
    let scene_prepare_request = scene_request.clone();
    let scene_prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            course::prepare_openmaic_scene(conn, &scene_prepare_id, &scene_prepare_request)
        })
        .await
    {
        Ok(Ok(value)) => value,
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return error(
                StatusCode::NOT_FOUND,
                "OpenMAIC source document is unavailable",
            );
        }
        Ok(Err(_)) => {
            return error(
                StatusCode::CONFLICT,
                "OpenMAIC quiz request or source snapshot is invalid or changed",
            );
        }
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC scene preparation failed",
            );
        }
    };
    let scene_pending = match scene_prepared {
        course::OpenMaicPreparation::Existing(_) => {
            return error(
                StatusCode::CONFLICT,
                "this create request ID already owns a scene candidate without the outline-quiz record",
            );
        }
        course::OpenMaicPreparation::Pending(pending) => pending,
    };
    let scene_build = match runtime
        .executor
        .openmaic_scene_with_generation(generation, scene_request.clone(), Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "scene_build",
                "OpenMAIC scene builder unavailable",
                Value::Null,
            );
        }
    };
    let scene_outcome = openmaic_stage_outcome(&scene_build);
    if scene_build["exit_code"] != 0 || scene_build["document"]["status"] != "CANDIDATE" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "scene_build",
            "OpenMAIC scene builder did not produce a candidate",
            scene_outcome,
        );
    }
    let record = openmaic_quiz::openmaic_quiz_record_with_actions(
        &create_request_id,
        &openmaic_slide::openmaic_slide_request_sha256(&request, &selection),
        &selection,
        &openmaic_quiz::openmaic_quiz_prompt_record(&binding),
        &model["document"],
        &replay["document"],
        &actions_stage,
    );
    let generation_chain = openmaic_quiz::OpenMaicQuizGeneration {
        scene_request: scene_request.clone(),
        record,
    };
    let commit_id = create_request_id.clone();
    let commit_request = request.clone();
    let worker_document = scene_build["document"].clone();
    let committed = runtime
        .executor
        .commit_openmaic_if_current(generation, move |conn| {
            openmaic_quiz::commit_openmaic_quiz_candidate(
                conn,
                &commit_id,
                &commit_request,
                &pending,
                &scene_pending,
                &worker_document,
                &generation_chain,
            )
        })
        .await;
    match committed {
        Ok(Ok(receipt)) => openmaic_quiz_receipt_response(&receipt, true),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => error(
            StatusCode::CONFLICT,
            "OpenMAIC quiz request, capability or workspace changed",
        ),
        Ok(Err(_)) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC quiz candidate persistence failed",
        ),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC quiz capability unavailable or withdrawn",
        ),
    }
}

/// The interactive chain needs its prompt and normalize adapters plus the
/// existing scene builder. A missing adapter names that stage instead of dropping
/// it silently.
fn openmaic_interactive_script_gap(runtime: &Runtime) -> Option<&'static str> {
    for (stage, label) in [
        (OpenMaicInteractiveStage::Prompt, "interactive_prompt"),
        (OpenMaicInteractiveStage::Normalize, "interactive_normalize"),
    ] {
        if runtime
            .executor
            .openmaic_interactive_script(stage)
            .is_none()
        {
            return Some(label);
        }
    }
    if runtime.executor.openmaic_node_paths().is_none() {
        return Some("scene_build");
    }
    None
}

/// Outline-to-interactive generation: capture the donor widget prompt, call the
/// declared local model, extract and post-process the model HTML through the
/// interactive normalize adapter, then build the scene through the existing fixed
/// builder. Only an admitted normalize result is persisted; the HTML is never
/// executed, sanitized into trusted content or authorized for rendering here.
async fn openmaic_interactive_chain(
    runtime: Runtime,
    create_request_id: String,
    request: Value,
    selection: Value,
    admission: Result<u64, String>,
) -> Response {
    // The shared outline-scene body is versioned per route; this chain's own
    // schema is what its refusal, preparation and record identity check.
    let mut request = request;
    request["schema"] = json!(openmaic_interactive::OPENMAIC_INTERACTIVE_REQUEST_SCHEMA);
    let (widget, _) = match openmaic_interactive::openmaic_interactive_widget(&selection) {
        Ok(value) => value,
        Err(failure) => return openmaic_interactive_error(failure),
    };
    let prepare_id = create_request_id.clone();
    let prepare_request = request.clone();
    let prepare_selection = selection.clone();
    let prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            openmaic_interactive::prepare_openmaic_interactive_candidate(
                conn,
                &prepare_id,
                &prepare_request,
                &prepare_selection,
            )
        })
        .await
    {
        Ok(Ok(value)) => value,
        Ok(Err(failure)) => return openmaic_interactive_error(failure),
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC interactive preparation failed",
            );
        }
    };
    let pending = match prepared {
        openmaic_interactive::OpenMaicInteractivePreparation::Existing(receipt) => {
            // A repeated request reads the stored candidate; no prompt, model or
            // worker runs again.
            return openmaic_interactive_receipt_response(&receipt, false);
        }
        openmaic_interactive::OpenMaicInteractivePreparation::Pending(pending) => pending,
    };
    if let Some(stage) = openmaic_interactive_script_gap(&runtime) {
        return openmaic_stage_failure(
            StatusCode::SERVICE_UNAVAILABLE,
            stage,
            "OpenMAIC interactive chain unavailable: a fixed sibling script is missing",
            Value::Null,
        );
    }
    let generation = match admission {
        Ok(value) => value,
        Err(_) => {
            return error(
                StatusCode::SERVICE_UNAVAILABLE,
                "OpenMAIC provider unavailable or disabled",
            );
        }
    };
    // Stage 1: the donor widget prompt. It carries no reply, so the worker can
    // only produce the prompt binding.
    let prompt_request = match openmaic_interactive::openmaic_interactive_prompt_request(&selection)
    {
        Ok(value) => value,
        Err(failure) => return openmaic_interactive_error(failure),
    };
    let prompt = match runtime
        .executor
        .openmaic_interactive_with_generation(
            OpenMaicInteractiveStage::Prompt,
            generation,
            prompt_request,
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "interactive_prompt",
                "OpenMAIC interactive prompt worker unavailable",
                Value::Null,
            );
        }
    };
    let prompt_outcome = openmaic_stage_outcome(&prompt);
    if prompt["exit_code"] != 0 || prompt["document"]["status"] != "BUILT" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "interactive_prompt",
            "OpenMAIC interactive prompt did not build the donor prompts",
            prompt_outcome,
        );
    }
    let binding = match openmaic_interactive::openmaic_interactive_prompt_binding(
        &prompt["document"],
        &widget,
    ) {
        Ok(value) => value,
        Err(archeaxis_domain::document::Error::Invalid(reason)) => {
            let mut outcome = prompt_outcome.clone();
            outcome["receipt_refusal"] = json!(reason);
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "interactive_prompt",
                "OpenMAIC interactive prompt receipt is inconsistent",
                outcome,
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "interactive_prompt",
                "OpenMAIC interactive prompt receipt is inconsistent",
                prompt_outcome,
            );
        }
    };
    // Stage 2: the declared local model, through the same capability and worker
    // as the outline route. An unregistered or disabled capability is named.
    let model_request =
        openmaic_interactive::openmaic_interactive_model_request(&binding, &request["model"]);
    let model = match runtime
        .executor
        .derived_json(
            openmaic_outline::OPENMAIC_OUTLINE_MODEL_CAPABILITY,
            model_request,
            Duration::from_secs(120),
        )
        .await
    {
        Ok(value) => value,
        Err(reason) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "local_model",
                &format!("local model capability unavailable: {reason}"),
                Value::Null,
            );
        }
    };
    let model_outcome = openmaic_stage_outcome(&model);
    if model["exit_code"] != 0 || model["document"]["status"] != "REPLY" {
        let named = model["document"]["status"].as_str().unwrap_or("");
        let status = match named {
            "INVALID_MODEL_OUTPUT" | "MODEL_REJECTED" => StatusCode::UNPROCESSABLE_ENTITY,
            "MODEL_TIMEOUT" | "NO_FINAL_ANSWER" => StatusCode::GATEWAY_TIMEOUT,
            _ => StatusCode::SERVICE_UNAVAILABLE,
        };
        return openmaic_stage_failure(
            status,
            "local_model",
            "the local model did not produce a usable interactive reply",
            model_outcome,
        );
    }
    let Some(content) =
        openmaic_outline::openmaic_outline_new_model_content(&model["document"]).map(str::to_owned)
    else {
        return openmaic_stage_failure(
            StatusCode::BAD_GATEWAY,
            "local_model",
            "local model receipt is inconsistent",
            model_outcome,
        );
    };
    // Stage 3: the interactive normalize adapter. It extracts one HTML document,
    // compiles (never runs) the classic inline scripts and applies the donor
    // post-processor. A rejected reply keeps the worker's own status and reason.
    let normalize_request_id =
        openmaic_interactive::openmaic_interactive_normalize_request_id(&create_request_id);
    let normalize_request = match openmaic_interactive::openmaic_interactive_normalize_request(
        &create_request_id,
        &widget,
        &content,
    ) {
        Ok(value) => value,
        Err(archeaxis_domain::document::Error::Invalid(reason)) => {
            return openmaic_stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "interactive_normalize",
                "the local model reply exceeds the interactive normalize budget",
                json!({"status":"MODEL_REPLY_EXCEEDS_BOUND","reason":reason,
                    "exit_code":model["exit_code"]}),
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "interactive_normalize",
                "the local model reply cannot be replayed",
                model_outcome,
            );
        }
    };
    let normalize = match runtime
        .executor
        .openmaic_interactive_with_generation(
            OpenMaicInteractiveStage::Normalize,
            generation,
            normalize_request,
            Duration::from_secs(30),
        )
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "interactive_normalize",
                "OpenMAIC interactive normalize worker unavailable",
                Value::Null,
            );
        }
    };
    let normalize_outcome = openmaic_stage_outcome(&normalize);
    let normalized = match openmaic_interactive::openmaic_interactive_normalized(
        &normalize["document"],
        &normalize_request_id,
        &widget,
        &content,
    ) {
        Ok(Some(value)) => value,
        Ok(None) => {
            return openmaic_stage_failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "interactive_normalize",
                "the donor normalize adapter did not admit the model HTML",
                normalize_outcome,
            );
        }
        Err(archeaxis_domain::document::Error::Invalid(reason)) => {
            let mut outcome = normalize_outcome.clone();
            outcome["receipt_refusal"] = json!(reason);
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "interactive_normalize",
                "OpenMAIC interactive normalize receipt is inconsistent",
                outcome,
            );
        }
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::BAD_GATEWAY,
                "interactive_normalize",
                "OpenMAIC interactive normalize receipt is inconsistent",
                normalize_outcome,
            );
        }
    };
    // Stage 4: the existing scene builder and the existing v2 candidate writer.
    let scene_request = match openmaic_interactive::openmaic_interactive_scene_build_request(
        &create_request_id,
        &selection,
        &normalized,
        &request["source"],
    ) {
        Ok(value) => value,
        Err(failure) => return openmaic_interactive_error(failure),
    };
    let scene_prepare_id = create_request_id.clone();
    let scene_prepare_request = scene_request.clone();
    let scene_prepared = match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            course::prepare_openmaic_scene(conn, &scene_prepare_id, &scene_prepare_request)
        })
        .await
    {
        Ok(Ok(value)) => value,
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => {
            return error(
                StatusCode::NOT_FOUND,
                "OpenMAIC source document is unavailable",
            );
        }
        Ok(Err(_)) => {
            return error(
                StatusCode::CONFLICT,
                "OpenMAIC interactive request or source snapshot is invalid or changed",
            );
        }
        _ => {
            return error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "OpenMAIC scene preparation failed",
            );
        }
    };
    let scene_pending = match scene_prepared {
        course::OpenMaicPreparation::Existing(_) => {
            return error(
                StatusCode::CONFLICT,
                "this create request ID already owns a scene candidate without the outline-interactive record",
            );
        }
        course::OpenMaicPreparation::Pending(pending) => pending,
    };
    let scene_build = match runtime
        .executor
        .openmaic_scene_with_generation(generation, scene_request.clone(), Duration::from_secs(30))
        .await
    {
        Ok(value) => value,
        Err(_) => {
            return openmaic_stage_failure(
                StatusCode::SERVICE_UNAVAILABLE,
                "scene_build",
                "OpenMAIC scene builder unavailable",
                Value::Null,
            );
        }
    };
    let scene_outcome = openmaic_stage_outcome(&scene_build);
    if scene_build["exit_code"] != 0 || scene_build["document"]["status"] != "CANDIDATE" {
        return openmaic_stage_failure(
            StatusCode::UNPROCESSABLE_ENTITY,
            "scene_build",
            "OpenMAIC scene builder did not produce a candidate",
            scene_outcome,
        );
    }
    let record = openmaic_interactive::openmaic_interactive_record(
        &create_request_id,
        &openmaic_interactive::openmaic_interactive_request_sha256(&request, &selection),
        &selection,
        &binding,
        &model["document"],
        &normalize["document"],
    );
    let generation_chain = openmaic_interactive::OpenMaicInteractiveGeneration {
        scene_request: scene_request.clone(),
        record,
    };
    let commit_id = create_request_id.clone();
    let commit_request = request.clone();
    let worker_document = scene_build["document"].clone();
    let committed = runtime
        .executor
        .commit_openmaic_if_current(generation, move |conn| {
            openmaic_interactive::commit_openmaic_interactive_candidate(
                conn,
                &commit_id,
                &commit_request,
                &pending,
                &scene_pending,
                &worker_document,
                &generation_chain,
            )
        })
        .await;
    match committed {
        Ok(Ok(receipt)) => openmaic_interactive_receipt_response(&receipt, true),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_)))
        | Ok(Err(archeaxis_domain::document::Error::Conflict(_)))
        | Ok(Err(archeaxis_domain::document::Error::NotFound)) => error(
            StatusCode::CONFLICT,
            "OpenMAIC interactive request, capability or workspace changed",
        ),
        Ok(Err(_)) => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "OpenMAIC interactive candidate persistence failed",
        ),
        Err(_) => error(
            StatusCode::SERVICE_UNAVAILABLE,
            "OpenMAIC interactive capability unavailable or withdrawn",
        ),
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

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct ListQuery {
    cursor: Option<String>,
}

pub(super) async fn list(
    State(runtime): State<Runtime>,
    axum::extract::Query(query): axum::extract::Query<ListQuery>,
) -> Response {
    if query.cursor.as_ref().is_some_and(|id| {
        id.is_empty()
            || id.len() > 256
            || !id
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_')
    }) {
        return error(StatusCode::UNPROCESSABLE_ENTITY, "invalid course cursor");
    }
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| course::list_candidates(conn, query.cursor.as_deref()))
        .await
    {
        Ok(Ok(value)) => (StatusCode::OK, Json(value)).into_response(),
        _ => error(StatusCode::INTERNAL_SERVER_ERROR, "course list read failed"),
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct PackageProjectionBody {
    document_ids: Vec<String>,
}

/// Read-only OpenMAIC course-package projection over persisted scene candidates.
///
/// It reports scene count, type distribution and recorded playability; it parses
/// no course payload, runs no renderer, validates no course and writes nothing.
pub(super) async fn openmaic_package_projection(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<PackageProjectionBody>,
) -> Response {
    // Scene candidates can carry answer keys and material, so this stays human
    // only exactly like the scene creation and read paths.
    if crate::request_actor(&headers) != Ok("human") {
        return error(
            StatusCode::FORBIDDEN,
            "OpenMAIC package projection requires a human actor",
        );
    }
    let document_ids = body.document_ids;
    let projected = runtime
        .executor
        .store()
        .submit_wait(move |conn| course::openmaic_package_projection(conn, &document_ids))
        .await;
    match projected {
        Ok(Ok(value)) => Json(value).into_response(),
        Ok(Err(archeaxis_domain::document::Error::Invalid(_))) => error(
            StatusCode::UNPROCESSABLE_ENTITY,
            "package projection needs 1 to 64 unique bounded document IDs",
        ),
        Ok(Err(archeaxis_domain::document::Error::NotFound)) => error(
            StatusCode::NOT_FOUND,
            "package projection document is unavailable",
        ),
        _ => error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "package projection failed",
        ),
    }
}
