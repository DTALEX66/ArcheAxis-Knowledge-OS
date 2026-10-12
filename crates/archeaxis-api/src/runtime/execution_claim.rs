//! Durable pre-inference barrier. A lost process cannot silently reuse an unfinished claim.
use rusqlite::{Connection, OptionalExtension};
use serde_json::{Value, json};

const MAX_ATTEMPTS: u64 = 3;

fn key(id: &str) -> String {
    format!("machine_execution_claim_{}", super::withheld::digest(id))
}
pub(super) fn attempt(conn: &Connection, id: &str) -> rusqlite::Result<u64> {
    let raw: String = conn.query_row(
        "SELECT value FROM workspace_meta WHERE key=?1",
        [key(id)],
        |r| r.get(0),
    )?;
    let claim: Value = serde_json::from_str(&raw)
        .map_err(|_| rusqlite::Error::InvalidParameterName("unreadable execution claim".into()))?;
    claim["attempt"]
        .as_u64()
        .filter(|n| (1..=MAX_ATTEMPTS).contains(n))
        .ok_or_else(|| rusqlite::Error::InvalidParameterName("unknown execution attempt".into()))
}

pub(super) fn admit(conn: &Connection, id: &str, request: &Value) -> rusqlite::Result<()> {
    let key = key(id);
    let digest = super::withheld::digest(&request.to_string());
    let old: Option<String> = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [&key],
            |r| r.get(0),
        )
        .optional()?;
    let mut attempt = 1;
    if let Some(old) = old {
        let old: Value = serde_json::from_str(&old).map_err(|_| {
            rusqlite::Error::InvalidParameterName(
                "unreadable execution claim; prior execution UNVERIFIED".into(),
            )
        })?;
        if old["schema"] != "archeaxis.machine-execution-claim/v1"
            || old["request_sha256"] != digest
            || old["state"] != "KNOWN_FAILURE"
        {
            return Err(rusqlite::Error::InvalidParameterName("unfinished or conflicting execution claim; prior execution UNVERIFIED; inference not repeated".into()));
        }
        // Older claims have no attempt counter. Their prior count cannot be
        // reconstructed safely, so retain them rather than reset the budget.
        let prior = old["attempt"]
            .as_u64()
            .filter(|n| *n > 0 && *n < MAX_ATTEMPTS)
            .ok_or_else(|| {
                rusqlite::Error::InvalidParameterName(
                    "execution retry budget exhausted or UNVERIFIED; inference not repeated".into(),
                )
            })?;
        attempt = prior + 1;
    }
    let value = json!({"schema":"archeaxis.machine-execution-claim/v1","request_sha256":digest,"state":"IN_FLIGHT","attempt":attempt,"max_attempts":MAX_ATTEMPTS});
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value", rusqlite::params![key,value.to_string()])?;
    Ok(())
}

/// An unconfirmed executor/cleanup outcome must keep the durable barrier.
/// This describes only local worker completion, never provider-side stop status.
pub(super) fn record_failure(conn: &Connection, id: &str, error: &str) -> rusqlite::Result<()> {
    let confirmed = matches!(
        error,
        "invalid machine answer budget or input"
            | "machine worker cancelled"
            | "machine selection verification timed out"
            | "machine selection is not verified in local inventory"
            | "machine selection budget exhausted"
            | "machine staging unavailable"
            | "machine context staging failed"
            | "machine worker spawn failed"
            | "machine pipe read failed"
            | "machine worker output exceeds bound"
            | "machine status unavailable"
            | "machine worker timed out"
            | "machine worker returned invalid JSON"
            | "machine worker returned no candidate answer"
            | "machine worker model selection mismatch"
            | "machine failure: MODEL_CALL_FAILED"
            | "machine failure: NO_FINAL_ANSWER"
            | "machine failure: EMPTY_ANSWER"
            | "machine failure: WORKER_FAILED"
    );
    if !confirmed {
        return Ok(());
    }
    known_failure(conn, id)
}

