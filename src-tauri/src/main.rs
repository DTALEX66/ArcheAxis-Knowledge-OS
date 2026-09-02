#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[cfg(windows)]
#[path = "recovery.rs"]
mod recovery;

#[cfg(all(test, windows))]
mod recovery_contract_tests {
    use super::recovery::{
        sanitize_recovery_message, validate_enumerated_backup_name, RecoveryLogTailDto,
        RecoveryState, RecoveryStatusDto,
    };
    use super::{
        try_operation_guard, try_refresh_if_idle, DesktopBackend, RECOVERY_OPERATION_IN_PROGRESS,
        RECOVERY_STATE_UNAVAILABLE,
    };
    use std::sync::{Arc, Mutex};

    const BACKUP_DISPLAY_NAME: &str = "cognitive_os_20260823T010203_000000Z.sqlite";

    fn idle_backend() -> DesktopBackend {
        DesktopBackend {
            process: Arc::new(Mutex::new(None)),
            runtime: Arc::new(Mutex::new(None)),
            resolver: Arc::new(Mutex::new(None)),
            recovery: Arc::new(Mutex::new(RecoveryState::booting(false))),
            operations: Arc::new(Mutex::new(())),
        }
    }

    #[test]
    fn recovery_reads_skip_refresh_and_writes_fail_fast_while_an_operation_runs() {
        let state = idle_backend();
        let operation = state.operations.lock().expect("operation lock");

        assert_eq!(try_refresh_if_idle(&state), Ok(false));
        assert!(matches!(
            try_operation_guard(&state),
            Err(error) if error == RECOVERY_OPERATION_IN_PROGRESS
        ));

        drop(operation);
        assert_eq!(try_refresh_if_idle(&state), Ok(true));
    }

    #[test]
    fn a_poisoned_operation_lock_is_not_reported_as_busy() {
        let state = idle_backend();
        let operations = state.operations.clone();
        let _ = std::thread::spawn(move || {
            let _operation = operations.lock().expect("operation lock");
            panic!("poison operation lock");
        })
        .join();

        assert_eq!(
            try_refresh_if_idle(&state),
            Err(RECOVERY_STATE_UNAVAILABLE.to_owned())
        );
        assert!(matches!(
            try_operation_guard(&state),
            Err(error) if error == RECOVERY_STATE_UNAVAILABLE
        ));
    }

    fn contains_forbidden_key(value: &serde_json::Value, forbidden: &str) -> bool {
        match value {
            serde_json::Value::Object(object) => object.iter().any(|(key, nested)| {
                key.eq_ignore_ascii_case(forbidden) || contains_forbidden_key(nested, forbidden)
            }),
            serde_json::Value::Array(items) => items
                .iter()
                .any(|nested| contains_forbidden_key(nested, forbidden)),
            _ => false,
        }
    }

    fn contains_forbidden_text(value: &serde_json::Value, forbidden: &str) -> bool {
        match value {
            serde_json::Value::String(text) => text.contains(forbidden),
            serde_json::Value::Object(object) => object
                .values()
                .any(|nested| contains_forbidden_text(nested, forbidden)),
            serde_json::Value::Array(items) => items
                .iter()
                .any(|nested| contains_forbidden_text(nested, forbidden)),
            _ => false,
        }
    }

    #[test]
    fn sanitization_is_bounded_and_removes_tokens_paths_and_http_bodies() {
        let input = format!(
            "token=launch-secret C:\\Users\\Alex\\private\\vault.db \\ \\\\server\\share \\ \
             http://127.0.0.1:4312/api body={{\"secret\":\"value\"}} {}",
            "x".repeat(512)
        );
        let sanitized = sanitize_recovery_message(&input);

        assert!(sanitized.len() <= 240);
        for forbidden in [
            "launch-secret",
            "C:\\Users\\Alex\\private\\vault.db",
            "\\\\server\\share",
            "http://127.0.0.1:4312/api",
            "\"secret\":\"value\"",
        ] {
            assert!(!sanitized.contains(forbidden), "leaked {forbidden}");
        }
    }

