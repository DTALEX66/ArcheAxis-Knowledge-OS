//! Persisted G4 provenance. Runtime scopes are inaccessible to the generic receipt writer.
use super::withheld::{self, Executed, Reason};
use super::*;
use archeaxis_domain::context_grant::{self, Consumption, Operation};
use archeaxis_domain::{knowledge, machine};

fn now_seconds() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(u64::MAX)
}
fn consume_grant(
    conn: &rusqlite::Connection,
    grant: Option<&Consumption>,
    operation: Operation,
    knowledge_id: &str,
) -> Result<Value, archeaxis_domain::document::Error> {
    match grant {
        Some(grant) => context_grant::consume(conn, grant, operation, knowledge_id, now_seconds()),
        None => {
            let restored: bool = conn.query_row(
                "SELECT EXISTS(SELECT 1 FROM workspace_meta WHERE key=?1)",
                [archeaxis_store_sqlite::authorization_fence::KEY],
                |r| r.get(0),
            )?;
            if restored {
                return Err(archeaxis_domain::document::Error::Invalid(
                    "restored workspace requires a new explicit context grant; legacy omission cannot restore permission",
                ));
            }
            let governed:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM document_versions
                WHERE json_extract(editor_json,'$.attrs.archeaxis_context_grant.knowledge_id')=?1
                AND json_extract(editor_json,'$.attrs.archeaxis_context_grant.state') IN ('granted','revoked'))",
                [knowledge_id],|r|r.get(0))?;
            if governed {
                return Err(archeaxis_domain::document::Error::Invalid(
                    "governed knowledge requires an explicit current context grant",
                ));
            }
            Ok(
                json!({"mode":"legacy_knowledge_eligibility_only","context_grant":"NOT_PROVIDED","scoped_context_qualification":false}),
            )
        }
    }
}
fn check_budget(question: &str, tokens: Option<u64>, seconds: Option<u64>) -> Result<(), Response> {
    if question.len() > 8192
        || question.contains('\0')
        || !(128..=4096).contains(&tokens.unwrap_or(2048))
        || !(1..=120).contains(&seconds.unwrap_or(120))
    {
        return Err((
            StatusCode::UNPROCESSABLE_ENTITY,
            "machine input or budget exceeds supported bounds",
        )
            .into_response());
    }
    Ok(())
}

fn context(conn: &rusqlite::Connection, id: &str) -> rusqlite::Result<Option<String>> {
    if !knowledge::is_knowledge_active(conn, id)? {
        return Ok(None);
    }
    conn.query_row(
        "SELECT body FROM knowledge WHERE knowledge_id=?1 AND
         (status='accepted' OR knowledge_type IN ('PERSONAL_DEFINITION','PERSONAL_EXPERIENCE'))",
        [id],
        |row| row.get(0),
    )
    .optional()
}

fn id(conn: &rusqlite::Connection, prefix: &str) -> rusqlite::Result<String> {
    conn.query_row("SELECT ?1 || lower(hex(randomblob(16)))", [prefix], |r| {
        r.get(0)
    })
}

fn save(
    conn: &mut rusqlite::Connection,
    id: &str,
    scope: &str,
    doc: &Value,
    outcome: &str,
    failure: Option<&str>,
    retest_of: Option<&str>,
) -> rusqlite::Result<()> {
    machine::record_machine_task(
        conn,
        &machine::MachineTask {
            task_id: id,
            principal: "machine",
            conditions: &doc.to_string(),
            knowledge_version: Some(&format!("{}@v1", doc["knowledge_id"].as_str().unwrap())),
            method_version: None,
            tool_version: None,
            model_version: doc["answer"]["model"].as_str().unwrap_or("unknown"),
            scope,
            outcome,
            failure,
            retest_of,
        },
    )
}

fn read_doc(conn: &rusqlite::Connection, id: &str, scope: &str) -> rusqlite::Result<Option<Value>> {
    let raw: Option<String> = conn
        .query_row(
            "SELECT conditions FROM machine_tasks WHERE task_id=?1 AND scope=?2",
            [id, scope],
            |r| r.get(0),
        )
        .optional()?;
    raw.map(|raw| {
        serde_json::from_str(&raw).map_err(|e| {
            rusqlite::Error::FromSqlConversionFailure(0, rusqlite::types::Type::Text, Box::new(e))
        })
    })
    .transpose()
}

