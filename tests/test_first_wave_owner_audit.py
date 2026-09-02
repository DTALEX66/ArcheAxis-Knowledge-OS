"""Regression coverage for the G0 source-only owner inventory."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "audit_first_wave_owners.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("first_wave_owner_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_lists_only_production_python_sqlite_connection_sites(tmp_path: Path) -> None:
    (tmp_path / "app" / "workspace").mkdir(parents=True)
    (tmp_path / "app" / "tests").mkdir(parents=True)
    (tmp_path / "shared").mkdir()
    (tmp_path / "app" / "workspace" / "service.py").write_text(
        "import sqlite3\nsqlite3.connect('workspace.db')\n", encoding="utf-8"
    )
    (tmp_path / "app" / "tests" / "test_service.py").write_text(
        "import sqlite3\nsqlite3.connect(':memory:')\n", encoding="utf-8"
    )
    (tmp_path / "shared" / "reader.py").write_text("VALUE = 1\n", encoding="utf-8")

    module = _load_module()

    assert module.audit_sqlite_connection_owners(tmp_path) == [
        "app/workspace/service.py"
    ]


def test_current_first_wave_inventory_keeps_the_documented_owner_count() -> None:
    module = _load_module()

    owners = module.audit_sqlite_connection_owners(ROOT)

    assert len(owners) == 58
    assert "app/workspace/service.py" in owners
    assert "app/learning/event_store.py" in owners
