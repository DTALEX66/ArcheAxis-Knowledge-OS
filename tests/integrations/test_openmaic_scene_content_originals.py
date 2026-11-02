"""Offline source identity checks; this selection is not a runnable provider."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "services/learning-providers/openmaic/vendor/scene-content-0.3.28-original"
ARCHIVE = ROOT / ".project-local/archives/owner-inputs/20261101-learning-platform-sources/OpenMAIC-1.3.0.zip"
ARCHIVE_SHA = "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40"
PREFIX = "OpenMAIC-1.3.0/packages/@openmaic/"
MANIFEST_SHA = {
    "SOURCE.json": "63c019fafbd68d869b8812c80961e5c9f3e0b1b64edd4564752273aeb0a4d159",
    "generation/ORIGINALS.json": "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3",
    "dsl/ORIGINALS.json": "c7564a5741c0807834ebcf77779a50590b927fa8b7e93f49494d1ef8eac6c317",
    "geometry/ORIGINALS.json": "07c0ce415204aff5074fb3c74f6bd4f12e80bd4af0f919def3f715aede048f01",
}
VERSIONS = {"generation": "0.3.28", "dsl": "0.12.0", "geometry": "0.1.0"}
LICENSE_SHA = "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(relative: str) -> dict:
    raw = (VENDOR / relative).read_bytes().replace(b"\r\n", b"\n")
    assert sha(raw) == MANIFEST_SHA[relative]
    return json.loads(raw)


def test_fixed_manifests_and_all_retained_members_are_self_contained():
    source = manifest("SOURCE.json")
    assert source["schema"] == "archeaxis.openmaic-scene-content-originals/v1"
    assert source["archive_sha256"] == ARCHIVE_SHA and source["scope"] == "SOURCE_ONLY_NOT_EXECUTABLE"
    assert (source["static_runtime_ts_count"], source["content_asset_count"],
            source["package_metadata_count"], source["member_count"]) == (46, 25, 9, 80)
    members = source["members"]
    assert isinstance(members, dict) and len(members) == 80
    catalog = {}
    for package, version in VERSIONS.items():
        record = manifest(f"{package}/ORIGINALS.json")
        assert record["archive_sha256"] == ARCHIVE_SHA and record["version"] == version
        assert record["license"] == "MIT" and record["source_prefix"] == f"{PREFIX}{package}/"
        for relative, identity in record["originals"].items():
            catalog[f"{package}/{relative}"] = identity
        metadata = json.loads((VENDOR / package / "package.json").read_bytes())
        assert metadata["name"] == f"@openmaic/{package}" and metadata["version"] == version
        assert metadata["license"] == "MIT" and sha((VENDOR / package / "LICENSE").read_bytes()) == LICENSE_SHA
    assert set(catalog) == set(members)
    for relative, expected in members.items():
        component = PurePosixPath(relative)
        assert not component.is_absolute() and ".." not in component.parts
        path = VENDOR.joinpath(*component.parts)
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert expected == {"archive_member": f"{PREFIX}{relative}", "bytes": len(data), "sha256": sha(data)}
        assert catalog[relative] == sha(data)
    actual = {p.relative_to(VENDOR).as_posix() for package in VERSIONS
              for p in (VENDOR / package).rglob("*") if p.is_file() and p.name != "ORIGINALS.json"}
    assert actual == set(members)


def test_static_runtime_import_graph_is_present_without_claiming_type_or_build_closure():
    source = manifest("SOURCE.json")
    members = source["members"]
    ts_members = {name for name in members if "/src/" in name and name.endswith(".ts")}
    assert len(ts_members) == 46
    imports = re.compile(
        r"""(?ms)^\s*(?:import|export)\s+(?!type\b)(?:\{[^;]*?\}|\*[^;]*?|[\w$]+(?:\s*,\s*\{[^;]*?\})?)\s+from\s+["'](?P<path>[^"']+)["']\s*;|^\s*import\s+["'](?P<side>[^"']+)["']\s*;"""
    )
    pending, seen, external = ["generation/src/scene-generator.ts"], set(), set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        assert current in ts_members
        seen.add(current)
        text = VENDOR.joinpath(*PurePosixPath(current).parts).read_text(encoding="utf-8")
        for match in imports.finditer(text):
            target = match.group("path") or match.group("side")
            if target.startswith("."):
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(current), target))
                if resolved.endswith(".js"):
                    resolved = resolved[:-3] + ".ts"
                assert resolved in ts_members, (current, target)
                pending.append(resolved)
            elif target == "@openmaic/dsl":
                pending.append("dsl/src/index.ts")
            elif target == "@openmaic/geometry":
                pending.append("geometry/src/index.ts")
            else:
                external.add(target)
    assert seen == ts_members
    assert external == {"entities", "es-module-lexer/js", "jsonrepair", "katex", "nanoid", "parse5",
                        "partial-json", "postcss", "postcss-value-parser", "svg-pathdata", "tinycolor2",
                        "node:fs", "node:path", "node:url", "node:vm"}
    # These omitted type-only sources are needed by a full original tsc build;
    # graph presence is deliberately not a claim that this tree can execute.
    assert "import type" in (VENDOR / "generation/src/scene-generator.ts").read_text(encoding="utf-8")
    assert not (VENDOR / "generation/src/scene-types.ts").exists()
    assert not (VENDOR / "generation/src/pipeline-types.ts").exists()


def test_selected_content_assets_cover_declared_direct_template_references():
    source = manifest("SOURCE.json")
    names = set(source["members"])
    templates = {name for name in names if name.startswith("generation/templates/")}
    snippets = {name for name in names if name.startswith("generation/snippets/")}
    pbl = {name for name in names if name.startswith("generation/prompts-pbl/")}
    assert (len(templates), len(snippets), len(pbl)) == (16, 7, 2)
    references = set()
    for relative in templates:
        text = VENDOR.joinpath(*PurePosixPath(relative).parts).read_text(encoding="utf-8")
        references.update(re.findall(r"\{\{snippet:([\w-]+)\}\}", text))
    assert snippets == {f"generation/snippets/{name}.md" for name in references}
    assert pbl == {"generation/prompts-pbl/planner-single-call-system.md",
                   "generation/prompts-pbl/planner-scenario-single-call-system.md"}
    assert not (VENDOR / "generation/prompts-pbl/planner-system.md").exists()


def test_local_owner_zip_members_match_original_bytes_when_archive_is_available():
    if not ARCHIVE.is_file():
        pytest.skip("ignored Owner ZIP is unavailable in this checkout")
    assert sha(ARCHIVE.read_bytes()) == ARCHIVE_SHA, "registered Owner ZIP identity differs"
    members = manifest("SOURCE.json")["members"]
    with zipfile.ZipFile(ARCHIVE) as archive:
        counts = Counter(info.filename for info in archive.infolist())
        for relative, identity in members.items():
            member = identity["archive_member"]
            assert counts[member] == 1
            original = archive.read(member)
            assert len(original) == identity["bytes"] and sha(original) == identity["sha256"]
            assert VENDOR.joinpath(*PurePosixPath(relative).parts).read_bytes() == original
