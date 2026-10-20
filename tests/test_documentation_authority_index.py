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

    assert "DIRECTORY_AUTHORITY_INDEX.md" in content
    assert "history/README.md" in content
    manifest = json.loads((ROOT / "docs/history/repository-consolidation-20261019/MANIFEST.json").read_text(encoding="utf-8"))
    originals = {item["original_path"] for item in manifest["files"]}
    assert "docs/current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md" in originals
    assert "docs/current/AX_DIR_010_INVENTORY_SCHEMA.md" in originals

    gap_register = ROOT / 'docs/history/repository-consolidation-20261019/current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md'
    gap_register_text = gap_register.read_text(encoding="utf-8")
    assert "Historical Snapshot" in gap_register_text.splitlines()[0]
    assert "not an" in gap_register_text
    assert "active blocker register" in gap_register_text

    inventory = ROOT / 'docs/history/repository-consolidation-20261019/current/AX_DIR_010_INVENTORY_SCHEMA.md'
    inventory_text = inventory.read_text(encoding="utf-8")
    assert "Historical classifications reconciled" in inventory_text
    assert "`frontend/` and `src-tauri/` are the formal React/Tauri host" in inventory_text
    assert "`apps/ArcheAxis.Desktop/` is a migration donor" in inventory_text
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

    assert "history/README.md" in content
    assert "AAOS-ACTIVE-EXECUTION.json" in content
    historical = ROOT / "docs/history/repository-consolidation-20261019/navigation-before/docs/DOCUMENTATION_AUTHORITY_INDEX.md"
    before = historical.read_text(encoding="utf-8")
    assert "OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md" in before
    assert "Dated diagnostic archive" in before
    assert "旧整包执行顺序不作为当前队列" in content


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
    current_reality = (ROOT / 'docs/history/repository-consolidation-20261019/current/CURRENT_REALITY_2026-09-01.md').read_text(
        encoding="utf-8"
    )

    assert "LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md" in current_reality
    assert "DIRECTORY_AUTHORITY_INDEX.md" in current_reality