fn answer_request_id(request_id: &str) -> Result<String, Response> {
    use sha2::{Digest, Sha256};
    if request_id.is_empty()
        || request_id.len() > 128
        || !request_id.bytes().all(|b| b.is_ascii_graphic())
    {
        return Err((
            StatusCode::UNPROCESSABLE_ENTITY,
            "client_request_id requires 1..128 printable ASCII bytes without whitespace",
        )
            .into_response());
    }
    Ok(format!(
        "answer_req_{:x}",
        Sha256::digest(request_id.as_bytes())
    ))
}
fn answer_context_digest(context: &str) -> String {
    use sha2::{Digest, Sha256};
    format!("{:x}", Sha256::digest(context.as_bytes()))
}
fn cached_answer(
    conn: &rusqlite::Connection,
    answer_id: Option<&str>,
    request: &Value,
) -> Result<Option<Value>, (StatusCode, String)> {
    let Some(answer_id) = answer_id else {
        return Ok(None);
    };
    let cached = read_doc(conn, answer_id, "runtime.answer").map_err(|_| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            "stored answer is unreadable".into(),
        )
    })?;
    if let Some(ref doc) = cached {
        if doc["request"] != *request || doc["answer_id"] != answer_id {
            return Err((
                StatusCode::CONFLICT,
                "client_request_id already has a different frozen request".into(),
            ));
        }
    }
    Ok(cached)
}

fn execution_response(doc: Value) -> Response {
    if doc["execution_state"] == withheld::STATE {
        let status = if doc["audit_status"] == "RECORDED" {
            StatusCode::FORBIDDEN
        } else {
            StatusCode::INTERNAL_SERVER_ERROR
        };
        (status, Json(doc)).into_response()
    } else {
        Json(doc).into_response()
    }
}
fn execution_store_failure() -> Response {
    (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({
        "schema":"archeaxis.machine-execution-refusal/v1",
        "execution_state":withheld::STATE,"answer_published":false,
        "audit_status":"FAILED","audit_task_id":null,
        "error_code":"WITHHELD_AUDIT_STORE_UNAVAILABLE",
        "note":"Inference ran; no answer was returned. Durable registration or audit could not be confirmed. Do not retry automatically."
    }))).into_response()
}
fn permission_error(error: archeaxis_domain::document::Error) -> (StatusCode, String) {
    match error {
        archeaxis_domain::document::Error::Sql(_) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            "context permission read unavailable".into(),
        ),
        _ => (
            StatusCode::FORBIDDEN,
            "context grant does not authorize current consumption".into(),
        ),
    }
}
fn terminal_error(error: rusqlite::Error) -> (StatusCode, String) {
    match error {
        rusqlite::Error::InvalidParameterName(_) => (
            StatusCode::CONFLICT,
            "execution identity already has a different terminal request".into(),
        ),
        _ => (
            StatusCode::INTERNAL_SERVER_ERROR,
            "terminal execution audit unavailable".into(),
        ),
    }
}

