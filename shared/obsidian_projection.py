"""Obsidian projection adapter — B-line assets → Obsidian Markdown pages.

Protocol:
  B-line asset → render → {frontmatter, body} → dry_run report
  Default write_policy = dry_run (never auto-write to Obsidian vault).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from shared.approved_paths import ApprovedRoots, ApprovedRootsError


@dataclass
class ObsidianProjection:
    projection_id: str = ""
    source_asset_id: str = ""
    asset_type: str = ""
    target_path: str = ""
    render_mode: str = "markdown"
    frontmatter: dict = field(default_factory=dict)
    body_template: str = ""
    write_policy: str = "dry_run"
    rendered_body: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "proj") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ── Renderers ───────────────────────────────────────────


def render_taskpack(task: dict, target_dir: str = "60_Tasks") -> ObsidianProjection:
    """TaskPack → Obsidian task note."""
    task_id = task.get("task_id") or task.get("id", "unknown")
    steps = task.get("steps", [])
    steps_md = "\n".join(
        f"- [ ] **{s.get('step_id', '?')}**: {s.get('action', '')} (`{s.get('tool', 'echo')}`)"
        for s in steps
    )

    body = f"""# {task.get("goal", "Untitled Task")}

**Risk**: `{task.get("risk_level", "low")}` | **Tools**: {", ".join(task.get("allowed_tools", []))}

## Steps
{steps_md}

## Constraints
{chr(10).join("- " + c for c in task.get("constraints", [])) or "_none_"}

## Success Criteria
{chr(10).join("- " + s for s in task.get("success_criteria", [])) or "_none_"}
"""

    return ObsidianProjection(
        projection_id=_new_id(),
        source_asset_id=task_id,
        asset_type="TaskPack",
        target_path=f"{target_dir}/{task_id}.md",
        render_mode="markdown",
        frontmatter={
            "type": "taskpack",
            "status": "candidate",
            "risk": task.get("risk_level", "low"),
        },
        body_template="TaskPack report",
        rendered_body=body,
    )


def render_trace(trace: dict, target_dir: str = "70_Traces") -> ObsidianProjection:
    """ExecutionTrace → Obsidian trace report."""
    trace_id = trace.get("trace_id") or trace.get("id", "unknown")
    events = trace.get("events", [])
    events_md = "\n".join(
        f"### Step {i + 1}: {e.get('step', {}).get('name', '?')}\n"
        f"- Tool: `{e.get('result', {}).get('tool', '?')}`\n"
        f"- Status: `{e.get('result', {}).get('status', '?')}`\n"
        f"- Message: {e.get('result', {}).get('message', '')}\n"
        for i, e in enumerate(events)
    )

    status = "✅ success" if trace.get("success") else "❌ failed"
    body = f"""# Trace: {trace_id}

**Task**: `{trace.get("task_id", "?")}` | **Status**: {status} | **Date**: {trace.get("created_at", "")}

{events_md}

## Result
```json
{json.dumps(trace.get("result", {}), ensure_ascii=False, indent=2)}
```
"""

    return ObsidianProjection(
        projection_id=_new_id(),
        source_asset_id=trace_id,
        asset_type="ExecutionTrace",
        target_path=f"{target_dir}/{trace_id}.md",
        render_mode="report",
        frontmatter={"type": "trace", "status": "success" if trace.get("success") else "failed"},
        body_template="Trace report",
        rendered_body=body,
    )


def render_lesson(lesson: dict, target_dir: str = "80_Lessons") -> ObsidianProjection:
    """MachineLesson → Obsidian lesson page."""
    lesson_id = lesson.get("lesson_id") or lesson.get("id", "unknown")

    body = f"""# Lesson: {lesson.get("pattern", "Unknown Pattern")}

**Type**: `{lesson.get("lesson_type", "unknown")}` | **Trace**: `{lesson.get("evidence_trace_id", "?")}`

## Pattern
{lesson.get("pattern", "")}

