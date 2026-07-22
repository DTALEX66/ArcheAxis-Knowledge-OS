"""Permission check — gates execution based on tool risk levels.

Rules:
  low       → auto-execute, must trace
  medium    → default dry-run, needs confirmation for real run
  high      → blocked by default, requires human review
  critical  → permanently blocked (shell_exec, delete_file)

Blocked keywords in task content also force REVIEW.
"""

from __future__ import annotations

from app.core.router import RISK_KEYWORDS, _matched_keywords
from app.schemas import PermissionDecision, TaskPack
from app.tools.registry import TOOL_RISK, list_tools

# ── Risk level → allowed strategy ──

RISK_POLICY: dict[str, dict] = {
    "low": {"auto": True, "dry_run": False, "blocked": False},
    "medium": {"auto": True, "dry_run": True, "blocked": False},
    "high": {"auto": False, "dry_run": True, "blocked": False},
    "critical": {"auto": False, "dry_run": True, "blocked": True},
}


def check_permission(task: TaskPack, content: str = "") -> PermissionDecision:
    """Check whether a TaskPack can execute, and under what constraints.

    Returns a PermissionDecision with allowed/blocked tools and review flag.
    """
    allowed: list[str] = []
    blocked: list[str] = []
    reasons: list[str] = []
    max_risk: str = "low"

    list_tools()

    declared_tools = list(dict.fromkeys(task.tools))
    step_tools = list(
        dict.fromkeys(str(step.get("tool", "echo")) for step in task.steps)
    )
    if set(declared_tools) != set(step_tools):
        blocked_mismatch = list(dict.fromkeys([*step_tools, *declared_tools]))
        return PermissionDecision(
            task_id=task.id,
            risk_level="high",
            allowed_tools=[],
            blocked_tools=blocked_mismatch,
            requires_human_review=True,
            reason=(
                "declared task tools do not match executable step tools: "
                f"declared={declared_tools}, steps={step_tools}"
            ),
        )

    # ── Check each requested tool ──
    for tool_name in declared_tools:
        tool_risk = TOOL_RISK.get(tool_name, "medium")
        policy = RISK_POLICY.get(tool_risk, RISK_POLICY["medium"])
        max_risk = _escalate_risk(max_risk, tool_risk)

        if policy["blocked"]:
            blocked.append(tool_name)
            reasons.append(f"{tool_name}: critical risk — permanently blocked")
        elif not policy["auto"]:
            blocked.append(tool_name)
            reasons.append(f"{tool_name}: high risk — requires human review")
        else:
            allowed.append(tool_name)

    # ── Check task content for risk keywords ──
    if content:
        risk_matches = _matched_keywords(content, RISK_KEYWORDS)
        if risk_matches:
            max_risk = _escalate_risk(max_risk, "high")
            reasons.append(f"content contains risk keywords: {', '.join(risk_matches[:5])}")

    # ── Build decision ──
    requires_review = max_risk in ("high", "critical")
    if not reasons:
        reasons.append("all tools within safe risk bounds")

    return PermissionDecision(
        task_id=task.id,
        risk_level=max_risk,  # type: ignore[arg-type]
        allowed_tools=allowed,
        blocked_tools=blocked,
        requires_human_review=requires_review,
        reason="; ".join(reasons),
    )


def _escalate_risk(current: str, new: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return new if order.get(new, 0) > order.get(current, 0) else current
