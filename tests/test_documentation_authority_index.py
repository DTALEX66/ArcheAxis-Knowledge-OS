"""The documentation entrypoint must link only to existing authority records."""

import contextlib
import hashlib
import json
import re
import zipfile
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def test_published_september_package_preserves_original_member_bytes() -> None:
    base = ROOT / "docs/history/planning-blueprint-absorption/2026-09-29"
    archive = base / "AAOS_历史规划蓝图吸收池完整总结文档包_2026-09-29.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == (
        "a453646b2e59dba1bbc1500cd610fbd7484e19995384b7d0474fe0db5d9c2cb5"
    )
    with zipfile.ZipFile(archive) as package:
        members = [entry for entry in package.infolist() if not entry.is_dir()]
        assert len(members) == 14
        for entry in members:
            name = entry.filename
            if not entry.flag_bits & 0x800:
                with contextlib.suppress(UnicodeEncodeError, UnicodeDecodeError):
                    name = name.encode("cp437").decode("utf-8")
            original = base / "package-unpacked" / name
            assert original.resolve().is_relative_to((base / "package-unpacked").resolve())
            # ZipFile.read also checks CRC; no original BOM/EOL/content rewriting.
            assert original.read_bytes() == package.read(entry)


def test_documentation_authority_index_exists_and_its_local_links_resolve() -> None:
    index = ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md"
    assert index.is_file()
    content = index.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", content)
    assert links
    unresolved = [link for link in links if not (index.parent / link).resolve().exists()]
    assert unresolved == []


def test_documentation_authority_index_classifies_g0_as_historical_and_routes_directory_gates(
) -> None:
    content = (ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )

    assert "AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md" in content
    assert "AX_DIR_010_INVENTORY_SCHEMA.md" in content
    assert "dated historical evidence" in content
    assert "superseded" in content

    gap_register = ROOT / "docs" / "current" / "AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md"
    gap_register_text = gap_register.read_text(encoding="utf-8")
    assert "Historical Snapshot" in gap_register_text.splitlines()[0]
    assert "not an" in gap_register_text
    assert "active blocker register" in gap_register_text

    inventory = ROOT / "docs" / "current" / "AX_DIR_010_INVENTORY_SCHEMA.md"
    inventory_text = inventory.read_text(encoding="utf-8")
    assert "historical and superseded" in inventory_text
    assert "formal desktop" in inventory_text
    data_class = next(line for line in inventory_text.splitlines() if "`data_class`" in line)
    assert "`LEGACY_SOURCE`" in data_class
    assert "`IGNORED_DEVELOPMENT`" in data_class
    assert "`LEGACY_MIXED_PRESERVE`" in data_class
    assert "`.project-local/` development outputs" in inventory_text


def test_documentation_authority_index_classifies_operational_issue_archive_as_dated() -> None:
    """Old issue statuses must not be presented as the live R6 execution queue."""
    content = (ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )

    assert "OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md" in content
    assert "Dated diagnostic archive" in content
    assert "R6-EXECUTION" in content


def test_documentation_authority_index_links_language_and_directory_authorities() -> None:
    content = (ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )

    assert "LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md" in content
    assert "DIRECTORY_AUTHORITY_INDEX.md" in content


