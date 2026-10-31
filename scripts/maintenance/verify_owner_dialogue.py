"""Verify the frozen dialogue using byte-checked public migration identities.

The original verifier and snapshot remain immutable. Only exact retired locators
in the consolidation manifest may resolve to preserved bytes; no path revival.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = "docs/history/owner-dialogue-20261019"
CONSOLIDATION = "docs/history/repository-consolidation-20261019/MANIFEST.json"


def module_at(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUTES = module_at("dialogue_public_routes", Path(__file__).with_name("authority_routes.py"))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def identity(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def resolve_reference(root: Path, reference: str, files: list[dict]) -> Path:
    original = ROUTES.public_path(root, reference)
    matches = [item for item in files if item["original_path"] == reference]
    if len(matches) > 1:
        raise ValueError("ambiguous migration identity: " + reference)
    if not matches:
        if not original.is_file():
            raise ValueError("unregistered missing reference: " + reference)
        return original
    entry = matches[0]
    if original.exists():
        raise ValueError("retired original revived: " + reference)
    archived = entry["archive_path"]
    if not archived.startswith(str(Path(CONSOLIDATION).parent).replace("\\", "/") + "/"):
        raise ValueError("migration outside consolidation archive: " + reference)
    target = ROUTES.public_path(root, archived)
    if (type(entry["bytes"]) is not int or entry["bytes"] < 0
            or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
        raise ValueError("invalid migration identity: " + reference)
    if not target.is_file() or identity(target) != (entry["bytes"], entry["sha256"]):
        raise ValueError("migration bytes mismatch: " + reference)
    return target


def verify(require_local_attachments: bool = False, root: Path = ROOT) -> dict:
    archive = ROUTES.public_path(root, ARCHIVE)
    manifest = load(ROUTES.public_path(root, ARCHIVE + "/MANIFEST.json"))
    # Check all executable/input members before importing the frozen implementation.
    for entry in manifest["members"]:
        target = ROUTES.public_path(root, ARCHIVE + "/" + entry["path"])
        if identity(target) != (entry["bytes"], entry["sha256"]):
            raise ValueError("frozen member identity mismatch: " + entry["path"])
    members = [entry["path"] for entry in manifest["members"]]
    if len(members) != len(set(members)) or "verify_archive.py" not in members:
        raise ValueError("invalid frozen verifier membership")
    consolidation = load(ROUTES.public_path(root, CONSOLIDATION))
    if consolidation["schema"] != "archeaxis.repository-consolidation/v1":
        raise ValueError("invalid consolidation manifest")
    files = consolidation["files"]
    original_names = [entry["original_path"] for entry in files]
    if len(original_names) != len(set(original_names)):
        raise ValueError("ambiguous migration identities")
    frozen = module_at("frozen_owner_dialogue", archive / "verify_archive.py")
    frozen.REPO, frozen.ARCHIVE = root, archive
    original_confined = frozen.confined
    # The local-only option permits precisely the three hash-bound frozen payloads.
    attachments = {entry["archive"] for entry in load(archive / "attachments.json")["files"]}
    migrated: dict[str, str] = {}

    def confined(base: Path, reference: str) -> Path:
        if base != root:
            return original_confined(base, reference)
        if require_local_attachments and reference in attachments:
            return original_confined(base, reference)
        target = resolve_reference(root, reference, files)
        if target != root.joinpath(*Path(reference).parts):
            migrated[reference] = target.relative_to(root).as_posix()
        return target

    frozen.confined = confined
    result = frozen.verify(require_local_attachments)
    result["maintained_verifier"] = "scripts/maintenance/verify_owner_dialogue.py"
    result["migration_identities_checked"] = migrated
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-local-attachments", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.require_local_attachments), ensure_ascii=False, indent=2))
