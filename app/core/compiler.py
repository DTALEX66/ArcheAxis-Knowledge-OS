from collections.abc import Sequence

from app.agent.planner import plan_goal
from app.evaluation.governance import ReviewedFeedback
from app.schemas import ContextPack, TaskPack


def compile_task(
    context: ContextPack, *, reviewed_feedback: Sequence[ReviewedFeedback] = ()
) -> TaskPack:
    goal = context.query[:300] if context.query else "Process context"
    steps = plan_goal(goal)
    tools = list(dict.fromkeys(step["tool"] for step in steps))
    constraints = ["log every step", "do not execute high-risk actions without review"]
    constraints.extend(
        "reviewed feedback: "
        f"{feedback.rationale}; next constraint: {feedback.evaluation.improvement}"
        for feedback in reviewed_feedback
    )
    return TaskPack(
        goal=goal,
        steps=steps,
        constraints=constraints,
        tools=tools,
        risk_level="low",
        success_criteria=[
            "execution completes",
            "every step returns an ok result",
            "a non-dry-run tool result carries attributable evidence",
        ],
    )
