from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_root_tauri_config_has_restrictive_csp_and_no_legacy_product_name() -> None:
    config = json.loads((ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    assert config["productName"] == "ArcheAxis Knowledge"
    csp = config["app"]["security"]["csp"]
    assert isinstance(csp, str) and csp
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "http://127.0.0.1:*" in csp
    connect_source = csp.split("connect-src", 1)[1].split(";", 1)[0]
    assert "connect-src *" not in csp
    assert "https:" not in connect_source
    frame_source = csp.split("frame-src", 1)[1].split(";", 1)[0]
    assert "blob:" in frame_source
    assert "http:" not in frame_source and "https:" not in frame_source


def test_root_desktop_keeps_the_recovery_ui_alive_and_retries_core_locally() -> None:
    source = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    assert "fn retry_backend" in source
    setup = source[source.index(".setup(move |app|") : source.index(".on_window_event")]
    assert setup.index("WebviewWindowBuilder::new") < setup.index("std::thread::spawn")
    assert setup.index("std::thread::spawn") < setup.index("launch_product_backend(&runtime)")
    helper = source[
        source.index("fn launch_product_backend(") : source.index("struct RuntimeResolutionContext")
    ]
    assert "CoreSpec::beside_runtime(runtime)" in helper
    assert "BackendProcess::launch_core(&spec)" in helper
    assert "None => BackendProcess::launch(runtime)" in helper
    retry = source[source.index("fn retry_backend_blocking(") : source.index("fn recovery_status(")]
    assert "launch_product_backend(&runtime)" in retry
    assert "Create the packaged Recovery WebView before migration/Core startup" in source


def test_recovery_reads_never_wait_for_the_long_backend_launch_operation() -> None:
    source = (ROOT / "src-tauri/src/main.rs").read_text(encoding="utf-8")
    status = source[source.index("fn recovery_status(") : source.index("fn recovery_log_tail(")]
    log_tail = source[
        source.index("fn recovery_log_tail(") : source.index("async fn enter_safe_mode(")
    ]
    backend_info = source[
        source.index("fn backend_info(") : source.index("async fn retry_backend(")
    ]
    retry = source[source.index("fn retry_backend_blocking(") : source.index("fn recovery_status(")]
    safe_mode = source[
        source.index("fn enter_safe_mode_blocking(") : source.index("fn restore_backup_blocking(")
    ]

    restore = source[
        source.index("fn restore_backup_blocking(") : source.index("fn dispatch_exit_immediately")
    ]

    assert "fn try_refresh_if_idle" in source
    assert "TryLockError::WouldBlock" in source
    assert "TryLockError::Poisoned" in source
    for read_only_command in (status, log_tail, backend_info):
        assert "try_refresh_if_idle" in read_only_command
    assert "return recovery_status_snapshot(&state);" in status
    for write_command in (retry, safe_mode, restore):
        assert "try_operation_guard" in write_command
    assert safe_mode.index(".enter_safe_mode()") < safe_mode.index("process.shutdown()")
    assert restore.index(".enter_safe_mode()") < restore.index("process.shutdown()")
    assert "RECOVERY_OPERATION_IN_PROGRESS" in source


def test_root_desktop_registers_the_complete_narrow_recovery_command_surface() -> None:
    source = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    handler = re.search(
        r"invoke_handler\s*\(\s*tauri::generate_handler!\s*\[([^\]]+)\]",
        source,
        flags=re.DOTALL,
    )
    assert handler is not None, "Tauri command dispatcher is required"
    registered = {command.strip() for command in handler.group(1).split(",") if command.strip()}
    required = {
        "backend_info",
        "core_command",
        "recovery_status",
        "recovery_log_tail",
        "enter_safe_mode",
        "retry_backend",
        "restore_backup",
        "exit_application",
    }
    assert required <= registered, (
        "the webview must receive recovery data and operations only through "
        "the narrow Tauri command surface"
    )


def test_desktop_keeps_launch_credentials_in_host_and_projects_only_ready() -> None:
    source = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    backend_source = (ROOT / "desktop" / "src-tauri" / "src" / "backend.rs").read_text(
        encoding="utf-8"
    )
    info = re.search(r"struct BackendInfo\s*\{([^}]+)\}", source)
    assert info is not None
    assert re.findall(r"(\w+)\s*:", info.group(1)) == ["ready"]
    assert "ready: bool" in info.group(1)
    assert "ARCHEAXIS_DESKTOP_WRITE_SCOPES" in backend_source
    bridge = (ROOT / "src-tauri/src/core_bridge.rs").read_text(encoding="utf-8")
    request = re.search(
        r"#\[serde\(deny_unknown_fields\)\]\s*pub struct Request\s*\{([^}]+)\}", bridge
    )
    assert request is not None
    assert re.findall(r"pub (\w+)\s*:", request.group(1)) == ["operation", "payload"]
    assert "pub operation: Operation" in request.group(1)
    operation = re.search(r"pub enum Operation\s*\{([^}]+)\}", bridge)
    assert operation is not None
    assert not {"Http", "Request", "Url", "Shell", "ExecuteCommand"} & set(
        re.findall(r"\b\w+\b", operation.group(1))
    )
    assert "value.len() > 128" in bridge
    assert "c.is_ascii_alphanumeric() || c == b'-' || c == b'_'" in bridge
    assert '"CORE_COMMAND_ID_INVALID"' in bridge
    assert "> 8 * 1024 * 1024" in bridge and '"CORE_COMMAND_BODY_TOO_LARGE"' in bridge
    assert ".no_proxy()" in bridge and "reqwest::redirect::Policy::none()" in bridge
    assert 'format!("http://127.0.0.1:{port}{path}")' in bridge
    assert '.header("X-ArcheAxis-Launch-Token", token)' in bridge
    command = source[
        source.index("async fn core_command(") : source.index("async fn retry_backend(")
    ]
    assert "process.port != port || process.token != token" in command
    assert '"CORE_WORKSPACE_CHANGED"' in command
    assert command.index("drop(operation)") < command.index(
        "core_bridge::execute(port, &token, request)"
    )
    assert command.index('"CORE_WORKSPACE_CHANGED"') < command.index("core_bridge::save_export")
