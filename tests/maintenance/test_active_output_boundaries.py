from __future__ import annotations

import json
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
        if path.relative_to(ROOT).as_posix() == "frontend/src/api/generated/resource-catalog.ts":
            payload = json.loads(text.split("export const RESOURCE_CATALOG: ResourceCatalog = ", 1)[1].removesuffix(";\n"))
            # original_surface and ledger are lossless historical records, verified by contract tests.
            # All current projection fields remain checked for executable path drift.
            for entry in payload["entries"]:
                entry.pop("original_surface")
                entry.pop("ledger")
            text = json.dumps(payload, ensure_ascii=False)
        if "D:/All projects" in text or "D:\\All projects" in text:
            violations.append(f"{path.relative_to(ROOT)}: absolute D: root")
        if ".hermes/task-runtime" in text or ".hermes\\task-runtime" in text:
            violations.append(f"{path.relative_to(ROOT)}: legacy runtime output")
    assert not violations, "active path boundary violations:\n" + "\n".join(violations)
