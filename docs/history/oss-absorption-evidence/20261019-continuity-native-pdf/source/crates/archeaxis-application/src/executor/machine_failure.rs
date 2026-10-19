//! Bounded measurements from an unsuccessful worker, never model text or stderr.
use serde_json::{Map, Value};
use std::time::{Duration, Instant};

// 小于一秒仍交给Core硬时限；等于/超过截止时刻不得启动。
pub(super) fn remaining_worker_timeout(now: Instant, deadline: Instant) -> Option<u64> {
    (now < deadline).then(|| deadline.duration_since(now).as_secs().max(1))
}

pub(super) fn accept_success(
    value: Value,
    model: Option<&str>,
    max_tokens: u64,
    started: Instant,
    timeout: Duration,
    now: Instant,
) -> Result<Value, MachineFailure> {
    if now >= started + timeout {
        return Err(MachineFailure::timed_out(
            model,
            max_tokens,
            timeout,
            now.saturating_duration_since(started),
        ));
    }
    if !value.is_object()
        || !value["answer"]
            .as_str()
            .is_some_and(|s| !s.trim().is_empty())
    {
        return Err("machine worker returned no candidate answer".into());
    }
    if model.is_some_and(|selected| {
        value["requested_model"].as_str() != Some(selected)
            || value["model"].as_str() != Some(selected)
    }) {
        return Err("machine worker model selection mismatch".into());
    }
    Ok(value)
}

#[cfg(test)]
mod deadline_tests {
    use super::*;

    #[test]
    fn expired_worker_is_not_admitted_and_remaining_budget_is_bounded() {
        let deadline = Instant::now() + Duration::from_secs(10);
        assert_eq!(remaining_worker_timeout(deadline, deadline), None);
        assert_eq!(
            remaining_worker_timeout(deadline + Duration::from_nanos(1), deadline),
            None
        );
        assert_eq!(
            remaining_worker_timeout(deadline - Duration::from_nanos(1), deadline),
            Some(1)
        );
        assert_eq!(
            remaining_worker_timeout(deadline - Duration::from_millis(2999), deadline),
            Some(2)
        );
    }

    #[test]
    fn complete_success_at_or_after_deadline_is_rejected() {
        let started = Instant::now();
        let timeout = Duration::from_secs(5);
        let deadline = started + timeout;
        let value =
            serde_json::json!({"answer": "synthetic answer", "requested_model": "m", "model": "m"});
        assert!(
            accept_success(
                value.clone(),
                Some("m"),
                128,
                started,
                timeout,
                deadline - Duration::from_nanos(1)
            )
            .is_ok()
        );
        for now in [deadline, deadline + Duration::from_nanos(1)] {
            let error =
                accept_success(value.clone(), Some("m"), 128, started, timeout, now).unwrap_err();
            assert_eq!(error.reason_code(), "WORKER_TIMEOUT");
            assert_eq!(error.diagnostics().unwrap()["error_type"], "TimeoutError");
            assert_eq!(
                error.diagnostics().unwrap()["request_stage"],
                "worker_deadline"
            );
            assert!(!format!("{error:?}").contains("synthetic answer"));
        }
    }
}

#[derive(Clone, Debug)]
pub struct MachineFailure {
    message: String,
    diagnostics: Option<Value>,
}

impl MachineFailure {
    pub(super) fn timed_out(
        requested_model: Option<&str>,
        max_tokens: u64,
        timeout: std::time::Duration,
        elapsed: std::time::Duration,
    ) -> Self {
        // Core测量，不捏造worker输出、模型身份、用量或服务端停止状态。
        Self {
            message: "machine worker timed out".into(),
            diagnostics: sanitize(&serde_json::json!({
                "requested_model": requested_model,
                "max_tokens": max_tokens,
                "timeout_s": timeout.as_secs(),
                "elapsed_s": elapsed.as_secs_f64(),
                "request_stage": "worker_deadline",
                "error_type": "TimeoutError"
            })),
        }
    }
    pub fn message(&self) -> &str {
        &self.message
    }
    pub fn diagnostics(&self) -> Option<&Value> {
        self.diagnostics.as_ref()
    }
    pub fn reason_code(&self) -> &'static str {
        match self.message() {
            "machine failure: MODEL_CALL_FAILED" => "MODEL_CALL_FAILED",
            "machine failure: MODEL_CALL_TIMEOUT" => "MODEL_CALL_TIMEOUT",
            "machine failure: NO_FINAL_ANSWER" => "NO_FINAL_ANSWER",
            "machine failure: EMPTY_ANSWER" | "machine worker returned no candidate answer" => {
                "EMPTY_ANSWER"
            }
            "machine worker timed out" => "WORKER_TIMEOUT",
            "machine worker output exceeds bound" => "OUTPUT_LIMIT",
            "machine worker returned invalid JSON" => "INVALID_OUTPUT",
            "machine worker pipe drain unavailable" => "PIPE_DRAIN_FAILED",
            _ => "WORKER_FAILED",
        }
    }
    pub(super) fn from_worker(bytes: &[u8]) -> Self {
        let value = serde_json::from_slice::<Value>(bytes).ok();
        let valid = value
            .as_ref()
            .filter(|v| v["schema"] == "archeaxis.machine-worker-failure/v1");
        let code = valid.and_then(|v| v["reason_code"].as_str()).filter(|c| {
            matches!(
                *c,
                "MODEL_CALL_FAILED" | "MODEL_CALL_TIMEOUT" | "NO_FINAL_ANSWER" | "EMPTY_ANSWER"
            )
        });
        Self {
            message: format!("machine failure: {}", code.unwrap_or("WORKER_FAILED")),
            diagnostics: code
                .and_then(|_| valid)
                .and_then(|v| sanitize(&v["diagnostics"])),
        }
    }
}
impl From<String> for MachineFailure {
    fn from(message: String) -> Self {
        Self {
            message,
            diagnostics: None,
        }
    }
}
impl From<&str> for MachineFailure {
    fn from(message: &str) -> Self {
        message.to_owned().into()
    }
}
impl std::fmt::Display for MachineFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.message())
    }
}
impl std::error::Error for MachineFailure {}

