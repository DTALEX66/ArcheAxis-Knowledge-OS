"""Actual openpyxl and pinned upstream XLSX branch, using synthetic bytes only."""

import base64
import copy
import datetime
import hashlib
import importlib.util
import io
import json
import os
import re
import socket
import struct
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

import pytest
from defusedxml import ElementTree as safe_xml
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.spreadsheet_drawing import SpreadsheetDrawing
from openpyxl.worksheet._writer import WorksheetWriter
from openpyxl.writer.excel import ExcelWriter

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "services" / "learning-providers" / "deeptutor" / "practice_import.py"
SPEC = importlib.util.spec_from_file_location("deeptutor_practice_xlsx_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


@pytest.fixture
def isolated_adapter():
    """Each cleanup-unknown experiment owns a separate module-instance slot."""
    name = "deeptutor_practice_xlsx_isolated_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


class _ObservedReadPipe:
    """Record only synthetic byte counts while preserving real pipe behavior."""
    def __init__(self, raw, counts):
        self.raw, self.counts = raw, counts

    def read(self, size):
        data = self.raw.read(size)
        self.counts.append(len(data))
        return data

    def close(self):
        self.raw.close()


class _MemoryExcelWriter(ExcelWriter):
    """Use the real writer while keeping worksheet XML out of temporary files."""
    def write_worksheet(self, sheet):
        sheet._drawing = SpreadsheetDrawing()
        sheet._drawing.charts = sheet._charts
        sheet._drawing.images = sheet._images
        out = io.BytesIO()
        writer = WorksheetWriter(sheet, out=out)
        writer.write()
        sheet._rels = writer._rels
        self._archive.writestr(sheet.path[1:], out.getvalue())
        self.manifest.append(sheet)


def workbook_bytes(change=None):
    book = Workbook()
    sheet = book.active
    sheet.append(["question", "type", "A", "B", "answer", "user_answer", "extra"])
    sheet.append(["Which 甲?", "single_choice", "one", "two", "B", "A", "SYNTHETIC_PRIVATE"])
    sheet.append([None] * 7)
    sheet.append(["Why 中文?", "short_answer", None, None, "SYNTHETIC_KEY", None, None])
    if change:
        change(book, sheet)
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        _MemoryExcelWriter(book, archive).save()
    book.close()
    return target.getvalue()


def rewrite_part(raw, name, transform):
    target = io.BytesIO()
    seen = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(target, "w") as result:
        for item in source.infolist():
            content = source.read(item)
            if item.filename == name:
                content = transform(content)
                seen += 1
            result.writestr(item, content)
    assert seen == 1
    return target.getvalue()


def sheet_part(raw, transform):
    return rewrite_part(raw, "xl/worksheets/sheet1.xml", transform)


def add_xml_attribute(data, element_start, name, value):
    assert data.count(element_start) == 1
    return data.replace(element_start, element_start + b' ' + name + b'="' + value + b'" ', 1)


def test_real_upstream_xlsx_branch_and_private_loss_trace(monkeypatch):
    raw = workbook_bytes()
    loader, safe_xml = adapter._xlsx_engine()
    calls = []

    def audited_loader(*args, **kwargs):
        calls.append(kwargs.copy())
        return loader(*args, **kwargs)

    monkeypatch.setattr(adapter, "_xlsx_engine", lambda: (audited_loader, safe_xml))
    # Test-only in-process instrumentation uses synthetic data. Public XLSX
    # previews use a separately spawned worker to contain library diagnostics.
    batch = adapter._private_preview_in_process(raw, "xlsx")
    # Preflight calls the real library, then the pinned upstream function does
    # so again in its original XLSX branch; this is not a replacement parser.
    assert calls == [{"read_only": True, "data_only": False, "keep_links": False}] * 2
    assert batch.source == raw and batch.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert [item["row"] for item in batch.rows] == [2, 4]
    assert batch.skipped_rows == [3]
    assert batch.rows[0]["candidate"]["correct_answer"] == "B"
    assert batch.rows[0]["unmapped"] == [{"key": "extra", "value": "SYNTHETIC_PRIVATE",
                                           "reason": "not_selected_by_upstream"}]
    assert batch.rows[1]["candidate"]["correct_answer"] == "SYNTHETIC_KEY"
    visible = adapter.preview_bytes(raw, "xlsx")
    assert visible["source_row_scope"] == "xlsx_worksheet_row_one_based_including_header"
    assert visible["workbook_scope"] == "single_visible_active_worksheet_only"
    assert visible["workbook_non_cell_content"] == "not_preserved_in_preview"
    assert visible["rows"][0]["question"]["options"] == {"A": "one", "B": "two"}
    assert visible["rows"][1]["question"]["question"] == "Why 中文?"
    encoded = json.dumps(visible, ensure_ascii=False)
    assert all(secret not in encoded for secret in ("SYNTHETIC_KEY", "SYNTHETIC_PRIVATE", batch.source_sha256))
    assert "source_byte_length" not in visible and "source_sha256" not in visible


def test_option_override_is_private_and_not_claimed_lossless():
    def change(_book, sheet):
        sheet["H1"] = "options"
        sheet["H2"] = '{"A":"SYNTHETIC_OLD_OPTION","B":"two"}'
    raw = workbook_bytes(change)
    private = adapter._private_preview(raw, "xlsx")
    assert private.rows[0]["candidate"]["options"]["A"] == "one"
    assert private.rows[0]["option_changes"] == [{"key": "A", "old": "SYNTHETIC_OLD_OPTION", "new": "one",
                                                 "reason": "option_column_override"}]
    visible = adapter.preview_bytes(raw, "xlsx")
    assert visible["rows"][0]["known_option_changes_count"] == 1
    assert visible["rows"][0]["other_selected_values_compared"] is False
    assert "SYNTHETIC_OLD_OPTION" not in json.dumps(visible)


def test_xlsx_path_never_connects_network(monkeypatch):
    raw = workbook_bytes()

    def forbidden(*_args, **_kwargs):
        pytest.fail("unexpected network attempt")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert adapter._private_preview_in_process(raw, "xlsx").rows[0]["candidate"] is not None


def test_synthetic_workbook_writer_never_requests_a_temporary_file(monkeypatch):
    import openpyxl.worksheet._writer as writer_module

    def forbidden(*_args, **_kwargs):
        pytest.fail("unexpected worksheet temporary file")

    monkeypatch.setattr(writer_module, "create_temporary_file", forbidden)
    assert adapter.preview_bytes(workbook_bytes(), "xlsx")["rows"][0]["status"] == "CANDIDATE"


@pytest.mark.parametrize("change", [
    lambda book, sheet: book.create_sheet("extra"),
    lambda book, sheet: setattr(sheet.row_dimensions[2], "hidden", True),
    lambda book, sheet: setattr(sheet.column_dimensions["B"], "hidden", True),
    lambda book, sheet: sheet.merge_cells("A2:B2"),
    lambda book, sheet: setattr(sheet["A2"], "value", "=1+1"),
    lambda book, sheet: setattr(sheet["A2"], "value", datetime.datetime(2024, 1, 2)),
    lambda book, sheet: setattr(sheet["A2"], "value", datetime.time(12, 0)),
    lambda book, sheet: setattr(sheet["A2"], "value", datetime.timedelta(days=1)),
    lambda book, sheet: setattr(sheet["A2"], "value", "#DIV/0!"),
    lambda book, sheet: setattr(sheet["B1"], "value", " QUESTION "),
    lambda book, sheet: setattr(sheet["B1"], "value", None),
], ids=["extra_sheet", "hidden_row", "hidden_column", "merged", "formula", "date", "time",
        "duration", "excel_error", "duplicate_header", "blank_header"])
def test_unsupported_workbook_content_is_refused(change):
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(workbook_bytes(change), "xlsx")


def test_hidden_only_worksheet_is_refused_even_if_modified_after_save():
    raw = workbook_bytes()
    changed = rewrite_part(raw, "xl/workbook.xml", lambda part: part.replace(b'state="visible"', b'state="hidden"'))
    assert changed != raw
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(changed, "xlsx")


@pytest.mark.parametrize("value", [None, b"0", b"false"], ids=["absent", "zero", "false"])
def test_default_row_visibility_valid_values_through_isolated_child(value):
    raw = workbook_bytes()
    if value is not None:
        raw = sheet_part(raw, lambda data: add_xml_attribute(data, b"<sheetFormatPr", b"zeroHeight", value))
    result = adapter.preview_bytes(raw, "xlsx")
    assert [row["source_row"] for row in result["rows"]] == [2, 4]


@pytest.mark.parametrize("value", [b"1", b"true", b"FALSE", b"f", b"", b" true "],
                         ids=["one", "true", "uppercase_false", "shorthand", "empty", "whitespace"])
def test_default_row_visibility_hidden_and_invalid_values_through_isolated_child(value):
    raw = sheet_part(workbook_bytes(), lambda data: add_xml_attribute(data, b"<sheetFormatPr", b"zeroHeight", value))
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(raw, "xlsx")


def test_openpyxl_hidden_by_default_and_duplicate_defaults_are_rejected():
    raw = workbook_bytes(lambda _book, sheet: setattr(sheet.sheet_format, "zeroHeight", True))
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(raw, "xlsx")

    def duplicate(data):
        match = re.search(rb"<sheetFormatPr\b[^>]*/>", data)
        assert match is not None
        return data[:match.end()] + match.group(0) + data[match.end():]

    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(sheet_part(workbook_bytes(), duplicate), "xlsx")


@pytest.mark.parametrize("kind", ["row", "column"])
@pytest.mark.parametrize("value", [None, b"0", b"false"], ids=["absent", "zero", "false"])
def test_row_and_column_visibility_valid_values_through_isolated_child(kind, value):
    if kind == "row":
        raw, marker = workbook_bytes(), b'<row r="2"'
    else:
        raw = workbook_bytes(lambda _book, sheet: setattr(sheet.column_dimensions["B"], "width", 12))
        marker = b"<col "
    if value is not None:
        raw = sheet_part(raw, lambda data: add_xml_attribute(data, marker, b"hidden", value))
    # Guard the fixture independently: a malformed attribute must never be
    # mistaken for an implementation failure or a visibility rejection.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        safe_xml.fromstring(archive.read("xl/worksheets/sheet1.xml"),
                            forbid_dtd=True, forbid_entities=True, forbid_external=True)
    book = load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
    try:
        assert [cells[0].value for cells in book.active.iter_rows()] == ["question", "Which 甲?", None, "Why 中文?"]
    finally:
        book.close()
    assert adapter.preview_bytes(raw, "xlsx")["rows"][0]["status"] == "CANDIDATE"


