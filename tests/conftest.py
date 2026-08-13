"""Shared test fixtures."""
import os
import secrets
import sys
import tempfile
from pathlib import Path

import pytest

# Make app importable from tests/
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

_TASK_RUNTIME = _PROJECT_ROOT / ".hermes" / "task-runtime"
_TASK_TMP = _TASK_RUNTIME / "pytest-tmp"
# resolve() guards against MSYS /d/... path forms leaking into child
# processes: a /d/All projects/... prefix would otherwise resolve to
# D:\d\All projects\... on Windows Python (workspace-hygiene §project-local).
_TASK_PYCACHE = (_TASK_RUNTIME / "pycache").resolve()
for _path in (_TASK_TMP, _TASK_PYCACHE):
    _path.mkdir(parents=True, exist_ok=True)
for _name in ("TMP", "TEMP", "TMPDIR"):
    os.environ[_name] = str(_TASK_TMP)
os.environ["PYTHONPYCACHEPREFIX"] = str(_TASK_PYCACHE)
# Keep unrelated integration tests from exhausting the production-like default
# bucket; dedicated rate-limit tests override these values explicitly.
os.environ.setdefault("COGNITIVE_RATE_LIMIT_READ", "10000")
os.environ.setdefault("COGNITIVE_RATE_LIMIT_WRITE", "1000")
os.environ.setdefault("COGNITIVE_RATE_LIMIT_TOKEN", "100")
tempfile.tempdir = str(_TASK_TMP)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the --run-network flag used by live-API connector tests."""
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Run live-network tests (DOI/API connector calls).",
    )


@pytest.fixture
def admin_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Provision an isolated, explicit administrator key for one test."""
    api_key = secrets.token_urlsafe(32)
    monkeypatch.setenv("COGNITIVE_API_KEY", api_key)
    return api_key


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Surface failing test ids as workflow annotations on CI (log-less).

    GitHub Actions only exposes step logs to repo admins; annotations are
    readable via the checks API. `::error::` lines on stdout are parsed by
    the runner into annotations, so failed test names become visible.
    """
    if exitstatus == 0:
        return
    reports = session.config.stash.get(_failed_reports, [])
    seen: set[str] = set()
    for report in reports:
        if report.nodeid in seen:
            continue
        seen.add(report.nodeid)
        print(f"::error::PYTEST-FAILED {report.nodeid}")
        if report.longrepr is not None:
            print(f"::error::PYTEST-FAIL-REASON {str(report.longrepr)[:1200]}")
        if len(seen) >= 25:
            break


_failed_reports = pytest.StashKey[list[pytest.TestReport]]()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call) -> pytest.TestReport:
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        session = item.session
        reports = session.config.stash.setdefault(_failed_reports, [])
        reports.append(report)
    return report
