"""Synthetic worker transfer controls; these do not execute or prove Core.

Each case writes only under pytest's temporary directory. The XLS source is a
temporary copy of the existing golden workbook, never the original fixture.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from email.message import EmailMessage
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKERS = ROOT / "services" / "python-workers" / "document"
GOLDEN_XLS = ROOT / "tests" / "fixtures" / "golden" / "golden-xls-anchor.xls"
GOLDEN_XLS_SHA256 = "3225b8bb590f799dc0a16a92118a1f80aec8cde53e0b4c71bc200f451aa72353"
SENTINEL = b"SYNTHETIC_SENTINEL_MUST_NOT_BE_REPLACED\n"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=("mail", "xls"))
def source(request, tmp_path):
    if request.param == "mail":
        message = EmailMessage()
        message["From"] = "sender@example.invalid"
        message["To"] = "reader@example.invalid"
        message["Subject"] = "Synthetic attachment"
        message.set_content("Synthetic body.\n")
        message.add_attachment(b"synthetic attachment bytes\n", maintype="application",
                               subtype="octet-stream", filename="note.txt")
        path = tmp_path / "synthetic.eml"
        path.write_bytes(message.as_bytes())
        worker = _load("member_transfer_mail", WORKERS / "worker_text.py")
        return "mail", worker, path, "0001-note.txt"

    pytest.importorskip("xlrd", reason="the real XLS worker requires the optional xlrd engine")
    raw = GOLDEN_XLS.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_XLS_SHA256
    path = tmp_path / "synthetic-copy.xls"
    path.write_bytes(raw)
    worker = _load("member_transfer_office", WORKERS / "worker_office.py")
    return "xls", worker, path, "sheet-01-Evidence.csv"


def _extract(source, member_dir):
    kind, worker, path, _ = source
    if kind == "mail":
        return worker.extract(str(path), "message/rfc822", member_dir=str(member_dir))
    return worker.extract(str(path), member_dir=str(member_dir))


def _offered(result):
    return result["loss_receipt"]["params"]["structure"]["extractable_members"]


def _clean_member(source, tmp_path):
    """Show the same input works in a fresh area before testing a collision."""
    baseline = tmp_path / "baseline"
    result = _extract(source, baseline)
    expected_name = source[3]
    matching = [item for item in _offered(result) if item["file"] == expected_name]
    assert len(matching) == 1
    raw = (baseline / expected_name).read_bytes()
    assert raw != SENTINEL
    assert matching[0]["bytes"] == len(raw) and matching[0]["sha256"] == hashlib.sha256(raw).hexdigest()
    return raw


def _extract_or_reject(source, member_dir):
    # A safe implementation may reject the route or report a rejected member;
    # either way it must preserve the pre-existing destination and not offer
    # that member as successfully written.
    try:
        return _extract(source, member_dir)
    except OSError:
        return None


def _assert_not_offered(result, filename):
    if result is not None:
        assert all(item["file"] != filename for item in _offered(result))


def test_different_existing_member_is_not_overwritten_or_offered(source, tmp_path):
    _clean_member(source, tmp_path)
    members = tmp_path / "members"
    members.mkdir()
    target = members / source[3]
    target.write_bytes(SENTINEL)
    before = target.stat()

    result = _extract_or_reject(source, members)

    assert target.read_bytes() == SENTINEL
    assert target.stat().st_ino == before.st_ino
    _assert_not_offered(result, target.name)


def test_hardlinked_member_cannot_overwrite_its_synthetic_other_name(source, tmp_path):
    _clean_member(source, tmp_path)
    members = tmp_path / "members"
    members.mkdir()
    sentinel = tmp_path / "synthetic-hardlink-sentinel"
    sentinel.write_bytes(SENTINEL)
    target = members / source[3]
    try:
        os.link(sentinel, target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"same-volume hardlinks unavailable: {type(exc).__name__}")
    assert target.stat().st_nlink >= 2 and os.path.samefile(target, sentinel)

    result = _extract_or_reject(source, members)

    assert sentinel.read_bytes() == SENTINEL
    assert target.read_bytes() == SENTINEL and os.path.samefile(target, sentinel)
    _assert_not_offered(result, target.name)


def test_identical_existing_member_is_reused_without_rewrite(source, tmp_path):
    payload = _clean_member(source, tmp_path)
    members = tmp_path / "members"
    members.mkdir()
    target = members / source[3]
    target.write_bytes(payload)
    # Fix an old timestamp so a truncation/rewrite is observable even on a
    # filesystem with coarse modification-time resolution.
    old_ns = 946_684_800 * 1_000_000_000
    try:
        os.utime(target, ns=(old_ns, old_ns))
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"synthetic file timestamp cannot be set: {type(exc).__name__}")
    before = target.stat()

    result = _extract(source, members)

    after = target.stat()
    assert target.read_bytes() == payload
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    matching = [item for item in _offered(result) if item["file"] == target.name]
    assert len(matching) == 1 and matching[0]["sha256"] == hashlib.sha256(payload).hexdigest()


def test_mail_member_filename_satisfies_current_core_plain_name_rule(tmp_path):
    # This checks the worker's name against the current static Core rule in
    # container.rs, which rejects any '..', '/' or '\\' in member.file. It does
    # not execute the Rust Core or claim actual member import.
    message = EmailMessage()
    message.set_content("Synthetic body.\n")
    message.add_attachment(b"synthetic payload\n", maintype="text", subtype="plain", filename="a..txt")
    path = tmp_path / "synthetic.eml"
    path.write_bytes(message.as_bytes())
    worker = _load("member_transfer_dotdot", WORKERS / "worker_text.py")

    result = worker.extract(str(path), "message/rfc822", member_dir=str(tmp_path / "members"))

    offered = _offered(result)
    assert len(offered) == 1 and offered[0]["name"] == "a..txt"
    filename = offered[0]["file"]
    assert ".." not in filename and "/" not in filename and "\\" not in filename


@pytest.mark.parametrize("title", ["a..b", "ends.", "...", "中文..页"])
def test_xls_flat_name_removes_consecutive_dots_but_keeps_csv_suffix(title):
    worker = _load("member_transfer_xls_names", WORKERS / "worker_office.py")
    name = worker._safe_csv_name(1, title)
    assert ".." not in name and "/" not in name and "\\" not in name
    assert name.startswith("sheet-01-") and name.endswith(".csv")


@pytest.mark.parametrize("title", ["a..txt", "a...txt", "中文..md"])
def test_mail_flat_name_removes_consecutive_dots_and_keeps_extension(title):
    light = _load("member_transfer_mail_names", WORKERS / "worker_light_formats.py")
    name = light._safe_attachment_name(1, title)
    assert ".." not in name and "/" not in name and "\\" not in name
    assert name.startswith("0001-") and name.endswith(Path(title).suffix)


def _native(path):
    text = str(path)
    if sys.platform == "win32" and Path(text).is_absolute() and not text.startswith("\\\\?\\"):
        return "\\\\?\\" + text
    return text


def test_shared_helper_uses_the_callers_native_path_for_create_and_retry(tmp_path):
    helper = _load("member_transfer_native", WORKERS / "member_transfer.py")
    calls = []

    def native(path):
        calls.append(str(path))
        return _native(path)

    members = tmp_path / "nested" / "members"
    target = members / "target.txt"
    helper.prepare_directory(members, native)
    helper.offer_member(target, b"synthetic bytes", native)
    before = target.stat()
    helper.offer_member(target, b"synthetic bytes", native)
    after = target.stat()
    assert target.read_bytes() == b"synthetic bytes"
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert str(members) in calls and str(target) in calls


@pytest.mark.parametrize("same_bytes", [False, True])
def test_shared_helper_rejects_a_hardlink_even_if_bytes_match(tmp_path, same_bytes):
    helper = _load("member_transfer_hardlink", WORKERS / "member_transfer.py")
    members = tmp_path / "members"
    members.mkdir()
    victim = tmp_path / "synthetic-hardlink-victim"
    payload = b"same synthetic bytes" if same_bytes else SENTINEL
    victim.write_bytes(payload)
    target = members / "target.txt"
    try:
        os.link(_native(victim), _native(target))
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"same-volume hardlinks unavailable: {type(exc).__name__}")
    assert target.stat().st_nlink >= 2
    before = victim.stat()
    with pytest.raises(OSError):
        helper.offer_member(target, b"same synthetic bytes", _native)
    assert victim.read_bytes() == payload and os.path.samefile(_native(target), _native(victim))
    assert victim.stat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("position", ["target", "directory"])
def test_actual_symlink_is_refused_where_creation_is_available(tmp_path, position):
    helper = _load("member_transfer_symlink", WORKERS / "member_transfer.py")
    victim = tmp_path / "synthetic-victim"
    members = tmp_path / "members"
    if position == "target":
        victim.write_bytes(SENTINEL)
        members.mkdir()
        link = members / "target.txt"
    else:
        victim.mkdir()
        link = members
    try:
        os.symlink(_native(victim), _native(link), target_is_directory=position == "directory")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"synthetic symlink unavailable: {type(exc).__name__}")
    with pytest.raises(OSError):
        if position == "target":
            helper.offer_member(link, b"new synthetic bytes", _native)
        else:
            helper.prepare_directory(link, _native)
    assert link.is_symlink()
    if position == "target":
        assert victim.read_bytes() == SENTINEL
    else:
        assert list(victim.iterdir()) == []


@pytest.mark.parametrize("position", ["target", "directory"])
def test_observed_reparse_attribute_blocks_both_real_worker_paths(source, tmp_path, monkeypatch, position):
    _clean_member(source, tmp_path)
    members = tmp_path / "members"
    members.mkdir()
    target = members / source[3]
    if position == "target":
        target.write_bytes(SENTINEL)
    marked = target if position == "target" else members
    wanted = os.path.normcase(os.path.normpath(_native(marked)))
    original_lstat = os.lstat
    observed = []

    class WithReparse:
        def __init__(self, value):
            self.value = value

        @property
        def st_file_attributes(self):
            return getattr(self.value, "st_file_attributes", 0) | 0x400

        def __getattr__(self, name):
            return getattr(self.value, name)

    def synthetic_lstat(path, *args, **kwargs):
        value = original_lstat(path, *args, **kwargs)
        if os.path.normcase(os.path.normpath(str(path))) == wanted:
            observed.append(True)
            return WithReparse(value)
        return value

    with monkeypatch.context() as patch:
        patch.setattr(os, "lstat", synthetic_lstat)
        result = _extract_or_reject(source, members)
    assert observed, "the intended simulated Windows attribute was not observed"
    if position == "target":
        assert target.read_bytes() == SENTINEL
    else:
        assert list(members.iterdir()) == []
    _assert_not_offered(result, target.name)


@pytest.mark.parametrize("failure", ["partial_write", "close_after_write"])
def test_shared_helper_preserves_failed_target_without_claiming_success(tmp_path, monkeypatch, failure):
    helper = _load("member_transfer_partial", WORKERS / "member_transfer.py")
    members = tmp_path / "members"
    helper.prepare_directory(members, _native)
    target = members / "target.txt"
    original_write, original_close = os.write, os.close
    calls = []

    def is_target(fd):
        try:
            opened, current = os.fstat(fd), os.stat(_native(target))
            return (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino)
        except OSError:
            return False

    def fail_write(fd, data):
        if is_target(fd):
            if not calls:
                calls.append("short")
                return original_write(fd, data[:2])
            calls.append("error")
            raise OSError("synthetic partial write")
        return original_write(fd, data)

    def fail_close(fd):
        selected = is_target(fd)
        original_close(fd)
        if selected:
            calls.append("closed")
            raise OSError("synthetic failure after close")

    with monkeypatch.context() as patch:
        if failure == "partial_write":
            patch.setattr(os, "write", fail_write)
        else:
            patch.setattr(os, "close", fail_close)
        with pytest.raises(OSError):
            helper.offer_member(target, b"payload", _native)
    assert calls
    # The helper owns neither cleanup nor an assertion that failed output is
    # complete. A close failure can leave the entire file even though it failed.
    assert target.read_bytes() == (b"pa" if failure == "partial_write" else b"payload")


@pytest.mark.parametrize("limit", ["attempts", "bytes"])
def test_mail_failed_partial_write_reserves_budget_and_is_not_declared(tmp_path, monkeypatch, limit):
    light = _load("member_transfer_budget_mail", WORKERS / "worker_light_formats.py")
    helper = _load("member_transfer_budget_helper", WORKERS / "member_transfer.py")
    real_offer = helper.offer_member
    calls = []

    def fail_first(target, payload, native_path):
        calls.append(target.name)
        if len(calls) == 1:
            Path(native_path(target)).write_bytes(payload[:1])
            raise OSError("synthetic partial failure")
        return real_offer(target, payload, native_path)

    monkeypatch.setattr(helper, "offer_member", fail_first)
    monkeypatch.setattr(light, "_load_member_transfer", lambda: helper)
    monkeypatch.setattr(light, "ATTACHMENT_JOB_CAP", 2 if limit == "attempts" else 50)
    monkeypatch.setattr(light, "ATTACHMENT_BYTES_CAP", 100 if limit == "attempts" else 7)
    message = EmailMessage()
    message.set_content("synthetic body\n")
    for number in range(1, 4):
        message.add_attachment(b"abcd", maintype="application", subtype="octet-stream", filename=f"a{number}.txt")
    members = tmp_path / "members"

    offered, problems = light.mail_attachments(message.as_bytes(), members)

    assert (members / "0001-a1.txt").read_bytes() == b"a"
    assert all(item["file"] != "0001-a1.txt" for item in offered)
    assert any("partial" in item and "remain" in item for item in problems)
    if limit == "attempts":
        assert calls == ["0001-a1.txt", "0002-a2.txt"]
        assert [item["file"] for item in offered] == ["0002-a2.txt"]
        assert not (members / "0003-a3.txt").exists()
        assert any("attempt limit" in item for item in problems)
    else:
        assert calls == ["0001-a1.txt"] and offered == []
        assert not (members / "0002-a2.txt").exists()
        assert any("byte budget" in item for item in problems)


def _watch_xls_release(monkeypatch):
    xlrd = pytest.importorskip("xlrd", reason="the real XLS worker requires the optional xlrd engine")
    original = xlrd.open_workbook
    observed = []

    class WatchedBook:
        def __init__(self, book):
            self.book = book
            self.released = False

        def __getattr__(self, name):
            return getattr(self.book, name)

        def release_resources(self):
            self.released = True
            return self.book.release_resources()

    def watched_open(*args, **kwargs):
        book = WatchedBook(original(*args, **kwargs))
        observed.append(book)
        return book

    monkeypatch.setattr(xlrd, "open_workbook", watched_open)
    return observed


def test_xls_partial_transfer_fails_and_releases_workbook(tmp_path, monkeypatch):
    worker = _load("member_transfer_partial_xls", WORKERS / "worker_office.py")
    observed = _watch_xls_release(monkeypatch)
    raw = GOLDEN_XLS.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_XLS_SHA256
    source = tmp_path / "copy.xls"
    source.write_bytes(raw)
    members = tmp_path / "members"
    target = members / "sheet-01-Evidence.csv"
    original_write = os.write
    calls = []

    def fail_write(fd, data):
        try:
            opened, current = os.fstat(fd), os.stat(_native(target))
            selected = (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino)
        except OSError:
            selected = False
        if selected:
            if not calls:
                calls.append("short")
                return original_write(fd, data[:2])
            calls.append("error")
            raise OSError("synthetic partial write")
        return original_write(fd, data)

    with monkeypatch.context() as patch:
        patch.setattr(os, "write", fail_write)
        with pytest.raises(OSError, match="partial transfer file may remain"):
            worker.extract(str(source), member_dir=str(members))
    assert calls == ["short", "error"] and target.stat().st_size == 2
    assert len(observed) == 1 and observed[0].released
    assert source.read_bytes() == raw


def _portable_tree(tmp_path):
    # A minimal local copy of the same relative layout, not an installed or
    # released program. The missing-helper phase is deliberate.
    root = tmp_path / "portable"
    document = root / "workers" / "document"
    transport = root / "workers" / "transport"
    document.mkdir(parents=True)
    transport.mkdir(parents=True)
    for name in ("worker_text.py", "worker_light_formats.py", "worker_office.py"):
        shutil.copyfile(WORKERS / name, document / name)
    transport_source = ROOT / "services" / "python-workers" / "transport" / "text_ndjson.py"
    shutil.copyfile(transport_source, transport / "text_ndjson.py")
    return root, document, transport / "text_ndjson.py"


def _transport_extract(transport, raw, media, staging, artifacts):
    digest = hashlib.sha256(raw).hexdigest()
    (staging / "input").mkdir(parents=True, exist_ok=True)
    (staging / "input" / digest).write_bytes(raw)
    request = {"schema": "archeaxis.worker-request/v1", "type": "job_request", "request_id": "synthetic_r",
               "job_id": "synthetic_j", "attempt": 1, "protocol_minor": 0, "capability": "text.extract",
               "capability_version": "1", "deadline_ms": 60_000,
               "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media}],
               "parameters": {}}
    outputs, _, _ = transport.execute(request, staging, artifact_root=artifacts)
    loss = next(item for item in outputs if item["kind"] == "loss_report")
    return json.loads((staging / "output" / loss["uri"].rsplit("/", 1)[-1]).read_bytes())


def test_portable_mail_transport_loads_sibling_only_for_real_members(tmp_path):
    _, document, transport_path = _portable_tree(tmp_path)
    transport = _load("portable_member_transport", transport_path)
    staging = tmp_path / "staging"
    plain_root = tmp_path / "plain-artifacts"
    plain = _transport_extract(transport, b"synthetic plain text\n", "text/plain", staging, plain_root)
    assert plain["params"]["structure"]["extractable_members"] == []
    assert not plain_root.exists()

    no_attachment = EmailMessage()
    no_attachment.set_content("synthetic mail body\n")
    no_attachment_root = tmp_path / "no-attachment-artifacts"
    receipt = _transport_extract(transport, no_attachment.as_bytes(), "message/rfc822", staging, no_attachment_root)
    assert receipt["params"]["structure"]["extractable_members"] == []
    assert not no_attachment_root.exists()

    message = EmailMessage()
    message.set_content("synthetic mail body\n")
    message.add_attachment(b"synthetic attachment\n", maintype="text", subtype="plain", filename="note.txt")
    raw = message.as_bytes()
    without_transfer = _transport_extract(transport, raw, "message/rfc822", staging, None)
    assert without_transfer["params"]["structure"]["extractable_members"] == []
    mail_root = tmp_path / "mail-artifacts"
    with pytest.raises(RuntimeError, match="member transfer helper unavailable"):
        _transport_extract(transport, raw, "message/rfc822", staging, mail_root)
    assert not mail_root.exists()

    shutil.copyfile(WORKERS / "member_transfer.py", document / "member_transfer.py")
    receipt = _transport_extract(transport, raw, "message/rfc822", staging, mail_root)
    offered = receipt["params"]["structure"]["extractable_members"]
    assert len(offered) == 1 and offered[0]["name"] == "note.txt"
    assert (mail_root / "members" / offered[0]["file"]).read_bytes() == b"synthetic attachment\n"


def test_portable_xls_without_transfer_works_and_missing_helper_releases_book(tmp_path, monkeypatch):
    _, document, _ = _portable_tree(tmp_path)
    pytest.importorskip("xlrd", reason="the real XLS worker requires the optional xlrd engine")
    worker = _load("portable_xls_worker", document / "worker_office.py")
    raw = GOLDEN_XLS.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_XLS_SHA256
    source = tmp_path / "portable-copy.xls"
    source.write_bytes(raw)
    plain = worker.extract(str(source))
    assert plain["text"] and _offered(plain) == []

    observed = _watch_xls_release(monkeypatch)
    members = tmp_path / "members"
    with pytest.raises(RuntimeError, match="member transfer helper unavailable"):
        worker.extract(str(source), member_dir=str(members))
    assert len(observed) == 1 and observed[0].released and not members.exists()

    shutil.copyfile(WORKERS / "member_transfer.py", document / "member_transfer.py")
    result = worker.extract(str(source), member_dir=str(members))
    assert len(observed) == 2 and observed[1].released
    assert [item["name"] for item in _offered(result)] == ["Evidence.csv", "Numbers.csv"]
