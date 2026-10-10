"""Regression cases for stale task/grant routing, broken links and unsafe locators."""
import json
from pathlib import Path

import pytest

from scripts.maintenance.authority_routes import check_routes, public_path, resolve


def fixture(root: Path) -> dict:
    data = {
        "schema": "archeaxis.authority-routes/v1",
        "active_pointer": "docs/current/AAOS-ACTIVE-EXECUTION.json",
        "entries": [{"path": name, "role": "LIVE_NAVIGATION"}
                    for name in ("README.md", "AUTHORITY.md", "AGENTS.md")]
                   + [{"path": "docs/current/AAOS-ACTIVE-EXECUTION.json", "role": "ACTIVE_ROUTER"}],
        "aliases": [{"old_path": "docs/old.md", "canonical_path": "docs/new.md"}],
        "rules": [
            {"pattern": "docs/history/frozen/**", "role": "FROZEN_SOURCE_INPUT"},
            {"pattern": "docs/current/**", "role": "DATED_SCOPED_RECORD_NOT_AUTOMATIC_AUTHORITY"},
            {"pattern": "*.md", "role": "REFERENCE_REQUIRES_CONCERN_AUTHORITY"},
        ],
    }
    pointer = {
        "authority_routes": "docs/current/AAOS-AUTHORITY-ROUTES.json",
        "execution_control": {"state": "PAUSED_BY_OWNER", "automatic_continuation": False},
        "frozen_source_inputs": [{"state": "FROZEN_BY_OWNER", "execution": "NOT_EXECUTED",
                                  "index": "docs/history/frozen/INDEX.md", "manifest": "docs/history/frozen/MANIFEST.json"}],
    }
    files = {
        "README.md": "[routes](docs/current/AAOS-AUTHORITY-ROUTES.json)\n",
        "AUTHORITY.md": "AAOS-AUTHORITY-ROUTES.json\n",
        "AGENTS.md": "AAOS-AUTHORITY-ROUTES.json\n",
        "docs/new.md": "canonical\n",
        "docs/history/frozen/INDEX.md": "frozen\n",
        "docs/history/frozen/MANIFEST.json": "{}\n",
        "docs/current/AAOS-ACTIVE-EXECUTION.json": json.dumps(pointer),
        "docs/current/AAOS-AUTHORITY-ROUTES.json": json.dumps(data),
    }
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return data


def save(root: Path, data: dict) -> None:
    (root / "docs/current/AAOS-AUTHORITY-ROUTES.json").write_text(json.dumps(data), encoding="utf-8")


def test_clean_routes_and_old_locator_resolve(tmp_path):
    data = fixture(tmp_path)
    assert check_routes(tmp_path) == []
    assert resolve("docs/old.md", data, tmp_path)["canonical_path"] == "docs/new.md"
    assert resolve("docs/current/AAOS01-AGENT-HANDOFF-20261006.txt", data, tmp_path)["role"].startswith("DATED_")


def test_old_handoff_cannot_be_promoted_to_active_queue(tmp_path):
    data = fixture(tmp_path)
    name = "docs/current/AAOS01-AGENT-HANDOFF-20261006.txt"
    (tmp_path / name).write_text("old grant", encoding="utf-8")
    data["entries"].append({"path": name, "role": "ACTIVE_ROUTER"})
    save(tmp_path, data)
    assert any("historical path promoted" in e for e in check_routes(tmp_path))


def test_frozen_source_cannot_be_masked_by_a_live_exact_route(tmp_path):
    data = fixture(tmp_path)
    data["entries"].append({"path": "docs/history/frozen/INDEX.md", "role": "ACTIVE_ROUTER"})
    save(tmp_path, data)
    assert any("frozen input routing missing" in e for e in check_routes(tmp_path))


def test_broken_live_link_and_alias_are_reported(tmp_path):
    data = fixture(tmp_path)
    (tmp_path / "README.md").write_text("AAOS-AUTHORITY-ROUTES.json [bad](docs/missing.md)", encoding="utf-8")
    data["aliases"][0]["canonical_path"] = "docs/gone.md"
    save(tmp_path, data)
    errors = check_routes(tmp_path)
    assert any("missing alias destination" in e for e in errors)
    assert any("unresolved live link" in e for e in errors)


@pytest.mark.parametrize("name", ["../other/AGENTS.md", "E:/protected.md", "C:/Users/private.md", ".codex/session.json", ".env", "docs/../private.md"])
def test_private_absolute_and_traversal_paths_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        public_path(tmp_path, name)


def test_selected_tasks_dont_override_owner_pause(tmp_path):
    fixture(tmp_path)
    path = tmp_path / "docs/current/AAOS-ACTIVE-EXECUTION.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["execution_control"]["automatic_continuation"] = True
    data["selected_tasks"] = ["UF13"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert any("continuation" in e for e in check_routes(tmp_path))


def test_registry_missing_is_a_failure(tmp_path):
    assert check_routes(tmp_path)


def test_empty_registry_cannot_silently_disable_entry_checks(tmp_path):
    data = fixture(tmp_path)
    data["entries"] = []
    save(tmp_path, data)
    assert any("required public entry" in e for e in check_routes(tmp_path))