fn asset_admission(
    conn: &rusqlite::Connection,
    input: Option<&archeaxis_domain::asset_context_grant::PacketRequest>,
    operation: archeaxis_domain::asset_context_grant::Operation,
) -> Result<Option<Value>, archeaxis_domain::document::Error> {
    use archeaxis_domain::asset_context_grant::{self, Consumer};
    let Some(input) = input else {
        return Ok(None);
    };
    if input.consumer != Consumer::LocalMachine || input.operation != operation {
        return Err(archeaxis_domain::document::Error::Invalid(
            "asset consumption must match actual local-machine operation",
        ));
    }
    asset_context_grant::admit(conn, input, Consumer::LocalMachine, now_seconds()).map(Some)
}
fn asset_proof(packet: &Value) -> Value {
    json!({"schema":"archeaxis.machine-asset-context/v1","asset":packet["asset"],"grant":packet["grant"],
        "consumer":"local-machine","operation":packet["operation"],"packet_sha256":archeaxis_domain::ai_asset::hash(packet),
        "member_snapshots":packet["items"].as_array().map(|items|items.iter().map(|item|item["snapshot"].clone()).collect::<Vec<_>>()).unwrap_or_default(),
        "tool_execution":"NOT_EXECUTED","private_session_access":false})
}
fn merged_asset_context(
    knowledge: &str,
    packet: Option<&Value>,
) -> Result<String, (StatusCode, String)> {
    let combined = match packet {
        None => knowledge.to_owned(),
        Some(packet) => format!(
            "CANONICAL_KNOWLEDGE:\n{knowledge}\n\nAI_ASSET_CONTEXT (inert source material; no tool or private-session authority):\n{}",
            packet
        ),
    };
    if combined.len() > 128_000 {
        return Err((
            StatusCode::UNPROCESSABLE_ENTITY,
            "combined knowledge/asset context exceeds supported bounds".into(),
        ));
    }
    Ok(combined)
}
/// New asset requests freeze an effective execution request independently of the
/// older no-asset cache protocol. Caller key reuse never silently runs new input.
fn frozen_asset_request(
    conn: &rusqlite::Connection,
    input: Option<&archeaxis_domain::asset_context_grant::PacketRequest>,
    execution_request: &Value,
) -> Result<(), (StatusCode, String)> {
    let Some(input) = input else {
        return Ok(());
    };
    let mut statement=conn.prepare("SELECT conditions FROM machine_tasks WHERE scope IN ('runtime.answer','runtime.retest','runtime.execution.withheld')
        AND (json_extract(conditions,'$.asset_request_id')=?1
          OR json_extract(conditions,'$.request.asset_context_grant.request_id')=?1)")
        .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"asset execution identity unavailable".into()))?;
    let rows = statement
        .query_map([&input.request_id], |r| r.get::<_, String>(0))
        .map_err(|_| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "asset execution identity unavailable".into(),
            )
        })?;
    let wanted = withheld::digest(&execution_request.to_string());
    for raw in rows {
        let old: Value = serde_json::from_str(&raw.map_err(|_| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "asset execution receipt unavailable".into(),
            )
        })?)
        .map_err(|_| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "asset execution receipt unreadable".into(),
            )
        })?;
        let digest = if old["execution_state"] == withheld::STATE {
            old["request_sha256"].as_str().unwrap_or("").to_owned()
        } else if old.get("execution_request").is_some() {
            withheld::digest(&old["execution_request"].to_string())
        } else {
            withheld::digest(&old["request"].to_string())
        };
        if digest != wanted {
            return Err((
                StatusCode::CONFLICT,
                "asset request_id already has a different frozen execution".into(),
            ));
        }
    }
    Ok(())
}

