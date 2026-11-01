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


def test_live_workflow_runtime_consumers_initialize_fixed_job_forecasts():
    import yaml
    root = Path(__file__).resolve().parents[1]
    found = 0
    for name in ("ci.yml", "release.yml"):
        workflow = yaml.safe_load((root / ".github/workflows" / name).read_text(encoding="utf-8"))
        assert "ARCHEAXIS_RUNTIME_GENERATED_BYTES" not in workflow.get("env", {})
        for job in workflow["jobs"].values():
            initialization = 0
            synced = False
            runtime_syncs = []
            for step in job.get("steps", []):
                script = step.get("run", "")
                if "uv sync --frozen" in script:
                    synced = True
                    runtime_syncs += [line.strip() for line in script.splitlines() if "uv sync --frozen" in line]
                if "-m scripts.release.ci_runtime_checkpoint" in script:
                    assert synced
                    assert all("--no-install-project" in line for line in runtime_syncs)
                    initialization += 1
                    assert 'scripts.release.ci_runtime_checkpoint --repository . --run-id "$runtimeRunId"' in script
                    lines = script.splitlines()
                    for command in (line for line in lines if "-m scripts.release.ci_runtime_checkpoint" in line):
                        assert lines[lines.index(command) + 1].strip() == "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"
                    if "--reserve" in script:
                        assert script.index("--reserve") < script.index("cargo build") < script.index("--seal")
                if "-m desktop.scripts.prepare_bundle --" not in script:
                    continue
                found += 1
                assert initialization == 1
                assert script.index("-m scripts.release.ci_runtime_checkpoint") < script.index("-m desktop.scripts.prepare_bundle")
                assert '--run-id "$runtimeRunId"' in script
                assert '--ci-runtime-checkpoint "$runtimeCheckpoint"' in script
                assert "--storage-generated-bytes" not in script
                for option in ("purpose", "sharing", "retention-reason"):
                    assert "--storage-" + option in script
            if initialization:
                for step in job["steps"]:
                    assert all("--no-sync" in line for line in step.get("run", "").splitlines()
                               if "uv run " in line)
                uploads = [step for step in job["steps"]
                           if "actions/upload-artifact@" in step.get("uses", "")
                           and "ci-runtime-pre-seal.json" in step.get("with", {}).get("path", "")]
                assert len(uploads) == 1
                assert "always()" in uploads[0]["if"]
                assert "ci-runtime-seal-review.json" in uploads[0]["with"]["path"]
                assert uploads[0]["with"]["include-hidden-files"] is True
                assert len(uploads[0]["with"]["path"].splitlines()) == 5
                assert "*" not in uploads[0]["with"]["path"]
    assert found == 4
