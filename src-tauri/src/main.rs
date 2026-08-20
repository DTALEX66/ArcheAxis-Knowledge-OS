#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/backend.rs"]
mod backend;
#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/job.rs"]
mod job;
#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/runtime.rs"]
mod runtime;
#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/protocol.rs"]
mod protocol;

#[cfg(windows)]
use backend::BackendProcess;
#[cfg(windows)]
use serde::Serialize;
#[cfg(windows)]
use std::path::{Path, PathBuf};
#[cfg(windows)]
use std::sync::{Arc, Mutex};
#[cfg(windows)]
use std::time::Duration;
#[cfg(windows)]
use tauri::{Manager, State, WebviewUrl, WebviewWindowBuilder, WindowEvent};

#[cfg(windows)]
const CLOSE_WATCHDOG_TIMEOUT: Duration = Duration::from_secs(12);

#[cfg(windows)]
#[derive(Clone)]
struct DesktopBackend {
    process: Arc<Mutex<Option<BackendProcess>>>,
    runtime: Arc<Mutex<Option<runtime::RuntimeSpec>>>,
}

#[cfg(windows)]
#[derive(Serialize)]
struct BackendInfo {
    port: u16,
    token: String,
}

#[cfg(windows)]
#[tauri::command]
fn backend_info(state: State<'_, DesktopBackend>) -> Result<Option<BackendInfo>, String> {
    let backend = state
        .process
        .lock()
        .map_err(|_| "desktop backend state is poisoned".to_owned())?;
    Ok(backend.as_ref().map(|process| BackendInfo {
        port: process.port,
        token: process.token.clone(),
    }))
}

#[cfg(windows)]
#[tauri::command]
fn retry_backend(state: State<'_, DesktopBackend>) -> Result<BackendInfo, String> {
    let mut process = state
        .process
        .lock()
        .map_err(|_| "desktop backend state is poisoned".to_owned())?;
    if let Some(existing) = process.as_ref() {
        return Ok(BackendInfo {
            port: existing.port,
            token: existing.token.clone(),
        });
    }
    let runtime = state
        .runtime
        .lock()
        .map_err(|_| "desktop runtime state is poisoned".to_owned())?
        .clone()
        .ok_or_else(|| "desktop runtime could not be resolved during startup".to_owned())?;
    let launched = BackendProcess::launch(&runtime)?;
    let info = BackendInfo {
        port: launched.port,
        token: launched.token.clone(),
    };
    *process = Some(launched);
    Ok(info)
}

#[cfg(windows)]
fn main() {
    let backend = DesktopBackend {
        process: Arc::new(Mutex::new(None)),
        runtime: Arc::new(Mutex::new(None)),
    };
    let startup_backend = backend.clone();
    let exit_backend = backend.clone();
    let app = tauri::Builder::default()
        .manage(backend)
        .invoke_handler(tauri::generate_handler![backend_info, retry_backend])
        .setup(move |app| {
            let resources = app.path().resource_dir()?;
            let local_data = app.path().app_local_data_dir()?;
            let legacy_manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../desktop/src-tauri");
            let executable = std::env::current_exe()?;
            let portable_root = runtime::portable_root_for_executable(&executable);
            let runtime = runtime::resolve_runtime_with_portable_root(
                Path::new(&legacy_manifest),
                &resources,
                &local_data,
                cfg!(debug_assertions),
                portable_root.as_deref(),
            );
            let webview_data_dir = runtime
                .as_ref()
                .map(|resolved| resolved.data_dir.clone())
                .unwrap_or_else(|_| local_data.clone());
            // A failed Core start must leave the packaged UI running. The UI
            // exposes only the retry command and cannot obtain a loopback
            // token until this state successfully launches.
            if let Ok(runtime) = runtime {
                *startup_backend
                    .runtime
                    .lock()
                    .map_err(|_| std::io::Error::other("desktop runtime state is poisoned"))? = Some(runtime.clone());
                if let Ok(process) = BackendProcess::launch(&runtime) {
                    *startup_backend
                        .process
                        .lock()
                        .map_err(|_| std::io::Error::other("desktop backend state is poisoned"))? = Some(process);
                }
            }
            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("ArcheAxis Learning Workspace")
                .inner_size(1280.0, 800.0)
                .data_directory(webview_data_dir)
                .build()?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                // The Windows close request alone does not reliably end the
                // Tauri run loop on the packaged shell.  The backend shutdown
                // can wait for up to several seconds, so do not perform it on
                // the native event loop that must dispatch the exit request.
                api.prevent_close();
                // Tauri requires exit requests to be issued outside the
                // event-loop callback that received CloseRequested.  Do not
                // synchronously destroy the window here: that can deadlock
                // the same native event loop before the exit is dispatched.
                // Do not wait for a command that may be launching/retrying
                // Core: the Job Object will reclaim any process that remains
                // owned when the application exits.
                let process = window
                    .app_handle()
                    .state::<DesktopBackend>()
                    .process
                    .try_lock()
                    .ok()
                    .and_then(|mut state| state.take());
                let app_handle = window.app_handle().clone();
                std::thread::spawn(move || {
                    // A failed Core stop must not make a healthy desktop
                    // window survive WM_CLOSE indefinitely. The normal
                    // shutdown worker wins first; this is only a bounded
                    // escape hatch before the installer verifier's timeout.
                    // AppHandle::exit depends on the Tauri event loop, which
                    // is precisely the component that may be unresponsive
                    // here. The Job Object owns Core and kills it when this
                    // Windows process closes its handles.
                    std::thread::sleep(CLOSE_WATCHDOG_TIMEOUT);
                    std::process::exit(0);
                });
                std::thread::spawn(move || {
                    if let Some(mut process) = process {
                        process.shutdown();
                    }
                    app_handle.exit(0);
                });
            }
        })
        .build(tauri::generate_context!())
        .expect("ArcheAxis desktop shell startup failed");

    app.run(move |_handle, event| {
        if matches!(event, tauri::RunEvent::ExitRequested { .. }) {
            let process = exit_backend
                .process
                .try_lock()
                .ok()
                .and_then(|mut state| state.take());
            if let Some(mut process) = process {
                // ExitRequested also runs on Tauri's event loop. Keep its
                // Core teardown non-blocking; the Windows Job Object owns the
                // child if the process exits before graceful shutdown ends.
                std::thread::spawn(move || process.shutdown());
            }
        }
    });
}

#[cfg(not(windows))]
fn main() {
    panic!("ArcheAxis desktop shell is supported only on Windows");
}
