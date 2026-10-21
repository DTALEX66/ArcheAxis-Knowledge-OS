use archeaxis_application::executor::{Cancellation, Executor};
use archeaxis_domain::model_configuration::*;
use std::{collections::BTreeMap, path::PathBuf, time::Duration};

#[tokio::test]
async fn dormant_material_cloud_is_refused_before_worker_or_local_discovery() {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("worker.py");
    std::fs::write(&worker, "from pathlib import Path\nPath(__file__).with_suffix('.started').touch()\nraise SystemExit(1)\n").unwrap();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").unwrap()),
        &worker,
        &[("machine.answer", worker.clone())],
    )
    .await
    .unwrap();
    let configuration = Resolved {
        workspace_id: "a".repeat(32),
        restore_epoch: "initial".into(),
        schema: "archeaxis.resolved-model/v1".into(),
        configuration_revision: 1,
        configuration_sha256: "b".repeat(64),
        purpose: Purpose::Material,
        lane: Lane::Fast,
        profile_id: "synthetic_cloud".into(),
        profile: Profile {
            endpoint: "https://synthetic.invalid/v1".into(),
            protocol: "openai".into(),
            model: "synthetic-model".into(),
            credential_ref: Some(format!("aak_cred_{}", "c".repeat(32))),
            max_tokens: 128,
            timeout_s: 5,
        },
    };
    let result = executor
        .machine_answer_configured(
            "Synthetic material".into(),
            "Question".into(),
            128,
            Duration::from_secs(5),
            Some("synthetic-model".into()),
            Cancellation::new(),
            Some(configuration.clone()),
        )
        .await;
    assert_eq!(result.unwrap_err(), "MATERIAL_CLOUD_NOT_ACTIVATED");
    for (purpose, endpoint) in [
        (Purpose::Material, "http://127.0.0.1:1234/v1"),
        (Purpose::Answer, "https://synthetic.invalid/v1"),
    ] {
        let mut legacy = configuration.clone();
        legacy.purpose = purpose;
        legacy.profile.endpoint = endpoint.into();
        let error = executor
            .machine_answer_configured(
                "Synthetic material".into(),
                "Question".into(),
                128,
                Duration::from_secs(5),
                Some("synthetic-model".into()),
                Cancellation::new(),
                Some(legacy),
            )
            .await
            .unwrap_err();
        assert_eq!(
            error, "LOCAL_CREDENTIAL_NOT_SUPPORTED",
            "local/other-purpose error contract changed"
        );
    }
    assert!(!worker.with_extension("started").exists());
}
#[tokio::test]
async fn configured_deep_executes_exact_destination_and_rejects_changed_revision() {
    let dir = tempfile::tempdir().unwrap();
    let worker = dir.path().join("worker.py");
    std::fs::write(&worker,"import os,json,sys\nif '--probe' in sys.argv:\n print(json.dumps({'inventory_status':'READ_VERIFIED','loaded_status':'UNKNOWN','inference_status':'NOT_EXECUTED','evidence_scope':'MODEL_INVENTORY_ONLY','available':[os.environ['ARCHEAXIS_MACHINE_MODEL']],'model':os.environ['ARCHEAXIS_MACHINE_MODEL'],'capability':True,'availability':'MODEL_LISTED_INFERENCE_UNVERIFIED'}));sys.exit(0)\nprint(json.dumps({'answer':'synthetic answer','model':os.environ['ARCHEAXIS_MACHINE_MODEL'],'requested_model':os.environ['ARCHEAXIS_MACHINE_MODEL'],'endpoint':os.environ['ARCHEAXIS_MACHINE_ENDPOINT'],'protocol':os.environ['ARCHEAXIS_MACHINE_PROTOCOL']}))\n").unwrap();
    let executor = Executor::open_routes(
        &dir.path().join("db"),
        &dir.path().join("staging"),
        &PathBuf::from(std::env::var_os("ARCHEAXIS_PYTHON").expect("declared Python")),
        &worker,
        &[("machine.answer", worker.clone())],
    )
    .await
    .unwrap();
    let config = Configuration {
        workspace_id: String::new(),
        restore_epoch: String::new(),
        schema: "archeaxis.model-configuration/v1".into(),
        revision: 0,
        profiles: BTreeMap::from([(
            "deep".into(),
            Profile {
                endpoint: "http://127.0.0.1:43123/v1".into(),
                protocol: "openai".into(),
                model: "synthetic-deep".into(),
                credential_ref: None,
                max_tokens: 2048,
                timeout_s: 30,
            },
        )]),
        bindings: vec![Binding {
            purpose: Purpose::Answer,
            lane: Lane::Deep,
            profile_id: "deep".into(),
        }],
    };
    executor
        .store()
        .submit_wait(move |c| {
            let identity = read(c)?;
            let mut config = config;
            config.workspace_id = identity.workspace_id;
            config.restore_epoch = identity.restore_epoch;
            put(c, 0, config)
        })
        .await
        .unwrap()
        .unwrap();
    let r = executor
        .store()
        .submit_wait(|c| resolve(c, Purpose::Answer, Lane::Deep))
        .await
        .unwrap()
        .unwrap();
    let answer = executor
        .machine_answer_configured(
            "synthetic material".into(),
            "synthetic question".into(),
            512,
            Duration::from_secs(20),
            Some(r.profile.model.clone()),
            Cancellation::new(),
            Some(r.clone()),
        )
        .await
        .unwrap();
    assert_eq!(answer["endpoint"], r.profile.endpoint);
    assert_eq!(answer["model"], "synthetic-deep");
    assert_eq!(answer["protocol"], "openai");
    executor
        .store()
        .submit_wait(|c| {
            let mut next = read(c)?;
            next.profiles.get_mut("deep").unwrap().model = "changed".into();
            put(c, 1, next)
        })
        .await
        .unwrap()
        .unwrap();
    assert!(
        executor
            .machine_answer_configured(
                "synthetic".into(),
                "question".into(),
                512,
                Duration::from_secs(20),
                Some(r.profile.model.clone()),
                Cancellation::new(),
                Some(r)
            )
            .await
            .unwrap_err()
            .contains("MODEL_CONFIGURATION_CHANGED")
    );
}
