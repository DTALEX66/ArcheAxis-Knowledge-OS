"""ArcheAxis system API — handshake + supervisor status/restart (AXW-RUN-203/204).

Mounted at ``/api/v1/system``:

* ``GET  /api/v1/system/handshake`` — product identity + runtime facts
* ``GET  /api/v1/system/status``    — supervisor state / uptime / pid / logs
* ``POST /api/v1/system/restart``   — simulated restart (202) or 409 if stopped
"""

from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import tomllib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.workspace.router import _require_local_request
from app.workspace.supervisor import BackendSupervisorState, supervisor
from shared.config import resolve_runtime_path
from shared.runtime_profile import resolve_runtime_mode
from shared.storage import DB_PATH

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

PRODUCT_ID = "archeaxis-workspace"
PRODUCT_NAME = "ArcheAxis Knowledge"
API_CONTRACT = "1.x"


def _backend_version() -> str:
    """Read the version from pyproject.toml (single source of truth)."""
    try:
        with open(_PROJECT_ROOT / "pyproject.toml", "rb") as f:
            return str(tomllib.load(f)["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "unknown"


def _source_commit() -> str:
    """HEAD short sha via git, or 'unknown' when the checkout is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit = result.stdout.strip()
        return commit if result.returncode == 0 and commit else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _schema_version() -> int:
    """Read the SQLite user_version from the live DB, or 1 when unavailable."""
    try:
        with sqlite3.connect(
            f"file:{DB_PATH}?mode=ro", uri=True, timeout=5.0
        ) as connection:
            row = connection.execute("PRAGMA user_version").fetchone()
            version = int(row[0]) if row and row[0] else 0
            return version if version > 0 else 1
    except (sqlite3.Error, OSError, TypeError, ValueError):
        return 1


def _workspace_id() -> str:
    """Stable workspace id derived from the resolved runtime data root."""
    data_root = str(resolve_runtime_path("data")).replace("\\", "/")
    return hashlib.sha256(data_root.encode("utf-8")).hexdigest()[:16]


def _migration_state() -> str:
    """Reflect the supervisor's schema-migration phase for the handshake."""
    state = supervisor.state
    if state is BackendSupervisorState.MIGRATING:
        return "migrating"
    if state is BackendSupervisorState.FAILED:
        return "failed"
    return "ready"


router = APIRouter(
    prefix="/api/v1/system",
    tags=["system"],
    dependencies=[Depends(_require_local_request)],
)


@router.get("/handshake")
def system_handshake() -> dict[str, object]:
    """Product identity + runtime facts for the desktop shell (launch gate)."""
    return {
        "product_id": PRODUCT_ID,
        "product_name": PRODUCT_NAME,
        "api_contract": API_CONTRACT,
        "backend_version": _backend_version(),
        "source_commit": _source_commit(),
        "schema_version": _schema_version(),
        "runtime_mode": resolve_runtime_mode(),
        "workspace_id": _workspace_id(),
        "capabilities": [],
        "migration_state": _migration_state(),
    }


@router.get("/status")
def system_status(tail_n: int = 10) -> dict[str, object]:
    """Supervisor state: state / uptime / pid / recent log lines."""
    if tail_n < 1 or tail_n > 200:
        raise HTTPException(status_code=422, detail="tail_n must be within 1..200")
    return supervisor.status(tail_n=tail_n)


@router.post("/restart")
def system_restart() -> JSONResponse:
    """Idempotent simulated restart; 409 when the backend is not running."""
    try:
        state = supervisor.restart()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONResponse(
        status_code=202,
        content={
            "accepted": True,
            "state": state.value,
            "events": supervisor.events()[-3:],
        },
    )