    #[test]
    fn restore_selection_rejects_traversal_and_unknown_backup_names() {
        let backups = [BACKUP_DISPLAY_NAME];

        assert!(validate_enumerated_backup_name(backups, BACKUP_DISPLAY_NAME).is_ok());
        for invalid in [
            "../private.axbak",
            "C:\\private.axbak",
            "backup/child.axbak",
            "unknown.axbak",
        ] {
            assert!(
                validate_enumerated_backup_name(backups, invalid).is_err(),
                "accepted {invalid}"
            );
        }
        let private_path = "C:\\Users\\Alex\\private\\cognitive_os_20260823T010203_000000Z.sqlite";
        assert!(
            validate_enumerated_backup_name([private_path], private_path).is_err(),
            "accepted an enumerated private path"
        );
    }

    #[test]
    fn invalid_backup_selection_diagnostic_is_fixed_and_contains_no_user_value() {
        let malicious_selection = "../private-token.sqlite";
        let mut state = RecoveryState::failed("Core startup is unavailable");

        state.record_diagnostic(super::RECOVERY_BACKUP_SELECTION_REJECTED);
        let logs = state.log_tail();

        assert_eq!(
            logs.lines.last().map(String::as_str),
            Some(super::RECOVERY_BACKUP_SELECTION_REJECTED)
        );
        assert!(!logs
            .lines
            .iter()
            .any(|line| line.contains(malicious_selection)));
    }

    #[test]
    fn safe_mode_stops_core_and_preserves_recovery_operations() {
        let mut state = RecoveryState::failed("Core startup is unavailable");

        state.enter_safe_mode();

        assert!(state.safe_mode());
        assert!(!state.may_start_core());
        assert!(!state.may_run_migrations());
        assert!(state.recovery_operations_available());
    }

    #[test]
    fn exit_dispatch_does_not_wait_for_a_long_operation_guard() {
        let operations = std::sync::Mutex::new(());
        let _long_operation = operations.lock().expect("hold long operation");
        let (sent, received) = std::sync::mpsc::sync_channel(1);

        super::dispatch_exit_immediately(|code| {
            sent.send(code).expect("record exit dispatch");
        });

        assert_eq!(
            received
                .recv_timeout(std::time::Duration::from_millis(100))
                .expect("exit dispatch was blocked"),
            0
        );
    }

    #[test]
    fn recovery_dtos_exclude_tokens_paths_and_request_response_bodies() {
        let unsafe_message = "token=launch-secret C:\\Users\\Alex\\private\\vault.db \
            http://127.0.0.1:4312/api request={\"body\":\"response-secret\"}";
        let private_backup =
            "C:\\Users\\Alex\\private\\cognitive_os_20260823T010203_000000Z.sqlite";
        let status = RecoveryStatusDto::failed(
            unsafe_message,
            vec![BACKUP_DISPLAY_NAME.into(), private_backup.into()],
        );
        let logs = RecoveryLogTailDto::new(vec![unsafe_message.into()]);
        let status = serde_json::to_value(status).expect("status must serialize");
        let logs = serde_json::to_value(logs).expect("logs must serialize");

        let status_object = status.as_object().expect("status DTO must be an object");
        assert!(status_object
            .get("state")
            .is_some_and(serde_json::Value::is_string));
        assert!(status_object
            .get("safe_mode")
            .is_some_and(serde_json::Value::is_boolean));
        assert!(status_object
            .get("backend_available")
            .is_some_and(serde_json::Value::is_boolean));
        assert!(status_object
            .get("message")
            .is_some_and(serde_json::Value::is_string));
        let backup_names = status_object
            .get("backups")
            .and_then(serde_json::Value::as_array)
            .expect("status DTO must contain backup display names");
        assert_eq!(backup_names.len(), 1);
        assert_eq!(backup_names[0].as_str(), Some(BACKUP_DISPLAY_NAME));

        let logs_object = logs.as_object().expect("log DTO must be an object");
        assert!(logs_object
            .get("lines")
            .is_some_and(serde_json::Value::is_array));

        for dto in [&status, &logs] {
            let object = dto.as_object().expect("recovery DTO must be an object");
            for forbidden in ["token", "path", "body", "request", "response", "secret"] {
                assert!(!object.contains_key(forbidden), "DTO exposed {forbidden}");
                assert!(
                    !contains_forbidden_key(dto, forbidden),
                    "DTO exposed nested {forbidden}"
                );
            }
            for forbidden in [
                "launch-secret",
                "C:\\Users\\Alex\\private\\vault.db",
                private_backup,
                "http://127.0.0.1:4312/api",
                "response-secret",
            ] {
                assert!(
                    !contains_forbidden_text(dto, forbidden),
                    "DTO serialized private value {forbidden}"
                );
            }
        }
    }
}

