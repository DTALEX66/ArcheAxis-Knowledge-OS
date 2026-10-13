"""Composite computed CSS sRGB colors for browser accessibility checks."""
from __future__ import annotations

import re


def composite(color: str, background: tuple[float, ...]) -> tuple[float, ...]:
    normalized = color.strip().lower()
    if normalized.startswith("color(srgb "):
        body = normalized[len("color(srgb "):-1]
        channels, separator, opacity = body.partition("/")
        values = [float(value) * 255 for value in channels.split()]
        alpha = float(opacity.strip()) if separator else 1.0
    elif normalized.startswith(("rgb(", "rgba(")):
        numbers = [float(n) for n in re.findall(r"[\d.]+", normalized)]
        assert len(numbers) in (3, 4), color
        values = numbers[:3]
        alpha = numbers[3] if len(numbers) == 4 else 1.0
    else:
        raise ValueError("unsupported computed CSS color: " + color)
    assert len(values) == len(background) == 3 and 0 <= alpha <= 1, color
    return tuple(alpha * value + (1 - alpha) * base for value, base in zip(values, background))
