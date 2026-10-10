//! Core-owned, redacted audit of inference that ran but could not be published.
//! This module is not an HTTP writer; generic runtime.* writes remain forbidden.
use archeaxis_domain::{context_grant::Consumption, machine};
use rusqlite::{Connection, OptionalExtension};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

pub(super) const SCOPE: &str = "runtime.execution.withheld";
pub(super) const STATE: &str = "EXECUTED_BUT_WITHHELD";

#[derive(Clone, Copy)]
pub(super) enum Reason {
    AuthorizationChanged,
    KnowledgeNoLongerEligible,
    KnowledgeBodyChanged,
    PostcheckUnavailable,
    AssetAuthorizationChanged,
    AssetPacketChanged,
}
impl Reason {
    fn code(self) -> &'static str {
        match self {
            Self::AuthorizationChanged => "CONTEXT_AUTHORIZATION_CHANGED",
            Self::KnowledgeNoLongerEligible => "KNOWLEDGE_NO_LONGER_ELIGIBLE",
            Self::KnowledgeBodyChanged => "KNOWLEDGE_BODY_CHANGED",
            Self::PostcheckUnavailable => "POSTCHECK_UNAVAILABLE",
            Self::AssetAuthorizationChanged => "ASSET_AUTHORIZATION_CHANGED",
            Self::AssetPacketChanged => "ASSET_PACKET_CHANGED",
        }
    }
}

pub(super) fn digest(value: &str) -> String {
    format!("{:x}", Sha256::digest(value.as_bytes()))
}
pub(super) fn audit_id(execution_id: &str) -> String {
    format!("withheld_{}", digest(execution_id))
}

/// All fields come from the actual admitted execution, not a late UI state.
/// Model must come from the worker's returned `model`, never its requested route.
pub(super) struct Executed<'a> {
    pub execution_id: &'a str,
    pub client_request_id: Option<&'a str>,
    pub operation: &'a str,
    pub knowledge_id: &'a str,
    pub grant: Option<&'a Consumption>,
    pub request: &'a Value,
    pub context_sha256: &'a str,
    pub answer: &'a Value,
    pub retest_of: Option<&'a str>,
}

