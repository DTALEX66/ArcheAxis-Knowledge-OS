use archeaxis_domain::model_configuration::*;
use archeaxis_store_sqlite::init_workspace;
use std::collections::BTreeMap;
fn configuration() -> Configuration {
    Configuration {
        workspace_id: "a".repeat(32),
        restore_epoch: "initial".into(),
        schema: "archeaxis.model-configuration/v1".into(),
        revision: 0,
        profiles: BTreeMap::from([(
            "local".into(),
            Profile {
                endpoint: "http://127.0.0.1:1234/v1".into(),
                protocol: "openai".into(),
                model: "synthetic-model".into(),
                credential_ref: None,
                max_tokens: 4096,
                timeout_s: 120,
            },
        )]),
        bindings: vec![
            Binding {
                purpose: Purpose::Answer,
                lane: Lane::Fast,
                profile_id: "local".into(),
            },
            Binding {
                purpose: Purpose::Retest,
                lane: Lane::Deep,
                profile_id: "local".into(),
            },
        ],
    }
}
#[test]
fn purpose_lane_destination_changes_the_frozen_journal_identity() {
    let base = serde_json::json!({"knowledge_id":"knowledge","question":"same question","max_tokens":512,"timeout_s":20,"client_request_id":"same-id"});
    let mut fast = base.clone();
    fast["model_configuration"] = serde_json::json!({"lane":"fast","configuration_revision":1,"profile":{"model":"m","endpoint":"http://127.0.0.1:1/v1"}});
    let mut deep = fast.clone();
    deep["model_configuration"]["lane"] = "deep".into();
    let fingerprint = archeaxis_domain::ui_state::machine_request_fingerprint;
    assert_ne!(fingerprint("answer", &fast), fingerprint("answer", &deep));
    deep = fast.clone();
    deep["model_configuration"]["configuration_revision"] = 2.into();
    assert_ne!(fingerprint("answer", &fast), fingerprint("answer", &deep));
    deep = fast.clone();
    deep["model_configuration"]["profile"]["endpoint"] = "http://127.0.0.1:2/v1".into();
    assert_ne!(fingerprint("answer", &fast), fingerprint("answer", &deep));
    assert_ne!(fingerprint("answer", &base), fingerprint("answer", &fast));
}
#[test]
fn cas_restart_frozen_purpose_and_plain_secret_rejection() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(read(&conn).unwrap().revision, 0);
    let mut initial = configuration();
    let identity = read(&conn).unwrap();
    initial.workspace_id = identity.workspace_id;
    initial.restore_epoch = identity.restore_epoch;
    let first = put(&mut conn, 0, initial).unwrap();
    assert_eq!(first.revision, 1);
    assert!(put(&mut conn, 0, configuration()).is_err());
    let r = resolve(&conn, Purpose::Answer, Lane::Fast).unwrap();
    assert_current(&conn, &r).unwrap();
    assert!(resolve(&conn, Purpose::Answer, Lane::Deep).is_err());
    drop(conn);
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(read(&conn).unwrap(), first);
    let mut next = first.clone();
    next.profiles.get_mut("local").unwrap().model = "another-model".into();
    put(&mut conn, 1, next).unwrap();
    assert!(assert_current(&conn, &r).is_err());
    let mut raw = serde_json::to_value(configuration()).unwrap();
    raw["profiles"]["local"]["api_key"] = "synthetic-not-a-real-secret".into();
    assert!(serde_json::from_value::<Configuration>(raw).is_err());
    let mut invalid = configuration();
    invalid.profiles.get_mut("local").unwrap().endpoint = "https://external.invalid/v1".into();
    assert!(validate(&invalid).is_err());
    assert_eq!(
        conn.query_row("SELECT COUNT(*) FROM knowledge", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        0
    );
}
#[test]
fn embedding_change_requires_index_plan() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("db").to_str().unwrap()).unwrap();
    let mut c = configuration();
    let identity = read(&conn).unwrap();
    c.workspace_id = identity.workspace_id;
    c.restore_epoch = identity.restore_epoch;
    c.bindings.push(Binding {
        purpose: Purpose::Embedding,
        lane: Lane::Fast,
        profile_id: "local".into(),
    });
    let mut c = put(&mut conn, 0, c).unwrap();
    c.profiles.get_mut("local").unwrap().model = "new-embedding".into();
    assert!(
        put(&mut conn, 1, c)
            .unwrap_err()
            .to_string()
            .contains("NEEDS_INDEX_REBUILD")
    );
}

