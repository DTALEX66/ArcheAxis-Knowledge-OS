"""OCR language data must be chosen by whether it serves the language being read.

`_usable_tessdata` accepted any directory containing `*.traineddata`. An ambient
`TESSDATA_PREFIX` holding a few unrelated languages therefore qualified, the worker kept
it and passed no `--tessdata-dir`, and tesseract failed with

    Failed loading language 'eng'
    Tesseract couldn't load any languages!

for a language the declared data could have served. The check now requires the requested
language, and these tests pin the precedence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services" / "python-workers" / "vision" / "worker_ocr.py"

MANIFEST = """
capabilities:
  toolchains:
    - name: tesseract-languages
      external_paths: ["10-toolchains/scoop/apps/tesseract-languages/current"]
"""


def load():
    spec = importlib.util.spec_from_file_location("worker_ocr_tessdata", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def traineddata(directory: Path, languages: list[str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for language in languages:
        (directory / f"{language}.traineddata").write_bytes(b"stub")
    return directory


@pytest.fixture()
def layout(tmp_path, monkeypatch):
    """An ambient tessdata with only `deu`, and a declared one holding `eng`."""
    ambient = traineddata(tmp_path / "stale" / "tessdata", ["deu"])
    declared = traineddata(
        tmp_path / "external" / "10-toolchains" / "scoop" / "apps"
        / "tesseract-languages" / "current", ["eng", "deu"])
    manifest = tmp_path / "external" / "capability-requirements.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(tmp_path / "external"))
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(manifest))
    monkeypatch.setenv("TESSDATA_PREFIX", str(ambient))
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    return {"module": load(), "ambient": ambient, "declared": declared}


def test_ambient_data_without_the_language_yields_to_the_declared_data(layout):
    module = layout["module"]
    resolved = module._declared_tessdata("eng")
    assert resolved is not None
    assert resolved.resolve() == layout["declared"].resolve()


def test_ambient_data_that_serves_the_language_is_kept(layout):
    module = layout["module"]
    resolved = module._declared_tessdata("deu")
    assert resolved is not None
    assert resolved.resolve() == layout["ambient"].resolve()


def test_any_traineddata_is_not_enough(tmp_path, monkeypatch):
    """Directly: a directory with unrelated languages is not usable for another one."""
    module = load()
    monkeypatch.delenv("ARCHEAXIS_EXTERNAL_ROOT", raising=False)
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    directory = traineddata(tmp_path / "data", ["deu"])
    assert module._usable_tessdata(directory, "deu") == directory
    assert module._usable_tessdata(directory, "eng") is None
    assert module._usable_tessdata(directory) == directory, "no language keeps the broad check"


def test_an_unset_language_keeps_the_broad_check(tmp_path):
    module = load()
    directory = traineddata(tmp_path / "data", ["eng"])
    assert module._usable_tessdata(directory, None) == directory
    assert module._usable_tessdata(tmp_path / "absent", None) is None


def test_a_missing_declared_language_is_reported_as_unavailable(layout, monkeypatch):
    """If neither the ambient nor the declared data serves the language, say so."""
    module = layout["module"]
    monkeypatch.setenv("TESSDATA_PREFIX", str(layout["ambient"]))
    assert module._declared_tessdata("fra") is None