## Future Constraint
> {lesson.get("future_constraint", "")}
"""

    return ObsidianProjection(
        projection_id=_new_id(),
        source_asset_id=lesson_id,
        asset_type="MachineLesson",
        target_path=f"{target_dir}/{lesson_id}.md",
        render_mode="markdown",
        frontmatter={"type": "machine-lesson", "lesson_type": lesson.get("lesson_type", "unknown")},
        body_template="MachineLesson report",
        rendered_body=body,
    )


def render_daily_brief(brief: dict, target_dir: str = "50_Daily") -> ObsidianProjection:
    """DailyBrief → Obsidian daily report."""
    brief_id = brief.get("brief_id", "unknown")
    sections = brief.get("sections", {})
    repo_list = "\n".join(f"- `{r}`" for r in brief.get("github_ai_projects", []))

    parts = [f"# Daily Brief: {brief.get('date', '')}"]
    for section_name in ("gold", "design", "technology", "ai"):
        items = sections.get(section_name, [])
        if items:
            parts.append(f"\n## {section_name.title()}")
            for item in items:
                parts.append(
                    f"- **{item.get('title', '?')}**: {item.get('summary', '')} _{item.get('impact', '')}_"
                )

    if repo_list:
        parts.append(f"\n## GitHub AI Projects\n{repo_list}")

    body = "\n".join(parts)

    return ObsidianProjection(
        projection_id=_new_id(),
        source_asset_id=brief_id,
        asset_type="DailyBrief",
        target_path=f"{target_dir}/{brief_id}.md",
        render_mode="dashboard",
        frontmatter={"type": "daily-brief", "date": brief.get("date", "")},
        body_template="Daily brief dashboard",
        rendered_body=body,
    )


# ── Write helper ────────────────────────────────────────


def write_projection(proj: ObsidianProjection, vault_root: str = "", dry_run: bool = True) -> dict:
    """Write projection to disk. dry_run=True only returns preview."""
    if proj.write_policy == "blocked":
        return {
            "status": "blocked",
            "reason": "write_policy=blocked",
            "preview": proj.rendered_body[:500],
        }

    if dry_run or proj.write_policy == "dry_run":
        target = Path(vault_root) / proj.target_path if vault_root else Path(proj.target_path)
        return {
            "status": "dry_run",
            "target": str(target),
            "preview": proj.rendered_body[:500],
            "full_length": len(proj.rendered_body),
        }

    if not str(vault_root).strip():
        return {"status": "blocked", "reason": "vault_root is required for writes"}
    try:
        target = ApprovedRoots(output_roots=[vault_root]).resolve_output(proj.target_path)
    except ApprovedRootsError as exc:
        return {"status": "blocked", "reason": str(exc)}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(proj.rendered_body, encoding="utf-8")
    return {"status": "written", "target": str(target), "size": len(proj.rendered_body)}


# ── Enhanced renderers (Phase 6+) ───────────────────────


def render_card(card: dict, target_dir: str = "03_知识卡片") -> ObsidianProjection:
    """KB Card → Obsidian knowledge card note (round-trip compatible)."""
    card_id = card.get("card_id") or card.get("id", "unknown")
    tags = card.get("tags", [])
    tag_str = ", ".join(tags) if tags else "knowledge-card"

    frontmatter = {
        "title": card.get("title", card_id),
        "type": "knowledge-card",
        "kb_id": card_id,
        "review_status": card.get("review_status", "draft"),
        "tags": tags,
        "created": card.get("created_at", ""),
    }

    body = f"""---
title: {frontmatter["title"]}
type: knowledge-card
kb_id: {card_id}
review_status: {frontmatter["review_status"]}
tags: [{tag_str}]
created: {frontmatter["created"]}
---

# {card.get("title", card_id)}

{card.get("content", "")}

---

> Imported from Cognitive-OS KB | ID: `{card_id}`
"""

    return ObsidianProjection(
        projection_id=_new_id(),
        source_asset_id=card_id,
        asset_type="KnowledgeCard",
        target_path=f"{target_dir}/{card_id}.md",
        render_mode="markdown",
        frontmatter=frontmatter,
        body_template="Knowledge card",
        rendered_body=body,
    )


def render_review_card(
    card: dict, reviews: list[dict], target_dir: str = "04_复习卡片"
) -> ObsidianProjection:
    """KB Card + review history → Obsidian review note."""
    card_id = card.get("card_id") or card.get("id", "unknown")
    title = card.get("title", card_id)

    review_md = ""
    for i, r in enumerate(reviews[:10], 1):
        q = r.get("quality", "?")
        emoji = "🟢" if q >= 4 else "🟡" if q >= 2 else "🔴"
        review_md += f"| {i} | {emoji} {q} | {r.get('interval_days', '?')}d | {r.get('ease_factor', '?')} | {r.get('created_at', '')[:10]} |\n"

    body = f"""---
title: 📝 Review: {title}
type: review-card
kb_id: {card_id}
tags: [review, knowledge-card]
---

# 📝 Review: {title}

{card.get("content", "")[:500]}

## Review History

| # | Quality | Interval | Ease | Date |
|---|---------|----------|------|------|
{review_md}

---

> ID: `{card_id}` | Last reviewed: {reviews[0].get("created_at", "")[:10] if reviews else "never"}
"""

    return ObsidianProjection(
        projection_id=_new_id(),
        source_asset_id=card_id,
        asset_type="ReviewCard",
        target_path=f"{target_dir}/{card_id}.md",
        render_mode="markdown",
        frontmatter={"type": "review-card", "kb_id": card_id},
        body_template="Review card with history",
        rendered_body=body,
    )


def render_machine_knowledge(
    unit: dict, target_dir: str = "50_领域知识/机器知识"
) -> ObsidianProjection:
    """MachineKnowledgeUnit → Obsidian domain knowledge note."""
    unit_id = unit.get("id", "unknown")
    unit_type = unit.get("unit_type", "rule")
    conf = unit.get("confidence", 0.5)

    body = f"""---
title: 🤖 {unit.get("title", unit_id)}
type: machine-knowledge
kb_id: {unit_id}
unit_type: {unit_type}
confidence: {conf}
source: {unit.get("source_type", "manual")}
tags: [machine-knowledge, {unit_type}]
---

# 🤖 {unit.get("title", unit_id)}

**Type**: `{unit_type}` | **Confidence**: {conf:.0%} | **Source**: {unit.get("source_type", "manual")}

---

{unit.get("content", "")}

---

> Machine Knowledge Unit | ID: `{unit_id}` | Active: {unit.get("active", True)}
"""

    return ObsidianProjection(
        projection_id=_new_id(),
        source_asset_id=unit_id,
        asset_type="MachineKnowledge",
        target_path=f"{target_dir}/{unit_id}.md",
        render_mode="markdown",
        frontmatter={"type": "machine-knowledge", "unit_type": unit_type, "confidence": conf},
        body_template="Machine knowledge unit",
        rendered_body=body,
    )
