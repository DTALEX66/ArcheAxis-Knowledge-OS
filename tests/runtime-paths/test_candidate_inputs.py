"""Tiny fixed-role inputs only; no retained Host, assembler or network is run."""
import builtins
import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.runtime import candidate_inputs as subject


@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path / "repo 空间"
    root.mkdir()
    dev = root / ".project-local"
    key = hashlib.sha256(str(root).casefold().encode()).hexdigest()[:10]
    run = dev / "runs" / key / "prepare"
    (run / "artifacts").mkdir(parents=True)
    (run / "tmp").mkdir()
    (run / "run-metadata.json").write_text(json.dumps({
        "owner": "ArcheAxis-Knowledge-OS", "worktree_root": str(root), "run_id": run.name,
        "source_commit": "a" * 40, "source_patch_sha256": "b" * 64}), encoding="utf-8")
    paths = {"root": root, "dev": dev, "run": run, "artifacts": run / "artifacts", "tmp": run / "tmp"}
    host = b"tiny Host; never executed"
    pin = json.dumps({"host_sha256": hashlib.sha256(host).hexdigest(),
                      "donor_path": r"D:\historical public donor\ArcheAxis.exe"}).encode()
    bodies = [host, b'{"status":"HISTORICAL_MIXED_COMPONENTS"}\n', pin]
    rows = []
    for row, body in zip(subject.FILES, bodies, strict=True):
        role, relative, destination, _, _ = row
        source = root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(body)
        rows.append((role, relative, destination, len(body), hashlib.sha256(body).hexdigest()))
    monkeypatch.setattr(subject, "FILES", tuple(rows))  # No production CLI hash/source override exists.
    return paths, rows, bodies


def test_fixed_host_role_preserves_original_metadata_and_explicit_consumer_argv(case, monkeypatch):
    paths, rows, bodies = case
    def no_walk(*args, **kwargs):
        pytest.fail("No payload tree enumeration is needed for three fixed objects")
    monkeypatch.setattr(os, "walk", no_walk)
    result = subject.prepare(paths)
    target = paths["artifacts"] / "cpphost-input"
    assert set(os.listdir(target)) == {*(row[2] for row in rows), "SOURCE-MAP.json"}
    for row, body in zip(rows, bodies, strict=True):
        source, copied = paths["root"] / row[1], target / row[2]
        assert source.read_bytes() == copied.read_bytes() == body
        assert copied.stat().st_nlink == 1 and not os.path.samestat(source.stat(), copied.stat())
    document = json.loads((target / "SOURCE-MAP.json").read_bytes())
    assert document["status"] == "COMPLETE_HOST_INPUT_ONLY"
    assert document["whole_package"] == "HOLD_NOT_RETIRED"
    assert document["original_donor_path"] == json.loads(bodies[2])["donor_path"]
    assert document["copied_bytes"] == sum(len(body) for body in bodies)
    assert result["consumer_argv"] == ["--host-exe", str(target / rows[0][2]),
                                       "--donor-manifest", str(target / rows[2][2])]
    assert document["execution"] == "NOT_EXECUTED"
    with pytest.raises(ValueError, match="Fresh"):
        subject.prepare(paths)


@pytest.mark.parametrize("change", ["changed", "hardlink", "private", "outside", "owner", "linked-owner"])
def test_invalid_sources_or_caller_rejected_before_output(case, monkeypatch, change):
    paths, rows, _ = case
    source = paths["root"] / rows[0][1]
    if change == "changed":
        source.write_bytes(b"changed")
    elif change == "hardlink":
        os.link(source, source.with_name("another.exe"))
    elif change in {"private", "outside"}:
        replacement = ".project-local/runs/old/.codex/state" if change == "private" else "../outside.exe"
        monkeypatch.setattr(subject, "FILES", ((rows[0][0], replacement, *rows[0][2:]), *rows[1:]))
    elif change == "owner":
        (paths["run"] / "run-metadata.json").write_text("{}", encoding="utf-8")
    else:
        paths["root"] = paths["root"] / "linked"
    with pytest.raises((ValueError, OSError)):
        subject.prepare(paths)
    assert not (paths["artifacts"] / "cpphost-input").exists()


