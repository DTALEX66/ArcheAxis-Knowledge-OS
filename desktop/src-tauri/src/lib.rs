#[cfg(windows)]
pub mod backend;
#[cfg(windows)]
pub mod job;
pub mod navigation;
pub mod protocol;
pub mod runtime;

#[cfg(windows)]
use backend::BackendProcess;
#[cfg(windows)]
use navigation::navigation_allowed;
#[cfg(windows)]
use runtime::resolve_runtime_with_portable_root;
#[cfg(windows)]
use std::path::{Path, PathBuf};
#[cfg(windows)]
use std::sync::{Arc, Mutex};
#[cfg(windows)]
use tauri::webview::NewWindowResponse;
#[cfg(windows)]
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent};

#[cfg(windows)]
pub fn run() {
    if let Err(error) = run_inner() {
        show_startup_error(&error);
    }
}

#[cfg(not(windows))]
pub fn run() {
    panic!("ArcheAxis desktop shell is supported only on Windows");
}

#[cfg(windows)]
fn run_inner() -> Result<(), String> {
    let backend: Arc<Mutex<Option<BackendProcess>>> = Arc::new(Mutex::new(None));
    let setup_backend = Arc::clone(&backend);
    let app = tauri::Builder::default()
        .setup(move |app| {
            let result = (|| -> Result<(), String> {
                let resources = app
                    .path()
                    .resource_dir()
                    .map_err(|error| error.to_string())?;
                let local_data = app
                    .path()
                    .app_local_data_dir()
                    .map_err(|error| error.to_string())?;
                let portable_root = std::env::var_os("COGNITIVE_PORTABLE_ROOT").map(PathBuf::from);
                let runtime = resolve_runtime_with_portable_root(
                    Path::new(env!("CARGO_MANIFEST_DIR")),
                    &resources,
                    &local_data,
                    cfg!(debug_assertions),
                    portable_root.as_deref(),
                )?;
                let process = BackendProcess::launch(&runtime)?;
                let port = process.port;
                let url = format!("http://127.0.0.1:{port}/workspace")
                    .parse()
                    .map_err(|error| format!("invalid Workspace URL: {error}"))?;
                WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
                    .title("ArcheAxis Knowledge")
                    .inner_size(1280.0, 800.0)
                    .min_inner_size(960.0, 640.0)
                    .resizable(true)
                    .center()
                    .devtools(cfg!(debug_assertions))
                    .data_directory(runtime.data_dir.clone())
                    .on_navigation(move |target| navigation_allowed(target, port))
                    .on_new_window(|_, _| NewWindowResponse::Deny)
                    .on_download(|_, _| false)
                    .build()
                    .map_err(|error| format!("failed to create Workspace window: {error}"))?;
                *setup_backend
                    .lock()
                    .map_err(|_| "desktop backend state is poisoned".to_owned())? = Some(process);
                Ok(())
            })();
            if let Err(error) = result {
                show_startup_error(&error);
                app.handle().exit(1);
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                // WM_CLOSE is already being handled. Prevent Tauri's default
                // close path, destroy the native window explicitly, and let
                // the ExitRequested hook close the owned backend. The
                // prevent_close guard avoids re-entering this handler.
                api.prevent_close();
                let _ = window.destroy();
                window.app_handle().exit(0);
            }
        })
        .build(tauri::generate_context!())
        .map_err(|error| format!("desktop shell startup failed: {error}"))?;

    let exit_backend = Arc::clone(&backend);
    app.run(move |_handle, event| {
        if matches!(event, tauri::RunEvent::ExitRequested { .. })
            && let Ok(mut state) = exit_backend.lock()
            && let Some(process) = state.as_mut()
        {
            process.shutdown();
        }
    });
    Ok(())
}

#[cfg(windows)]
fn show_startup_error(message: &str) {
    use windows::Win32::UI::WindowsAndMessaging::{MB_ICONERROR, MB_OK, MessageBoxW};
    use windows::core::PCWSTR;

    let text: Vec<u16> = format!("ArcheAxis Knowledge 无法启动。\n\n{message}\0")
        .encode_utf16()
        .collect();
    let title: Vec<u16> = "ArcheAxis Knowledge\0".encode_utf16().collect();
    unsafe {
        let _ = MessageBoxW(
            None,
            PCWSTR(text.as_ptr()),
            PCWSTR(title.as_ptr()),
            MB_OK | MB_ICONERROR,
        );
    }
}
