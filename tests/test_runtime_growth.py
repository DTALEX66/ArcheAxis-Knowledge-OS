"""Small runtime producer boundaries; no engine, uv or actual runtime execution."""
import builtins
import copy
import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.release import runtime_growth as growth
from scripts.runtime import runtime_resources as resources


def core_pair(tmp_path, monkeypatch, name="archeaxis_api.exe"):
    """Real tiny hardlinks; the name enumerator alone is synthetic on POSIX."""
    root = tmp_path / ".project-local/build/cargo"
    source = root / "release/archeaxis-api.exe"
    pair = root / "release/deps" / name
    pair.parent.mkdir(parents=True)
    source.write_bytes(b"tiny Core; never executed")
    os.link(source, pair)
    monkeypatch.setattr(growth.portable, "REPO", tmp_path)
    monkeypatch.setattr(growth.portable.dev, "layout", lambda *a, **k: {"cargo_build": root})
    if os.name != "nt":
        monkeypatch.setattr(resources, "_core_link_paths", lambda path: {
            "paths": [source, pair], "raw_names": [str(source), str(pair)], "method": "SYNTHETIC_NAMES_REAL_POSIX_INODES"})
    return source, pair


@pytest.mark.parametrize("name", ["archeaxis_api.exe", "archeaxis_api-1234567890abcdef.exe"])
def test_core_only_materializes_exact_cargo_pair(tmp_path, monkeypatch, name):
    from desktop.scripts.prepare_bundle import install_core
    source, pair = core_pair(tmp_path, monkeypatch, name)
    with pytest.raises(ValueError, match="independent"):
        growth.row(source)
    target = tmp_path / "output"
    staged = install_core(destination=target, core=source)
    assert staged.read_bytes() == source.read_bytes()
    assert staged.stat().st_nlink == 1
    assert source.stat().st_nlink == pair.stat().st_nlink == 2
    assert not os.path.samestat(staged.stat(), source.stat())


@pytest.mark.parametrize("change", ["third", "missing", "different-inode", "foreign-pair", "foreign-root",
                                    "wrong-name", "directory", "symbolic", "enumeration-error"])
def test_core_pair_role_rejects_unqualified_links(tmp_path, monkeypatch, change):
    source, pair = core_pair(tmp_path, monkeypatch)
    names = [source, pair]
    if change == "third":
        os.link(source, pair.with_name("extra.exe"))
    elif change in {"missing", "different-inode"}:
        pair.unlink()
        # Keep nlink == 2 while the claimed deps path is absent or another inode.
        os.link(source, pair.with_name("unclaimed.exe"))
        if change == "different-inode":
            pair.write_bytes(source.read_bytes())
    elif change == "foreign-pair":
        pair.unlink()
        pair = tmp_path / "outside.exe"
        os.link(source, pair)
        names = [source, pair]
    elif change == "foreign-root":
        source = source.rename(source.with_name("foreign.exe"))
        names = [source, pair]
    elif change == "wrong-name":
        pair = pair.rename(pair.with_name("different.exe"))
        names = [source, pair]
    elif change == "directory":
        source.unlink()
        source.mkdir()
    elif change == "symbolic":
        # The portable safe-path rejection is also exercised by native symlink fixtures elsewhere.
        original = resources.checked
        def linked(path):
            if path == source:
                raise ValueError("Linked candidate path rejected")
            return original(path)
        monkeypatch.setattr(resources, "checked", linked)
    def enumerate_names(path):
        if change == "enumeration-error":
            raise OSError("fixture cannot enumerate hardlink names")
        return {"paths": names, "raw_names": [str(p) for p in names], "method": "SYNTHETIC_NAMES_REAL_INODES"}
    monkeypatch.setattr(resources, "_core_link_paths", enumerate_names, raising=False)
    with pytest.raises((ValueError, OSError)) as caught:
        growth.core_row(source)
    assert any("Core input public lstat" in note for note in caught.value.__notes__)


