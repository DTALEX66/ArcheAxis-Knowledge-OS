"""Small runtime producer boundaries; no engine, uv or actual runtime execution."""
import builtins
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.release import runtime_growth as growth


def storage_fixture(repository, run, monkeypatch):
    portable = growth.portable
    paths = portable.dev.layout(repository, run.name)
    monkeypatch.setattr(portable, "REPO", repository)
    report = {"schema": "aaos.storage-footprint/v2", "repository": str(repository),
              "measured_at": "2026-11-01T00:00:00+00:00", "readable_bytes": 3 * 1024 ** 3,
              "measurement_status": "PARTIAL", "measurement_errors": [], "excluded_private": ["preserved"],
              "excluded_checkouts": [], "out_of_layout": [],
              "dev_root": [{"name": "runs/", "bytes": 3 * 1024 ** 3, "budget_gb": 2.0, "over_budget": True}]}
    baseline = paths["artifacts"] / "checkpoint.json"
    raw = json.dumps(report).encode()
    baseline.write_bytes(raw)
    descriptor = {"schema": portable.CHECKPOINT_SCHEMA, "path": baseline.relative_to(repository).as_posix(),
                  "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "report_schema": report["schema"],
                  "recorded_by": "synthetic authorized checkpoint", "measurement_scope": "partial synthetic coverage"}
    pointer = repository / "docs/current/AAOS-ACTIVE-EXECUTION.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps({"execution_control": {"owner_priority_20261030": {
        "operator_storage_checkpoint": descriptor}}}), encoding="utf-8")
    calls = []
    def measure(root):
        calls.append(root)
        return copy.deepcopy(report)
    monkeypatch.setattr(portable.storage_report, "measure", measure)
    context = {"paths": paths, "purpose": "finite fixture", "sharing": "reuse source",
               "retention_reason": "original boundary evidence"}
    return context, report, calls


@pytest.mark.parametrize("change", ["grow", "short", "hash", "new", "missing"])
def test_pinned_runtime_tree_rejects_changes(tmp_path, monkeypatch, change):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    member = source / "member"
    member.write_bytes(b"planned")
    plan = growth.snapshot(source)
    if change == "new":
        (source / "extra").write_bytes(b"extra")
    elif change == "missing":
        member.unlink()
    else:
        original = builtins.open
        def mutate(path, mode="r", *args, **kwargs):
            if growth.plain(path) == member and mode == "rb":
                member.write_bytes({"grow": b"g" * 71, "short": b"s", "hash": b"changed"}[change])
            return original(path, mode, *args, **kwargs)
        monkeypatch.setattr(builtins, "open", mutate)
    with pytest.raises(ValueError):
        growth.copytree(source, target, inputs=plan)
    copied = target / "member"
    if copied.exists():
        assert copied.stat().st_size <= 7


def test_unknown_generation_cannot_use_zero_projection(tmp_path):
    with pytest.raises(ValueError, match="positive"), growth.batch(tmp_path / "output", {}, 0, unknown_output=True):
        pytest.fail("generation started")


def test_live_workflow_runtime_consumers_require_reviewed_forecasts():
    import yaml
    root = Path(__file__).resolve().parents[1]
    found = 0
    for name in ("ci.yml", "release.yml"):
        workflow = yaml.safe_load((root / ".github/workflows" / name).read_text(encoding="utf-8"))
        assert workflow["env"]["ARCHEAXIS_RUNTIME_GENERATED_BYTES"] == "${{ vars.ARCHEAXIS_RUNTIME_GENERATED_BYTES }}"
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run", "")
                if "-m desktop.scripts.prepare_bundle --" not in script:
                    continue
                found += 1
                assert "[long]::TryParse($env:ARCHEAXIS_RUNTIME_GENERATED_BYTES" in script
                assert "$runtimeForecast -le 0) { throw" in script
                assert '--run-id "$runtimeRunId"' in script
                assert '--storage-generated-bytes "$runtimeForecast"' in script
                for option in ("purpose", "sharing", "retention-reason"):
                    assert "--storage-" + option in script
    assert found == 4
