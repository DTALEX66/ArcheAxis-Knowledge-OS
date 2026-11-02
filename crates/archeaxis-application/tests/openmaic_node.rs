//! Optional explicit Node route. These tests do not claim installed or model qualification.
use archeaxis_application::executor::Executor;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    io::Read,
    path::{Path, PathBuf},
    time::Duration,
};

fn repository() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap()
}

fn worker() -> PathBuf {
    repository().join("services/learning-providers/openmaic/scene-build-worker.mjs")
}

fn file_sha(path: &Path) -> String {
    let mut file = std::fs::File::open(path).unwrap();
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer).unwrap();
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
    }
    hex::encode(hash.finalize())
}

async fn executor(dir: &std::path::Path) -> Executor {
    Executor::open(
        &dir.join("workspace.sqlite"),
        &dir.join("staging"),
        &dir.join("unused-python"),
        &dir.join("unused-python-worker"),
    )
    .await
    .unwrap()
}

fn request() -> serde_json::Value {
    json!({"schema":"archeaxis.openmaic-scene-build/v1", "request_id":"req_1", "attempt":1,
      "source":{"document_id":"doc_1", "version":1, "content_sha256":"a".repeat(64)},
      "stage_id":"stage_1", "scene_id":"scene_1",
      "outline":{"id":"outline_1", "type":"quiz", "title":"Test", "description":"Synthetic", "keyPoints":[], "order":0},
      "content":{"questions":[{"id":"q1", "type":"short_answer", "question":"Explain"}]}, "actions":[]})
}

#[tokio::test]
async fn absent_profile_refuses_node_without_affecting_the_store() {
    let dir = tempfile::tempdir().unwrap();
    let ex = executor(dir.path()).await;
    assert_eq!(
        ex.derived_json(
            "course.openmaic.scene-build",
            request(),
            Duration::from_secs(1)
        )
        .await
        .unwrap_err(),
        "OpenMAIC Node worker not configured"
    );
    assert_eq!(
        ex.derived_json("unknown.capability", request(), Duration::from_secs(1))
            .await
            .unwrap_err(),
        "unsupported derived capability"
    );
    let value = ex
        .store()
        .submit_wait(|conn| conn.query_row("SELECT 1", [], |row| row.get::<_, i64>(0)))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(value, 1);
}

#[tokio::test]
async fn changed_or_missing_worker_files_fail_closed() {
    let dir = tempfile::tempdir().unwrap();
    let ex = executor(dir.path()).await;
    let node = dir
        .path()
        .join(if cfg!(windows) { "node.exe" } else { "node" });
    let script = dir.path().join("scene-build-worker.mjs");
    std::fs::write(&node, b"not an executable").unwrap();
    std::fs::write(&script, b"wrong worker").unwrap();
    let sha = file_sha(&node);
    assert!(ex.clone().with_openmaic_node(&node, &sha, &script).is_err());
    assert!(
        ex.clone()
            .with_openmaic_node(&node, &"0".repeat(64), &worker())
            .is_err()
    );
    assert!(
        ex.with_openmaic_node(&dir.path().join("missing-node"), &sha, &worker())
            .is_err()
    );
}

#[tokio::test]
#[ignore = "requires an explicit ARCHEAXIS_TEST_NODE absolute Node 24 path; no PATH discovery"]
async fn explicit_node_executes_pinned_upstream_and_respects_disable() {
    let dir = tempfile::tempdir().unwrap();
    let node = PathBuf::from(
        std::env::var_os("ARCHEAXIS_TEST_NODE").expect("explicit Node path required"),
    )
    .canonicalize()
    .unwrap();
    let sha = file_sha(&node);
    let ex = executor(dir.path())
        .await
        .with_openmaic_node(&node, &sha, &worker())
        .unwrap();
    let output = ex
        .derived_json(
            "course.openmaic.scene-build",
            request(),
            Duration::from_secs(10),
        )
        .await
        .unwrap();
    assert_eq!(output["exit_code"], 0);
    assert_eq!(output["document"]["status"], "CANDIDATE");
    assert_eq!(output["document"]["scene"]["id"], "scene_1");
    assert_eq!(
        output["document"]["source_binding"],
        "client_declared_unverified"
    );
    assert_eq!(output["document"]["canonical_bindings_verified"], false);
    assert_eq!(output["document"]["model_call"], "NOT_INVOKED");
    ex.store()
        .submit_wait(|conn| {
            archeaxis_store_sqlite::capability_settings::set_enabled(
                conn,
                "course.openmaic.scene-build",
                false,
            )
        })
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        ex.derived_json(
            "course.openmaic.scene-build",
            request(),
            Duration::from_secs(1)
        )
        .await
        .unwrap_err(),
        "derived capability is disabled"
    );
}
