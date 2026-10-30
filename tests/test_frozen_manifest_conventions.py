"""Frozen registrations preserve exact bytes without exempting a directory."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts import check_repository_conventions as scanner

MANIFEST = "docs/archive/MANIFEST.json"
MEMBER = "docs/archive/evidence.txt"


@pytest.mark.parametrize("path,pinned", scanner._OCT30_PRESERVED_INPUT_HASHES.items())
def test_oct30_originals_require_exact_path_and_bytes(path, pinned):
    content = (Path(__file__).resolve().parents[1] / path).read_bytes()
    assert hashlib.sha256(content).hexdigest() == pinned
    assert scanner.scan_text_bytes(path, content) == []
    assert [issue.code for issue in scanner.scan_text_bytes(path, content + b"x")] == ["preserved-fixture-mismatch"]
    if b"\r" in content or content.startswith(b"\xef\xbb\xbf") or not content.endswith(b"\n"):
        assert scanner.scan_text_bytes("workspace/intake/unregistered-copy.txt", content)


def test_xiaoqi_original_crlf_is_accepted_only_at_exact_path_and_hash():
    path = "docs/history/xiaoqi-source-20261018/STATE-ASSET-INDEX.json"
    content = (Path(__file__).resolve().parents[1] / path).read_bytes()
    assert b"\r\n" in content
    assert hashlib.sha256(content).hexdigest() == scanner._PRESERVED_PACKAGE_MEMBER_HASHES[path]
    assert scanner.scan_text_bytes(path, content) == []
    for altered in (content.replace(b"\r\n", b"\n"), content + b"x"):
        assert [issue.code for issue in scanner.scan_text_bytes(path, altered)] == ["preserved-fixture-mismatch"]
    assert "crlf" in {issue.code for issue in scanner.scan_text_bytes("docs/copy/STATE-ASSET-INDEX.json", content)}


def fixture_snapshot(*, members=None, schema="aaos.evidence-snapshot/v1"):
    content = b"\xef\xbb\xbfarchived raw bytes \r\nlast line"
    if members is None:
        members = [{"path": "evidence.txt", "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest()}]
    raw = json.dumps({"schema": schema, "members": members}).encode()
    registry = {MANIFEST: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                           "schema": schema}}
    return {MANIFEST: raw, MEMBER: content}, registry


def validate(contents, registry, **kwargs):
    return scanner.validate_preserved_manifests(contents, registrations=registry, **kwargs)


def test_preserves_only_validated_member_and_manifest_raw_bytes():
    contents, registry = fixture_snapshot()
    pins, issues = validate(contents, registry)
    assert not issues
    assert set(pins) == {MANIFEST, MEMBER}
    for path, content in contents.items():
        assert scanner.scan_text_bytes(path, content, preserved_pins=pins) == []
    for unregistered in ["docs/archive/unlisted.txt", "docs/copy/evidence.txt"]:
        assert scanner.scan_text_bytes(unregistered, contents[MEMBER], preserved_pins=pins)
    assert scanner.scan_text_bytes(MEMBER, contents[MEMBER] + b"x", preserved_pins=pins)


@pytest.mark.parametrize("mutation", ["member", "manifest", "missing-member", "missing-manifest", "size"])
def test_any_failed_registration_returns_no_recognized_members(mutation):
    contents, registry = fixture_snapshot()
    if mutation == "member":
        contents[MEMBER] += b"x"
    elif mutation == "manifest":
        contents[MANIFEST] += b"\n"
    elif mutation == "missing-member":
        del contents[MEMBER]
    elif mutation == "missing-manifest":
        del contents[MANIFEST]
    else:
        body = json.loads(contents[MANIFEST])
        body["members"][0]["bytes"] += 1
        contents[MANIFEST] = json.dumps(body).encode()
        registry[MANIFEST].update(bytes=len(contents[MANIFEST]),
                                 sha256=hashlib.sha256(contents[MANIFEST]).hexdigest())
    pins, issues = validate(contents, registry)
    assert pins == {}
    assert [issue.code for issue in issues] == ["preserved-manifest-mismatch"]


@pytest.mark.parametrize("path", ["../evidence.txt", "/evidence.txt", "C:/evidence.txt",
                                  "a\\evidence.txt", "a//evidence.txt", "./evidence.txt",
                                  "a/../evidence.txt", "nul\x00.txt"])
def test_manifest_rejects_unsafe_paths_without_reading_files(path):
    contents, registry = fixture_snapshot(members=[{"path": path, "bytes": 0, "sha256": "0" * 64}])
    pins, issues = validate(contents, registry)
    assert not pins and issues
    assert "invalid relative member path" in issues[0].detail


@pytest.mark.parametrize("mutation", ["duplicate-member", "case-collision", "bool-size", "bad-hash", "duplicate-json"])
def test_manifest_rejects_ambiguous_or_invalid_identity(mutation):
    contents, registry = fixture_snapshot()
    body = json.loads(contents[MANIFEST])
    member = body["members"][0]
    if mutation in {"duplicate-member", "case-collision"}:
        duplicate = dict(member)
        if mutation == "case-collision":
            duplicate["path"] = "EVIDENCE.TXT"
        body["members"].append(duplicate)
    elif mutation == "bool-size":
        member["bytes"] = True
    elif mutation == "bad-hash":
        member["sha256"] = "0" * 63 + "\n"
    raw = json.dumps(body).encode()
    if mutation == "duplicate-json":
        raw = raw.replace(b'"schema":', b'"schema": "ignored", "schema":', 1)
    contents[MANIFEST] = raw
    registry[MANIFEST].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    pins, issues = validate(contents, registry)
    assert not pins and issues


def test_hash_only_legacy_manifest_needs_separate_reviewed_size_pins():
    contents, registry = fixture_snapshot()
    digest = hashlib.sha256(contents[MEMBER]).hexdigest()
    contents, registry = fixture_snapshot(members={"evidence.txt": digest}, schema="aaos.archive-members/v1")
    assert validate(contents, registry)[1]
    pins, issues = validate(contents, registry, hash_only_sizes={MANIFEST: {"evidence.txt": len(contents[MEMBER])}})
    assert not issues and MEMBER in pins
    assert validate(contents, registry, hash_only_sizes={MANIFEST: {"evidence.txt": len(contents[MEMBER]) + 1}})[1]


def test_one_failed_manifest_does_not_leave_other_registration_recognized():
    contents, registry = fixture_snapshot()
    registry["docs/missing/MANIFEST.json"] = registry[MANIFEST]
    assert validate(contents, registry)[0] == {}


def test_git_source_identity_is_not_repaired_by_worktree(tmp_path: Path, monkeypatch):
    # Only fixture children lose inherited Git location context; user env is untouched.
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("GIT_"):
            env.pop(key)

    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, env=env,
                              check=True, capture_output=True)

    contents, registry = fixture_snapshot()
    monkeypatch.setattr(scanner, "_PRESERVED_MANIFESTS", registry, raising=False)
    monkeypatch.setattr(scanner, "_PRESERVED_HASH_ONLY_MEMBER_SIZES", {}, raising=False)
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    git("init", "-q")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    (tmp_path / ".gitattributes").write_bytes(b"* -text\n")
    for path, content in contents.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    git("add", ".gitattributes", MANIFEST, MEMBER)
    git("commit", "-qm", "exact fixture")
    assert scanner.scan_git_repository(tmp_path, source="head") == []
    (tmp_path / MEMBER).write_bytes(contents[MEMBER].replace(b"\r\n", b"\n"))
    git("add", MEMBER)
    (tmp_path / MEMBER).write_bytes(contents[MEMBER])
    assert scanner.scan_git_repository(tmp_path, source="worktree") == []
    assert any(issue.code == "preserved-manifest-mismatch"
               for issue in scanner.scan_git_repository(tmp_path, source="index"))
    assert scanner.scan_git_repository(tmp_path, source="head") == []
    git("rm", "--cached", "-f", MEMBER)
    assert any(issue.code == "preserved-manifest-mismatch"
               for issue in scanner.scan_git_repository(tmp_path, source="index"))


@pytest.mark.parametrize("path", [
    path for path in scanner._PRESERVED_PACKAGE_MEMBER_HASHES
    if any(part in path for part in (
        "rules-entry-repair-20261023/", "owner-dialogue-20261022-desktop-launcher/",
        "owner-dialogue-20261023-thread-handoff/", "20261024-resource-source-binding/",
    ))
])
def test_october_delivery_archives_preserve_exact_bytes_and_reject_changes(path):
    content = (Path(__file__).resolve().parents[1] / path).read_bytes()
    assert scanner.scan_text_bytes(path, content) == []
    assert [issue.code for issue in scanner.scan_text_bytes(path, content + b"x")] == [
        "preserved-fixture-mismatch"
    ]
    if b"\r\n" in content:
        normalized = content.replace(b"\r\n", b"\n")
        assert scanner.scan_text_bytes(path, normalized)
        assert "crlf" in {issue.code for issue in scanner.scan_text_bytes("docs/copy/evidence.txt", content)}
