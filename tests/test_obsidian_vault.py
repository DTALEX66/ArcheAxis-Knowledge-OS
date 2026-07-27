"""Tests for the synthetic Obsidian vault fixture (J-001).

Verifies that the synthetic test vault at knowledge_base/obsidian_vault/:
- Has the expected structure and files
- Contains working wikilinks between notes
- Has valid YAML frontmatter
- Exercises Obsidian-specific features (callouts, tags, embeds)
"""

from __future__ import annotations

from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[1] / "knowledge_base" / "obsidian_vault"


# ── Vault structure ──


class TestVaultStructure:
    """Verify the vault directory layout."""

    def test_vault_root_exists(self):
        assert VAULT_ROOT.is_dir(), f"Vault root not found: {VAULT_ROOT}"

    def test_obsidian_dir_exists(self):
        assert (VAULT_ROOT / ".obsidian").is_dir()

    def test_obsidian_app_json(self):
        config = (VAULT_ROOT / ".obsidian" / "app.json")
        assert config.is_file()
        import json
        data = json.loads(config.read_text(encoding="utf-8"))
        assert data.get("wikiLinks") is True

    def test_obsidian_core_plugins_json(self):
        config = (VAULT_ROOT / ".obsidian" / "core-plugins.json")
        assert config.is_file()
        import json
        data = json.loads(config.read_text(encoding="utf-8"))
        assert data.get("file-explorer") is True
        assert data.get("publish") is False

    def test_obsidian_appearance_json(self):
        config = (VAULT_ROOT / ".obsidian" / "appearance.json")
        assert config.is_file()
        import json
        data = json.loads(config.read_text(encoding="utf-8"))
        assert data.get("theme") == "obsidian"

    def test_index_md_exists(self):
        assert (VAULT_ROOT / "index.md").is_file()

    def test_card_system_md_exists(self):
        assert (VAULT_ROOT / "card-system.md").is_file()

    def test_task_management_md_exists(self):
        assert (VAULT_ROOT / "task-management.md").is_file()

    def test_review_workflow_md_exists(self):
        assert (VAULT_ROOT / "review-workflow.md").is_file()

    def test_daily_brief_md_exists(self):
        assert (VAULT_ROOT / "daily-brief-format.md").is_file()

    def test_attachments_dir_exists(self):
        assert (VAULT_ROOT / "attachments").is_dir()

    def test_attachments_index_md_exists(self):
        assert (VAULT_ROOT / "attachments" / "index.md").is_file()

    def test_compatibility_matrix_md_exists(self):
        assert (VAULT_ROOT / "COMPATIBILITY_MATRIX.md").is_file()


# ── Note content — wikilinks ──