#[test]
fn identity_restore_safe_integer_and_oversized_raw_never_write() {
    let dir = tempfile::tempdir().unwrap();
    let mut a = init_workspace(dir.path().join("a").to_str().unwrap()).unwrap();
    let mut b = init_workspace(dir.path().join("b").to_str().unwrap()).unwrap();
    let mut next = configuration();
    let identity = read(&a).unwrap();
    next.workspace_id = identity.workspace_id;
    next.restore_epoch = identity.restore_epoch;
    assert!(put(&mut b, 0, next.clone()).is_err());
    assert_eq!(read(&b).unwrap().revision, 0);
    let first = put(&mut a, 0, next).unwrap();
    let resolved = resolve(&a, Purpose::Answer, Lane::Fast).unwrap();
    let tx = a.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    assert!(put(&mut a, 1, first.clone()).is_err());
    assert!(assert_current(&a, &resolved).is_err());
    assert_eq!(read(&a).unwrap().revision, 1);
    let mut maximum = read(&a).unwrap();
    maximum.revision = MAX_REVISION;
    let raw = serde_json::to_string(&maximum).unwrap();
    a.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key='product_model_configuration_v1'",
        [&raw],
    )
    .unwrap();
    assert!(put(&mut a, MAX_REVISION, maximum).is_err());
    assert_eq!(read(&a).unwrap().revision, MAX_REVISION);
    let raw = "x".repeat(65_537);
    a.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key='product_model_configuration_v1'",
        [&raw],
    )
    .unwrap();
    assert!(read(&a).is_err());
    assert!(put(&mut a, 0, first).is_err());
    let unchanged: String = a
        .query_row(
            "SELECT value FROM workspace_meta WHERE key='product_model_configuration_v1'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(unchanged, raw);
}

#[test]
fn companion_and_material_bindings_are_independent_and_frozen() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("companion.sqlite").to_str().unwrap()).unwrap();
    let identity = read(&conn).unwrap();
    let mut next = configuration();
    next.workspace_id = identity.workspace_id;
    next.restore_epoch = identity.restore_epoch;
    next.bindings.push(Binding {
        purpose: Purpose::Companion,
        lane: Lane::Fast,
        profile_id: "local".into(),
    });
    put(&mut conn, 0, next).unwrap();
    let frozen = resolve(&conn, Purpose::Companion, Lane::Fast).unwrap();
    assert_eq!(frozen.purpose, Purpose::Companion);
    assert!(resolve(&conn, Purpose::Material, Lane::Fast).is_err());
    assert_current(&conn, &frozen).unwrap();
    let mut changed = read(&conn).unwrap();
    changed.profiles.get_mut("local").unwrap().endpoint = "http://127.0.0.1:1235/v1".into();
    put(&mut conn, 1, changed).unwrap();
    assert!(assert_current(&conn, &frozen).is_err());
}

#[test]
fn buffered_cloud_is_material_only_and_requires_opaque_credential() {
    let mut c = configuration();
    c.bindings = vec![Binding {
        purpose: Purpose::Material,
        lane: Lane::Fast,
        profile_id: "local".into(),
    }];
    let p = c.profiles.get_mut("local").unwrap();
    p.endpoint = "https://api.openai.com/v1".into();
    p.protocol = "openai-buffered".into();
    p.timeout_s = 60;
    p.credential_ref = Some(format!("aak_cred_{}", "a".repeat(32)));
    validate(&c).unwrap();
    for purpose in [
        Purpose::Answer,
        Purpose::Retest,
        Purpose::Companion,
        Purpose::Embedding,
        Purpose::DocumentCheck,
    ] {
        c.bindings[0].purpose = purpose;
        assert!(validate(&c).is_err());
    }
    c.bindings[0].purpose = Purpose::Material;
    c.bindings[0].lane = Lane::Deep;
    validate(&c).unwrap();
    for credential in [
        None,
        Some("secret".into()),
        Some(format!("aak_cred_{}", "A".repeat(32))),
    ] {
        c.profiles.get_mut("local").unwrap().credential_ref = credential;
        assert!(validate(&c).is_err());
    }
}
#[test]
fn cloud_endpoint_rejects_private_and_ambiguous_authorities_without_loosening_local() {
    let mut c = configuration();
    c.bindings.clear();
    let p = c.profiles.get_mut("local").unwrap();
    p.protocol = "openai-buffered".into();
    p.timeout_s = 60;
    p.credential_ref = Some(format!("aak_cred_{}", "1".repeat(32)));
    for endpoint in [
        "http://api.openai.com/v1",
        "https://127.0.0.1/v1",
        "https://10.0.0.1/v1",
        "https://[::1]/v1",
        "https://localhost/v1",
        "https://host.local/v1",
        "https://host.internal/v1",
        "https://host.home.arpa/v1",
        "https://user@api.openai.com/v1",
        "https://api.openai.com/v1?q=a",
        "https://api.openai.com/v1#fragment",
        "https://api.openai.com./v1",
        "https://api.openai.com:0/v1",
        "https://api.openai.com:8443/v1",
        "https://api.openai.com/v1.0",
        "https://api.openai.com/a//b",
        "https://api.openai.com/%2e",
        "https://api.openai.com\\@localhost/v1",
    ] {
        c.profiles.get_mut("local").unwrap().endpoint = endpoint.into();
        assert!(validate(&c).is_err(), "{endpoint}");
    }
    for protocol in ["openai", "ollama"] {
        let p = c.profiles.get_mut("local").unwrap();
        p.endpoint = "https://api.openai.com/v1".into();
        p.protocol = protocol.into();
        assert!(validate(&c).is_err());
    }
}
