"""HERMES bedtime unattended loop engine.

Local-first implementation for the night-time unattended scenario:
- deterministic task splitting
- SQLite durable ledger
- hard boundary guardrails
- crash-resumable pending/running queue
- quiet local logs only

The module intentionally avoids external Redis/MySQL requirements so the engine
can run offline inside the current Cognitive-Loop-OS/FastAPI runtime.  The table
shape mirrors a future Redis/MySQL deployment boundary: queue state is explicit,
all operations append immutable events, and runtime config is stored separately
from execution records.
"""

from __future__ import annotations

import gc
import json
import os
import re
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from shared import sleep_loop_migration
from shared.config import resolve_runtime_path
from shared.stable_hash import stable_hash_text
from shared.storage import DB_PATH, _conn
from shared.tool_evidence import has_real_tool_evidence

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOG_DIR = resolve_runtime_path("data/logs/sleep-loop")
LOG_DIR.mkdir(parents=True, exist_ok=True)

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_SLEEPING = "sleeping"
STATUS_PAUSED = "paused"
STATUS_STOPPED = "stopped"
STATUS_COOLING = "cooling"
STATUS_HALTED = "halted"

TASK_PENDING = "pending"
TASK_RUNNING = "running"
TASK_DONE = "done"
TASK_FAILED = "failed"
TASK_BLOCKED = "blocked"
TASK_ARCHIVED = "archived"

REAL_EXECUTORS = {"file_read", "safe_write", "kb_search", "mk_search"}
NON_REAL_EXECUTORS = {"echo", "context_pack_build", "taskpack_generate"}
REPLAY_SAFE_EXECUTORS = {"file_read", "kb_search", "mk_search"}
_RUNTIME_TASK_EXECUTOR: Callable[[dict[str, Any]], dict[str, Any]] | None = None

HARD_BLOCK_PATTERNS = [
    r"人工.*(确认|输入|问答)|弹窗|交互式|human\s*review|manual\s*confirm",
    r"批量删除.*(全库|数据库)|drop\s+database|truncate\s+table|format\s+[a-z]:",
    r"rm\s+-rf\s+[/~]|del\s+/s|rmdir\s+/s|格式化|无备份覆盖",
    r"上传.*(隐私|密钥|token|cookie|凭证)|明文上传|外网高危",
    r"修改.*(核心调度|协议文件|系统启动脚本|HERMES底层)",
    r"无限递归|自我复制|fork\s*bomb|while\s*true.*生成",
    r"管理员权限|root权限|sudo\s+rm|提权",
]

NETWORK_PATTERN = re.compile(r"https?://([^/\s]+)", re.IGNORECASE)
LOCAL_NET_PREFIXES = (
    "localhost",
    "127.",
    "10.",
    "192.168.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.2",
    "172.30.",
    "172.31.",
)


