"""Optional Node launch shape; path authority remains a Core runtime check."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "packages/contracts/bootstrap/v2/launch.schema.json").read_text(encoding="utf-8"))


def launch():
    return {"protocol": "archeaxis.desktop-launch/v2", "actor": "human", "launch_token": "a" * 64,
            "machine_token": "b" * 64, "session_id": "c" * 32}


def test_existing_launch_and_optional_node_profile_are_both_valid():
    validator = Draft202012Validator(SCHEMA)
    validator.validate(launch())
    assert validator.is_valid({**launch(), "openmaic_node_worker": None})
    assert validator.is_valid({**launch(), "openmaic_node_worker": {
        "executable": "C:\\runtime\\node.exe", "executable_sha256": "d" * 64, "script": "D:\\product\\scene-build-worker.mjs"}})


@pytest.mark.parametrize("profile", [
    {}, {"executable": "", "executable_sha256": "a" * 64, "script": "x"},
    {"executable": "x", "executable_sha256": "bad", "script": "y"},
    {"executable": "x", "executable_sha256": "a" * 64, "script": 4},
    {"executable": "x", "executable_sha256": "a" * 64, "script": "y", "command": "unexpected"}, "node",
])
def test_malformed_node_profiles_are_not_launch_contracts(profile):
    assert not Draft202012Validator(SCHEMA).is_valid({**launch(), "openmaic_node_worker": profile})
