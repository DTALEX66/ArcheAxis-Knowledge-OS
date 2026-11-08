//! Bounded, text-free observations from the declared local-model worker.
use archeaxis_domain::openmaic_outline::OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA;
use serde_json::{Value, json};

pub(super) fn project(document: &Value) -> Option<Value> {
    if document["schema"] != OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA
        || document["network_scope"] != "LOOPBACK_LOCAL_MODEL_ONLY"
    {
        return None;
    }
    let bounded = |value: &Value| value.as_u64().filter(|number| *number <= u32::MAX.into());
    let status = document["diagnostic"]["http_status"]
        .as_u64()
        .filter(|status| (100..=599).contains(status));
    Some(json!({
        "scope":"LOCAL_MODEL_WORKER_REPORTED",
        "elapsed_ms":bounded(&document["elapsed_ms"]),
        "network_performed":document["network_performed"].as_bool(),
        "http_status":status,
        "provider_prompt_tokens":bounded(&document["diagnostic"]["n_prompt_tokens"]),
        "provider_context_tokens":bounded(&document["diagnostic"]["n_ctx"]),
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn projects_only_bounded_numbers_and_never_provider_text() {
        let document = json!({"schema":OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA,
            "network_scope":"LOOPBACK_LOCAL_MODEL_ONLY", "network_performed":true,
            "elapsed_ms":1234,"diagnostic":{"http_status":400,"n_prompt_tokens":9496,
            "n_ctx":8192,"message":"SYNTHETIC_PRIVATE_BODY"}});
        let observation = project(&document).unwrap();
        assert_eq!(observation["http_status"], 400);
        assert_eq!(observation["provider_prompt_tokens"], 9496);
        assert_eq!(observation["provider_context_tokens"], 8192);
        assert_eq!(observation["elapsed_ms"], 1234);
        assert_eq!(observation["network_performed"], true);
        assert!(!observation.to_string().contains("SYNTHETIC_PRIVATE_BODY"));

        let invalid = json!({"schema":OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA,
            "network_scope":"LOOPBACK_LOCAL_MODEL_ONLY", "network_performed":"SYNTHETIC_PRIVATE",
            "elapsed_ms":u64::MAX,"diagnostic":{"http_status":900,"n_prompt_tokens":-1,
            "n_ctx":"SYNTHETIC_PRIVATE"}});
        let observation = project(&invalid).unwrap();
        for field in [
            "http_status",
            "provider_prompt_tokens",
            "provider_context_tokens",
            "elapsed_ms",
            "network_performed",
        ] {
            assert!(observation[field].is_null(), "{field}");
        }
        assert!(!observation.to_string().contains("SYNTHETIC_PRIVATE"));
        assert!(project(&json!({"schema":"other"})).is_none());
        assert!(
            project(&json!({"schema":OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA,
            "network_scope":"EXTERNAL"}))
            .is_none()
        );

        let timeout = json!({"schema":OPENMAIC_OUTLINE_MODEL_REPLY_SCHEMA,
            "network_scope":"LOOPBACK_LOCAL_MODEL_ONLY","network_performed":null,
            "elapsed_ms":110000,"diagnostic":{"error_type":"TimeoutError"}});
        let observation = project(&timeout).unwrap();
        assert_eq!(observation["elapsed_ms"], 110000);
        assert!(observation["network_performed"].is_null());
    }
}
