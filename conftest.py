"""Hermetic repository-wide pytest environment."""

from __future__ import annotations

import atexit
import os
from tempfile import TemporaryDirectory

_RUNTIME = TemporaryDirectory(prefix="cognitive-pytest-")
os.environ["COGNITIVE_DATA_DIR"] = _RUNTIME.name
atexit.register(_RUNTIME.cleanup)


def pytest_configure() -> None:
    from app.memory import database as memory_database
    from shared import migration, storage

    storage.init()
    memory_database.init_db()
    migration.migrate(db_path=storage.DB_PATH, backup_dir=migration.BACKUP_DIR)