#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/backend.rs"]
mod backend;
#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/job.rs"]
mod job;
#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/protocol.rs"]
mod protocol;
#[cfg(windows)]
#[path = "../../desktop/src-tauri/src/runtime.rs"]
mod runtime;

#[cfg(windows)]
use backend::{run_restore_backup, BackendProcess};
#[cfg(windows)]
use recovery::{
    enumerate_backups, stage_backup_for_restore, validate_enumerated_backup_name, EnumeratedBackup,
    RecoveryLogTailDto, RecoveryState, RecoveryStatusDto,
};
#[cfg(windows)]
use serde::Serialize;
#[cfg(windows)]
use std::path::PathBuf;
#[cfg(windows)]
use std::sync::{Arc, Mutex, MutexGuard, TryLockError};
#[cfg(windows)]
use tauri::{AppHandle, Manager, State, WebviewUrl, WebviewWindowBuilder, WindowEvent};

#[cfg(windows)]
const RECOVERY_STATE_UNAVAILABLE: &str = "RECOVERY_STATE_UNAVAILABLE";
#[cfg(windows)]
const RECOVERY_RUNTIME_UNAVAILABLE: &str = "RECOVERY_RUNTIME_UNAVAILABLE";
#[cfg(windows)]
const RECOVERY_RETRY_FAILED: &str = "RECOVERY_RETRY_FAILED";
#[cfg(windows)]
const RECOVERY_OPERATION_IN_PROGRESS: &str = "RECOVERY_OPERATION_IN_PROGRESS";
#[cfg(windows)]
const RECOVERY_BACKUP_INVALID: &str = "RECOVERY_BACKUP_INVALID";
#[cfg(windows)]
const RECOVERY_RESTORE_FAILED: &str = "RECOVERY_RESTORE_FAILED";
#[cfg(windows)]
const RECOVERY_BACKUP_SELECTION_REJECTED: &str = "Backup selection was rejected";

#[cfg(windows)]
#[derive(Clone)]
struct RuntimeResolutionContext {
    manifest_dir: PathBuf,
    resource_dir: PathBuf,
    local_data_dir: PathBuf,
    portable_root: Option<PathBuf>,
}

#[cfg(windows)]
impl RuntimeResolutionContext {
    fn resolve(&self) -> Result<runtime::RuntimeSpec, String> {
        runtime::resolve_runtime_with_portable_root(
            &self.manifest_dir,
            &self.resource_dir,
            &self.local_data_dir,
            cfg!(debug_assertions),
            self.portable_root.as_deref(),
        )
    }
}

#[cfg(windows)]
#[derive(Clone)]
struct DesktopBackend {
    process: Arc<Mutex<Option<BackendProcess>>>,
    runtime: Arc<Mutex<Option<runtime::RuntimeSpec>>>,
    resolver: Arc<Mutex<Option<RuntimeResolutionContext>>>,
    recovery: Arc<Mutex<RecoveryState>>,
    operations: Arc<Mutex<()>>,
}

#[cfg(windows)]
#[derive(Serialize)]
struct BackendInfo {
    port: u16,
    token: String,
    scopes: Vec<String>,
}

#[cfg(windows)]
#[derive(Serialize)]
struct RestoreReceiptDto {
    status: &'static str,
}

#[cfg(windows)]
fn record_failure(state: &DesktopBackend, message: &str) {
    if let Ok(mut recovery) = state.recovery.lock() {
        recovery.record_failure(message);
    }
}