@pytest.mark.parametrize("change", ["inode", "same-size", "grow", "short", "destination-hardlink", "destination-exists"])
def test_core_pair_copy_rechecks_planned_identity_and_independent_destination(tmp_path, monkeypatch, change):
    source, pair = core_pair(tmp_path, monkeypatch)
    identity = growth.core_row(source)
    destination = tmp_path / "copied.exe"
    if change == "destination-hardlink":
        os.link(source, destination)
    elif change == "destination-exists":
        destination.write_bytes(b"preserve existing")
    original = builtins.open
    reads = 0
    def mutate(path, mode="r", *args, **kwargs):
        nonlocal reads
        if growth.plain(path) == source and mode == "rb":
            reads += 1
            if change == "inode":
                raw = source.read_bytes()
                source.unlink()
                pair.unlink()
                source.write_bytes(raw)
                os.link(source, pair)
        stream = original(path, mode, *args, **kwargs)
        if growth.plain(path) != source or mode != "rb" or reads != 2 or change not in {"same-size", "grow", "short"}:
            return stream
        class ChangingReader:
            changed = False
            def __getattr__(self, name):
                return getattr(stream, name)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return stream.__exit__(*args)
            def read(self, count):
                if not self.changed:
                    self.changed = True
                    size = {"same-size": identity["bytes"], "grow": identity["bytes"] + 40, "short": 1}[change]
                    source.write_bytes(b"X" * size)
                return stream.read(count)
        return ChangingReader()
    monkeypatch.setattr(builtins, "open", mutate)
    with growth.batch(tmp_path, {source: identity}, identity["bytes"]), pytest.raises((ValueError, FileExistsError)):
        growth.copy2(source, destination)
    if change.startswith("destination"):
        assert destination.read_bytes() == (source.read_bytes() if change == "destination-hardlink" else b"preserve existing")
    elif destination.exists():
        assert destination.stat().st_size <= identity["bytes"]


def test_core_pair_enumeration_order_is_not_identity(tmp_path, monkeypatch):
    source, pair = core_pair(tmp_path, monkeypatch)
    initial = growth.core_row(source)
    enumerate_names = resources._core_link_paths
    def reverse(path):
        observed = enumerate_names(path)
        return {**observed, "paths": list(reversed(observed["paths"])),
                "raw_names": list(reversed(observed["raw_names"]))}
    monkeypatch.setattr(resources, "_core_link_paths", reverse)
    assert growth.core_row(source) == initial
    with growth.batch(tmp_path, {source: initial}, initial["bytes"]):
        growth.copy2(source, tmp_path / "independent.exe")
    assert (tmp_path / "independent.exe").stat().st_nlink == 1


@pytest.mark.skipif(os.name != "nt", reason="Native Windows handle-close evidence")
@pytest.mark.parametrize("third", [False, True])
def test_core_native_name_handle_close_failure_preserves_primary(tmp_path, monkeypatch, third):
    import ctypes
    from ctypes import wintypes
    source, pair = core_pair(tmp_path, monkeypatch)
    if third:
        os.link(source, pair.with_name("third.exe"))
    real = ctypes.WinDLL("kernel32", use_last_error=True)
    real.FindClose.argtypes, real.FindClose.restype = [wintypes.HANDLE], wintypes.BOOL
    closed = []
    def close(handle):
        assert real.FindClose(handle)
        closed.append(handle)
        ctypes.set_last_error(6)
        return False  # Actual handle already closed; no native leak in the fixture.
    kernel = SimpleNamespace(FindFirstFileNameW=real.FindFirstFileNameW,
                             FindNextFileNameW=real.FindNextFileNameW, FindClose=close)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **k: kernel)
    with pytest.raises(ValueError if third else OSError) as caught:
        resources._core_link_paths(source)
    assert len(closed) == 1
    if third:
        assert "more than two" in str(caught.value)
        assert any("FindClose" in note for note in caught.value.__notes__)


def test_core_copy_rejects_dual_role_without_reading_source(tmp_path, monkeypatch):
    source, _ = core_pair(tmp_path, monkeypatch)
    identity = growth.core_row(source)
    identity["interpreter_alias"] = {"target": str(source)}
    with growth.batch(tmp_path, {source: identity}, identity["bytes"]), pytest.raises(ValueError, match="exclusive"):
        growth.copy2(source, tmp_path / "never-created.exe")
    assert not (tmp_path / "never-created.exe").exists()


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
