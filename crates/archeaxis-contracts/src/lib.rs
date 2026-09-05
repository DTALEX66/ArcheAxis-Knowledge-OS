//! ArcheAxis contracts: stable vocabulary shared by all vNext crates.
//! Zero-dependency constants — the single source of truth for knowledge types
//! and review statuses (see packages/contracts/v1 for the machine-readable
//! JSON Schema, added in a later slice).

pub const KNOWLEDGE_TYPES: &[&str] = &[
    "PERSONAL_DEFINITION", "NOTE", "OBSERVATION", "OPINION", "QUESTION",
    "HYPOTHESIS", "RUMOR_REPORT", "FORECAST", "FACTUAL_CLAIM",
];

pub const STATUS_CANDIDATE: &str = "candidate";
pub const STATUS_ACCEPTED: &str = "accepted";
pub const STATUS_REJECTED: &str = "rejected";
pub const STATUS_DEPRECATED: &str = "deprecated";
