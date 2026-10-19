//! 有限只读互联合同。凭据不属于响应 DTO；对象引用不授予执行或知识接纳。
use serde::{Deserialize, Serialize};

pub const PROTOCOL: &str = "archeaxis.project-observer/v1";
pub const SCHEMA: &str = "archeaxis.project-observer-response/v1";
pub const MAX_OBJECTS: usize = 32;
pub const MAX_RESPONSE_BYTES: usize = 65_536;
pub const FRESHNESS_MS: u64 = 30_000;

pub fn hex(value: &str, n: usize) -> bool {
    value.len() == n
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
pub fn object_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum ConsumerNamespace {
    WorkLab,
    DesignLab,
}
impl ConsumerNamespace {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::WorkLab => "work-lab",
            Self::DesignLab => "design-lab",
        }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ConsumerIdentity {
    pub namespace: ConsumerNamespace,
    pub instance_id: String,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ProducerIdentity {
    pub namespace: String,
    pub workspace_id: String,
    pub restore_epoch: String,
}
impl ProducerIdentity {
    pub fn valid(&self) -> bool {
        self.namespace == "archeaxis"
            && hex(&self.workspace_id, 32)
            && (self.restore_epoch == "initial" || hex(&self.restore_epoch, 32))
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ObjectReference {
    pub document_id: String,
    pub version: u64,
    pub content_sha256: String,
}
impl ObjectReference {
    pub fn valid(&self) -> bool {
        object_id(&self.document_id)
            && (1..=i64::MAX as u64).contains(&self.version)
            && hex(&self.content_sha256, 64)
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ObjectState {
    Current,
    Stale,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub enum NavigationState {
    #[serde(rename = "UNAVAILABLE")]
    Unavailable,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Payload {
    Handshake {
        operations: Vec<String>,
        authority: String,
        grants_execution: bool,
        grants_knowledge_acceptance: bool,
    },
    Objects {
        objects: Vec<ObjectReference>,
        navigation: NavigationState,
    },
    ObjectStatus {
        reference: ObjectReference,
        state: ObjectState,
        navigation: NavigationState,
    },
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ReadResponse {
    pub schema: String,
    pub protocol: String,
    pub producer: ProducerIdentity,
    pub consumer: ConsumerIdentity,
    pub checked_at_ms: u64,
    pub expires_at_ms: u64,
    pub payload: Payload,
}
impl ReadResponse {
    pub fn valid(&self, now_ms: u64) -> bool {
        self.schema == SCHEMA
            && self.protocol == PROTOCOL
            && self.producer.valid()
            && hex(&self.consumer.instance_id, 32)
            && self.checked_at_ms <= now_ms
            && self.expires_at_ms > now_ms
            && self.expires_at_ms > self.checked_at_ms
            && self.expires_at_ms - self.checked_at_ms <= FRESHNESS_MS
            && match &self.payload {
                Payload::Handshake {
                    operations,
                    authority,
                    grants_execution,
                    grants_knowledge_acceptance,
                } => {
                    operations == &["handshake", "objects.read", "object.status"]
                        && authority == "REFERENCE_ONLY"
                        && !grants_execution
                        && !grants_knowledge_acceptance
                }
                Payload::Objects { objects, .. } => {
                    objects.len() <= MAX_OBJECTS && objects.iter().all(ObjectReference::valid) && {
                        let mut ids = std::collections::HashSet::new();
                        objects.iter().all(|o| ids.insert(&o.document_id))
                    }
                }
                Payload::ObjectStatus { reference, .. } => reference.valid(),
            }
    }
}
