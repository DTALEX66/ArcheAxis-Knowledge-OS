//! Run the synthetic asset-correction journey against Cargo's actual Core binary.
//!
//! The worker and human decisions are fixtures; this does not measure model
//! quality, real user learning, or an installed product.
use std::{path::PathBuf, process::Command};

#[test]
fn synthetic_asset_formal_retest_uses_current_core_and_survives_restore() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let python = std::env::var_os("ARCHEAXIS_PYTHON")
        .expect("ARCHEAXIS_PYTHON must select the project test interpreter");
    let work = tempfile::tempdir().expect("isolated test directory");
    let receipt = work.path().join("asset-formal-retest.json");
    let basetemp = work.path().join("pytest");
    let output = Command::new(python)
        .current_dir(&repo)
        .env("AAOS_TEST_CORE_EXE", env!("CARGO_BIN_EXE_archeaxis-api"))
        .env_remove("AAOS_TEST_CORE_SHA256")
        .env("AAOS_TEST_ASSET_RETEST_REAL_MODEL", "0")
        .env("AAOS_TEST_ASSET_RETEST_OUTPUT", &receipt)
        .args([
            "-B",
            "-m",
            "pytest",
            "tests/contract/test_ai_asset_formal_retest_real_core.py",
            "-q",
            "--tb=short",
            "--basetemp",
        ])
        .arg(basetemp)
        .output()
        .expect("start real-Core synthetic retest");
    assert!(
        output.status.success(),
        "real-Core synthetic retest failed ({:?})\nstdout:\n{}\nstderr:\n{}",
        output.status.code(),
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let data = std::fs::read(&receipt).expect("retest skipped or did not write its receipt");
    let result: serde_json::Value = serde_json::from_slice(&data).expect("valid retest receipt");
    assert_eq!(result["worker_mode"], "synthetic_fixture");
    assert_eq!(result["fixture_worker_invocations"], 3);
    assert_eq!(result["old_asset_references"], "historical_and_superseded");
    assert_eq!(result["revised_asset_reference_states"], "current");
    assert_eq!(result["restart_cached_without_worker"], true);
    assert_eq!(result["independent_restore"], true);
    assert_eq!(result["restored_old_grants_fenced"], true);
    assert_eq!(result["old_asset_grant_independently_fenced"], true);
    assert_eq!(result["old_knowledge_grant_independently_fenced"], true);
    assert_eq!(result["fresh_retest_after_restore"], true);
}
