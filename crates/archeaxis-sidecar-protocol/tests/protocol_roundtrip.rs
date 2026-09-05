//! Sidecar protocol round-trip tests.
use archeaxis_sidecar_protocol::{Message, PROTOCOL_VERSION, decode, encode};

#[test]
fn handshake_roundtrip() {
    let msg = Message::Handshake {
        runtime: "archeaxis-application".into(),
        contract: "0.1.0-outline".into(),
        schema_version: 1,
        workspace_ready: true,
    };
    let line = encode(msg.clone()).unwrap();
    let env = decode(&line).unwrap();
    assert_eq!(env.version, PROTOCOL_VERSION);
    assert_eq!(env.message, msg);
}

#[test]
fn worker_receipt_roundtrip() {
    let msg = Message::WorkerReceipt {
        job_id: "job-1".into(),
        state: "completed".into(),
        engine: Some("python-worker".into()),
        loss_receipt: Some(serde_json::json!({"loss_note": null})),
    };
    let line = encode(msg.clone()).unwrap();
    let env = decode(&line).unwrap();
    assert_eq!(env.message, msg);
}

#[test]
fn version_mismatch_rejected() {
    let line = r#"{"version":99,"message":{"kind":"ping","nonce":"x"}}"#;
    let err = decode(line).unwrap_err();
    assert!(err.to_string().contains("version mismatch"), "{err}");
}

#[test]
fn malformed_rejected() {
    assert!(decode("not-json").is_err());
}