def test_authority_indexes_route_normalization_to_a_frozen_historical_record() -> None:
    """Old cleanup and migration snapshots must not appear to be current authority."""
    state = ROOT / 'docs/history/repository-consolidation-20261019/current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md'
    assert state.is_file()
    content = state.read_text(encoding="utf-8")

    assert "Historical normalization queue" in content
    assert "React/TypeScript as product surface" in content
    assert "superseded" in content
    assert "Frozen historical snapshot (2026-09-25)" in content
    language = (ROOT / "docs" / "LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "Inherited migration acceptance requirements remain defined by R6 A13 and" in language
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
    assert "history/repository-consolidation-20261019/MANIFEST.json" in documentation
    assert "REPOSITORY_NORMALIZATION_STATE_2026-09-03.md" in directory
    assert "REPOSITORY_NORMALIZATION_STATE_2026-09-03.md" in language
    historical_index = ROOT / "docs/history/repository-consolidation-20261019/navigation-before/docs/DOCUMENTATION_AUTHORITY_INDEX.md"
    assert "Historical cleanup/index/language snapshot" in historical_index.read_text(encoding="utf-8")
    assert "frozen 2026-09-03 snapshot" in directory


def test_superseded_g0_implementation_plan_is_explicitly_frozen() -> None:
    plan = ROOT / 'docs/history/repository-consolidation-20261019/directories/docs/superpowers/plans/2026-09-03-runtime-authority-and-language-g0.md'
    text = plan.read_text(encoding="utf-8")
    assert "HISTORICAL / SUPERSEDED" in text.splitlines()[0]
    assert "R6/M0" in text.splitlines()[2]


def test_current_ui_roadmap_uses_new_design_and_shared_five_themes() -> None:
    roadmap = (ROOT / "docs/current/UI_V3_PRODUCT_ROADMAP.md").read_text(encoding="utf-8")
    current = roadmap.split("## 历史视觉与路线说明", 1)[0]
    assert "新22页参考" in current
    assert "blueprint" in current and "blueprint-light" in current
    assert all(theme in current for theme in ("black", "white", "cosmic"))
    assert "五主题共用新布局" in current
    assert "统一语义颜色" in current
    assert "主题切换只更新前端宿主资源，不更改 Core 配置或知识数据" in current
    assert "历史参考，不是默认主题" in current
    assert "B10 最终高保真可部署母版是最高视觉依据" not in current
    contract = json.loads((ROOT / "config/product/UI_CONTRACT_V2.json").read_text(encoding="utf-8"))
    projection = contract["visualProjection"]
    assert projection["defaultTheme"] == "blueprint"
    assert projection["themes"] == ["blueprint", "blueprint-light", "black", "white", "cosmic"]
    assert projection["sharedNewLayout"] and projection["legacyThemesArePaletteOnly"]
    assert projection["consistentSemanticColorsWithinTheme"]
    assert not projection["changesCoreOrKnowledgeData"]
    assert contract["executionProjection"]["canonicalPointer"] == "docs/current/AAOS-ACTIVE-EXECUTION.json"


def test_active_execution_pointer_routes_ui_and_keeps_q_evidence_scoped() -> None:
    pointer = json.loads((ROOT / "docs/current/AAOS-ACTIVE-EXECUTION.json").read_text(encoding="utf-8"))
    assert pointer["schema"] == "archeaxis.active-execution/v1"
    assert pointer["active_taskpack"] == "docs/taskpacks/aaos-ui-first-20261009"
    assert pointer["active_progress"] == "docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md"
    assert pointer["inherited_progress"] == ["docs/history/repository-consolidation-20261019/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md"]
    assert (ROOT / pointer["active_taskpack"] / "TASKPACK.md").is_file()
    assert (ROOT / pointer["active_progress"]).is_file()


def test_readme_marks_pre_r6_capability_and_phase_roadmaps_as_historical() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Historical snapshot: pre-R6 Research implementation" in readme
    assert "Historical snapshot: pre-R6 program roadmap" in readme
    assert "AAOS-ACTIVE-EXECUTION.json" in readme
    assert "AAOS-UI-FIRST-EXECUTION-20261009.md" in readme
    assert "当前事实、限制和验证证据见 [`docs/history/repository-consolidation-20261019/legacy-docs/PROJECT_STATUS.md`]" not in readme


def test_live_delivery_and_navigation_do_not_reactivate_historical_pause() -> None:
    pointer = json.loads((ROOT / "docs/current/AAOS-ACTIVE-EXECUTION.json").read_text(encoding="utf-8"))
    # Delivery permission is independent of execution state: keep one live state.
    for section in ("delivery_authorization", "governance_delivery"):
        assert "product_execution" not in pointer[section]
        assert pointer[section]["product_execution_ref"] == "#/execution_control"
    assert pointer["execution_control"]["state"] in {"RUNNING_BY_OWNER", "PAUSED_BY_OWNER"}
    assert pointer["delivery_readback"]["local_worktrees_equal"] is False
    assert pointer["delivery_history"]["delivery_readback"]["state"] == "BRANCH_PUBLISHED"
    for relative in ("docs/README.md", "docs/DIRECTORY_AUTHORITY_INDEX.md",
                     "docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md", "docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md"):
        navigation = (ROOT / relative).read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", navigation)
        targets = {(ROOT / relative).parent.joinpath(link).resolve() for link in links}
        assert (ROOT / "docs/current/AAOS-ACTIVE-EXECUTION.json").resolve() in targets
        assert (ROOT / "docs/current/AAOS-AUTHORITY-ROUTES.json").resolve() in targets
        assert all(target.is_relative_to(ROOT.resolve()) and target.exists() for target in targets)
    # Historical status banners remain evidence in the original navigation,
    # rather than requiring every live index to duplicate a changing state.
    manifest = json.loads((ROOT / "docs/history/repository-consolidation-20261019/MANIFEST.json").read_text(encoding="utf-8"))
    snapshot = next(row for row in manifest["navigation_snapshots"] if row["original_path"] == "docs/README.md")
    raw = (ROOT / snapshot["archive_path"]).read_bytes()
    assert len(raw) == snapshot["bytes"]
    assert hashlib.sha256(raw).hexdigest() == snapshot["sha256"]
    heading = raw.decode("utf-8").splitlines()[2]
    assert "RUNNING_BY_OWNER" in heading and "PAUSED_BY_OWNER" not in heading


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
