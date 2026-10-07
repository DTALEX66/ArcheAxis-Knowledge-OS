"""The manifest must bind each engine and model to a named artifact, and the index must agree.

A row that names only a capability is the failure that keeps recurring here: the model is on disk, the
worker resolves through the declaration, and the capability is still reported missing - so "declared"
was never "bound". These two checks are host-independent on purpose: they compare what the manifest
declares against what the generated index records, so they gate the declaration rather than the
particular caches of this machine.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config" / "environment" / "capability-requirements.yaml"
INDEX = ROOT / "config" / "environment" / "external-resources-index.json"

BINDABLE_CATEGORIES = ("engines", "models")
# only what genuinely has no artifact to name is exempt: `uv` resolves from the interpreter's own
# scripts dir, WebView2 is a system runtime, and the desktop runtime row points inside the app
PATH_RESOLVED_NAMES = {"uv", "webview2-evergreen", "desktop-runtime-v1"}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _rows() -> list[dict]:
    document = _manifest()
    found = []
    for category, group in (document.get("capabilities") or {}).items():
        for entry in group or []:
            if isinstance(entry, dict):
                found.append({**entry, "category": category})
    return found


def _index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))


def test_every_engine_and_model_row_names_the_artifact_it_resolves_through() -> None:
    unbound = [
        f"{row['category']}/{row['name']}"
        for row in _rows()
        if row["category"] in BINDABLE_CATEGORIES
        and row["name"] not in PATH_RESOLVED_NAMES
        and not row.get("external_paths")
    ]
    assert not unbound, f"name-only rows are declared but not bound: {unbound}"


def test_the_generated_index_records_every_declared_path() -> None:
    index = _index()
    recorded = {row["name"]: {item["declared"] for item in row["external_paths"]} for row in index["entries"]}
    for row in _rows():
        declared = set(row.get("external_paths") or [])
        assert recorded.get(row["name"], set()) == declared, (
            f"{row['name']}: the index does not mirror the manifest"
        )


def test_the_index_builder_refuses_an_absolute_or_parent_traversing_declaration(tmp_path: Path) -> None:
    """A declaration is not allowed to name a location the runtime resolver cannot reach."""
    spec = importlib.util.spec_from_file_location(
        "build_external_resources_index", ROOT / "scripts" / "environment" / "build_external_resources_index.py"
    )
    assert spec and spec.loader
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    base = tmp_path / "external"
    (base / "10-toolchains").mkdir(parents=True)
    (base / "10-toolchains" / "tool.exe").write_bytes(b"MZ")
    assert builder.resolve(str(base / "outside.exe"), base) == ("", False), "an absolute declaration is refused"
    assert builder.resolve("../sibling/model", base) == ("", False), "a `..` declaration is refused"
    reached, exists = builder.resolve("10-toolchains/tool.exe", base)
    assert exists is True and Path(reached) == (base / "10-toolchains" / "tool.exe").resolve()
    assert builder.resolve("10-toolchains/missing.exe", base) == (
        str((base / "10-toolchains" / "missing.exe").resolve()), False), "a gap is recorded as MISSING, not as absent-by-assumption"
