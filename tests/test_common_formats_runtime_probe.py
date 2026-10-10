"""Actual local parser tests plus probe gate negative controls; not candidate Core qualification."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def probe(monkeypatch):
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    load("aaos01_office_runtime_loop", ROOT / "scripts/probes/aaos01_office_runtime_loop.py")
    result = load("common_formats_probe", ROOT / "scripts/probes/aaos01_common_formats_runtime_loop.py")
    result.load_worker = load
    return result


@pytest.fixture
def materials(probe, tmp_path):
    directory = tmp_path / "materials"
    result = subprocess.run([sys.executable, "-B", "-I", "-c", probe.GENERATOR, str(directory)],
                            capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stderr
    return directory


def snapshot(result):
    loss = copy.deepcopy(result["loss_receipt"])
    if loss["engine"] != "pymupdf-native-pdf":
        loss["params"]["worker_structure"] = result["structure"]
    loss.setdefault("losses", [])
    outputs = {"text": result["text"], "document_structure": json.dumps(result["structure"]),
               "loss_report": json.dumps(loss)}
    return {"job": {"status": 200, "body": {"state": "succeeded", "attempt": 1}},
            "quality": {"status": 200, "body": {}},
            **{key: {"status": 200, "body": {"content": value,
                                             "metadata": {"sha256": hashlib.sha256(value.encode()).hexdigest(),
                                                          "byte_length": len(value.encode())}}}
               for key, value in outputs.items()}}


@pytest.mark.parametrize("extension", ["docx", "xlsx", "pptx", "pdf"])
def test_generated_chinese_composite_files_are_actual_content_not_header_metadata(probe, materials, extension):
    script = "worker_pdf.py" if extension == "pdf" else "worker_office.py"
    worker = probe.load_worker("actual_common_" + extension, ROOT / "services/python-workers/document" / script)
    result = worker.extract(str(materials / f"complex.{extension}"))
    text, loss, positions = probe.validate_outputs(extension, snapshot(result))
    assert "中文" in text and len(positions) >= 2
    bad = snapshot(result)
    bad["text"]["body"]["metadata"]["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        probe.validate_outputs(extension, bad)
    bad = snapshot(result)
    bad["job"]["body"]["state"] = "failed"
    with pytest.raises(AssertionError):
        probe.validate_outputs(extension, bad)


def test_location_gate_binds_actual_span_and_refuses_stale_resolution(probe):
    sample = {"text": {"body": {"content": "中文正文"}}, "job": {"body": {"attempt": 1}}}
    source = {"source_id": "source", "sha256": "a" * 64}
    calls = []

    def call(method, path, body=None, expected=200):
        calls.append((method, path, body, expected))
        if method == "POST" and expected == 201:
            assert body["checksum"] == hashlib.sha256("中文".encode()).hexdigest()
            assert json.loads(body["position"])["job_id"] == "job"
            return {"anchor_id": "anchor", "location_status": "located"}
        if method == "POST":
            assert expected == 400 and body["checksum"] == "0" * 64
            return {}
        return {"status": "STALE", "scope": "locator_provenance_only"}

    with pytest.raises(AssertionError):
        probe.create_location(call, source, "job", sample,
                              {"char_start": 0, "char_end": 2, "kind": "paragraph", "path": ["paragraph-1"]})
    assert len(calls) == 3


def test_pdf_location_uses_canonical_page_line_span_and_structure_result_digest(probe):
    sample = {"text": {"body": {"content": "第一页\n第二页"}}, "job": {"body": {"attempt": 1}},
              "document_structure": {"body": {"metadata": {"sha256": "b" * 64}}}}
    source = {"source_id": "pdf-source", "sha256": "a" * 64}
    created = []

    def call(method, path, body=None, expected=200):
        if method == "POST" and expected == 201:
            locator = json.loads(body["position"])
            assert locator == {"type": "pdf_line", "job_id": "pdf-job", "attempt": 1, "kind": "line",
                               "path": ["page-2", "line-2"], "char_start": 4, "char_end": 7,
                               "result_sha256": "b" * 64}
            assert body["checksum"] == hashlib.sha256("第二页".encode()).hexdigest()
            created.append(body)
            return {"anchor_id": "pdf-anchor", "location_status": "located"}
        if method == "POST":
            assert expected == 400 and body["checksum"] == "0" * 64
            return {}
        return {"status": "CURRENT", "scope": "locator_provenance_only"}

    result = probe.create_location(call, source, "pdf-job", sample,
                                   {"kind": "line", "path": ["page-2", "line-2"],
                                    "char_start": 4, "char_end": 7}, native_pdf=True)
    assert result["resolution"]["status"] == "CURRENT" and len(created) == 1


@pytest.mark.parametrize("changed", [False, True])
def test_simulated_receipt_finalization_rejects_source_change_after_success(probe, monkeypatch, tmp_path, changed):
    """Exercise main's final gate; simulated process setup is not Core qualification."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    identities = iter([(False, "initial"), (False, "changed" if changed else "initial")])
    dev = SimpleNamespace(
        layout=lambda root: {"run": tmp_path, "artifacts": artifacts},
        prepare=lambda paths: None,
        worktree_identity=lambda root: next(identities),
        git=lambda *args: "simulated-source-commit",
    )
    launcher = SimpleNamespace(load_profile=lambda path: {"python": sys.executable}, stop=lambda child: None)
    modules = {"common_dev": dev, "common_launcher": launcher, "common_client": SimpleNamespace()}
    monkeypatch.setattr(probe.office, "load", lambda name, path: modules[name])
    monkeypatch.setattr(probe.office, "source_changes", lambda runtime: [])
    monkeypatch.setattr(probe.office, "identity", lambda path: {"sha256": "simulated-identity"})
    monkeypatch.setattr(probe.office, "start", lambda *args: (object(), "simulated-base", "unused", None))
    monkeypatch.setattr(probe, "FORMATS", ())
    monkeypatch.setattr(probe.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(sys, "argv", ["probe", "--candidate", str(tmp_path / "candidate")])

    status = probe.main()
    receipt = json.loads((artifacts / "common-formats.json").read_text(encoding="utf-8"))
    assert status == (1 if changed else 0)
    assert receipt["ok"] is (not changed)
    assert receipt["source_consistent"] is (not changed)
    if changed:
        assert receipt["qualification"] == "NOT_QUALIFIED_SOURCE_CHANGED_OR_UNVERIFIED"