@pytest.mark.parametrize("kind", ["row", "column"])
@pytest.mark.parametrize("value", [b"1", b"true", b"FALSE", b"f", b"", b" false "],
                         ids=["one", "true", "uppercase_false", "shorthand", "empty", "whitespace"])
def test_row_and_column_visibility_hidden_and_invalid_through_isolated_child(kind, value):
    if kind == "row":
        raw, marker = workbook_bytes(), b'<row r="2"'
    else:
        raw = workbook_bytes(lambda _book, sheet: setattr(sheet.column_dimensions["B"], "width", 12))
        marker = b"<col "
    raw = sheet_part(raw, lambda data: add_xml_attribute(data, marker, b"hidden", value))
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(raw, "xlsx")


def workbook_dimension(kind, value):
    def replace_attribute(data, element, attribute):
        pattern = rb'(<'+ element + rb'\b[^>]*?\b' + attribute + rb'=")[^"]*(")'
        changed, count = re.subn(pattern, lambda match: match.group(1) + value + match.group(2), data, count=1)
        assert count == 1
        return changed

    if kind == "row":
        def change(data):
            data = add_xml_attribute(data, b'<row r="2"', b"ht", value)
            return add_xml_attribute(data, b'<row r="2"', b"customHeight", b"1")
        return sheet_part(workbook_bytes(), change)
    if kind == "column":
        raw = workbook_bytes(lambda _book, sheet: setattr(sheet.column_dimensions["B"], "width", 12))
        return sheet_part(raw, lambda data: replace_attribute(data, b"col", b"width"))
    if kind == "default_row":
        return sheet_part(workbook_bytes(), lambda data: replace_attribute(data, b"sheetFormatPr", b"defaultRowHeight"))
    if kind == "default_column":
        return sheet_part(workbook_bytes(), lambda data: add_xml_attribute(data, b"<sheetFormatPr", b"defaultColWidth", value))
    return sheet_part(workbook_bytes(), lambda data: replace_attribute(data, b"sheetFormatPr", b"baseColWidth"))


