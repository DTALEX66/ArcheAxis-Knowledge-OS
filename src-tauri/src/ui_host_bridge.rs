//! Versioned finite adapter. Missing ports have no fallback; IDs correlate, not deduplicate.
#[path = "../../crates/archeaxis-contracts/src/generated/ui_host.rs"]
pub mod contract;
use crate::core_bridge;
use contract::{Outcome, Request, Response, CONTRACT_DIGEST};
use serde_json::{json, Value};
use std::time::{SystemTime, UNIX_EPOCH};

pub fn reply(
    request: &Request,
    outcome: Outcome,
    reason: Option<&str>,
    status: Option<u16>,
    result: Option<Value>,
) -> Response {
    Response {
        schema: "archeaxis.ui-host-response/v2".into(),
        contract_digest: CONTRACT_DIGEST.into(),
        request_id: request.request_id.clone(),
        workspace_id: request.workspace_id.clone(),
        restore_epoch: request.restore_epoch.clone(),
        operation: request.operation.clone(),
        outcome,
        reason_code: reason.map(str::to_owned),
        core_status: status,
        build_identity: contract::BuildIdentity {
            host_version: env!("CARGO_PKG_VERSION").into(),
            source_revision: None,
        },
        checked_at: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0),
        result_ref: result,
    }
}
pub fn mapped(request: &Request) -> Result<Option<core_bridge::Request>, String> {
    request.validate().map_err(str::to_owned)?;
    request
        .operation
        .core_operation()
        .map(|operation| {
            serde_json::from_value(json!({"operation":operation,"payload":{}}))
                .map_err(|_| "HOST_MAPPING_INVALID".into())
        })
        .transpose()
}
pub fn workspace_matches(request: &Request, result: &core_bridge::Reply) -> bool {
    result.status == 200
        && result.body["workspace_id"] == request.workspace_id
        && result.body["restore_epoch"] == request.restore_epoch
}
pub fn project(request: &Request, result: Result<core_bridge::Reply, String>) -> Response {
    match result {
        Err(_) => reply(
            request,
            Outcome::Unknown,
            Some("RESULT_UNKNOWN"),
            None,
            None,
        ),
        Ok(result) if !(200..300).contains(&result.status) => reply(
            request,
            if result.status >= 500 {
                Outcome::Unavailable
            } else {
                Outcome::Rejected
            },
            Some(if result.status >= 500 {
                "CORE_UNAVAILABLE"
            } else {
                "CORE_REJECTED"
            }),
            Some(result.status),
            None,
        ),
        Ok(result) if !valid_result(request, &result.body) => reply(
            request,
            Outcome::Unknown,
            Some("INVALID_CORE_RESULT"),
            Some(result.status),
            None,
        ),
        Ok(result) => reply(
            request,
            Outcome::ReadOk,
            None,
            Some(result.status),
            Some(result.body),
        ),
    }
}
fn valid_result(request: &Request, body: &Value) -> bool {
    if !body.is_object() {
        return false;
    }
    let schemas: Value = match serde_json::from_str(contract::CORE_RESPONSE_SCHEMAS) {
        Ok(value) => value,
        Err(_) => return false,
    };
    let operation = match serde_json::to_value(&request.operation) {
        Ok(Value::String(value)) => value,
        _ => return false,
    };
    if let Some(schema) = schemas.get(&operation) {
        return schema_matches(schema, body);
    }
    match request.operation {
        contract::Operation::CapabilityCatalogRead => {
            body["schema"] == "archeaxis.capabilities/v1"
                && body["capabilities"].as_array().is_some_and(|rows| {
                    rows.iter()
                        .all(|row| row["capability"].as_str().is_some_and(|s| !s.is_empty()))
                })
        }
        contract::Operation::ModelConfigurationRead => {
            body["schema"] == "archeaxis.machine-configuration/v1"
                && body["inference_status"] == "NOT_EXECUTED"
                && body["worker_registered"].is_boolean()
        }
        contract::Operation::ModelInventoryRead => {
            body["schema"] == "archeaxis.machine-inventory/v1"
                && body["inference_status"] == "NOT_EXECUTED"
                && body["loaded_status"] == "UNKNOWN"
                && body["evidence_scope"] == "MODEL_INVENTORY_ONLY"
        }
        _ => false,
    }
}

