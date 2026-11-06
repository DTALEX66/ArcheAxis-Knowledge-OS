"""The selected OpenMAIC runtime closure.

A staging manifest cannot be written by hand for hundreds of adapter files, and
an unlisted file would silently change what an installation ships. This module
therefore owns one explicit selection: which worker scripts and which vendor
directories travel beside them. ``RUNTIME-CLOSURE.json`` is generated from that
selection and rechecked byte-for-byte before staging.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA = "archeaxis.openmaic-runtime-closure/v1"
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/learning-providers/openmaic"
MANIFEST = SOURCE / "RUNTIME-CLOSURE.json"

# Every adapter Core can resolve as a fixed sibling of the configured scene
# script, plus the guard file the outline adapter pins by SHA.
WORKERS = (
    "scene-build-worker.mjs",
    "outline-replay-worker.mjs",
    "outline-prompt-guard.mjs",
    "slide-prompt-worker.mjs",
    "slide-reply-worker.mjs",
    "slide-normalize-worker.mjs",
    "quiz-replay-worker.mjs",
    "quiz-actions-replay-worker.mjs",
    "slide-actions-replay-worker.mjs",
    "interactive-prompt-worker.mjs",
    "interactive-normalize-worker.mjs",
    "interactive-outline-worker.mjs",
)

# The exact donor and locked-dependency closures those adapters import. Only
# these directories are copied; other material in the donor checkout is not.
VENDORS = (
    "vendor/generation-0.3.28",
    "vendor/generation-0.3.28-outline",
    "vendor/generation-0.3.28-quiz",
    "vendor/generation-0.3.28-quiz-actions",
    "vendor/dsl-0.12.0-actions",
    "vendor/scene-content-0.3.28-original",
    "vendor/generation-0.3.28-slide-actions",
    "vendor/prompts-1.3.0-interactive-outline",
    "vendor/npm",
)


def row(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def selected_files() -> list[str]:
    files: list[str] = []
    for name in WORKERS:
        if not (SOURCE / name).is_file():
            raise ValueError(f"selected worker is missing: {name}")
        files.append(name)
    for directory in VENDORS:
        root = SOURCE / directory
        if not root.is_dir():
            raise ValueError(f"selected vendor directory is missing: {directory}")
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                files.append(path.relative_to(SOURCE).as_posix())
    return sorted(files)


def rows() -> dict[str, dict[str, object]]:
    return {relative: row(SOURCE / relative) for relative in selected_files()}


def document() -> dict[str, object]:
    return {"schema": SCHEMA, "workers": list(WORKERS), "vendors": list(VENDORS),
            "files": rows()}


def write(path: Path = MANIFEST) -> None:
    payload = document()
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def load(path: Path = MANIFEST) -> dict[str, dict[str, object]]:
    document_value = json.loads(path.read_text(encoding="utf-8"))
    if document_value.get("schema") != SCHEMA or not isinstance(document_value.get("files"), dict):
        raise ValueError("OpenMAIC runtime closure manifest is invalid")
    return document_value["files"]


if __name__ == "__main__":
    write()
    print(f"wrote {MANIFEST} with {len(rows())} files")
