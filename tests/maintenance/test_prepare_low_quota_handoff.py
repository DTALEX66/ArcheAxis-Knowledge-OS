from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("low_quota", ROOT / "scripts/maintenance/prepare_low_quota_handoff.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_threshold_is_closed_and_explicit():
    assert module.classify_quota(11) == "MONITORING"
    assert module.classify_quota(2) == "UPLOAD_REQUIRED"
    assert module.classify_quota(0) == "UPLOAD_REQUIRED"


@pytest.mark.parametrize("value", [-1, 101])
def test_invalid_quota_rejected(value):
    with pytest.raises(ValueError):
        module.classify_quota(value)


def test_handoff_paths_exclude_private_state():
    assert all(not path.startswith((".codex", ".zcode", ".hermes")) for path in module.HANDOFF_PATHS)
