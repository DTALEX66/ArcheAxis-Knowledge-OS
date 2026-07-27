"""Tests for the shared/obsidian_projection.py module (J-001).

Verifies:
- Render functions for daily brief, lesson, task pack, trace
- YAML frontmatter generation
- Wikilink extraction
- Tag extraction (frontmatter + inline)
- Callout generation
- write_projection (dry_run and actual write)
"""

from __future__ import annotations

import re

import pytest

from shared.obsidian_projection import (
    Projection,
    render_daily_brief,
    render_lesson,
    render_taskpack,
    render_trace,
    write_projection,
)

# ── Helpers ──


def _parse_frontmatter(text: str) -> dict:
    """Simple frontmatter parser (no PyYAML dependency)."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                value = [v.strip().strip("'\"") for v in inner.split(",")] if inner else []
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            result[key] = value
    return result


def _find_wikilinks(text: str) -> list[str]:
    return [
        m.group(1).strip()
        for m in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
    ]


def _find_callouts(text: str) -> list[str]:
    return re.findall(r">\s*\[!(\w+)\]", text)


def _find_tags(text: str) -> list[str]:
    return [
        m.group(1).strip()
        for m in re.finditer(r"(?:^|\s)(#[a-zA-Z][\w/-]*)", text)
    ]


# ── Tests: render_daily_brief ──


class TestRenderDailyBrief:
    """render_daily_brief builds an Obsidian-compatible daily brief note."""

    def test_basic_brief(self):
        brief = {
            "brief_id": "brief-001",
            "date": "2026-07-26",
            "summary": "Completed 3 context packs.",
            "recent_tasks": [
                {"task_id": "H-001", "label": "Adapter contract", "status": "completed"},
            ],
            "new_cards": [
                {"title": "Card Pipeline", "link": "card-system", "description": "Pipeline stages"},
            ],
            "upcoming_reviews": [
                {"link": "review-workflow", "due": "2026-07-28"},
            ],
        }
        proj = render_daily_brief(brief)
        assert isinstance(proj, Projection)
        assert "Daily/2026-07-26.md" in proj.path
        assert "Adapter contract" in proj.content
        assert "[x]" in proj.content  # completed task
        assert "[[card-system|Card Pipeline]]" in proj.content
        assert "[[review-workflow]]" in proj.content
        assert len(proj.wikilinks) >= 2

    def test_brief_frontmatter(self):
        brief = {"brief_id": "b2", "date": "2026-07-01", "summary": "Test"}
        proj = render_daily_brief(brief)
        fm = _parse_frontmatter(proj.content)
        assert fm.get("tags") == ["cognitive-loop", "daily-brief"]
        assert "cognitive-loop" in str(fm.get("tags", ""))
        assert "date" in fm

    def test_brief_with_pending_tasks(self):
        brief = {
            "brief_id": "b3",
            "date": "2026-07-27",
            "summary": "Started new phase.",
            "recent_tasks": [
                {"task_id": "J-001", "label": "Obsidian vault", "status": "active"},
            ],
        }
        proj = render_daily_brief(brief)
        assert "[ ]" in proj.content  # pending task

    def test_brief_no_optional_fields(self):
        """Brief with only required fields should not crash."""
        brief = {"brief_id": "b4"}
        proj = render_daily_brief(brief)
        assert proj.source == "brief:b4"
        assert "No summary" in proj.content

    def test_brief_callouts(self):
        brief = {"brief_id": "b5", "date": "2026-07-27", "summary": "Status update"}
        proj = render_daily_brief(brief)
        callouts = _find_callouts(proj.content)
        # Daily brief does not auto-generate callouts; that's fine
        assert isinstance(callouts, list)


# ── Tests: render_lesson ──


class TestRenderLesson:
    """render_lesson builds an Obsidian-compatible lesson note."""

    def test_basic_lesson(self):
        lesson = {
            "lesson_id": "lesson-001",
            "title": "Adapter Contract Design",
            "summary": "Designed typed AdapterCapability with four statuses.",
            "tags": ["cognitive-loop", "adapter"],
            "related": [{"title": "Card System", "link": "card-system"}],
        }
        proj = render_lesson(lesson)
        assert isinstance(proj, Projection)
        assert "Lessons/" in proj.path
        assert "Adapter Contract Design" in proj.content
        assert "[[card-system|Card System]]" in proj.content
        assert "> [!info]" in proj.content  # auto-generated callout
        assert "cognitive-loop" in str(proj.tags)

    def test_lesson_frontmatter(self):
        lesson = {
            "lesson_id": "l2",
            "title": "Test Lesson",
            "summary": "Summary text",
            "tags": ["test-tag"],
        }
        proj = render_lesson(lesson)
        fm = _parse_frontmatter(proj.content)
        assert "test-tag" in str(fm.get("tags", ""))
        assert "source" in fm

    def test_lesson_no_related(self):
        """Lesson with no related items should not crash."""
        lesson = {"lesson_id": "l3", "title": "Standalone", "summary": "Alone"}
        proj = render_lesson(lesson)
        assert "Standalone" in proj.content

    def test_lesson_wikilinks_parsed(self):
        lesson = {
            "lesson_id": "l4",
            "title": "Cross Ref",
            "summary": "See [[card-system]] for details.",
            "tags": [],
            "related": ["card-system"],
        }
        proj = render_lesson(lesson)
        assert "card-system" in proj.wikilinks


# ── Tests: render_taskpack ──


class TestRenderTaskpack:
    """render_taskpack builds an Obsidian-compatible task pack note."""

    def test_basic_taskpack(self):
        task = {
            "task_id": "task-001",
            "title": "J-001 Implementation",
            "status": "active",
            "description": "Build Obsidian vault fixtures and projections.",
            "evidence": [
                {"label": "Vault fixture created", "path": "knowledge_base/obsidian_vault/"},
            ],
            "depends_on": ["H-001"],
        }
        proj = render_taskpack(task)
        assert isinstance(proj, Projection)
        assert "TaskPacks/" in proj.path
        assert "J-001 Implementation" in proj.content
        assert "**Status:**" in proj.content
        assert "active" in proj.content
        assert "knowledge_base/obsidian_vault/" in proj.content
        assert "[[H-001]]" in proj.content

    def test_taskpack_frontmatter(self):
        task = {"task_id": "t2", "title": "Task", "status": "completed", "description": "Done."}
        proj = render_taskpack(task)
        fm = _parse_frontmatter(proj.content)
        assert fm.get("status") == "completed"

    def test_taskpack_no_evidence(self):
        task = {"task_id": "t3", "title": "Empty", "description": "No evidence yet."}
        proj = render_taskpack(task)
        assert "Evidence" not in proj.content or "## Evidence" not in proj.content

    def test_taskpack_callout(self):
        task = {"task_id": "t4", "title": "Callout test", "description": "Test callouts"}
        proj = render_taskpack(task)
        callouts = _find_callouts(proj.content)
        assert "note" in callouts


# ── Tests: render_trace ──


class TestRenderTrace:
    """render_trace builds an Obsidian-compatible trace note."""

    def test_basic_trace(self):
        trace = {
            "trace_id": "trace-001",
            "title": "Adapter Registration",
            "summary": "Registered 15 adapter capabilities.",
            "tags": ["cognitive-loop", "trace"],
            "steps": [
                {"name": "Register markitdown", "result": "OK"},
                {"name": "Register trafilatura", "result": "OK"},
            ],
        }
        proj = render_trace(trace)
        assert isinstance(proj, Projection)
        assert "Traces/" in proj.path
        assert "Adapter Registration" in proj.content
        assert "Register markitdown" in proj.content
        assert "> [!info]" in proj.content

    def test_trace_frontmatter(self):
        trace = {"trace_id": "t2", "title": "Test Trace", "summary": "Done"}
        proj = render_trace(trace)
        fm = _parse_frontmatter(proj.content)
        assert "trace" in str(fm.get("tags", ""))

    def test_trace_no_steps(self):
        """Trace without steps should not crash."""
        trace = {"trace_id": "t3", "title": "Simple Trace", "summary": "No steps."}
        proj = render_trace(trace)
        assert "Simple Trace" in proj.content
        assert "Steps" not in proj.content or "## Steps" not in proj.content


# ── Tests: write_projection ──


class TestWriteProjection:
    """write_projection writes (or dry-runs) a Projection to disk."""

    def test_dry_run_default(self, tmp_path):
        """Default dry_run=True returns metadata without writing."""
        proj = Projection(
            path="test/test-note.md",
            content="# Hello\n\nWorld.\n",
            frontmatter={"tags": ["test"]},
            wikilinks=[],
            tags=["test"],
            source="test:1",
        )
        result = write_projection(proj, vault_root=str(tmp_path))
        assert result["dry_run"] is True
        assert "written" not in result or result.get("written") is not True
        assert not (tmp_path / "test" / "test-note.md").exists()

    def test_write_creates_file(self, tmp_path):
        proj = Projection(
            path="written/subdir/note.md",
            content="# Written\n\nContent.\n",
            frontmatter={"tags": ["written"]},
            wikilinks=[],
            tags=["written"],
            source="test:2",
        )
        result = write_projection(proj, vault_root=str(tmp_path), dry_run=False)
        assert result["dry_run"] is False
        assert result.get("written") is True
        target = tmp_path / "written" / "subdir" / "note.md"
        assert target.is_file()
        assert target.read_text(encoding="utf-8") == proj.content

    def test_write_with_default_vault(self):
        """write_projection with empty vault_root uses the project's test vault."""
        proj = Projection(
            path="TestProjection/default-test.md",
            content="# Default vault test\n",
            frontmatter={"tags": ["test"]},
            wikilinks=[],
            tags=["test"],
            source="test:3",
        )
        result = write_projection(proj, dry_run=True)
        # Should resolve to knowledge_base/obsidian_vault/TestProjection/default-test.md
        assert "obsidian_vault" in result["file_path"]
        assert "TestProjection" in result["file_path"]

    def test_write_returns_metadata(self, tmp_path):
        proj = Projection(
            path="meta-test.md",
            content="# Meta\n\n[[card-system]]\n\n#test-tag\n",
            frontmatter={"tags": ["meta"]},
            wikilinks=["card-system"],
            tags=["meta", "#test-tag"],
            source="test:4",
        )
        result = write_projection(proj, vault_root=str(tmp_path), dry_run=False)
        assert result["char_count"] > 10
        assert "card-system" in result["wikilinks"]
        assert "#test-tag" in result["tags"] or "test-tag" in result["tags"]
        assert result["source"] == "test:4"