@pytest.mark.parametrize("kind", ["row", "column", "default_row", "default_column", "base_column"])
@pytest.mark.parametrize("value", [b"0", b"-1", b"NaN", b"1_0", b"1e9999", b""],
                         ids=["zero", "negative", "not_finite", "underscore", "overflow", "empty"])
def test_zero_and_invalid_row_height_column_width_fail_closed(kind, value):
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(workbook_dimension(kind, value), "xlsx")


@pytest.mark.parametrize("kind", ["row", "column", "default_row", "default_column", "base_column"])
def test_positive_row_height_column_width_remains_supported(kind):
    result = adapter.preview_bytes(workbook_dimension(kind, b"12"), "xlsx")
    assert result["rows"][0]["status"] == "CANDIDATE"


@pytest.mark.parametrize("dimension", [b"A1:A1", b"A1:G2", b"A1:H4", b"A2:G4"])
def test_spoofed_or_mismatched_dimensions_fail_closed(dimension):
    def replace(data):
        changed, count = re.subn(rb'<dimension ref="[^"]+"', b'<dimension ref="' + dimension + b'"', data, count=1)
        assert count == 1
        return changed
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(sheet_part(workbook_bytes(), replace), "xlsx")


def test_duplicate_cell_coordinate_and_nonfinite_value_fail_closed():
    def duplicate(data):
        match = re.search(rb'<c r="A2"[^>]*>.*?</c>', data)
        assert match is not None
        return data[:match.end()] + match.group(0) + data[match.end():]

    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(sheet_part(workbook_bytes(), duplicate), "xlsx")
    numeric = workbook_bytes(lambda _book, sheet: setattr(sheet["G2"], "value", 42))
    changed = sheet_part(numeric, lambda part: part.replace(b"<v>42</v>", b"<v>1e9999</v>"))
    assert changed != numeric
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(changed, "xlsx")


