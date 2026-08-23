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


def test_root_desktop_keeps_the_recovery_ui_alive_and_retries_core_locally() -> None:
    source = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    assert "fn retry_backend" in source
    assert "if let Ok(process) = BackendProcess::launch(&runtime)" in source
    assert "failed Core start must leave the packaged UI running" in source


def test_root_desktop_registers_the_complete_narrow_recovery_command_surface() -> None:
    source = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    handler = re.search(
        r"invoke_handler\s*\(\s*tauri::generate_handler!\s*\[([^\]]+)\]",
        source,
        flags=re.DOTALL,
    )
    assert handler is not None, "Tauri command dispatcher is required"
    registered = {
        command.strip()
        for command in handler.group(1).split(",")
        if command.strip()
    }
    required = {
        "backend_info",
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


def test_desktop_issues_workspace_write_scope_to_core_and_backend_info() -> None:
    source = (ROOT / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    backend_source = (ROOT / "desktop" / "src-tauri" / "src" / "backend.rs").read_text(
        encoding="utf-8"
    )
    assert 'scopes: vec!["workspace:write".to_owned()]' in source
    assert "ARCHEAXIS_DESKTOP_WRITE_SCOPES" in backend_source