#[cfg(windows)]
fn try_operation_guard(state: &DesktopBackend) -> Result<MutexGuard<'_, ()>, String> {
    match state.operations.try_lock() {
        Ok(guard) => Ok(guard),
        Err(TryLockError::WouldBlock) => Err(RECOVERY_OPERATION_IN_PROGRESS.to_owned()),
        Err(TryLockError::Poisoned(_)) => Err(RECOVERY_STATE_UNAVAILABLE.to_owned()),
    }
}

#[cfg(windows)]
fn try_refresh_if_idle(state: &DesktopBackend) -> Result<bool, String> {
    let _operation = match state.operations.try_lock() {
        Ok(guard) => guard,
        Err(TryLockError::WouldBlock) => return Ok(false),
        Err(TryLockError::Poisoned(_)) => return Err(RECOVERY_STATE_UNAVAILABLE.to_owned()),
    };
    refresh_backend_state(state)?;
    Ok(true)
}

#[cfg(windows)]
fn record_invalid_backup_selection(state: &DesktopBackend) {
    if let Ok(mut recovery) = state.recovery.lock() {
        recovery.record_diagnostic(RECOVERY_BACKUP_SELECTION_REJECTED);
    }
}

#[cfg(windows)]
fn refresh_backend_state(state: &DesktopBackend) -> Result<(), String> {
    let (diagnostic, removed_process) = {
        let mut process = state
            .process
            .lock()
            .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?;
        let diagnostic = match process.as_mut() {
            Some(process) => process.exit_diagnostic(),
            None => return Ok(()),
        };
        match diagnostic {
            Ok(Some(message)) => {
                let removed = process.take();
                (Some(message), removed)
            }
            Ok(None) => (None, None),
            Err(message) => {
                let removed = process.take();
                (Some(message), removed)
            }
        }
    };
    drop(removed_process);
    if let Some(message) = diagnostic {
        record_failure(state, &message);
    }
    Ok(())
}

#[cfg(windows)]
fn current_runtime(state: &DesktopBackend) -> Result<Option<runtime::RuntimeSpec>, String> {
    state
        .runtime
        .lock()
        .map(|runtime| runtime.clone())
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())
}

#[cfg(windows)]
fn fresh_backups(runtime: Option<&runtime::RuntimeSpec>) -> Result<Vec<EnumeratedBackup>, String> {
    let Some(runtime) = runtime else {
        return Ok(Vec::new());
    };
    enumerate_backups(&runtime.data_dir)
}

#[cfg(windows)]
fn recovery_status_dto(
    state: &DesktopBackend,
    runtime: Option<&runtime::RuntimeSpec>,
) -> Result<RecoveryStatusDto, String> {
    let backups = match fresh_backups(runtime) {
        Ok(backups) => backups,
        Err(error) => {
            if let Ok(mut recovery) = state.recovery.lock() {
                recovery.record_diagnostic(&error);
            }
            Vec::new()
        }
    };
    let names = backups.into_iter().map(|backup| backup.name).collect();
    state
        .recovery
        .lock()
        .map(|recovery| recovery.status(names))
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())
}

#[cfg(windows)]
fn recovery_status_snapshot(state: &DesktopBackend) -> Result<RecoveryStatusDto, String> {
    state
        .recovery
        .lock()
        .map(|recovery| recovery.status(Vec::new()))
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())
}

#[cfg(windows)]
#[tauri::command]
fn backend_info(state: State<'_, DesktopBackend>) -> Result<Option<BackendInfo>, String> {
    if !try_refresh_if_idle(&state)? {
        return Ok(None);
    }
    let backend = state
        .process
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?;
    Ok(backend.as_ref().map(|process| BackendInfo {
        port: process.port,
        token: process.token.clone(),
        scopes: vec!["workspace:write".to_owned()],
    }))
}

#[cfg(windows)]
#[tauri::command]
async fn retry_backend(state: State<'_, DesktopBackend>) -> Result<BackendInfo, String> {
    let state = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || retry_backend_blocking(state))
        .await
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
}

