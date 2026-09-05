//! ArcheAxis contracts: stable vocabulary shared by all vNext crates.
//!
//! Single source of truth is the machine-readable JSON Schema under
//! `packages/contracts/v1/` (assessment-vocabulary.schema.json and
//! job-status.schema.json). The constants below mirror the closed enums so
//! Rust code never hand-writes vocabulary strings; a unit test and the
//! `contracts-vnext` CI gate both fail on drift between this file and the
//! schemas. Enums serialize as strings and gain values only through a new
//! major contract version (packages/contracts/v1/compatibility-policy.md).

/// Canonical knowledge types (assessment-vocabulary `knowledge_type`).
pub const KNOWLEDGE_TYPES: &[&str] = &[
    "PERSONAL_DEFINITION", "NOTE", "OBSERVATION", "OPINION", "QUESTION",
    "HYPOTHESIS", "RUMOR_REPORT", "FORECAST", "FACTUAL_CLAIM",
];

/// Canonical review statuses (assessment-vocabulary `review_status`).
pub const STATUS_DRAFT: &str = "DRAFT";
pub const STATUS_MACHINE_CANDIDATE: &str = "MACHINE_CANDIDATE";
pub const STATUS_NEEDS_REVIEW: &str = "NEEDS_REVIEW";
pub const STATUS_USER_ACCEPTED: &str = "USER_ACCEPTED";
pub const STATUS_USER_REJECTED: &str = "USER_REJECTED";
pub const STATUS_SUPERSEDED: &str = "SUPERSEDED";

/// Canonical job lifecycle (job-status `job_status`).
pub const JOB_QUEUED: &str = "queued";
pub const JOB_RUNNING: &str = "running";
pub const JOB_SUCCEEDED: &str = "succeeded";
pub const JOB_FAILED: &str = "failed";
pub const JOB_REJECTED: &str = "rejected";
pub const JOB_CANCELLED: &str = "cancelled";

/// Research verdicts (job-status `research_verdict`).
pub const VERDICT_PASS: &str = "PASS";
pub const VERDICT_PARTIAL: &str = "PARTIAL";
pub const VERDICT_FAIL: &str = "FAIL";
pub const VERDICT_UNMEASURED: &str = "UNMEASURED";
pub const VERDICT_BLOCKED_CREDENTIALS: &str = "BLOCKED_CREDENTIALS";

#[cfg(test)]
mod tests {
    use super::*;

    const VOCAB_SCHEMA: &str =
        include_str!("../../../packages/contracts/v1/assessment-vocabulary.schema.json");
    const JOB_STATUS_SCHEMA: &str =
        include_str!("../../../packages/contracts/v1/job-status.schema.json");

    fn assert_all_present(constants: &[&str], schema: &str, context: &str) {
        for value in constants {
            assert!(
                schema.contains(&format!("\"{value}\"")),
                "{context}: {value} missing from the canonical schema"
            );
        }
    }

    #[test]
    fn vocabulary_matches_canonical_schemas() {
        assert_all_present(KNOWLEDGE_TYPES, VOCAB_SCHEMA, "knowledge_type");
        assert_all_present(
            &[
                STATUS_DRAFT,
                STATUS_MACHINE_CANDIDATE,
                STATUS_NEEDS_REVIEW,
                STATUS_USER_ACCEPTED,
                STATUS_USER_REJECTED,
                STATUS_SUPERSEDED,
            ],
            VOCAB_SCHEMA,
            "review_status",
        );
        assert_all_present(
            &[
                JOB_QUEUED, JOB_RUNNING, JOB_SUCCEEDED, JOB_FAILED, JOB_REJECTED, JOB_CANCELLED,
            ],
            JOB_STATUS_SCHEMA,
            "job_status",
        );
        assert_all_present(
            &[
                VERDICT_PASS,
                VERDICT_PARTIAL,
                VERDICT_FAIL,
                VERDICT_UNMEASURED,
                VERDICT_BLOCKED_CREDENTIALS,
            ],
            JOB_STATUS_SCHEMA,
            "research_verdict",
        );
    }
}
