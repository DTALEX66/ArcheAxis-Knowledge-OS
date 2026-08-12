use serde::Deserialize;
use std::fmt::Write;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ReadinessPayload {
    pub schema_version: String,
    pub product: String,
    pub workspace: String,
}

pub fn launch_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|error| format!("launch token generation failed: {error}"))?;
    let mut token = String::with_capacity(64);
    for byte in bytes {
        write!(&mut token, "{byte:02x}").map_err(|error| error.to_string())?;
    }
    Ok(token)
}

pub fn readiness_payload_valid(body: &str) -> bool {
    let Ok(payload) = serde_json::from_str::<ReadinessPayload>(body) else {
        return false;
    };
    payload.schema_version == "v1"
        && payload.product == "ArcheAxis Learning Workspace"
        && payload.workspace == "Human–AI Learning Workspace"
}

#[cfg(test)]
mod tests {
    use super::{launch_token, readiness_payload_valid};

    #[test]
    fn launch_tokens_are_strong_hex_and_unique() {
        let first = launch_token().expect("first token");
        let second = launch_token().expect("second token");
        assert_eq!(first.len(), 64);
        assert!(first.bytes().all(|byte| byte.is_ascii_hexdigit()));
        assert_ne!(first, second);
    }

    #[test]
    fn readiness_requires_the_exact_product_identity() {
        assert!(readiness_payload_valid(
            r#"{"schema_version":"v1","product":"ArcheAxis Learning Workspace","workspace":"Human–AI Learning Workspace"}"#
        ));
        assert!(!readiness_payload_valid(
            r#"{"schema_version":"v2","product":"ArcheAxis OS","workspace":"Human–AI Learning Workspace"}"#
        ));
        assert!(!readiness_payload_valid(
            r#"{"schema_version":"v1","product":"ArcheAxis OS","workspace":"Human–AI Learning Workspace"}"#
        ));
        assert!(!readiness_payload_valid(
            r#"{"schema_version":"v1","product":"Another Service","workspace":"Human–AI Learning Workspace"}"#
        ));
        assert!(!readiness_payload_valid("not-json"));
    }
}
