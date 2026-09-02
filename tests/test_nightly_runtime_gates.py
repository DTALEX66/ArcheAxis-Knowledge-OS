from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NIGHTLY = ROOT / ".github" / "workflows" / "nightly.yml"


def _job(workflow: str, name: str, next_name: str | None = None) -> str:
    start = workflow.index(f"\n  {name}:")
    end = workflow.index(f"\n  {next_name}:", start) if next_name else len(workflow)
    return workflow[start:end]


def test_nightly_browser_smoke_installs_locked_frontend_tooling() -> None:
    browser = _job(NIGHTLY.read_text(encoding="utf-8"), "browser-smoke", "windows-runtime")

    assert "actions/setup-node@1a4442cacd436585916779262731d5b162bc6ec7" in browser
    assert 'node-version: "24"' in browser
    assert "npm ci --prefix frontend --ignore-scripts --no-audit --no-fund" in browser


def test_nightly_windows_runtime_uses_powershell_safe_env_and_http_smoke() -> None:
    windows = _job(NIGHTLY.read_text(encoding="utf-8"), "windows-runtime")

    assert "shell: pwsh" in windows
    assert "Remove-Item -LiteralPath Env:PYTHONPATH -ErrorAction SilentlyContinue" in windows
    assert "uv run --frozen --group ci --group ci-adapters python -m app.runtime_entrypoint migrate" in windows
    assert "uv run --frozen --group ci --group ci-adapters python scripts/runtime_http_smoke.py" in windows
