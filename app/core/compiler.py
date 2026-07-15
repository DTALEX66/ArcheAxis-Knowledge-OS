from app.agent.planner import plan_goal
from app.schemas import ContextPack, TaskPack


def compile_task(context: ContextPack) -> TaskPack:
    goal = context.query[:300] if context.query else "Process context"
    steps = plan_goal(goal)
    tools = list(dict.fromkeys(step["tool"] for step in steps))
    return TaskPack(
        goal=goal,
        steps=steps,
        constraints=["log every step", "do not execute high-risk actions without review"],
        tools=tools,
        risk_level="low",
        success_criteria=[
            "execution completes",
            "every step returns an ok result",
            "a non-dry-run tool result carries attributable evidence",
        ],
    )