@dataclass
class SleepLoopConfig:
    max_split_tasks: int = 20
    hard_max_split_tasks: int = 50
    global_queue_limit: int = 200
    derived_task_limit: int = 8
    max_retries: int = 3
    max_parallel_tasks: int = 4
    task_timeout_seconds: int = 120
    idle_poll_interval_seconds: int = 30
    active_poll_interval_seconds: int = 1
    cycle_sleep_seconds: int = 30
    max_cycles: int | None = None
    repeat_seed_tasks: bool = False
    max_runtime_hours: int | None = 12
    night_window_enabled: bool = False
    night_window_start: str = "23:00"
    night_window_end: str = "08:00"
    cpu_threshold_percent: int = 70
    cpu_over_threshold_seconds: int = 60
    cpu_cooldown_seconds: int = 180
    memory_cache_limit_mb: int = 800
    batch_file_limit: int = 50
    max_log_file_mb: int = 200
    http_per_minute_limit: int = 30
    local_network_only: bool = False
    failure_streak_limit: int = 10
    db_loss_halt_seconds: int = 300
    quiet_mode: bool = True
    enforce_real_tasks: bool = True

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None = None) -> SleepLoopConfig:
        base = cls()
        if not payload:
            return base
        data = asdict(base)
        for key, value in payload.items():
            if key not in data:
                continue
            data[key] = value
        cfg = cls(**data)
        cfg.max_split_tasks = max(
            1, min(int(cfg.max_split_tasks), int(cfg.hard_max_split_tasks), 50)
        )
        cfg.global_queue_limit = max(1, min(int(cfg.global_queue_limit), 200))
        cfg.derived_task_limit = max(0, min(int(cfg.derived_task_limit), 8))
        cfg.max_retries = max(0, min(int(cfg.max_retries), 3))
        cfg.max_parallel_tasks = max(1, min(int(cfg.max_parallel_tasks), 4))
        cfg.task_timeout_seconds = max(1, min(int(cfg.task_timeout_seconds), 120))
        cfg.idle_poll_interval_seconds = max(1, min(int(cfg.idle_poll_interval_seconds), 24 * 3600))
        cfg.cycle_sleep_seconds = max(1, min(int(cfg.cycle_sleep_seconds), 24 * 3600))
        cfg.http_per_minute_limit = max(1, min(int(cfg.http_per_minute_limit), 30))
        cfg.failure_streak_limit = max(1, min(int(cfg.failure_streak_limit), 10))
        if cfg.max_cycles is not None:
            cfg.max_cycles = max(1, int(cfg.max_cycles))
        if cfg.max_runtime_hours is not None:
            cfg.max_runtime_hours = max(1, min(int(cfg.max_runtime_hours), 12))
        cfg.enforce_real_tasks = True
        return cfg

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sleep_task_request_fingerprint(request: dict[str, Any]) -> str:
    canonical = json.dumps(
        request,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return stable_hash_text(canonical, namespace="sleep-task-request-v1")


def _load(value: str | None, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def init_sleep_loop_schema() -> None:
    """Require the operator-owned Sleep Loop schema without mutating it."""

    sleep_loop_migration.require_applied(db_path=DB_PATH)

def _append_file_log(level: str, event_type: str, message: str) -> None:
    path = LOG_DIR / f"sleep-loop-{datetime.now():%Y%m%d}.log"
    if path.exists() and path.stat().st_size > 200 * 1024 * 1024:
        rotated = LOG_DIR / f"sleep-loop-{datetime.now():%Y%m%d-%H%M%S}.log"
        path.rename(rotated)
    line = _dump({"ts": _now(), "level": level, "event": event_type, "message": message})
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def log_event(
    event_type: str,
    message: str,
    *,
    run_id: str = "",
    task_id: str = "",
    level: str = "info",
    metadata: dict[str, Any] | None = None,
) -> None:
    init_sleep_loop_schema()
    conn = _conn()
    conn.execute(
        "INSERT INTO sleep_loop_events "
        "(id, run_id, task_id, level, event_type, message, metadata_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _new_id("evt"),
            run_id,
            task_id,
            level,
            event_type,
            message,
            _dump(metadata or {}),
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    _append_file_log(level, event_type, message)


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    data = dict(row)
    for key in list(data):
        if key.endswith("_json"):
            data[key[:-5]] = _load(data.pop(key), {} if key == "config_json" else [])
    return data


def get_active_run() -> dict[str, Any] | None:
    init_sleep_loop_schema()
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM sleep_loop_runs WHERE status IN (?, ?, ?, ?) "
        "ORDER BY started_at DESC, rowid DESC LIMIT 1",
        (STATUS_RUNNING, STATUS_SLEEPING, STATUS_PAUSED, STATUS_COOLING),
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def get_latest_run() -> dict[str, Any] | None:
    """Return the latest run, including stopped/completed history."""
    init_sleep_loop_schema()
    conn = _conn()
    row = conn.execute("SELECT * FROM sleep_loop_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def _is_inside_project(path_value: str) -> bool:
    if not path_value:
        return True
    try:
        target = (PROJECT_ROOT / path_value).resolve()
        target.relative_to(PROJECT_ROOT.resolve())
        return True
    except Exception:
        return False


def guard_task(content: str, cfg: SleepLoopConfig) -> tuple[bool, str]:
    text = str(content)
    for pattern in HARD_BLOCK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"hard_boundary_match:{pattern}"

    if cfg.local_network_only:
        for host in NETWORK_PATTERN.findall(text):
            h = host.lower()
            if not h.startswith(LOCAL_NET_PREFIXES):
                return False, f"external_network_blocked:{host}"

    if re.search(r"处理.*(\d+)\s*个文件|scan\s+(\d+)\s+files", text, re.IGNORECASE):
        numbers = [int(n) for n in re.findall(r"\d+", text)]
        if numbers and max(numbers) > cfg.batch_file_limit:
            return False, "batch_file_limit_exceeded"

    path_hits = re.findall(r"(?:path|file|目录|文件)[:=]\s*([^\s,，]+)", text, re.IGNORECASE)
    for path_value in path_hits:
        if not _is_inside_project(path_value):
            return False, f"path_outside_project:{path_value}"

    return True, "allowed"


def validate_real_task(task: dict[str, Any], cfg: SleepLoopConfig) -> tuple[bool, str]:
    """Reject preview/heartbeat/shell tasks before they can enter the queue."""
    if not cfg.enforce_real_tasks:
        return False, "real_task_enforcement_cannot_be_disabled"
    executor = str(task.get("executor", "")).strip()
    payload = task.get("payload", {}) or {}
    if executor in NON_REAL_EXECUTORS:
        return False, f"non_real_executor_blocked:{executor}"
    if executor not in REAL_EXECUTORS:
        return False, f"executor_not_real_task:{executor or '<missing>'}"
    if payload.get("dry_run") is True:
        return False, "dry_run_task_blocked"
    if executor == "safe_write" and payload.get("dry_run") is not False:
        return False, "safe_write_requires_dry_run_false_for_real_task"
    if executor == "file_read" and not str(payload.get("path", "")).strip():
        return False, "file_read_requires_path_evidence"
    if executor in {"kb_search", "mk_search"} and not str(payload.get("query", "")).strip():
        return False, f"{executor}_requires_query_evidence"
    return True, "real_task_allowed"


def has_real_evidence(executor: str, result: dict[str, Any]) -> tuple[bool, str]:
    """Compatibility wrapper around the runtime-wide evidence truth source."""
    return has_real_tool_evidence(executor, result)


def split_task(goal: str, max_items: int) -> list[dict[str, Any]]:
    """Deterministically split a main goal into bounded sub tasks."""
    text = str(goal).strip()
    if not text:
        return []

    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
    if len(lines) <= 1:
        chunks = re.split(r"[。；;]\s*|\n+", text)
        lines = [item.strip(" -\t") for item in chunks if item.strip()]

    if len(lines) <= 1:
        lines = [
            f"梳理任务边界：{text[:120]}",
            f"执行标准后台任务：{text[:120]}",
            "记录执行结果与衍生任务",
        ]

    tasks: list[dict[str, Any]] = []
    for index, item in enumerate(lines[:max_items], start=1):
        tasks.append(
            {
                "title": f"子任务 {index}: {item[:48]}",
                "content": item,
                "priority": index,
                "executor": "kb_search",
                "payload": {"query": item, "top_k": 5},
                "dependencies": [],
            }
        )
    return tasks


def _queue_counts(conn: Any, run_id: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM sleep_loop_tasks WHERE run_id=? GROUP BY status",
        (run_id,),
    ).fetchall()
    data = {row["status"]: int(row["n"]) for row in rows}
    return {
        "pending": data.get(TASK_PENDING, 0),
        "running": data.get(TASK_RUNNING, 0),
        "done": data.get(TASK_DONE, 0),
        "failed": data.get(TASK_FAILED, 0),
        "blocked": data.get(TASK_BLOCKED, 0),
        "archived": data.get(TASK_ARCHIVED, 0),
        "total": sum(data.values()),
    }


def add_task(
    run_id: str,
    task: dict[str, Any],
    cfg: SleepLoopConfig,
    *,
    parent_id: str = "",
    cycle_no: int = 0,
    _connection: Any | None = None,
) -> dict[str, Any]:
    owns_connection = _connection is None
    if owns_connection:
        init_sleep_loop_schema()
    allowed, reason = guard_task(str(task.get("content", task.get("title", ""))), cfg)
    if allowed:
        allowed, reason = validate_real_task(task, cfg)
    dependencies = task.get("dependencies", [])
    if not isinstance(dependencies, list) or not all(
        isinstance(dependency, str) and dependency.strip() for dependency in dependencies
    ):
        raise ValueError("sleep task dependencies must be non-empty string IDs")
    dependencies = list(dict.fromkeys(dependency.strip() for dependency in dependencies))
    normalized_request = {
        "parent_id": parent_id,
        "cycle_no": cycle_no,
        "title": str(task.get("title", "未命名任务"))[:200],
        "content": str(task.get("content", task.get("title", ""))),
        "priority": int(task.get("priority", 100)),
        "executor": str(task.get("executor", "")),
        "payload": task.get("payload", {}),
        "dependencies": dependencies,
        "max_retries": int(task.get("max_retries", cfg.max_retries)),
        "risk_level": str(task.get("risk_level", "low")),
        "requires_review": bool(task.get("requires_review", False)),
    }
    request_fingerprint = _sleep_task_request_fingerprint(normalized_request)
    supplied_key = str(task.get("idempotency_key", "")).strip()
    if len(supplied_key) > 200:
        raise ValueError("sleep task idempotency key exceeds 200 characters")
    if supplied_key and cycle_no > 1:
        cycle_suffix = f":cycle:{cycle_no}"
        idempotency_key = (
            f"{supplied_key}{cycle_suffix}"
            if len(supplied_key) + len(cycle_suffix) <= 200
            else f"cycle:{cycle_no}:{stable_hash_text(supplied_key)}"
        )
    else:
        idempotency_key = supplied_key or request_fingerprint
    task_id = _new_id("slt")
    status = TASK_PENDING if allowed else TASK_BLOCKED
    conn = _connection or _conn()
    try:
        if owns_connection:
            conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id, status, error, request_fingerprint FROM sleep_loop_tasks "
            "WHERE run_id=? AND idempotency_key=?",
            (run_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if str(existing["request_fingerprint"]) != request_fingerprint:
                raise ValueError("idempotency key was reused with a different request")
            if owns_connection:
                conn.commit()
            return {
                "id": str(existing["id"]),
                "status": str(existing["status"]),
                "reason": str(existing["error"] or reason),
                "deduplicated": True,
            }
        if dependencies:
            placeholders = ", ".join("?" for _ in dependencies)
            dependency_rows = conn.execute(
                f"SELECT id FROM sleep_loop_tasks WHERE run_id=? AND id IN ({placeholders})",
                (run_id, *dependencies),
            ).fetchall()
            if {str(row["id"]) for row in dependency_rows} != set(dependencies):
                raise ValueError("sleep task dependencies must exist in the same run")
        counts = _queue_counts(conn, run_id)
        if counts["pending"] + counts["running"] >= cfg.global_queue_limit:
            status = TASK_BLOCKED
            reason = "global_queue_limit_reached"
        conn.execute(
            "INSERT INTO sleep_loop_tasks "
            "(id, run_id, parent_id, cycle_no, title, content, status, priority, executor, "
            "payload_json, dependencies_json, retries, max_retries, risk_level, requires_review, "
            "error, created_at, idempotency_key, request_fingerprint) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                run_id,
                normalized_request["parent_id"],
                normalized_request["cycle_no"],
                normalized_request["title"],
                normalized_request["content"],
                status,
                normalized_request["priority"],
                normalized_request["executor"],
                _dump(normalized_request["payload"]),
                _dump(normalized_request["dependencies"]),
                normalized_request["max_retries"],
                normalized_request["risk_level"],
                1 if normalized_request["requires_review"] else 0,
                "" if allowed else reason,
                _now(),
                idempotency_key,
                request_fingerprint,
            ),
        )
        if owns_connection:
            conn.commit()
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()
    if not allowed and owns_connection:
        log_event("task_blocked", reason, run_id=run_id, task_id=task_id, level="warning")
    return {"id": task_id, "status": status, "reason": reason, "deduplicated": False}


def start_loop(goal: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    init_sleep_loop_schema()
    payload = payload or {}
    cfg = SleepLoopConfig.from_payload(payload.get("config", {}))
    raw_tasks = payload.get("tasks") or split_task(goal, cfg.max_split_tasks)
    seed_tasks = []
    for index, item in enumerate(raw_tasks[: cfg.max_split_tasks], start=1):
        if isinstance(item, dict):
            seed_tasks.append(item)
        else:
            text = str(item)
            seed_tasks.append(
                {
                    "title": f"子任务 {index}: {text[:48]}",
                    "content": text,
                    "priority": index,
                    "executor": "kb_search",
                    "payload": {"query": text, "top_k": 5},
                    "dependencies": [],
                }
            )
    run_id = _new_id("slr")
    now = _now()
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        active_row = conn.execute(
            "SELECT * FROM sleep_loop_runs WHERE status IN (?, ?, ?, ?) "
            "ORDER BY started_at DESC, rowid DESC LIMIT 1",
            (STATUS_RUNNING, STATUS_SLEEPING, STATUS_PAUSED, STATUS_COOLING),
        ).fetchone()
        if active_row is not None:
            conn.commit()
            return {
                "ok": False,
                "error": "sleep loop already active",
                "run": _row_to_dict(active_row),
            }
        conn.execute(
            "INSERT INTO sleep_loop_runs "
            "(id, status, goal, cycle_no, failure_streak, started_at, updated_at, "
            "config_json, seed_tasks_json) "
            "VALUES (?, ?, ?, 1, 0, ?, ?, ?, ?)",
            (
                run_id,
                STATUS_RUNNING,
                goal,
                now,
                now,
                _dump(cfg.to_dict()),
                _dump(seed_tasks),
            ),
        )
        added = [
            add_task(run_id, task, cfg, cycle_no=1, _connection=conn)
            for task in seed_tasks
        ]
        conn.execute(
            "INSERT INTO sleep_loop_events "
            "(id, run_id, task_id, level, event_type, message, metadata_json, created_at) "
            "VALUES (?, ?, '', 'info', 'loop_started', ?, ?, ?)",
            (
                _new_id("evt"),
                run_id,
                "就寝无人值守循环已开启",
                _dump({"config": cfg.to_dict()}),
                _now(),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    with suppress(OSError):
        _append_file_log("info", "loop_started", "就寝无人值守循环已开启")
    return {
        "ok": True,
        "run_id": run_id,
        "status": STATUS_RUNNING,
        "queued": sum(not item["deduplicated"] for item in added),
        "config": cfg.to_dict(),
    }


def stop_loop(
    reason: str = "manual_stop", *, target_status: str = STATUS_STOPPED
) -> dict[str, Any]:
    init_sleep_loop_schema()
    active = get_active_run()
    if not active:
        return {"ok": True, "status": STATUS_IDLE, "message": "no active loop"}
    conn = _conn()
    conn.execute(
        "UPDATE sleep_loop_runs SET status=?, stopped_at=?, updated_at=?, stop_reason=? WHERE id=?",
        (target_status, _now(), _now(), reason, active["id"]),
    )
    conn.execute(
        "UPDATE sleep_loop_tasks SET status=?, finished_at=?, error=?, lease_owner='', "
        "lease_token='', lease_expires_at=NULL, heartbeat_at=NULL "
        "WHERE run_id=? AND status=?",
        (TASK_FAILED, _now(), reason, active["id"], TASK_RUNNING),
    )
    conn.execute(
        "UPDATE sleep_loop_attempts SET status=?, error=?, finished_at=? "
        "WHERE run_id=? AND status=?",
        (TASK_FAILED, reason, _now(), active["id"], TASK_RUNNING),
    )
    conn.commit()
    conn.close()
    log_event(
        "loop_stopped",
        reason,
        run_id=active["id"],
        level="warning" if target_status == STATUS_HALTED else "info",
    )
    return {"ok": True, "run_id": active["id"], "status": target_status, "reason": reason}


def pause_loop(reason: str = "manual_pause") -> dict[str, Any]:
    active = get_active_run()
    if not active:
        return {"ok": False, "error": "no active loop"}
    conn = _conn()
    conn.execute(
        "UPDATE sleep_loop_runs SET status=?, updated_at=? WHERE id=?",
        (STATUS_PAUSED, _now(), active["id"]),
    )
    conn.commit()
    conn.close()
    log_event("loop_paused", reason, run_id=active["id"])
    return {"ok": True, "run_id": active["id"], "status": STATUS_PAUSED}


def resume_loop() -> dict[str, Any]:
    active = get_active_run()
    if not active:
        return {"ok": False, "error": "no paused/sleeping loop"}
    if active.get("status") not in {STATUS_PAUSED, STATUS_SLEEPING, STATUS_COOLING}:
        return {"ok": True, "run_id": active["id"], "status": active.get("status")}
    conn = _conn()
    conn.execute(
        "UPDATE sleep_loop_runs SET status=?, updated_at=?, next_cycle_at=NULL WHERE id=?",
        (STATUS_RUNNING, _now(), active["id"]),
    )
    conn.commit()
    conn.close()
    log_event("loop_resumed", "就寝循环恢复执行", run_id=active["id"])
    return {"ok": True, "run_id": active["id"], "status": STATUS_RUNNING}


def _night_window_allows(cfg: SleepLoopConfig) -> bool:
    if not cfg.night_window_enabled:
        return True
    now = datetime.now().time()
    start_h, start_m = [int(x) for x in cfg.night_window_start.split(":")[:2]]
    end_h, end_m = [int(x) for x in cfg.night_window_end.split(":")[:2]]
    start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end


def _runtime_exceeded(run: dict[str, Any], cfg: SleepLoopConfig) -> bool:
    if cfg.max_runtime_hours is None:
        return False
    started = datetime.fromisoformat(run["started_at"])
    return datetime.now() - started >= timedelta(hours=cfg.max_runtime_hours)


def _resource_guard(run_id: str, cfg: SleepLoopConfig) -> dict[str, Any]:
    """Check low-load bedtime resource boundaries.

    Uses psutil when available.  If unavailable, the engine keeps running and
    records no false failure because offline operation is more important than an
    optional sampler.
    """
    try:
        import psutil
    except Exception:  # noqa: BLE001 - optional dependency
        return {"ok": True, "sampler": "unavailable"}

    proc = psutil.Process(os.getpid())
    cpu = proc.cpu_percent(interval=0.1)
    rss_mb = proc.memory_info().rss / 1024 / 1024

    if cpu >= cfg.cpu_threshold_percent:
        next_at = datetime.now() + timedelta(seconds=cfg.cpu_cooldown_seconds)
        conn = _conn()
        conn.execute(
            "UPDATE sleep_loop_runs SET status=?, next_cycle_at=?, updated_at=? WHERE id=?",
            (STATUS_COOLING, next_at.isoformat(timespec="seconds"), _now(), run_id),
        )
        conn.commit()
        conn.close()
        log_event(
            "resource_cpu_cooling",
            f"CPU {cpu:.1f}% 超过阈值 {cfg.cpu_threshold_percent}%，进入冷却",
            run_id=run_id,
            level="warning",
            metadata={"cpu_percent": cpu, "next_cycle_at": next_at.isoformat()},
        )
        return {"ok": False, "status": STATUS_COOLING, "cpu_percent": cpu}

    if rss_mb >= cfg.memory_cache_limit_mb:
        gc.collect()
        rss_after = proc.memory_info().rss / 1024 / 1024
        if rss_after >= cfg.memory_cache_limit_mb:
            log_event(
                "resource_memory_halt",
                f"内存 {rss_after:.1f}MB 超过阈值 {cfg.memory_cache_limit_mb}MB",
                run_id=run_id,
                level="alert",
                metadata={"rss_mb": rss_after},
            )
            stop_loop("memory_threshold_exceeded", target_status=STATUS_HALTED)
            return {"ok": False, "status": STATUS_HALTED, "rss_mb": rss_after}

    return {"ok": True, "cpu_percent": cpu, "rss_mb": rss_mb}


def _parse_derived_tasks(result: dict[str, Any]) -> list[dict[str, Any]]:
    derived = result.get("derived_tasks")
    if not isinstance(derived, list):
        return []
    return [item for item in derived if isinstance(item, dict)]


def _execute_runtime_task(task: dict[str, Any]) -> dict[str, Any]:
    executor = _RUNTIME_TASK_EXECUTOR
    if executor is None:
        raise RuntimeError("sleep runtime task executor port is not configured")
    return executor(task)


def configure_runtime_task_executor(
    executor: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    """Configure the upper-layer Runtime execution port at a composition root."""

    global _RUNTIME_TASK_EXECUTOR
    _RUNTIME_TASK_EXECUTOR = executor


def _run_with_timeout(
    task: dict[str, Any],
    timeout_seconds: int,
    *,
    heartbeat: Callable[[], bool | None] | None = None,
) -> dict[str, Any]:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_execute_runtime_task, task)
    deadline = time.monotonic() + timeout_seconds
    interval = min(5.0, max(0.25, timeout_seconds / 3))
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                future.cancel()
                return {
                    "status": "error",
                    "error": "task_timeout",
                    "timeout_seconds": timeout_seconds,
                }
            try:
                return future.result(timeout=min(interval, remaining))
            except FutureTimeout:
                if heartbeat is not None and heartbeat() is False:
                    future.cancel()
                    return {"status": "error", "error": "lease_lost"}
            except Exception as exc:  # noqa: BLE001 - ledger must record and continue
                return {"status": "error", "error": str(exc)[:300]}
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _next_pending_task(conn: Any, run_id: str) -> dict[str, Any] | None:
    rows = conn.execute(
        "SELECT * FROM sleep_loop_tasks WHERE run_id=? AND status=? "
        "AND (next_attempt_at IS NULL OR next_attempt_at<=?) "
        "ORDER BY priority ASC, created_at ASC, rowid ASC",
        (run_id, TASK_PENDING, datetime.now().isoformat(timespec="microseconds")),
    ).fetchall()
    for row in rows:
        task = _row_to_dict(row)
        deps = task.get("dependencies", []) or []
        if not deps:
            return task
        placeholders = ", ".join("?" for _ in deps)
        dependency_rows = conn.execute(
            f"SELECT id, status FROM sleep_loop_tasks WHERE run_id=? AND id IN ({placeholders})",
            (run_id, *deps),
        ).fetchall()
        dependency_states = {
            str(dependency["id"]): str(dependency["status"])
            for dependency in dependency_rows
        }
        missing = [dependency for dependency in deps if dependency not in dependency_states]
        failed = [
            dependency
            for dependency in deps
            if dependency_states.get(dependency)
            in {TASK_FAILED, TASK_BLOCKED, TASK_ARCHIVED}
        ]
        if missing or failed:
            detail = ",".join((*missing, *failed))[:240]
            conn.execute(
                "UPDATE sleep_loop_tasks SET status=?, error=?, finished_at=? "
                "WHERE id=? AND run_id=? AND status=?",
                (
                    TASK_BLOCKED,
                    f"dependency_terminal_failure:{detail}",
                    _now(),
                    task["id"],
                    run_id,
                    TASK_PENDING,
                ),
            )
            continue
        if all(dependency_states.get(dependency) == TASK_DONE for dependency in deps):
            return task
    return None


def claim_next_task(
    run_id: str,
    cfg: SleepLoopConfig,
    *,
    worker_id: str,
) -> dict[str, Any] | None:
    """Atomically lease one dependency-ready task to one worker."""

    init_sleep_loop_schema()
    owner = str(worker_id).strip()
    if not owner or len(owner) > 128:
        raise ValueError("sleep loop worker_id must be between 1 and 128 characters")
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        run = conn.execute(
            "SELECT status FROM sleep_loop_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if run is None or str(run["status"]) != STATUS_RUNNING:
            conn.commit()
            return None
        live_running = int(
            conn.execute(
                "SELECT COUNT(*) FROM sleep_loop_tasks WHERE run_id=? AND status=? "
                "AND lease_expires_at>?",
                (
                    run_id,
                    TASK_RUNNING,
                    datetime.now().isoformat(timespec="microseconds"),
                ),
            ).fetchone()[0]
        )
        if live_running >= cfg.max_parallel_tasks:
            conn.commit()
            return None
        task = _next_pending_task(conn, run_id)
        if task is None:
            conn.commit()
            return None
        claimed_at = datetime.now()
        lease_token = _new_id("lease")
        lease_expires_at = claimed_at + timedelta(seconds=cfg.task_timeout_seconds)
        claimed_at_text = claimed_at.isoformat(timespec="microseconds")
        updated = conn.execute(
            "UPDATE sleep_loop_tasks SET status=?, started_at=?, attempt_no=attempt_no+1, "
            "lease_owner=?, lease_token=?, lease_expires_at=?, heartbeat_at=? "
            "WHERE id=? AND run_id=? AND status=?",
            (
                TASK_RUNNING,
                claimed_at_text,
                owner,
                lease_token,
                lease_expires_at.isoformat(timespec="microseconds"),
                claimed_at_text,
                task["id"],
                run_id,
                TASK_PENDING,
            ),
        )
        if updated.rowcount != 1:
            conn.rollback()
            return None
        attempt_no = int(task.get("attempt_no", 0)) + 1
        conn.execute(
            "INSERT INTO sleep_loop_attempts(id, task_id, run_id, attempt_no, lease_owner, "
            "lease_token, status, started_at, heartbeat_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _new_id("sla"),
                task["id"],
                run_id,
                attempt_no,
                owner,
                lease_token,
                TASK_RUNNING,
                claimed_at_text,
                claimed_at_text,
            ),
        )
        row = conn.execute(
            "SELECT * FROM sleep_loop_tasks WHERE id=? AND lease_token=?",
            (task["id"], lease_token),
        ).fetchone()
        conn.commit()
        if row is None:
            raise RuntimeError("claimed sleep task could not be read back")
        return _row_to_dict(row)
    finally:
        conn.close()


def heartbeat_task(
    task_id: str,
    *,
    lease_token: str,
    worker_id: str,
    extend_seconds: int,
    now: datetime | None = None,
) -> bool:
    """Extend one live lease only when the worker still owns its exact token."""

    init_sleep_loop_schema()
    owner = str(worker_id).strip()
    token = str(lease_token).strip()
    if not owner or not token:
        return False
    extension = max(1, min(int(extend_seconds), 300))
    heartbeat_at = now or datetime.now()
    heartbeat_at_text = heartbeat_at.isoformat(timespec="microseconds")
    lease_expires_at = heartbeat_at + timedelta(seconds=extension)
    conn = _conn()
    try:
        updated = conn.execute(
            "UPDATE sleep_loop_tasks SET heartbeat_at=?, lease_expires_at=? "
            "WHERE id=? AND status=? AND lease_owner=? AND lease_token=? "
            "AND lease_expires_at>?",
            (
                heartbeat_at_text,
                lease_expires_at.isoformat(timespec="microseconds"),
                task_id,
                TASK_RUNNING,
                owner,
                token,
                heartbeat_at_text,
            ),
        )
        if updated.rowcount == 1:
            conn.execute(
                "UPDATE sleep_loop_attempts SET heartbeat_at=? "
                "WHERE task_id=? AND lease_owner=? AND lease_token=? AND status=?",
                (heartbeat_at_text, task_id, owner, token, TASK_RUNNING),
            )
        conn.commit()
        return updated.rowcount == 1
    finally:
        conn.close()


def recover_expired_leases(
    run_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Recover expired work without blindly replaying uncertain writes."""

    init_sleep_loop_schema()
    recovered_at = now or datetime.now()
    recovered_at_text = recovered_at.isoformat(timespec="microseconds")
    requeued = 0
    requires_reconciliation = 0
    events: list[tuple[str, str, str]] = []
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT * FROM sleep_loop_tasks WHERE run_id=? AND status=? "
            "AND lease_expires_at IS NOT NULL AND lease_expires_at<=? "
            "ORDER BY lease_expires_at ASC, rowid ASC",
            (run_id, TASK_RUNNING, recovered_at_text),
        ).fetchall()
        for row in rows:
            task = _row_to_dict(row)
            retries = int(task.get("retries", 0)) + 1
            max_retries = int(task.get("max_retries", 0))
            replay_safe = str(task.get("executor", "")) in REPLAY_SAFE_EXECUTORS
            if replay_safe and retries <= max_retries:
                backoff_seconds = min(300, 2 ** min(retries, 8))
                next_attempt_at = recovered_at + timedelta(seconds=backoff_seconds)
                updated = conn.execute(
                    "UPDATE sleep_loop_tasks SET status=?, retries=?, error=?, started_at=NULL, "
                    "next_attempt_at=?, lease_owner='', lease_token='', lease_expires_at=NULL, "
                    "heartbeat_at=NULL WHERE id=? AND status=? AND lease_token=?",
                    (
                        TASK_PENDING,
                        retries,
                        "lease_expired_requeued",
                        next_attempt_at.isoformat(timespec="microseconds"),
                        task["id"],
                        TASK_RUNNING,
                        task["lease_token"],
                    ),
                )
                if updated.rowcount == 1:
                    receipt = conn.execute(
                        "UPDATE sleep_loop_attempts SET status=?, error=?, finished_at=? "
                        "WHERE task_id=? AND lease_token=? AND status=?",
                        (
                            "lease_expired_requeued",
                            "lease_expired_requeued",
                            recovered_at_text,
                            task["id"],
                            task["lease_token"],
                            TASK_RUNNING,
                        ),
                    )
                    if receipt.rowcount != 1:
                        raise RuntimeError("expired sleep lease has no running attempt receipt")
                    requeued += 1
                    events.append(
                        (str(task["id"]), "lease_expired_requeued", "expired read lease requeued")
                    )
                continue
            reason = (
                "unknown_outcome_requires_reconciliation"
                if not replay_safe
                else "lease_retry_budget_exhausted"
            )
            updated = conn.execute(
                "UPDATE sleep_loop_tasks SET status=?, retries=?, error=?, finished_at=?, "
                "lease_owner='', lease_token='', lease_expires_at=NULL, heartbeat_at=NULL "
                "WHERE id=? AND status=? AND lease_token=?",
                (
                    TASK_BLOCKED,
                    retries,
                    reason,
                    recovered_at_text,
                    task["id"],
                    TASK_RUNNING,
                    task["lease_token"],
                ),
            )
            if updated.rowcount == 1:
                receipt = conn.execute(
                    "UPDATE sleep_loop_attempts SET status=?, error=?, finished_at=? "
                    "WHERE task_id=? AND lease_token=? AND status=?",
                    (
                        "reconciliation_required",
                        reason,
                        recovered_at_text,
                        task["id"],
                        task["lease_token"],
                        TASK_RUNNING,
                    ),
                )
                if receipt.rowcount != 1:
                    raise RuntimeError("expired sleep lease has no running attempt receipt")
                requires_reconciliation += 1
                events.append((str(task["id"]), "lease_reconciliation_required", reason))
        conn.commit()
    finally:
        conn.close()
    for task_id, event_type, message in events:
        log_event(
            event_type,
            message,
            run_id=run_id,
            task_id=task_id,
            level="warning",
        )
    return {
        "requeued": requeued,
        "requires_reconciliation": requires_reconciliation,
    }


def tick_once(*, worker_id: str | None = None) -> dict[str, Any]:
    """Run one bounded scheduler tick.

    A PM2/cron/worker loop can call this repeatedly.  The function never asks for
    user input and never raises operational task errors to the caller.
    """
    init_sleep_loop_schema()
    active = get_active_run()
    if not active:
        return {"ok": True, "status": STATUS_IDLE, "message": "no active loop"}

    cfg = SleepLoopConfig.from_payload(active.get("config", {}))
    run_id = active["id"]

    if active["status"] == STATUS_PAUSED:
        return {"ok": True, "status": STATUS_PAUSED, "run_id": run_id}
    if not _night_window_allows(cfg):
        return pause_loop("outside_night_window")
    resource = _resource_guard(run_id, cfg)
    if not resource.get("ok"):
        return {"ok": True, "run_id": run_id, **resource}
    if _runtime_exceeded(active, cfg):
        return stop_loop("max_runtime_hours_reached", target_status=STATUS_HALTED)
    if cfg.max_cycles is not None and int(active.get("cycle_no", 0)) > cfg.max_cycles:
        return stop_loop("max_cycles_reached", target_status=STATUS_STOPPED)
    if int(active.get("failure_streak", 0)) >= cfg.failure_streak_limit:
        return stop_loop("failure_streak_limit_reached", target_status=STATUS_HALTED)

    recover_expired_leases(run_id)
    conn = _conn()
    counts = _queue_counts(conn, run_id)

    if counts["pending"] == 0 and counts["running"] == 0:
        if not cfg.repeat_seed_tasks:
            conn.close()
            return stop_loop("queue_completed", target_status=STATUS_STOPPED)

        next_cycle_at = active.get("next_cycle_at")
        if not next_cycle_at:
            wake_at = datetime.now() + timedelta(seconds=cfg.cycle_sleep_seconds)
            next_cycle_at = wake_at.isoformat(timespec="seconds")
            conn.execute(
                "UPDATE sleep_loop_runs SET status=?, next_cycle_at=?, updated_at=? WHERE id=?",
                (STATUS_SLEEPING, next_cycle_at, _now(), run_id),
            )
            conn.commit()
            conn.close()
            log_event(
                "cycle_sleep_started",
                f"队列清空，休眠 {cfg.cycle_sleep_seconds}s 后开启下一轮",
                run_id=run_id,
                metadata={"next_cycle_at": next_cycle_at},
            )
            return {
                "ok": True,
                "status": STATUS_SLEEPING,
                "run_id": run_id,
                "next_cycle_at": next_cycle_at,
            }
        if next_cycle_at and datetime.now() < datetime.fromisoformat(next_cycle_at):
            conn.execute(
                "UPDATE sleep_loop_runs SET status=?, updated_at=? WHERE id=?",
                (STATUS_SLEEPING, _now(), run_id),
            )
            conn.commit()
            conn.close()
            return {
                "ok": True,
                "status": STATUS_SLEEPING,
                "run_id": run_id,
                "next_cycle_at": next_cycle_at,
            }

        next_cycle = int(active.get("cycle_no", 0)) + 1
        if cfg.max_cycles is not None and next_cycle > cfg.max_cycles:
            conn.close()
            return stop_loop("max_cycles_reached", target_status=STATUS_STOPPED)
        seed_tasks = active.get("seed_tasks", []) or []
        conn.execute(
            "UPDATE sleep_loop_runs SET status=?, cycle_no=?, "
            "next_cycle_at=NULL, updated_at=? WHERE id=?",
            (STATUS_RUNNING, next_cycle, _now(), run_id),
        )
        conn.commit()
        conn.close()
        log_event(
            "cycle_started",
            f"开启第 {next_cycle} 轮循环",
            run_id=run_id,
            metadata={"cycle_no": next_cycle},
        )
        added = [
            add_task(run_id, task, cfg, cycle_no=next_cycle)
            for task in seed_tasks[: cfg.max_split_tasks]
        ]
        gc.collect()
        return {
            "ok": True,
            "status": STATUS_RUNNING,
            "run_id": run_id,
            "cycle_no": next_cycle,
            "queued": sum(not item["deduplicated"] for item in added),
        }

    conn.close()
    effective_worker_id = worker_id or f"sleep-worker-{os.getpid()}-{threading.get_ident()}"
    task = claim_next_task(
        run_id,
        cfg,
        worker_id=effective_worker_id,
    )
    if not task:
        return {
            "ok": True,
            "status": STATUS_RUNNING,
            "run_id": run_id,
            "message": "waiting_for_dependencies",
        }

    task_id = task["id"]
    lease_token = str(task["lease_token"])
    allowed, reason = guard_task(task.get("content", ""), cfg)
    if not allowed:
        conn = _conn()
        conn.execute(
            "UPDATE sleep_loop_tasks SET status=?, error=?, finished_at=?, lease_owner='', "
            "lease_token='', lease_expires_at=NULL, heartbeat_at=NULL "
            "WHERE id=? AND status=? AND lease_token=?",
            (TASK_BLOCKED, reason, _now(), task_id, TASK_RUNNING, lease_token),
        )
        conn.commit()
        conn.close()
        log_event("hard_boundary_block", reason, run_id=run_id, task_id=task_id, level="alert")
        return stop_loop("high_risk_task_detected", target_status=STATUS_HALTED)

    log_event("task_started", task.get("title", ""), run_id=run_id, task_id=task_id)

    executor = task.get("executor", "")
    result = _run_with_timeout(
        task,
        cfg.task_timeout_seconds,
        heartbeat=lambda: heartbeat_task(
            task_id,
            lease_token=lease_token,
            worker_id=effective_worker_id,
            extend_seconds=cfg.task_timeout_seconds,
        ),
    )
    success = result.get("runtime_status") == "done"
    if success:
        _, evidence_reason = has_real_evidence(str(executor), result)
        result["real_evidence"] = evidence_reason

    conn = _conn()
    if success:
        terminal_update = conn.execute(
            "UPDATE sleep_loop_tasks SET status=?, result_json=?, finished_at=?, "
            "terminal_trace_id=?, lease_owner='', lease_token='', lease_expires_at=NULL, "
            "heartbeat_at=NULL WHERE id=? AND status=? AND lease_token=?",
            (
                TASK_DONE,
                _dump(result),
                _now(),
                str(result.get("trace_id", "")),
                task_id,
                TASK_RUNNING,
                lease_token,
            ),
        )
        log_level = "info"
        event_type = "task_done"
        message = task.get("title", "")
    else:
        retries = int(task.get("retries", 0)) + 1
        max_retries = int(task.get("max_retries", cfg.max_retries))
        unknown_write_outcome = (
            str(executor) not in REPLAY_SAFE_EXECUTORS
            and str(result.get("error", "")) == "task_timeout"
        )
        if unknown_write_outcome:
            terminal_update = conn.execute(
                "UPDATE sleep_loop_tasks SET status=?, retries=?, result_json=?, error=?, "
                "finished_at=?, lease_owner='', lease_token='', lease_expires_at=NULL, "
                "heartbeat_at=NULL WHERE id=? AND status=? AND lease_token=?",
                (
                    TASK_BLOCKED,
                    retries,
                    _dump(result),
                    "unknown_outcome_requires_reconciliation",
                    _now(),
                    task_id,
                    TASK_RUNNING,
                    lease_token,
                ),
            )
            event_type = "task_reconciliation_required"
            message = "写任务超时，执行结果未知，禁止自动重放"
        elif retries <= max_retries:
            terminal_update = conn.execute(
                "UPDATE sleep_loop_tasks SET status=?, retries=?, result_json=?, "
                "error=?, started_at=NULL, lease_owner='', lease_token='', "
                "lease_expires_at=NULL, heartbeat_at=NULL WHERE id=? AND status=? AND lease_token=?",
                (
                    TASK_PENDING,
                    retries,
                    _dump(result),
                    str(result.get("error", ""))[:300],
                    task_id,
                    TASK_RUNNING,
                    lease_token,
                ),
            )
            event_type = "task_retry_scheduled"
            message = f"任务失败，安排第 {retries}/{max_retries} 次重试"
        else:
            terminal_update = conn.execute(
                "UPDATE sleep_loop_tasks SET status=?, retries=?, result_json=?, "
                "error=?, finished_at=?, terminal_trace_id=?, lease_owner='', lease_token='', "
                "lease_expires_at=NULL, heartbeat_at=NULL "
                "WHERE id=? AND status=? AND lease_token=?",
                (
                    TASK_ARCHIVED,
                    retries,
                    _dump(result),
                    str(result.get("error", ""))[:300],
                    _now(),
                    str(result.get("trace_id", "")),
                    task_id,
                    TASK_RUNNING,
                    lease_token,
                ),
            )
            event_type = "task_failed_archived"
            message = "任务重试耗尽，归档并继续"
        log_level = "warning"

    if terminal_update.rowcount != 1:
        conn.rollback()
        conn.close()
        return {
            "ok": False,
            "status": STATUS_RUNNING,
            "run_id": run_id,
            "task_id": task_id,
            "success": False,
            "reason": "lease_lost",
        }
    attempt_status = {
        "task_done": TASK_DONE,
        "task_retry_scheduled": "retry_scheduled",
        "task_reconciliation_required": TASK_BLOCKED,
        "task_failed_archived": TASK_ARCHIVED,
    }[event_type]
    receipt_update = conn.execute(
        "UPDATE sleep_loop_attempts SET status=?, trace_id=?, result_json=?, error=?, "
        "finished_at=? WHERE task_id=? AND attempt_no=? AND lease_token=? AND status=?",
        (
            attempt_status,
            str(result.get("trace_id", "")),
            _dump(result),
            str(result.get("error", ""))[:300],
            _now(),
            task_id,
            int(task["attempt_no"]),
            lease_token,
            TASK_RUNNING,
        ),
    )
    if receipt_update.rowcount != 1:
        conn.rollback()
        conn.close()
        raise RuntimeError("sleep task terminal receipt update failed")
    if success:
        conn.execute(
            "UPDATE sleep_loop_runs SET failure_streak=0, updated_at=? WHERE id=?",
            (_now(), run_id),
        )
    elif event_type == "task_failed_archived":
        conn.execute(
            "UPDATE sleep_loop_runs SET failure_streak=failure_streak+1, updated_at=? WHERE id=?",
            (_now(), run_id),
        )
    conn.commit()
    conn.close()
    log_event(
        event_type,
        message,
        run_id=run_id,
        task_id=task_id,
        level=log_level,
        metadata={"result": result},
    )

    derived = _parse_derived_tasks(result) if success else []
    if derived:
        if len(derived) > cfg.derived_task_limit:
            log_event(
                "derived_task_expansion_alert",
                f"衍生任务 {len(derived)} 条超过上限 {cfg.derived_task_limit}，已截断",
                run_id=run_id,
                task_id=task_id,
                level="alert",
            )
        for index, item in enumerate(derived[: cfg.derived_task_limit]):
            try:
                add_task(
                    run_id,
                    item,
                    cfg,
                    parent_id=task_id,
                    cycle_no=int(task.get("cycle_no", 0)),
                )
            except (RuntimeError, ValueError) as exc:
                log_event(
                    "derived_task_rejected",
                    "结构化衍生任务未通过队列约束",
                    run_id=run_id,
                    task_id=task_id,
                    level="warning",
                    metadata={"index": index, "reason": str(exc)[:300]},
                )

    return {
        "ok": True,
        "status": STATUS_RUNNING,
        "run_id": run_id,
        "task_id": task_id,
        "success": success,
    }


def set_config(config_payload: dict[str, Any]) -> dict[str, Any]:
    active = get_active_run()
    cfg = SleepLoopConfig.from_payload(config_payload)
    if not active:
        return {"ok": True, "config": cfg.to_dict(), "message": "validated only; no active run"}
    conn = _conn()
    conn.execute(
        "UPDATE sleep_loop_runs SET config_json=?, updated_at=? WHERE id=?",
        (_dump(cfg.to_dict()), _now(), active["id"]),
    )
    conn.commit()
    conn.close()
    log_event(
        "config_updated",
        "前端更新就寝循环参数",
        run_id=active["id"],
        metadata={"config": cfg.to_dict()},
    )
    return {"ok": True, "run_id": active["id"], "config": cfg.to_dict()}


def list_tasks(
    run_id: str | None = None, status: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    init_sleep_loop_schema()
    active = get_active_run()
    latest = get_latest_run()
    rid = run_id or (active or latest or {}).get("id", "")
    if not rid:
        return []
    limit = max(1, min(int(limit), 500))
    conn = _conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM sleep_loop_tasks WHERE run_id=? AND status=? "
            "ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (rid, status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sleep_loop_tasks WHERE run_id=? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (rid, limit),
        ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def list_attempts(
    *,
    task_id: str | None = None,
    run_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    init_sleep_loop_schema()
    limit = max(1, min(int(limit), 500))
    conn = _conn()
    if task_id:
        rows = conn.execute(
            "SELECT * FROM sleep_loop_attempts WHERE task_id=? "
            "ORDER BY attempt_no DESC LIMIT ?",
            (task_id, limit),
        ).fetchall()
    elif run_id:
        rows = conn.execute(
            "SELECT * FROM sleep_loop_attempts WHERE run_id=? "
            "ORDER BY started_at DESC, rowid DESC LIMIT ?",
            (run_id, limit),
        ).fetchall()
    else:
        rows = []
    conn.close()
    return [_row_to_dict(row) for row in rows]


def list_events(
    run_id: str | None = None, limit: int = 100, level: str | None = None
) -> list[dict[str, Any]]:
    init_sleep_loop_schema()
    active = get_active_run()
    latest = get_latest_run()
    rid = run_id or (active or latest or {}).get("id", "")
    limit = max(1, min(int(limit), 500))
    conn = _conn()
    if rid and level:
        rows = conn.execute(
            "SELECT * FROM sleep_loop_events WHERE run_id=? AND level=? "
            "ORDER BY created_at DESC LIMIT ?",
            (rid, level, limit),
        ).fetchall()
    elif rid:
        rows = conn.execute(
            "SELECT * FROM sleep_loop_events WHERE run_id=? ORDER BY created_at DESC LIMIT ?",
            (rid, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sleep_loop_events ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def status() -> dict[str, Any]:
    init_sleep_loop_schema()
    active = get_active_run()
    if not active:
        return {
            "status": STATUS_IDLE,
            "active": False,
            "config": SleepLoopConfig().to_dict(),
            "queue": {},
        }
    conn = _conn()
    counts = _queue_counts(conn, active["id"])
    oldest_running = conn.execute(
        "SELECT started_at FROM sleep_loop_tasks WHERE run_id=? AND status=? "
        "ORDER BY started_at ASC LIMIT 1",
        (active["id"], TASK_RUNNING),
    ).fetchone()
    conn.close()
    started = datetime.fromisoformat(active["started_at"])
    return {
        "active": True,
        "run_id": active["id"],
        "status": active["status"],
        "goal": active["goal"],
        "cycle_no": active["cycle_no"],
        "failure_streak": active["failure_streak"],
        "queue": counts,
        "started_at": active["started_at"],
        "runtime_seconds": int((datetime.now() - started).total_seconds()),
        "next_cycle_at": active.get("next_cycle_at"),
        "oldest_running_started_at": oldest_running["started_at"] if oldest_running else None,
        "config": SleepLoopConfig.from_payload(active.get("config", {})).to_dict(),
        "db_path": str(DB_PATH),
        "log_dir": str(LOG_DIR),
    }


def sleep_loop_architecture() -> str:
    return """```mermaid
stateDiagram-v2
    [*] --> Idle: 待机
    Idle --> Running: 开启就寝模式
    Running --> Split: 拆解主任务
    Split --> Queue: 子任务入队
    Queue --> Execute: 执行子任务
    Execute --> Derived: 捕获衍生任务
    Derived --> Queue: 追加队尾
    Execute --> Retry: 单任务失败
    Retry --> Queue: 未超重试上限
    Retry --> Archive: 重试耗尽
    Execute --> BoundaryBlock: 命中硬边界
    BoundaryBlock --> Halted: 立刻终止整轮
    Queue --> Sleeping: 队列清空
    Sleeping --> Running: 轮间间隔结束
    Running --> Paused: 手动暂停/非夜间窗口
    Paused --> Running: 恢复
    Running --> Stopped: 手动终止/达到轮次上限
    Running --> Halted: 连续失败/资源超限/账本不可写
    Stopped --> [*]
    Halted --> [*]
```"""
