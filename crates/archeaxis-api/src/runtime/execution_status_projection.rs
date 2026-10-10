//! Candidate: read-only enrichment only for /execution-status; legacy /jobs stays unchanged.
//! Wire hook in runtime::mod.rs: mod execution_status_projection; route get(execution_status).
//! Copy status() faulted-active check; submit this function in its Store closure and preserve 404/503.
use rusqlite::{Connection, OptionalExtension};
use serde_json::{Value, json};

pub fn project(conn: &Connection, job: &str) -> rusqlite::Result<Option<Value>> {
    let current: Option<(String,String,String)> = conn.query_row(
        "SELECT state,input_ref,kind FROM jobs WHERE job_id=?1", [job],
        |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?))
    ).optional()?;
    let Some((state,input_ref,kind)) = current else { return Ok(None) };
    let mut statement = conn.prepare("SELECT attempt,request_id,state,error,request_json,result_digest,created_at,completed_at,response_json IS NOT NULL FROM job_attempts WHERE job_id=?1 ORDER BY attempt DESC LIMIT 21")?;
    let rows = statement.query_map([job], |r| Ok((r.get::<_,i64>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,Option<String>>(3)?,r.get::<_,String>(4)?,r.get::<_,Option<String>>(5)?,r.get::<_,String>(6)?,r.get::<_,Option<String>>(7)?,r.get::<_,bool>(8)?)))?.collect::<rusqlite::Result<Vec<_>>>()?;
    let capped = rows.len() > 20;
    let mut attempts = Vec::new();
    for (attempt,request_id,attempt_state,error,request_wire,result_digest,created_at,completed_at,response_committed) in rows.iter().take(20) {
        // Request JSON is authoritative persisted worker request, but it includes private staging paths.
        // Reject corrupt JSON; whitelist only public finite-budget choices, never serialize the envelope.
        let request: Value = serde_json::from_str(request_wire).map_err(|_|rusqlite::Error::InvalidQuery)?;
        if request.get("job_id").and_then(Value::as_str) != Some(job)
            || request.get("request_id").and_then(Value::as_str) != Some(request_id.as_str())
            || request.get("attempt").and_then(Value::as_i64) != Some(*attempt) {
            return Err(rusqlite::Error::InvalidQuery);
        }
        let deadline = request.get("deadline_ms").and_then(Value::as_u64).filter(|v| (1..=300000).contains(v)).ok_or(rusqlite::Error::InvalidQuery)?;
        let capability = request.get("capability").and_then(Value::as_str).ok_or(rusqlite::Error::InvalidQuery)?;
        let split = request.pointer("/parameters/split").and_then(Value::as_bool).unwrap_or(false);
        let words = request.pointer("/parameters/words").and_then(Value::as_bool).unwrap_or(false);
        let mut outputs = Vec::new();
        let mut windows = Value::Null;
        let mut output_statement = conn.prepare("SELECT kind,metadata_json,CASE WHEN kind='loss_report' AND length(CAST(content AS BLOB))<=262144 THEN content ELSE NULL END FROM job_outputs WHERE job_id=?1 AND attempt=?2 ORDER BY kind LIMIT 51")?;
        let output_rows = output_statement.query_map(rusqlite::params![job,attempt], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,Option<String>>(2)?)))?.collect::<rusqlite::Result<Vec<_>>>()?;
        let outputs_capped = output_rows.len() > 50;
        for (output_kind,wire,loss) in output_rows.iter().take(50) {
            let metadata: Value = serde_json::from_str(wire).map_err(|_|rusqlite::Error::InvalidQuery)?;
            let sha256 = metadata.get("sha256").and_then(Value::as_str).ok_or(rusqlite::Error::InvalidQuery)?;
            let bytes = metadata.get("byte_length").and_then(Value::as_u64).ok_or(rusqlite::Error::InvalidQuery)?;
            outputs.push(json!({"kind":output_kind,"sha256":sha256,"byte_length":bytes,"media_type":metadata.get("media_type"),"schema":metadata.get("schema"),"authority_effect":metadata.get("authority_effect")}));
            if let Some(loss) = loss {
                let receipt: Value = serde_json::from_str(loss).map_err(|_|rusqlite::Error::InvalidQuery)?;
                if let Some(value) = receipt.pointer("/params/worker_output/windows").and_then(Value::as_object) {
                    // Persisted worker-reported window evidence only; never derive completed counts from attempts.
                    let mut summary = serde_json::Map::new();
                    for key in ["status","windows_expected","windows_present","windows_missing","windows_resumed"] {
                        if let Some(value) = value.get(key) { summary.insert(key.into(),value.clone()); }
                    }
                    windows = Value::Object(summary);
                }
            }
        }
        let checkpoint_status = if outputs.is_empty() { "NOT_OBSERVED" } else { "CORE_COMMITTED" };
        let next_attempt_eligible_state = rows.first().is_some_and(|row| row.0 == *attempt)
            && ["failed","cancelled"].contains(&state.as_str());
        // Runtime registration/current capability policy still decides on claim, never a status projection.
        let resume = if capability == "media.transcribe" && split { "NOT_OBSERVED" } else { "NOT_SUPPORTED" };
        attempts.push(json!({"attempt":attempt,"request_id":request_id,"state":attempt_state,"error":error,
            "budget":{"deadline_ms":deadline,"split":split,"words":words,"capability":capability},
            "created_at":created_at,"completed_at":completed_at,"result_digest":result_digest,
            "steps":{"durable_claim":"RECORDED","worker_response_commit":if *response_committed {"RECORDED"} else {"NOT_OBSERVED"},"terminal_write":if completed_at.is_some(){"RECORDED"}else{"NOT_OBSERVED"}},
            "checkpoint":{"status":checkpoint_status,"scope":"CORE_COMMITTED_OUTPUTS_ONLY","outputs":outputs,"outputs_capped":outputs_capped,"worker_reported_windows":windows,"worker_cache_readback":"NOT_OBSERVED"},
            "continuation":{"resume_status":resume,"new_attempt_eligible_state":next_attempt_eligible_state,"condition":"CURRENT_DECLARED_ROUTE_CAPABILITY_SOURCE_AND_NEW_REQUEST_ID_REQUIRED","same_request_replay":"RETURNS_RECORDED_OUTCOME_WITHOUT_REEXECUTION"}}));
    }
    let latest = attempts.first();
    Ok(Some(json!({"job_id":job,"input_ref":input_ref,"kind":kind,"state":state,
        "attempt":latest.map(|v|v["attempt"].clone()).unwrap_or(Value::Null),
        "request_id":latest.map(|v|v["request_id"].clone()).unwrap_or(Value::Null),
        "error":latest.map(|v|v["error"].clone()).unwrap_or(Value::Null),
        "attempts":attempts,"attempts_capped":capped,
        "evidence_scope":"DURABLE_CORE_ROWS; WORKER_CACHE_NOT_INSPECTED"})))
}
