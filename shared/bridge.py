"""IR → KB bridge: auto-generate ContextPack + TaskPack from qualified projects."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

from context_pack import build_context_pack
from taskpack import build_taskpack

from shared.storage import insert


def bridge_intake_to_kb(intake_card: dict) -> dict:
    """Convert IR IntakeCard → KB ContextPack + TaskPack. Returns both IDs."""
    ctx = build_context_pack(
        goal=intake_card.get("why", ""),
        sources=[intake_card.get("id", "")],
        constraints=["quarantine first", "no direct DB write", intake_card.get("risk_level", "low")],
    )
    ctx_dict = ctx.to_dict()
    ctx_dict["id"] = ctx_dict.pop("context_id")
    insert("kb_context_packs", ctx_dict)

    task = build_taskpack(
        goal=intake_card.get("why", ""),
        steps=[
            {"step_id": "s1", "action": "review_intake", "tool": "echo"},
            {"step_id": "s2", "action": "plan_absorption", "tool": "echo"},
            {"step_id": "s3", "action": "create_engineering_contract", "tool": "echo"},
        ],
        allowed_tools=["echo", "file_read"],
        risk_level=intake_card.get("risk_level", "low"),
    )
    task_dict = task.to_dict()
    task_dict["id"] = task_dict.pop("task_id")
    task_dict.pop("context_id", None)  # not in SQLite schema
    insert("kb_taskpacks", task_dict)

    return {"context_pack_id": ctx.context_id, "taskpack_id": task.task_id}


def bridge_contract_to_kb(contract: dict) -> dict:
    """Convert IR EngineeringContract → KB TaskPack for Cognitive-OS execution."""
    task = build_taskpack(
        goal=contract.get("goal", ""),
        steps=[
            {"step_id": "s1", "action": "review_contract", "tool": "echo"},
            {"step_id": "s2", "action": "check_deliverables", "tool": "echo"},
            {"step_id": "s3", "action": "verify_acceptance", "tool": "echo"},
        ],
        allowed_tools=["echo", "file_read"],
        risk_level=contract.get("risk_level", "low"),
    )
    task_dict = task.to_dict()
    task_dict["id"] = task_dict.pop("task_id")
    task_dict.pop("context_id", None)
    insert("kb_taskpacks", task_dict)
    return {"taskpack_id": task.task_id}


def bridge_trending_to_kb(trending_repos: list[dict]) -> dict:
    """Batch bridge: trending repos → KB ContextPacks for qualified items."""
    results = []
    for repo in trending_repos:
        if repo.get("qualifies"):
            ctx = build_context_pack(
                goal=f"Evaluate: {repo['repo']}",
                sources=[repo.get("repo", "")],
                constraints=["evaluate license", "check dependencies", "adapter pattern"],
            )
            ctx_dict = ctx.to_dict()
            ctx_dict["id"] = ctx_dict.pop("context_id")
            insert("kb_context_packs", ctx_dict)
            results.append({"repo": repo["repo"], "context_pack_id": ctx.context_id})
    return {"bridged": len(results), "items": results}
