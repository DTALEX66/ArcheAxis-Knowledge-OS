//! Persisted G4 provenance. Runtime scopes are inaccessible to the generic receipt writer.
use super::*;
use archeaxis_domain::{knowledge, machine};

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

async fn get_context(runtime: &Runtime, knowledge_id: &str) -> Result<String, Response> {
    let wanted = knowledge_id.to_string();
    match runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection| context(conn, &wanted)).await {
        Ok(Ok(Some(text))) if !text.trim().is_empty() => Ok(text),
        Ok(Ok(_)) => Err((StatusCode::NOT_FOUND, format!("no knowledge item {knowledge_id} with an active accepted/personal body to answer from")).into_response()),
        Ok(Err(e)) => Err((StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()),
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response()),
    }
}

pub(super) async fn machine_answer(
    State(runtime): State<Runtime>,
    Json(body): Json<MachineAnswerBody>,
) -> Response {
    if body.question.trim().is_empty() {
        return (StatusCode::UNPROCESSABLE_ENTITY, "a question is required").into_response();
    }
    if let Some(refusal) = crate::capabilities::refusal(&runtime.executor, "machine.answer").await {
        return refusal;
    }
    let context = match get_context(&runtime, &body.knowledge_id).await {
        Ok(c) => c,
        Err(r) => return r,
    };
    let answer = match runtime
        .executor
        .machine_answer(
            context,
            body.question.clone(),
            body.max_tokens.unwrap_or(2048),
            std::time::Duration::from_secs(body.timeout_s.unwrap_or(300).clamp(1, 900)),
        )
        .await
    {
        Ok(a) if a["answer"].as_str().is_some_and(|s| !s.trim().is_empty()) => a,
        Ok(_) => {
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                "the worker returned no answer",
            )
                .into_response();
        }
        Err(e) => return (StatusCode::SERVICE_UNAVAILABLE, e).into_response(),
    };
    let stored = runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection| {
        let answer_id = id(conn, "answer_")?;
        let doc = json!({
            "schema":"archeaxis.machine-answer/v1", "answer_id":answer_id,
            "knowledge_id":body.knowledge_id, "question":body.question, "answer":answer,
            "authority":"candidate", "note":"model output awaiting human review; it is not accepted knowledge and nothing was promoted"
        });
        save(conn, &answer_id, "runtime.answer", &doc, "unmeasured", None, None)?;
        Ok::<_, rusqlite::Error>(doc)
    }).await;
    match stored {
        Ok(Ok(doc)) => Json(doc).into_response(),
        Ok(Err(e)) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
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
    if body.question.trim().is_empty() {
        return (StatusCode::UNPROCESSABLE_ENTITY, "a question is required").into_response();
    }
    if body.retest_of.trim().is_empty() {
        return (StatusCode::UNPROCESSABLE_ENTITY, "retest_of is required").into_response();
    }
    // One inference per receipt identity, including concurrent requests in this Core.
    let _guard = runtime.colearning_admission.lock().await;
    let prior_id = body.retest_of.clone();
    let prior = runtime
        .executor
        .store()
        .submit_wait(move |conn: &mut rusqlite::Connection| {
            read_doc(conn, &prior_id, "runtime.evaluation.failed")
        })
        .await;
    let prior = match prior {
        Ok(Ok(Some(doc))) => doc,
        Ok(Ok(None)) => {
            return (
                StatusCode::NOT_FOUND,
                "no machine task with a persisted answer and failed human evaluation",
            )
                .into_response();
        }
        Ok(Err(e)) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    };
    if prior["question"] != body.question {
        return (
            StatusCode::CONFLICT,
            "a retest must use the original question",
        )
            .into_response();
    }
    let request = json!({"retest_of":body.retest_of,"knowledge_id":body.knowledge_id,
        "question":body.question,"max_tokens":body.max_tokens.unwrap_or(2048)});
    let wanted = request.to_string();
    let cached = runtime
        .executor
        .store()
        .submit_wait(move |conn: &mut rusqlite::Connection| {
            let raw: Option<String> = conn
                .query_row(
                    "SELECT conditions FROM machine_tasks WHERE scope='runtime.retest'
             AND json_extract(conditions,'$.request')=json(?1) LIMIT 1",
                    [wanted],
                    |r| r.get(0),
                )
                .optional()?;
            raw.map(|s| {
                serde_json::from_str::<Value>(&s).map_err(|e| {
                    rusqlite::Error::FromSqlConversionFailure(
                        0,
                        rusqlite::types::Type::Text,
                        Box::new(e),
                    )
                })
            })
            .transpose()
        })
        .await;
    match cached {
        Ok(Ok(Some(doc))) => return Json(doc).into_response(),
        Ok(Ok(None)) => {}
        Ok(Err(e)) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
    let context = match get_context(&runtime, &body.knowledge_id).await {
        Ok(c) => c,
        Err(r) => return r,
    };
    let original_id = prior["knowledge_id"].as_str().unwrap_or("").to_string();
    let correction_id = prior["correction"]["correction_candidate_id"]
        .as_str()
        .unwrap_or("")
        .to_string();
    let target = body.knowledge_id.clone();
    let related = runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection| {
        conn.query_row("WITH RECURSIVE lineage(id) AS (
            SELECT ?1 UNION SELECT ?2 UNION
            SELECT new_knowledge_id FROM knowledge_supersedes JOIN lineage ON old_knowledge_id=lineage.id
        ) SELECT EXISTS(SELECT 1 FROM lineage WHERE id=?3)",
            rusqlite::params![original_id,correction_id,target], |r| r.get::<_,bool>(0))
    }).await;
    match related {
        Ok(Ok(true)) => {}
        Ok(Ok(false)) => {
            return (
                StatusCode::CONFLICT,
                "retest knowledge must be the original or its reviewed correction lineage",
            )
                .into_response();
        }
        Ok(Err(e)) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        Err(e) => return (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
    if let Some(refusal) = crate::capabilities::refusal(&runtime.executor, "machine.answer").await {
        return refusal;
    }
    let answer = match runtime
        .executor
        .machine_answer(
            context,
            body.question.clone(),
            body.max_tokens.unwrap_or(2048),
            std::time::Duration::from_secs(body.timeout_s.unwrap_or(300).clamp(1, 900)),
        )
        .await
    {
        Ok(a) if a["answer"].as_str().is_some_and(|s| !s.trim().is_empty()) => a,
        Ok(_) => {
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                "the worker returned no answer",
            )
                .into_response();
        }
        Err(e) => return (StatusCode::SERVICE_UNAVAILABLE, e).into_response(),
    };
    let stored = runtime.executor.store().submit_wait(move |conn: &mut rusqlite::Connection| {
        let retest_id = id(conn,"retest_")?;
        let doc = json!({
            "schema":"archeaxis.machine-retest/v1","retest_task_id":retest_id,"answer_id":retest_id,"retest_of":body.retest_of,
            "knowledge_id":body.knowledge_id,"question":body.question,"answer":answer,
            "answered":answer["answer"],"request":request,"authority":"candidate",
            "prior":{"conditions":prior,"outcome":"failed","model_version":prior["answer"]["model"],
                "knowledge_version":format!("{}@v1",prior["knowledge_id"].as_str().unwrap())},
            "note":"the Core does not decide whether the correction helped; a human compares both answers"
        });
        save(conn,&retest_id,"runtime.retest",&doc,"unmeasured",None,Some(&body.retest_of))?;
        Ok::<_,rusqlite::Error>(doc)
    }).await;
    match stored {
        Ok(Ok(doc)) => Json(doc).into_response(),
        Ok(Err(e)) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()).into_response(),
    }
}
