import importlib.util
from pathlib import Path
import pytest


@pytest.mark.parametrize("format", ["srt", "vtt"])
@pytest.mark.parametrize(
    "fraction,expected", [("008", 8), ("080", 80), ("8", 800), ("08", 80), ("800", 800)]
)
def test_real_parse_preserves_fraction_digits(format, fraction, expected):
    spec = importlib.util.spec_from_file_location(
        "subtitle_worker",
        Path(__file__).resolve().parents[2]
        / "services/python-workers/document/worker_subtitles.py",
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    text = (
        f"1\n00:00:00,{fraction} --> 00:00:01,008\n原始句子\n"
        if format == "srt"
        else f"WEBVTT\n\n1\n00:00:00.{fraction} --> 00:00:01.008\n原始句子\n"
    )
    cue = (m._parse_srt(text) if format == "srt" else m._parse_vtt(text))[0]
    assert cue["offset_ms"] == expected
    assert cue["duration_ms"] == 1008 - expected
    assert cue["text"] == "原始句子"