def test_configuration_authority_index_names_fast_full_and_release_ci_layers() -> None:
    content = (ROOT / "docs" / "CONFIGURATION_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )

    assert ".github/workflows/ci.yml" in content
    assert ".github/workflows/nightly.yml" in content
    assert ".github/workflows/release.yml" in content


def test_language_and_directory_authority_indexes_have_resolvable_local_links() -> None:
    for name in ("LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md", "DIRECTORY_AUTHORITY_INDEX.md"):
        index = ROOT / "docs" / name
        content = index.read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", content)
        assert links
        unresolved = [link for link in links if not (index.parent / link).resolve().exists()]
        assert unresolved == []


def test_current_reality_routes_language_and_directory_changes_to_their_indexes() -> None:
    current_reality = (ROOT / "docs" / "current" / "CURRENT_REALITY_2026-09-01.md").read_text(
        encoding="utf-8"
    )

    assert "LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md" in current_reality
    assert "DIRECTORY_AUTHORITY_INDEX.md" in current_reality


def test_authority_indexes_route_normalization_to_a_frozen_historical_record() -> None:
    """Old cleanup and migration snapshots must not appear to be current authority."""
    state = ROOT / "docs" / "current" / "REPOSITORY_NORMALIZATION_STATE_2026-09-03.md"
    assert state.is_file()
    content = state.read_text(encoding="utf-8")

    assert "Historical normalization queue" in content
    assert "React/TypeScript as product surface" in content
    assert "superseded" in content
    assert "Frozen historical snapshot (2026-09-25)" in content
    language = (ROOT / "docs" / "LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "Current migration acceptance is defined by R6 A13 and" in language
    assert "Historical T13 evidence is not a current gate" in language

    documentation = (ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )
    directory = (ROOT / "docs" / "DIRECTORY_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )
    language = (ROOT / "docs" / "LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "REPOSITORY_NORMALIZATION_STATE_2026-09-03.md" in documentation
    assert "REPOSITORY_NORMALIZATION_STATE_2026-09-03.md" in directory
    assert "REPOSITORY_NORMALIZATION_STATE_2026-09-03.md" in language
    assert "Historical cleanup/index/language snapshot" in documentation
    assert "frozen 2026-09-03 snapshot" in directory


def test_superseded_g0_implementation_plan_is_explicitly_frozen() -> None:
    plan = ROOT / "docs" / "superpowers" / "plans" / "2026-09-03-runtime-authority-and-language-g0.md"
    text = plan.read_text(encoding="utf-8")
    assert "HISTORICAL / SUPERSEDED" in text.splitlines()[0]
    assert "R6/M0" in text.splitlines()[2]


def test_current_ui_roadmap_declares_b10_authority_and_shared_dual_themes() -> None:
    roadmap = (ROOT / "docs" / "current" / "UI_V3_PRODUCT_ROADMAP.md").read_text(
        encoding="utf-8"
    )

    assert "B10 最终高保真可部署母版是最高视觉依据" in roadmap
    assert "Aurora 与黑白深色两套配色共用布局及状态" in roadmap
    assert "两套主题共用 ArcheAxis 母版布局、组件状态、页面密度和缩放规则" in roadmap
    assert "主题切换只更新前端宿主资源，不更改 Core 配置或知识数据" in roadmap
    assert "历史参考，不是默认主题" in roadmap
    assert "设计底座：Archive Desk + Liquid Glass" not in roadmap


def test_readme_marks_pre_r6_capability_and_phase_roadmaps_as_historical() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Historical snapshot: pre-R6 Research implementation" in readme
    assert "Historical snapshot: pre-R6 program roadmap" in readme
    assert "Current execution is defined by AAOS-01" in readme
    assert "AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md" in readme
    assert "当前事实、限制和验证证据见 [`docs/PROJECT_STATUS.md`]" not in readme


def test_r6_formal_shell_supersedes_web_first_priority_without_banning_reuse() -> None:
    ledger = (ROOT / "DECISION_SUPERSESSION_LEDGER.yaml").read_text(encoding="utf-8")
    assert "  - id: SUP-021\n" in ledger
    sup013 = ledger.split("  - id: SUP-013\n", 1)[1].split("  - id: SUP-014\n", 1)[0]
    sup021 = ledger.split("  - id: SUP-021\n", 1)[1]
    ui_contract = json.loads(
        (ROOT / "config" / "product" / "UI_CONTRACT_V2.json").read_text(
            encoding="utf-8"
        )
    )

    assert "status: superseded" in sup013
    assert "status: effective" in sup021
    assert "first-release shell priority" in sup021
    assert "TypeScript/JavaScript" in sup021
    # SUP-022 supersedes SUP-021's formal-shell priority, so the machine-readable UI contract
    # must carry the Tauri/React host rather than the donor it replaced.
    sup022 = ledger.split("  - id: SUP-022\n", 1)[1].split("  - id: SUP-023\n", 1)[0]
    assert "status: effective" in sup022
    assert "SUP-021 formal-shell priority only" in sup022
    assert "Tauri 2 with React" in sup022
    assert ui_contract["productShell"]["base"] == "ArcheAxis Tauri 2 + React/TypeScript/Vite"
    assert ui_contract["productShell"]["authorityDecision"] == "SUP-022"
    assert ui_contract["productShell"]["donorShell"]["base"] == "ArcheAxis C#/Avalonia"
    assert ui_contract["productShell"]["donorShell"]["role"] == (
        "frozen-behavior-and-component-donor"
    )


def test_decision_supersession_ledger_matches_its_json_schema() -> None:
    ledger = yaml.safe_load(
        (ROOT / "DECISION_SUPERSESSION_LEDGER.yaml").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / ".project" / "schemas" / "decision-supersession-ledger.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(ledger)
    ids = [decision["id"] for decision in ledger["decisions"]]
    assert len(ids) == len(set(ids))
