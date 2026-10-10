use std::{env, fs, path::Path};

fn watch_tree(path: &Path) {
    println!("cargo:rerun-if-changed={}", path.display());
    let Ok(entries) = fs::read_dir(path) else {
        return;
    };
    for entry in entries.flatten() {
        let entry_path = entry.path();
        if entry_path.is_dir() {
            watch_tree(&entry_path);
        } else {
            println!("cargo:rerun-if-changed={}", entry_path.display());
        }
    }
}

fn main() {
    // Tauri's frontend is embedded in the Windows executable. Cargo otherwise
    // sees only Rust source changes and may reuse stale embedded assets.
    println!("cargo:rerun-if-env-changed=ARCHEAXIS_FRONTEND_DIST");
    println!("cargo:rerun-if-env-changed=TAURI_CONFIG");
    let manifest = std::path::PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let config: serde_json::Value =
        serde_json::from_str(&env::var("TAURI_CONFIG").unwrap_or_else(|_| "{}".to_owned()))
            .expect("invalid effective Tauri configuration");
    if let Ok(routed) = env::var("ARCHEAXIS_FRONTEND_DIST") {
        let explicit = config
            .pointer("/build/frontendDist")
            .and_then(serde_json::Value::as_str)
            .expect("routed Tauri frontend directory is missing");
        // FrontendDist tries Url before Directory. An absolute D:\\ path becomes
        // an external/file URL and silently disables embedding on Windows.
        assert!(!Path::new(explicit).is_absolute() && !explicit.contains(':'));
        assert_eq!(
            fs::canonicalize(manifest.join(explicit)).expect("frontend directory missing"),
            fs::canonicalize(routed).expect("routed frontend directory missing"),
            "Tauri embedding and frontend run paths differ"
        );
        let merged = config.to_string();
        env::set_var("TAURI_CONFIG", &merged);
        println!("cargo:rustc-env=TAURI_CONFIG={merged}");
    }
    let base: serde_json::Value = serde_json::from_str(include_str!("tauri.conf.json")).unwrap();
    let frontend_dist = config
        .pointer("/build/frontendDist")
        .or_else(|| base.pointer("/build/frontendDist"))
        .and_then(serde_json::Value::as_str)
        .expect("effective frontendDist must be a directory");
    watch_tree(&manifest.join(frontend_dist));
    tauri_build::build()
}
