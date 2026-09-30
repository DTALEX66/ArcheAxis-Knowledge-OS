from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICON = ROOT / "apps" / "ArcheAxis.Desktop" / "Assets" / "aaos-app-icon.ico"


def test_windows_application_icon_uses_b10_aa_gradient_tile():
    icon = Image.open(ICON)
    assert icon.format == "ICO"
    assert {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)} <= icon.info["sizes"]

    image = icon.resize((256, 256)).convert("RGBA")
    assert image.getpixel((0, 0))[3] == 0
    tile = image.getpixel((128, 220))
    assert tile[3] > 240 and 40 < tile[0] < 180 and tile[1] > 130 and tile[2] < 180
    white_pixels = sum(1 for pixel in image.getdata() if pixel[0] > 235 and pixel[1] > 235 and pixel[2] > 235 and pixel[3] > 240)
    assert white_pixels > 150
