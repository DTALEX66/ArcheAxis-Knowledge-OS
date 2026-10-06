"""The OCR route's language and language data must be selectable, and declared.

The transport hardcoded `eng` and only passed a tessdata directory when the repository's
bundled copy existed. A Chinese page was therefore handed the English model and read as
noise, and the declared `tesseract-languages` entry was never consulted.

These tests pin the selection: the language comes from configuration, the directory is one
that actually holds that language, and the declared entry is a candidate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = ROOT / "services" / "python-workers" / "transport" / "text_ndjson.py"

MANIFEST = """
capabilities:
  toolchains:
    - name: tesseract-languages
      external_paths: ["10-toolchains/scoop/apps/tesseract-languages/current"]
"""


def load():
    spec = importlib.util.spec_from_file_location("transport_lang", TRANSPORT)
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
def declared(tmp_path, monkeypatch):
    """A declared language pack holding chi_sim, and nothing bundled in the repo."""
    pack = traineddata(
        tmp_path / "external" / "10-toolchains" / "scoop" / "apps"
        / "tesseract-languages" / "current", ["chi_sim", "eng"])
    manifest = tmp_path / "external" / "capability-requirements.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_ROOT", str(tmp_path / "external"))
    monkeypatch.delenv("OS_EXTERNAL_CONFIG", raising=False)
    monkeypatch.setenv("ARCHEAXIS_CAPABILITY_MANIFEST", str(manifest))
    monkeypatch.delenv("ARCHEAXIS_OCR_LANG", raising=False)
    monkeypatch.delenv("ARCHEAXIS_OCR_TESSDATA", raising=False)
    return {"module": load(), "pack": pack}


def test_the_language_defaults_to_eng_and_is_configurable(declared, monkeypatch):
    module = declared["module"]
    assert module._ocr_language() == "eng"
    monkeypatch.setenv("ARCHEAXIS_OCR_LANG", "chi_sim")
    assert module._ocr_language() == "chi_sim"
    monkeypatch.setenv("ARCHEAXIS_OCR_LANG", "   ")
    assert module._ocr_language() == "eng", "blank configuration falls back to the default"


def test_language_data_is_taken_from_the_declared_entry(declared):
    module = declared["module"]
    resolved = module._ocr_tessdata("chi_sim")
    assert resolved is not None
    assert resolved.resolve() == declared["pack"].resolve()


def test_a_directory_without_the_language_is_not_used(declared, monkeypatch):
    module = declared["module"]
    wrong = traineddata(declared["pack"].parent.parent / "other", ["deu"])
    monkeypatch.setenv("ARCHEAXIS_OCR_TESSDATA", str(wrong))
    resolved = module._ocr_tessdata("chi_sim")
    assert resolved is not None
    assert resolved.resolve() == declared["pack"].resolve(), "the declared pack still wins"


def test_an_explicit_directory_is_used_when_it_serves_the_language(declared, monkeypatch):
    module = declared["module"]
    explicit = traineddata(declared["pack"].parent.parent / "explicit", ["chi_sim"])
    monkeypatch.setenv("ARCHEAXIS_OCR_TESSDATA", str(explicit))
    assert module._ocr_tessdata("chi_sim").resolve() == explicit.resolve()


def test_no_candidate_is_reported_as_none_not_as_a_wrong_directory(declared):
    module = declared["module"]
    assert module._ocr_tessdata("fra") is None