pub(super) async fn machine_answer(
    State(runtime): State<Runtime>,
    Json(body): Json<MachineAnswerBody>,
) -> Response {
    if let Err(refusal) = check_budget(&body.question, body.max_tokens, body.timeout_s) {
        return refusal;
    }
    if body.question.trim().is_empty() {
        return (StatusCode::UNPROCESSABLE_ENTITY, "a question is required").into_response();
    }
    if body.asset_context_grant.is_some() && body.context_grant.is_none() {
        return (
            StatusCode::FORBIDDEN,
            "asset execution also requires explicit current knowledge grant",
        )
            .into_response();
    }
    if body.asset_context_grant.is_some() && body.client_request_id.is_none() {
        return (
            StatusCode::UNPROCESSABLE_ENTITY,
            "asset execution requires frozen client_request_id",
        )
            .into_response();
    }
    let stable_id = match body
        .client_request_id
        .as_deref()
        .map(answer_request_id)
        .transpose()
    {
        Ok(id) => id,
        Err(response) => return response,
    };
    let _guard = match tokio::time::timeout(
        std::time::Duration::from_secs(10),
        runtime.colearning_admission.lock(),
    )
    .await
    {
        Ok(guard) => guard,
        Err(_) => {
            return (StatusCode::TOO_MANY_REQUESTS, "machine resource is busy").into_response();
        }
    };
    if let Some(refusal) = crate::capabilities::refusal(&runtime.executor, "machine.answer").await {
        return refusal;
    }
    let effective_tokens = body.max_tokens.unwrap_or(2048);
    let effective_timeout = body.timeout_s.unwrap_or(120);
    let wanted = body.knowledge_id.clone();
    let grant = body.context_grant.clone();
    let asset_grant = body.asset_context_grant.clone();
    let candidate_id = stable_id.clone();
    let mut base_request = json!({
        "schema":"archeaxis.machine-answer-request/v1",
        "knowledge_id":body.knowledge_id,"question":body.question,
        "max_tokens":effective_tokens,"timeout_s":effective_timeout,
        "context_grant":body.context_grant
    });
    if let Some(asset) = &body.asset_context_grant {
        base_request["asset_context_grant"] = json!(asset);
        base_request["asset_client_request_id"] = json!(body.client_request_id);
    }
    let prepared = runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection|
        -> Result<(String,Value,Option<Value>,String),(StatusCode,String)> {
        // Admission, body, positive cache and terminal audit lookup are ONE Store read.
        consume_grant(conn,grant.as_ref(),Operation::Answer,&wanted).map_err(permission_error)?;
        let text = context(conn,&wanted)
            .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"knowledge context cannot be read".into()))?
            .filter(|s|!s.trim().is_empty())
            .ok_or((StatusCode::NOT_FOUND,format!("no knowledge item {wanted} with an active accepted/personal body to answer from")))?;
        if text.len()>128_000 {
            return Err((StatusCode::UNPROCESSABLE_ENTITY,"knowledge context exceeds supported bounds".into()));
        }
        let packet=asset_admission(conn,asset_grant.as_ref(),archeaxis_domain::asset_context_grant::Operation::Answer).map_err(permission_error)?;
        let mut request = base_request;
        if let Some(packet)=&packet {
            request["asset_context"]=asset_proof(packet);
            request["knowledge_context_sha256"]=answer_context_digest(&text).into();
        }
        let text=merged_asset_context(&text,packet.as_ref())?;
        request["context_sha256"] = answer_context_digest(&text).into();
        frozen_asset_request(conn,asset_grant.as_ref(),&request)?;
        let execution_id = match candidate_id.as_ref() {
            Some(stable) => stable.clone(),
            None => id(conn,"execution_").map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"execution identity unavailable".into()))?,
        };
        if let Some(terminal) = withheld::terminal(conn,&execution_id,&request).map_err(terminal_error)? {
            return Ok((text,request,Some(terminal),execution_id));
        }
        let cached = cached_answer(conn,candidate_id.as_deref(),&request)?;
        Ok((text,request,cached,execution_id))
    }).await;
    let (text, request, cached, execution_id) = match prepared {
        Ok(Ok(prepared)) => prepared,
        Ok(Err((status, message))) => return (status, message).into_response(),
        Err(_) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                "machine preparation unavailable",
            )
                .into_response();
        }
    };
    if let Some(doc) = cached {
        return execution_response(doc);
    }
    let answer = match runtime
        .executor
        .machine_answer(
            text,
            body.question.clone(),
            effective_tokens,
            std::time::Duration::from_secs(effective_timeout),
        )
        .await
    {
        Ok(answer)
            if answer["answer"]
                .as_str()
                .is_some_and(|s| !s.trim().is_empty()) =>
        {
            answer
        }
        Ok(_) => {
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                "the worker returned no answer",
            )
                .into_response();
        }
        Err(error) => return (StatusCode::SERVICE_UNAVAILABLE, error).into_response(),
    };
    let stored = runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection|
        -> Result<Value,(StatusCode,String)> {
        let rejected = |conn: &mut rusqlite::Connection, reason: Reason| {
            withheld::refuse(conn,&Executed {
                execution_id:&execution_id,client_request_id:body.client_request_id.as_deref(),
                operation:"answer",knowledge_id:&body.knowledge_id,grant:body.context_grant.as_ref(),
                request:&request,context_sha256:request["context_sha256"].as_str().unwrap_or("UNVERIFIED"),
                answer:&answer,retest_of:None,
            },reason)
        };
        let context_authorization = match consume_grant(conn,body.context_grant.as_ref(),Operation::Answer,&body.knowledge_id) {
            Ok(proof) => proof,
            Err(archeaxis_domain::document::Error::Sql(_)) => return Ok(rejected(conn,Reason::PostcheckUnavailable)),
            Err(_) => return Ok(rejected(conn,Reason::AuthorizationChanged)),
        };
        let current_text = match context(conn,&body.knowledge_id) {
            Ok(Some(text)) if !text.trim().is_empty() => text,
            Ok(_) => return Ok(rejected(conn,Reason::KnowledgeNoLongerEligible)),
            Err(_) => return Ok(rejected(conn,Reason::PostcheckUnavailable)),
        };
        let packet=match asset_admission(conn,body.asset_context_grant.as_ref(),archeaxis_domain::asset_context_grant::Operation::Answer) {
            Ok(packet)=>packet,
            Err(archeaxis_domain::document::Error::Sql(_))=>return Ok(rejected(conn,Reason::PostcheckUnavailable)),
            Err(_)=>return Ok(rejected(conn,Reason::AssetAuthorizationChanged)),
        };
        if let Some(packet)=&packet {
            if request["knowledge_context_sha256"]!=answer_context_digest(&current_text) {return Ok(rejected(conn,Reason::KnowledgeBodyChanged));}
            if request["asset_context"]!=asset_proof(packet) {return Ok(rejected(conn,Reason::AssetPacketChanged));}
        }
        let combined=match merged_asset_context(&current_text,packet.as_ref()) {
            Ok(text)=>text,Err(_)=>return Ok(rejected(conn,Reason::AssetPacketChanged)),
        };
        if request["context_sha256"] != answer_context_digest(&combined) {return Ok(rejected(conn,Reason::KnowledgeBodyChanged));}
        if let Some(cached) = cached_answer(conn,stable_id.as_deref(),&request)? { return Ok(cached); }
        let answer_id = match stable_id {
            Some(id) => id,
            None => id(conn,"answer_").map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"answer identity unavailable".into()))?,
        };
        let doc = json!({
            "schema":"archeaxis.machine-answer/v1","answer_id":answer_id,
            "knowledge_id":body.knowledge_id,"question":body.question,"answer":answer,
            "context_authorization":context_authorization,"request":request,
            "client_request_id":body.client_request_id,
            "authority":"candidate",
            "note":"model output awaiting human review; it is not accepted knowledge and nothing was promoted"
        });
        save(conn,&answer_id,"runtime.answer",&doc,"unmeasured",None,None)
            .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"machine answer registration failed".into()))?;
        Ok(doc)
    }).await;
    match stored {
        Ok(Ok(doc)) => execution_response(doc),
        // The worker has run even if Store/registration fails. No raw SQL or answer is returned.
        Ok(Err(_)) | Err(_) => execution_store_failure(),
    }
}

