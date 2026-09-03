"""The documentation entrypoint must link only to existing authority records."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_documentation_authority_index_exists_and_its_local_links_resolve() -> None:
    index = ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md"
    assert index.is_file()
    content = index.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", content)
    assert links
    unresolved = [link for link in links if not (index.parent / link).resolve().exists()]
    assert unresolved == []


def test_documentation_authority_index_links_active_g0_and_directory_gates() -> None:
    content = (ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )

    assert "AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md" in content
    assert "AX_DIR_010_INVENTORY_SCHEMA.md" in content


def test_documentation_authority_index_routes_to_the_operational_issue_archive() -> None:
    """Recurring failures must have one current, discoverable resolution record."""
    content = (ROOT / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md").read_text(
        encoding="utf-8"
    )

    assert "OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md" in content


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


def test_authority_indexes_route_normalization_to_the_current_state_record() -> None:
    """Cleanup and migration work must have one current, evidence-bound queue."""
    state = ROOT / "docs" / "current" / "REPOSITORY_NORMALIZATION_STATE_2026-09-03.md"
    assert state.is_file()
    content = state.read_text(encoding="utf-8")

    assert "G0-001" in content
    assert "TRANSIENT_AUTOMATION" in content
    assert "no Rust/Python dual writer" in content

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


def test_current_ui_roadmap_declares_the_black_and_white_default() -> None:
    roadmap = (ROOT / "docs" / "current" / "UI_V3_PRODUCT_ROADMAP.md").read_text(
        encoding="utf-8"
    )

    assert "黑白深色基线" in roadmap
    assert "历史参考，不是默认主题" in roadmap
    assert "设计底座：Archive Desk + Liquid Glass" not in roadmap
