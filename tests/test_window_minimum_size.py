"""The window's declared minimum and the gate's narrowest viewport must not drift apart.

The formal Tauri host declared no `min_inner_size` while the recovery entry did, so the
product window could be dragged under the layout floor - at 520px the shell measures a
640px scrollWidth and 120px of the reading column sits outside the window. Pinning the
declaration here means dropping it, or widening the gap between what the app promises and
what the browser gate actually exercises, fails a test instead of being noticed by hand.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BUILDERS = {
    "formal host": ROOT / "src-tauri" / "src" / "main.rs",
    "recovery entry": ROOT / "desktop" / "src-tauri" / "src" / "lib.rs",
}
MIN_SIZE = re.compile(r"\.min_inner_size\(\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*\)")


def declared_minimum(path: Path) -> tuple[float, float]:
    source = path.read_text(encoding="utf-8")
    matches = MIN_SIZE.findall(source)
    assert matches, f"{path.name} builds a window without declaring .min_inner_size(...)"
    return float(matches[0][0]), float(matches[0][1])


def load_gate():
    spec = importlib.util.spec_from_file_location(
        "a0_for_minimum", ROOT / "scripts" / "a0_browser_smoke.py")
    assert spec and spec.loader
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)
    return gate


def test_both_window_builders_declare_a_minimum_size() -> None:
    for label, path in BUILDERS.items():
        assert path.is_file(), f"missing window source for the {label}: {path}"
        width, height = declared_minimum(path)
        assert 320 <= width <= 1600, f"{label} declares an implausible minimum width {width}"
        assert 240 <= height <= 1200, f"{label} declares an implausible minimum height {height}"


def test_the_formal_host_floor_matches_the_gate_narrowest_viewport() -> None:
    """The gate must exercise exactly the floor the window enforces: testing only wider
    sizes would leave the boundary unverified, and testing narrower ones measures a state
    the product refuses to render, which reads as a pass about nothing."""
    gate = load_gate()
    width, _height = declared_minimum(BUILDERS["formal host"])
    narrowest = min(entry[1] for entry in gate.DESKTOP_MATRIX)
    assert narrowest == width, (
        f"the window floor is {width}px but the browser gate's narrowest viewport is "
        f"{narrowest}px; one of them is wrong")
    assert any(entry[1] == width for entry in gate.DESKTOP_MATRIX)


def test_the_gate_measures_painted_overlap_not_bounding_boxes() -> None:
    """A geometry check that only looks at one strip cannot see the shell stacking, which is the
    failure the owner reported - and a check that compares raw rects calls every scrollable page
    broken, because a tall child keeps a rect that runs past its scroll container while painting
    nothing there."""
    source = (ROOT / "scripts" / "a0_browser_smoke.py").read_text(encoding="utf-8")
    for key in ("landmarkOverlaps", "clippedBands", "landmarkCount", "missingBands",
                "expectedBands", "unreachableBands"):
        assert key in source, f"the geometry probe no longer reports {key}"
    assert 'assert not geometry["landmarkOverlaps"]' in source
    assert 'assert not geometry["missingBands"]' in source
    assert 'assert not geometry["unreachableBands"]' in source
    # The two things that make the verdict mean something: the box is reduced by every clipping
    # ancestor before comparison, and the crossing point is hit-tested so a red names a real
    # painted element.
    assert "clipBox" in source and "overflowY" in source
    assert "elementFromPoint" in source
    # An empty overlap list proves nothing unless the landmark set it compared is the one the
    # caller declared, so the count is pinned to that set rather than to a bare minimum.
    assert 'assert geometry["landmarkCount"] == len(bands)' in source


def test_the_widest_component_is_measured_where_it_is_mounted() -> None:
    """`details.template-launcher` exists only on the canonical library surface, so requiring it
    on the fallback sweep asks for a component that page never renders - and omitting it leaves
    the one component likely to stack outside the non-stacking check entirely."""
    gate = load_gate()
    assert set(gate.CHROME_BANDS) == {"rail", "context", "center", "dock"}
    assert set(gate.LIBRARY_BANDS) == set(gate.CHROME_BANDS) | {"templates"}
    assert gate.LIBRARY_BANDS["templates"] == "details.template-launcher"
    assert "read_library_geometry" in (ROOT / "scripts" / "a0_browser_smoke.py").read_text(encoding="utf-8")


def test_the_library_geometry_sweep_reaches_the_window_floor() -> None:
    """Coverage of the host-only component has to extend to the same floor the window enforces,
    or the boundary is verified only on the pages that have no wide rows."""
    gate = load_gate()
    floor = declared_minimum(BUILDERS["formal host"])
    sizes = {entry[0]: (entry[1], entry[2]) for entry in gate.DESKTOP_MATRIX}
    sweeped = {label: sizes[label] for label in gate.LIBRARY_GEOMETRY_VIEWPORTS}
    assert sweeped, "the library geometry sweep covers no viewport in the matrix"
    assert (floor[0], floor[1]) in sweeped.values(), (
        f"the library surface is never measured at the window floor {floor}; "
        f"sweep covers {sorted(sweeped)}")
    assert all(label in sizes for label in gate.LIBRARY_GEOMETRY_VIEWPORTS), (
        f"a declared library viewport is not in DESKTOP_MATRIX: {gate.LIBRARY_GEOMETRY_VIEWPORTS}")
