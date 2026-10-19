//! BE10 本期 handoff 准备合同。只投影冻结引用，不传正文，不执行或接纳。
use crate::project_observer::{
    self as observer, ConsumerIdentity, ObjectReference, ProducerIdentity,
};
use serde::{Deserialize, Serialize};

pub const SCHEMA: &str = "archeaxis.project-handoff/v1";
pub const MAX_ITEMS: usize = 32;
pub const MAX_INTEGER: u64 = 9_007_199_254_740_991;

macro_rules! vocabulary {
    ($name:ident { $($variant:ident => $value:literal),+ $(,)? }) => {
        #[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
        pub enum $name { $(#[serde(rename = $value)] $variant),+ }
    };
}
vocabulary!(Authority { PreparationOnly => "PREPARATION_ONLY" });
vocabulary!(AuthorizationScope { ReferenceMetadataOnly => "REFERENCE_METADATA_ONLY" });
vocabulary!(Unverified { Unverified => "UNVERIFIED" });
vocabulary!(ExecutionAuthority { NotGranted => "NOT_GRANTED" });
vocabulary!(ReviewState { PendingHumanReview => "PENDING_HUMAN_REVIEW" });
vocabulary!(EvidenceSupport { NotAssessed => "NOT_ASSESSED" });
vocabulary!(ManifestIdentity { Unknown => "UNKNOWN" });
vocabulary!(ContributionPoint {
    FormatConversion => "format_conversion", Template => "template",
    LearningActivity => "learning_activity", GraphVisual => "graph_visual",
    ModelService => "model_service", ToolProtocol => "tool_protocol"
});
vocabulary!(ContextPurpose { Learning => "learning", Research => "research", Conversion => "conversion", Visualization => "visualization" });
vocabulary!(TaskGoal { PrepareLearningActivity => "prepare_learning_activity", PrepareResearchPlan => "prepare_research_plan", PrepareFormatConversion => "prepare_format_conversion", PrepareGraphView => "prepare_graph_view" });
vocabulary!(AssetFormat { Text => "text", Pdf => "pdf", Office => "office", Html => "html", Image => "image", Audio => "audio", Video => "video", Canvas => "canvas", Unknown => "unknown" });
vocabulary!(SourceRelationship { Original => "ORIGINAL", Derived => "DERIVED" });
vocabulary!(ProposalKind { Context => "context", TaskProposal => "task_proposal", AssetManifest => "asset_manifest", KnowledgeCandidate => "knowledge_candidate" });
vocabulary!(ReceiptState { Prepared => "PREPARED", Rejected => "REJECTED", Unknown => "UNKNOWN", Conflict => "CONFLICT" });
vocabulary!(ReceiptReason { None => "NONE", Unobserved => "UNOBSERVED", Timeout => "TIMEOUT", Disconnected => "DISCONNECTED", Expired => "EXPIRED", StaleReference => "STALE_REFERENCE", IdentityMismatch => "IDENTITY_MISMATCH", Unsupported => "UNSUPPORTED", IdempotencyConflict => "IDEMPOTENCY_CONFLICT" });

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Selection {
    WholeObject,
    TextRange {
        block_id: String,
        start_utf16: u64,
        end_utf16: u64,
    },
    PageRange {
        first_page: u64,
        last_page: u64,
    },
    TimeRange {
        start_ms: u64,
        end_ms: u64,
    },
}
impl Selection {
    fn valid(&self) -> bool {
        match self {
            Self::WholeObject => true,
            Self::TextRange {
                block_id,
                start_utf16,
                end_utf16,
            } => {
                observer::object_id(block_id)
                    && start_utf16 < end_utf16
                    && *end_utf16 <= MAX_INTEGER
            }
            Self::PageRange {
                first_page,
                last_page,
            } => *first_page > 0 && first_page <= last_page && *last_page <= MAX_INTEGER,
            Self::TimeRange { start_ms, end_ms } => start_ms < end_ms && *end_ms <= MAX_INTEGER,
        }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct SelectedReference {
    pub reference: ObjectReference,
    pub selection: Selection,
    pub selection_qualification: Unverified,
}
impl SelectedReference {
    fn valid(&self) -> bool {
        self.reference.valid() && self.selection.valid()
    }
}
/// 复用 HUB-003 六类贡献点及既有 CAP；未发布 manifest 不虚构已注册 identity。
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CapabilityLink {
    pub capability_id: String,
    pub contribution_point: ContributionPoint,
    pub manifest_identity: ManifestIdentity,
}
fn capability_id(value: &str) -> bool {
    matches!(
        value,
        "CAP-0010"
            | "CAP-0020"
            | "CAP-0030"
            | "CAP-0040"
            | "CAP-0050"
            | "CAP-0060"
            | "CAP-0070"
            | "CAP-0080"
            | "CAP-0090"
            | "CAP-0100"
            | "CAP-0110"
            | "CAP-0120"
            | "CAP-0130"
            | "CAP-0140"
            | "CAP-0150"
            | "CAP-0160"
    )
}
impl CapabilityLink {
    fn matches_goal(&self, goal: &TaskGoal) -> bool {
        capability_id(&self.capability_id)
            && match goal {
                TaskGoal::PrepareLearningActivity => {
                    self.capability_id == "CAP-0060"
                        && self.contribution_point == ContributionPoint::LearningActivity
                }
                TaskGoal::PrepareResearchPlan => {
                    self.capability_id == "CAP-0090"
                        && self.contribution_point == ContributionPoint::Template
                }
                TaskGoal::PrepareFormatConversion => {
                    self.capability_id == "CAP-0020"
                        && self.contribution_point == ContributionPoint::FormatConversion
                }
                TaskGoal::PrepareGraphView => {
                    self.capability_id == "CAP-0160"
                        && self.contribution_point == ContributionPoint::GraphVisual
                }
            }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(
    tag = "state",
    rename_all = "SCREAMING_SNAKE_CASE",
    deny_unknown_fields
)]
pub enum LossEvidence {
    Unknown,
    ReceiptReference { reference: ObjectReference },
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AssetEntry {
    pub reference: ObjectReference,
    pub source_reference: ObjectReference,
    pub relationship: SourceRelationship,
    pub format: AssetFormat,
    pub format_qualification: Unverified,
    pub loss: LossEvidence,
}
impl AssetEntry {
    fn valid(&self) -> bool {
        self.reference.valid()
            && self.source_reference.valid()
            && match self.relationship {
                SourceRelationship::Original => self.reference == self.source_reference,
                SourceRelationship::Derived => self.reference != self.source_reference,
            }
            && match &self.loss {
                LossEvidence::Unknown => true,
                LossEvidence::ReceiptReference { reference } => reference.valid(),
            }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ProposalReference {
    pub idempotency_key: String,
    pub proposal_sha256: String,
    pub kind: ProposalKind,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Payload {
    Context {
        source: SelectedReference,
        purpose: ContextPurpose,
        authorization_scope: AuthorizationScope,
    },
    TaskProposal {
        target: ObjectReference,
        context: Vec<SelectedReference>,
        goal: TaskGoal,
        capability: CapabilityLink,
        execution_authority: ExecutionAuthority,
    },
    AssetManifest {
        assets: Vec<AssetEntry>,
    },
    KnowledgeCandidate {
        candidate_id: String,
        candidate_revision: u64,
        claim_sha256: String,
        basis: ObjectReference,
        evidence: Vec<SelectedReference>,
        review_state: ReviewState,
        evidence_support: EvidenceSupport,
    },
    Receipt {
        proposal: ProposalReference,
        state: ReceiptState,
        reason: ReceiptReason,
    },
}
fn nonempty_bounded<T>(items: &[T]) -> bool {
    !items.is_empty() && items.len() <= MAX_ITEMS
}
impl Payload {
    pub fn proposal_kind(&self) -> Option<ProposalKind> {
        match self {
            Self::Context { .. } => Some(ProposalKind::Context),
            Self::TaskProposal { .. } => Some(ProposalKind::TaskProposal),
            Self::AssetManifest { .. } => Some(ProposalKind::AssetManifest),
            Self::KnowledgeCandidate { .. } => Some(ProposalKind::KnowledgeCandidate),
            Self::Receipt { .. } => None,
        }
    }
    pub fn references(&self) -> Vec<&ObjectReference> {
        match self {
            Self::Context { source, .. } => vec![&source.reference],
            Self::TaskProposal {
                target, context, ..
            } => std::iter::once(target)
                .chain(context.iter().map(|r| &r.reference))
                .collect(),
            Self::AssetManifest { assets } => assets
                .iter()
                .flat_map(|a| {
                    let mut refs = vec![&a.reference, &a.source_reference];
                    if let LossEvidence::ReceiptReference { reference } = &a.loss {
                        refs.push(reference);
                    }
                    refs
                })
                .collect(),
            Self::KnowledgeCandidate {
                basis, evidence, ..
            } => std::iter::once(basis)
                .chain(evidence.iter().map(|r| &r.reference))
                .collect(),
            Self::Receipt { .. } => vec![],
        }
    }
    fn valid(&self) -> bool {
        match self {
            Self::Context { source, .. } => source.valid(),
            Self::TaskProposal {
                target,
                context,
                goal,
                capability,
                ..
            } => {
                target.valid()
                    && nonempty_bounded(context)
                    && context.iter().all(SelectedReference::valid)
                    && capability.matches_goal(goal)
            }
            Self::AssetManifest { assets } => {
                nonempty_bounded(assets) && assets.iter().all(AssetEntry::valid) && {
                    let mut ids = std::collections::HashSet::new();
                    assets.iter().all(|a| ids.insert(&a.reference.document_id))
                }
            }
            Self::KnowledgeCandidate {
                candidate_id,
                candidate_revision,
                claim_sha256,
                basis,
                evidence,
                ..
            } => {
                observer::object_id(candidate_id)
                    && (1..=MAX_INTEGER).contains(candidate_revision)
                    && observer::hex(claim_sha256, 64)
                    && basis.valid()
                    && nonempty_bounded(evidence)
                    && evidence.iter().all(SelectedReference::valid)
            }
            Self::Receipt {
                proposal,
                state,
                reason,
            } => {
                observer::hex(&proposal.idempotency_key, 32)
                    && observer::hex(&proposal.proposal_sha256, 64)
                    && match state {
                        ReceiptState::Prepared => *reason == ReceiptReason::None,
                        ReceiptState::Unknown => matches!(
                            reason,
                            ReceiptReason::Unobserved
                                | ReceiptReason::Timeout
                                | ReceiptReason::Disconnected
                        ),
                        ReceiptState::Rejected => matches!(
                            reason,
                            ReceiptReason::Expired
                                | ReceiptReason::StaleReference
                                | ReceiptReason::IdentityMismatch
                                | ReceiptReason::Unsupported
                        ),
                        ReceiptState::Conflict => *reason == ReceiptReason::IdempotencyConflict,
                    }
            }
        }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Handoff {
    pub schema: String,
    pub protocol: String,
    pub idempotency_key: String,
    pub producer: ProducerIdentity,
    pub consumer: ConsumerIdentity,
    pub created_at_ms: u64,
    pub expires_at_ms: u64,
    pub authority: Authority,
    pub payload: Payload,
}
impl Handoff {
    pub fn valid(&self, now_ms: u64) -> bool {
        self.schema == SCHEMA
            && self.protocol == observer::PROTOCOL
            && observer::hex(&self.idempotency_key, 32)
            && self.producer.valid()
            && observer::hex(&self.consumer.instance_id, 32)
            && self.created_at_ms <= now_ms
            && now_ms <= MAX_INTEGER
            && self.expires_at_ms <= MAX_INTEGER
            && self.expires_at_ms > now_ms
            && self.expires_at_ms > self.created_at_ms
            && self.expires_at_ms - self.created_at_ms <= observer::FRESHNESS_MS
            && self.payload.valid()
            && match &self.payload {
                Payload::Receipt { proposal, .. } => {
                    proposal.idempotency_key != self.idempotency_key
                }
                _ => true,
            }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PrepareError {
    InvalidSnapshot,
    InvalidProposal,
    ReferenceNotCurrent,
    OriginalRequired,
    IdentityMismatch,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RetryClass {
    Equivalent,
    Conflict,
    Unrelated,
}
