"""Windowed transcription primitives: hand-computed expectations, no model and no media file.

The point of these tests is the arithmetic and the honesty rules, not the engine: a window's cues
must land on the recording's timeline, a window that produced nothing must be reported missing, and
a duration that cannot be read must fail rather than default.
"""

import importlib.util
import json
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


def plan_of(*ranges):
    return {
        "windows": [{"index": i, "start_ms": start, "end_ms": end, "audio_ms": end - start,
                     "estimated_ms": end - start} for i, (start, end) in enumerate(ranges)],
        "windows_total": len(ranges),
    }


def test_a_second_run_resumes_the_windows_that_already_succeeded(tmp_path):
    plan = plan_of((0, 1_000), (1_000, 2_000))
    calls: list[int] = []

    def per_window(window):
        calls.append(int(window["index"]))
        return {"status": "succeeded", "cues": [{"start_ms": 0, "end_ms": 500, "text": f"w{window['index']}"}],
                "text": f"w{window['index']}"}

    first = window_transcribe.run_windows(plan, per_window, staging=tmp_path)
    assert calls == [0, 1]
    assert first["windows_resumed"] == []
    assert first["status"] == "complete"

    calls.clear()
    second = window_transcribe.run_windows(plan, per_window, staging=tmp_path)
    assert calls == [], "a resumed window must not be transcribed again"
    assert second["windows_resumed"] == [0, 1]
    assert second["text"] == first["text"]


def test_a_failed_window_is_attempted_again_instead_of_being_cached_as_done(tmp_path):
    plan = plan_of((0, 1_000))
    attempts: list[int] = []

    def per_window(window):
        attempts.append(int(window["index"]))
        if len(attempts) == 1:
            raise RuntimeError("engine hiccup")
        return {"status": "succeeded", "cues": [], "text": "recovered"}

    first = window_transcribe.run_windows(plan, per_window, staging=tmp_path)
    assert first["status"] == "partial" and first["windows_missing"] == [0]
    second = window_transcribe.run_windows(plan, per_window, staging=tmp_path)
    assert attempts == [0, 0]
    assert second["status"] == "complete" and second["text"] == "recovered"


def test_one_broken_window_does_not_discard_the_others(tmp_path):
    plan = plan_of((0, 1_000), (1_000, 2_000))

    def per_window(window):
        if window["index"] == 0:
            raise ValueError("bad window")
        return {"status": "succeeded", "cues": [], "text": "second"}

    merged = window_transcribe.run_windows(plan, per_window, staging=tmp_path)
    assert merged["status"] == "partial"
    assert merged["windows_missing"] == [0]
    assert merged["text"] == "second"


def test_staging_leaves_no_temporary_file_behind(tmp_path):
    plan = plan_of((0, 1_000))
    window_transcribe.run_windows(
        plan,
        lambda window: {"status": "succeeded", "cues": [], "text": "x"},
        staging=tmp_path,
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == ["window-0000.json"]


def test_a_plan_that_disagrees_with_itself_is_refused():
    with pytest.raises(ValueError):
        window_transcribe.run_windows({"windows": [], "windows_total": 0}, lambda window: None)
    broken = plan_of((0, 1_000))
    broken["windows_total"] = 3
    with pytest.raises(ValueError):
        window_transcribe.run_windows(broken, lambda window: None)



def test_a_budget_stops_before_a_window_that_does_not_fit(tmp_path):
    """A bounded job stops between windows and says which windows it did not reach.

    Being killed mid-decode would leave the same windows on disk but with no statement about them,
    and a merge that cannot name what is missing is how a partial transcript gets presented as the
    whole recording.
    """
    plan = plan_of((0, 100_000), (100_000, 200_000), (200_000, 300_000))
    calls: list[int] = []
    now = [0.0]

    def clock():
        return now[0]

    def per_window(window):
        calls.append(int(window["index"]))
        now[0] += float(window["estimated_ms"]) / 1000  # a window really does take its estimate
        return {"status": "succeeded", "cues": [], "text": f"w{window['index']}"}

    # Each window estimates 100 s; after the first, only 50 s of a 150 s budget is left, so the
    # second window would not fit and must not be started.
    merged = window_transcribe.run_windows(plan, per_window, staging=tmp_path, budget_ms=150_000,
                                           clock=clock)
    assert calls == [0]
    assert merged["status"] == "partial"
    assert merged["windows_missing"] == [1, 2]
    assert merged["text"] == "w0"


def test_the_budget_never_prevents_the_first_window_from_running(tmp_path):
    plan = plan_of((0, 100_000), (100_000, 200_000))
    calls: list[int] = []

    def per_window(window):
        calls.append(int(window["index"]))
        return {"status": "succeeded", "cues": [], "text": "x"}

    merged = window_transcribe.run_windows(plan, per_window, staging=tmp_path, budget_ms=1)
    assert calls == [0], "a budget smaller than one window must still make progress"
    assert merged["windows_missing"] == [1]


def test_a_budget_does_not_stop_a_run_that_only_resumes(tmp_path):
    plan = plan_of((0, 100_000), (100_000, 200_000))
    for window in plan["windows"]:
        (tmp_path / f"window-{window['index']:04d}.json").write_text(
            json.dumps({"status": "succeeded", "cues": [], "text": "cached"}), encoding="utf-8")

    def per_window(window):  # pragma: no cover - must never be called
        raise AssertionError("a fully cached run must not decode anything")

    merged = window_transcribe.run_windows(plan, per_window, staging=tmp_path, budget_ms=1)
    assert merged["status"] == "complete"
    assert merged["windows_resumed"] == [0, 1]


def test_duration_probe_reads_the_files_own_banner():
    calls: list[list[str]] = []

    class Finished:
        returncode = 1  # ffmpeg exits non-zero when asked for no output; that is not the signal
        stderr = "  Duration: 00:12:03.42, start: 0.000000, bitrate: 88 kb/s\n"

    def run(command, **_kwargs):
        calls.append(list(command))
        return Finished()

    original = window_transcribe.subprocess.run
    window_transcribe.subprocess.run = run
    try:
        duration = window_transcribe.probe_duration_ms("ffmpeg.exe", "recording.mp3")
    finally:
        window_transcribe.subprocess.run = original
    assert duration == 723_420
    assert calls == [["ffmpeg.exe", "-hide_banner", "-nostdin", "-i", "recording.mp3"]]


def test_a_budget_stops_at_the_first_window_it_cannot_reach(tmp_path):
    """A bounded run advances from the start and does not skip ahead to a smaller later window.

    Skipping the middle of a recording to decode its tail would be progress of a confusing kind:
    the result would be partial either way, but the holes would be scattered instead of being the
    trailing windows the caller has not got to yet.
    """
    plan = plan_of((0, 100_000), (100_000, 200_000), (200_000, 210_000))
    calls: list[int] = []
    now = [0.0]

    def per_window(window):
        calls.append(int(window["index"]))
        now[0] += float(window["estimated_ms"]) / 1000
        return {"status": "succeeded", "cues": [], "text": f"w{window['index']}"}

    merged = window_transcribe.run_windows(plan, per_window, staging=tmp_path, budget_ms=150_000,
                                           clock=lambda: now[0])
    # Window 0 costs 100 s of a 150 s budget; window 1 would not fit, and the small window 2 is
    # therefore not decoded ahead of it.
    assert calls == [0]
    assert merged["windows_missing"] == [1, 2]
    assert merged["status"] == "partial"
