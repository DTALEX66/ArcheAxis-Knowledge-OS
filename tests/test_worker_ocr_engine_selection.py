"""OCR candidate discovery must measure usability before auto chooses an engine."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

WORKER = Path(__file__).resolve().parents[1] / "services/python-workers/vision/worker_ocr.py"


def load():
    spec = importlib.util.spec_from_file_location("ocr_engine_selection", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def isolated(monkeypatch):
    worker = load()
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    monkeypatch.setattr(worker, "_declared_path", lambda _name: None)
    monkeypatch.setattr(worker.shutil, "which", lambda _name: None)
    return worker


@pytest.mark.parametrize("command", ["missing-tesseract", "missing-bin/tesseract"])
def test_missing_relative_command_is_not_an_engine(isolated, monkeypatch, tmp_path, command):
    """Real subprocess lookup, with no replacement engine/declaration available."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TESSERACT_CMD", command)

    chosen, reason = isolated._choose_ocr_engine("auto", "eng")
    assert chosen == "rapidocr"
    assert "TESSERACT_CMD" in reason
    with pytest.raises(RuntimeError, match="configured TESSERACT_CMD"):
        isolated._choose_ocr_engine("tesseract", "eng")
    with pytest.raises(RuntimeError, match="rapidocr cannot serve language 'deu'"):
        isolated._choose_ocr_engine("auto", "deu")


@pytest.mark.parametrize("relative", [True, False])
def test_executable_from_the_wrong_product_is_not_tesseract(isolated, monkeypatch, relative):
    """Actually execute Python --version; running successfully is not enough."""
    command = os.path.relpath(sys.executable) if relative else sys.executable
    monkeypatch.setenv("TESSERACT_CMD", command)
    chosen, reason = isolated._choose_ocr_engine("auto", "eng")
    assert chosen == "rapidocr"
    assert "unusable" in reason


@pytest.mark.parametrize("relative", [True, False])
@pytest.mark.parametrize("probe_result", ["valid", "nonzero", "wrong-product", "timeout", "os-error"])
def test_every_existing_candidate_requires_a_bounded_identity_probe(
    isolated, monkeypatch, tmp_path, relative, probe_result
):
    """Controlled subprocess outcomes; these bytes are not a real executable."""
    binary = tmp_path / "bin" / "tesseract.exe"
    binary.parent.mkdir()
    binary.write_bytes(b"controlled executable identity fixture")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TESSERACT_CMD", str(binary.relative_to(tmp_path) if relative else binary))
    commands = []

    def run(command, **kwargs):
        commands.append((command, kwargs))
        if probe_result == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if probe_result == "os-error":
            raise OSError("cannot execute fixture")
        return subprocess.CompletedProcess(
            command, 2 if probe_result == "nonzero" else 0,
            "other-product 1.0" if probe_result == "wrong-product" else "tesseract 5.5.0", ""
        )

    monkeypatch.setattr(isolated, "_run", run)
    chosen, reason = isolated._choose_ocr_engine("auto", "eng")
    assert chosen == ("tesseract" if probe_result == "valid" else "rapidocr")
    assert (reason is None) is (probe_result == "valid")
    assert commands, "relative paths must not bypass the identity probe"
    assert all(command == [str(binary.resolve()), "--version"] for command, _ in commands)
    assert all(kwargs["timeout"] == 5 for _, kwargs in commands)
    assert all(not kwargs.get("shell", False) for _, kwargs in commands)


def test_stale_override_can_use_a_verified_declared_tesseract(isolated, monkeypatch, tmp_path):
    """Discovery precedence is retained, with validation at the declared fallback."""
    binary = tmp_path / "declared-tesseract.exe"
    binary.write_bytes(b"controlled executable identity fixture")
    monkeypatch.setenv("TESSERACT_CMD", "missing-bin/tesseract")
    monkeypatch.setattr(isolated, "_declared_path", lambda _name: str(binary))
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "tesseract 5.5.0", "")

    monkeypatch.setattr(isolated, "_run", run)
    assert isolated._tesseract() == str(binary.resolve())
    assert calls == [[str(binary.resolve()), "--version"]]


def test_real_declared_tesseract_can_be_selected_by_a_relative_path(monkeypatch):
    """Positive control with the declared local executable, never installed/downloaded."""
    worker = load()
    binary = worker._declared_path("tesseract")
    if not binary:
        pytest.skip("no declared local Tesseract executable")
    relative = os.path.relpath(binary)
    monkeypatch.setenv("TESSERACT_CMD", relative)
    monkeypatch.setattr(worker, "_declared_path", lambda _name: None)
    monkeypatch.setattr(worker.shutil, "which", lambda _name: None)
    assert Path(worker._tesseract()).resolve() == Path(binary).resolve()


def test_identity_timeout_reaps_the_owned_process_before_fallback(isolated, monkeypatch):
    """A controlled long-running probe uses the real subprocess timeout/cleanup path."""
    monkeypatch.setenv("TESSERACT_CMD", sys.executable)
    real_run, real_popen = isolated._run, subprocess.Popen
    expected_command = [str(Path(sys.executable).resolve()), "--version"]
    children = []
    timeouts = []

    def popen(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    def slow_identity(command, **kwargs):
        assert command == expected_command
        assert kwargs["timeout"] == 5
        # Shorten this controlled child, without changing the production probe timeout.
        kwargs["timeout"] = 0.3
        try:
            return real_run([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        except subprocess.TimeoutExpired as error:
            timeouts.append(error)
            raise

    monkeypatch.setattr(isolated.subprocess, "Popen", popen)
    monkeypatch.setattr(isolated, "_run", slow_identity)
    chosen, reason = isolated._choose_ocr_engine("auto", "eng")
    assert chosen == "rapidocr" and reason
    assert len(timeouts) == 1, "fallback must follow the real child timeout"
    assert len(children) == 1
    assert children[0].poll() is not None, "timed-out owned probe must already be reaped"


@pytest.mark.parametrize("lines", [
    [("LEFT FIRST", 10, 10), ("LEFT SECOND", 10, 110),
     ("RIGHT FIRST", 400, 10), ("RIGHT SECOND", 400, 110)],
    [("ENGINE FIRST", 10, 200), ("ENGINE SECOND", 10, 10)],
])
def test_rapidocr_preserves_the_engine_sequence_and_reports_it(
    isolated, monkeypatch, tmp_path, lines
):
    """Synthetic line boxes expose geometric reordering; no inference/accuracy claim."""
    rows = [([[x, y], [x + 160, y], [x + 160, y + 40], [x, y + 40]], text, 0.99)
            for text, x, y in lines]
    monkeypatch.setattr(isolated, "_rapidocr_engine", lambda: lambda _image: (rows, None))
    monkeypatch.setattr(isolated, "_rapidocr_version", lambda: "controlled-line-box-fixture")
    sample = tmp_path / "line-box-fixture.png"
    sample.write_bytes(b"synthetic line-box engine input")

    out = isolated.extract(sample, "eng", engine="rapidocr")
    expected = [text for text, _, _ in lines]
    order = out["loss_receipt"]["params"]["reading_order"]
    assert out["text"].splitlines() == expected
    assert [word["text"] for word in out["words"]] == expected
    assert [region["text"] for region in out["loss_receipt"]["params"]["regions"]] == expected
    assert order["original_order"] is True
    assert order["applied"] is False
    assert order["differs_from_engine_order"] is False
    assert order["columns"] is None, "preserving engine order does not measure columns"
    for region in out["loss_receipt"]["params"]["regions"]:
        assert out["text"][region["char_start"]:region["char_end"]] == region["text"]
