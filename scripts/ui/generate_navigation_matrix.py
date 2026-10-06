"""Render the current AAOS entry matrix from the generated navigation projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "frontend/src/api/generated/capability-catalog.ts"
SPACES = ROOT / "frontend/src/spaces/spaces.ts"
NAVIGATION = ROOT / "frontend/src/presentation/navigation.ts"
TARGET = ROOT / "docs/current/AAOS-UI-CAPABILITY-ENTRY-MATRIX-20261007.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_body(source: str, marker: str) -> str:
    match = re.search(re.escape(marker) + r"[^=]*=\s*\{(.*?)\n\};", source, re.S)
    if not match:
        raise ValueError(f"cannot locate {marker}")
    return match.group(1)


def generate() -> dict[str, object]:
    catalog_source = CATALOG.read_text(encoding="utf-8")
    json_start = catalog_source.index("= {") + 2
    json_end = catalog_source.rindex(" as const;")
    catalog = json.loads(catalog_source[json_start:json_end].strip())
    spaces_source = SPACES.read_text(encoding="utf-8")
    spaces = [
        {"id": item[0], "label": item[1], "icon": item[2], "description": item[3],
         "route": f"#space={item[0]}", "menu_visible": True, "command_search_visible": True}
        for item in re.findall(
            r'\{ id: "([^"]+)", label: "([^"]+)", icon: "([^"]+)", description: "([^"]+)" \}',
            spaces_source,
        )
    ]
    if not spaces:
        raise ValueError("no product spaces found")

    navigation_source = NAVIGATION.read_text(encoding="utf-8")
    destination_text = object_body(navigation_source, "CAPABILITY_DESTINATIONS")
    destinations = dict(re.findall(r'"(CAP-[0-9]+)": "([a-z-]+)"', destination_text))
    legacy_text = object_body(navigation_source, "LEGACY_SPACE_ALIASES")
    aliases: dict[str, list[str]] = {}
    for alias, space_id in re.findall(r"([a-z][a-z-]*): \"([a-z-]+)\"", legacy_text):
        aliases.setdefault(space_id, []).append(alias)
    for space in spaces:
        space["legacy_aliases"] = sorted(aliases.get(str(space["id"]), []))

    legacy_owner: dict[str, str] = {}
    for item in catalog["entries"]:
        for alias in item["atlas"]["origin_requirement_ids"]:
            legacy_owner.setdefault(alias, item["atlas"]["capability_id"])

    entries = []
    for item in catalog["entries"]:
        atlas = item["atlas"]
        capability_id = atlas["capability_id"]
        implementation = item["implementation"]
        destination = destinations.get(capability_id)
        entries.append({
            "entry_id": capability_id,
            "label": atlas["canonical_name"],
            "group_id": atlas["product_layer"],
            "authority_status": atlas["authority_status"],
            "roadmap_state": atlas["roadmap_state"],
            "activation_horizon": atlas["activation_horizon"],
            "implementation_state": implementation["state"],
            "runtime_capabilities": implementation["runtime_capabilities"],
            "menu_visible": True,
            "command_search_visible": True,
            "detail_available": True,
            "route": f"#capability/{capability_id}",
            "legacy_aliases": [
                {"alias": alias, "resolves_to_entry_id": legacy_owner[alias],
                 "route": f"#capability={alias}", "owned_by_this_entry": legacy_owner[alias] == capability_id}
                for alias in atlas["origin_requirement_ids"]
            ],
            "scene_objects": atlas["objects"],
            "related_views": atlas["views"],
            "dependencies": atlas["dependencies"],
            "entry_gate": atlas["entry_gate"],
            "required_exit_evidence": atlas["exit_evidence"],
            "fallbacks": atlas["fallbacks"],
            "destination_space": destination,
            "execution_action": (
                "Open mapped AAOS product space"
                if destination and implementation["state"] != "not_implemented"
                else "Details only; no direct execution"
            ),
        })

    return {
        "schema": "aaos.ui.entry-matrix/v1",
        "date": "2026-10-07",
        "purpose": "Read-only UI projection; it is not a second capability authority or progress ledger.",
        "projection_contract": {
            "product_spaces": "SPACES -> SpaceRail + CommandPalette",
            "capabilities": "CAPABILITY_CATALOG -> SpaceRail + CanonicalCapabilitiesSpace + CommandPalette",
            "future_detail": "Every catalog capability can open its detail route; execution remains gated by implementation state and destination mapping.",
            "old_aliases": "Atlas origin_requirement_ids and legacy space aliases remain resolvable.",
        },
        "source_hashes": {
            "capability_catalog_ts_sha256": sha256(CATALOG),
            "spaces_ts_sha256": sha256(SPACES),
            "navigation_ts_sha256": sha256(NAVIGATION),
            "authority_sources": catalog["sources"],
        },
        "product_space_count": len(spaces),
        "capability_count": len(entries),
        "product_spaces": spaces,
        "capabilities": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(generate(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != rendered:
            raise SystemExit("navigation matrix is stale; regenerate it")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
