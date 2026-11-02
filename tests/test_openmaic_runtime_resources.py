"""Synthetic declaration checks; no Node executable or Core is run."""
import copy

import pytest

from scripts.runtime import runtime_resources
from scripts.runtime.runtime_resources import parse_backend_manifest, verify_openmaic_contract


PREFIX = "workers/openmaic/"
NODE_SHA = "1" * 64
IDENTITIES = {
    "node.exe": NODE_SHA,
    "scene-build-worker.mjs": "c4a2dad9c96ebd13aa20827410227d2650cda0dac80e3a3927968d1e024779e9",
    "vendor/generation-0.3.28/scene-builder.ts": "e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a",
    "vendor/generation-0.3.28/nanoid.mjs": "d5d678dfcecc9a4c0f4dae6555c30b4d0ef41a87b00d4d16d744f31ddae6c16e",
    "vendor/generation-0.3.28/LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    "vendor/generation-0.3.28/UPSTREAM.md": "83962cee94daba3596fba378867756981c87a8bd7839ced586510643c113d579",
    "NODE-LICENSE": "3" * 64,
}


def rows():
    # Identity rows are synthetic; verify_members performs the real file read.
    return {PREFIX + name: {"bytes": 1, "sha256": sha} for name, sha in IDENTITIES.items()}


def test_absent_is_compatible_and_complete_declaration_is_accepted():
    verify_openmaic_contract({}, {})
    verify_openmaic_contract({"openmaic_scene_build": {"status": "NOT_INCLUDED", "node_sha256": None}}, {})
    verify_openmaic_contract({"openmaic_scene_build": {"status": "INCLUDED", "node_sha256": NODE_SHA}}, rows())


@pytest.mark.parametrize("mutation", ["missing", "worker", "node", "license", "upstream", "node_oversized", "license_oversized", "invalid_status", "absent_hash", "extra", "null"])
def test_incomplete_or_inconsistent_closure_is_rejected(mutation):
    backend = {"openmaic_scene_build": {"status": "INCLUDED", "node_sha256": NODE_SHA}}
    members = copy.deepcopy(rows())
    if mutation == "missing":
        del members[PREFIX + "vendor/generation-0.3.28/scene-builder.ts"]
    elif mutation == "worker":
        members[PREFIX + "scene-build-worker.mjs"]["sha256"] = "0" * 64
    elif mutation == "node":
        members[PREFIX + "node.exe"]["sha256"] = "0" * 64
    elif mutation == "license":
        members[PREFIX + "NODE-LICENSE"]["bytes"] = 0
    elif mutation == "upstream":
        members[PREFIX + "vendor/generation-0.3.28/UPSTREAM.md"]["sha256"] = "0" * 64
    elif mutation == "node_oversized":
        members[PREFIX + "node.exe"]["bytes"] = 512 * 1024 * 1024 + 1
    elif mutation == "license_oversized":
        members[PREFIX + "NODE-LICENSE"]["bytes"] = 1_000_001
    elif mutation == "invalid_status":
        backend["openmaic_scene_build"]["status"] = "OTHER"
    elif mutation == "absent_hash":
        backend["openmaic_scene_build"] = {"status": "NOT_INCLUDED", "node_sha256": NODE_SHA}
    elif mutation == "extra":
        backend["openmaic_scene_build"]["script"] = "elsewhere"
    else:
        backend["openmaic_scene_build"] = None
    with pytest.raises(ValueError, match="OpenMAIC|Node"):
        verify_openmaic_contract(backend, members)


@pytest.mark.parametrize("raw", [
    '{"schema":"one","schema":"two"}',
    '{"openmaic_scene_build":{"status":"INCLUDED","status":"INCLUDED"}}',
    '{"files":{"item":{"sha256":"a","sha256":"b"}}}',
])
def test_duplicate_manifest_fields_are_rejected(raw):
    with pytest.raises(ValueError, match="Duplicate backend manifest"):
        parse_backend_manifest(raw)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_manifest_numbers_are_rejected(constant):
    with pytest.raises(ValueError, match="Non-finite"):
        parse_backend_manifest('{"other":' + constant + "}")


def test_optional_runtime_manifest_must_fit_the_host_limit(monkeypatch):
    monkeypatch.setattr(runtime_resources, "MAX_OPENMAIC_MANIFEST_BYTES", 128)
    included = b'{"openmaic_scene_build":{"status":"INCLUDED","node_sha256":"' + b"1" * 64 + b'"}}'
    assert len(included) < 128
    assert parse_backend_manifest(included)["openmaic_scene_build"]["status"] == "INCLUDED"
    with pytest.raises(ValueError, match="host limit"):
        parse_backend_manifest(included + b" " * 129)
    assert parse_backend_manifest(b'{"schema":"legacy"}' + b" " * 129)["schema"] == "legacy"