fn safe_integer(v: &Value) -> bool {
    v.as_u64().is_some_and(|n| n <= 9_007_199_254_740_991)
}
fn sanitize(raw: &Value) -> Option<Value> {
    let raw = raw.as_object()?;
    let mut out = Map::new();
    for key in ["requested_model", "observed_model"] {
        if let Some(v) = raw.get(key) {
            if v.is_null()
                || v.as_str().is_some_and(|s| {
                    !s.is_empty()
                        && s.len() <= 256
                        && s.bytes()
                            .all(|c| c.is_ascii_alphanumeric() || b"_.:/@+-".contains(&c))
                })
            {
                out.insert(key.into(), v.clone());
            }
        }
    }
    for (key, choices) in [
        (
            "finish_reason",
            &[
                "stop",
                "length",
                "tool_calls",
                "function_call",
                "content_filter",
                "error",
            ][..],
        ),
        (
            "answer_source",
            &["content", "reasoning_content", "response", "none"][..],
        ),
        (
            "request_stage",
            &[
                "service_discovery",
                "model_request",
                "response_deadline",
                "worker_deadline",
            ][..],
        ),
        (
            "request_phase",
            &[
                "http_open",
                "body_read",
                "json_parse",
                "response_validation",
            ][..],
        ),
        (
            "error_type",
            &[
                "HTTPError",
                "URLError",
                "TimeoutError",
                "ConnectionError",
                "OSError",
                "ValueError",
                "TypeError",
                "KeyError",
                "IndexError",
                "JSONDecodeError",
            ][..],
        ),
    ] {
        if let Some(v) = raw
            .get(key)
            .filter(|v| v.as_str().is_some_and(|s| choices.contains(&s)))
        {
            out.insert(key.into(), v.clone());
        }
    }
    for key in ["max_tokens", "timeout_s"] {
        if let Some(v) = raw
            .get(key)
            .filter(|v| safe_integer(v) && v.as_u64() != Some(0))
        {
            out.insert(key.into(), v.clone());
        }
    }
    for key in [
        "prompt_utf8_bytes",
        "serialized_request_bytes",
        "response_bytes",
    ] {
        if let Some(v) = raw.get(key).filter(|v| safe_integer(v)) {
            out.insert(key.into(), v.clone());
        }
    }
    for key in [
        "elapsed_s",
        "discovery_elapsed_s",
        "http_open_elapsed_s",
        "body_read_elapsed_s",
        "json_parse_elapsed_s",
    ] {
        if let Some(v) = raw.get(key).filter(|v| {
            v.as_f64()
                .is_some_and(|n| n.is_finite() && (0.0..=9_007_199_254_740_991.0).contains(&n))
        }) {
            out.insert(key.into(), v.clone());
        }
    }
    if let Some(v) = raw
        .get("http_status")
        .filter(|v| v.as_u64().is_some_and(|n| (100..=599).contains(&n)))
    {
        out.insert("http_status".into(), v.clone());
    }
    if let Some(usage) = raw.get("usage").and_then(Value::as_object) {
        let usage: Map<String, Value> = ["input_tokens", "output_tokens", "total_tokens"]
            .into_iter()
            .filter_map(|k| {
                usage
                    .get(k)
                    .filter(|v| safe_integer(v))
                    .map(|v| (k.into(), v.clone()))
            })
            .collect();
        if !usage.is_empty() {
            out.insert("usage".into(), Value::Object(usage));
        }
    }
    (!out.is_empty()).then_some(Value::Object(out))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn timeout_keeps_only_finite_stage_measurements() {
        let raw = serde_json::json!({"schema":"archeaxis.machine-worker-failure/v1","reason_code":"MODEL_CALL_TIMEOUT","diagnostics":{"request_stage":"model_request","discovery_elapsed_s":0.25,"elapsed_s":5.0,"error_type":"TimeoutError","answer":"PRIVATE"}});
        let error = MachineFailure::from_worker(&serde_json::to_vec(&raw).unwrap());
        assert_eq!(error.reason_code(), "MODEL_CALL_TIMEOUT");
        assert_eq!(
            error.diagnostics(),
            Some(
                &serde_json::json!({"request_stage":"model_request","discovery_elapsed_s":0.25,"elapsed_s":5.0,"error_type":"TimeoutError"})
            )
        );
        let mut invalid = raw;
        invalid["diagnostics"] =
            serde_json::json!({"request_stage":"PRIVATE","discovery_elapsed_s":true});
        assert!(
            MachineFailure::from_worker(&serde_json::to_vec(&invalid).unwrap())
                .diagnostics()
                .is_none()
        );
    }
    #[test]
    fn rejects_unknown_schema_code_fields_and_invalid_measurements() {
        let raw = serde_json::json!({"schema":"archeaxis.machine-worker-failure/v1","reason_code":"NO_FINAL_ANSWER","diagnostics":{
            "requested_model":"bad\\model", "observed_model":null, "finish_reason":"PRIVATE", "answer_source":"reasoning_content",
            "max_tokens":true,"timeout_s":-1,"elapsed_s":-1,"http_status":600,
            "usage":{"input_tokens":0,"output_tokens":-1,"total_tokens":9007199254740992u64,"raw":"PRIVATE"},"stderr":"PRIVATE"}});
        let error = MachineFailure::from_worker(&serde_json::to_vec(&raw).unwrap());
        assert_eq!(
            error.diagnostics(),
            Some(
                &serde_json::json!({"observed_model":null,"answer_source":"reasoning_content","usage":{"input_tokens":0}})
            )
        );
        assert_eq!(error.to_string(), "machine failure: NO_FINAL_ANSWER");
        for key in ["schema", "reason_code"] {
            let mut invalid = raw.clone();
            invalid[key] = serde_json::json!("PRIVATE");
            let error = MachineFailure::from_worker(&serde_json::to_vec(&invalid).unwrap());
            assert_eq!(error.reason_code(), "WORKER_FAILED");
            assert!(error.diagnostics().is_none());
        }
    }
}

