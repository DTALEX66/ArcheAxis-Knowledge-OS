"""Verify a project-local Green candidate without launching it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = (
    "desktop/ArcheAxis.Desktop.exe",
    "desktop/hostfxr.dll",
    "desktop/hostpolicy.dll",
    "desktop/ArcheAxis.Desktop.runtimeconfig.json",
    "core/archeaxis-api.exe",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(candidate: Path) -> dict:
    candidate = candidate.resolve()
    manifest_path = candidate / "candidate-manifest.json"
    problems: list[str] = []
    if not candidate.is_dir():
        return {"ok": False, "problems": ["candidate directory is missing"]}
    if not manifest_path.is_file():
        return {"ok": False, "problems": ["candidate-manifest.json is missing"]}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "problems": [f"manifest unreadable: {exc}"]}
    if manifest.get("schema") != "archeaxis.green-candidate/v1":
        problems.append("unexpected candidate schema")
    files = manifest.get("files", {})
    for relative in REQUIRED:
        path = candidate / relative
        entry = files.get(relative)
        if not path.is_file() or not isinstance(entry, dict):
            problems.append(f"required file missing from candidate: {relative}")
            continue
        if _sha256(path) != entry.get("sha256"):
            problems.append(f"hash mismatch: {relative}")
    runtime_included = any(name.startswith("runtime/") for name in files)
    return {
        "ok": not problems,
        "scope": "desktop-core-runtime" if runtime_included else "desktop-core-only",
        "runtime_included": runtime_included,
        "version": manifest.get("version"),
        "files": len(files),
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    result = verify(args.candidate)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
