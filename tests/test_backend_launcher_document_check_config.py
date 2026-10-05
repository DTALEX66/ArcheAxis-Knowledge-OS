"""Synthetic fresh-owner nonsecret configuration fixtures, no network calls."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location(
        "owner_config_launcher", ROOT / "scripts/release/backend_launcher.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_invalid_and_valid_config_do_not_choose_defaults(tmp_path):
    launcher = load()
    assert launcher.document_check_config(tmp_path) == (None, None)
    folder = tmp_path / "config"
    folder.mkdir()
    path = folder / "document-check.json"
    valid = {
        "provider": "fixture",
        "model": "fixture/exact-v1",
        "max_tokens": 128,
        "timeout_seconds": 10,
        "search_limit": 1,
    }
    path.write_text(json.dumps(valid), encoding="utf-8")
    assert launcher.document_check_config(tmp_path) == (valid, None)
    duplicate = json.dumps(valid).replace('"provider": "fixture"', '"provider": "fixture", "provider": "fixture"')
    path.write_text(duplicate, encoding="utf-8")
    assert launcher.document_check_config(tmp_path) == (None, "invalid_config")
    for invalid in (
        {},
        dict(valid, provider="fixture-"),
        dict(valid, endpoint="https://fixture.invalid/ bad"),
        dict(valid, endpoint="https://fixture.invalid/" + "a" * 2048),
        dict(valid, api_key="synthetic-forbidden"),
        dict(valid, model="default"),
        dict(valid, max_tokens=True),
        dict(valid, endpoint="https://user:secret@fixture.invalid/v1"),
        dict(valid, endpoint="https://fixture.invalid/v1?token=synthetic"),
    ):
        path.write_text(json.dumps(invalid), encoding="utf-8")
        assert launcher.document_check_config(tmp_path) == (None, "invalid_config")
    path.write_bytes(b" " * (16 * 1024 + 1))
    assert launcher.document_check_config(tmp_path) == (None, "invalid_config")


def test_owned_windows_parent_junction_is_rejected(tmp_path):
    import os
    import subprocess

    import pytest

    if os.name != "nt":
        pytest.skip("Windows reparse-point fixture")
    data = tmp_path / "data"
    donor = tmp_path / "donor"
    data.mkdir()
    donor.mkdir()
    junction = data / "config"
    result = subprocess.run(
        ["cmd", "/C", "mklink", "/J", str(junction), str(donor)],
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    assert result.returncode == 0
    try:
        assert load().document_check_config(data) == (None, "invalid_config")
    finally:
        junction.rmdir()
