"""The project contract must not name files that do not exist.

`PROJECT_CONTRACT.yaml` is the agent-facing contract: it declares the mandatory
owner journey and the schema/graph/registry files an agent is told to read. A
declared path that does not exist is a dangling instruction, and it was already
real: `delivery.mandatory_journey` pointed at `tests/journey/v01-owner-loop.yaml`
from 2026-09-04 while the file was absent.

The known-dangling set is pinned rather than filtered, so this test fails both
when a *new* reference breaks and when the recorded broken one is repaired
without updating the record. One entry remains escalated, not silently accepted:
the digest profile's value is duplicated as a JSON-Schema `const` in
`.project/schemas/task-graph.schema.json` and mirrored in `.project/TASK-GRAPH.yaml`,
so repointing it is a governance change (see the DSH completion report) rather
than a truth-document edit. The equivalent document already exists at
`docs/vnext-seed/operations/digest-canonicalization.md`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "PROJECT_CONTRACT.yaml"
PATH_SUFFIXES = (".json", ".yaml", ".yml", ".md", ".toml", ".py", ".cs", ".rs")

# key -> declared value. Escalated, not repaired here.
KNOWN_DANGLING = {
    "agent_protocol.digest_profile": "docs/operations/digest-canonicalization.md",
}


def _load_contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


def _declared_paths(node, key: str = ""):
    if isinstance(node, dict):
        for child_key, value in node.items():
            yield from _declared_paths(value, f"{key}.{child_key}" if key else child_key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _declared_paths(value, f"{key}[{index}]")
    elif isinstance(node, str) and node.endswith(PATH_SUFFIXES) and "<" not in node:
        # Values carrying <placeholders> are path templates for issued artefacts,
        # not required files that must already exist.
        yield key, node


def test_every_declared_contract_path_exists_or_is_recorded_as_dangling() -> None:
    declared = dict(_declared_paths(_load_contract()))
    missing = {
        key: value for key, value in declared.items() if not (ROOT / value).exists()
    }

    assert missing == KNOWN_DANGLING, (
        "a declared contract path is missing, or a recorded one was repaired without "
        "updating KNOWN_DANGLING and the escalation note"
    )


def test_the_mandatory_journey_reference_resolves() -> None:
    journey = _load_contract()["delivery"]["mandatory_journey"]

    assert (ROOT / journey).is_file(), "the contract's mandatory journey must be readable"


def test_the_declared_journey_registers_only_real_statuses_and_evidence() -> None:
    journey_path = ROOT / _load_contract()["delivery"]["mandatory_journey"]
    journey = yaml.safe_load(journey_path.read_text(encoding="utf-8"))

    assert journey["journey"] == "v01-owner-loop"
    assert journey["acceptance_status"] in {"IMPLEMENTED", "PARTIAL", "BLOCKED"}
    assert journey["acceptance_status"] == "BLOCKED", (
        "an executor may not record owner acceptance; Q00/Q01 are still blocked"
    )

    steps = journey["steps"]
    assert [step["id"] for step in steps] == ["import", "read", "anchor", "claim",
                                              "learn", "practice", "review", "distill",
                                              "recover"]
    for step in steps:
        assert step["status"] in {"IMPLEMENTED", "PARTIAL", "BLOCKED"}, step["id"]
        assert step["not_verified"].strip(), (
            f"step {step['id']} must state what is not claimed"
        )
        assert step["evidence"], f"step {step['id']} must cite tracked evidence"

    cited = [
        path
        for step in steps
        for path in step["evidence"]
    ] + list(journey["evidence_index"])
    absent = sorted(path for path in cited if not (ROOT / path).exists())
    assert absent == [], f"journey cites evidence that does not exist: {absent}"
