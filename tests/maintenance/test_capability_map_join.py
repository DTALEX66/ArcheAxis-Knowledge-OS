"""The capability directory, the worker manifest and this map must agree, from one id each.

The atlas owns capability_id and intent. The workers manifest owns which worker serves which
runtime capability. This map owns only the link, because the alternative - repeating a
capability's implementation state in two files - is how a project ends up with two answers to
"is this implemented" and no way to tell which one is current.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "docs" / "truth" / "CAPABILITY_ATLAS_V2.yaml"
MANIFEST = ROOT / "services" / "python-workers" / "routes.json"
MAP = ROOT / "config" / "capability-map.v1.json"
CORE_NATIVE = {"text.extract"}


def _map():
    return json.loads(MAP.read_text(encoding="utf-8"))


def _atlas_ids():
    text = ATLAS.read_text(encoding="utf-8")
    return re.findall(r"\n  - capability_id:\s*\"?(CAP-[0-9]+)\"?", text)


def _runtime_capabilities():
    return set(json.loads(MANIFEST.read_text(encoding="utf-8"))["routes"])


def test_the_map_schema_is_declared():
    data = _map()
    assert data["schema"] == "archeaxis.capability-map/v1"
    assert set(data["states"]) == {"worker_backed", "core_native", "not_implemented"}


def test_the_map_covers_the_atlas_exactly_once():
    atlas = _atlas_ids()
    assert atlas, "the capability atlas declares no ids"
    assert len(atlas) == len(set(atlas)), "a capability_id appears twice in the atlas"
    mapped = [entry["capability_id"] for entry in _map()["capabilities"]]
    assert len(mapped) == len(set(mapped)), "a capability_id appears twice in the map"
    assert set(mapped) == set(atlas), (
        f"the map and the atlas disagree: atlas-only {sorted(set(atlas) - set(mapped))}, "
        f"map-only {sorted(set(mapped) - set(atlas))}")


def test_no_runtime_capability_is_claimed_by_two_capabilities():
    claims: dict[str, str] = {}
    for entry in _map()["capabilities"]:
        for runtime in entry["runtime_capabilities"]:
            assert runtime not in claims, (
                f"{runtime} is claimed by both {claims[runtime]} and {entry['capability_id']}; "
                "one runtime capability belongs to exactly one approved capability")
            claims[runtime] = entry["capability_id"]
    known = _runtime_capabilities() | CORE_NATIVE
    unknown = sorted(set(claims) - known)
    assert not unknown, f"the map names runtime capabilities nothing declares: {unknown}"


def test_every_declared_worker_route_is_claimed_by_exactly_one_capability():
    claimed = {runtime for entry in _map()["capabilities"] for runtime in entry["runtime_capabilities"]}
    orphaned = sorted(_runtime_capabilities() - claimed)
    assert not orphaned, (
        f"these worker routes are declared but belong to no approved capability: {orphaned}; an "
        "unclaimed route is a capability nobody approved or a map that has gone stale")


def test_the_state_agrees_with_what_is_listed():
    for entry in _map()["capabilities"]:
        runtime = entry["runtime_capabilities"]
        state = entry["state"]
        assert state in ("worker_backed", "core_native", "not_implemented"), entry
        if state == "worker_backed":
            assert runtime, f"{entry['capability_id']} is worker_backed but names no route"
        else:
            assert not runtime, (
                f"{entry['capability_id']} is {state} but names {runtime}; a capability with a "
                "route is worker_backed, whatever else it may also be")
