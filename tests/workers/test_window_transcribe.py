"""Windowed transcription primitives: hand-computed expectations, no model and no media file.

The point of these tests is the arithmetic and the honesty rules, not the engine: a window's cues
must land on the recording's timeline, a window that produced nothing must be reported missing, and
a duration that cannot be read must fail rather than default.
"""

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "window_transcribe", HERE / "services" / "python-workers" / "media" / "window_transcribe.py"
)
assert SPEC and SPEC.loader
window_transcribe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(window_transcribe)

FFMPEG_BANNER = (
    "ffmpeg version 7.1 Copyright (c) 2000-2024 the FFmpeg developers\n"
    "  Duration: 00:12:03.42, start: 0.000000, bitrate: 128 kb/s\n"
)


def test_duration_is_read_from_the_ffmpeg_banner():
    assert window_transcribe.parse_ffmpeg_duration_ms(FFMPEG_BANNER) == 723_420


def test_duration_shorter_than_a_second_keeps_its_milliseconds():
    assert window_transcribe.parse_ffmpeg_duration_ms("  Duration: 00:00:00.08, start:") == 80


def test_a_missing_duration_line_is_refused_rather_than_defaulted():
    with pytest.raises(ValueError):
        window_transcribe.parse_ffmpeg_duration_ms("ffmpeg version 7.1\n")


def test_window_command_seeks_before_input_and_pins_the_sample_rate():
    argv = window_transcribe.window_command("ffmpeg.exe", "in.mp3", 140_000, 280_000, "out.wav")
    assert argv[:4] == ["ffmpeg.exe", "-hide_banner", "-nostdin", "-ss"]
    assert argv[4] == "140.000" and argv[5] == "-t" and argv[6] == "140.000"
    assert "-ac" in argv and argv[argv.index("-ac") + 1] == "1"
    assert argv[argv.index("-ar") + 1] == "16000"
    assert argv[-1] == "out.wav"


def test_window_command_refuses_an_empty_range():
    with pytest.raises(ValueError):
        window_transcribe.window_command("ffmpeg", "in.mp3", 5_000, 5_000, "out.wav")


def test_offsets_move_a_later_window_onto_the_recording_timeline():
    shifted = window_transcribe.offset_cues([{"start_ms": 250, "end_ms": 1_000, "text": "a"}], 140_000)
    assert shifted == [{"start_ms": 140_250, "end_ms": 141_000, "text": "a"}]


def test_merge_reports_a_window_that_produced_nothing_as_missing():
    merged = window_transcribe.merge_windows(
        [
            {"index": 0, "start_ms": 0, "end_ms": 140_000, "status": "succeeded", "cues": [{"start_ms": 0, "end_ms": 500, "text": "first"}], "text": "first"},
            {"index": 1, "start_ms": 140_000, "end_ms": 280_000, "status": "failed", "cues": [], "text": ""},
        ],
        expected_total=2,
    )
    assert merged["status"] == "partial"
    assert merged["windows_missing"] == [1]
    assert merged["text"] == "first"
    assert merged["cues"] == [{"start_ms": 0, "end_ms": 500, "text": "first"}]
    assert "1" in merged["note"]


def test_merge_of_every_window_keeps_global_positions_and_reports_complete():
    merged = window_transcribe.merge_windows(
        [
            {"index": 0, "start_ms": 0, "end_ms": 140_000, "status": "succeeded", "cues": [{"start_ms": 1_000, "end_ms": 2_000, "text": "one"}], "text": "one"},
            {"index": 1, "start_ms": 140_000, "end_ms": 280_000, "status": "succeeded", "cues": [{"start_ms": 500, "end_ms": 900, "text": "two"}], "text": "two"},
        ],
        expected_total=2,
    )
    assert merged["status"] == "complete"
    assert merged["windows_missing"] == []
    assert [cue["start_ms"] for cue in merged["cues"]] == [1_000, 140_500]
    assert merged["text"] == "one\ntwo"


def test_merge_refuses_a_duplicated_window():
    window = {"index": 0, "start_ms": 0, "end_ms": 10, "status": "succeeded", "cues": [], "text": ""}
    with pytest.raises(ValueError):
        window_transcribe.merge_windows([window, dict(window)], expected_total=1)
