"""The published route inventory and the router must not drift apart.

A UI calls the pairs docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md lists. If the
router stops serving one, the UI gets a 404 it cannot tell from a missing object; if the router
gains one, that surface has been reviewed by nobody. Both directions are checked here, from the
source rather than from either list.

Writing this test found a defect in the check itself worth recording: a first version matched
`.route(` with a single-line regex and reported two routes as unserved that are in fact
mounted, because several `.route(` calls in this repository span lines. The matcher now walks
balanced parentheses, and it separates unconditional mounts from conditional ones, because the
contract makes a claim about each: the thirty inventory rows are the production surface, and
`/jobs/{id}/receipts` is deliberately absent from it.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "docs/current/AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md"
API_SRC = REPO / "crates/archeaxis-api/src"

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
    """The production inventory includes the fourteen AAOS-01 method/path additions."""
    assert len(documented_routes()) == 88, (
        "the inventory size changed; update §3's heading and this expectation together")
