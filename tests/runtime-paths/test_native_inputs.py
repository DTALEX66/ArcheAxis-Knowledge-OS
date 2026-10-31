"""Finite native replay preparation counterexamples. Never launches a VM."""
import copy
import hashlib
import json
import os
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from scripts.runtime import native_inputs as subject
from scripts.runtime import shared_sandbox as shared


def row(data=b"x"):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


@pytest.fixture
def trees(tmp_path):
    roots = {name: tmp_path / name for name in subject.COUNTS}
    body = {name: {"member.txt": row()} for name in subject.COUNTS}
    for root in roots.values():
        root.mkdir()
        (root / "member.txt").write_bytes(b"x")
    return roots, body


@pytest.mark.parametrize("name", [
    "../outside", "/absolute", r"a\b", "a//b", "a/./b", "a/../b",
    ".git/config", ".agents/state", ".hilo/content", ".codex/session",
    ".env", ".env.local", "node_modules/file", ".project-local/state",
    "file:stream", "CON", "tail.", "bad\nname",
])
def test_all_names_are_validated_before_any_payload(trees, monkeypatch, name):
    roots, body = trees
    body["tools"][name] = row()
    monkeypatch.setattr(subject.inputs, "identity", lambda _: pytest.fail("Payload hash before declaration complete"))
    with pytest.raises(ValueError):
        subject.inspect_trees(roots, body)


@pytest.mark.parametrize("change", ["boolsize", "negative", "uppercase", "extra", "missinggroup", "casealias"])
def test_schema_aliases_and_identity_rows_rejected(trees, change):
    _, body = trees
    if change == "boolsize":
        body["input"]["member.txt"]["bytes"] = True
    elif change == "negative":
        body["input"]["member.txt"]["bytes"] = -1
    elif change == "uppercase":
        body["input"]["member.txt"]["sha256"] = "A" * 64
    elif change == "extra":
        body["input"]["member.txt"]["extra"] = 1
    elif change == "missinggroup":
        del body["tools"]
    else:
        body["input"]["MEMBER.TXT"] = row()
    with pytest.raises(ValueError):
        subject.declaration(body)


def test_every_inventory_precedes_all_payload_hashes(trees, monkeypatch):
    roots, body = trees
    (roots["tools"] / "unexpected.txt").write_bytes(b"new")
    monkeypatch.setattr(subject.inputs, "identity", lambda _: pytest.fail("Unexpected inventory must precede hashes"))
    with pytest.raises(ValueError, match="inventory"):
        subject.inspect_trees(roots, body)


def test_unknown_private_directory_is_not_traversed(trees, monkeypatch):
    roots, body = trees
    (roots["input"] / ".hilo").mkdir()
    monkeypatch.setattr(subject.inputs, "identity", lambda _: pytest.fail("Private boundary before hashes"))
    with pytest.raises(ValueError, match="Private"):
        subject.inspect_trees(roots, body)


def test_hardlink_is_rejected(trees):
    roots, body = trees
    os.link(roots["input"] / "member.txt", roots["input"] / "alias.txt")
    with pytest.raises(ValueError, match="independent"):
        subject.inspect_trees(roots, body)


def test_full_tree_proof_is_bound_to_names_bytes_and_content(trees):
    roots, body = trees
    proof = subject.inspect_trees(roots, body)
    assert sum(group["members"] for group in proof.values()) == 3
    (roots["tools"] / "member.txt").write_bytes(b"y")
    with pytest.raises(ValueError, match="bytes/hash"):
        subject.inspect_trees(roots, body)
    changed = copy.deepcopy(body["input"])
    changed["renamed"] = changed.pop("member.txt")
    assert subject.tree_identity(changed) != subject.tree_identity(body["input"])
    assert subject.tree_identity(dict(reversed(list(changed.items())))) == subject.tree_identity(changed)