/// Persist a redacted terminal audit and release the retry barrier atomically.
/// Unknown cleanup outcomes deliberately produce neither a terminal audit nor a release.
pub(super) fn record_terminal_failure(
    conn: &mut Connection,
    id: &str,
    error: &str,
    identity: &Value,
) -> rusqlite::Result<()> {
    let tx = conn.savepoint()?;
    record_failure(&tx, id, error)?;
    let raw: String = tx.query_row(
        "SELECT value FROM workspace_meta WHERE key=?1",
        [key(id)],
        |r| r.get(0),
    )?;
    let claim: Value = serde_json::from_str(&raw)
        .map_err(|_| rusqlite::Error::InvalidParameterName("unreadable execution claim".into()))?;
    if claim["state"] != "KNOWN_FAILURE" {
        return tx.commit();
    }
    let attempt = claim["attempt"]
        .as_u64()
        .filter(|n| *n > 0 && *n <= MAX_ATTEMPTS)
        .ok_or_else(|| rusqlite::Error::InvalidParameterName("unknown execution attempt".into()))?;
    let task_id = format!(
        "failure_{}",
        super::withheld::digest(&format!("{id}:{attempt}"))
    );
    let doc = json!({
        "schema":"archeaxis.machine-execution-failed/v1", "audit_task_id":task_id,
        "operation":identity["operation"], "knowledge_id":identity["knowledge_id"],
        "client_request_id":identity["client_request_id"], "retest_of":identity["retest_of"],
        "admission_request_sha256":identity["admission_request_sha256"],
        "request_sha256":claim["request_sha256"], "attempt":attempt,"max_attempts":MAX_ATTEMPTS,
        "reason_code":error, "execution_state":"UNVERIFIED", "answer_published":false,
        "provider_stop_state":"UNKNOWN", "usage":null,"cost":null,
        "authority":"historical_execution_audit"
    });
    let serialized = doc.to_string();
    archeaxis_domain::machine::record_machine_task_in_transaction(
        &tx,
        &archeaxis_domain::machine::MachineTask {
            task_id: &task_id,
            principal: "machine",
            conditions: &serialized,
            knowledge_version: None,
            method_version: None,
            tool_version: None,
            model_version: "UNKNOWN_WORKER_MODEL",
            scope: "runtime.execution.failed",
            outcome: "failed",
            failure: Some(error),
            retest_of: identity["retest_of"].as_str(),
        },
    )?;
    tx.execute(
        "UPDATE workspace_meta SET value=json_set(value,'$.terminal_task_id',?2) WHERE key=?1",
        rusqlite::params![key(id), task_id],
    )?;
    let readback = archeaxis_domain::machine::machine_task(&tx, &task_id)?
        .ok_or_else(|| rusqlite::Error::InvalidParameterName("failure audit missing".into()))?;
    if readback.conditions != serialized {
        return Err(rusqlite::Error::InvalidParameterName(
            "failure audit readback mismatch".into(),
        ));
    }
    tx.commit()
}

