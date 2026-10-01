from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XAML = (ROOT / "apps/ArcheAxis.Desktop/AaosReviewScheduleChart.axaml").read_text(encoding="utf-8")
CODE = (ROOT / "apps/ArcheAxis.Desktop/AaosReviewScheduleChart.axaml.cs").read_text(encoding="utf-8")


def test_review_schedule_empty_chart_keeps_theme_aware_plot_grid_and_date_axis() -> None:
    assert 'BorderBrush="{DynamicResource AaosBorderBrush}"' in XAML
    assert "TimelineAxis" in XAML
    assert "AxisDay0" in XAML and "AxisDay6" in XAML
    assert "AddDays(dayOffset)" in CODE
    assert 'Text="+1 天"' not in XAML


def test_review_schedule_draws_only_core_points_and_explains_missing_projection() -> None:
    assert "Core 未提供未来复习数量" in CODE
    assert "point.DueCount" in CODE
    assert "Core 未返回这一天的排程数量" in CODE
    assert "new ReviewScheduleDay" not in CODE


def test_review_schedule_chart_motion_respects_reduced_motion_setting() -> None:
    assert "AAOS_REDUCED_MOTION" in CODE
    assert "Dispatcher.UIThread.Post" in CODE
    assert "Opacity" in CODE
