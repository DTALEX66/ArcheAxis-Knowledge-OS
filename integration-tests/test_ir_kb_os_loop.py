"""IR → KB → OS integration test — exercises the full B-line loop.

Research Note → IntakeCard → EngineeringContract
  → ContextPack → TaskPack
    → /run → PermissionCheck → Execute → Trace → Eval → Lesson
"""
from app.adapters.taskpack import from_knowledge_taskpack, project_to_runtime
from app.agent.executor import execute
from app.core.permissions import check_permission
from app.memory.database import save_lesson_db
from inspiration_research.contracts.generator import generate_contract
from inspiration_research.intake.generator import generate_intake_card
from knowledge_base.context_pack import build_context_pack
from knowledge_base.taskpack import build_taskpack as kb_build_taskpack


def test_ir_to_kb_to_os_full_loop():
    """Simulate a complete B-line research-to-execution cycle."""

    # ── Phase 1: IR — Research → Intake → Contract ──
    intake = generate_intake_card(
        title="MarkItDown Adapter Integration",
        why="Enable multi-format document ingestion (PDF/Word/PPT) for Knowledge-Base",
        what_to_absorb=["MarkItDown library", "file conversion pipeline", "quarantine gate"],
        what_not_to_absorb=["direct core DB write", "auto-install", "unverified output"],
        risk_level="low",
    )
    assert intake.intake_id.startswith("intake_")
    assert intake.why

    contract = generate_contract(
        goal="Integrate MarkItDown adapter for multi-format ingestion",
        deliverables=["markitdown_adapter.py (Phase 2 real impl)", "file conversion tests", "quarantine gate"],
        acceptance_criteria=["5 formats pass conversion", "no direct core write", "fallback works"],
        blocked_actions=["shell_exec", "code_exec", "delete_file"],
        risk_level="low",
    )
    assert contract.contract_id.startswith("contract_")

    # ── Phase 2: KB — ContextPack → TaskPack ──
    ctx = build_context_pack(
        goal=contract.goal,
        sources=[intake.intake_id, contract.contract_id],
        constraints=["quarantine first", "no direct DB write", "all external content sanitized"],
    )
    assert ctx.goal
    assert len(ctx.sources) == 2

    kb_task = kb_build_taskpack(
        goal=ctx.goal,
        steps=[
            {"step_id": "s1", "action": "read_contract", "tool": "echo"},
            {"step_id": "s2", "action": "implement_adapter", "tool": "echo"},
            {"step_id": "s3", "action": "verify_tests", "tool": "echo"},
        ],
        allowed_tools=["echo", "file_read", "safe_write"],
        risk_level="low",
    )
    assert len(kb_task.steps) == 3

    # Map KB TaskPack → canonical v1 → explicit narrower Runtime projection.
    canonical_task = from_knowledge_taskpack(kb_task)
    projection = project_to_runtime(canonical_task)
    assert projection.task.tools == ["echo"]
    assert projection.unmapped_fields == {
        "declared_allowed_tools": kb_task.allowed_tools,
        "explicitly_blocked_tools": kb_task.blocked_tools,
    }
    task = projection.task

    # ── Phase 3: Cognitive-OS — Permission → Execute → Trace → Lesson ──
    perm = check_permission(task, contract.goal)
    assert not perm.requires_human_review
    assert "echo" in perm.allowed_tools

    trace = execute(task, perm)
    assert trace.success is True
    assert len(trace.events) == 3

    # ── Phase 4: Machine lesson from trace ──
    lesson = {
        "id": f"lesson_{trace.id}",
        "pattern": "ir_kb_os_integration_loop",
        "lesson_type": "success",
        "future_constraint": "quarantine all external input before ingestion",
        "evidence_trace_id": trace.id,
        "created_at": trace.created_at,
    }
    save_lesson_db(lesson)
    assert lesson["pattern"] == "ir_kb_os_integration_loop"

    print("✓ Full IR → KB → OS loop completed successfully")
    print(f"  Intake: {intake.intake_id}")
    print(f"  Contract: {contract.contract_id}")
    print(f"  Context: {ctx.context_id}")
    print(f"  Task: {task.id}")
    print(f"  Trace: {trace.id} (success={trace.success})")


if __name__ == "__main__":
    test_ir_to_kb_to_os_full_loop()
