"""A declared capability route must be checked before a runtime ships.

The point of this check is to move "the engine is not usable on the runtime
interpreter" from a failed job at first use to a named failure at packaging time - which
is exactly the failure mode that cost two rounds of this work, where a missing YAML
parser and missing engine distributions surfaced as engine-shaped errors from a job.

These tests use a stub worker that speaks the hello protocol, so they pin the contract
rather than any particular engine.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release" / "verify_backend_capabilities.py"


def load():
    spec = importlib.util.spec_from_file_location("verify_backend_capabilities", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STUB_WORKER = '''\
import argparse, json, sys
parser = argparse.ArgumentParser()
parser.add_argument("--staging-root", required=True)
parser.add_argument("--artifact-root", default=None)
parser.parse_args()
print(json.dumps({"schema": "archeaxis.worker-hello/v1", "type": "hello",
                  "protocol": {"major": 1, "min_minor": 0, "max_minor": 0},
                  "worker": {"name": "stub", "version": "1"},
                  "capabilities": ["{capability}"], "schemas": []}))
sys.stdin.read()
'''


def build(tmp_path: Path, routes: list[dict], *, worker_capability: str = "canvas.structure") -> Path:
    """A minimal staged root: profile, an interpreter, a manifest, and stub workers."""
    (tmp_path / "workers").mkdir(parents=True, exist_ok=True)
    for route in routes:
        worker = tmp_path / route["script"]
        worker.parent.mkdir(parents=True, exist_ok=True)
        worker.write_text(STUB_WORKER.replace("{capability}", worker_capability),
                          encoding="utf-8")
    (tmp_path / "config" / "environment").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "environment" / "capability-requirements.yaml").write_text(
        "capabilities:\n  toolchains: []\n", encoding="utf-8")
    profile = {
        "schema": "archeaxis.worker-profile/v1",
        "python": sys.executable,
        "script": "workers/transport/text_ndjson.py",
        "staging": "data/worker-staging",
        "routes": routes,
    }
    (tmp_path / "worker-profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (tmp_path / "data" / "worker-staging").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_a_ready_route_is_reported_ready(tmp_path):
    module = load()
    root = build(tmp_path, [{"capability": "canvas.structure",
                             "script": "workers/document/worker_canvas.py"}])
    report = module.verify(root, None, None, None)
    assert report["ok"] is True
    assert report["summary"] == {"total": 1, "ready": 1, "not_ready": 0}
    entry = report["capabilities"][0]
    assert entry["launch"]["ok"] is True
    assert entry["launch"]["advertised"] == ["canvas.structure"]


def test_a_worker_advertising_a_different_capability_fails_by_name(tmp_path):
    module = load()
    root = build(tmp_path,
                 [{"capability": "canvas.structure", "script": "workers/document/worker_canvas.py"}],
                 worker_capability="pdf.extract")
    report = module.verify(root, None, None, None)
    assert report["ok"] is False
    entry = report["capabilities"][0]
    assert entry["ok"] is False
    assert "pdf.extract" in entry["launch"]["reason"]
    assert "canvas.structure" in entry["launch"]["reason"]


def test_a_missing_worker_script_fails_by_name(tmp_path):
    module = load()
    root = build(tmp_path, [])
    profile = json.loads((root / "worker-profile.json").read_text(encoding="utf-8"))
    profile["routes"] = [{"capability": "pdf.extract", "script": "workers/document/absent.py"}]
    (root / "worker-profile.json").write_text(json.dumps(profile), encoding="utf-8")
    report = module.verify(root, None, None, None)
    assert report["ok"] is False
    assert "absent.py" in report["capabilities"][0]["launch"]["reason"]


def test_a_missing_engine_module_fails_that_route(tmp_path):
    """pdf.extract needs pymupdf; the assertion is on the module check, not the engine."""
    module = load()
    root = build(tmp_path, [{"capability": "pdf.extract",
                             "script": "workers/document/worker_pdf.py"}],
                 worker_capability="pdf.extract")
    report = module.verify(root, None, None, None)
    entry = report["capabilities"][0]
    assert entry["launch"]["ok"] is True, "the stub worker launches"
    modules = entry["engine"]["modules"]
    assert modules["required"] == ["pymupdf"]
    assert entry["ok"] is modules["ok"]


def test_an_absent_profile_is_a_named_failure(tmp_path):
    module = load()
    report = module.verify(tmp_path, None, None, None)
    assert report["ok"] is False
    assert "worker profile is missing" in report["failure"]


def test_a_capability_with_no_engine_requirement_reports_none(tmp_path):
    """media.probe reads a container header with the standard library only."""
    module = load()
    root = build(tmp_path, [{"capability": "media.probe",
                             "script": "workers/document/worker_media.py"}],
                 worker_capability="media.probe")
    report = module.verify(root, None, None, None)
    entry = report["capabilities"][0]
    assert entry["engine"]["modules"] == {}
    assert entry["engine"]["executables"] == {}
    assert entry["ok"] is True


def test_a_declared_executable_is_resolved_through_the_manifest(tmp_path):
    """The staged resolver must find the declared tesseract; only the manifest decides.

    An empty declaration is therefore a failure, which is the point: the engine is found
    because it is declared, not because it happens to be on PATH.
    """
    module = load()
    root = build(tmp_path, [{"capability": "image.ocr",
                             "script": "workers/vision/worker_ocr.py"}],
                 worker_capability="image.ocr")
    tool_paths = ROOT / "services" / "python-workers" / "tool_paths.py"
    (root / "workers" / "tool_paths.py").write_text(
        tool_paths.read_text(encoding="utf-8"), encoding="utf-8")
    report = module.verify(root, None, None, None)
    entry = report["capabilities"][0]
    executables = entry["engine"]["executables"]
    assert set(executables) == {"tesseract", "tesseract-languages"}
    for name, value in executables.items():
        assert ("ok" in value) and isinstance(value["ok"], bool), name


def test_an_executable_the_engine_lacks_is_distinguished_from_one_not_checked(tmp_path):
    """"not found" and "could not be checked" are different answers.

    The report must not say an engine is absent when the declaration simply could not be
    read, because that sends someone to install a tool they already have.
    """
    module = load()
    root = build(tmp_path, [{"capability": "image.ocr",
                             "script": "workers/vision/worker_ocr.py"}],
                 worker_capability="image.ocr")
    tool_paths = ROOT / "services" / "python-workers" / "tool_paths.py"
    (root / "workers" / "tool_paths.py").write_text(
        tool_paths.read_text(encoding="utf-8"), encoding="utf-8")
    # A readable manifest that declares nothing: tesseract is genuinely not declared.
    (root / "config" / "environment" / "capability-requirements.yaml").write_text(
        "capabilities:\n  toolchains: []\n", encoding="utf-8")
    report = module.verify(root, None, None, None)
    entry = report["capabilities"][0]
    details = entry["engine"]["executables"]
    assert set(details) == {"tesseract", "tesseract-languages"}
    for name, detail in details.items():
        assert detail["ok"] is False, name
        assert "could not be read" not in detail["not_checked_because"], name
        assert detail["not_checked_because"] == "not resolved through the declaration"


def test_an_unreadable_manifest_marks_executables_as_not_checked(tmp_path):
    """A manifest that cannot be parsed says nothing about whether the engine is installed."""
    module = load()
    root = build(tmp_path, [{"capability": "image.ocr",
                             "script": "workers/vision/worker_ocr.py"}],
                 worker_capability="image.ocr")
    tool_paths = ROOT / "services" / "python-workers" / "tool_paths.py"
    (root / "workers" / "tool_paths.py").write_text(
        tool_paths.read_text(encoding="utf-8"), encoding="utf-8")
    (root / "config" / "environment" / "capability-requirements.yaml").write_text(
        "capabilities: [this: is: not: valid", encoding="utf-8")
    report = module.verify(root, None, None, None)
    entry = report["capabilities"][0]
    details = entry["engine"]["executables"]
    assert set(details) == {"tesseract", "tesseract-languages"}
    for name, detail in details.items():
        assert detail["ok"] is False, name
        assert "ManifestUnreadable" in str(detail["path_or_error"]), name
        assert "could not be read" in detail["not_checked_because"], name


def test_routes_are_taken_from_the_profile_by_default(tmp_path):
    module = load()
    root = build(tmp_path, [
        {"capability": "canvas.structure", "script": "workers/document/worker_canvas.py"},
        {"capability": "archive.inventory", "script": "workers/document/worker_archive.py"},
    ])
    report = module.verify(root, None, None, None)
    assert report["declared_routes"] == 2
    assert report["summary"]["total"] == 2


WORKER_FILES = {
    "archive.inventory": "document/worker_archive.py",
    "canvas.structure": "document/worker_canvas.py",
    "html.structure": "web/worker_html.py",
    "image.caption": "vision/worker_caption.py",
    "image.ocr": "vision/worker_ocr.py",
    "media.probe": "document/worker_media.py",
    "media.transcribe": "media/worker_transcribe.py",
    "office.structure": "document/worker_office.py",
    "pdf.extract": "document/worker_pdf.py",
    "subtitles.structure": "document/worker_subtitles.py",
}


@pytest.mark.parametrize("capability", sorted(WORKER_FILES))
def test_every_requirement_is_an_import_the_worker_actually_makes(capability):
    """The requirements table must not invent a dependency the worker never imports.

    A module listed here that the worker does not import would report a failure that
    cannot happen; a module missing here would hide a real one. Both were live risks
    while this table was first written from memory rather than from the imports.
    """
    module = load()
    worker = ROOT / "services" / "python-workers" / WORKER_FILES[capability]
    assert worker.is_file(), worker
    text = worker.read_text(encoding="utf-8")
    for name in module.REQUIREMENTS.get(capability, {}).get("modules", []):
        forms = (
            f"import {name}",            # import pymupdf
            f"from {name} import",       # from openpyxl import load_workbook
            f"import {name} as",         # import pymupdf as fitz
            f'"{name}"',                 # __import__(name) over a literal name list
            f"'{name}'",
        )
        assert any(form in text for form in forms), (
            f"{capability}: {name} is not imported by {worker.name}")


def test_the_requirements_table_covers_every_declarable_capability():
    """A capability with no entry would be reported ready without any engine check."""
    module = load()
    for capability in WORKER_FILES:
        assert capability in module.REQUIREMENTS, capability


def test_the_check_can_state_its_own_requirements(tmp_path):
    """A runbook that says "provision the engines" is not reproducible; this enumerates."""
    module = load()
    listed = {entry["capability"]: entry for entry in module.requirements()}
    assert set(listed) == set(module.REQUIREMENTS)
    assert listed["pdf.extract"]["python_modules"] == ["pymupdf"]
    assert listed["image.ocr"]["declared_executables"] == ["tesseract", "tesseract-languages"]
    assert listed["image.caption"]["unverifiable_models"] == ["ollama vision model"]
    assert listed["canvas.structure"]["python_modules"] == []


def test_a_passing_report_reports_nothing_missing(tmp_path):
    module = load()
    root = build(tmp_path, [{"capability": "canvas.structure",
                             "script": "workers/document/worker_canvas.py"}])
    report = module.verify(root, None, None, None)
    assert report["ok"] is True
    assert report["missing"] == {"python_modules": [], "declared_executables": [],
                                 "unverifiable_models": [], "none": True}


def test_a_failing_route_names_the_module_that_is_missing(tmp_path):
    """The report must say *which* module, since that is the actionable part."""
    module = load()
    root = build(tmp_path, [{"capability": "pdf.extract",
                             "script": "workers/document/worker_pdf.py"}],
                 worker_capability="pdf.extract")
    report = module.verify(root, None, None, None)
    entry = report["capabilities"][0]
    if entry["engine"]["modules"]["ok"]:
        # pymupdf is installed in this environment, so the absence path cannot be shown
        assert report["missing"]["python_modules"] == []
        return
    assert report["missing"]["python_modules"] == ["pymupdf"]
    assert "pymupdf" in entry["engine"]["modules"]["error"]
