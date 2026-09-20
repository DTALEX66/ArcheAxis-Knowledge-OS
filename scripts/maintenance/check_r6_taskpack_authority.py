"""Verify R6 TaskPack source provenance and canonical repository bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "docs" / "authority" / "taskpack-0919-r6"
SOURCE_SHA = "dcc51e922a35d30ca361e9014e040674b62cee644a3ea57aae12ffa6c2949529"
REPOSITORY_SHA = "788c5d50b5953d21eb9f67587d5406d37ad2e5457c2ca3b991399d9988e5951b"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check() -> list[str]:
    errors: list[str] = []
    manifest = json.loads((PACK / "MANIFEST.json").read_text(encoding="utf-8"))
    tasks = json.loads((PACK / "TASKS.json").read_text(encoding="utf-8"))
    state = json.loads((ROOT / "docs" / "current" / "R6-STATE.json").read_text(encoding="utf-8"))
    records = (manifest, tasks, state)
    for record in records:
        if record.get("taskpack_sha256") != SOURCE_SHA:
            errors.append("source TaskPack SHA does not match the recorded provenance digest")
        if record.get("taskpack_sha256_scope") != "user-provided source bytes with CRLF line endings":
            errors.append("source TaskPack SHA scope is missing or ambiguous")
        if record.get("repository_taskpack_sha256") != REPOSITORY_SHA:
            errors.append("repository TaskPack SHA is missing or stale")
        if record.get("repository_taskpack_line_endings") != "LF":
            errors.append("repository TaskPack line-ending policy is not LF")

    taskpack_bytes = (PACK / "TASKPACK.md").read_bytes()
    if _sha256(taskpack_bytes) != REPOSITORY_SHA:
        errors.append("TASKPACK.md bytes do not match the recorded repository SHA")
    normalized = taskpack_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    source_bytes = normalized.replace(b"\n", b"\r\n")
    if _sha256(source_bytes) != SOURCE_SHA:
        errors.append("normalized TASKPACK.md does not reproduce the source provenance SHA")

    start = (PACK / "EXECUTOR-START.md").read_text(encoding="utf-8")
    if "$sha" in start:
        errors.append("EXECUTOR-START.md contains an unresolved SHA placeholder")
    if SOURCE_SHA not in start or REPOSITORY_SHA not in start:
        errors.append("EXECUTOR-START.md does not expose both TaskPack digests")
    return errors


def main() -> int:
    errors = check()
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS")
    print(f"- source_sha={SOURCE_SHA}")
    print(f"- repository_sha={REPOSITORY_SHA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