#[cfg(windows)]
fn retry_backend_blocking(state: DesktopBackend) -> Result<BackendInfo, String> {
    let _operation = try_operation_guard(&state)?;
    refresh_backend_state(&state)?;
    if let Some(existing) = state
        .process
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
        .as_ref()
    {
        return Ok(BackendInfo {
            port: existing.port,
            token: existing.token.clone(),
            scopes: vec!["workspace:write".to_owned()],
        });
    }
    state
        .recovery
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
        .begin_retry();
    let runtime = match current_runtime(&state)? {
        Some(runtime) => runtime,
        None => {
            let resolver = state
                .resolver
                .lock()
                .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
                .clone()
                .ok_or_else(|| RECOVERY_RUNTIME_UNAVAILABLE.to_owned())?;
            match resolver.resolve() {
                Ok(runtime) => {
                    *state
                        .runtime
                        .lock()
                        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())? =
                        Some(runtime.clone());
                    state
                        .recovery
                        .lock()
                        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
                        .set_external_dev(runtime.external_dev);
                    runtime
                }
                Err(error) => {
                    record_failure(&state, &error);
                    return Err(RECOVERY_RUNTIME_UNAVAILABLE.to_owned());
                }
            }
        }
    };
    let launched = match BackendProcess::launch(&runtime) {
        Ok(process) => process,
        Err(error) => {
            record_failure(&state, &error);
            return Err(RECOVERY_RETRY_FAILED.to_owned());
        }
    };
    let info = BackendInfo {
        port: launched.port,
        token: launched.token.clone(),
        scopes: vec!["workspace:write".to_owned()],
    };
    *state
        .process
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())? = Some(launched);
    state
        .recovery
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
        .mark_ready();
    Ok(info)
}

#[cfg(windows)]
#[tauri::command]
fn recovery_status(state: State<'_, DesktopBackend>) -> Result<RecoveryStatusDto, String> {
    if !try_refresh_if_idle(&state)? {
        return recovery_status_snapshot(&state);
    }
    let runtime = current_runtime(&state)?;
    recovery_status_dto(&state, runtime.as_ref())
}

#[cfg(windows)]
#[tauri::command]
fn recovery_log_tail(state: State<'_, DesktopBackend>) -> Result<RecoveryLogTailDto, String> {
    try_refresh_if_idle(&state)?;
    state
        .recovery
        .lock()
        .map(|recovery| recovery.log_tail())
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())
}

#[cfg(windows)]
#[tauri::command]
async fn enter_safe_mode(state: State<'_, DesktopBackend>) -> Result<RecoveryStatusDto, String> {
    let state = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || enter_safe_mode_blocking(state))
        .await
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
}

#[cfg(windows)]
fn enter_safe_mode_blocking(state: DesktopBackend) -> Result<RecoveryStatusDto, String> {
    let _operation = try_operation_guard(&state)?;
    state
        .recovery
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
        .enter_safe_mode();
    let process = state
        .process
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
        .take();
    if let Some(mut process) = process {
        process.shutdown();
    }
    let runtime = current_runtime(&state)?;
    recovery_status_dto(&state, runtime.as_ref())
}

#[cfg(windows)]
#[tauri::command]
async fn restore_backup(
    state: State<'_, DesktopBackend>,
    name: String,
) -> Result<RestoreReceiptDto, String> {
    let state = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || restore_backup_blocking(state, name))
        .await
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
}