#[cfg(test)]
mod request_measurement_tests {
    use super::*;
    #[test]
    fn keeps_finite_request_substage_counts_but_never_private_provider_fields() {
        for phase in [
            "http_open",
            "body_read",
            "json_parse",
            "response_validation",
        ] {
            let input = serde_json::json!({"schema":"archeaxis.machine-worker-failure/v1","reason_code":"MODEL_CALL_TIMEOUT","diagnostics":{
                "request_stage":"model_request","request_phase":phase,"http_open_elapsed_s":0.25,"body_read_elapsed_s":0,"json_parse_elapsed_s":1,
                "prompt_utf8_bytes":0,"serialized_request_bytes":753,"response_bytes":4194305,"prompt":"PRIVATE","url":"PRIVATE","headers":{"token":"PRIVATE"},"ttft_s":0}});
            let failure = MachineFailure::from_worker(&serde_json::to_vec(&input).unwrap());
            let diag = failure.diagnostics().unwrap();
            assert_eq!(diag["request_phase"], phase);
            assert_eq!(diag["serialized_request_bytes"], 753);
            assert_eq!(diag["response_bytes"], 4194305);
            assert!(!diag.to_string().contains("PRIVATE"));
            assert!(diag.get("ttft_s").is_none());
            assert_eq!(failure.reason_code(), "MODEL_CALL_TIMEOUT");
        }
    }
    #[test]
    fn invalid_new_measurements_are_rejected_and_old_stage_remains_compatible() {
        let input = serde_json::json!({"request_stage":"model_request","request_phase":"PRIVATE","prompt_utf8_bytes":true,"serialized_request_bytes":-1,
            "response_bytes":9007199254740992u64,"http_open_elapsed_s":true,"body_read_elapsed_s":-1,"json_parse_elapsed_s":"PRIVATE"});
        assert_eq!(
            sanitize(&input),
            Some(serde_json::json!({"request_stage":"model_request"}))
        );
        assert_eq!(
            sanitize(
                &serde_json::json!({"response_bytes":0,"prompt_utf8_bytes":9007199254740991u64})
            ),
            Some(serde_json::json!({"response_bytes":0,"prompt_utf8_bytes":9007199254740991u64}))
        );
    }
}
