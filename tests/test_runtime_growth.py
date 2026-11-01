"""Small runtime producer boundaries; no engine, uv or actual runtime execution."""
import builtins
import copy
import hashlib
import json
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.release import runtime_growth as growth


def mock_file_alias(monkeypatch, alias, target, *, mode=stat.S_IFLNK, reparse_tag=0xA000000C):
    """Model native file-symlink metadata without requiring Windows link privileges."""
    alias.write_bytes(b"native-link-fixture")
    links = {alias: str(target)}
    original_stat, original_readlink = Path.lstat, growth.os.readlink
    def lstat(path, *args, **kwargs):
        if growth.plain(path) in links:
            return SimpleNamespace(st_mode=mode | 0o777, st_file_attributes=0x400,
                                   st_reparse_tag=reparse_tag)
        return original_stat(path, *args, **kwargs)
    def readlink(path, *args, **kwargs):
        if growth.plain(path) in links:
            return links[growth.plain(path)]
        return original_readlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(growth.os, "readlink", readlink)
    return links


def test_implicit_python3_alias_materializes_bounded_independent_file(tmp_path, monkeypatch):
    from desktop.scripts.stage_runtime import stage_runtime
    source = tmp_path / "base"
    source.mkdir()
    python = source / "python.exe"
    python.write_bytes(b"tiny interpreter; never run")
    alias = source / "python3.exe"
    mock_file_alias(monkeypatch, alias, "python.exe")
    monkeypatch.setattr(growth.sys, "base_prefix", str(source))
    destination = tmp_path / "repo/.project-local/runtime"
    staged = stage_runtime(repository=tmp_path / "repo", destination=destination)
    copied = staged.with_name("python3.exe")
    assert copied.read_bytes() == python.read_bytes()
    assert not copied.is_symlink() and copied.stat().st_nlink == 1
    binding = json.loads((destination / "python-source-binding.json").read_bytes())
    assert binding["executable_aliases"][str(alias)]["raw_target"] == "python.exe"
    assert binding["executable_aliases"][str(alias)]["target"] == str(python)
    with pytest.raises(ValueError, match="linked"):
        growth.snapshot(source)  # Explicit/generic donors never inherit this exception.


@pytest.mark.parametrize("linked", [False, True])
def test_runtime_inputs_explicit_regular_donor_keeps_generic_contract(tmp_path, monkeypatch, linked):
    from desktop.scripts.stage_runtime import runtime_inputs
    source = tmp_path / "explicit-donor"
    source.mkdir()
    python = source / "python.exe"
    python.write_bytes(b"explicit donor")
    monkeypatch.setattr(growth.sys, "base_prefix", str(tmp_path / "different-implicit-root"))
    if linked:
        mock_file_alias(monkeypatch, source / "python3.exe", "python.exe")
        with pytest.raises(ValueError, match="linked"):
            runtime_inputs(source)
    else:
        assert runtime_inputs(source) == {python: growth.row(python)}


@pytest.mark.parametrize("change", ["outside", "other-file", "directory", "directory-entry", "nested",
                                    "unknown-name", "unknown-reparse", "wrong-tag", "primary-link"])
def test_python3_alias_exception_rejects_other_redirects(tmp_path, monkeypatch, change):
    from desktop.scripts.stage_runtime import stage_runtime
    source = tmp_path / "base"
    source.mkdir()
    (source / "python.exe").write_bytes(b"expected")
    other = tmp_path / "other.exe"
    other.write_bytes(b"expected")
    alias, target = source / "python3.exe", "python.exe"
    if change == "outside":
        target = str(other)
    elif change == "other-file":
        (source / "other.exe").write_bytes(b"expected")
        target = "other.exe"
    elif change == "directory":
        target = str(source)
    elif change == "nested":
        (source / "Lib").mkdir()
        alias, target = source / "Lib/python3.exe", str(source / "python.exe")
    elif change == "unknown-name":
        alias = source / "python3.12.exe"
    if change == "primary-link":
        alias, target = source / "python.exe", str(other)
    mock_file_alias(monkeypatch, alias, target,
                    mode=stat.S_IFREG if change == "unknown-reparse" else stat.S_IFLNK,
                    reparse_tag=0xA0000003 if change in {"unknown-reparse", "wrong-tag"} else 0xA000000C)
    if change == "wrong-tag":
        native_os = growth.os
        class WindowsMetadataOS:
            name = "nt"
            def __getattr__(self, name):
                return getattr(native_os, name)
        monkeypatch.setattr(growth, "os", WindowsMetadataOS())
    if change == "directory-entry":
        alias.unlink()
        alias.mkdir()
    monkeypatch.setattr(growth.sys, "base_prefix", str(source))
    destination = tmp_path / "repo/.project-local/runtime"
    with pytest.raises(ValueError):
        stage_runtime(repository=tmp_path / "repo", destination=destination)
    assert not destination.exists()


@pytest.mark.parametrize("change", ["retarget", "same-size-target", "replaced-link"])
def test_python3_alias_plan_is_rechecked_before_and_after_copy(tmp_path, monkeypatch, change):
    from desktop.scripts.stage_runtime import runtime_inputs
    source = tmp_path / "base"
    source.mkdir()
    python = source / "python.exe"
    python.write_bytes(b"expected")
    alias = source / "python3.exe"
    links = mock_file_alias(monkeypatch, alias, "python.exe")
    monkeypatch.setattr(growth.sys, "base_prefix", str(source))
    binding = growth.interpreter_source()
    inputs = runtime_inputs(source, interpreter_binding=binding)
    assert inputs[alias]["bytes"] == python.stat().st_size
    target = tmp_path / "output"
    target.mkdir()
    original_open = builtins.open
    def mutate(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        if growth.plain(path) == python and mode == "rb":
            if change == "retarget":
                links[alias] = str(tmp_path / "foreign.exe")
            elif change == "same-size-target":
                python.write_bytes(b"tampered")
            else:
                links.pop(alias)
        return stream
    monkeypatch.setattr(builtins, "open", mutate)
    with (growth.batch(target, inputs, sum(row["bytes"] for row in inputs.values()), interpreter_binding=binding),
          pytest.raises(ValueError)):
        growth.copy2(alias, target / "python3.exe", identity=inputs[alias])
    assert (target / "python3.exe").stat().st_size <= inputs[alias]["bytes"]


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
                assert uploads[0]["uses"] == "actions/upload-artifact@834a144ee995460fba8ed112a2fc961b36a5ec5a"
                assert "include-hidden-files" not in uploads[0]["with"]
                assert len(uploads[0]["with"]["path"].splitlines()) == 5
                assert "*" not in uploads[0]["with"]["path"]
    assert found == 4
