"""The LM Studio migration must hold in source and in a staged worker runtime."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / "services/python-workers"


def test_current_declaration_has_no_retired_automatic_endpoint():
    manifest = yaml.safe_load((ROOT / "config/environment/capability-requirements.yaml").read_text("utf-8"))
    endpoints = [entry["endpoint"] for entries in manifest["capabilities"].values()
                 for entry in entries if "endpoint" in entry]
    assert endpoints
    assert all(entry["protocol"] == "openai" for entry in endpoints)
    assert {entry["base_url"] for entry in endpoints} == {"http://127.0.0.1:1234/v1"}


def test_archived_profiles_keep_original_bytes_and_are_not_live_configuration():
    archive = ROOT / "docs/history/runtime-migration-20261018"
    manifest = json.loads((archive / "MANIFEST.json").read_text("utf-8"))
    for record in manifest["records"]:
        assert not (ROOT / record["original"]).exists()
        data = (ROOT / record["archive"]).read_bytes()
        assert len(data) == record["bytes"]
        assert hashlib.sha256(data).hexdigest() == record["sha256"]


@pytest.fixture(params=["machine/worker_machine_answer.py", "vision/worker_caption.py"])
def worker(request, monkeypatch):
    for prefix in ["MACHINE", "CAPTION"]:
        for suffix in ["ENDPOINT", "MODEL", "PROTOCOL"]:
            monkeypatch.delenv(f"ARCHEAXIS_{prefix}_{suffix}", raising=False)
    monkeypatch.delenv("ARCHEAXIS_CAPABILITY_MANIFEST", raising=False)
    return request.param


def load(path):
    spec = importlib.util.spec_from_file_location("local_runtime_policy_worker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("layout", ["source", "staged_without_manifest"])
@pytest.mark.parametrize("reachable", [True, False])
def test_automatic_route_never_contacts_retired_runtime(worker, layout, reachable, tmp_path, monkeypatch):
    path = WORKERS / worker
    if layout == "staged_without_manifest":
        staged = tmp_path / "workers"
        path = staged / worker
        path.parent.mkdir(parents=True)
        shutil.copyfile(WORKERS / worker, path)
        for sibling in ["tool_paths.py", "local_http.py"]:
            shutil.copyfile(WORKERS / sibling, staged / sibling)
    module = load(path)
    calls = []

    def inventory(url, timeout):
        calls.append(url)
        if not reachable:
            raise OSError("Synthetic LM Studio unavailable")
        return io.BytesIO(b'{"data":[]}')

    monkeypatch.setattr(module, "local_urlopen", inventory)
    endpoint = module._endpoint()
    assert endpoint["protocol"] == "openai"
    assert endpoint["base"] == "http://127.0.0.1:1234/v1"
    assert calls == ["http://127.0.0.1:1234/v1/models"]
    assert module.DEFAULT_MODEL == module.OPENAI_MODEL


def test_old_manifest_order_cannot_reactivate_retired_runtime(worker, tmp_path, monkeypatch):
    manifest = tmp_path / "old-capabilities.json"
    manifest.write_text(json.dumps({"capabilities": {"models": [
        {"name": "retired", "role": "caption", "endpoint": {
            "protocol": "ollama", "base_url": "http://127.0.0.1:11434"}},
        {"name": "lm-studio", "role": "caption", "endpoint": {
            "protocol": "openai", "base_url": "http://127.0.0.1:1234/v1"}},
    ]}}), encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(manifest))
    module = load(WORKERS / worker)
    lanes = module._declared_lanes()
    assert [(lane["protocol"], lane["base"]) for lane in lanes] == [
        ("openai", "http://127.0.0.1:1234/v1")]
