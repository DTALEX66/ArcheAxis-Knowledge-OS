"""Synthetic DeepTutor staging; no installed Core, model, or real user data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from scripts.release import backend_launcher as launcher
from scripts.release import stage_backend_runtime as stager
from scripts.runtime import runtime_resources
from tests.test_backend_in_place import prepared, run_stager  # noqa: F401 - shared fixture
from tests.test_deeptutor_practice_host_worker import (  # noqa: F401 - shared fixture
    child_env,
    request_for,
    result_of,
    run_worker,
    source_and_row,
    wire_for,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "services/learning-providers/deeptutor"
CAPABILITY = "deeptutor.practice.import"
SCRIPT = "workers/deeptutor/practice_host_worker.py"
_SUBPROCESS_RUN = subprocess.run


def add_synthetic_provider(case):
    """Put exact public provider bytes in the synthetic repository fixture."""
    repository = case["repo"]
    donor = repository / "services/learning-providers/deeptutor"
    for relative, expected in stager.PRACTICE_FILES.items():
        raw = (SOURCE / relative).read_bytes()
        assert {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} == expected
        target = donor / relative
        stager.filesystem_path(target.parent).mkdir(parents=True, exist_ok=True)
        stager.filesystem_path(target).write_bytes(raw)
    workers = repository / "services/python-workers"
    archive = workers / "document/worker_archive.py"
    stager.filesystem_path(archive.parent).mkdir(parents=True, exist_ok=True)
    stager.filesystem_path(archive).write_bytes(b"# synthetic non-private worker\n")
    routes = workers / "routes.json"
    document = {"schema": "archeaxis.worker-routes/v1",
                "routes": {"archive.inventory": ["document/worker_archive.py"]}}
    stager.filesystem_path(routes).write_text(json.dumps(document) + "\n", encoding="utf-8")
    return donor, routes


def test_selected_provider_is_in_growth_plan_and_both_staged_route_views(prepared, monkeypatch, child_env):
    case = prepared
    donor, routes = add_synthetic_provider(case)
    original_routes = stager.filesystem_path(routes).read_bytes()
    calls = []
    stage = stager.stage_practice_provider

    def check_plan(root, plan):
        active = stager.growth._batch.get()
        assert active is not None
        assert plan["repository"] == case["repo"]
        assert plan["files"] == stager.PRACTICE_FILES
        for relative, identity in stager.PRACTICE_FILES.items():
            assert active["inputs"][stager.growth.plain(donor / relative)] == identity
        assert active["inputs"][stager.growth.plain(routes)] == plan["routes_original"]
        assert active["total"] >= sum(row["bytes"] for row in active["inputs"].values()) + len(plan["routes_payload"])
        calls.append(True)
        return stage(root, plan)

    monkeypatch.setattr(stager, "stage_practice_provider", check_plan)
    assert run_stager(case) == 0
    assert calls == [True]
    root = case["output"]
    manifest = json.loads(stager.filesystem_path(root / "backend-runtime-manifest.json").read_bytes())
    profile = json.loads(stager.filesystem_path(root / "worker-profile.json").read_bytes())
    native = json.loads(stager.filesystem_path(root / "workers/routes.json").read_bytes())
    assert stager.filesystem_path(routes).read_bytes() == original_routes
    assert native["routes"][CAPABILITY] == ["deeptutor/practice_host_worker.py"]
    assert native["routes"]["deeptutor.question.turn"] == ["deeptutor/question_turn_worker.py"]
    assert native["routes"]["deeptutor.teaching.feedback"] == ["deeptutor/teaching_feedback_worker.py"]
    assert {row["capability"]: row["script"] for row in profile["routes"]}[CAPABILITY] == SCRIPT
    assert {row["capability"]: row["script"] for row in profile["routes"]}[
        "deeptutor.question.turn"] == "workers/deeptutor/question_turn_worker.py"
    assert {row["capability"]: row["script"] for row in profile["routes"]}[
        "deeptutor.teaching.feedback"] == "workers/deeptutor/teaching_feedback_worker.py"
    assert manifest["deeptutor_practice_import"]["status"] == "INCLUDED"
    for relative, identity in stager.PRACTICE_FILES.items():
        target = root / "workers/deeptutor" / relative
        assert stager.filesystem_path(target).read_bytes() == stager.filesystem_path(donor / relative).read_bytes()
        assert manifest["files"][f"workers/deeptutor/{relative}"] == identity
    runtime_resources.verify_worker_contract(root, manifest["files"])
    assert any(row["capability"] == CAPABILITY for row in launcher.load_profile(root)["routes"])

    # Exercise the copied worker with a synthetic input using the test Python;
    # the synthetic runtime python.exe and Core are never executed.
    raw, row = source_and_row("csv")
    wire = wire_for(request_for(raw, "csv", row))
    # The staging fixture blocks subprocess.run to prevent execution of its
    # synthetic runtime. Restore it only for this explicit copied-worker check.
    with monkeypatch.context() as private_child:
        private_child.setattr(subprocess, "run", _SUBPROCESS_RUN)
        child = run_worker(wire, child_env, script=root / SCRIPT)
    assert child.returncode == 0
    result = result_of(child)
    assert result["status"] == "PRIVATE_CANDIDATE"
    assert result["core_write"] == "NOT_EXECUTED"


@pytest.mark.parametrize("mutation", ["missing", "changed", "missing_routes"])
def test_unqualified_provider_is_not_declared_and_ordinary_launch_stays_available(prepared, mutation):
    case = prepared
    donor, routes = add_synthetic_provider(case)
    if mutation == "missing":
        stager.filesystem_path(donor / "LICENSE").unlink()
    elif mutation == "changed":
        stager.filesystem_path(donor / "practice_import.py").write_bytes(b"synthetic wrong source")
    else:
        stager.filesystem_path(routes).unlink()
    assert run_stager(case) == 0
    root = case["output"]
    profile = json.loads(stager.filesystem_path(root / "worker-profile.json").read_bytes())
    manifest = json.loads(stager.filesystem_path(root / "backend-runtime-manifest.json").read_bytes())
    assert manifest["deeptutor_practice_import"]["status"] == "NOT_INCLUDED"
    assert all(row["capability"] != CAPABILITY for row in profile.get("routes", []))
    assert not stager.filesystem_path(root / "workers/deeptutor").exists()
    assert all(row["capability"] != CAPABILITY for row in launcher.load_profile(root)["routes"])


@pytest.mark.parametrize("mutation", ["provider", "routes"])
def test_selected_provider_or_routes_changed_after_planning_fails(prepared, mutation):
    case = prepared
    donor, routes = add_synthetic_provider(case)
    source = donor / "practice_import.py" if mutation == "provider" else routes

    def changed_during_preparation(root):
        original = stager.filesystem_path(source).read_bytes()
        changed = bytes([original[0] ^ 1]) + original[1:]
        assert len(changed) == len(original)
        stager.filesystem_path(source).write_bytes(changed)
        return case["prepare"](repository=case["repo"], destination=root, _backend_in_place=True,
                               _environment=case["env"])

    with pytest.raises((ValueError, OSError)):
        run_stager(case, callback=changed_during_preparation)
    assert not stager.filesystem_path(case["output"] / "backend-runtime-manifest.json").exists()
    assert not stager.filesystem_path(case["output"] / "worker-profile.json").exists()


def test_existing_private_source_route_is_rejected_before_staging(prepared):
    case = prepared
    _, routes = add_synthetic_provider(case)
    document = json.loads(stager.filesystem_path(routes).read_bytes())
    document["routes"][CAPABILITY] = ["elsewhere.py"]
    stager.filesystem_path(routes).write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="already present"):
        run_stager(case)
    assert not stager.filesystem_path(case["output"]).exists()


def test_launcher_skips_only_missing_optional_private_worker(tmp_path):
    for relative in ("runtime/python.exe", "workers/transport/text_ndjson.py", "workers/document/worker_archive.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic file")
    profile = {"schema": "archeaxis.worker-profile/v1", "python": "runtime/python.exe",
               "script": "workers/transport/text_ndjson.py", "staging": "data/worker-staging",
               "routes": [{"capability": CAPABILITY, "script": SCRIPT},
                          {"capability": "archive.inventory", "script": "workers/document/worker_archive.py"}]}
    (tmp_path / "worker-profile.json").write_text(json.dumps(profile), encoding="utf-8")
    assert [row["capability"] for row in launcher.load_profile(tmp_path)["routes"]] == ["archive.inventory"]
    (tmp_path / "workers/document/worker_archive.py").unlink()
    with pytest.raises(launcher.LaunchFailure, match="archive.inventory"):
        launcher.load_profile(tmp_path)
