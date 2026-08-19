// R5: ArcheAxis desktop shell (scaffold). Build BLOCKED locally: cargo not installed.
// Backend (FastAPI) is spawned as a supervised child process; this shell only
// hosts the React build and supervises the backend (see docs/R5 plan).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running ArcheAxis desktop");
}
