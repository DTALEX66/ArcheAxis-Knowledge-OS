"""Fail-closed compatibility sentinel for the retired external daily collector.

Phase 4 requires every GitHub repository payload to enter through the canonical
quarantine/provenance/candidate-only ResearchPackage path.  The former cron/CLI
collector bypassed that boundary and is intentionally unavailable.
"""

from typing import NoReturn

_DISABLED_MESSAGE = (
    "legacy external daily collection is disabled; submit one canonical GitHub "
    "repository URL through POST /research/github-repository"
)


def run_daily(since: str = "daily", count: int = 10) -> NoReturn:
    """Reject the retired cron/CLI workflow without network or filesystem effects."""

    del since, count
    raise RuntimeError(_DISABLED_MESSAGE)


if __name__ == "__main__":
    raise SystemExit(_DISABLED_MESSAGE)
