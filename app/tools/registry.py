from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAFE_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
SAFE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
        path = (PROJECT_ROOT / path_value).resolve()
        path.relative_to(PROJECT_ROOT.resolve())
        return path
    except Exception:
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
    filename = str(payload.get("filename", "output.txt")).replace("..", "_")
    content = str(payload.get("content", ""))
    target = (SAFE_OUTPUT_DIR / filename).resolve()
    try:
        target.relative_to(SAFE_OUTPUT_DIR.resolve())
    except Exception:
        result.update({"status": "blocked", "error": "safe_write target must stay under data/output"})
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

    return {
        "tool": name,
        "risk_level": spec.risk_level,
        "dry_run": effective_dry_run,
        "status": "error",
        "error": "tool registered without handler",
    }
