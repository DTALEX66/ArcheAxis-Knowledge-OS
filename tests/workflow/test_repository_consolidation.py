"""Synthetic archival guard regressions: no product services or real user data."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.maintenance.authority_routes import (
    CONSOLIDATION, REGISTRY, check_consolidation, public_path, resolve,
)


def write(root, name, body):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def save(root, manifest):
    write(root, CONSOLIDATION, json.dumps(manifest))


def scenario(root):
    old = "old-plans/旧 plan.md"
    archive = str(Path(CONSOLIDATION).parent / old).replace("\\", "/")
    raw = b"historical bytes\r\n"
    path = root / archive
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    write(root, "docs/current/handoff.md", "current\n")
    write(root, "README.md", "[current](docs/current/handoff.md)\n")
    write(root, "docs/guide.md", "current\n")
    routes = {"aliases": [], "entries": [
        {"path": "README.md", "role": "LIVE_NAVIGATION"},
        {"path": "docs/guide.md", "role": "LIVE_NAVIGATION"},
        {"path": archive, "role": "HISTORICAL_RECORD"}], "rules": []}
    write(root, REGISTRY, json.dumps(routes))
    manifest = {"schema": "archeaxis.repository-consolidation/v1",
                "source_commit": "a" * 40, "whole_directories": ["old-plans"],
                "files": [{"original_path": old, "archive_path": archive,
                           "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                           "replacement": "docs/current/handoff.md",
                           "role": "HISTORICAL_RECORD", "baseline_commit": "a" * 40}]}
    save(root, manifest)
    return manifest, routes


def test_exact_archive_passes_and_old_locator_resolves_without_stub(tmp_path):
    manifest, routes = scenario(tmp_path)
    assert check_consolidation(tmp_path) == []
    item = manifest["files"][0]
    result = resolve(item["original_path"], routes, tmp_path)
    assert result == {"path": item["original_path"], "role": "RETIRED_LOCATOR",
                      "canonical_path": item["archive_path"],
                      "replacement": item["replacement"]}
    assert not (tmp_path / item["original_path"]).exists()


@pytest.mark.parametrize("mutation", ["archive", "size", "hash", "replacement", "original", "baseline", "duplicate"])
def test_identity_or_migration_damage_is_detected(tmp_path, mutation):
    manifest, _ = scenario(tmp_path)
    item = manifest["files"][0]
    expected = {
        "archive": "identity mismatch", "size": "identity mismatch",
        "hash": "identity mismatch", "replacement": "missing consolidation replacement",
        "original": "retired original still exists", "baseline": "invalid baseline_commit",
        "duplicate": "duplicate consolidation identity",
    }[mutation]
    if mutation == "archive":
        (tmp_path / item["archive_path"]).write_bytes(b"changed\n")
    elif mutation == "size":
        item["bytes"] += 1
    elif mutation == "hash":
        item["sha256"] = "0" * 64
    elif mutation == "replacement":
        (tmp_path / item["replacement"]).unlink()
    elif mutation == "original":
        write(tmp_path, item["original_path"], "stub\n")
    elif mutation == "baseline":
        item["baseline_commit"] = "unknown"
    elif mutation == "duplicate":
        manifest["files"].append(item.copy())
    save(tmp_path, manifest)
    assert any(expected in issue for issue in check_consolidation(tmp_path))


def test_unlisted_nested_public_residual_is_detected(tmp_path):
    scenario(tmp_path)
    write(tmp_path, "old-plans/subdir/unlisted.md", "residual\n")
    assert any("public residual: old-plans/subdir/unlisted.md" in issue
               for issue in check_consolidation(tmp_path))


def test_private_residual_is_not_read_or_descended(tmp_path, monkeypatch):
    scenario(tmp_path)
    private = tmp_path / "old-plans/.hilo"
    private.mkdir(parents=True)
    original = Path.iterdir

    def guarded(path):
        assert path != private, "private state must not be traversed"
        return original(path)

    monkeypatch.setattr(Path, "iterdir", guarded)
    assert check_consolidation(tmp_path) == []


def test_linked_residual_fails_without_traversal(tmp_path, monkeypatch):
    scenario(tmp_path)
    write(tmp_path, "old-plans/linked-target/never-read.md", "sentinel\n")
    original_iterdir = Path.iterdir
    original_lstat = Path.lstat
    linked = tmp_path / "old-plans/linked-target"

    def guarded_iterdir(path):
        assert path != linked, "linked directory must not be traversed"
        return original_iterdir(path)

    class Reparse:
        st_mode = 0
        st_file_attributes = 0x400

    def reparse_lstat(path):
        return Reparse() if path == linked else original_lstat(path)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    monkeypatch.setattr(Path, "lstat", reparse_lstat)
    assert any("uninspectable retired directory child" in issue
               for issue in check_consolidation(tmp_path))


def test_relative_encoded_live_link_to_retired_file_fails(tmp_path):
    scenario(tmp_path)
    write(tmp_path, "docs/guide.md", "[old](../old-plans/./%E6%97%A7%20plan.md#section)\n")
    assert any("live link targets retired original" in issue for issue in check_consolidation(tmp_path))


def test_frozen_archive_old_literal_and_link_do_not_become_live_checks(tmp_path):
    manifest, _ = scenario(tmp_path)
    item = manifest["files"][0]
    raw = b"old-plans/old.md [old](../../old-plans/old.md)\r\n"
    (tmp_path / item["archive_path"]).write_bytes(raw)
    item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    save(tmp_path, manifest)
    assert check_consolidation(tmp_path) == []


@pytest.mark.parametrize("unsafe", ["../escape.md", ".hilo/storage.json", ".project-local/private.md"])
def test_manifest_cannot_request_private_or_outside_read(tmp_path, unsafe):
    manifest, _ = scenario(tmp_path)
    manifest["files"][0]["archive_path"] = unsafe
    save(tmp_path, manifest)
    assert check_consolidation(tmp_path)


def test_missing_manifest_is_a_failure(tmp_path):
    assert check_consolidation(tmp_path)
