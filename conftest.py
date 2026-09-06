"""Hermetic repository-wide pytest environment."""

from __future__ import annotations

import atexit
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.runtime.dev import pytest_environment as _pytest_environment

_PROJECT_ROOT = Path(__file__).resolve().parent
_TASK_RUNTIME = _pytest_environment(_PROJECT_ROOT)
_TASK_TMP = _TASK_RUNTIME / "tmp"
_TASK_PYCACHE = _TASK_RUNTIME / "pycache"
for _path in (_TASK_TMP, _TASK_PYCACHE):
    _path.mkdir(parents=True, exist_ok=True)
for _name, _path in (
    ("TMP", _TASK_TMP),
    ("TEMP", _TASK_TMP),
    ("TMPDIR", _TASK_TMP),
    ("PYTHONPYCACHEPREFIX", _TASK_PYCACHE),
):
    os.environ[_name] = str(_path)

_RUNTIME = TemporaryDirectory(prefix="archeaxis-pytest-", dir=_TASK_TMP)
os.environ["ARCHEAXIS_DATA_DIR"] = _RUNTIME.name
os.environ.pop("COGNITIVE_DATA_DIR", None)
atexit.register(_RUNTIME.cleanup)


def pytest_configure() -> None:
    from shared import migration, storage
    from shared.migration_runner import MigrationOperator, default_registry

    storage.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(storage.DB_PATH)):
        pass
    operator = MigrationOperator(db_path=storage.DB_PATH, backup_dir=migration.BACKUP_DIR)
    for owner in default_registry().owners:
        if owner.kind.startswith("sqlite"):
            operator.apply(owner.owner)
