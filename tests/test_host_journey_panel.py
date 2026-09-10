"""R10: the host panel must project the Core honestly or say nothing.

DeepTutor is an immutable external dependency, so host integration is project-side:
`scripts/host/journey_panel.py` serves the mountable URL. These tests pin the two
rules that make it trustworthy - the two readings stay separate, and an unreachable
Core renders no state at all - plus the token handling, which must never reach the
page, a query string or a log line.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "host" / "journey_panel.py"

LEARNER = {
    "event_count": 3,
    "correct_streak": 2,
    "scheduled_events": 2,
    "unscheduled_events": 1,
    "references": [{"knowledge_id": "k_1", "active": True}],
    "recording": "a human records learning outcomes through the learning-events endpoint",
}
MACHINE = {"status": "not_recorded", "note": "machine capability receipts are written by the machine loop"}


def _load():
    spec = importlib.util.spec_from_file_location("journey_panel_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


panel = _load()


def _call_returning(status: int, body):
    calls: list[tuple] = []

    def call(base_url, method, path, token, body_arg=None, timeout=30.0):
        calls.append((base_url, method, path, token))
        return status, body

    return call, calls


# ------------------------------------------------------------------- payload


def test_state_separates_the_learner_reading_from_the_machine_reading():
    call, calls = _call_returning(200, {"item_key": "card-1", "learner": LEARNER, "machine": MACHINE})
    status, payload = panel.build_state("http://core", "card-1", "tok", call=call)
    assert status == 200
    assert payload["core"] == {"reachable": True, "status": 200}
    assert payload["learner"] == LEARNER
    assert payload["machine"] == MACHINE
    # the panel asks the Core for the item state, under the Core's own prefix
    assert calls == [("http://core", "GET", f"{panel.CORE_BASE}/learning/items/card-1/state", "tok")]
    assert "never presented as machine competence" in payload["note"]


def test_an_unreachable_core_leaves_both_readings_empty():
    call, _ = _call_returning(0, {"error": "core unreachable: connection refused"})
    status, payload = panel.build_state("http://core", "card-1", "tok", call=call)
    assert status == 503
    assert payload["core"]["reachable"] is False
    assert "connection refused" in payload["core"]["reason"]
    assert payload["learner"] is None and payload["machine"] is None
    assert "no state is shown" in payload["rendering"]


def test_an_error_status_is_not_rendered_as_an_empty_history():
    """A 404 or 500 must not look like an item with zero events."""
    call, _ = _call_returning(500, {"error": "boom"})
    status, payload = panel.build_state("http://core", "card-1", None, call=call)
    assert status == 503
    assert payload["learner"] is None


def test_item_keys_are_quoted_into_the_path():
    call, calls = _call_returning(200, {"learner": LEARNER, "machine": MACHINE})
    panel.build_state("http://core", "card with space/and-slash", None, call=call)
    assert calls[0][2] == f"{panel.CORE_BASE}/learning/items/card%20with%20space%2Fand-slash/state"


def test_health_reports_reachability_and_never_a_fake_ok():
    call, calls = _call_returning(200, "archeaxis 0.1.0")
    status, payload = panel.build_health("http://core", "tok", call=call)
    assert status == 200 and payload["reachable"] is True
    assert calls[0][2] == f"{panel.CORE_BASE}/system/version"

    call, _ = _call_returning(0, {"error": "core unreachable"})
    status, payload = panel.build_health("http://core", "tok", call=call)
    assert status == 503 and payload["reachable"] is False


# ---------------------------------------------------------------------- page


def test_the_page_shows_both_panels_and_the_unreachable_banner():
    page = panel.render_page("card-1")
    assert "学习者记录（人类）" in page
    assert "机器能力收据（AI）" in page
    assert "Core 不可达" in page
    assert 'id="item" value="card-1"' in page
    assert "project-side" in page


def test_the_page_never_contains_the_token_or_a_token_parameter():
    page = panel.render_page("card-1")
    assert "token" not in page.lower().replace("token_env", ""), "the page must not carry token handling"
    assert "launch_token" not in page
    # and the server reads it from the environment, not from the query string
    source = MODULE.read_text(encoding="utf-8")
    assert 'os.environ.get(self.server.token_env)' in source
    assert 'query.get("token")' not in source


def test_the_panel_binds_loopback_only_and_does_not_log_query_strings():
    source = MODULE.read_text(encoding="utf-8")
    assert 'ThreadingHTTPServer(("127.0.0.1", port)' in source
    # the access log drops everything after "?", so a token cannot land in a log
    assert 'split("?")[0]' in source


def test_cli_requires_a_core_url_and_reads_the_token_from_the_named_variable():
    source = MODULE.read_text(encoding="utf-8")
    assert '"--core-url", required=True' in source
    assert '"--token-env"' in source
    assert 'default="ARCHEAXIS_LAUNCH_TOKEN"' in source
    assert "token_present" in source
