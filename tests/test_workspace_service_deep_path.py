"""A workspace database at the depth the product actually builds has to answer.

The service handed SQLite a plain name at 23 call sites.  Under a deep workspace root every
command then failed with `unable to open database file` - wording that reads as "there is no
database here" while the file was present and migrated, so an operator would have rebuilt the
workspace instead of naming the path correctly.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

DATABASE_NAME = "workspace.sqlite"
# Measured on this volume: a plain create works at 251 characters and is refused at 252, while a
# plain open of `directory/name` is refused as soon as the whole name passes 260. The database
# file is therefore placed in a directory that a plain call can still create.
CREATABLE_DIRECTORY_LIMIT = 251
TARGET_DIRECTORY = 248


def _deep_database(tmp_path: Path) -> Path:
    """A database whose directory a plain call creates and whose plain name the API refuses."""
    node = tmp_path / "workspace"
    if len(str(node)) > TARGET_DIRECTORY:
        pytest.skip(f"the temporary base is already {len(str(node))} characters deep")
    node.mkdir(parents=True, exist_ok=True)
    while len(str(node / ("c" * 24))) <= TARGET_DIRECTORY - 26:
        node = node / ("c" * 24)
        node.mkdir(parents=True, exist_ok=True)
    remainder = TARGET_DIRECTORY - len(str(node)) - 1
    if remainder > 1:
        node = node / ("c" * (remainder - 1))
        node.mkdir(parents=True, exist_ok=True)
    assert len(str(node)) <= CREATABLE_DIRECTORY_LIMIT, "the directory must be plain-creatable"
    assert len(str(node / DATABASE_NAME)) > CREATABLE_DIRECTORY_LIMIT + 9, \
        "only the database name is over the limit, which is what SQLite is handed"
    return node / DATABASE_NAME


def _migrated(tmp_path: Path) -> Path:
    """A real governed workspace database, created at the depth the product builds."""
    from shared.migration_runner import MigrationOperator
    from shared.paths import native_path

    database = _deep_database(tmp_path)
    Path(native_path(database)).touch()
    operator = MigrationOperator(db_path=database, backup_dir=database.parent / "backups")
    for owner in ("research.sqlite", "core.sqlite", "knowledge-governance.sqlite", "workspace.sqlite"):
        operator.apply(owner)
    return database


def test_the_service_reads_a_migrated_workspace_at_the_host_depth(tmp_path: Path) -> None:
    service = importlib.import_module("app.workspace.service")
    database = _migrated(tmp_path)

    assert len(str(database)) >= 261, "the test only means something at the refused depth"
    jobs = service.workspace_jobs(db_path=database)
    assert jobs["schema_version"] == "v1" and jobs["jobs"] == []
    library = service.workspace_library(db_path=database)
    assert library["schema_version"] == "v1" and library["items"] == []


def test_the_service_writes_through_the_same_name(tmp_path: Path, monkeypatch) -> None:
    """One real intake writes job, outbox and receipt through the same naming rule."""
    from tests.workspace_capture_stub import capture_web_stub

    service = importlib.import_module("app.workspace.service")
    database = _migrated(tmp_path)
    monkeypatch.setattr(service, "capture_web", capture_web_stub("# deep\nWritten at depth."))

    intake = service.intake_url(url="https://example.com/deep", db_path=database)

    assert intake["status"] == "candidate"
    jobs = service.workspace_jobs(db_path=database)["jobs"]
    assert [job["state"] for job in jobs] == ["succeeded"], jobs
    assert service.intake_job(job_id=intake["job_id"], db_path=database)["job_id"] == intake["job_id"]


@pytest.mark.skipif(sys.platform != "win32", reason="the refusal being guarded against is Windows-only")
def test_the_depth_alone_is_what_lost_the_database_without_the_prefix(tmp_path: Path, monkeypatch) -> None:
    """Disable the prefix and require the old failure back, or the tests above prove nothing."""
    service = importlib.import_module("app.workspace.service")
    paths = importlib.import_module("shared.paths")
    database = _migrated(tmp_path)
    monkeypatch.setattr(service, "native_path", lambda path: str(path))
    with pytest.raises(sqlite3.OperationalError):
        service.workspace_jobs(db_path=database)
    monkeypatch.setattr(service, "native_path", paths.native_path)
    assert service.workspace_jobs(db_path=database)["jobs"] == []
