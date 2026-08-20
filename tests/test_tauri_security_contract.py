from __future__ import annotations

import json
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
    assert "generate_handler![backend_info, retry_backend]" in source
    assert "if let Ok(process) = BackendProcess::launch(&runtime)" in source
    assert "failed Core start must leave the packaged UI running" in source
