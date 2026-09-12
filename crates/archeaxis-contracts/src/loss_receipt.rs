//! Loss accounting at the actual Core boundary. Unknown fields are errors,
//! not permission to discard worker evidence. Schema: loss-receipt.schema.json.
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct LossReceipt {
    pub engine: String,
    pub engine_version: String,
    pub params: serde_json::Value,
    #[serde(deserialize_with = "required_note")]
    pub loss_note: Option<String>,
    #[serde(default, deserialize_with = "present", skip_serializing_if = "Option::is_none")]
    pub losses: Option<Vec<String>>,
    #[serde(default, deserialize_with = "count", skip_serializing_if = "Option::is_none")]
    pub covered: Option<u64>,
    #[serde(default, deserialize_with = "count", skip_serializing_if = "Option::is_none")]
    pub total: Option<u64>,
    #[serde(default, deserialize_with = "present", skip_serializing_if = "Option::is_none")]
    pub coverage: Option<f64>,
}

fn present<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where D: serde::Deserializer<'de>, T: Deserialize<'de> {
    // Absence is unmeasured, explicit null is invalid for these schema fields.
    T::deserialize(deserializer).map(Some)
}

fn required_note<'de, D>(deserializer: D) -> Result<Option<String>, D::Error>
where D: serde::Deserializer<'de> {
    // loss_note is required but nullable; serde's implicit Option default would
    // otherwise accept a missing property and change the worker's wire shape.
    Option::<String>::deserialize(deserializer)
}

fn count<'de, D>(deserializer: D) -> Result<Option<u64>, D::Error>
where D: serde::Deserializer<'de> {
    // JSON Schema integers are mathematical integers, including 1.0 and 1e0.
    // Do not cast arbitrary floats (rounding/negative/null/bool are not counts).
    let value = serde_json::Value::deserialize(deserializer)?;
    let number = value.as_f64().filter(|value| value.is_finite()
        && (0.0..=9_007_199_254_740_991.0).contains(value) && value.fract() == 0.0)
        .ok_or_else(|| serde::de::Error::custom("count must be an exact nonnegative JSON integer <= 2^53-1"))?;
    Ok(Some(number as u64))
}

impl LossReceipt {
    /// Counts use the exact-integer range shared by JSON consumers. Coverage
    /// is a ratio of declared units, NOT a claim about extraction accuracy.
    /// Missing counts mean unmeasured; the legacy four-field receipt remains
    /// byte-shape compatible for durable idempotency of existing jobs.
    pub fn validate(&self) -> Result<(), &'static str> {
        if self.engine.trim().is_empty() || self.engine_version.trim().is_empty() {
            return Err("receipt engine and version must be nonempty");
        }
        if !self.params.is_object() { return Err("receipt params must be an object"); }
        if self.losses.as_ref().is_some_and(|items| items.iter().any(|item| item.trim().is_empty())) {
            return Err("loss entries must be nonempty");
        }
        match (self.covered, self.total, self.coverage) {
            (None, None, None) => Ok(()),
            (Some(covered), Some(total), Some(ratio)) => {
                if covered > total || total > 9_007_199_254_740_991 {
                    return Err("coverage counts are inconsistent or outside exact JSON integer range");
                }
                let expected = if total == 0 { 1.0 } else { covered as f64 / total as f64 };
                if !ratio.is_finite() || !(0.0..=1.0).contains(&ratio) || (ratio - expected).abs() > 1e-12 {
                    return Err("coverage must equal covered/total (zero total is 1)");
                }
                Ok(())
            }
            _ => Err("covered, total and coverage must be supplied together"),
        }
    }
}
