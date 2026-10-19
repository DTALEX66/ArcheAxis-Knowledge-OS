"""The published route inventory and the router must not drift apart.

A UI calls the pairs docs/history/repository-consolidation-20261019/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md lists. If the
router stops serving one, the UI gets a 404 it cannot tell from a missing object; if the router
gains one, that surface has been reviewed by nobody. Both directions are checked here, from the
source rather than from either list.

Writing this test found a defect in the check itself worth recording: a first version matched
`.route(` with a single-line regex and reported two routes as unserved that are in fact
mounted, because several `.route(` calls in this repository span lines. The matcher now walks
balanced parentheses, and it separates unconditional mounts from conditional ones, because the
contract makes a claim about each: the inventory rows are the production surface, and
`/jobs/{id}/receipts` is deliberately absent from it.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "docs/history/repository-consolidation-20261019/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md"
API_SRC = REPO / "crates/archeaxis-api/src"
OPENAPI = REPO / "packages/contracts/v1/openapi-outline.yaml"

# Mounted only under a condition, or deliberately excluded from the production surface. Each
# entry says why, so removing the condition without revisiting this list fails the test.
KNOWN_CONDITIONAL = {
    ("POST", "/api/v1/jobs/:p/receipts"): (
        "mounted only when the router is built with manual_receipts=true, which the shipped "
        "binary never does; contract §6 documents it as absent and not to be called"
    ),
}


def normalise(path: str) -> str:
    path = path.strip().strip("`")
    path = re.sub(r"\{[^}]+\}", ":p", path)
    return re.sub(r":[A-Za-z_][A-Za-z0-9_]*", ":p", path)


def balanced_call(text: str, open_index: int) -> str:
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[open_index + 1 : index]
    return text[open_index + 1 :]


def served_routes() -> tuple[set, set]:
    """(unconditional, conditional) sets of (method, normalised path)."""
    unconditional: set = set()
    conditional: set = set()
    for source in sorted(API_SRC.rglob("*.rs")):
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"\.route\s*\(", text):
            args = balanced_call(text, match.end() - 1)
            path_match = re.search(r'"([^"]+)"', args)
            if not path_match:
                continue
            methods = {
                name.upper()
                for name in re.findall(r"\b(get|post|put|patch|delete)\s*\(", args)
            }
            line_start = text.rfind("\n", 0, match.start()) + 1
            prefix = text[:line_start]
            under_condition = bool(
                re.search(r"(if\s+[^\n{]*\{\s*\n\s*$|\bmatch\b[^\n{]*\{\s*\n\s*$)", prefix)
            )
            for method in methods:
                entry = (method, normalise(path_match.group(1)))
                (conditional if under_condition else unconditional).add(entry)
    return unconditional, conditional


def documented_routes() -> set:
    documented: set = set()
    for line in CONTRACT.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*(?:\d+|R\d+)\s*\|\s*`([A-Z]+)\s+([^`]+)`\s*\|", line)
        if match:
            path = match.group(2).split("?")[0].strip()
            documented.add((match.group(1), normalise(path)))
    return documented


def test_every_documented_route_is_served():
    unconditional, conditional = served_routes()
    documented = documented_routes()
    assert documented, "the inventory parsed as empty; the table format changed"
    unserved = sorted(documented - unconditional - set(KNOWN_CONDITIONAL))
    assert not unserved, (
        "the contract documents routes the router does not serve unconditionally, so a UI "
        f"following it would get an unexplainable 404: {unserved}")


def test_every_served_route_is_documented():
    unconditional, _conditional = served_routes()
    documented = documented_routes()
    undocumented = sorted(unconditional - documented)
    assert not undocumented, (
        f"the router serves routes the contract does not document: {undocumented}")


def test_the_conditional_exceptions_are_still_conditional():
    """A route that became unconditional must leave this list, or the note goes stale."""
    unconditional, conditional = served_routes()
    for entry, reason in KNOWN_CONDITIONAL.items():
        assert entry in conditional, f"{entry} is no longer a conditional mount ({reason})"
        assert entry not in unconditional, f"{entry} is now served unconditionally"
    assert reason  # the reason is part of the record, not decoration


def test_the_inventory_is_the_size_the_contract_claims():
    """The production inventory includes the two local-human handoff read method/path additions."""
    assert len(documented_routes()) == 120, (
        "the inventory size changed; update §3's heading and this expectation together")


def test_handoff_reads_openapi_bind_strict_context_and_exact_response_schemas():
    """New local-human read mounts must expose their actual bounded DTO, not a generic POST."""
    import copy
    import json
    import yaml
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    outline = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    base_path = REPO / "packages/contracts/v2/project-handoff.schema.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    registry = Registry().with_resource(base_path.as_uri(), Resource.from_contents(base))
    cases = json.loads(base_path.with_name("project-handoff.cases.json").read_text(encoding="utf-8"))
    context = next(case["value"] for case in cases if case["name"] == "valid_context")
    non_context = [case["value"] for case in cases if case["schema_valid"] and case["value"]["payload"]["kind"] != "context"]
    assert non_context, "positive non-context fixtures are required to check the endpoint restriction"
    unconditional, _ = served_routes()
    for kind in ("preview", "snapshot"):
        path = f"/api/v1/project-handoff/{kind}"
        assert ("POST", path) in unconditional
        assert ("POST", path) in documented_routes()
        item = outline["paths"][path]
        assert set(item) == {"post"}
        operation = item["post"]
        assert operation["x-allowed-actor"] == "human"
        assert operation["x-max-request-bytes"] == 65536
        request = operation["requestBody"]["content"]["application/json"]["schema"]
        assert request["allOf"][0] == {"$ref": "../v2/project-handoff.schema.json"}
        validation_schema = copy.deepcopy(request)
        validation_schema["allOf"][0]["$ref"] = base_path.as_uri()
        validator = Draft202012Validator(validation_schema, registry=registry)
        assert validator.is_valid(context)
        for value in non_context:
            assert not validator.is_valid(value), value["payload"]["kind"]
        malformed = copy.deepcopy(context)
        malformed["unregistered"] = "must reject"
        assert not validator.is_valid(malformed)
        response = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert response == {"$ref": f"../v2/project-handoff-{kind}.schema.json"}
        schema = json.loads(base_path.with_name(f"project-handoff-{kind}.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["properties"]["grants_execution"] == {"const": False}
        assert schema["properties"]["grants_knowledge_acceptance"] == {"const": False}
        assert {"400", "401", "403", "409", "413", "503"} <= set(operation["responses"])
        assert ("404" in operation["responses"]) == (kind == "snapshot")
