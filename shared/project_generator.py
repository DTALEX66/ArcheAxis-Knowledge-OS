"""Project generator — adapted from Obsidian-Assistance v7 course_project_generator.

Auto-generates project taskpacks from mastered knowledge, bridging
the gap between learning and doing.

Adapted from: scripts/v7/course_project_generator.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.storage import insert, select_all  # noqa: E402


def generate_project_from_topic(
    topic: str,
    difficulty: str = "medium",
) -> dict[str, Any]:
    """Generate a project taskpack from a mastered topic.

    Finds all cards with the given topic tag, extracts keywords,
    and builds a structured project with milestones and deliverables.

    Args:
        topic: topic tag to build project around.
        difficulty: 'easy' | 'medium' | 'hard'.

    Returns:
        Project plan dict with milestones, deliverables, review prompts.
    """
    cards = select_all("kb_cards", limit=500)
    relevant = [
        c
        for c in cards
        if topic
        in (
            c.get("tags", [])
            if isinstance(c.get("tags"), list)
            else str(c.get("tags", "")).split(",")
        )
    ]

    if not relevant:
        return {"error": f"No cards found for topic: {topic}"}

    from shared.auto_tagger import extract_keywords

    # Extract knowledge from cards
    all_text = " ".join((c.get("title", "") + " " + c.get("content", "")) for c in relevant)
    keywords = [k["keyword"] for k in extract_keywords(all_text, top_k=10)]

    # Build milestones
    milestones = [
        f"Research: understand {keywords[0] if keywords else topic} fundamentals",
        f"Practice: implement basic {keywords[1] if len(keywords) > 1 else topic} examples",
        f"Build: create a working {topic} project",
        f"Review: test and document the {topic} implementation",
        "Share: write up learnings and contribute back",
    ]

    # Build deliverables
    deliverables = [
        f"Working {topic} implementation",
        f"Documentation / README for {topic}",
        f"Test suite for {topic}",
    ]

    # Build review prompts
    review_prompts = [
        f"What is the core principle behind {topic}?",
        f"How does {topic} relate to {keywords[1] if len(keywords) > 1 else 'other concepts'}?",
        f"What was the hardest part of implementing {topic}?",
    ]

    from taskpack import build_taskpack

    task = build_taskpack(
        goal=f"Master {topic} through project-based learning",
        steps=[
            {"step_id": f"s{i + 1}", "action": m, "tool": "echo"} for i, m in enumerate(milestones)
        ],
        allowed_tools=["echo", "file_read", "kb_search", "mk_search"],
        risk_level=difficulty if difficulty == "hard" else "low",
    )

    task_dict = task.to_dict()
    task_dict["id"] = task_dict.pop("task_id")
    task_dict.pop("context_id", None)
    insert("kb_taskpacks", task_dict)

    return {
        "topic": topic,
        "difficulty": difficulty,
        "card_count": len(relevant),
        "keywords": keywords,
        "taskpack_id": task.task_id,
        "milestones": milestones,
        "deliverables": deliverables,
        "review_prompts": review_prompts,
    }


def suggest_projects(limit: int = 5) -> list[dict[str, Any]]:
    """Suggest project-worthy topics based on mastered cards.

    Scans mastered cards for topics with enough depth to build a project.
    """
    cards = select_all("kb_cards", limit=500)
    mastered = [c for c in cards if c.get("review_status") == "mastered"]

    # Group by tags
    topic_depth: dict[str, int] = {}
    for c in mastered:
        tags = c.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        for t in tags:
            if t and len(t) > 2:
                topic_depth[t] = topic_depth.get(t, 0) + 1

    # Filter topics with enough cards for a project
    candidates = [
        {"topic": t, "card_count": c, "depth": "deep" if c >= 5 else "shallow"}
        for t, c in topic_depth.items()
        if c >= 2
    ]
    candidates.sort(key=lambda x: x["card_count"], reverse=True)
    return candidates[:limit]