def test_duplicate_zip_names_and_declared_expansion_are_rejected():
    raw = workbook_bytes()
    target = io.BytesIO(raw)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(target, "a") as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"<irrelevant/>")
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(target.getvalue(), "xlsx")
    # Change central directory size only: no large data or output is created.
    corrupted = bytearray(raw)
    central = corrupted.index(b"PK\x01\x02")
    struct.pack_into("<I", corrupted, central + 24, adapter.MAX_XLSX_EXPANDED + 1)
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(bytes(corrupted), "xlsx")


def test_member_count_and_xml_node_limits_reject_before_loader(monkeypatch):
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for number in range(adapter.MAX_XLSX_PARTS + 1):
            archive.writestr(f"{number}.xml", "<x/>")
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(target.getvalue(), "xlsx")
    monkeypatch.setattr(adapter, "MAX_XLSX_XML_NODES", 10)
    with pytest.raises(adapter.InvalidInput):
        adapter._private_preview_in_process(workbook_bytes(), "xlsx")


def test_dtd_external_relationship_and_binary_part_are_rejected():
    raw = workbook_bytes()
    changed = sheet_part(raw, lambda data: data.replace(b"<worksheet", b'<!DOCTYPE worksheet [<!ENTITY x "x">]><worksheet', 1))
    assert changed != raw
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(changed, "xlsx")
    changed = rewrite_part(raw, "_rels/.rels", lambda data: data.replace(b" Target=", b' TargetMode="External" Target=', 1))
    assert changed != raw
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(changed, "xlsx")
    target = io.BytesIO(raw)
    with zipfile.ZipFile(target, "a") as archive:
        archive.writestr("xl/media/image.png", b"synthetic")
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(target.getvalue(), "xlsx")


