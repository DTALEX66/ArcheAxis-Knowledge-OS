from __future__ import annotations

import json
from pathlib import Path


def test_open_source_absorption_ledger_covers_the_source_registry_without_risk_upgrade() -> None:
    root = Path(__file__).resolve().parents[1]
    source = json.loads(
        (root / "inspiration_research/resources/open_source_project_registry.json").read_text(
            encoding="utf-8"
        )
    )["projects"]
    ledger = json.loads(
        (root / "inspiration_research/resources/open_source_absorption_ledger.json").read_text(
            encoding="utf-8"
        )
    )["projects"]

    assert len(source) == len(ledger)
    source_by_id = {project["project_id"]: project for project in source}
    ledger_by_id = {project["project_id"]: project for project in ledger}
    assert set(ledger_by_id) == set(source_by_id)
    assert all(
        project["execution_state"]
        in {
            "implemented",
            "adapter_contract_pending",
            "deferred_review",
            "reference_only",
        }
        for project in ledger
    )
    assert all(
        project.get("implementation_evidence")
        for project in ledger
        if project["execution_state"] == "implemented"
    )
    assert all(
        ledger_by_id[project_id]["execution_state"] != "adapter_contract_pending"
        for project_id, source_project in source_by_id.items()
        if source_project["risk_policy"] == "must_review_before_use"
    )


def test_absorption_catalog_uses_live_registry_count() -> None:
    root = Path(__file__).resolve().parents[1]
    source = json.loads(
        (root / "inspiration_research/resources/open_source_project_registry.json").read_text(
            encoding="utf-8"
        )
    )["projects"]
    catalog = (root / "docs/bc-lines/13_开源项目吸收总库.md").read_text(encoding="utf-8")

    assert f"总计：**{len(source)} 个开源项目**" in catalog
