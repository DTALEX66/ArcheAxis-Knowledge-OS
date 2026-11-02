"""Bounded offline preview using pinned DeepTutor 1.7.1 import functions.

No upstream module top level, model, network or database is run. The private
in-memory result retains the exact input bytes and unmapped fields only for the
life of the call; the display receipt does not persist them or permit restart
recovery. The caller-supplied source and upstream import ID are not Core
bindings, proof of provider generation, or answer-secrecy mechanisms.
"""
from __future__ import annotations

import __future__
import ast
import base64
import binascii
import csv
import datetime
import hashlib
import io
import json
import math
import os
import re
import secrets
import stat
import subprocess
import sys
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "archeaxis.deeptutor-practice-import-preview/v1"
UPSTREAM_SHA256 = "9ee4dd1abfa150fd81c3e3e31e2321761bab05509f6e4a5fca555ede2bbfd260"
UPSTREAM_SIZE = 8_880
UPSTREAM_ROOT = Path(__file__).absolute().parent / "upstream"
UPSTREAM = UPSTREAM_ROOT / "importing.py"
MAX_BYTES = 5 * 1024 * 1024
MAX_REQUEST = ((MAX_BYTES + 2) // 3) * 4 + 4096
MAX_NODES = 50_000
MAX_CELL_BYTES = 20_000
FORMATS = frozenset({"csv", "tsv", "json", "xlsx"})
MAX_XLSX_PARTS = 2_000
MAX_XLSX_EXPANDED = 30 * 1024 * 1024
MAX_XLSX_XML_NODES = 150_000
MAX_XLSX_CHILD_OUTPUT = 40 * 1024 * 1024
MAX_XLSX_CHILD_DIAGNOSTIC = 64 * 1024
XLSX_CHILD_TIMEOUT_SECONDS = 30
_XLSX_CHILD_SCHEMA = "archeaxis.deeptutor-xlsx-private-child/v1"
_SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
# Bound launches within this module instance. If direct-child or pipe cleanup
# cannot be confirmed, retain the slot; other instances/processes are not
# covered and descendant cleanup is never implied by this check.
_XLSX_SLOT = threading.BoundedSemaphore(1)


class InvalidInput(ValueError):
    """The bytes or envelope are outside the finite import contract."""


class UpstreamUnavailable(RuntimeError):
    """The fixed upstream source or reviewed subset could not be verified."""


def _read_original():
    """Refuse links and Windows reparse ancestors before opening the source."""
    path = UPSTREAM.absolute()
    if path.parent != UPSTREAM_ROOT.absolute() or path.name != "importing.py":
        raise UpstreamUnavailable("upstream path mismatch")
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise UpstreamUnavailable("upstream link is not allowed")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise UpstreamUnavailable("upstream ancestor unavailable")
            before.append(info)
        expected = before[-1]
        if not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1 or expected.st_size != UPSTREAM_SIZE or not expected.st_ino:
            raise UpstreamUnavailable("upstream source unavailable")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise UpstreamUnavailable("upstream identity changed")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise UpstreamUnavailable("upstream ancestor changed")
            data = bytearray()
            while len(data) <= UPSTREAM_SIZE:
                chunk = os.read(fd, UPSTREAM_SIZE + 1 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
        finally:
            os.close(fd)
    except OSError as error:
        raise UpstreamUnavailable("upstream source unavailable") from error
    source = bytes(data)
    if len(source) != UPSTREAM_SIZE or hashlib.sha256(source).hexdigest() != UPSTREAM_SHA256:
        raise UpstreamUnavailable("upstream source identity mismatch")
    return source


def _unique_object(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise InvalidInput("duplicate JSON member")
        output[key] = value
    return output


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise InvalidInput("non-finite number")
    return number


def _limited_int(value):
    if len(value) > 100:
        raise InvalidInput("integer outside bounds")
    return int(value)


def _invalid_constant(_value):
    raise InvalidInput("non-finite number")


class _StrictJson:
    dumps = staticmethod(json.dumps)

    @staticmethod
    def loads(value):
        return json.loads(value, object_pairs_hook=_unique_object, parse_float=_finite_float,
                          parse_int=_limited_int, parse_constant=_invalid_constant)


def _one(nodes, predicate):
    matches = [node for node in nodes if predicate(node)]
    if len(matches) != 1:
        raise UpstreamUnavailable("upstream definition mismatch")
    return matches[0]


class _RemoveXlsx(ast.NodeTransformer):
    """Remove the one optional openpyxl branch; leave CSV/TSV/JSON AST intact."""
    def __init__(self):
        self.removed = 0

    def visit_If(self, node):
        test = node.test
        if (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "suffix"
                and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
                and len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == ".xlsx"):
            self.removed += 1
            return [self.visit(child) for child in node.orelse]
        return self.generic_visit(node)


class _BindXlsx(ast.NodeTransformer):
    """Bind only the pinned branch's import to an already checked callable."""
    def __init__(self):
        self.bound = 0

    def visit_If(self, node):
        test = node.test
        if (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "suffix"
                and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
                and len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == ".xlsx"):
            imports = [part for part in node.body if isinstance(part, ast.ImportFrom)]
            if (len(imports) != 1 or imports[0].module != "openpyxl" or imports[0].level != 0
                    or len(imports[0].names) != 1 or imports[0].names[0].name != "load_workbook"
                    or imports[0].names[0].asname is not None):
                raise UpstreamUnavailable("upstream spreadsheet import mismatch")
            node.body.remove(imports[0])
            self.bound += 1
        return self.generic_visit(node)


def _selected_functions(*, xlsx_loader=None):
    try:
        tree = ast.parse(_read_original(), filename="deeptutor-1.7.1/practice/importing.py")
    except (SyntaxError, ValueError, UnicodeError) as error:
        raise UpstreamUnavailable("upstream source invalid") from error
    constants = []
    for name in ("MAX_BYTES", "MAX_ROWS", "MAX_CELL", "MAX_COLUMNS", "ALIASES", "TYPES"):
        node = _one(tree.body, lambda n: isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
        try:
            if name == "MAX_BYTES":
                # The exact pinned original is a multiplication AST, not a
                # literal. Accept only that precise syntax; never eval input.
                expected = ast.parse("5 * 1024 * 1024", mode="eval").body
                if ast.dump(node.value, include_attributes=False) != ast.dump(expected, include_attributes=False):
                    raise ValueError("unexpected maximum expression")
            else:
                value = ast.literal_eval(node.value)
                limits = {"MAX_ROWS": 500, "MAX_CELL": 20000, "MAX_COLUMNS": 64}
                if name in limits and (type(value) is not int or value != limits[name]):
                    raise ValueError("unexpected maximum")
        except (ValueError, TypeError, SyntaxError) as error:
            raise UpstreamUnavailable("upstream constant mismatch") from error
        constants.append(node)
    functions = [_one(tree.body, lambda n: isinstance(n, ast.FunctionDef) and n.name == name)
                 for name in ("_cell", "parse_rows", "normalize_question")]
    transformer = _RemoveXlsx() if xlsx_loader is None else _BindXlsx()
    functions[1] = transformer.visit(functions[1])
    if (transformer.removed if xlsx_loader is None else transformer.bound) != 1:
        raise UpstreamUnavailable("upstream spreadsheet branch mismatch")
    for definition in [*constants, *functions]:
        for node in ast.walk(definition):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
                raise UpstreamUnavailable("unexpected upstream operation")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "open", "__import__", "compile"}:
                raise UpstreamUnavailable("unexpected upstream operation")
    module = ast.Module(body=[*constants, *functions], type_ignores=[])
    ast.fix_missing_locations(module)
    builtins = {"str": str, "dict": dict, "list": list, "set": set, "len": len,
                "isinstance": isinstance, "enumerate": enumerate, "any": any, "zip": zip,
                "chr": chr, "next": next, "sorted": sorted, "int": int,
                "ValueError": ValueError, "TypeError": TypeError, "UnicodeDecodeError": UnicodeDecodeError}
    namespace = {"__name__": "deeptutor_171_import_subset", "__builtins__": builtins,
                 "csv": csv, "hashlib": hashlib, "io": io, "json": _StrictJson, "Path": Path, "re": re}
    if xlsx_loader is not None:
        builtins["sum"] = sum
        namespace.update(zipfile=zipfile, load_workbook=xlsx_loader)
    try:
        code = compile(module, "deeptutor-1.7.1/practice/importing.py", "exec",
                       flags=__future__.annotations.compiler_flag, dont_inherit=True)
        exec(code, namespace)  # noqa: S102
        return namespace
    except (NameError, TypeError, ValueError, KeyError) as error:
        raise UpstreamUnavailable("upstream subset unavailable") from error


def _bounded_tree(value, *, max_nodes=MAX_NODES):
    """Bound nested JSON values before upstream normalization/string coercion."""
    stack = [(value, 0)]
    seen = 0
    while stack:
        item, depth = stack.pop()
        seen += 1
        if seen > max_nodes or depth > 8:
            raise InvalidInput("input structure exceeds bounds")
        if isinstance(item, str):
            if "\x00" in item or len(item.encode("utf-8")) > MAX_CELL_BYTES:
                raise InvalidInput("cell outside bounds")
        elif isinstance(item, dict):
            if len(item) > 64 or any(not isinstance(key, str) for key in item):
                raise InvalidInput("object outside bounds")
            stack.extend((part, depth + 1) for pair in item.items() for part in pair)
        elif isinstance(item, list):
            if len(item) > 500:
                raise InvalidInput("list outside bounds")
            stack.extend((part, depth + 1) for part in item)
        elif type(item) is float and not math.isfinite(item):
            raise InvalidInput("non-finite input value")
        elif item is not None and type(item) not in (int, float, bool):
            raise InvalidInput("unsupported input value")


def _csv_structure(data, format):
    """Reject upstream zip truncation and report intentionally skipped rows."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("gb18030")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel_tab if format == "tsv" else csv.excel
    reader = csv.reader(io.StringIO(text, newline=""), dialect, strict=True)
    headers = next(reader, None)
    if not headers or any(not item.strip() for item in headers):
        raise InvalidInput("empty headers are not supported")
    if len(headers) > 64:
        raise InvalidInput("too many columns")
    # Match the upstream's duplicate-header normalization without rewriting
    # distinct names; unselected columns remain traceable in the private row.
    canonical = [item.strip().lower() for item in headers]
    if len(canonical) != len(set(canonical)):
        raise InvalidInput("duplicate or ambiguous headers")
    skipped = []
    for number, row in enumerate(reader, 2):
        if number > 502:
            raise InvalidInput("too many rows")
        if not any(value.strip() for value in row):
            skipped.append(number)
        elif len(row) != len(headers):
            raise InvalidInput("row width does not match headers")
    return skipped


def _xlsx_engine():
    """Use only the locally reviewed XML-protected library versions."""
    try:
        import defusedxml
        import defusedxml.ElementTree as safe_xml
        import openpyxl
        import openpyxl.xml as openpyxl_xml
        import openpyxl.xml.functions as xml_functions
    except ImportError:
        raise UpstreamUnavailable("spreadsheet dependencies unavailable") from None
    if (getattr(openpyxl, "__version__", None) != "3.1.5" or getattr(defusedxml, "__version__", None) != "0.7.1"
            or getattr(openpyxl_xml, "DEFUSEDXML", None) is not True
            or getattr(xml_functions, "iterparse", None) is not getattr(safe_xml, "iterparse", None)
            or not callable(getattr(safe_xml, "iterparse", None))
            or not callable(getattr(openpyxl, "load_workbook", None))):
        raise UpstreamUnavailable("spreadsheet XML protection unavailable")
    return openpyxl.load_workbook, safe_xml


def _positive_xlsx_dimension(element, name, *, integer=False):
    value = element.attrib.get(name)
    if value is None:
        return
    pattern = r"[+]?[0-9]+" if integer else r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
    if len(value) > 64 or re.fullmatch(pattern, value) is None:
        raise InvalidInput("invalid spreadsheet dimension")
    number = int(value) if integer else float(value)
    if not math.isfinite(number) or number <= 0:
        raise InvalidInput("zero or invalid spreadsheet dimension")


def _xlsx_xml(name, data, safe_xml, node_budget, sheet):
    """Check every XML part before openpyxl sees the workbook bytes."""
    if b"\x00" in data:
        raise InvalidInput("unsupported spreadsheet XML encoding")
    text = data.decode("utf-8-sig")
    declaration = re.match(r"\s*<\?xml\s+[^?]*encoding\s*=\s*(['\"])([^'\"]+)\1", text, re.I)
    if declaration and declaration.group(2).lower() not in {"utf-8", "utf8"}:
        raise InvalidInput("unsupported spreadsheet XML encoding")
    # Conservative: even DTD/entity-looking content in comments is rejected.
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise InvalidInput("spreadsheet XML declaration forbidden")
    stack = []
    dimension = None
    dimensions_seen = sheet_data_seen = sheet_format_seen = 0
    max_row = max_column = 0
    last_row = 0
    row_number = None
    last_column = 0
    cell_parts = None
    relationship_ids = set()
    for event, element in safe_xml.iterparse(io.BytesIO(data), events=("start", "end"),
                                             forbid_dtd=True, forbid_entities=True, forbid_external=True):
        tag = element.tag
        if event == "start":
            node_budget[0] += 1
            if node_budget[0] > MAX_XLSX_XML_NODES or len(stack) >= 64:
                raise InvalidInput("spreadsheet XML exceeds bounds")
            parent = stack[-1] if stack else None
            stack.append(tag)
            if name.lower().endswith(".rels") and tag.endswith("}Relationship"):
                identity = element.attrib.get("Id", "")
                mode = element.attrib.get("TargetMode", "Internal").lower()
                target = element.attrib.get("Target", "")
                if (not identity or identity in relationship_ids or mode != "internal"
                        or not target or ":" in target or "\\" in target
                        or "?" in target or "#" in target or target.startswith("//")
                        or ".." in target.split("/")):
                    raise InvalidInput("ambiguous or external spreadsheet relationship")
                relationship_ids.add(identity)
            if not sheet:
                continue
            if len(stack) == 1 and tag != _SHEET_NS + "worksheet":
                raise InvalidInput("invalid worksheet root")
            if tag == _SHEET_NS + "dimension":
                dimensions_seen += 1
                if parent != _SHEET_NS + "worksheet" or dimensions_seen != 1:
                    raise InvalidInput("ambiguous worksheet dimension")
                dimension = element.attrib.get("ref")
            elif tag == _SHEET_NS + "sheetData":
                sheet_data_seen += 1
                if parent != _SHEET_NS + "worksheet" or sheet_data_seen != 1:
                    raise InvalidInput("ambiguous worksheet data")
            elif tag == _SHEET_NS + "sheetFormatPr":
                sheet_format_seen += 1
                if parent != _SHEET_NS + "worksheet" or sheet_format_seen != 1:
                    raise InvalidInput("ambiguous worksheet defaults")
                if element.attrib.get("zeroHeight", "0") not in {"0", "false"}:
                    raise InvalidInput("hidden or invalid default row height")
                _positive_xlsx_dimension(element, "defaultRowHeight")
                _positive_xlsx_dimension(element, "defaultColWidth")
                _positive_xlsx_dimension(element, "baseColWidth", integer=True)
            elif tag == _SHEET_NS + "row":
                if parent != _SHEET_NS + "sheetData" or row_number is not None:
                    raise InvalidInput("ambiguous worksheet row")
                raw_row = element.attrib.get("r", "")
                if re.fullmatch(r"[1-9][0-9]{0,2}", raw_row) is None:
                    raise InvalidInput("invalid worksheet row")
                row_number = int(raw_row)
                if row_number <= last_row or row_number > 501:
                    raise InvalidInput("worksheet row outside bounds")
                if element.attrib.get("hidden", "0") not in {"0", "false"}:
                    raise InvalidInput("hidden spreadsheet row")
                _positive_xlsx_dimension(element, "ht")
                max_row = max(max_row, row_number)
                last_row, last_column = row_number, 0
            elif tag == _SHEET_NS + "col":
                if element.attrib.get("hidden", "0") not in {"0", "false"}:
                    raise InvalidInput("hidden spreadsheet column")
                _positive_xlsx_dimension(element, "width")
            elif tag == _SHEET_NS + "c":
                if parent != _SHEET_NS + "row" or row_number is None or cell_parts is not None:
                    raise InvalidInput("ambiguous worksheet cell")
                match = re.fullmatch(r"([A-Z]{1,2})([1-9][0-9]{0,2})", element.attrib.get("r", ""))
                if not match or int(match.group(2)) != row_number:
                    raise InvalidInput("invalid worksheet coordinate")
                column = 0
                for char in match.group(1):
                    column = column * 26 + ord(char) - 64
                if column <= last_column or column > 64:
                    raise InvalidInput("worksheet column outside bounds")
                last_column = column
                max_column = max(max_column, column)
                cell_parts = set()
            elif tag in {_SHEET_NS + "f", _SHEET_NS + "mergeCells"}:
                raise InvalidInput("formulas or merged cells unsupported")
            elif parent == _SHEET_NS + "c" and tag in {_SHEET_NS + "v", _SHEET_NS + "is"}:
                if cell_parts is None or cell_parts:
                    raise InvalidInput("duplicate worksheet cell content")
                cell_parts.add(tag)
        else:
            if sheet and tag == _SHEET_NS + "c":
                cell_parts = None
            elif sheet and tag == _SHEET_NS + "row":
                row_number = None
            stack.pop()
            element.clear()
    if not sheet:
        return None
    if dimension is None or sheet_data_seen != 1 or not max_row or not max_column:
        raise InvalidInput("missing worksheet dimension")
    from openpyxl.utils.cell import range_boundaries
    bounds = range_boundaries(dimension)
    if bounds != (1, 1, max_column, max_row):
        raise InvalidInput("worksheet dimension does not match cells")
    return max_row, max_column


def _xlsx_structure(data, loader, safe_xml, cell_text):
    """Conservatively preflight ZIP, worksheet layout and all observed values."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_XLSX_PARTS or sum(item.file_size for item in entries) > MAX_XLSX_EXPANDED:
                raise InvalidInput("spreadsheet archive exceeds bounds")
            names = set()
            sheet_path = None
            sheet_bounds = None
            node_budget = [0]
            for item in entries:
                name = item.filename
                parts = name.rstrip("/").split("/")
                folded = name.casefold()
                if (not name or name.startswith("/") or "\\" in name or ":" in name
                        or any(part in {"", ".", ".."} for part in parts)
                        or any(ord(char) < 32 for char in name) or folded in names
                        or item.flag_bits & 1 or item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        or stat.S_ISLNK(item.external_attr >> 16)):
                    raise InvalidInput("ambiguous spreadsheet archive")
                names.add(folded)
                if (folded.startswith("xl/externallinks/") or folded.startswith("xl/embeddings/")
                        or folded.endswith("vbaproject.bin")):
                    raise InvalidInput("unsupported spreadsheet part")
                if item.is_dir():
                    continue
                # Do not hand an unchecked non-XML part to the workbook loader.
                # Images, macros and other binary workbook parts are unsupported.
                if not folded.endswith((".xml", ".rels")):
                    raise InvalidInput("unsupported spreadsheet part")
                is_sheet = re.fullmatch(r"xl/worksheets/[^/]+\.xml", name) is not None
                if is_sheet and sheet_path is not None:
                    raise InvalidInput("multiple worksheet parts")
                part = archive.read(item)
                bounds = _xlsx_xml(name, part, safe_xml, node_budget, is_sheet)
                if is_sheet:
                    sheet_path, sheet_bounds = name, bounds
            if sheet_path is None:
                raise InvalidInput("spreadsheet worksheet missing")
        book = loader(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
        try:
            if len(book.sheetnames) != 1 or len(book.worksheets) != 1 or book.active is None:
                raise InvalidInput("exactly one active worksheet required")
            sheet = book.active
            if (sheet.sheet_state != "visible" or sheet._worksheet_path != sheet_path
                    or (sheet.max_row, sheet.max_column) != sheet_bounds):
                raise InvalidInput("worksheet identity or dimension mismatch")
            rows = []
            for cells in sheet.iter_rows():
                row = []
                for cell in cells:
                    value = cell.value
                    if cell.data_type in {"f", "e"} or isinstance(value, (datetime.date, datetime.time, datetime.timedelta)):
                        raise InvalidInput("formula, error or date cell unsupported")
                    if type(value) is float and not math.isfinite(value):
                        raise InvalidInput("non-finite spreadsheet cell")
                    if value is not None and type(value) not in {str, int, float, bool}:
                        raise InvalidInput("unsupported spreadsheet cell")
                    row.append(value)
                _bounded_tree(row)
                rows.append(row)
            if len(rows) != sheet_bounds[0] or not rows:
                raise InvalidInput("worksheet rows do not match dimensions")
            headers = [cell_text(value).lower() for value in rows[0]]
            if any(not value for value in headers) or len(headers) != len(set(headers)):
                raise InvalidInput("empty or duplicate spreadsheet headers")
            parsed = []
            skipped = []
            for number, row in enumerate(rows[1:], 2):
                if any(cell_text(value) for value in row):
                    parsed.append((number, dict(zip(headers, row, strict=True))))
                else:
                    skipped.append(number)
            return parsed, skipped
        finally:
            book.close()
    except (InvalidInput, UpstreamUnavailable):
        raise
    except Exception:
        # ZIP/XML/library errors can contain private workbook content or paths.
        raise InvalidInput("spreadsheet could not be parsed") from None


def _unmapped(raw, aliases):
    """Trace fields the pinned normalizer did not select, including collisions."""
    entries = list(raw.items())
    effective = {}
    for index, (key, _value) in enumerate(entries):
        effective[str(key).strip().lower()] = index
    selected = set()
    for names in aliases.values():
        for name in names:
            if name in effective:
                selected.add(effective[name])
                break
    for letter in "abcdefghij":
        for name in (letter, f"选项{letter}"):
            if name in effective:
                selected.add(effective[name])
                break
    return [{"key": key, "value": value, "reason": "not_selected_by_upstream"}
            for index, (key, value) in enumerate(entries) if index not in selected]


def _option_changes(raw, candidate, functions):
    """Trace observed option replacements; other field changes are not compared."""
    row = {str(key).strip().lower(): value for key, value in raw.items()}
    options = next((row[name] for name in functions["ALIASES"]["options"] if name in row), "") or {}
    if isinstance(options, str):
        options = _StrictJson.loads(options)
    if isinstance(options, list):
        options = {chr(65 + index): value for index, value in enumerate(options)}
    current = {}
    changes = []
    cell = functions["_cell"]
    for key, value in options.items():
        value = cell(value)
        if value:
            key = str(key).strip().upper()
            if key in current and current[key] != value:
                changes.append({"key": key, "old": current[key], "new": value, "reason": "option_key_collision"})
            current[key] = value
    for letter in "ABCDEFGHIJ":
        value = cell(row.get(letter.lower(), row.get(f"选项{letter.lower()}", "")))
        if value:
            if letter in current and current[letter] != value:
                changes.append({"key": letter, "old": current[letter], "new": value, "reason": "option_column_override"})
            current[letter] = value
    for key in current.keys() | candidate["options"].keys():
        if current.get(key) != candidate["options"].get(key):
            changes.append({"key": key, "old": current.get(key), "new": candidate["options"].get(key),
                            "reason": "question_type_option_change"})
    return changes


@dataclass(repr=False)
class _PrivatePreview:
    source: bytes
    source_sha256: str
    format: str
    rows: list
    skipped_rows: list
    preview_id: str


def _private_preview_in_process(data, format):
    """Internal child implementation; callers must not run XLSX in a shared host."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_BYTES or not isinstance(format, str) or format not in FORMATS:
        raise InvalidInput("unsupported or oversized import")
    loader, safe_xml = _xlsx_engine() if format == "xlsx" else (None, None)
    functions = _selected_functions(xlsx_loader=loader)
    try:
        # JSON's tree is checked separately before the original parser sees it.
        if format == "json":
            _bounded_tree(_StrictJson.loads(data.decode("utf-8-sig")))
            skipped = []
        elif format == "xlsx":
            expected, skipped = _xlsx_structure(data, loader, safe_xml, functions["_cell"])
        else:
            skipped = _csv_structure(data, format)
        parsed = functions["parse_rows"](data, f"synthetic.{format}")
        if format == "xlsx" and parsed != expected:
            raise InvalidInput("spreadsheet parser disagreement")
        _bounded_tree([row for _number, row in parsed])
    except (UnicodeError, ValueError, TypeError, RecursionError, csv.Error) as error:
        raise InvalidInput("input could not be parsed") from error
    except Exception:
        if format == "xlsx":
            raise InvalidInput("spreadsheet could not be parsed") from None
        raise
    rows = []
    for number, raw in parsed:
        unmapped = _unmapped(raw, functions["ALIASES"])
        try:
            candidate = functions["normalize_question"](raw)
        except (ValueError, TypeError, RecursionError):
            rows.append({"row": number, "raw": raw, "unmapped": unmapped, "candidate": None, "option_changes": None})
        else:
            try:
                changes = _option_changes(raw, candidate, functions)
            except (ValueError, TypeError, AttributeError, RecursionError):
                changes = None
            rows.append({"row": number, "raw": raw, "unmapped": unmapped, "candidate": candidate, "option_changes": changes})
    if not rows:
        raise InvalidInput("no questions")
    return _PrivatePreview(source=data, source_sha256=hashlib.sha256(data).hexdigest(), format=format, rows=rows,
                           skipped_rows=skipped, preview_id="preview_" + secrets.token_hex(16))


def _xlsx_child_environment():
    """Pass only system startup and non-secret, project-owned home paths."""
    home_path = Path(__file__).absolute().parents[3] / ".project-local"
    if not home_path.is_dir():
        raise UpstreamUnavailable("spreadsheet worker directory unavailable")
    home = str(home_path)
    env = {name: home for name in ("HOME", "USERPROFILE", "TEMP", "TMP", "APPDATA", "LOCALAPPDATA",
                                    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME")}
    for name in ("SystemRoot", "WINDIR", "SYSTEMDRIVE"):
        if name in os.environ:
            env[name] = os.environ[name]
    for name in ("OPENPYXL_DEFUSEDXML", "OPENPYXL_LXML"):
        if name in os.environ:
            value = os.environ[name]
            if value not in {"True", "true", "1", "False", "false", "0"}:
                raise UpstreamUnavailable("spreadsheet configuration unavailable")
            env[name] = value
    return env


def _isolated_xlsx_preview(data):
    """Allow one owned child per instance, failing closed on unknown cleanup."""
    if not _XLSX_SLOT.acquire(blocking=False):
        raise UpstreamUnavailable("spreadsheet worker busy or cleanup unknown")
    cleanup_confirmed = [True]
    try:
        return _isolated_xlsx_preview_owned(data, cleanup_confirmed)
    finally:
        if cleanup_confirmed[0]:
            _XLSX_SLOT.release()


def _isolated_xlsx_preview_owned(data, cleanup_confirmed):
    """Read private child output with finite bounds; discard diagnostic bytes."""
    envelope = {"schema": _XLSX_CHILD_SCHEMA, "data_base64": base64.b64encode(data).decode("ascii")}
    wire = json.dumps(envelope, separators=(",", ":")).encode("ascii") + b"\n"
    if len(wire) > MAX_REQUEST:
        raise InvalidInput("spreadsheet request exceeds bounds")
    child_env = _xlsx_child_environment()
    # Set before attempting launch: an interruption during Popen cannot release
    # the slot while the child's actual state is unknown.
    cleanup_confirmed[0] = False
    try:
        child = subprocess.Popen([sys.executable, "-I", "-B", str(Path(__file__).absolute()), "--xlsx-private-child"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 cwd=str(Path(__file__).absolute().parent), env=child_env)
    except (OSError, ValueError):
        # Popen can fail after OS process creation, before returning a handle.
        # Its child and pipe state are therefore not established by the error.
        raise UpstreamUnavailable("spreadsheet worker unavailable") from None
    output = bytearray()
    problems = []
    diagnostic_size = [0]

    def terminate_direct():
        try:
            child.kill()
        except OSError:
            pass

    def close_pipe(stream):
        try:
            stream.close()
        except Exception:
            problems.append("pipe_close")

    def write_input():
        try:
            child.stdin.write(wire)
        except Exception:
            problems.append("input")
        finally:
            close_pipe(child.stdin)

    def read_output():
        try:
            while True:
                chunk = child.stdout.read(min(65_536, MAX_XLSX_CHILD_OUTPUT + 1 - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > MAX_XLSX_CHILD_OUTPUT:
                    problems.append("output_limit")
                    terminate_direct()
                    break
        except Exception:
            problems.append("output")
        finally:
            close_pipe(child.stdout)

    def discard_diagnostics():
        try:
            while True:
                chunk = child.stderr.read(65_536)
                if not chunk:
                    break
                diagnostic_size[0] += len(chunk)
                if diagnostic_size[0] > MAX_XLSX_CHILD_DIAGNOSTIC:
                    problems.append("diagnostic_limit")
                    terminate_direct()
                    break
        except Exception:
            problems.append("diagnostic")
        finally:
            close_pipe(child.stderr)

    threads = []
    unowned_pipes = [child.stdin, child.stdout, child.stderr]
    try:
        for target, pipe in zip((write_input, read_output, discard_diagnostics),
                                (child.stdin, child.stdout, child.stderr), strict=True):
            thread = threading.Thread(target=target, daemon=True)
            threads.append(thread)
            # A failed/interrupted start may have launched the thread already.
            # Do not close that pipe from this thread without ownership proof.
            unowned_pipes.remove(pipe)
            thread.start()
    except BaseException as error:
        terminate_direct()
        try:
            child.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
        for thread in threads:
            try:
                if thread.ident is not None:
                    thread.join(timeout=2)
            except (OSError, RuntimeError):
                pass
        for pipe in unowned_pipes:
            close_pipe(pipe)
        if not isinstance(error, Exception):
            raise
        raise UpstreamUnavailable("spreadsheet worker outcome unknown") from None
    try:
        exit_code = child.wait(timeout=XLSX_CHILD_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        problems.append("timeout")
        terminate_direct()
        try:
            exit_code = child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            exit_code = None
    for thread in threads:
        thread.join(timeout=2)
    pipe_threads_alive = any(thread.is_alive() for thread in threads)
    if exit_code is not None and not pipe_threads_alive and "pipe_close" not in problems:
        cleanup_confirmed[0] = True
    if pipe_threads_alive or problems or diagnostic_size[0] or exit_code != 0:
        # A direct-process kill cannot establish that trampoline descendants or
        # pipe-writing threads stopped. Never replay automatically or expose
        # the private bytes or diagnostic text in an error.
        raise UpstreamUnavailable("spreadsheet worker outcome unknown")
    try:
        reply = _StrictJson.loads(bytes(output).decode("utf-8"))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise UpstreamUnavailable("spreadsheet worker response unavailable") from None
    if (isinstance(reply, dict) and reply == {"schema": _XLSX_CHILD_SCHEMA, "status": "INVALID"}):
        raise InvalidInput("spreadsheet could not be parsed")
    try:
        if not isinstance(reply, dict) or reply.get("schema") != _XLSX_CHILD_SCHEMA:
            raise ValueError("invalid response")
        if (set(reply) != {"schema", "status", "source_sha256", "rows", "skipped_rows"}
                or reply["status"] != "OK" or reply["source_sha256"] != hashlib.sha256(data).hexdigest()
                or not isinstance(reply["rows"], list) or not reply["rows"]
                or not isinstance(reply["skipped_rows"], list)):
            raise ValueError("invalid response")
        _bounded_tree(reply["rows"], max_nodes=300_000)
        functions = _selected_functions()

        def canonical(value):
            return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

        def canonical_changes(value):
            if value is None:
                return None
            if not isinstance(value, list):
                raise ValueError("invalid changes")
            return sorted(canonical(item) for item in value)

        numbers = []
        for row in reply["rows"]:
            if (not isinstance(row, dict) or set(row) != {"row", "raw", "unmapped", "candidate", "option_changes"}
                    or type(row["row"]) is not int or not 2 <= row["row"] <= 501
                    or not isinstance(row["raw"], dict) or not row["raw"] or not isinstance(row["unmapped"], list)
                    or (row["candidate"] is not None and not isinstance(row["candidate"], dict))
                    or (row["option_changes"] is not None and not isinstance(row["option_changes"], list))):
                raise ValueError("invalid row")
            raw = row["raw"]
            if (any(not isinstance(key, str) or not key or key != key.strip().lower() for key in raw)
                    or any(value is not None and type(value) not in (str, int, float, bool) for value in raw.values())
                    or not any(functions["_cell"](value) for value in raw.values())):
                raise ValueError("invalid source row")
            if canonical(row["unmapped"]) != canonical(_unmapped(raw, functions["ALIASES"])):
                raise ValueError("unmapped fields differ")
            try:
                candidate = functions["normalize_question"](raw)
            except (ValueError, TypeError, RecursionError):
                candidate = None
                changes = None
            else:
                try:
                    changes = _option_changes(raw, candidate, functions)
                except (ValueError, TypeError, AttributeError, RecursionError):
                    changes = None
            if (canonical(row["candidate"]) != canonical(candidate)
                    or canonical_changes(row["option_changes"]) != canonical_changes(changes)):
                raise ValueError("candidate differs")
            numbers.append(row["row"])
        skipped = reply["skipped_rows"]
        if (numbers != sorted(set(numbers)) or len(skipped) > 500
                or any(type(n) is not int or not 2 <= n <= 501 for n in skipped)
                or skipped != sorted(set(skipped)) or set(numbers) & set(skipped)
                or set(numbers + skipped) != set(range(2, max(numbers + skipped) + 1))):
            raise ValueError("invalid row identities")
        return _PrivatePreview(source=data, source_sha256=reply["source_sha256"], format="xlsx",
                               rows=reply["rows"], skipped_rows=skipped,
                               preview_id="preview_" + secrets.token_hex(16))
    except Exception:
        raise UpstreamUnavailable("spreadsheet worker response unavailable") from None


def _private_preview(data, format):
    if (not isinstance(data, bytes) or not data or len(data) > MAX_BYTES
            or not isinstance(format, str) or format not in FORMATS):
        raise InvalidInput("unsupported or oversized import")
    if format == "xlsx":
        return _isolated_xlsx_preview(data)
    return _private_preview_in_process(data, format)


def _xlsx_child_main():
    """Private pipe protocol; stdout can contain answers and is never public."""
    try:
        raw = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        if not raw or len(raw) > MAX_REQUEST:
            raise InvalidInput("invalid input")
        value = _StrictJson.loads(raw.decode("utf-8"))
        if (not isinstance(value, dict) or set(value) != {"schema", "data_base64"}
                or value["schema"] != _XLSX_CHILD_SCHEMA or not isinstance(value["data_base64"], str)):
            raise InvalidInput("invalid input")
        data = base64.b64decode(value["data_base64"], validate=True)
        batch = _private_preview_in_process(data, "xlsx")
        reply = {"schema": _XLSX_CHILD_SCHEMA, "status": "OK", "source_sha256": batch.source_sha256,
                 "rows": batch.rows, "skipped_rows": batch.skipped_rows}
    except (InvalidInput, ValueError, TypeError, UnicodeError, RecursionError, binascii.Error):
        reply = {"schema": _XLSX_CHILD_SCHEMA, "status": "INVALID"}
    except Exception:
        # Do not print diagnostics, source bytes, or exceptions from libraries.
        reply = {"schema": _XLSX_CHILD_SCHEMA, "status": "UNAVAILABLE"}
    try:
        parts = bytearray()
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        for text in encoder.iterencode(reply):
            chunk = text.encode("utf-8")
            if len(parts) + len(chunk) + 1 > MAX_XLSX_CHILD_OUTPUT:
                return 1
            parts.extend(chunk)
        sys.stdout.buffer.write(parts + b"\n")
        return 0
    except (ValueError, TypeError, UnicodeError, OSError):
        return 1


def preview_bytes(data, format):
    """Return a redacted, ephemeral preview; this function never reads a path."""
    batch = _private_preview(data, format)
    rows = []
    for item in batch.rows:
        candidate = item["candidate"]
        row = {"source_row": item["row"], "source_field_count": len(item["raw"]),
               "unselected_top_level_field_count": len(item["unmapped"]),
               "known_option_changes_count": None if item["option_changes"] is None else len(item["option_changes"]),
               "other_selected_values_compared": False,
               "normalization": "upstream_normalized_original_not_retained_in_receipt",
               "projection_omitted_fields": ["correct_answer", "user_answer", "explanation", "difficulty", "tags"]}
        if candidate is None:
            row.update(status="REJECTED", issue_codes=["upstream_row_invalid"])
        else:
            row.update(status="CANDIDATE",
                       question={key: candidate[key] for key in ("question", "question_type", "options")})
        rows.append(row)
    result = {"schema": SCHEMA, "preview_id": batch.preview_id, "preview_id_scope": "ephemeral_not_content_binding",
            "source_within_size_limit": True,
            "source_row_scope": "json_array_index_one_based" if batch.format == "json"
                                else "xlsx_worksheet_row_one_based_including_header" if batch.format == "xlsx"
                                else "tabular_record_index_one_based_including_header",
            "source_format": batch.format, "upstream_member_sha256": UPSTREAM_SHA256,
            "origin": "caller_declared_unverified", "upstream_identity_in_receipt": False,
            "original_bytes_persisted": False, "restart_recovery": "not_available",
            "unmapped_values_persisted": False, "provider_run": "NOT_INVOKED", "model_call": "NOT_INVOKED",
            "independent_mastery": "not_established", "skipped_source_rows": batch.skipped_rows, "rows": rows}
    if batch.format == "xlsx":
        result.update(workbook_scope="single_visible_active_worksheet_only",
                      workbook_non_cell_content="not_preserved_in_preview")
    return result


def main():
    try:
        raw = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        if not raw or len(raw) > MAX_REQUEST:
            raise InvalidInput("empty or oversized request")
        value = _StrictJson.loads(raw.decode("utf-8"))
        if not isinstance(value, dict) or set(value) != {"schema", "request_id", "format", "data_base64"} or value["schema"] != SCHEMA:
            raise InvalidInput("invalid envelope")
        request_id = value["request_id"]
        if not isinstance(request_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) is None:
            raise InvalidInput("invalid request identity")
        encoded = value["data_base64"]
        if not isinstance(encoded, str) or len(encoded) > ((MAX_BYTES + 2) // 3) * 4:
            raise InvalidInput("invalid byte encoding")
        data = base64.b64decode(encoded, validate=True)
        result = preview_bytes(data, value["format"])
        result["request_id"] = request_id
    except (InvalidInput, ValueError, TypeError, UnicodeError, RecursionError, binascii.Error):
        result = {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
        code = 2
    except (UpstreamUnavailable, OSError, SyntaxError):
        result = {"schema": SCHEMA, "status": "UNAVAILABLE", "reason_code": "UPSTREAM_UNAVAILABLE"}
        code = 1
    else:
        result["status"] = "PREVIEW"
        code = 0
    # The worker protocol is UTF-8 regardless of the host's text console code page.
    wire = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(wire + b"\n")
    return code


if __name__ == "__main__":
    if sys.argv[1:] == ["--xlsx-private-child"]:
        raise SystemExit(_xlsx_child_main())
    raise SystemExit(main())
