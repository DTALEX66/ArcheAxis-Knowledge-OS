"""Computed color-mix values must retain normalized sRGB units and alpha."""
import pytest

from scripts.browser_color import composite


def test_color_mix_composites_identically_to_rgba():
    background = (32.0, 90.0, 155.0)
    assert composite("color(srgb 1 1 1 / 0.93)", background) == pytest.approx(
        composite("rgba(255, 255, 255, 0.93)", background)
    )
    assert composite("color(srgb 0.25 0.5 0.75)", (0.0, 0.0, 0.0)) == (63.75, 127.5, 191.25)
    assert composite("rgb(32, 90, 155)", background) == background


def test_unknown_color_space_is_not_silently_qualified():
    with pytest.raises(ValueError, match="unsupported"):
        composite("color(display-p3 1 1 1)", (0.0, 0.0, 0.0))
