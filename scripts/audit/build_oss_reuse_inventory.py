"""Lossless crosswalk, not an installer or a capability dispatcher.

Keep each source row, including duplicates and pool-external runtimes/APIs.
Only reviewed explicit aliases match; a name or source hit never yields A/C.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

POOL = "docs/history/planning-blueprint-absorption/2026-09-29/package-unpacked/AAOS_OSS_RESEARCH_POOL_369_2026-08-11.csv"
REGISTRY = "inspiration_research/resources/open_source_project_registry.json"
ABSORPTION = "inspiration_research/resources/open_source_absorption_ledger.json"
SUPPLY = "docs/truth/SUPPLY_CHAIN_LEDGER.json"
CAPABILITIES = "docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml"
DISPOSITION = "docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json"


def normalize(name: str) -> str:
    name = name.strip().casefold().removeprefix("https://github.com/").rstrip("/")
    return name.removesuffix(".git")


def build(root: Path, decisions: dict, verification: dict | None = None) -> dict:
    verification = verification or {}
    aliases = {}
    for decision in decisions["decisions"]:
        for alias in [decision["canonical_name"], *decision.get("aliases", [])]:
            key = normalize(alias)
            if key in aliases and aliases[key] != decision:
                raise ValueError(f"ambiguous explicit alias: {alias}")
            aliases[key] = decision
    rows = []
    sources = {}

    def append(path, records, id_field, name_field, scope):
        raw = (root / path).read_bytes()
        sources[path] = {"sha256": hashlib.sha256(raw).hexdigest(), "row_count": len(records)}
        for index, original in enumerate(records, 1):
            name = original.get(name_field) or original.get("upstream_or_owner") or original.get("capability_name") or original.get("upstream_project") or "UNKNOWN"
            decision = aliases.get(normalize(name))
            category = "D"
            reason = "No qualified result or concrete extracted reference is recorded for this source row."
            value = original.get("note") or original.get("capability") or original.get("categories") or original.get("capability_name") or original.get("category") or name
            trigger = f"A real template needs {value}, and the current primary/fallback fails a representative input; review fixed revision, license and isolated cost first."
            evidence = []
            capability = None
            if decision:
                category = decision["category"]
                reason = decision["reason"]
                trigger = decision["reevaluate_when"]
                evidence = decision.get("evidence", [])
                capability = decision.get("capability_id")
                if category == "A":
                    raise ValueError("A must come from bound verification, not an audit decision")
                if category == "C" and not decision.get("reference_result"):
                    raise ValueError("C requires a concrete reference result")
                proof = verification.get("capabilities", {}).get(capability, {})
                if category == "B" and proof.get("status") == "PASS" and proof.get("level") in {"INTEGRATED", "REAL"}:
                    if not proof.get("entry") or not proof.get("assertions"):
                        raise ValueError("verification must name entry and result assertions")
                    category = "A"
                    evidence = [*evidence, proof]
            source_id = str(original.get(id_field) or f"row-{index:04d}")
            rows.append({"record_key": f"{scope}:{source_id}:{index}", "scope": scope,
                         "source_path": path, "source_row": index, "original_id": original.get(id_field),
                         "original_name": name, "original_record": original,
                         "canonical_name": decision["canonical_name"] if decision else normalize(name),
                         "match_basis": "explicit_reviewed_alias" if decision else "unmatched_preserved",
                         "category": category, "capability_id": capability, "reason": reason,
                         "value": value, "reevaluate_when": trigger, "evidence": evidence,
                         "reference_result": decision.get("reference_result") if decision else None,
                         "code_license": original.get("code_license") or original.get("license") or "UNVERIFIED",
                         "model_license": original.get("model_license", "UNVERIFIED_OR_NOT_APPLICABLE")})

    def read(path):
        return json.loads((root / path).read_text(encoding="utf-8"))

    with (root / POOL).open(encoding="utf-8-sig", newline="") as stream:
        append(POOL, list(csv.DictReader(stream)), "id", "candidate", "pool")
    append(REGISTRY, read(REGISTRY)["projects"], "project_id", "name", "registry")
    append(ABSORPTION, read(ABSORPTION)["projects"], "project_id", "name", "absorption-ledger")
    append(SUPPLY, read(SUPPLY)["components"], "id", "name", "supply-chain")
    append(CAPABILITIES, yaml.safe_load((root / CAPABILITIES).read_text(encoding="utf-8"))["entries"], "capability_id", "upstream_project", "capability-registry")
    disposition = read(DISPOSITION)
    archived = [*disposition["supply_chain_47_as_archived"], *disposition["capability_absorption_11_as_archived"]]
    append(DISPOSITION, archived, "id", "name", "disposition-archived")
    groups = defaultdict(list)
    for row in rows:
        groups[row["canonical_name"]].append(row["record_key"])
    pool = [row for row in rows if row["scope"] == "pool"]
    if len(pool) != 369:
        raise ValueError(f"historical pool changed: {len(pool)}")
    return {"schema": "archeaxis.oss-reuse-crosswalk/v1", "observed_at": verification.get("observed_at", "2026-10-08"),
            "baseline": verification.get("baseline", "UNVERIFIED"), "sources": sources,
            "definitions": {"A": "Result verified through the named product entry in the stated environment; not installed-desktop qualification.",
                            "B": "Existing implementation/entry, current qualification or binding incomplete.",
                            "C": "Concrete extracted behavior/format/test with project mapping; no runtime adoption implied.",
                            "D": "Future candidate, with value, deferral reason and demand trigger.",
                            "E": "Not adopted for the stated role, with alternative and reason."},
            "pool_counts": dict(Counter(row["category"] for row in pool)), "records": rows,
            "identity_groups": dict(groups), "verification": verification,
            "limits": ["No fuzzy suffix matching or silent duplicate collapse.", "Historical installed/implemented/CURRENT labels are retained as source claims only.",
                       "No v0.2 package was supplied or found in tracked task files; rebuilt from repository records.",
                       "Unmatched does not mean rejected; it means deferred until an evidenced need."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--verification", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    output.relative_to(root)
    payload = build(root, json.loads(args.decisions.read_text(encoding="utf-8")),
                    json.loads(args.verification.read_text(encoding="utf-8")) if args.verification else None)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with output.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ["record_key", "scope", "original_id", "original_name", "canonical_name", "match_basis", "category", "capability_id", "reason", "value", "reevaluate_when"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(payload["records"])
    print(json.dumps({"pool_counts": payload["pool_counts"], "source_counts": {key: val["row_count"] for key, val in payload["sources"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
