use archeaxis_contracts::ui_host::{CONTRACT_DIGEST, Request};
use serde_json::{Value, json};

fn valid() -> Value {
    json!({"schema":"archeaxis.ui-host-request/v2","contract_digest":CONTRACT_DIGEST,"request_id":"trace_1","workspace_id":"a".repeat(32),"restore_epoch":"initial","operation":"model.inventory.read","input":{}})
}
#[test]
fn finite_request_identity_version_and_unknown_input_are_rejected() {
    let req: Request = serde_json::from_value(valid()).unwrap();
    assert!(req.validate().is_ok());
    assert_eq!(req.operation.core_operation(), Some("machine_inventory"));
    for (field, value) in [
        ("schema", json!("archeaxis.ui-host-request/v1")),
        ("contract_digest", json!("b".repeat(64))),
        ("workspace_id", json!("nonempty")),
        ("request_id", json!("../escape")),
        ("restore_epoch", json!("UNKNOWN")),
    ] {
        let mut raw = valid();
        raw[field] = value;
        assert!(
            serde_json::from_value::<Request>(raw)
                .unwrap()
                .validate()
                .is_err(),
            "{field}"
        );
    }
    for raw in [
        {
            let mut r = valid();
            r["operation"] = "shell.exec".into();
            r
        },
        {
            let mut r = valid();
            r["input"] = json!({"url":"http://127.0.0.1:1234"});
            r
        },
        {
            let mut r = valid();
            r["scope_ref"] = "grant".into();
            r
        },
    ] {
        assert!(serde_json::from_value::<Request>(raw).is_err());
    }
}
#[test]
fn request_id_is_not_an_execution_receipt_or_grant() {
    let mut pending = valid();
    pending["operation"] = "companion.send".into();
    let req: Request = serde_json::from_value(pending.clone()).unwrap();
    assert!(req.validate().is_ok());
    assert_eq!(req.operation.core_operation(), None);
    assert!(
        serde_json::from_value::<Request>(pending)
            .unwrap()
            .validate()
            .is_ok()
    );
}

#[test]
fn prior_host_digest_is_rejected_after_response_schema_change() {
    for prior_digest in [
        "3826d07e70d1d8dff5c421d8c6e8f704b5927683e48809ac47019ed996ec82bb",
        "d9d26d3a256dbe08ca69918a6979e1aa84c76fae3e021c68ef32d210cd356504",
        "5d187a74d6b6c8e727febd9a01b81d52fac389f09682504ca1d39857724daf5a",
    ] {
        let mut request = valid();
        request["contract_digest"] = json!(prior_digest);
        assert_ne!(request["contract_digest"], CONTRACT_DIGEST);
        assert_eq!(
            serde_json::from_value::<Request>(request)
                .unwrap()
                .validate(),
            Err("HOST_VERSION_INCOMPATIBLE")
        );
    }
    assert!(
        serde_json::from_value::<Request>(valid())
            .unwrap()
            .validate()
            .is_ok()
    );
}
