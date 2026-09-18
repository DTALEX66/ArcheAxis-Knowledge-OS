from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NIGHTLY = ROOT / ".github" / "workflows" / "nightly.yml"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _job(workflow: str, name: str, next_name: str | None = None) -> str:
    start = workflow.index(f"\n  {name}:")
    end = workflow.index(f"\n  {next_name}:", start) if next_name else len(workflow)
    return workflow[start:end]


def _os_packages(workflow: str) -> set[str]:
    match = re.search(r"apt-get install --yes --no-install-recommends ([^\n]+)", workflow)
    assert match, "the local OCR engine install line must exist"
    return set(match.group(1).split())


def test_nightly_full_suite_checks_out_the_history_it_re_derives() -> None:
    """The whole-suite job resolves commits that tracked records name.

    `tests/test_path_conventions.py` and `tests/test_axr060_completion_audit.py`
    run `git cat-file`/`git ls-tree` against the historical commits a record
    declares. A depth-1 checkout makes those objects absent, which turns a dated
    record into a failure that says nothing about the code.
    """
    full_suite = _job(NIGHTLY.read_text(encoding="utf-8"), "full-suite", "browser-smoke")

    assert "fetch-depth: 0" in full_suite, (
        "full-suite re-derives recorded history; it needs a complete checkout"
    )


def test_nightly_full_suite_os_packages_mirror_ci() -> None:
    """Nightly runs the same integration tests, so its OS deps must match CI.

    ci.yml installs fonts-noto-cjk specifically for the CJK browser-OCR
    crosscheck; nightly's copy of the same apt line was taken before that and
    went stale, so the OCR crosscheck failed there while the screenshot passed.
    """
    nightly = _os_packages(NIGHTLY.read_text(encoding="utf-8"))
    ci = _os_packages(CI.read_text(encoding="utf-8"))

    assert nightly == ci, (
        "nightly full-suite's OS package set drifted from ci.yml: "
        f"nightly-only={sorted(nightly - ci)} ci-only={sorted(ci - nightly)}"
    )


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