pub(super) async fn record_correction(
    State(runtime): State<Runtime>,
    headers: HeaderMap,
    Json(body): Json<CorrectionBody>,
) -> Response {
    for (name, value) in [
        ("question", &body.question),
        ("machine_answer", &body.machine_answer),
        ("corrected_answer", &body.corrected_answer),
        ("error_note", &body.error_note),
    ] {
        if value.trim().is_empty() {
            return (
                StatusCode::UNPROCESSABLE_ENTITY,
                format!("{name} is required"),
            )
                .into_response();
        }
    }
    if crate::request_actor(&headers).unwrap_or("human") == "machine" {
        return (
            StatusCode::FORBIDDEN,
            "a correction is a human act; a machine principal cannot record one",
        )
            .into_response();
    }
    let _guard = runtime.colearning_admission.lock().await;
    let written = runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection| -> Result<Value,(StatusCode,String)> {
        let db = |e:rusqlite::Error| (StatusCode::INTERNAL_SERVER_ERROR,e.to_string());
        // Legacy clients may omit the id, but only a byte-identical stored tuple can resolve it.
        let answer_id = match body.answer_id {
            Some(id) => id,
            None => conn.query_row(
                "SELECT task_id FROM machine_tasks WHERE scope IN ('runtime.answer','runtime.retest')
                 AND json_extract(conditions,'$.knowledge_id')=?1
                 AND json_extract(conditions,'$.question')=?2
                 AND json_extract(conditions,'$.answer.answer')=?3 ORDER BY rowid DESC LIMIT 1",
                rusqlite::params![body.knowledge_id,body.question,body.machine_answer], |r| r.get(0)
            ).optional().map_err(db)?.ok_or((StatusCode::NOT_FOUND,"no persisted machine answer matches this correction".into()))?,
        };
        let mut original = read_doc(conn,&answer_id,"runtime.answer").map_err(db)?
            .or(read_doc(conn,&answer_id,"runtime.retest").map_err(db)?)
            .ok_or((StatusCode::NOT_FOUND,"no persisted machine answer".into()))?;
        original["answer_id"] = answer_id.clone().into();
        if original["knowledge_id"] != body.knowledge_id || original["question"] != body.question ||
            original["answer"]["answer"] != body.machine_answer {
            return Err((StatusCode::CONFLICT,"correction does not match the persisted machine answer".into()));
        }
        let failed_id = format!("evaluation_{answer_id}");
        let reviewer = body.reviewer.unwrap_or_else(||"human".into());
        if let Some(existing) = read_doc(conn,&failed_id,"runtime.evaluation.failed").map_err(db)? {
            let correction = &existing["correction"];
            if correction["corrected_answer"] == body.corrected_answer && correction["error_note"] == body.error_note &&
                correction["reviewer"] == reviewer { return Ok(correction.clone()); }
            return Err((StatusCode::CONFLICT,"this answer already has a different immutable correction".into()));
        }
        // Nested domain savepoints let candidate, review event and evaluation commit together.
        conn.execute_batch("SAVEPOINT machine_correction").map_err(db)?;
        let result = (|| {
        let candidate = knowledge::create_machine_correction_candidate(conn, &body.corrected_answer, &answer_id).map_err(db)?;
        let correction = json!({
            "schema":"archeaxis.machine-correction/v1","answer_id":answer_id,
            "failed_task_id":failed_id,"correction_candidate_id":candidate,
            "corrects_knowledge_id":body.knowledge_id,"question":body.question,
            "machine_answer":original["answer"]["answer"],"corrected_answer":body.corrected_answer,
            "error_note":body.error_note,"reviewer":reviewer,"status":"candidate","authority":"candidate",
            "promotion":"this candidate is not knowledge until a human accepts it through review-decisions"
        });
        conn.execute("INSERT INTO review_events(knowledge_id,action,reviewer,note) VALUES(?1,'correction_recorded',?2,?3)",
            rusqlite::params![candidate,reviewer,correction.to_string()]).map_err(db)?;
        let mut evaluation = original;
        evaluation["correction"] = correction.clone();
        save(conn,&failed_id,"runtime.evaluation.failed",&evaluation,"failed",Some(&body.error_note),None).map_err(db)?;
        Ok(correction)
        })();
        if result.is_ok() {
            conn.execute_batch("RELEASE machine_correction").map_err(db)?;
        } else {
            conn.execute_batch("ROLLBACK TO machine_correction; RELEASE machine_correction").map_err(db)?;
        }
        result
    }).await;
    match written {
        Ok(Ok(doc)) => Json(doc).into_response(),
        Ok(Err((status, e))) => (status, e).into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}

