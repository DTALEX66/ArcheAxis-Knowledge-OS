"""The seven-day forecast must be fed from the schedule the Core already returns.

`AaosReviewScheduleChart` accepted a `Schedule` list and had no way to receive one: the control
was declared without a name and nothing ever assigned the property, so `GET /api/v1/learning/items`
could return `next_review` for every item and the chart would still say the Core had not provided
a forecast. These assertions pin the wiring, not the pixels.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml"
CODE = ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs"


def test_the_forecast_chart_can_be_reached_from_code():
    xaml = XAML.read_text(encoding="utf-8")
    assert '<local:AaosReviewScheduleChart x:Name="ReviewScheduleChart"' in xaml


def test_the_forecast_is_bucketed_from_the_items_the_core_returned():
    code = CODE.read_text(encoding="utf-8")
    # the items response is the only source, so no new route is required for this surface
    assert '"/api/v1/learning/items"' in code
    assert 'item.TryGetProperty("next_review", out var dueAt)' in code
    assert "ReviewScheduleChart.Schedule = BuildReviewSchedule(scheduleDue);" in code
    # a stale forecast must not survive a reload
    assert "ReviewScheduleChart.Schedule = null;" in code


def test_the_bucketing_stays_inside_the_seven_day_window():
    code = CODE.read_text(encoding="utf-8")
    helper = code.split("private static IReadOnlyList<ReviewScheduleDay> BuildReviewSchedule", 1)[1]
    helper = helper.split("private async Task RefreshHomeRecentEvidenceAsync", 1)[0]
    assert "var counts = new int[7];" in helper
    assert "if (offset >= 0 && offset < counts.Length)" in helper
    # local days, because the axis the chart draws is local
    assert "due.ToLocalTime()" in helper
    assert "new ReviewScheduleDay(today.AddDays(offset), count)" in helper