def test_duplicate_relationship_id_is_rejected():
    def duplicate(data):
        match = re.search(rb'<Relationship\b[^>]*/>', data)
        assert match is not None
        return data[:match.end()] + match.group(0) + data[match.end():]
    raw = rewrite_part(workbook_bytes(), "_rels/.rels", duplicate)
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(raw, "xlsx")


def test_xlsx_ast_rejects_changed_import_and_other_imports(monkeypatch):
    loader, _ = adapter._xlsx_engine()
    source = adapter._read_original()
    before = b"from openpyxl import load_workbook"
    assert source.count(before) == 1
    monkeypatch.setattr(adapter, "_read_original", lambda: source.replace(before, before + b", extra", 1))
    with pytest.raises(adapter.UpstreamUnavailable):
        adapter._selected_functions(xlsx_loader=loader)
    monkeypatch.setattr(adapter, "_read_original", lambda: source.replace(before, before + b"\n        import os", 1))
    with pytest.raises(adapter.UpstreamUnavailable):
        adapter._selected_functions(xlsx_loader=loader)


def child_environment(tmp_path):
    home, temp = tmp_path / "home", tmp_path / "temp"
    home.mkdir()
    temp.mkdir()
    env = {"HOME": str(home), "USERPROFILE": str(home), "TEMP": str(temp), "TMP": str(temp),
           "APPDATA": str(home), "LOCALAPPDATA": str(home), "XDG_CONFIG_HOME": str(home),
           "XDG_CACHE_HOME": str(home), "XDG_DATA_HOME": str(home)}
    if sys.platform == "win32":
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