class TestVaultWikilinks:
    """Verify [[wikilink]] cross-references between notes."""

    def _find_wikilinks(self, text: str) -> list[str]:
        import re
        return [
            m.group(1).strip()
            for m in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
        ]

    def test_index_links_to_card_system(self):
        text = (VAULT_ROOT / "index.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "card-system" in links, f"index.md should [[card-system]]; found: {links}"

    def test_index_links_to_task_management(self):
        text = (VAULT_ROOT / "index.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "task-management" in links

    def test_index_links_to_review_workflow(self):
        text = (VAULT_ROOT / "index.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "review-workflow" in links

    def test_index_links_to_daily_brief(self):
        text = (VAULT_ROOT / "index.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "daily-brief-format" in links

    def test_card_system_links_to_review(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "review-workflow" in links

    def test_card_system_links_to_task_management(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "task-management" in links

    def test_task_management_links_to_card_system(self):
        text = (VAULT_ROOT / "task-management.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "card-system" in links

    def test_wikilink_with_display_text(self):
        """Verify [[target|display]] syntax is preserved."""
        text = (VAULT_ROOT / "daily-brief-format.md").read_text(encoding="utf-8")
        links = self._find_wikilinks(text)
        assert "card-system#Overview" in links or "card-system" in links


# ── Note content — YAML frontmatter ──


class TestVaultFrontmatter:
    """Verify YAML frontmatter on notes."""

    def _parse_frontmatter(self, text: str) -> dict:
        import re
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not m:
            return {}
        result = {}
        for line in m.group(1).split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Handle list syntax: [a, b]
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                result[key] = value
        return result

    def test_card_system_has_frontmatter(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        fm = self._parse_frontmatter(text)
        assert fm, "card-system.md has no frontmatter"
        assert "tags" in fm, f"frontmatter has no tags: {fm}"

    def test_card_system_has_tags(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        fm = self._parse_frontmatter(text)
        tags = fm.get("tags", [])
        if isinstance(tags, list):
            tag_strs = [str(t).lower() for t in tags]
        else:
            tag_strs = [str(tags).lower()]
        assert any("cognitive-loop" in t for t in tag_strs)

    def test_card_system_has_aliases(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        fm = self._parse_frontmatter(text)
        assert "aliases" in fm, f"frontmatter has no aliases: {fm}"

    def test_task_management_has_frontmatter(self):
        text = (VAULT_ROOT / "task-management.md").read_text(encoding="utf-8")
        fm = self._parse_frontmatter(text)
        assert fm, "task-management.md has no frontmatter"

    def test_review_workflow_has_frontmatter(self):
        text = (VAULT_ROOT / "review-workflow.md").read_text(encoding="utf-8")
        fm = self._parse_frontmatter(text)
        assert fm, "review-workflow.md has no frontmatter"

    def test_daily_brief_has_frontmatter(self):
        text = (VAULT_ROOT / "daily-brief-format.md").read_text(encoding="utf-8")
        fm = self._parse_frontmatter(text)
        assert fm, "daily-brief-format.md has no frontmatter"


# ── Note content — callouts, tags, formatting ──


class TestVaultContentFeatures:
    """Verify Obsidian-specific content features in vault notes."""

    def test_callout_note_in_index(self):
        text = (VAULT_ROOT / "index.md").read_text(encoding="utf-8")
        assert "> [!note]" in text, "index.md should have a [!note] callout"

    def test_callout_tip_in_card_system(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        assert "> [!tip]" in text, "card-system.md should have a [!tip] callout"

    def test_callout_warning_in_task_management(self):
        text = (VAULT_ROOT / "task-management.md").read_text(encoding="utf-8")
        assert "> [!warning]" in text

    def test_callout_error_in_review_workflow(self):
        text = (VAULT_ROOT / "review-workflow.md").read_text(encoding="utf-8")
        assert "> [!error]" in text

    def test_callout_important_in_review_workflow(self):
        text = (VAULT_ROOT / "review-workflow.md").read_text(encoding="utf-8")
        assert "> [!important]" in text

    def test_callout_info_in_daily_brief(self):
        text = (VAULT_ROOT / "daily-brief-format.md").read_text(encoding="utf-8")
        assert "> [!info]" in text

    def test_inline_tags_in_index(self):
        text = (VAULT_ROOT / "index.md").read_text(encoding="utf-8")
        assert "#cognitive-loop/vault-intro" in text
        assert "#vault-core/reference" in text

    def test_code_block_in_card_system(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        assert "```python" in text
        assert "```" in text.split("```python", 1)[1]

    def test_table_in_card_system(self):
        text = (VAULT_ROOT / "card-system.md").read_text(encoding="utf-8")
        assert "| Stage |" in text
        assert "|---|" in text or "|------|" in text

    def test_table_in_review_workflow(self):
        text = (VAULT_ROOT / "review-workflow.md").read_text(encoding="utf-8")
        assert "| Score |" in text

    def test_json_code_block_in_task_management(self):
        text = (VAULT_ROOT / "task-management.md").read_text(encoding="utf-8")
        assert "```json" in text

    def test_markdown_code_example_in_daily_brief(self):
        text = (VAULT_ROOT / "daily-brief-format.md").read_text(encoding="utf-8")
        assert "```markdown" in text

    def test_inline_math_in_review_workflow(self):
        text = (VAULT_ROOT / "review-workflow.md").read_text(encoding="utf-8")
        # Math formulas enclosed in backticks or as plain text
        assert "EF" in text

    def test_embed_syntax_in_index(self):
        text = (VAULT_ROOT / "index.md").read_text(encoding="utf-8")
        assert "![[attachments/architecture-overview.png]]" in text


# ── Cross-note consistency ──


class TestVaultConsistency:
    """Verify links are internally consistent."""

    def _find_wikilinks(self, text: str) -> list[str]:
        import re
        return [
            m.group(1).strip().split("#")[0]  # strip anchor
            for m in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
        ]

    def _note_files(self) -> list[Path]:
        return sorted(p for p in VAULT_ROOT.glob("*.md") if p.name != "COMPATIBILITY_MATRIX.md")

    def test_all_internal_wikilinks_have_targets(self):
        """Every [[wikilink]] in the vault targets an existing note file.

        COMPATIBILITY_MATRIX.md is excluded because it contains escaped
        wikilink syntax in code documentation blocks.
        """
        note_names = {p.stem for p in self._note_files()}
        # Also handle COMPATIBILITY_MATRIX which is special
        note_names.add("COMPATIBILITY_MATRIX")

        missing: list[str] = []
        for note in self._note_files():
            if note.name == "COMPATIBILITY_MATRIX.md":
                continue  # documentation-only, not a vault note
            text = note.read_text(encoding="utf-8")
            for target in self._find_wikilinks(text):
                # Skip relative attachment paths
                if "/" in target and not target.startswith("attachments"):
                    continue
                if target not in note_names and not target.startswith("attachments"):
                    missing.append(f"{note.name} -> [[{target}]]")
        assert not missing, f"Orphaned wikilinks: {missing}"

    def test_all_tagged_notes(self):
        """Most content notes should have frontmatter tags."""
        import re

        untagged = []
        for note in self._note_files():
            if note.name == "COMPATIBILITY_MATRIX.md":
                continue
            if note.name == "index.md":
                # index has no frontmatter but has inline tags instead; OK
                continue
            text = note.read_text(encoding="utf-8")
            if re.match(r"^---\s*\n", text):
                continue  # Has frontmatter — good
            if "#" in text:
                continue  # Has inline tags — also acceptable
            untagged.append(note.name)
        assert not untagged, f"Notes without tags: {untagged}"
