"""Legacy Obsidian projection endpoints isolated from the main API module."""

from __future__ import annotations

from fastapi import APIRouter

from shared.obsidian_projection import (
    render_daily_brief,
    render_lesson,
    render_taskpack,
    render_trace,
    write_projection,
)
from shared.storage import select_one

router = APIRouter(prefix="/project", tags=["projection"])


@router.post("/taskpack/{task_id}")
def project_taskpack(task_id: str, vault_root: str = "", dry_run: bool = True):
    task = select_one("kb_taskpacks", task_id)
    if not task:
        return {"error": "not found"}
    return write_projection(render_taskpack(task), vault_root=vault_root, dry_run=dry_run)


@router.post("/trace/{trace_id}")
def project_trace(trace_id: str, vault_root: str = "", dry_run: bool = True):
    from app.memory.database import list_traces_db

    traces = [
        trace
        for trace in list_traces_db(limit=200)
        if trace.get("trace_id") == trace_id or trace.get("id") == trace_id
    ]
    if not traces:
        return {"error": "not found"}
    return write_projection(render_trace(traces[0]), vault_root=vault_root, dry_run=dry_run)


@router.post("/lesson/{lesson_id}")
def project_lesson(lesson_id: str, vault_root: str = "", dry_run: bool = True):
    from app.memory.database import list_lessons_db

    lessons = [
        lesson
        for lesson in list_lessons_db(limit=200)
        if lesson.get("lesson_id") == lesson_id or lesson.get("id") == lesson_id
    ]
    if not lessons:
        return {"error": "not found"}
    return write_projection(render_lesson(lessons[0]), vault_root=vault_root, dry_run=dry_run)


@router.post("/daily-brief/{brief_id}")
def project_brief(brief_id: str, vault_root: str = "", dry_run: bool = True):
    brief = select_one("ir_daily_briefs", brief_id)
    if not brief:
        return {"error": "not found"}
    return write_projection(render_daily_brief(brief), vault_root=vault_root, dry_run=dry_run)