fn read(conn: &Connection, task_id: &str) -> rusqlite::Result<Option<Value>> {
    // Read-only preflight: no table creation, even in an empty owned store.
    let exists: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='machine_tasks')",
        [],
        |r| r.get(0),
    )?;
    if !exists {
        return Ok(None);
    }
    let raw: Option<String> = conn
        .query_row(
            "SELECT conditions FROM machine_tasks WHERE task_id=?1 AND scope=?2",
            rusqlite::params![task_id, SCOPE],
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

/// Before a new worker invocation, bind the terminal failure to the frozen request.
/// Call under the existing admission mutex, in the same Store preparation closure.
/// A different request with the same client key is a conflict, never a new inference.
pub(super) fn terminal(
    conn: &Connection,
    execution_id: &str,
    request: &Value,
) -> rusqlite::Result<Option<Value>> {
    let task_id = audit_id(execution_id);
    let Some(doc) = read(conn, &task_id)? else {
        return Ok(None);
    };
    if doc["schema"] != "archeaxis.machine-execution-withheld/v1"
        || doc["execution_state"] != STATE
        || doc["request_sha256"] != digest(&request.to_string())
    {
        return Err(rusqlite::Error::InvalidParameterName(
            "client request identity already has a different or unreadable terminal execution"
                .into(),
        ));
    }
    Ok(Some(response(&doc, true)))
}

fn response(doc: &Value, replayed: bool) -> Value {
    json!({
        "schema":"archeaxis.machine-execution-refusal/v1",
        "execution_state":STATE,
        "answer_published":false,
        "audit_status":"RECORDED",
        "audit_task_id":doc["audit_task_id"],
        "reason_code":doc["reason_code"],
        "replayed":replayed,
        "note":"Inference ran; no answer was published. The audit grants no current permission."
    })
}

fn record(
    conn: &mut Connection,
    executed: &Executed<'_>,
    reason: Reason,
) -> rusqlite::Result<Value> {
    if !matches!(executed.operation, "answer" | "retest")
        || executed.execution_id.is_empty()
        || executed.knowledge_id.is_empty()
    {
        return Err(rusqlite::Error::InvalidParameterName(
            "invalid Core execution audit identity".into(),
        ));
    }
    let task_id = audit_id(executed.execution_id);
    // Missing actual model is explicit unknown provenance, never a claimed model.
    let actual_model = executed.answer["model"]
        .as_str()
        .filter(|s| !s.trim().is_empty());
    let model_version = actual_model.unwrap_or("UNKNOWN_WORKER_MODEL");
    let grant = executed.grant.map(|g| {
        json!({
            "document_id":g.document_id,"version":g.version,"content_sha256":g.content_sha256
        })
    });
    let mut doc = json!({
        "schema":"archeaxis.machine-execution-withheld/v1",
        "audit_task_id":task_id,
        "execution_state":STATE,
        "operation":executed.operation,
        "knowledge_id":executed.knowledge_id,
        "client_request_id":executed.client_request_id,
        "request_sha256":digest(&executed.request.to_string()),
        "admitted_context_sha256":executed.context_sha256,
        "consumed_context_grant":grant,
        "admission_mode":if executed.grant.is_some() {"pinned_context_grant"} else {"legacy_knowledge_eligibility_only"},
        "model_id":actual_model,
        "model_provenance":if actual_model.is_some() {"WORKER_REPORTED"} else {"UNVERIFIED"},
        "answer_sha256":executed.answer["answer"].as_str().map(digest),
        "reason_code":reason.code(),
        "answer_published":false,
        "current_permission_valid":false,
        "authority":"historical_execution_audit",
        "grants_human_mastery":false,
        "grants_ai_qualification":false
    });
    let actual_request = executed.request.get("request").unwrap_or(executed.request);
    if let Some(input) = actual_request.get("asset_context_grant") {
        doc["asset_request_id"] = input["request_id"].clone();
        doc["consumed_asset_context"] = executed.request["asset_context"].clone();
    }
    if let Some(old) = read(conn, &task_id)? {
        if old == doc {
            return Ok(response(&old, true));
        }
        return Err(rusqlite::Error::InvalidParameterName(
            "immutable withheld receipt conflicts".into(),
        ));
    }
    let serialized = doc.to_string();
    machine::record_machine_task(
        conn,
        &machine::MachineTask {
            task_id: &task_id,
            principal: "machine",
            conditions: &serialized,
            // The knowledge may now be withdrawn. The historical ID is in conditions.
            knowledge_version: None,
            method_version: None,
            tool_version: None,
            model_version,
            scope: SCOPE,
            outcome: "failed",
            failure: Some(reason.code()),
            retest_of: executed.retest_of,
        },
    )?;
    // Never return RECORDED without checking the actual immutable readback.
    if read(conn, &task_id)?.as_ref() != Some(&doc) {
        return Err(rusqlite::Error::InvalidParameterName(
            "withheld audit readback mismatch".into(),
        ));
    }
    Ok(response(&doc, false))
}

/// Return an explicit executed state even when durable audit persistence fails.
/// The HTTP handler must map RECORDED -> 403, FAILED -> 500, never a 2xx.
pub(super) fn refuse(conn: &mut Connection, executed: &Executed<'_>, reason: Reason) -> Value {
    record(conn, executed, reason).unwrap_or_else(|_| json!({
        "schema":"archeaxis.machine-execution-refusal/v1",
        "execution_state":STATE,"answer_published":false,
        "audit_status":"FAILED","audit_task_id":null,
        "reason_code":reason.code(),"error_code":"WITHHELD_AUDIT_WRITE_FAILED",
        "note":"Inference ran and no answer was published; durable audit could not be confirmed. Do not retry automatically."
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    fn execute<'a>(
        request: &'a Value,
        answer: &'a Value,
        grant: Option<&'a Consumption>,
    ) -> Executed<'a> {
        Executed {
            execution_id: "answer_req_fixture",
            client_request_id: Some("fixture"),
            operation: "answer",
            knowledge_id: "withdrawn_original_knowledge",
            grant,
            request,
            context_sha256: "pinned_delivered_context_sha",
            answer,
            retest_of: None,
        }
    }
    #[test]
    fn redacted_failed_receipt_survives_missing_knowledge_and_replays_without_overwrite() {
        let mut conn = Connection::open_in_memory().unwrap();
        let request = json!({"question":"SECRET QUESTION","client_request_id":"fixture"});
        let answer = json!({"answer":"SECRET ANSWER","model":"actual/fixture-model"});
        let grant = Consumption {
            document_id: "actual-grant".into(),
            version: 7,
            content_sha256: "actual-sha".into(),
            purpose: "SECRET BASIS".into(),
        };
        let executed = execute(&request, &answer, Some(&grant));
        let first = refuse(&mut conn, &executed, Reason::AuthorizationChanged);
        assert_eq!(first["audit_status"], "RECORDED");
        let task_id = first["audit_task_id"].as_str().unwrap();
        let receipt = machine::machine_task(&conn, task_id).unwrap().unwrap();
        assert_eq!(receipt.scope, SCOPE);
        assert_eq!(receipt.outcome, "failed");
        assert_eq!(receipt.model_version, "actual/fixture-model");
        assert!(receipt.knowledge_version.is_none());
        assert!(!receipt.conditions.contains("SECRET"));
        let doc: Value = serde_json::from_str(&receipt.conditions).unwrap();
        assert_eq!(doc["consumed_context_grant"]["version"], 7);
        assert_eq!(doc["knowledge_id"], "withdrawn_original_knowledge");
        assert_eq!(doc["answer_sha256"], digest("SECRET ANSWER"));
        assert_eq!(
            terminal(&conn, executed.execution_id, &request)
                .unwrap()
                .unwrap()["replayed"],
            true
        );
        assert_eq!(
            refuse(&mut conn, &executed, Reason::AuthorizationChanged)["replayed"],
            true
        );
        assert!(terminal(&conn, executed.execution_id, &json!({"question":"changed"})).is_err());
        let different = json!({"answer":"different answer","model":"actual/fixture-model"});
        assert_eq!(
            refuse(
                &mut conn,
                &execute(&request, &different, Some(&grant)),
                Reason::AuthorizationChanged
            )["audit_status"],
            "FAILED"
        );
        assert_eq!(
            machine::machine_task(&conn, task_id)
                .unwrap()
                .unwrap()
                .conditions,
            receipt.conditions
        );
    }
    #[test]
    fn audit_storage_failure_still_reports_executed_not_not_run() {
        let mut conn = Connection::open_in_memory().unwrap();
        conn.execute_batch("CREATE TABLE machine_tasks(task_id TEXT);")
            .unwrap();
        let response = refuse(
            &mut conn,
            &execute(
                &json!({}),
                &json!({"answer":"hidden","model":"actual"}),
                None,
            ),
            Reason::PostcheckUnavailable,
        );
        assert_eq!(response["execution_state"], STATE);
        assert_eq!(response["audit_status"], "FAILED");
        assert!(response["audit_task_id"].is_null());
        assert_eq!(response["answer_published"], false);
        assert!(!response.to_string().contains("hidden"));
    }
    #[test]
    fn empty_store_terminal_read_does_not_create_table() {
        let conn = Connection::open_in_memory().unwrap();
        assert!(terminal(&conn, "fixture", &json!({})).unwrap().is_none());
        let count: i64 = conn
            .query_row(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='machine_tasks'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(count, 0);
    }
}