#[cfg(windows)]
fn restore_backup_blocking(
    state: DesktopBackend,
    name: String,
) -> Result<RestoreReceiptDto, String> {
    let _operation = try_operation_guard(&state)?;
    let runtime =
        current_runtime(&state)?.ok_or_else(|| RECOVERY_RUNTIME_UNAVAILABLE.to_owned())?;
    let backups = enumerate_backups(&runtime.data_dir).map_err(|error| {
        if let Ok(mut recovery) = state.recovery.lock() {
            recovery.record_diagnostic(&error);
        }
        RECOVERY_BACKUP_INVALID.to_owned()
    })?;
    if validate_enumerated_backup_name(backups.iter().map(|backup| backup.name.as_str()), &name)
        .is_err()
    {
        record_invalid_backup_selection(&state);
        return Err(RECOVERY_BACKUP_INVALID.to_owned());
    }
    let initially_selected = match backups.into_iter().find(|backup| backup.name == name) {
        Some(selected) => selected,
        None => {
            record_invalid_backup_selection(&state);
            return Err(RECOVERY_BACKUP_INVALID.to_owned());
        }
    };
    state
        .recovery
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
        .enter_safe_mode();
    let process = state
        .process
        .lock()
        .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
        .take();
    if let Some(mut process) = process {
        process.shutdown();
    }
    let fresh_backups = enumerate_backups(&runtime.data_dir).map_err(|error| {
        if let Ok(mut recovery) = state.recovery.lock() {
            recovery.record_safe_mode_failure(&error);
        }
        RECOVERY_BACKUP_INVALID.to_owned()
    })?;
    let selected = match fresh_backups.into_iter().find(|backup| backup.name == name) {
        Some(selected) => selected,
        None => {
            record_invalid_backup_selection(&state);
            return Err(RECOVERY_BACKUP_INVALID.to_owned());
        }
    };
    if !initially_selected.same_source_identity(&selected) {
        record_invalid_backup_selection(&state);
        return Err(RECOVERY_BACKUP_INVALID.to_owned());
    }
    let staged = stage_backup_for_restore(&runtime.data_dir, &selected).map_err(|_| {
        record_invalid_backup_selection(&state);
        RECOVERY_BACKUP_INVALID.to_owned()
    })?;
    staged.revalidate_for_restore().map_err(|_| {
        record_invalid_backup_selection(&state);
        RECOVERY_BACKUP_INVALID.to_owned()
    })?;
    match run_restore_backup(&runtime, staged.backup_path()) {
        Ok(()) => {
            state
                .recovery
                .lock()
                .map_err(|_| RECOVERY_STATE_UNAVAILABLE.to_owned())?
                .mark_restore_success();
            Ok(RestoreReceiptDto { status: "restored" })
        }
        Err(error) => {
            if let Ok(mut recovery) = state.recovery.lock() {
                recovery.record_safe_mode_failure(&error);
            }
            Err(RECOVERY_RESTORE_FAILED.to_owned())
        }
    }
}

#[cfg(windows)]
fn dispatch_exit_immediately<F>(exit: F)
where
    F: FnOnce(i32),
{
    exit(0);
}

#[cfg(windows)]
fn cleanup_backend_on_exit(state: DesktopBackend) {
    std::thread::spawn(move || {
        let process = state
            .process
            .lock()
            .ok()
            .and_then(|mut process| process.take());
        if let Some(mut process) = process {
            process.shutdown();
        }
    });
}

#[cfg(windows)]
#[tauri::command]
fn exit_application(app: AppHandle) -> Result<(), String> {
    dispatch_exit_immediately(|code| {
        app.exit(code);
    });
    Ok(())
}

