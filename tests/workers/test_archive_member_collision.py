"""Named synthetic ZIP/TAR collisions against the actual archive worker.

The fixture owns every target; tests do not operate on existing project data.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import tarfile
import zipfile

import pytest

from scripts.release.tauri_portable_candidate import native

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/document/worker_archive.py"
PRIMARY = "synthetic-note.txt"
SECONDARY = "synthetic-other.txt"
OFFERED_PRIMARY = "0001-synthetic-note.txt"
OFFERED_SECONDARY = "0002-synthetic-other.txt"
PAYLOAD = b"synthetic archive member\n"
OTHER = b"synthetic second member\n"
EXISTING = b"preexisting owner bytes\n"


def load_worker():
    spec = importlib.util.spec_from_file_location("archive_collision_worker", WORKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path: Path) -> bytes:
    return Path(native(path)).read_bytes()


def write(path: Path, payload: bytes) -> None:
    Path(native(path)).write_bytes(payload)


def snapshot(path: Path):
    info = os.lstat(native(path))
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns)


def archive_bytes(kind: str, entries=None) -> bytes:
    if entries is None:
        entries = ((PRIMARY, PAYLOAD), (SECONDARY, OTHER))
    out = io.BytesIO()
    if kind == "zip":
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, content in entries:
                archive.writestr(name, content)
    else:
        with tarfile.open(fileobj=out, mode="w") as archive:
            for name, content in entries:
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
    return out.getvalue()


@pytest.fixture(params=["zip", "tar"])
def case(tmp_path, request):
    root = tmp_path / "collision"
    Path(native(root)).mkdir()
    source = root / ("synthetic-source." + request.param)
    raw = archive_bytes(request.param)
    write(source, raw)
    return load_worker(), root, source, raw


def extract(worker, source, raw, members):
    result = worker.extract(str(native(source)), member_dir=members)
    assert read(source) == raw, "source archive must retain its original bytes"
    return result


def declarations(result):
    return result["loss_receipt"]["params"]["structure"]["extractable_members"]


def assert_conflict_receipt(result):
    assert result["loss_receipt"]["losses"], "member refusal must be recorded"
    assert PRIMARY not in [item["name"] for item in declarations(result)]


def assert_secondary(result, members):
    offered = declarations(result)
    assert [item["name"] for item in offered] == [SECONDARY]
    assert offered[0]["file"] == OFFERED_SECONDARY
    assert offered[0]["bytes"] == len(OTHER)
    assert offered[0]["sha256"] == hashlib.sha256(OTHER).hexdigest()
    assert read(members / OFFERED_SECONDARY) == OTHER


def make_directory(path: Path):
    Path(native(path)).mkdir()


@pytest.mark.parametrize("same_length", [False, True])
def test_different_existing_member_is_preserved_and_never_declared(case, same_length):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    existing = members / OFFERED_PRIMARY
    old_bytes = b"x" * len(PAYLOAD) if same_length else EXISTING
    write(existing, old_bytes)
    unrelated = members / "synthetic-unrelated.txt"
    write(unrelated, b"unrelated owner bytes\n")
    os.utime(native(existing), ns=(1_600_000_000_000_000_000,) * 2)
    before = snapshot(existing)
    unrelated_before = snapshot(unrelated)
    result = extract(worker, source, raw, members)
    assert read(existing) == old_bytes
    assert snapshot(existing) == before
    assert read(unrelated) == b"unrelated owner bytes\n" and snapshot(unrelated) == unrelated_before
    assert_conflict_receipt(result)
    assert_secondary(result, members)


def test_same_content_retry_reuses_without_overwrite(case):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    existing = members / OFFERED_PRIMARY
    write(existing, PAYLOAD)
    os.utime(native(existing), ns=(1_600_000_000_000_000_000,) * 2)
    before = snapshot(existing)
    result = extract(worker, source, raw, members)
    assert read(existing) == PAYLOAD
    assert snapshot(existing) == before, "retry must not rewrite an identical existing file"
    offered = declarations(result)
    assert [item["name"] for item in offered] == [PRIMARY, SECONDARY]
    assert offered[0]["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert read(members / OFFERED_SECONDARY) == OTHER
    assert "written out or verified" in result["loss_receipt"]["params"]["projection_note"]


@pytest.mark.parametrize("position", ["target", "directory", "ancestor"])
def test_observed_reparse_attribute_is_refused_without_following(case, monkeypatch, position):
    """A simulated Windows attribute, not an actual junction qualification."""
    worker, root, source, raw = case
    parent = root / "synthetic-parent"
    make_directory(parent)
    members = parent / "members"
    make_directory(members)
    existing = members / OFFERED_PRIMARY
    write(existing, PAYLOAD)
    before = snapshot(existing)
    marked = {"target": existing, "directory": members, "ancestor": parent}[position]
    wanted = os.path.normcase(os.path.normpath(str(native(marked))))
    original_lstat = os.lstat
    observed = []

    class WithReparseAttribute:
        def __init__(self, info):
            self.info = info

        def __getattr__(self, name):
            if name == "st_file_attributes":
                return getattr(self.info, name, 0) | 0x400
            return getattr(self.info, name)

    def synthetic_lstat(path, *args, **kwargs):
        info = original_lstat(path, *args, **kwargs)
        if os.path.normcase(os.path.normpath(os.fsdecode(path))) == wanted:
            observed.append(True)
            return WithReparseAttribute(info)
        return info

    monkeypatch.setattr(worker.os, "lstat", synthetic_lstat)
    if position == "target":
        result = extract(worker, source, raw, members)
        assert_conflict_receipt(result)
        assert_secondary(result, members)
    else:
        with pytest.raises(OSError):
            worker.extract(str(native(source)), member_dir=members)
        assert read(source) == raw
        assert not Path(native(members / OFFERED_SECONDARY)).exists()
    assert observed, "the intended synthetic attribute must be observed"
    assert read(existing) == PAYLOAD and snapshot(existing) == before


def test_growth_during_retry_is_read_with_a_fixed_bound_and_not_declared(case, monkeypatch):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    existing = members / OFFERED_PRIMARY
    write(existing, PAYLOAD)
    expected_identity = (os.stat(native(existing)).st_dev, os.stat(native(existing)).st_ino)
    original_read = os.read
    reads = []

    def grow_then_read(fd, maximum):
        info = os.fstat(fd)
        if (info.st_dev, info.st_ino) == expected_identity:
            if not reads:
                try:
                    with Path(native(existing)).open("ab") as changed:
                        changed.write(b"synthetic-growth")
                except PermissionError:
                    pytest.skip("filesystem does not permit the controlled concurrent append")
            data = original_read(fd, maximum)
            reads.append((maximum, len(data)))
            return data
        return original_read(fd, maximum)

    monkeypatch.setattr(worker.os, "read", grow_then_read)
    result = extract(worker, source, raw, members)
    assert reads and all(requested <= len(PAYLOAD) + 1 for requested, _ in reads)
    assert sum(actual for _, actual in reads) == len(PAYLOAD) + 1
    assert read(existing) == PAYLOAD + b"synthetic-growth"
    assert_conflict_receipt(result)
    assert_secondary(result, members)


@pytest.mark.parametrize("read_fails", [False, True])
def test_retry_handles_short_reads_and_rejects_read_errors(case, monkeypatch, read_fails):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    existing = members / OFFERED_PRIMARY
    write(existing, PAYLOAD)
    before = snapshot(existing)
    info = os.stat(native(existing))
    wanted = (info.st_dev, info.st_ino)
    original_read = os.read
    reads = []

    def short_or_failed_read(fd, maximum):
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino) == wanted:
            reads.append(maximum)
            if read_fails:
                raise OSError("synthetic read failure")
            return original_read(fd, min(maximum, 3))
        return original_read(fd, maximum)

    monkeypatch.setattr(worker.os, "read", short_or_failed_read)
    result = extract(worker, source, raw, members)
    assert reads and all(maximum <= len(PAYLOAD) + 1 for maximum in reads)
    assert read(existing) == PAYLOAD and snapshot(existing) == before
    if read_fails:
        assert_conflict_receipt(result)
        assert_secondary(result, members)
    else:
        assert len(reads) > 2
        assert [item["name"] for item in declarations(result)] == [PRIMARY, SECONDARY]


def test_failed_partial_write_is_not_declared_or_cleaned_as_an_existing_file(case, monkeypatch):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    target = members / OFFERED_PRIMARY
    original_write = os.write
    calls = []

    def partial_then_fail(fd, data):
        try:
            current = os.stat(native(target))
        except FileNotFoundError:
            return original_write(fd, data)
        opened = os.fstat(fd)
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            return original_write(fd, data)
        calls.append(True)
        if len(calls) == 1:
            return original_write(fd, data[:3])
        raise OSError("synthetic write failure")

    monkeypatch.setattr(worker.os, "write", partial_then_fail)
    result = extract(worker, source, raw, members)
    assert len(calls) == 2
    assert read(target) == PAYLOAD[:3]
    assert_conflict_receipt(result)
    assert_secondary(result, members)


def test_mismatching_new_file_is_not_declared(case, monkeypatch):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    target = members / OFFERED_PRIMARY
    original_write = os.write
    changed = []

    def write_different_bytes(fd, data):
        try:
            current = os.stat(native(target))
        except FileNotFoundError:
            return original_write(fd, data)
        opened = os.fstat(fd)
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            return original_write(fd, data)
        changed.append(True)
        return original_write(fd, b"x" * len(data))

    monkeypatch.setattr(worker.os, "write", write_different_bytes)
    result = extract(worker, source, raw, members)
    assert changed
    assert read(target) == b"x" * len(PAYLOAD)
    assert_conflict_receipt(result)
    assert_secondary(result, members)


def test_member_read_stays_bounded_if_stream_exceeds_its_metadata(case, monkeypatch):
    """Inject excess bytes into a named ZIP/TAR member stream; no real archive is corrupted."""
    worker, root, source, raw = case
    members = root / "members"
    budget = len(PAYLOAD) + len(OTHER)
    monkeypatch.setattr(worker, "MEMBER_BYTES_CAP", budget)
    calls = []

    class ExcessStream:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, maximum):
            calls.append(maximum)
            return b"x" * maximum

    container_type = worker.zipfile.ZipFile if source.suffix == ".zip" else worker._TarContainer
    original_open = container_type.open

    def synthetic_open(container, info, *args, **kwargs):
        if info.filename == PRIMARY:
            return ExcessStream()
        return original_open(container, info, *args, **kwargs)

    monkeypatch.setattr(container_type, "open", synthetic_open)
    result = extract(worker, source, raw, members)
    assert calls and max(calls) <= len(PAYLOAD) + 1
    assert_conflict_receipt(result)
    assert not Path(native(members / OFFERED_PRIMARY)).exists()
    assert_secondary(result, members)


def hardlink_or_skip(existing: Path, link: Path):
    try:
        os.link(native(existing), native(link))
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hard link unsupported: {type(error).__name__}")
    if os.stat(native(existing)).st_nlink < 2:
        pytest.skip("hard-link count not observable on this filesystem")
    assert os.path.samefile(native(existing), native(link))


@pytest.mark.parametrize("same_bytes", [False, True])
def test_existing_hardlink_is_not_followed_even_for_same_bytes(case, same_bytes):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    victim = root / "synthetic-hardlink-victim.txt"
    before_bytes = PAYLOAD if same_bytes else EXISTING
    write(victim, before_bytes)
    os.utime(native(victim), ns=(1_600_000_000_000_000_000,) * 2)
    alias = members / OFFERED_PRIMARY
    hardlink_or_skip(victim, alias)
    before = snapshot(victim)
    result = extract(worker, source, raw, members)
    assert read(victim) == before_bytes and read(alias) == before_bytes
    assert snapshot(victim) == before
    assert_conflict_receipt(result)
    assert_secondary(result, members)


def symlink_or_skip(existing: Path, link: Path, *, directory=False):
    try:
        os.symlink(native(existing), native(link), target_is_directory=directory)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symbolic link unavailable: {type(error).__name__}")
    info = os.lstat(native(link))
    assert stat.S_ISLNK(info.st_mode)
    if os.name == "nt":
        assert getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def test_existing_member_symlink_does_not_modify_its_target(case):
    worker, root, source, raw = case
    members = root / "members"
    make_directory(members)
    victim = root / "synthetic-symlink-victim.txt"
    write(victim, EXISTING)
    before = snapshot(victim)
    alias = members / OFFERED_PRIMARY
    symlink_or_skip(victim, alias)
    result = extract(worker, source, raw, members)
    assert read(victim) == EXISTING and snapshot(victim) == before
    assert stat.S_ISLNK(os.lstat(native(alias)).st_mode)
    assert_conflict_receipt(result)
    assert_secondary(result, members)


def test_member_directory_symlink_does_not_write_through(case):
    worker, root, source, raw = case
    victim_dir = root / "synthetic-directory-victim"
    make_directory(victim_dir)
    victim = victim_dir / OFFERED_PRIMARY
    write(victim, EXISTING)
    before = snapshot(victim)
    members = root / "members"
    symlink_or_skip(victim_dir, members, directory=True)
    try:
        result = extract(worker, source, raw, members)
    except (OSError, ValueError):
        result = None
    assert read(source) == raw
    assert read(victim) == EXISTING and snapshot(victim) == before
    assert not Path(native(victim_dir / OFFERED_SECONDARY)).exists()
    if result is not None:
        assert declarations(result) == [] and result["loss_receipt"]["losses"]


@pytest.mark.parametrize("mode", ["first_short", "many_short", "early_eof", "declared_long", "declared_short"])
def test_member_stream_must_match_declared_size_and_reach_eof(case, monkeypatch, mode):
    """Inject stream behavior into named ZIP/TAR members; archives remain intact."""
    worker, root, source, raw = case
    members = root / "members"
    observed = {"requests": [], "returned": 0}
    supplied = PAYLOAD
    if mode == "declared_long":
        supplied = PAYLOAD[:-1]
    elif mode == "declared_short":
        supplied = PAYLOAD + b"!"

    class SyntheticStream:
        def __init__(self):
            self.stream = io.BytesIO(supplied)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.stream.close()

        def read(self, maximum):
            observed["requests"].append(maximum)
            if mode == "early_eof" and observed["returned"] >= 6:
                return b""
            if mode in ("many_short", "early_eof", "declared_long", "declared_short"):
                maximum = min(maximum, 3)
            elif mode == "first_short" and len(observed["requests"]) == 1:
                maximum = 1
            result = self.stream.read(maximum)
            observed["returned"] += len(result)
            return result

    container_type = worker.zipfile.ZipFile if source.suffix == ".zip" else worker._TarContainer
    original_open = container_type.open

    def synthetic_open(container, info, *args, **kwargs):
        if info.filename == PRIMARY:
            return SyntheticStream()
        return original_open(container, info, *args, **kwargs)

    monkeypatch.setattr(container_type, "open", synthetic_open)
    result = extract(worker, source, raw, members)
    assert observed["requests"] and observed["returned"] <= len(PAYLOAD) + 1
    if mode in ("first_short", "many_short"):
        assert len(observed["requests"]) >= 3, "short reads and EOF must both be observed"
        assert observed["returned"] == len(PAYLOAD)
        offered = declarations(result)
        assert [item["name"] for item in offered] == [PRIMARY, SECONDARY]
        assert read(members / OFFERED_PRIMARY) == PAYLOAD
        assert offered[0]["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
    else:
        assert_conflict_receipt(result)
        assert not Path(native(members / OFFERED_PRIMARY)).exists()
        assert_secondary(result, members)
    assert all(0 < size <= len(PAYLOAD) + 1 for size in observed["requests"])


@pytest.mark.parametrize("kind", ["zip", "tar"])
@pytest.mark.parametrize("size,budget", [(8, 8), (8, 7), (0, 0)])
def test_member_byte_budget_and_empty_member_boundaries(tmp_path, kind, size, budget, monkeypatch):
    worker = load_worker()
    source = tmp_path / f"synthetic-budget.{kind}"
    payload = b"b" * size
    raw = archive_bytes(kind, ((PRIMARY, payload),))
    write(source, raw)
    members = tmp_path / "members"
    monkeypatch.setattr(worker, "MEMBER_BYTES_CAP", budget)
    try:
        result = extract(worker, source, raw, members)
    except ValueError:
        assert kind == "tar" and size > budget
        assert read(source) == raw
        assert not Path(native(members)).exists()
        return
    if size > budget:
        assert declarations(result) == [] and result["loss_receipt"]["losses"]
        assert not Path(native(members / OFFERED_PRIMARY)).exists()
    else:
        assert [item["name"] for item in declarations(result)] == [PRIMARY]
        assert read(members / OFFERED_PRIMARY) == payload


def inject_publication_fault(worker, monkeypatch, target, mode):
    """Fault only the test-owned first target; close its original fd before failing."""
    calls = []
    if mode == "partial_write":
        original_write = os.write

        def fail_write(fd, data):
            opened = os.fstat(fd)
            try:
                current = os.stat(native(target))
            except FileNotFoundError:
                return original_write(fd, data)
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                return original_write(fd, data)
            calls.append(True)
            if len(calls) == 1:
                return original_write(fd, data[:3])
            raise OSError("synthetic write failure")

        monkeypatch.setattr(worker.os, "write", fail_write)
    else:
        original_close = os.close

        def fail_after_close(fd):
            try:
                opened = os.fstat(fd)
                current = os.stat(native(target))
            except (FileNotFoundError, OSError):
                return original_close(fd)
            if not calls and (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino):
                calls.append(True)
                original_close(fd)
                raise OSError("synthetic close failure after close")
            return original_close(fd)

        monkeypatch.setattr(worker.os, "close", fail_after_close)
    return calls


@pytest.mark.parametrize("kind", ["zip", "tar"])
def test_single_partial_failure_does_not_claim_clean_extraction(tmp_path, kind, monkeypatch):
    worker = load_worker()
    source = tmp_path / f"synthetic-partial.{kind}"
    raw = archive_bytes(kind, ((PRIMARY, PAYLOAD),))
    write(source, raw)
    members = tmp_path / "members"
    target = members / OFFERED_PRIMARY
    fault = inject_publication_fault(worker, monkeypatch, target, "partial_write")
    result = extract(worker, source, raw, members)
    assert len(fault) == 2
    assert read(target) == PAYLOAD[:3]
    assert declarations(result) == [] and result["loss_receipt"]["losses"]
    note = result["loss_receipt"]["params"]["projection_note"].lower()
    assert "no complete member was declared" in note
    assert "partial" in note and "remain" in note


def synthetic_two_member_streams():
    payloads = {PRIMARY: b"A" * 8, SECONDARY: b"B" * 8}
    infos = []
    for name, payload in payloads.items():
        info = zipfile.ZipInfo(name)
        info.file_size = len(payload)
        infos.append(info)

    class Container:
        def __init__(self):
            self.opened = []

        def open(self, info):
            self.opened.append(info.filename)
            return io.BytesIO(payloads[info.filename])

    return infos, Container(), payloads


@pytest.mark.parametrize("mode", ["partial_write", "close_after_write"])
@pytest.mark.parametrize("limit", ["bytes", "attempts"])
def test_failed_write_reserves_capacity_before_later_members(tmp_path, monkeypatch, mode, limit):
    """Exercise the common member loop with synthetic streams, not damaged archives."""
    worker = load_worker()
    members = tmp_path / "members"
    target = members / OFFERED_PRIMARY
    infos, container, payloads = synthetic_two_member_streams()
    monkeypatch.setattr(worker, "MEMBER_BYTES_CAP", 10 if limit == "bytes" else 20)
    monkeypatch.setattr(worker, "MEMBER_JOB_CAP", 1 if limit == "attempts" else 50)
    fault = inject_publication_fault(worker, monkeypatch, target, mode)
    offered, problems = worker._extract_members(infos, container, members)
    assert len(fault) == (2 if mode == "partial_write" else 1)
    assert read(target) == (payloads[PRIMARY][:3] if mode == "partial_write" else payloads[PRIMARY])
    assert offered == [] and problems
    assert container.opened == [PRIMARY]
    assert not Path(native(members / OFFERED_SECONDARY)).exists()
    assert sum(os.stat(native(p)).st_size for p in Path(native(members)).iterdir()) <= worker.MEMBER_BYTES_CAP
    if limit == "attempts":
        assert any("attempt" in problem.lower() for problem in problems)


@pytest.mark.parametrize("limit", ["bytes", "attempts"])
def test_conflict_also_reserves_capacity_before_later_members(tmp_path, monkeypatch, limit):
    worker = load_worker()
    members = tmp_path / "members"
    make_directory(members)
    target = members / OFFERED_PRIMARY
    write(target, b"conflict")
    before = snapshot(target)
    infos, container, _ = synthetic_two_member_streams()
    monkeypatch.setattr(worker, "MEMBER_BYTES_CAP", 10 if limit == "bytes" else 20)
    monkeypatch.setattr(worker, "MEMBER_JOB_CAP", 1 if limit == "attempts" else 50)
    offered, problems = worker._extract_members(infos, container, members)
    assert read(target) == b"conflict" and snapshot(target) == before
    assert offered == [] and problems
    assert container.opened == [PRIMARY]
    assert not Path(native(members / OFFERED_SECONDARY)).exists()
    if limit == "attempts":
        assert any("attempt" in problem.lower() for problem in problems)


@pytest.mark.parametrize("kind", ["zip", "tar"])
def test_flat_member_names_preserve_source_and_suffix_without_double_dot(tmp_path, kind):
    worker = load_worker()
    source = tmp_path / f"synthetic-double-dot.{kind}"
    entries = (("report..csv", b"first\n"), ("report...csv", b"second\n"))
    raw = archive_bytes(kind, entries)
    write(source, raw)
    members = tmp_path / "members"
    offered = declarations(extract(worker, source, raw, members))
    assert [item["name"] for item in offered] == [name for name, _ in entries]
    assert len({item["file"] for item in offered}) == 2
    for index, (item, (_, content)) in enumerate(zip(offered, entries), 1):
        assert item["file"].startswith(f"{index:04d}-")
        assert ".." not in item["file"] and item["file"].endswith(".csv")
        assert read(members / item["file"]) == content
        assert item["sha256"] == hashlib.sha256(content).hexdigest()