fn schema_matches(schema: &Value, value: &Value) -> bool {
    if let Some(expected) = schema.get("const") {
        return value == expected;
    }
    if let Some(choices) = schema["enum"].as_array() {
        return choices.contains(value);
    }
    if let Some(choices) = schema["anyOf"].as_array() {
        return choices.iter().any(|choice| schema_matches(choice, value));
    }
    if let Some(types) = schema["type"].as_array() {
        return types.iter().any(|kind| {
            let mut one = schema.clone();
            one["type"] = kind.clone();
            schema_matches(&one, value)
        });
    }
    match schema["type"].as_str() {
        Some("object") => {
            let Some(object) = value.as_object() else {
                return false;
            };
            let properties = schema["properties"].as_object();
            if schema["required"].as_array().is_some_and(|keys| {
                keys.iter()
                    .any(|key| !object.contains_key(key.as_str().unwrap_or("")))
            }) {
                return false;
            }
            if schema["additionalProperties"] == false
                && object
                    .keys()
                    .any(|key| properties.is_none_or(|p| !p.contains_key(key)))
            {
                return false;
            }
            properties.is_none_or(|p| {
                p.iter()
                    .all(|(key, node)| object.get(key).is_none_or(|v| schema_matches(node, v)))
            })
        }
        Some("array") => value.as_array().is_some_and(|rows| {
            schema["minItems"]
                .as_u64()
                .is_none_or(|n| rows.len() >= n as usize)
                && schema["maxItems"]
                    .as_u64()
                    .is_none_or(|n| rows.len() <= n as usize)
                && rows.iter().all(|row| schema_matches(&schema["items"], row))
        }),
        Some("string") => value.as_str().is_some_and(|s| {
            schema["minLength"]
                .as_u64()
                .is_none_or(|n| s.chars().count() >= n as usize)
                && schema["maxLength"]
                    .as_u64()
                    .is_none_or(|n| s.chars().count() <= n as usize)
                && schema["pattern"]
                    .as_str()
                    .is_none_or(|pattern| match pattern {
                        "^[^\\u0000-\\u001f\\u007f]+$" => {
                            !s.is_empty() && s.chars().all(|c| c > '\u{001f}' && c != '\u{007f}')
                        }
                        _ => false,
                    })
        }),
        Some("integer") => value.as_i64().is_some_and(|n| {
            schema["minimum"].as_i64().is_none_or(|bound| n >= bound)
                && schema["maximum"].as_i64().is_none_or(|bound| n <= bound)
        }),
        Some("boolean") => value.is_boolean(),
        Some("null") => value.is_null(),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request(operation: &str) -> Request {
        serde_json::from_value(json!({"schema":"archeaxis.ui-host-request/v2","contract_digest":CONTRACT_DIGEST,"request_id":"trace_1","workspace_id":"a".repeat(32),"restore_epoch":"initial","operation":operation,"input":{}})).unwrap()
    }
    #[test]
    fn exactly_admitted_reads_map_and_pending_ports_never_dispatch() {
        for (operation, expected) in [
            ("capability.catalog.read", "capabilities_list"),
            ("model.configuration.read", "machine_configuration"),
            ("model.inventory.read", "machine_inventory"),
        ] {
            let req = request(operation);
            let mapped = mapped(&req).unwrap().unwrap();
            assert_eq!(serde_json::to_value(&req.operation).unwrap(), operation);
            let expected: core_bridge::Request =
                serde_json::from_value(json!({"operation":expected,"payload":{}})).unwrap();
            assert_eq!(
                std::mem::discriminant(&mapped.operation),
                std::mem::discriminant(&expected.operation)
            );
        }
        for op in [
            "companion.send",
            "layout.write",
            "material.answer",
            "credential.bind",
            "project.handoff.preview",
        ] {
            let req = request(op);
            assert!(mapped(&req).unwrap().is_none());
            let response = reply(
                &req,
                Outcome::Unavailable,
                Some("HOST_CONTRACT_MISSING"),
                None,
                None,
            );
            assert_eq!(response.outcome, Outcome::Unavailable);
            assert!(response.result_ref.is_none());
        }
    }
    #[test]
    fn workspace_epoch_is_checked_and_failures_never_publish_unverified_results() {
        let req = request("model.inventory.read");
        let mut state = core_bridge::Reply {
            status: 200,
            body: json!({"workspace_id":req.workspace_id,"restore_epoch":"initial"}),
        };
        assert!(workspace_matches(&req, &state));
        state.body["restore_epoch"] = "b".repeat(32).into();
        assert!(!workspace_matches(&req, &state));
        assert_eq!(
            project(&req, Err("unavailable".into())).outcome,
            Outcome::Unknown
        );
        assert_eq!(
            project(
                &req,
                Ok(core_bridge::Reply {
                    status: 200,
                    body: json!({"inference_status":"EXECUTED"})
                })
            )
            .outcome,
            Outcome::Unknown
        );
        let complete = json!({"schema":"archeaxis.machine-inventory/v1","status":"READ_VERIFIED","listed_model_count":1,"selected_model_listed":true,"model_choices":["local"],"inference_status":"NOT_EXECUTED","loaded_status":"UNKNOWN","evidence_scope":"MODEL_INVENTORY_ONLY","usage":null,"cost":null});
        assert_eq!(
            project(
                &req,
                Ok(core_bridge::Reply {
                    status: 200,
                    body: complete.clone()
                })
            )
            .outcome,
            Outcome::ReadOk
        );
        let mut invalid = complete;
        invalid["model_choices"] = json!(["invalid\nname"]);
        assert_eq!(
            project(
                &req,
                Ok(core_bridge::Reply {
                    status: 200,
                    body: invalid
                })
            )
            .outcome,
            Outcome::Unknown
        );
    }
}
