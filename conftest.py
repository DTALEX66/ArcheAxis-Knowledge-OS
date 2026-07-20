"""Hermetic repository-wide pytest environment."""

from __future__ import annotations

import atexit
import os
from pathlib import Path
from tempfile import TemporaryDirectory

_PROJECT_ROOT = Path(__file__).resolve().parent
_TASK_RUNTIME = _PROJECT_ROOT / ".hermes" / "task-runtime"
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

_RUNTIME = TemporaryDirectory(prefix="cognitive-pytest-", dir=_TASK_TMP)
os.environ["COGNITIVE_DATA_DIR"] = _RUNTIME.name
atexit.register(_RUNTIME.cleanup)


def pytest_configure() -> None:
    from app.memory import database as memory_database
    from shared import migration, storage

    storage.init()
    memory_database.init_db()
    migration.migrate(db_path=storage.DB_PATH, backup_dir=migration.BACKUP_DIR)