def test_real_child_protocol_and_disabled_xml_protection(tmp_path):
    raw = workbook_bytes()
    envelope = {"schema": adapter.SCHEMA, "request_id": "synthetic_xlsx", "format": "xlsx",
                "data_base64": base64.b64encode(raw).decode("ascii")}
    wire = json.dumps(envelope).encode("utf-8") + b"\n"
    env = child_environment(tmp_path)
    command = [sys.executable, "-I", "-B", str(SCRIPT)]
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    run = subprocess.run(command, input=wire, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, timeout=30, check=False)
    assert run.returncode == 0 and not run.stderr
    result = json.loads(run.stdout)
    assert result["status"] == "PREVIEW" and result["request_id"] == "synthetic_xlsx"
    assert b"SYNTHETIC_KEY" not in run.stdout and b"SYNTHETIC_PRIVATE" not in run.stdout
    env["OPENPYXL_DEFUSEDXML"] = "False"
    disabled = subprocess.run(command, input=wire, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=30, check=False)
    assert disabled.returncode == 1 and not disabled.stderr
    assert json.loads(disabled.stdout)["status"] == "UNAVAILABLE"
    assert b"SYNTHETIC_KEY" not in disabled.stdout and b"SYNTHETIC_PRIVATE" not in disabled.stdout
    env.pop("OPENPYXL_DEFUSEDXML")
    invalid = {**envelope, "data_base64": base64.b64encode(b"SYNTHETIC_KEY-not-a-workbook").decode("ascii")}
    refused = subprocess.run(command, input=json.dumps(invalid).encode("utf-8") + b"\n", env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    assert refused.returncode == 2 and not refused.stderr
    assert json.loads(refused.stdout)["status"] == "INVALID_REQUEST"
    assert b"SYNTHETIC_KEY" not in refused.stdout
    assert sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")) == before


def test_private_library_warning_is_not_returned_or_written_to_parent_stderr(capfd, monkeypatch, isolated_adapter):
    adapter = isolated_adapter
    def change(_book, sheet):
        sheet["G2"] = datetime.datetime(2024, 1, 2)
    raw = workbook_bytes(change)

    def overflow(data):
        changed, count = re.subn(rb'(<c r="G2"[^>]*><v>)[^<]+(</v></c>)',
                                 rb'\g<1>999999999\g<2>', data, count=1)
        assert count == 1
        return changed
    raw = sheet_part(raw, overflow)
    # Establish independently that this synthetic workbook really triggers a
    # library warning; a generic unavailable result alone is not evidence.
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with pytest.raises(adapter.InvalidInput):
            adapter._private_preview_in_process(raw, "xlsx")
    assert observed
    real_popen = adapter.subprocess.Popen
    children = []

    def capture_child(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(adapter.subprocess, "Popen", capture_child)
    with pytest.raises(adapter.UpstreamUnavailable) as outcome:
        adapter.preview_bytes(raw, "xlsx")
    assert len(children) == 1 and children[0].poll() is not None
    assert "999999999" not in str(outcome.value)
    captured = capfd.readouterr()
    assert captured.out == captured.err == ""


def test_worker_diagnostics_and_oversized_output_are_discarded(monkeypatch, capfd, isolated_adapter):
    adapter = isolated_adapter
    raw = workbook_bytes()
    real_popen = adapter.subprocess.Popen
    children, stdout_sizes = [], []

    def run_stub(_command, **kwargs):
        program = ("import sys; sys.stdin.buffer.readline(); "
                   "sys.stderr.write('SYNTHETIC_SECRET'); sys.stdout.write('x' * 4096)")
        child = real_popen([sys.executable, "-I", "-B", "-c", program], **kwargs)
        child.stdout = _ObservedReadPipe(child.stdout, stdout_sizes)
        children.append(child)
        return child

    monkeypatch.setattr(adapter.subprocess, "Popen", run_stub)
    monkeypatch.setattr(adapter, "MAX_XLSX_CHILD_OUTPUT", 1024)
    with pytest.raises(adapter.UpstreamUnavailable) as outcome:
        adapter.preview_bytes(raw, "xlsx")
    assert len(children) == 1 and children[0].poll() is not None
    assert sum(stdout_sizes) > adapter.MAX_XLSX_CHILD_OUTPUT
    assert "SYNTHETIC_SECRET" not in str(outcome.value)
    captured = capfd.readouterr()
    assert captured.out == captured.err == ""


def test_timeout_fails_closed_without_automatic_replay(monkeypatch, isolated_adapter):
    adapter = isolated_adapter
    raw = workbook_bytes()
    real_popen = adapter.subprocess.Popen
    children = []

    def run_stub(_command, **kwargs):
        # The fixed synthetic child also has its own finite lifetime if the
        # launcher is terminated before its descendant can be confirmed.
        program = "import sys,threading; sys.stdin.buffer.readline(); threading.Event().wait(1)"
        child = real_popen([sys.executable, "-I", "-B", "-c", program], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(adapter.subprocess, "Popen", run_stub)
    monkeypatch.setattr(adapter, "XLSX_CHILD_TIMEOUT_SECONDS", 0.05)
    with pytest.raises(adapter.UpstreamUnavailable):
        adapter.preview_bytes(raw, "xlsx")
    assert len(children) == 1 and children[0].poll() is not None


def test_diagnostic_limit_fails_closed(monkeypatch, capfd, isolated_adapter):
    adapter = isolated_adapter
    raw = workbook_bytes()
    real_popen = adapter.subprocess.Popen
    children, diagnostic_sizes = [], []
    program = "import sys; sys.stdin.buffer.readline(); sys.stderr.write('SYNTHETIC_SECRET' * 16)"

    def run_stub(_command, **kwargs):
        child = real_popen([sys.executable, "-I", "-B", "-c", program], **kwargs)
        child.stderr = _ObservedReadPipe(child.stderr, diagnostic_sizes)
        children.append(child)
        return child

    monkeypatch.setattr(adapter.subprocess, "Popen", run_stub)
    monkeypatch.setattr(adapter, "MAX_XLSX_CHILD_DIAGNOSTIC", 32)
    with pytest.raises(adapter.UpstreamUnavailable) as outcome:
        adapter.preview_bytes(raw, "xlsx")
    assert len(children) == 1 and children[0].poll() is not None
    assert sum(diagnostic_sizes) > adapter.MAX_XLSX_CHILD_DIAGNOSTIC
    assert "SYNTHETIC_SECRET" not in str(outcome.value)
    captured = capfd.readouterr()
    assert captured.out == captured.err == ""


def test_child_source_mismatch_fails_closed(monkeypatch, capfd, isolated_adapter):
    adapter = isolated_adapter
    raw = workbook_bytes()
    real_popen = adapter.subprocess.Popen
    children = []
    bad_reply = {"schema": adapter._XLSX_CHILD_SCHEMA, "status": "OK", "source_sha256": "0" * 64,
                 "rows": [{"row": 2, "raw": {}, "unmapped": [], "candidate": None, "option_changes": None}],
                 "skipped_rows": []}
    reply_bytes = (json.dumps(bad_reply) + "\n").encode("utf-8")
    program = "import sys; sys.stdin.buffer.readline(); sys.stdout.buffer.write(" + repr(reply_bytes) + ")"
    parse_hashes = []
    original_loads = adapter._StrictJson.loads

    def observed_loads(value):
        parse_hashes.append(hashlib.sha256(value.encode("utf-8")).hexdigest())
        return original_loads(value)

    def run_stub(_command, **kwargs):
        child = real_popen([sys.executable, "-I", "-B", "-c", program], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(adapter.subprocess, "Popen", run_stub)
    monkeypatch.setattr(adapter._StrictJson, "loads", staticmethod(observed_loads))
    with pytest.raises(adapter.UpstreamUnavailable):
        adapter.preview_bytes(raw, "xlsx")
    assert len(children) == 1 and children[0].poll() is not None
    assert parse_hashes == [hashlib.sha256(reply_bytes).hexdigest()]
    # The mismatched SHA was evaluated only after direct child and pipes were
    # confirmed closed, so an unknown-cleanup failure cannot satisfy the test.
    available = adapter._XLSX_SLOT.acquire(blocking=False)
    assert available
    if available:
        adapter._XLSX_SLOT.release()
    captured = capfd.readouterr()
    assert captured.out == captured.err == ""


def test_malformed_child_rows_fail_closed_without_echoing_private_values(monkeypatch, capfd):
    raw = workbook_bytes()
    identity = {"question": "Q", "question_type": "short_answer", "options": {}, "correct_answer": "A"}
    question_id = "import:" + hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    candidate = {**identity, "explanation": "", "difficulty": "", "user_answer": "", "tags": [],
                 "question_id": question_id}
    reply = {"schema": adapter._XLSX_CHILD_SCHEMA, "status": "OK", "source_sha256": hashlib.sha256(raw).hexdigest(),
             "rows": [{"row": 2, "raw": {"question": "Q", "answer": "A"}, "unmapped": [],
                       "candidate": candidate, "option_changes": []}], "skipped_rows": []}
    real_popen = adapter.subprocess.Popen
    program = [""]
    children, parse_hashes = [], []
    original_loads = adapter._StrictJson.loads

    def run_stub(_command, **kwargs):
        child = real_popen([sys.executable, "-I", "-B", "-c", program[0]], **kwargs)
        children.append(child)
        return child

    def set_reply(value):
        reply_bytes = (json.dumps(value) + "\n").encode("utf-8")
        program[0] = "import sys; sys.stdin.buffer.readline(); sys.stdout.buffer.write(" + repr(reply_bytes) + ")"
        return hashlib.sha256(reply_bytes).hexdigest()

    def observed_loads(value):
        parse_hashes.append(hashlib.sha256(value.encode("utf-8")).hexdigest())
        return original_loads(value)

    def check_attempt(expected_hash, count):
        assert len(children) == count and children[-1].poll() is not None
        assert len(parse_hashes) == count and parse_hashes[-1] == expected_hash
        available = adapter._XLSX_SLOT.acquire(blocking=False)
        assert available
        if available:
            adapter._XLSX_SLOT.release()

    monkeypatch.setattr(adapter.subprocess, "Popen", run_stub)
    monkeypatch.setattr(adapter._StrictJson, "loads", staticmethod(observed_loads))
    # A fully forged but internally consistent reply illustrates the stated
    # limit: a matching SHA and replay are not child or source authentication.
    expected_hash = set_reply(reply)
    assert adapter.preview_bytes(raw, "xlsx")["rows"][0]["question"]["question"] == "Q"
    check_attempt(expected_hash, 1)

    malformed = []
    missing = copy.deepcopy(reply)
    missing["rows"][0]["candidate"] = {}
    malformed.append(missing)
    wrong_answer = copy.deepcopy(reply)
    wrong_answer["rows"][0]["candidate"]["correct_answer"] = "SYNTHETIC_PRIVATE_ANSWER"
    malformed.append(wrong_answer)
    wrong_unmapped = copy.deepcopy(reply)
    wrong_unmapped["rows"][0]["unmapped"] = [{"key": "unexpected", "value": "SYNTHETIC_PRIVATE_FIELD",
                                                "reason": "not_selected_by_upstream"}]
    malformed.append(wrong_unmapped)
    wrong_changes = copy.deepcopy(reply)
    wrong_changes["rows"][0]["option_changes"] = [{"key": "A", "old": None, "new": "SYNTHETIC_PRIVATE_CHANGE",
                                                      "reason": "question_type_option_change"}]
    malformed.append(wrong_changes)
    wrong_raw_type = copy.deepcopy(reply)
    wrong_raw_type["rows"][0]["raw"]["answer"] = {"private": "SYNTHETIC_PRIVATE_FIELD"}
    malformed.append(wrong_raw_type)
    for count, value in enumerate(malformed, 2):
        expected_hash = set_reply(value)
        with pytest.raises(adapter.UpstreamUnavailable) as outcome:
            adapter.preview_bytes(raw, "xlsx")
        check_attempt(expected_hash, count)
        assert "SYNTHETIC_PRIVATE" not in str(outcome.value)
    captured = capfd.readouterr()
    assert captured.out == captured.err == ""


def test_dependency_missing_is_unavailable_without_affecting_json(monkeypatch):
    import builtins
    raw = workbook_bytes()
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "defusedxml" or name.startswith("defusedxml."):
            raise ImportError("synthetic unavailable dependency")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(adapter.UpstreamUnavailable):
        adapter._private_preview_in_process(raw, "xlsx")
    result = adapter.preview_bytes(b'[{"question":"Q","answer":"A"}]', "json")
    assert result["rows"][0]["status"] == "CANDIDATE"
