#![cfg(windows)]

use archeaxis_desktop_shell::backend::BackendProcess;
use archeaxis_desktop_shell::runtime::RuntimeSpec;
use std::path::PathBuf;

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .expect("desktop manifest must live below the repository root")
        .to_path_buf()
}

#[test]
#[ignore = "explicit Windows lifecycle smoke"]
fn launches_token_bound_core_and_shuts_down_cleanly() {
    let root = repository_root();
    let runtime = RuntimeSpec {
        python: root.join(".venv/Scripts/python.exe"),
        cwd: root.clone(),
        data_dir: root.join(".hermes/task-runtime/desktop-rust-lifecycle-smoke"),
        isolated: false,
        external_dev: true,
    };

    let mut backend = BackendProcess::launch(&runtime)
        .unwrap_or_else(|error| panic!("backend launch failed:\n{error}"));
    assert!(backend.port > 0);
    backend.shutdown();
    assert!(!backend.log_tail().is_empty());
}

#[test]
#[ignore = "explicit installed-runtime lifecycle smoke"]
fn installed_core_launches_in_isolated_mode_and_shuts_down_cleanly() {
    let root = repository_root();
    let data_dir = root.join(".hermes/task-runtime/desktop-installed-lifecycle-smoke");
    std::fs::create_dir_all(&data_dir).expect("installed-runtime data directory must exist");
    let runtime = RuntimeSpec {
        python: root.join(".hermes/rt/runtime/python/python.exe"),
        cwd: data_dir.clone(),
        data_dir,
        isolated: true,
        external_dev: false,
    };

    let mut backend = BackendProcess::launch(&runtime)
        .unwrap_or_else(|error| panic!("installed backend launch failed:\n{error}"));
    assert!(backend.port > 0);
    backend.shutdown();
    assert!(!backend.log_tail().is_empty());
}
