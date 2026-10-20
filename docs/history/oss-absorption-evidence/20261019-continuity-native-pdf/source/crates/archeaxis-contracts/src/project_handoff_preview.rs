//! 本地human只读预览；外部metadata声明不成为认证、投递、执行或接纳资格。
use crate::project_handoff::{AuthorizationScope, Handoff, Payload, Unverified};
use crate::project_observer::{self, NavigationState};
use serde::{Deserialize, Serialize};

pub const SCHEMA: &str = "archeaxis.project-handoff-preview/v1";
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ReferenceState {
    Current,
    Stale,
    NotFound,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Preview {
    pub schema: String,
    pub checked_at_ms: u64,
    pub expires_at_ms: u64,
    pub proposal: Handoff,
    pub proposal_sha256: String,
    pub reference_state: ReferenceState,
    pub source_authentication: Unverified,
    pub authority: AuthorizationScope,
    pub navigation: NavigationState,
    pub grants_execution: bool,
    pub grants_knowledge_acceptance: bool,
}
impl Preview {
    pub fn valid(&self, now_ms: u64) -> bool {
        self.schema == SCHEMA
            && self.proposal.valid(now_ms)
            && matches!(self.proposal.payload, Payload::Context { .. })
            && project_observer::hex(&self.proposal_sha256, 64)
            && self.checked_at_ms >= self.proposal.created_at_ms
            && self.checked_at_ms <= now_ms
            && self.expires_at_ms > now_ms
            && self.expires_at_ms <= self.proposal.expires_at_ms
            && self.expires_at_ms - self.checked_at_ms <= project_observer::FRESHNESS_MS
            && !self.grants_execution
            && !self.grants_knowledge_acceptance
    }
}

#[cfg(test)]
mod tests {
    use super::Preview;
    #[test]
    fn shared_preview_cases_decode_and_validate_real_dto() {
        let cases: serde_json::Value = serde_json::from_str(include_str!(
            "../../../packages/contracts/v2/project-handoff-preview.cases.json"
        ))
        .unwrap();
        for case in cases.as_array().unwrap() {
            let accepted = serde_json::from_value::<Preview>(case["value"].clone())
                .is_ok_and(|value| value.valid(case["now_ms"].as_u64().unwrap()));
            assert_eq!(
                accepted,
                case["runtime_valid"].as_bool().unwrap(),
                "{}",
                case["name"]
            );
        }
    }
}