pub(super) async fn run_retest(
    State(runtime): State<Runtime>,
    Json(body): Json<RetestBody>,
) -> Response {
    if let Err(refusal) = check_budget(&body.question, body.max_tokens, body.timeout_s) {
        return refusal;
    }
    if body.question.trim().is_empty() {
        return (StatusCode::UNPROCESSABLE_ENTITY, "a question is required").into_response();
    }
    if body.retest_of.trim().is_empty() {
        return (StatusCode::UNPROCESSABLE_ENTITY, "retest_of is required").into_response();
    }
    let _guard = match tokio::time::timeout(
        std::time::Duration::from_secs(10),
        runtime.colearning_admission.lock(),
    )
    .await
    {
        Ok(guard) => guard,
        Err(_) => {
            return (StatusCode::TOO_MANY_REQUESTS, "machine resource is busy").into_response();
        }
    };
    let prior_id = body.retest_of.clone();
    let prior = match runtime
        .executor
        .store()
        .submit_wait(move |conn: &mut rusqlite::Connection| {
            read_doc(conn, &prior_id, "runtime.evaluation.failed")
        })
        .await
    {
        Ok(Ok(Some(doc))) => doc,
        Ok(Ok(None)) => {
            return (
                StatusCode::NOT_FOUND,
                "no machine task with a persisted answer and failed human evaluation",
            )
                .into_response();
        }
        Ok(Err(_)) | Err(_) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                "prior evaluation unavailable",
            )
                .into_response();
        }
    };
    if prior["question"] != body.question {
        return (
            StatusCode::CONFLICT,
            "a retest must use the original question",
        )
            .into_response();
    }
    if body.asset_context_grant.is_some() && body.context_grant.is_none() {
        return (
            StatusCode::FORBIDDEN,
            "asset retest also requires explicit current knowledge grant",
        )
            .into_response();
    }
    if prior["request"].get("asset_context_grant").is_some() && body.asset_context_grant.is_none() {
        return (StatusCode::CONFLICT,"retest of an asset-grounded answer requires explicit asset consumption; omission cannot reuse its authority").into_response();
    }
    // COMPATIBILITY: preserve original frozen four-field positive-cache matching.
    // Only explicit context_grant adds the already-existing fifth field.
    let mut request = json!({"retest_of":body.retest_of,"knowledge_id":body.knowledge_id,
        "question":body.question,"max_tokens":body.max_tokens.unwrap_or(2048)});
    if let Some(grant) = &body.context_grant {
        request["context_grant"] = json!(grant);
    }
    if let Some(asset) = &body.asset_context_grant {
        request["asset_context_grant"] = json!(asset);
    }
    let cache_asset = body.asset_context_grant.clone();
    let cache_request = request.clone();
    let wanted = request.to_string();
    let cache_grant = body.context_grant.clone();
    let cache_knowledge = body.knowledge_id.clone();
    let original_id = prior["knowledge_id"].as_str().unwrap_or("").to_string();
    let correction_id = prior["correction"]["correction_candidate_id"]
        .as_str()
        .unwrap_or("")
        .to_string();
    let effective_timeout = body.timeout_s.unwrap_or(120);
    let prepared=runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection|
        -> Result<(String,Value,String,Option<Value>),(StatusCode,String)> {
        consume_grant(conn,cache_grant.as_ref(),Operation::Retest,&cache_knowledge).map_err(permission_error)?;
        // Legacy cached answers are historical reads, never renewed scoped permission.
        // Governed knowledge has already refused an omitted grant above.
        if cache_grant.is_none() && cache_asset.is_none() {
            let raw:Option<String>=conn.query_row(
                "SELECT conditions FROM machine_tasks WHERE scope='runtime.retest'
                 AND json_extract(conditions,'$.request')=json(?1) LIMIT 1",
                [&wanted],|r|r.get(0)).optional()
                .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"retest history unavailable".into()))?;
            if let Some(raw)=raw {
                let cached=serde_json::from_str::<Value>(&raw)
                    .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"retest history unreadable".into()))?;
                return Ok((String::new(),Value::Null,String::new(),Some(cached)));
            }
        }
        let text=context(conn,&cache_knowledge)
            .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"knowledge context unavailable".into()))?
            .filter(|s|!s.trim().is_empty())
            .ok_or((StatusCode::NOT_FOUND,"no knowledge item with current retest eligibility".into()))?;
        if text.len()>128_000 {
            return Err((StatusCode::UNPROCESSABLE_ENTITY,"knowledge context exceeds supported bounds".into()));
        }
        let related:bool=conn.query_row("WITH RECURSIVE lineage(id) AS (
            SELECT ?1 UNION SELECT ?2 UNION
            SELECT new_knowledge_id FROM knowledge_supersedes JOIN lineage ON old_knowledge_id=lineage.id
        ) SELECT EXISTS(SELECT 1 FROM lineage WHERE id=?3)",
            rusqlite::params![original_id,correction_id,cache_knowledge],|r|r.get(0))
            .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"retest lineage unavailable".into()))?;
        if !related {
            return Err((StatusCode::CONFLICT,"retest knowledge must be the original or its reviewed correction lineage".into()));
        }
        // Separate audit identity pins effective budget AND the actually admitted body.
        // It does not mutate request or rewrite/read old runtime.retest receipts.
        let packet=asset_admission(conn,cache_asset.as_ref(),archeaxis_domain::asset_context_grant::Operation::Retest).map_err(permission_error)?;
        let knowledge_digest=answer_context_digest(&text);
        let text=merged_asset_context(&text,packet.as_ref())?;
        let mut execution_request=json!({"schema":"archeaxis.machine-retest-execution/v1",
            "request":cache_request,"timeout_s":effective_timeout,
            "context_sha256":answer_context_digest(&text)});
        if let Some(packet)=&packet {
            execution_request["asset_context"]=asset_proof(packet);
            execution_request["knowledge_context_sha256"]=knowledge_digest.into();
        }
        frozen_asset_request(conn,cache_asset.as_ref(),&execution_request)?;
        let execution_id=format!("retest_exec_{}",withheld::digest(&execution_request.to_string()));
        if let Some(terminal)=withheld::terminal(conn,&execution_id,&execution_request).map_err(terminal_error)? {
            return Ok((text,execution_request,execution_id,Some(terminal)));
        }
        let raw:Option<String>=conn.query_row(
            "SELECT conditions FROM machine_tasks WHERE scope='runtime.retest'
             AND json_extract(conditions,'$.request')=json(?1) LIMIT 1",
            [wanted],|r|r.get(0)).optional()
            .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"retest history unavailable".into()))?;
        let cached=raw.map(|s|serde_json::from_str::<Value>(&s)
            .map_err(|_|(StatusCode::INTERNAL_SERVER_ERROR,"retest history unreadable".into()))).transpose()?;
        if let Some(cached)=&cached {
            if cache_asset.is_some() && cached["execution_request"]!=execution_request {
                return Err((StatusCode::CONFLICT,"asset retest cache differs from frozen execution context or budget".into()));
            }
        }
        Ok((text,execution_request,execution_id,cached))
    }).await;
    let (admitted_text, execution_request, execution_id, cached) = match prepared {
        Ok(Ok(prepared)) => prepared,
        Ok(Err((status, message))) => return (status, message).into_response(),
        Err(_) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                "retest preparation unavailable",
            )
                .into_response();
        }
    };
    if let Some(doc) = cached {
        return execution_response(doc);
    }
    if let Some(refusal) = crate::capabilities::refusal(&runtime.executor, "machine.answer").await {
        return refusal;
    }
    let answer = match runtime
        .executor
        .machine_answer(
            admitted_text,
            body.question.clone(),
            body.max_tokens.unwrap_or(2048),
            std::time::Duration::from_secs(effective_timeout),
        )
        .await
    {
        Ok(answer)
            if answer["answer"]
                .as_str()
                .is_some_and(|s| !s.trim().is_empty()) =>
        {
            answer
        }
        Ok(_) => {
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                "the worker returned no answer",
            )
                .into_response();
        }
        Err(e) => return (StatusCode::SERVICE_UNAVAILABLE, e).into_response(),
    };
    let stored=runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection| {
        let rejected=|conn: &mut rusqlite::Connection,reason:Reason| {
            withheld::refuse(conn,&Executed {
                execution_id:&execution_id,client_request_id:None,operation:"retest",
                knowledge_id:&body.knowledge_id,grant:body.context_grant.as_ref(),request:&execution_request,
                context_sha256:execution_request["context_sha256"].as_str().unwrap_or("UNVERIFIED"),
                answer:&answer,retest_of:Some(&body.retest_of),
            },reason)
        };
        let context_authorization=match consume_grant(conn,body.context_grant.as_ref(),Operation::Retest,&body.knowledge_id) {
            Ok(proof)=>proof,
            Err(archeaxis_domain::document::Error::Sql(_))=>return Ok(rejected(conn,Reason::PostcheckUnavailable)),
            Err(_)=>return Ok(rejected(conn,Reason::AuthorizationChanged)),
        };
        let current_text=match context(conn,&body.knowledge_id) {
            Ok(Some(text)) if !text.trim().is_empty()=>text,
            Ok(_)=>return Ok(rejected(conn,Reason::KnowledgeNoLongerEligible)),
            Err(_)=>return Ok(rejected(conn,Reason::PostcheckUnavailable)),
        };
        let packet=match asset_admission(conn,body.asset_context_grant.as_ref(),archeaxis_domain::asset_context_grant::Operation::Retest) {
            Ok(packet)=>packet,
            Err(archeaxis_domain::document::Error::Sql(_))=>return Ok(rejected(conn,Reason::PostcheckUnavailable)),
            Err(_)=>return Ok(rejected(conn,Reason::AssetAuthorizationChanged)),
        };
        if let Some(packet)=&packet {
            if execution_request["knowledge_context_sha256"]!=answer_context_digest(&current_text) {return Ok(rejected(conn,Reason::KnowledgeBodyChanged));}
            if execution_request["asset_context"]!=asset_proof(packet) {return Ok(rejected(conn,Reason::AssetPacketChanged));}
        }
        let combined=match merged_asset_context(&current_text,packet.as_ref()) {Ok(text)=>text,Err(_)=>return Ok(rejected(conn,Reason::AssetPacketChanged))};
        if execution_request["context_sha256"] != answer_context_digest(&combined) {return Ok(rejected(conn,Reason::KnowledgeBodyChanged));}
        let retest_id=id(conn,"retest_")?;
        let mut doc=json!({
            "schema":"archeaxis.machine-retest/v1","retest_task_id":retest_id,"answer_id":retest_id,"retest_of":body.retest_of,
            "knowledge_id":body.knowledge_id,"question":body.question,"answer":answer,
            "answered":answer["answer"],"request":request,"authority":"candidate","context_authorization":context_authorization,
            "prior":{"conditions":prior,"outcome":"failed","model_version":prior["answer"]["model"],
                "knowledge_version":format!("{}@v1",prior["knowledge_id"].as_str().unwrap())},
            "note":"the Core does not decide whether the correction helped; a human compares both answers"
        });
        if body.asset_context_grant.is_some() {doc["execution_request"]=execution_request;}
        save(conn,&retest_id,"runtime.retest",&doc,"unmeasured",None,Some(&body.retest_of))?;
        Ok::<_,rusqlite::Error>(doc)
    }).await;
    match stored {
        Ok(Ok(doc)) => execution_response(doc),
        Ok(Err(_)) | Err(_) => execution_store_failure(),
    }
}
