from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_ROOTS = ("app", "apps", "archeaxis", "crates", "packages", "scripts", "services", "desktop", "frontend", "src-tauri")
EXTENSIONS = {".py", ".rs", ".cs", ".js", ".cjs", ".ts", ".tsx", ".ps1", ".sh", ".bat"}


def _active_text_files():
    for root_name in ACTIVE_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.casefold() in EXTENSIONS and "__pycache__" not in path.parts:
                yield path


def test_active_sources_do_not_embed_machine_absolute_roots_or_legacy_runtime_output():
    violations = []
    for path in _active_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "D:/All projects" in text or "D:\\All projects" in text:
            violations.append(f"{path.relative_to(ROOT)}: absolute D: root")
        if ".hermes/task-runtime" in text or ".hermes\\task-runtime" in text:
            violations.append(f"{path.relative_to(ROOT)}: legacy runtime output")
    assert not violations, "active path boundary violations:\n" + "\n".join(violations)
