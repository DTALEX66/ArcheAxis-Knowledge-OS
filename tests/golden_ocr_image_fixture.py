"""Build the project-authored screenshot fixture used by the OCR golden test."""

from __future__ import annotations

from pathlib import Path


def write_golden_screenshot(destination: Path) -> None:
    """Write a synthetic, no-personal-data screenshot with an OCR truth marker."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1600, 520), "#f7f9fc")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 70, 1520, 450), radius=28, fill="#ffffff", outline="#cbd5e1", width=4)
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 72)
    subtitle = ImageFont.truetype("DejaVuSans.ttf", 32)
    draw.text((180, 175), "OCR GOLDEN ANCHOR", fill="#102a43", font=font)
    draw.text((184, 290), "Synthetic screenshot fixture - no personal data", fill="#486581", font=subtitle)
    image.save(destination, format="PNG", optimize=False)


if __name__ == "__main__":
    write_golden_screenshot(Path(__file__).resolve().parent / "fixtures" / "golden" / "golden-screenshot-ocr.png")
