use std::{fs, path::Path};

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
    watch_tree(Path::new("../frontend/dist"));
    tauri_build::build()
}