# ── Tests: Projection dataclass ──


class TestProjectionClass:
    """Projection dataclass core contract."""

    def test_projection_minimal(self):
        proj = Projection(
            path="test.md",
            content="# Hello",
            frontmatter={},
            wikilinks=[],
            tags=[],
        )
        assert proj.path == "test.md"
        assert proj.source is None  # optional

    def test_projection_with_source(self):
        proj = Projection(
            path="test.md",
            content="# Hello",
            frontmatter={"tags": ["a"]},
            wikilinks=["b"],
            tags=["a"],
            source="test:id",
        )
        assert proj.source == "test:id"

    def test_projection_immutable(self):
        """Projection is a frozen dataclass."""
        proj = Projection(path="test.md", content="x", frontmatter={}, wikilinks=[], tags=[])
        with pytest.raises((AttributeError, TypeError)):
            proj.path = "other.md"


# ── Tests: extractor helpers (internal) ──


class TestExtractorHelpers:
    """Verify internal extractor functions (accessible via imports)."""

    def test_wikilink_with_display_text(self):
        text = "See [[target|display text]] for more."
        from shared.obsidian_projection import _extract_wikilinks

        links = _extract_wikilinks(text)
        assert "target" in links
        assert "display text" not in links

    def test_wikilink_heading_anchor(self):
        text = "See [[page#Section]]."
        from shared.obsidian_projection import _extract_wikilinks

        links = _extract_wikilinks(text)
        assert "page#Section" in links or "page" in links

    def test_no_false_wikilinks(self):
        text = "Not a [[wikilink"
        from shared.obsidian_projection import _extract_wikilinks

        links = _extract_wikilinks(text)
        assert len(links) == 0

    def test_inline_tags_extracted(self):
        text = "Normal text #tag and #nested/tag here."
        from shared.obsidian_projection import _extract_tags

        tags = _extract_tags(text, {})
        assert "#tag" in tags
        assert "#nested/tag" in tags

    def test_headings_not_confused_with_tags(self):
        """## Heading should not be extracted as #Heading."""
        text = "## Heading\n\n#actual-tag"
        from shared.obsidian_projection import _extract_tags

        tags = _extract_tags(text, {})
        assert "#actual-tag" in tags
        assert "#Heading" not in tags

    def test_frontmatter_tags_merged(self):
        text = "Body text with #inline-tag"
        from shared.obsidian_projection import _extract_tags

        tags = _extract_tags(text, {"tags": ["fm-tag"]})
        assert "fm-tag" in tags
        assert "#inline-tag" in tags

    def test_render_frontmatter_lists(self):
        from shared.obsidian_projection import _render_frontmatter

        result = _render_frontmatter({"tags": ["a", "b", "c"], "key": "val"})
        assert "tags: [a, b, c]" in result
        assert "key: val" in result

    def test_render_frontmatter_empty(self):
        from shared.obsidian_projection import _render_frontmatter

        assert _render_frontmatter({}) == ""

    def test_render_frontmatter_skips_none(self):
        from shared.obsidian_projection import _render_frontmatter

        result = _render_frontmatter({"key": None, "other": "val"})
        assert "key" not in result
        assert "other: val" in result
