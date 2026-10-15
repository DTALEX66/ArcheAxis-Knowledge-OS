//! Scope-bounded observations; declaration/file presence never qualifies execution.
use serde::{Deserialize, Serialize};
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Status {
    Ready,
    NotReady,
    Unverified,
    Unknown,
    Expired,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observation {
    pub operation: String,
    pub implementation: String,
    pub dependencies: String,
    pub connection: String,
    pub qualification: String,
    pub permission: String,
    pub status: Status,
    pub reasons: Vec<String>,
    pub expires_at_ms: u64,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Snapshot {
    pub schema: String,
    pub scope: String,
    pub observed_at_ms: u64,
    pub expires_at_ms: u64,
    pub aggregate: Status,
    pub operations: Vec<Observation>,
    pub network_performed: bool,
    pub models_loaded: bool,
    pub execution_authorized: bool,
}
pub fn observe(
    operation: String,
    implemented: bool,
    dependencies: bool,
    permission: Option<bool>,
    expires_at_ms: u64,
) -> Observation {
    let mut reasons = vec![];
    if !implemented {
        reasons.push("OPERATION_NOT_REGISTERED".into());
    }
    if !dependencies {
        reasons.push("DEPENDENCY_MISSING".into());
    }
    if permission == Some(false) {
        reasons.push("CAPABILITY_DISABLED".into());
    }
    if permission.is_none() {
        reasons.push("PERMISSION_UNVERIFIED".into());
    }
    reasons.push("CONNECTION_NOT_PROBED".into());
    reasons.push("RUNTIME_QUALIFICATION_UNVERIFIED".into());
    Observation {
        operation,
        implementation: if implemented {
            "IMPLEMENTED"
        } else {
            "MISSING"
        }
        .into(),
        dependencies: if dependencies { "AVAILABLE" } else { "MISSING" }.into(),
        connection: "UNKNOWN".into(),
        qualification: "UNVERIFIED".into(),
        permission: match permission {
            Some(true) => "ENABLED",
            Some(false) => "DISABLED",
            None => "UNKNOWN",
        }
        .into(),
        status: if !implemented || !dependencies || permission == Some(false) {
            Status::NotReady
        } else if permission.is_none() {
            Status::Unknown
        } else {
            Status::Unverified
        },
        reasons,
        expires_at_ms,
    }
}
pub fn aggregate(rows: &[Observation], now: u64) -> Status {
    if rows.is_empty() {
        return Status::Unknown;
    }
    if rows
        .iter()
        .any(|r| now >= r.expires_at_ms || r.status == Status::Expired)
    {
        return Status::Expired;
    }
    if rows.iter().any(|r| r.status == Status::NotReady) {
        return Status::NotReady;
    }
    if rows.iter().any(|r| r.status == Status::Unknown) {
        return Status::Unknown;
    }
    if rows.iter().any(|r| r.status == Status::Unverified) {
        return Status::Unverified;
    }
    Status::Ready
}
pub fn snapshot(scope: String, now: u64, operations: Vec<Observation>) -> Snapshot {
    let expiry = operations
        .iter()
        .map(|r| r.expires_at_ms)
        .min()
        .unwrap_or(now);
    let overall = aggregate(&operations, now);
    Snapshot {
        schema: "archeaxis.operation-readiness/v1".into(),
        scope,
        observed_at_ms: now,
        expires_at_ms: expiry,
        aggregate: overall,
        operations,
        network_performed: false,
        models_loaded: false,
        execution_authorized: false,
    }
}