#[cfg(windows)]
fn main() {
    let backend = DesktopBackend {
        process: Arc::new(Mutex::new(None)),
        runtime: Arc::new(Mutex::new(None)),
        resolver: Arc::new(Mutex::new(None)),
        recovery: Arc::new(Mutex::new(RecoveryState::booting(false))),
        operations: Arc::new(Mutex::new(())),
    };
    let startup_backend = backend.clone();
    let exit_backend = backend.clone();
    let app = tauri::Builder::default()
        .manage(backend)
        .invoke_handler(tauri::generate_handler![
            backend_info,
            recovery_status,
            recovery_log_tail,
            enter_safe_mode,
            retry_backend,
            restore_backup,
            exit_application,
        ])
        .setup(move |app| {
            let resources = app
                .path()
                .resource_dir()
                .map_err(|_| std::io::Error::other("RECOVERY_RESOURCE_DIR_UNAVAILABLE"))?;
            let local_data = app
                .path()
                .app_local_data_dir()
                .map_err(|_| std::io::Error::other("RECOVERY_DATA_DIR_UNAVAILABLE"))?;
            let legacy_manifest =
                PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../desktop/src-tauri");
            let portable_root = match std::env::current_exe() {
                Ok(executable) => runtime::portable_root_for_executable(&executable),
                Err(error) => {
                    if let Ok(mut recovery) = startup_backend.recovery.lock() {
                        recovery.record_diagnostic(&error.to_string());
                    }
                    None
                }
            };
            let resolver = RuntimeResolutionContext {
                manifest_dir: legacy_manifest,
                resource_dir: resources,
                local_data_dir: local_data.clone(),
                portable_root,
            };
            *startup_backend
                .resolver
                .lock()
                .map_err(|_| std::io::Error::other(RECOVERY_STATE_UNAVAILABLE))? =
                Some(resolver.clone());
            let resolved_runtime = resolver.resolve();
            let webview_data_dir = resolved_runtime
                .as_ref()
                .map(|resolved| resolved.data_dir.clone())
                .unwrap_or_else(|_| local_data.clone());
            // Create the packaged Recovery WebView before migration/Core startup.
            // Backend launch can take up to the migration + readiness timeout;
            // it must never leave the user staring at an absent window.
            let pending_runtime = match resolved_runtime {
                Ok(runtime) => {
                    *startup_backend
                        .runtime
                        .lock()
                        .map_err(|_| std::io::Error::other(RECOVERY_STATE_UNAVAILABLE))? =
                        Some(runtime.clone());
                    *startup_backend
                        .recovery
                        .lock()
                        .map_err(|_| std::io::Error::other(RECOVERY_STATE_UNAVAILABLE))? =
                        RecoveryState::booting(runtime.external_dev);
                    Some(runtime)
                }
                Err(error) => {
                    record_failure(&startup_backend, &error);
                    None
                }
            };
            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("星环知识平台（ArcheAxis Knowledge）")
                .inner_size(1280.0, 800.0)
                .data_directory(webview_data_dir)
                .build()
                .map_err(|_| std::io::Error::other("RECOVERY_WINDOW_CREATE_FAILED"))?;
            if let Some(runtime) = pending_runtime {
                let launch_state = startup_backend.clone();
                std::thread::spawn(move || {
                    let Ok(_operation) = launch_state.operations.lock() else {
                        record_failure(&launch_state, RECOVERY_STATE_UNAVAILABLE);
                        return;
                    };
                    match BackendProcess::launch(&runtime) {
                        Ok(process) => {
                            if let Ok(mut slot) = launch_state.process.lock() {
                                *slot = Some(process);
                            } else {
                                record_failure(&launch_state, RECOVERY_STATE_UNAVAILABLE);
                                return;
                            }
                            if let Ok(mut recovery) = launch_state.recovery.lock() {
                                recovery.mark_ready();
                            } else {
                                record_failure(&launch_state, RECOVERY_STATE_UNAVAILABLE);
                            }
                        }
                        Err(error) => record_failure(&launch_state, &error),
                    }
                });
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::CloseRequested { .. }) {
                // Let Tauri's native close path end the window and event loop.
                // Blocking or preventing WM_CLOSE here has proved racy on a
                // packaged Windows shell. Core is held by a KILL_ON_JOB_CLOSE
                // Job Object, so a process that exits before graceful teardown
                // still reclaims the owned child process.
                let state = window
                    .app_handle()
                    .state::<DesktopBackend>()
                    .inner()
                    .clone();
                cleanup_backend_on_exit(state);
            }
        })
        .build(tauri::generate_context!())
        .expect("ArcheAxis desktop shell startup failed");

    app.run(move |_handle, event| {
        if matches!(event, tauri::RunEvent::ExitRequested { .. }) {
            let state = exit_backend.clone();
            // ExitRequested runs on Tauri's event loop. Keep its Core teardown
            // non-blocking; the Windows Job Object still owns the child if the
            // process exits before graceful shutdown ends.
            cleanup_backend_on_exit(state);
        }
    });
}

#[cfg(not(windows))]
fn main() {
    panic!("ArcheAxis desktop shell is supported only on Windows");
}
