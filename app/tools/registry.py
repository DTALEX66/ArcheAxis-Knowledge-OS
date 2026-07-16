from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from shared.approved_paths import ApprovedRoots, ApprovedRootsError
from shared.config import resolve_runtime_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAFE_OUTPUT_DIR = resolve_runtime_path("data/output")
SAFE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
APPROVED_PATHS = ApprovedRoots(source_roots=[PROJECT_ROOT], output_roots=[SAFE_OUTPUT_DIR])


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risk_level: str
    default_dry_run: bool
    description: str


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "echo": ToolSpec(
        name="echo",
        risk_level="low",
        default_dry_run=False,
        description="Return a simple echo result for pipeline verification.",
    ),
    "file_read": ToolSpec(
        name="file_read",
        risk_level="low",
        default_dry_run=False,
        description="Read a UTF-8 text file inside the Cognitive-OS project directory.",
    ),
    "safe_write": ToolSpec(
        name="safe_write",
        risk_level="medium",
        default_dry_run=True,
        description="Write a text file under data/output only; dry-run by default.",
    ),
    "code_exec": ToolSpec(
        name="code_exec",
        risk_level="high",
        default_dry_run=True,
        description="Preview code execution only; real execution is blocked in Phase 1.",
    ),
    # ── B-line knowledge tools (Phase 6) ──
    "kb_search": ToolSpec(
        name="kb_search",
        risk_level="low",
        default_dry_run=False,
        description="Semantic + keyword search over KB documents and cards.",
    ),
    "mk_search": ToolSpec(
        name="mk_search",
        risk_level="low",
        default_dry_run=False,
        description="Search machine knowledge units by keyword.",
    ),
    "context_pack_build": ToolSpec(
        name="context_pack_build",
        risk_level="low",
        default_dry_run=False,
        description="Build a ContextPack from goal + sources + constraints.",
    ),
    "taskpack_generate": ToolSpec(
        name="taskpack_generate",
        risk_level="medium",
        default_dry_run=True,
        description="Generate a TaskPack for Cognitive-OS execution.",
    ),
}

# Convenience: tool name → risk level mapping
TOOL_RISK: dict[str, str] = {name: spec.risk_level for name, spec in TOOL_REGISTRY.items()}


def list_tools() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in TOOL_REGISTRY.values()]


def _base_result(spec: ToolSpec, dry_run: bool, status: str = "ok") -> dict[str, Any]:
    return {
        "tool": spec.name,
        "risk_level": spec.risk_level,
        "dry_run": dry_run,
        "status": status,
    }


def _resolve_inside_project(path_value: str) -> Path | None:
    try:
        return APPROVED_PATHS.resolve_source(path_value, must_exist=False)
    except ApprovedRootsError:
        return None


def echo_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["echo"]
    result = _base_result(spec, dry_run)
    result["message"] = f"executed: {payload.get('name', payload)}"
    return result


def file_read_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["file_read"]
    result = _base_result(spec, dry_run)
    requested = str(payload.get("path", ""))
    target = _resolve_inside_project(requested)
    if target is None:
        result.update({"status": "blocked", "error": "path must stay inside project root"})
        return result
    if dry_run:
        result.update({"path": str(target), "preview": "dry-run read only"})
        return result
    if not target.exists() or not target.is_file():
        result.update({"status": "error", "error": "file not found"})
        return result
    result.update({"path": str(target), "content": target.read_text(encoding="utf-8")})
    return result


def safe_write_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["safe_write"]
    result = _base_result(spec, dry_run)
    filename = str(payload.get("filename", "output.txt"))
    content = str(payload.get("content", ""))
    try:
        target = APPROVED_PATHS.resolve_output(filename)
    except ApprovedRootsError:
        result.update(
            {"status": "blocked", "error": "safe_write target must stay under data/output"}
        )
        return result

    result.update({"path": str(target), "bytes": len(content.encode("utf-8"))})
    if dry_run:
        result["preview"] = content[:200]
        return result

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    result["written"] = True
    return result


def code_exec_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["code_exec"]
    result = _base_result(spec, True, status="blocked")
    result["code_preview"] = str(payload.get("code", ""))[:200]
    result["error"] = "code execution is blocked in Phase 1; dry-run preview only"
    return result


def run_tool(name: str, payload: dict[str, Any], dry_run: bool | None = None) -> dict[str, Any]:
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return {
            "tool": name,
            "risk_level": "unknown",
            "dry_run": True,
            "status": "error",
            "error": "unknown tool",
        }

    effective_dry_run = spec.default_dry_run if dry_run is None else bool(dry_run)
    if name == "echo":
        return echo_tool(payload, effective_dry_run)
    if name == "file_read":
        return file_read_tool(payload, effective_dry_run)
    if name == "safe_write":
        return safe_write_tool(payload, effective_dry_run)
    if name == "code_exec":
        return code_exec_tool(payload, True)
    if name == "kb_search":
        return _kb_search_tool(payload, effective_dry_run)
    if name == "mk_search":
        return _mk_search_tool(payload, effective_dry_run)
    if name == "context_pack_build":
        return _context_pack_build_tool(payload, effective_dry_run)
    if name == "taskpack_generate":
        return _taskpack_generate_tool(payload, effective_dry_run)

    return {
        "tool": name,
        "risk_level": spec.risk_level,
        "dry_run": effective_dry_run,
        "status": "error",
        "error": "tool registered without handler",
    }


# ── B-line knowledge tool handlers (Phase 6) ────────────


def _kb_search_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["kb_search"]
    result = _base_result(spec, dry_run)
    query = str(payload.get("query", ""))
    top_k = int(payload.get("top_k", 5))

    from knowledge_base.search import hybrid_search

    items = hybrid_search(query, top_k=top_k)
    result["items"] = items
    result["count"] = len(items)
    return result


def _mk_search_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["mk_search"]
    result = _base_result(spec, dry_run)
    query = str(payload.get("query", ""))
    limit = int(payload.get("limit", 20))

    from knowledge_base.machine_knowledge import search_units

    items = search_units(query, limit=limit)
    result["items"] = items
    result["count"] = len(items)
    return result


def _context_pack_build_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["context_pack_build"]
    result = _base_result(spec, dry_run)
    goal = str(payload.get("goal", ""))
    sources = payload.get("sources", [])
    constraints = payload.get("constraints", [])

    from knowledge_base.context_pack import build_context_pack

    ctx = build_context_pack(goal=goal, sources=sources, constraints=constraints)
    result["context_pack"] = ctx.to_dict()
    return result


def _taskpack_generate_tool(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    spec = TOOL_REGISTRY["taskpack_generate"]
    result = _base_result(spec, dry_run)
    goal = str(payload.get("goal", ""))
    steps = payload.get("steps", [])
    tools = payload.get("allowed_tools", ["echo"])
    risk = str(payload.get("risk_level", "low"))

    from knowledge_base.taskpack import build_taskpack

    task = build_taskpack(goal=goal, steps=steps, allowed_tools=tools, risk_level=risk)
    if dry_run:
        result["taskpack_preview"] = task.to_dict()
        return result

    from shared.storage import insert

    task_dict = task.to_dict()
    task_dict["id"] = task_dict.pop("task_id")
    insert("kb_taskpacks", task_dict)
    result["taskpack"] = task.to_dict()
    return result
