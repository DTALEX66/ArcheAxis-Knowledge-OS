//! A redacted, request-bound report of a precise restore fence rejection before inference.
//! NOT_EXECUTED covers this invocation only; it never erases an earlier execution identity.
use super::{MachineAnswerBody, RetestBody, withheld};
use archeaxis_domain::context_grant::Consumption;
use rusqlite::Connection;
use serde_json::{Value, json};

pub(super) fn answer_request(body: &MachineAnswerBody) -> Value {
    json!({"operation":"answer","request":{
        "knowledge_id":body.knowledge_id,"question":body.question,
        "max_tokens":body.max_tokens.unwrap_or(2048),"timeout_s":body.timeout_s.unwrap_or(120),
        "context_grant":body.context_grant,"asset_context_grant":body.asset_context_grant,
        "client_request_id":body.client_request_id,"retest_of":null}})
}

pub(super) fn retest_request(body: &RetestBody) -> Value {
    json!({"operation":"retest","request":{
        "knowledge_id":body.knowledge_id,"question":body.question,
        "max_tokens":body.max_tokens.unwrap_or(2048),"timeout_s":body.timeout_s.unwrap_or(120),
        "context_grant":body.context_grant,"asset_context_grant":body.asset_context_grant,
        "client_request_id":null,"retest_of":body.retest_of}})
}
pub(super) fn inspect(
    conn: &Connection,
    grant: Option<&Consumption>,
    request: &Value,
) -> rusqlite::Result<Option<Value>> {
    let Some(grant) = grant else {
        return Ok(None);
    };
    if grant.document_id.is_empty()
        || grant.document_id.len() > 256
        || grant.version < 1
        || grant.content_sha256.len() != 64
        || !grant
            .content_sha256
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Ok(None);
    }
    if !archeaxis_store_sqlite::authorization_fence::grant_is_fenced(conn, &grant.document_id)? {
        return Ok(None);
    }
    // serde_json's default sorted map serializes the normalized, finite request deterministically.
    Ok(Some(
        json!({"schema":"archeaxis.context-admission-refusal/v1",
        "reason_code":"RESTORED_GRANT_FENCED","execution_state":"NOT_EXECUTED",
        "execution_scope":"CURRENT_INVOCATION","prior_request_execution":"UNVERIFIED",
        "answer_published":false,"operation":request["operation"],
        "knowledge_id":request["request"]["knowledge_id"],
        "client_request_id":request["request"]["client_request_id"],
        "retest_of":request["request"]["retest_of"],
        "request_sha256":withheld::digest(&request.to_string()),
        "grant":{"document_id":grant.document_id,"version":grant.version,"content_sha256":grant.content_sha256}}),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finite_request_digest_binds_operation_defaults_purpose_and_assets() {
        let body: MachineAnswerBody = serde_json::from_value(json!({
            "knowledge_id":"k","question":"question","client_request_id":"client",
            "context_grant":{"document_id":"g","version":1,"content_sha256":"a".repeat(64),"purpose":"purpose"}
        })).unwrap();
        let normalized = answer_request(&body);
        assert_eq!(normalized["request"]["timeout_s"], 120);
        assert_eq!(normalized["request"]["max_tokens"], 2048);
        assert_eq!(normalized["request"]["asset_context_grant"], Value::Null);
        let digest = withheld::digest(&normalized.to_string());
        for pointer in [
            "/request/question",
            "/request/context_grant/purpose",
            "/request/asset_context_grant",
            "/operation",
        ] {
            let mut changed = normalized.clone();
            *changed.pointer_mut(pointer).unwrap() = json!("different");
            assert_ne!(withheld::digest(&changed.to_string()), digest);
        }
        let retest: RetestBody = serde_json::from_value(
            json!({"knowledge_id":"k","question":"question","retest_of":"failed"}),
        )
        .unwrap();
        assert_eq!(
            retest_request(&retest)["request"]["client_request_id"],
            Value::Null
        );
        assert_ne!(
            withheld::digest(&retest_request(&retest).to_string()),
            digest
        );
    }
}