@pytest.mark.parametrize("change", ["grow", "short", "same-size", "inode"])
def test_mutating_source_is_bounded_and_failure_preserved(case, monkeypatch, change):
    paths, rows, _ = case
    source = paths["root"] / rows[0][1]
    original = builtins.open
    reads = 0
    def mutate(path, mode="r", *args, **kwargs):
        nonlocal reads
        if Path(os.fspath(path).removeprefix("\\\\?\\")) == source and mode == "rb":
            reads += 1
            # First read is preflight; second is the copy's actual source open.
            if reads == 2:
                if change == "inode":
                    raw = source.read_bytes()
                    source.unlink()
                    source.write_bytes(raw)
                else:
                    length = {"grow": rows[0][3] + 25, "short": 1, "same-size": rows[0][3]}[change]
                    source.write_bytes(b"X" * length)
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", mutate)
    with pytest.raises(ValueError):
        subject.prepare(paths)
    target = paths["artifacts"] / "cpphost-input"
    assert (target / "FAILURE.json").is_file()
    assert (target / "INCOMPLETE").is_file()
    if (target / rows[0][2]).exists():
        assert (target / rows[0][2]).stat().st_size <= rows[0][3]
    assert not (target / "SOURCE-MAP.json").exists()


def test_late_source_change_rejected_even_after_its_copy(case, monkeypatch):
    paths, rows, _ = case
    original = subject._copy
    def change_earlier(source, destination, expected, metadata, progress):
        original(source, destination, expected, metadata, progress)
        if destination.name == rows[-1][2]:
            (paths["root"] / rows[0][1]).write_bytes(b"X" * rows[0][3])
    monkeypatch.setattr(subject, "_copy", change_earlier)
    with pytest.raises(ValueError):
        subject.prepare(paths)
    assert (paths["artifacts"] / "cpphost-input/FAILURE.json").exists()


def test_failure_evidence_error_does_not_replace_source_error(case, monkeypatch):
    paths, _, _ = case
    def original_failure(*args, **kwargs):
        raise ValueError("original copy rejection")
    original = subject._save
    def failed_failure(path, body):
        if path.name == "FAILURE.json":
            raise OSError("failure evidence unavailable")
        return original(path, body)
    monkeypatch.setattr(subject, "_copy", original_failure)
    monkeypatch.setattr(subject, "_save", failed_failure)
    with pytest.raises(ValueError, match="original copy rejection") as caught:
        subject.prepare(paths)
    assert any("failure evidence unavailable" in note for note in caught.value.__notes__)


@pytest.mark.parametrize("change", ["grow", "short", "same-size"])
def test_source_changes_during_actual_bounded_copy(case, monkeypatch, change):
    paths, rows, _ = case
    source = paths["root"] / rows[0][1]
    original = builtins.open
    reads = 0
    def open_reader(path, mode="r", *args, **kwargs):
        nonlocal reads
        stream = original(path, mode, *args, **kwargs)
        if Path(os.fspath(path).removeprefix("\\\\?\\")) != source or mode != "rb":
            return stream
        reads += 1
        if reads != 2:
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
                assert 0 < count <= rows[0][3]
                if not self.changed:
                    self.changed = True
                    size = {"grow": rows[0][3] + 25, "short": 1, "same-size": rows[0][3]}[change]
                    source.write_bytes(b"X" * size)
                return stream.read(count)
        return ChangingReader()
    monkeypatch.setattr(builtins, "open", open_reader)
    with pytest.raises(ValueError):
        subject.prepare(paths)
    target = paths["artifacts"] / "cpphost-input"
    assert (target / rows[0][2]).stat().st_size <= rows[0][3]
    assert (target / "FAILURE.json").exists()
    assert not (target / "SOURCE-MAP.json").exists()


