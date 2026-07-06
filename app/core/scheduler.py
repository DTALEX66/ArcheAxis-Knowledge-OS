"""APScheduler-based background task scheduler for Cognitive-Loop-OS.

Adapted from Star-Trails-Log discovery scheduler.
Supports interval jobs (cognition loops, KB review, IR discovery)
and one-shot triggers. Runs as an AsyncIO scheduler alongside FastAPI.
"""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ── Global scheduler instance ──

scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    executors={"default": AsyncIOExecutor()},
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 60,
    },
)


# ── Job registry (in-memory for now; migrate to SQLite with config) ──

_registry: dict[str, dict] = {}


def register(
    job_id: str,
    fn: Callable[..., Coroutine],
    trigger: str = "interval",
    **trigger_kwargs,
) -> str:
    """Register and schedule a background job.

    Args:
        job_id: Unique identifier, e.g. 'cognition_loop'
        fn: Async callable to execute.
        trigger: 'interval' or 'cron'.
        **trigger_kwargs: passed to APScheduler add_job.
            e.g. minutes=30, hours=1, cron='0 9 * * *'
    Returns:
        The job_id (for later management).
    """
    _registry[job_id] = {
        "fn_name": fn.__name__,
        "trigger": trigger,
        "trigger_kwargs": trigger_kwargs,
    }
    scheduler.add_job(
        fn,
        trigger,
        id=job_id,
        replace_existing=True,
        **trigger_kwargs,
    )
    return job_id


def unregister(job_id: str) -> bool:
    """Remove a scheduled job."""
    try:
        scheduler.remove_job(job_id)
        _registry.pop(job_id, None)
        return True
    except Exception:
        return False


def list_jobs() -> list[dict]:
    """List all registered jobs with status."""
    result = []
    for job in scheduler.get_jobs():
        result.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return result


def trigger_now(job_id: str) -> bool:
    """Manually trigger a registered job once (fire-and-forget)."""
    job = scheduler.get_job(job_id)
    if job is None:
        return False
    job.modify(next_run_time=datetime.now())
    return True


# ── Lifecycle ──


def start() -> None:
    """Start the scheduler (call during app startup)."""
    if scheduler.running:
        return
    scheduler.start()
    print(f"[Scheduler] Started — {len(scheduler.get_jobs())} jobs registered")


def stop() -> None:
    """Shut down the scheduler (call during app shutdown)."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped")


def is_running() -> bool:
    return scheduler.running
