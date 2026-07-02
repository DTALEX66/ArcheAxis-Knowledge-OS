"""Tests for project scorer."""
from Inspiration_Research.project_radar.scoring.scorer import score_project


def test_score_qualifies():
    result = score_project(token_saving=4.0, efficiency_gain=3.0, risk_level="low")
    assert result.qualifies is True
    assert result.total > 0


def test_score_critical_blocked():
    result = score_project(token_saving=5.0, risk_level="critical")
    assert result.qualifies is False


def test_score_below_threshold():
    result = score_project(token_saving=1.0, efficiency_gain=1.0, risk_level="low")
    assert result.qualifies is False
