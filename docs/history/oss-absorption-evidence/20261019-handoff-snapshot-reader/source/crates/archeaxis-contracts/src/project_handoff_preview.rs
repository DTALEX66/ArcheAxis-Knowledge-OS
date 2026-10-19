//! 本地human只读预览；外部metadata声明不成为认证、投递、执行或接纳资格。
use crate::project_handoff::{AuthorizationScope, Handoff, Payload, Unverified};
use crate::project_observer::{self, NavigationState};
use serde::{Deserialize, Serialize};

/// 正文仅供本机human阅读；它不是Observer输出，也不是提案授予的新权限。
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Snapshot {
    pub schema: String,
    pub checked_at_ms: u64,
    pub expires_at_ms: u64,
    pub proposal_sha256: String,
    pub producer: project_observer::ProducerIdentity,
    pub reference: project_observer::ObjectReference,
    pub reference_state: ReferenceState,
    pub source_authentication: Unverified,
    pub selection_qualification: Unverified,
    pub scope: SnapshotScope,
    pub editor_json: serde_json::Value,
    pub grants_execution: bool,
    pub grants_knowledge_acceptance: bool,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub enum SnapshotScope {
    #[serde(rename = "LOCAL_HUMAN_READ_ONLY")]
    LocalHumanReadOnly,
}
pub const SNAPSHOT_SCHEMA: &str = "archeaxis.project-handoff-snapshot/v1";
impl Snapshot {
    pub fn valid(&self, now_ms: u64) -> bool {
        self.schema == SNAPSHOT_SCHEMA
            && self.producer.valid()
            && self.reference.valid()
            && project_observer::hex(&self.proposal_sha256, 64)
            && self.checked_at_ms <= now_ms
            && self.expires_at_ms > now_ms
            && self.expires_at_ms.saturating_sub(self.checked_at_ms)
                <= project_observer::FRESHNESS_MS
            && self.reference_state != ReferenceState::NotFound
            && self.editor_json.is_object()
            && self.editor_json["type"] == "doc"
            && !self.grants_execution
            && !self.grants_knowledge_acceptance
    }
}

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
    use super::{Preview, Snapshot};
    #[test]
    fn shared_snapshot_cases_preserve_strict_local_read_contract() {
        let cases: serde_json::Value = serde_json::from_str(include_str!(
            "../../../packages/contracts/v2/project-handoff-snapshot.cases.json"
        ))
        .unwrap();
        for case in cases.as_array().unwrap() {
            let accepted = serde_json::from_value::<Snapshot>(case["value"].clone())
                .is_ok_and(|value| value.valid(case["now_ms"].as_u64().unwrap()));
            assert_eq!(
                accepted,
                case["runtime_valid"].as_bool().unwrap(),
                "{}",
                case["name"]
            );
        }
    }
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
