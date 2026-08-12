"""Obsidian projection layer — render KB/internal data as Markdown notes.

Generates Obsidian-compatible Markdown with [[wikilinks]], YAML frontmatter,
tags, callouts, and embedded references. This is a one-way projection only;
bidirectional sync and plugin syntax are explicitly out of scope.

Compatibility tiers:
  ✅ Fully compatible — plain Markdown, frontmatter, wikilinks, callouts, tags
  ⚠️ Partial — embedded attachments (copied as relative paths), heading anchors
  ❌ Not supported — Canvas, live preview plugins, Graph view data, bidirectional sync
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from shared.approved_paths import ApprovedRoots, ApprovedRootsError

# ── Types ──


@dataclass(frozen=True)
class Projection:
    """A rendered note ready to write into an Obsidian vault.

    Fields:
        path: relative path within the vault (e.g. "Daily/2026-07-26.md").
        content: full Markdown content, including frontmatter.
        frontmatter: parsed frontmatter dict (for inspection/testing).
        wikilinks: list of [[wikilink]] targets extracted from content.
        tags: list of #tags extracted from content or frontmatter.
        source: internal source identifier (trace_id, lesson_id, etc.).
    """

    path: str
    content: str
    frontmatter: dict[str, Any]
    wikilinks: list[str]
    tags: list[str]
    source: str | None = None
    write_policy: str = "dry_run"

    @property
    def target_path(self) -> str:
        """Backward-compatible alias for the projected vault-relative path."""
        return self.path


    @property
    def rendered_body(self) -> str:
        """Backward-compatible alias for the complete rendered Markdown."""
        return self.content



# ── Rendering helpers ──


def _render_frontmatter(meta: dict[str, Any]) -> str:
    """Render a dict as YAML-style frontmatter (simple key: value format).

    Uses basic string formatting rather than a PyYAML dependency to keep the
    projection module dependency-free and safe for import even when PyYAML
    is not installed.
    """
    if not meta:
        return ""
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            items = ", ".join(str(v) for v in value)
            lines.append(f"{key}: [{items}]")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, (date, datetime)):
            lines.append(f"{key}: {value.isoformat()}")
        elif value is None:
            continue
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _extract_wikilinks(text: str) -> list[str]:
    """Extract [[wikilink]] targets from Markdown text."""
    import re

    # Match [[target]] or [[target|display]] — extract the target part
    targets: list[str] = []
    for match in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text):
        target = match.group(1).strip()
        if target and target not in targets:
            targets.append(target)
    return targets


def _extract_tags(text: str, frontmatter: dict[str, Any]) -> list[str]:
    """Extract tags from both frontmatter tags field and inline #tags.

    Tags from frontmatter are treated as tags (not headings).
    Inline tags (#tag, #tag/subtag) are also extracted.
    """
    import re

    tags: list[str] = []

    # Frontmatter tags
    fm_tags = frontmatter.get("tags", [])
    if isinstance(fm_tags, list):
        for t in fm_tags:
            tag = str(t).strip()
            if tag and tag not in tags:
                tags.append(tag)

    # Inline #tags — avoid ## headings, # in code blocks, and urls
    for match in re.finditer(r"(?:^|\s)(#[a-zA-Z][\w/-]+)", text):
        tag = match.group(1).strip()
        if tag and tag not in tags:
            tags.append(tag)

    return tags


def _render_output_lines(body: str) -> str:
    """Add a trailing newline and ensure the body is properly terminated."""
    body = body.rstrip("\n")
    return body + "\n"


# ── Public render functions ──


def render_daily_brief(brief: dict[str, Any]) -> Projection:
    """Render a daily brief record as an Obsidian-compatible note."""
    brief_id = brief.get("brief_id", brief.get("id", "unknown"))
    brief_date = brief.get("date", brief.get("created_at", date.today().isoformat()))
    summary = brief.get("summary", "No summary available.")
    recent_tasks = brief.get("recent_tasks", [])
    new_cards = brief.get("new_cards", [])
    upcoming_reviews = brief.get("upcoming_reviews", [])

    frontmatter = {
        "tags": ["cognitive-loop", "daily-brief"],
        "source": f"brief:{brief_id}",
        "date": brief_date,
    }

    sections: list[str] = []
    sections.append(f"# Daily Brief — {brief_date}")
    sections.append("")
    sections.append(f"{summary}")
    sections.append("")

    if recent_tasks:
        sections.append("## Recent Tasks")
        sections.append("")
        for task in recent_tasks:
            status = task.get("status", "pending")
            label = task.get("label", task.get("task_id", "unknown"))
            cb = "[x]" if status in ("completed", "done") else "[ ]"
            sections.append(f"- {cb} {label}")
        sections.append("")

    if new_cards:
        sections.append("## New Cards")
        sections.append("")
        for card in new_cards:
            title = card.get("title", "unknown")
            link = card.get("link", "")
            desc = card.get("description", "")
            if link:
                sections.append(f"- [[{link}|{title}]] — {desc}")
            else:
                sections.append(f"- {title} — {desc}")
        sections.append("")

    if upcoming_reviews:
        sections.append("## Upcoming Reviews")
        sections.append("")
        for item in upcoming_reviews:
            link = item.get("link", "")
            due = item.get("due", "soon")
            if link:
                sections.append(f"- [[{link}]] — due {due}")
            else:
                sections.append(f"- {item.get('title', 'unknown')} — due {due}")
        sections.append("")

    body = "\n".join(sections)
    content = _render_frontmatter(frontmatter) + "\n" + _render_output_lines(body)
    wikilinks = _extract_wikilinks(body)
    tags = _extract_tags(body, frontmatter)

    return Projection(
        path=f"Daily/{brief_date}.md",
        content=content,
        frontmatter=frontmatter,
        wikilinks=wikilinks,
        tags=tags,
        source=f"brief:{brief_id}",
    )


def render_lesson(lesson: dict[str, Any]) -> Projection:
    """Render a machine lesson record as an Obsidian-compatible note."""
    lesson_id = lesson.get("lesson_id", lesson.get("id", "unknown"))
    title = lesson.get("title", f"Lesson {lesson_id}")
    summary = lesson.get("summary", lesson.get("content", "No summary"))
    tags_raw = lesson.get("tags", ["cognitive-loop", "lesson"])
    related = lesson.get("related", [])

    frontmatter = {
        "tags": tags_raw,
        "source": f"lesson:{lesson_id}",
        "created": lesson.get("created_at", lesson.get("timestamp", "")),
    }

    sections: list[str] = []
    sections.append(f"# {title}")
    sections.append("")
    sections.append(summary)
    sections.append("")

    if related:
        sections.append("## Related")
        sections.append("")
        for rel in related:
            if isinstance(rel, dict):
                name = rel.get("title", rel.get("id", "unknown"))
                link = rel.get("link", "")
                if link:
                    sections.append(f"- [[{link}|{name}]]")
                else:
                    sections.append(f"- {name}")
            else:
                sections.append(f"- [[{rel}]]")
        sections.append("")

    sections.append("> [!info] Auto-generated")
    sections.append("> This lesson was generated by the archeaxis-workspace learning pipeline.")
    sections.append("")

    body = "\n".join(sections)
    content = _render_frontmatter(frontmatter) + "\n" + _render_output_lines(body)
    wikilinks = _extract_wikilinks(body)
    tags = _extract_tags(body, frontmatter)

    title_slug = title.lower().replace(" ", "-").replace("/", "-")
    return Projection(
        path=f"Lessons/{title_slug}.md",
        content=content,
        frontmatter=frontmatter,
        wikilinks=wikilinks,
        tags=tags,
        source=f"lesson:{lesson_id}",
    )


def render_taskpack(task: dict[str, Any]) -> Projection:
    """Render a task pack record as an Obsidian-compatible note."""
    task_id = task.get("task_id", task.get("id", "unknown"))
    title = task.get("title", f"TaskPack {task_id}")
    status = task.get("status", "pending")
    description = task.get("description", task.get("summary", "No description"))
    evidence = task.get("evidence", [])
    depends_on = task.get("depends_on", [])

    frontmatter = {
        "tags": ["cognitive-loop", "taskpack"],
        "source": f"taskpack:{task_id}",
        "status": status,
        "depends_on": depends_on,
    }

    sections: list[str] = []
    sections.append(f"# {title}")
    sections.append("")
    sections.append(f"**Status:** {status}")
    sections.append("")
    sections.append(description)
    sections.append("")

    if evidence:
        sections.append("## Evidence")
        sections.append("")
        for item in evidence:
            if isinstance(item, dict):
                label = item.get("label", item.get("description", "Item"))
                path_or_link = item.get("path", item.get("link", ""))
                if path_or_link:
                    sections.append(f"- `{path_or_link}` — {label}")
                else:
                    sections.append(f"- {label}")
            else:
                sections.append(f"- {item}")
        sections.append("")

    if depends_on:
        sections.append("## Depends On")
        sections.append("")
        for dep in depends_on:
            sections.append(f"- [[{dep}]]")
        sections.append("")

    sections.append("> [!note] Task Artifact")
    sections.append("> This task pack was projected from the archeaxis-workspace runtime.")
    sections.append("")

    body = "\n".join(sections)
    content = _render_frontmatter(frontmatter) + "\n" + _render_output_lines(body)
    wikilinks = _extract_wikilinks(body)
    tags = _extract_tags(body, frontmatter)

    title_slug = title.lower().replace(" ", "-").replace("/", "-")
    return Projection(
        path=f"TaskPacks/{title_slug}.md",
        content=content,
        frontmatter=frontmatter,
        wikilinks=wikilinks,
        tags=tags,
        source=f"taskpack:{task_id}",
    )


def render_trace(trace: dict[str, Any]) -> Projection:
    """Render a trace record as an Obsidian-compatible note."""
    trace_id = trace.get("trace_id", trace.get("id", "unknown"))
    title = trace.get("title", f"Trace {trace_id}")
    summary = trace.get("summary", trace.get("result", "No trace data"))
    tags_raw = trace.get("tags", ["cognitive-loop", "trace"])
    steps = trace.get("steps", [])

    frontmatter = {
        "tags": tags_raw,
        "source": f"trace:{trace_id}",
        "created": trace.get("created_at", trace.get("timestamp", "")),
    }

    sections: list[str] = []
    sections.append(f"# {title}")
    sections.append("")
    sections.append(summary)
    sections.append("")

    if steps:
        sections.append("## Steps")
        sections.append("")
        for step in steps:
            if isinstance(step, dict):
                name = step.get("name", step.get("step", "Step"))
                result = step.get("result", "")
                sections.append(f"### {name}")
                if result:
                    sections.append(f"{result}")
                sections.append("")
            else:
                sections.append(f"- {step}")
        sections.append("")

    sections.append("> [!info] Agent Trace")
    sections.append("> This trace was recorded by the archeaxis-workspace execution runtime.")
    sections.append("")

    body = "\n".join(sections)
    content = _render_frontmatter(frontmatter) + "\n" + _render_output_lines(body)
    wikilinks = _extract_wikilinks(body)
    tags = _extract_tags(body, frontmatter)

    title_slug = title.lower().replace(" ", "-").replace("/", "-")
    return Projection(
        path=f"Traces/{title_slug}.md",
        content=content,
        frontmatter=frontmatter,
        wikilinks=wikilinks,
        tags=tags,
        source=f"trace:{trace_id}",
    )


# ── Writer ──


def write_projection(
    projection: Projection,
    vault_root: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Write a Projection to disk inside an Obsidian vault.

    Args:
        projection: The rendered Projection to write.
        vault_root: Path to the Obsidian vault root. If empty, uses the
            project's synthetic test vault at knowledge_base/obsidian_vault/.
        dry_run: If True, return the file path and content length without
            writing. If False, write the file.

    Returns:
        Dict with keys: file_path, char_count, wikilinks, tags, source, dry_run.
    """
    if projection.write_policy == "blocked":
        return {
            "status": "blocked",
            "reason": "write_policy=blocked",
            "preview": projection.rendered_body[:500],
        }

    if dry_run:
        if not vault_root:
            vault_root = str(
                Path(__file__).resolve().parents[1] / "knowledge_base" / "obsidian_vault"
            )
        target = Path(vault_root) / projection.target_path
        return {
            "status": "dry_run",
            "target": str(target),
            "file_path": str(target),
            "preview": projection.rendered_body[:500],
            "full_length": len(projection.rendered_body),
            "char_count": len(projection.rendered_body),
            "wikilinks": projection.wikilinks,
            "tags": projection.tags,
            "source": projection.source,
            "dry_run": True,
        }

    if not str(vault_root).strip():
        return {"status": "blocked", "reason": "vault_root is required for writes"}

    try:
        file_path = ApprovedRoots(output_roots=[vault_root]).resolve_output(projection.target_path)
    except ApprovedRootsError as exc:
        return {"status": "blocked", "reason": str(exc)}

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(projection.rendered_body, encoding="utf-8")
    return {
        "status": "written",
        "target": str(file_path),
        "file_path": str(file_path),
        "char_count": len(projection.rendered_body),
        "wikilinks": projection.wikilinks,
        "tags": projection.tags,
        "source": projection.source,
        "dry_run": False,
        "written": True,
        "size": len(projection.rendered_body),
    }