@pytest.mark.parametrize("hardlink", [False, True])
def test_existing_destination_member_is_never_overwritten(case, monkeypatch, hardlink):
    paths, rows, bodies = case
    original = subject._copy
    def collide(source, destination, expected, metadata, progress):
        if hardlink:
            os.link(source, destination)
        else:
            destination.write_bytes(b"preserve existing")
        return original(source, destination, expected, metadata, progress)
    monkeypatch.setattr(subject, "_copy", collide)
    with pytest.raises((ValueError, FileExistsError)):
        subject.prepare(paths)
    target = paths["artifacts"] / "cpphost-input"
    assert (target / rows[0][2]).read_bytes() == (bodies[0] if hardlink else b"preserve existing")
    assert (target / "FAILURE.json").exists()


@pytest.mark.parametrize("parent", [False, True])
def test_reparse_source_or_ancestor_rejected_before_payload_read(case, monkeypatch, parent):
    paths, rows, _ = case
    source = paths["root"] / rows[0][1]
    linked = source.parent if parent else source
    original = Path.lstat
    def reparse(path, *args, **kwargs):
        if Path(os.fspath(path).removeprefix("\\\\?\\")) == linked:
            return SimpleNamespace(st_mode=stat.S_IFDIR if parent else stat.S_IFREG, st_file_attributes=0x400)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(ValueError, match="linked|Linked"):
        subject.prepare(paths)
    assert not (paths["artifacts"] / "cpphost-input").exists()


def test_map_fsync_failure_keeps_failure_marker_and_original_error(case, monkeypatch):
    paths, rows, _ = case
    original = os.fsync
    calls = 0
    def fail_map(fd):
        nonlocal calls
        calls += 1
        if calls == len(rows) + 2:  # Claim + three payloads precede source-map fsync.
            raise OSError("source-map fsync failed")
        return original(fd)
    monkeypatch.setattr(os, "fsync", fail_map)
    with pytest.raises(OSError, match="source-map fsync failed"):
        subject.prepare(paths)
    target = paths["artifacts"] / "cpphost-input"
    assert (target / "SOURCE-MAP.json").exists()  # Preserved partial evidence is not usable success.
    failure = json.loads((target / "FAILURE.json").read_bytes())
    assert failure["error"] == "source-map fsync failed"
    assert (target / "INCOMPLETE").is_file()


def test_double_metadata_failure_keeps_incomplete_and_primary_error(case, monkeypatch):
    paths, rows, _ = case
    original_fsync, original_save = os.fsync, subject._save
    calls = 0
    def fail_map(fd):
        nonlocal calls
        calls += 1
        if calls == len(rows) + 2:
            raise OSError("original map fsync failure")
        return original_fsync(fd)
    def fail_failure(path, body):
        if path.name == "FAILURE.json":
            raise OSError("secondary failure marker write failure")
        return original_save(path, body)
    monkeypatch.setattr(os, "fsync", fail_map)
    monkeypatch.setattr(subject, "_save", fail_failure)
    with pytest.raises(OSError, match="original map fsync failure") as caught:
        subject.prepare(paths)
    target = paths["artifacts"] / "cpphost-input"
    assert (target / "SOURCE-MAP.json").is_file()
    assert (target / "INCOMPLETE").is_file()
    assert not (target / "FAILURE.json").exists()
    assert any("secondary failure marker write failure" in note for note in caught.value.__notes__)


def test_cli_has_no_hash_source_destination_override_and_fails_without_canonical_run(monkeypatch, capsys):
    for option in ("--sha256", "--source", "--destination", "--manifest-sha256"):
        with pytest.raises(SystemExit) as caught:
            subject.main(["--role", "cppcand1-host", option, "arbitrary"])
        assert caught.value.code == 2
    monkeypatch.delenv("ARCHEAXIS_RUN_ROOT", raising=False)
    assert subject.main(["--role", "cppcand1-host"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAIL_CLOSED"
    assert "consumer_argv" not in result
