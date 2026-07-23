"""Shared fixtures for deterministic, self-contained E2E transformation chain tests.

Every test receives an isolated, migrated SQLite database on a temporary filesystem.
No network, no real user content, no leaked IDs to C:\\Users\\ALEX.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from shared.migration_runner import MigrationOperator


@pytest.fixture
def workspace_db(tmp_path: Path) -> Path:
    """Isolated workspace with all applicable migrations applied."""
    database = tmp_path / "workspace.sqlite"
    # Sentinel table to ensure migration runner recognizes the owner
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("research.sqlite")
    operator.apply("workspace.sqlite")
    return database


@pytest.fixture
def full_db(tmp_path: Path) -> Path:
    """Isolated database with core + research + knowledge + workspace migrations."""
    database = tmp_path / "cognitive_os.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sentinel(id TEXT PRIMARY KEY)")
        connection.commit()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    for owner in (
        "core.sqlite",
        "research.sqlite",
        "knowledge-governance.sqlite",
        "taskpack.sqlite",
        "sleep-loop.sqlite",
        "workspace.sqlite",
    ):
        operator.apply(owner)
    return database
