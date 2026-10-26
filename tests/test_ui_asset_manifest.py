"""The current UI asset manifest must describe the files that are actually on disk.

Until now nothing read that manifest, so it could keep certifying bytes an earlier round shipped -
the same disease as an unverified receipt. Every claim this test checks is recomputed from the file
it names, and the superseded list is checked the other way round: an asset the manifest says was
replaced must not still be imported by the product.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "current" / "AAOS-UI-ASSET-MANIFEST-20261007.json"
THEME_SOURCE = ROOT / "frontend" / "src" / "design-system" / "theme.ts"
ASSET_IMPORT = re.compile(r'import\s+\w+\s+from\s+"(\.\./assets/[^"]+)"')


def manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_every_manifest_item_matches_the_file_it_names() -> None:
    data = manifest()
    items = data["items"]
    assert isinstance(items, list) and items, "the manifest lists no assets at all"
    drift = []
    for item in items:
        path = ROOT / item["path"]
        if not path.is_file():
            drift.append(f"{item['path']}: missing")
            continue
        blob = path.read_bytes()
        if len(blob) != item["bytes"]:
            drift.append(f"{item['path']}: {item['bytes']} bytes claimed, {len(blob)} present")
        if hashlib.sha256(blob).hexdigest() != item["sha256"]:
            drift.append(f"{item['path']}: sha256 does not match the file")
    assert not drift, drift


def test_the_theme_registry_imports_exactly_the_brand_assets_the_manifest_certifies() -> None:
    imports = {
        (THEME_SOURCE.parent / relative).resolve().relative_to(ROOT).as_posix()
        for relative in ASSET_IMPORT.findall(THEME_SOURCE.read_text(encoding="utf-8"))
    }
    certified = {item["path"] for item in manifest()["items"] if "brand-mark-" in item["path"]}
    assert imports == certified, (sorted(imports), sorted(certified))


def test_a_superseded_asset_is_not_still_referenced_by_the_product() -> None:
    """The manifest's own history claim is only honest if the replaced file really left the surface."""
    retired = [item["path"] for item in manifest().get("superseded", [])]
    assert retired, "the manifest records no superseded asset, so this check is guarding nothing"
    sources = list((ROOT / "frontend" / "src").rglob("*.ts*"))
    hits = [
        f"{path.name} still references {retired_path}"
        for retired_path in retired
        for path in sources
        if Path(retired_path).name in path.read_text(encoding="utf-8")
    ]
    assert not hits, hits


def test_the_logo_master_is_recorded_by_hash_because_the_file_is_not_repo_owned() -> None:
    """The owner's 4K sheet is a personal asset outside the repository, so the manifest certifies
    which bytes the cut-out came from without importing them - and this test refuses a blank."""
    master = manifest().get("logo_master")
    assert isinstance(master, dict), "the manifest does not say which master the marks were cut from"
    assert re.fullmatch(r"[0-9a-f]{64}", master["sha256"]), master
    assert master["bytes"] > 0 and master["emblem_master_canvas"][0] > 0


def test_native_icon_dimensions_and_all_ico_frames_match_current_png() -> None:
    items = {item["path"]: item for item in manifest()["items"]}
    png_path, ico_path, svg_path = ("src-tauri/icons/icon." + suffix for suffix in ("png", "ico", "svg"))
    with Image.open(ROOT / png_path) as source, Image.open(ROOT / ico_path) as icon:
        source.load()
        assert list(source.size) == items[png_path]["canvas"]
        frames = sorted(icon.ico.sizes())
        assert [list(size) for size in frames] == items[ico_path]["frames"]
        assert frames == [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        for size in frames:
            actual = icon.ico.getimage(size).convert("RGBA")
            expected = source.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
            assert ImageChops.difference(actual, expected).getbbox(alpha_only=False) is None, size
    vector = ET.parse(ROOT / svg_path).getroot()
    assert [int(vector.attrib[axis]) for axis in ("width", "height")] == items[svg_path]["canvas"]