/// Only a returned worker failure permits an explicit retry. Process disappearance does not.
pub(super) fn known_failure(conn: &Connection, id: &str) -> rusqlite::Result<()> {
    let changed = conn.execute("UPDATE workspace_meta SET value=json_set(value,'$.state','KNOWN_FAILURE') WHERE key=?1 AND json_extract(value,'$.state')='IN_FLIGHT'", [key(id)])?;
    if changed != 1 {
        return Err(rusqlite::Error::InvalidParameterName(
            "execution failure claim not confirmed".into(),
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn terminal_failure_is_redacted_durable_and_attempt_bound() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("terminal.sqlite");
        let mut conn = Connection::open(&path).unwrap();
        conn.execute_batch("CREATE TABLE workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            .unwrap();
        let request = json!({"question":"PRIVATE SYNTHETIC QUESTION"});
        let identity = json!({"operation":"answer","knowledge_id":"original","client_request_id":"fixed","admission_request_sha256":"frozen-digest"});
        admit(&conn, "fixed", &request).unwrap();
        record_terminal_failure(
            &mut conn,
            "fixed",
            "machine failure: MODEL_CALL_FAILED",
            &identity,
        )
        .unwrap();
        drop(conn);
        let mut conn = Connection::open(&path).unwrap();
        let raw: String = conn
            .query_row(
                "SELECT value FROM workspace_meta WHERE key=?1",
                [key("fixed")],
                |r| r.get(0),
            )
            .unwrap();
        let first: Value = serde_json::from_str(&raw).unwrap();
        let task = archeaxis_domain::machine::machine_task(
            &conn,
            first["terminal_task_id"].as_str().unwrap(),
        )
        .unwrap()
        .unwrap();
        assert_eq!(task.scope, "runtime.execution.failed");
        assert!(!task.conditions.contains("PRIVATE"));
        let doc: Value = serde_json::from_str(&task.conditions).unwrap();
        assert!(doc["usage"].is_null());
        assert_eq!(doc["provider_stop_state"], "UNKNOWN");
        admit(&conn, "fixed", &request).unwrap();
        record_terminal_failure(
            &mut conn,
            "fixed",
            "machine failure: MODEL_CALL_FAILED",
            &identity,
        )
        .unwrap();
        let raw: String = conn
            .query_row(
                "SELECT value FROM workspace_meta WHERE key=?1",
                [key("fixed")],
                |r| r.get(0),
            )
            .unwrap();
        let second: Value = serde_json::from_str(&raw).unwrap();
        assert_ne!(first["terminal_task_id"], second["terminal_task_id"]);
        assert_eq!(second["attempt"], 2);
        assert_eq!(
            archeaxis_domain::machine::machine_task(
                &conn,
                first["terminal_task_id"].as_str().unwrap()
            )
            .unwrap()
            .unwrap()
            .conditions,
            task.conditions
        );
    }
    #[test]
    fn failure_audit_write_failure_rolls_back_retry_release() {
        let mut conn = Connection::open_in_memory().unwrap();
        conn.execute_batch("CREATE TABLE workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE machine_tasks(task_id TEXT)").unwrap();
        let request = json!({"question":"synthetic"});
        admit(&conn, "fixed", &request).unwrap();
        assert!(
            record_terminal_failure(
                &mut conn,
                "fixed",
                "machine failure: MODEL_CALL_FAILED",
                &json!({"operation":"answer"})
            )
            .is_err()
        );
        assert!(admit(&conn, "fixed", &request).is_err());
        let raw: String = conn
            .query_row(
                "SELECT value FROM workspace_meta WHERE key=?1",
                [key("fixed")],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(
            serde_json::from_str::<Value>(&raw).unwrap()["state"],
            "IN_FLIGHT"
        );
    }
    #[test]
    fn reopened_unfinished_claim_blocks_repeat_but_known_failure_can_retry() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("claims.sqlite");
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch("CREATE TABLE workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            .unwrap();
        let request = json!({"model":"m1","question":"synthetic","max_tokens":2048});
        admit(&conn, "fixed", &request).unwrap();
        drop(conn);
        let conn = Connection::open(&path).unwrap();
        assert!(admit(&conn, "fixed", &request).is_err());
        known_failure(&conn, "fixed").unwrap();
        assert!(admit(&conn, "fixed", &json!({"model":"m2"})).is_err());
        admit(&conn, "fixed", &request).unwrap();
        assert!(admit(&conn, "fixed", &request).is_err());
        let stored: String = conn
            .query_row("SELECT value FROM workspace_meta", [], |r| r.get(0))
            .unwrap();
        assert!(!stored.contains("synthetic"));
    }

    #[test]
    fn unconfirmed_cleanup_keeps_barrier_after_reopen() {
        for error in [
            "machine worker cleanup incomplete",
            "machine answer task failed",
            "machine worker pipe drain unavailable",
            "unexpected future failure",
        ] {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("claims.sqlite");
            let conn = Connection::open(&path).unwrap();
            conn.execute_batch(
                "CREATE TABLE workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)",
            )
            .unwrap();
            let request = json!({"question":"synthetic"});
            admit(&conn, "fixed", &request).unwrap();
            record_failure(&conn, "fixed", error).unwrap();
            drop(conn);
            let conn = Connection::open(&path).unwrap();
            assert!(admit(&conn, "fixed", &request).is_err());
            let stored: String = conn
                .query_row("SELECT value FROM workspace_meta", [], |r| r.get(0))
                .unwrap();
            assert_eq!(
                serde_json::from_str::<Value>(&stored).unwrap()["state"],
                "IN_FLIGHT"
            );
        }
    }

    #[test]
    fn retry_budget_survives_reopen_and_never_resets() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("claims.sqlite");
        let request = json!({"question":"synthetic"});
        for attempt in 1..=MAX_ATTEMPTS {
            let conn = Connection::open(&path).unwrap();
            conn.execute_batch("CREATE TABLE IF NOT EXISTS workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)").unwrap();
            admit(&conn, "fixed", &request).unwrap();
            let stored: String = conn
                .query_row("SELECT value FROM workspace_meta", [], |r| r.get(0))
                .unwrap();
            assert_eq!(
                serde_json::from_str::<Value>(&stored).unwrap()["attempt"],
                attempt
            );
            record_failure(&conn, "fixed", "machine failure: MODEL_CALL_FAILED").unwrap();
        }
        let conn = Connection::open(&path).unwrap();
        assert!(admit(&conn, "fixed", &request).is_err());
    }

    #[test]
    fn legacy_unknown_attempt_count_never_gets_a_new_budget() {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch("CREATE TABLE workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            .unwrap();
        let request = json!({"question":"synthetic"});
        let legacy = json!({"schema":"archeaxis.machine-execution-claim/v1","state":"KNOWN_FAILURE","request_sha256":super::super::withheld::digest(&request.to_string())});
        conn.execute(
            "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
            rusqlite::params![key("fixed"), legacy.to_string()],
        )
        .unwrap();
        assert!(admit(&conn, "fixed", &request).is_err());
        let stored: String = conn
            .query_row("SELECT value FROM workspace_meta", [], |r| r.get(0))
            .unwrap();
        assert_eq!(serde_json::from_str::<Value>(&stored).unwrap(), legacy);
    }
}
