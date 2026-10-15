use archeaxis_domain::{
    configuration_plans::catalog,
    model_configuration::{self, Profile},
};
use archeaxis_store_sqlite::init_workspace;
use serde_json::json;

#[test]
fn plans_follow_persisted_revision_epoch_and_never_expose_credentials_or_artifact_claims() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("db").to_str().unwrap()).unwrap();
    let empty = catalog(model_configuration::read(&conn).unwrap(), vec![]).unwrap();
    assert!(empty.plans.is_empty());
    let mut config = model_configuration::read(&conn).unwrap();
    config.profiles.insert(
        "loopback".into(),
        Profile {
            endpoint: "http://127.0.0.1:1234/v1".into(),
            protocol: "openai".into(),
            model: "synthetic-model".into(),
            credential_ref: Some(format!("aak_cred_{}", "a".repeat(32))),
            max_tokens: 2048,
            timeout_s: 30,
        },
    );
    let first = model_configuration::put(&mut conn, 0, config).unwrap();
    let original = catalog(first.clone(), vec![]).unwrap();
    let repeated = catalog(first.clone(), vec![]).unwrap();
    assert_eq!(original.plans.len(), 2);
    assert_eq!(original.configuration_revision, 1);
    assert_eq!(original.plans[0].plan_id, repeated.plans[0].plan_id);
    assert_ne!(original.plans[0].plan_id, original.plans[1].plan_id);
    assert_eq!(
        original.plans[0].source.as_deref(),
        Some("http://127.0.0.1:1234/v1")
    );
    assert!(original.plans[1].source.is_none());
    for plan in &original.plans {
        assert!(!plan.executable);
        assert!(
            plan.version.is_none() && plan.size_bytes.is_none() && plan.artifact_sha256.is_none()
        );
    }
    let raw = serde_json::to_string(&original).unwrap();
    assert!(!raw.contains("aak_cred_") && !raw.contains("credential_ref"));
    assert!(!original.network_performed && !original.storage_changed && !original.worker_started);
    assert!(original.execution_grant.is_none() && !original.installer_available);
    assert_eq!(model_configuration::read(&conn).unwrap(), first);
    let mut next = first.clone();
    next.profiles.get_mut("loopback").unwrap().model = "other-model".into();
    let next = model_configuration::put(&mut conn, 1, next).unwrap();
    let changed = catalog(next.clone(), vec![]).unwrap();
    assert_ne!(original.configuration_sha256, changed.configuration_sha256);
    assert_ne!(original.plans[0].plan_id, changed.plans[0].plan_id);
    let mut restored = next;
    restored.restore_epoch = "b".repeat(32);
    assert_ne!(
        changed.plans[0].plan_id,
        catalog(restored, vec![]).unwrap().plans[0].plan_id
    );
}

#[test]
fn invalid_remote_profile_cannot_be_turned_into_a_valid_plan() {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("db").to_str().unwrap()).unwrap();
    let mut raw = serde_json::to_value(model_configuration::read(&conn).unwrap()).unwrap();
    raw["profiles"] = json!({"remote":{"endpoint":"https://external.invalid/v1","protocol":"openai","model":"synthetic","credential_ref":null,"max_tokens":2048,"timeout_s":30}});
    assert!(catalog(serde_json::from_value(raw).unwrap(), vec![]).is_err());
}