def test_wrong_stage_or_unreviewed_pin_fails_before_manifest_reads(tmp_path, monkeypatch):
    dev = tmp_path / ".project-local"
    stage = dev / "runs/key/cnprep3"
    monkeypatch.setattr(subject.inputs, "identity", lambda _: pytest.fail("Unreviewed stage cannot read manifests"))
    with pytest.raises(ValueError, match="exact reviewed"):
        subject.reviewed(stage, dev, subject.APPROVED_MANIFEST)
    key = hashlib.sha256(str(tmp_path).casefold().encode()).hexdigest()[:10]
    with pytest.raises(ValueError, match="exact reviewed"):
        subject.reviewed(dev / "runs" / key / "cnprep3", dev, "0" * 64)


@pytest.fixture
def guest(tmp_path):
    nonce, owned = uuid.uuid4().hex, str(uuid.uuid4())
    groups = {group: {"root": subject.GUEST[group], **subject.tree_identity({"f": row()})}
              for group in subject.COUNTS}
    probes = [subject.GUEST[name] + r"\f" for name in subject.COUNTS]
    binding = {"groups": groups, "probes": probes}
    plan = {"output": str(tmp_path), "nonce": nonce, "sandbox_id": owned,
            "source_manifest_sha256": subject.APPROVED_MANIFEST, "members": 3, "binding": binding}
    result = {"schema": "aaos.shared-native-inputs-guest-probe/v1",
              "status": "PASS_NATIVE_COMPLETE_TREES_READONLY_AND_FRESH_OUTPUT",
              "context": "SYSTEM_MAPPING_PROBE_ONLY", "nonce": nonce, "sandbox_id": owned,
              "manifest_sha256": subject.APPROVED_MANIFEST, "manifest_provenance": "HOST_PINNED_NOT_GUEST_READ",
              "groups": copy.deepcopy(groups), "members_verified": 3, "error": None,
              "readonly": [{"path": path, "write_open_access_denied": True} for path in probes]}
    (tmp_path / "shared-probe-marker.txt").write_bytes(("aaos-shared-probe:" + nonce).encode())
    return plan, result


@pytest.mark.parametrize("change", ["none", "nonce", "owned", "hash", "count", "bytes", "missinggroup",
                                    "write", "provenance", "error", "marker"])
def test_guest_proof_must_bind_complete_inputs_owned_id_and_fresh_output(guest, change):
    plan, result = guest
    if change == "nonce":
        result["nonce"] = uuid.uuid4().hex
    elif change == "owned":
        result["sandbox_id"] = str(uuid.uuid4())
    elif change == "hash":
        result["groups"]["input"]["sha256"] = "0" * 64
    elif change == "count":
        result["groups"]["input"]["members"] = 2
    elif change == "bytes":
        result["groups"]["input"]["bytes"] = 2
    elif change == "missinggroup":
        del result["groups"]["input"]
    elif change == "write":
        result["readonly"][0]["write_open_access_denied"] = False
    elif change == "provenance":
        result["manifest_provenance"] = "GUEST_HASHED_MANIFEST"
    elif change == "error":
        result["error"] = {"type": "failure"}
    elif change == "marker":
        (Path(plan["output"]) / "shared-probe-marker.txt").write_bytes(b"old")
    (Path(plan["output"]) / "shared-probe.json").write_text(json.dumps(result), encoding="utf-8")
    if change == "none":
        assert subject.verify_guest(plan) == result
    else:
        with pytest.raises(ValueError):
            subject.verify_guest(plan)


def test_mapping_mode_removes_native_business_command(tmp_path, monkeypatch):
    base = ET.fromstring(shared.inputs.proposal(tmp_path, tmp_path / "fresh", "0" * 64))
    base.find("./LogonCommand/Command").text = "historical installer command MUST NOT execute"
    monkeypatch.setattr(subject, "proposal", lambda *_: ET.tostring(base))
    config = ET.fromstring(shared.config_for(tmp_path, tmp_path / "fresh", "0" * 64, "native-mapping"))
    assert config.find("LogonCommand") is None
    assert len(config.findall("./MappedFolders/MappedFolder")) == 4
    assert config.findtext("Networking") == "Disable"
    command, _ = shared.command_for({"nonce": "fixture"}, "native-mapping")
    assert " -EncodedCommand " in command
