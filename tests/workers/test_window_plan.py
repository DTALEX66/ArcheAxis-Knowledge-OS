"""Bounded window planning: hand-computed expectations, no engine and no file access.

The numbers asserted here are written out by hand from the declared policy
(ceiling 300 000 ms, overhead 20 000 ms, factor 2.0 -> 140 000 ms of audio per window),
so a change in the arithmetic has to be argued, not absorbed.
"""

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "window_plan", HERE / "services" / "python-workers" / "media" / "window_plan.py"
)
assert SPEC and SPEC.loader
window_plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(window_plan)


def test_policy_yields_a_140_second_window():
    assert window_plan.window_audio_ms() == 140_000


def test_short_media_is_one_window_and_is_expected_to_finish_whole():
    plan = window_plan.plan_windows(83_000)
    assert plan["windows_total"] == 1
    assert plan["recommended"] == "whole"
    assert plan["whole_exceeds_ceiling"] is False
    assert plan["whole_estimated_ms"] == 186_000
    assert plan["windows"][0] == {
        "index": 0, "start_ms": 0, "end_ms": 83_000, "audio_ms": 83_000, "estimated_ms": 186_000,
    }


def test_twelve_minutes_is_six_windows_and_must_be_split():
    plan = window_plan.plan_windows(720_000)
    assert plan["windows_total"] == 6
    assert plan["recommended"] == "split"
    assert plan["whole_exceeds_ceiling"] is True
    assert plan["whole_estimated_ms"] == 1_460_000
    assert [window["audio_ms"] for window in plan["windows"]] == [140_000] * 5 + [20_000]
    assert plan["windows"][-1]["end_ms"] == 720_000


def test_exact_multiple_does_not_emit_a_zero_length_tail():
    plan = window_plan.plan_windows(280_000)
    assert plan["windows_total"] == 2
    assert [window["audio_ms"] for window in plan["windows"]] == [140_000, 140_000]


def test_windows_cover_the_recording_exactly_once():
    plan = window_plan.plan_windows(1_000_000)
    cursor = 0
    for window in plan["windows"]:
        assert window["start_ms"] == cursor
        cursor = window["end_ms"]
    assert cursor == 1_000_000


def test_every_window_estimate_fits_the_ceiling_with_headroom():
    plan = window_plan.plan_windows(3_600_000)
    assert plan["windows_total"] == 26
    for window in plan["windows"]:
        assert window["estimated_ms"] <= window_plan.CEILING_MS
        assert window["estimated_ms"] <= 300_000


@pytest.mark.parametrize("duration", [0, -1])
def test_non_positive_duration_is_refused(duration):
    with pytest.raises(ValueError):
        window_plan.plan_windows(duration)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ceiling_ms": 0},
        {"overhead_ms": -1},
        {"realtime_factor": 0},
        {"ceiling_ms": 10_000, "overhead_ms": 20_000},
        {"ceiling_ms": 100, "overhead_ms": 0, "realtime_factor": 1000.0},
    ],
)
def test_policy_that_cannot_produce_a_window_is_refused(kwargs):
    with pytest.raises(ValueError):
        window_plan.window_audio_ms(**kwargs)
