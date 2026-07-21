"""Generate deterministic ArcheAxis desktop icons with Pillow."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / "src-tauri" / "icons"
CANVAS = 1024


def _render(size: int) -> Image.Image:
    scale = 4
    extent = CANVAS * scale
    image = Image.new("RGBA", (extent, extent), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(value * scale for value in values)

    def points(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(x * scale, y * scale) for x, y in values]

    draw.rounded_rectangle(box((36, 36, 988, 988)), radius=224 * scale, fill="#170a29")
    draw.ellipse(box((164, 164, 860, 860)), outline="#63309a", width=34 * scale)
    draw.ellipse(box((116, 352, 908, 672)), outline="#b56cf2", width=28 * scale)

    gem = points([(512, 132), (748, 406), (512, 900), (276, 406)])
    draw.polygon(gem, fill="#6d28d9", outline="#ead7ff", width=16 * scale)
    draw.polygon(points([(276, 406), (512, 132), (512, 340)]), fill="#c99af5")
    draw.polygon(points([(748, 406), (512, 132), (512, 340)]), fill="#8b5cf6")
    draw.polygon(points([(276, 406), (512, 340), (512, 900)]), fill="#7c3aed")
    draw.polygon(points([(748, 406), (512, 340), (512, 900)]), fill="#4c1d95")
    draw.line(points([(512, 132), (512, 900)]), fill="#f2e7ff", width=24 * scale)
    draw.ellipse(box((452, 452, 572, 572)), fill="#f7f1ff", outline="#a855f7", width=20 * scale)

    return image.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    icon_32 = _render(32)
    icon_128 = _render(128)
    icon_256 = _render(256)
    icon_32.save(ROOT / "32x32.png", optimize=True)
    icon_128.save(ROOT / "128x128.png", optimize=True)
    icon_256.save(ROOT / "128x128@2x.png", optimize=True)
    icon_256.save(
        ROOT / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"generated desktop icons in {ROOT}")


if __name__ == "__main__":
    main()
