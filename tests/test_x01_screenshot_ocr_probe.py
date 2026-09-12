"""The screenshot probe must require every marker and use owned output paths."""

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('x01_probe', REPO / 'scripts/probes/x01_real_screenshot_ocr.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def _fake_capture(monkeypatch, text, destinations):
    original = probe._load_module

    def screenshot(url, path, **kwargs):
        destinations.append(path)
        path.write_bytes(b'synthetic screenshot fixture')
        return {'ok': True, 'engine': 'fixture'}

    monkeypatch.setattr(probe, '_load_module', lambda name, rel:
                        SimpleNamespace(screenshot_web=screenshot) if rel == 'app/ingestion/web_screenshot.py'
                        else original(name, rel))
    monkeypatch.setattr(probe, 'subprocess', SimpleNamespace(
        run=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps({'text': text})),
        CREATE_NO_WINDOW=0,
    ))


@pytest.mark.parametrize(('text', 'expected'), [
    ('ARCHEAXIS', 1), ('ARCHEAXIS OCR PROBE 1234', 1), ('ARCHEAXIS OCR PROBE 123', 0),
])
def test_probe_requires_all_complete_markers(tmp_path, monkeypatch, text, expected):
    _fake_capture(monkeypatch, text, [])
    monkeypatch.setattr(probe.sys, 'argv', [str(SPEC.origin), str(tmp_path)])
    assert probe.main() == expected


def test_default_output_does_not_fall_back_to_system_temp(tmp_path, monkeypatch):
    destinations = []
    _fake_capture(monkeypatch, 'ARCHEAXIS OCR PROBE 123', destinations)
    monkeypatch.setattr(probe, 'tempfile', SimpleNamespace(gettempdir=lambda: str(tmp_path)), raising=False)
    monkeypatch.setattr(probe.sys, 'argv', [str(SPEC.origin)])
    assert probe.main() == 0
    assert destinations[0].is_relative_to(Path(os.environ['ARCHEAXIS_RUN_ROOT']) / 'artifacts')
