"""R10 adapter (first slice): the host side addresses the Core only through the
Core's own API, and the request shapes say so.

These tests assert the built requests (no running Core needed) and pin the
boundaries that matter: authentication is a launch token header, identity is never
taken from a body, a learning event always carries a persistent client event id,
and a correction travels as `modified` with the new content instead of rewriting
the old body.
"""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "shared" / "core_client.py"


def _load():
    spec = importlib.util.spec_from_file_location("core_client_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load()


class TestAuthAndIdentity:
    def test_the_launch_token_travels_in_a_header_only(self) -> None:
        headers = core.headers("t" * 64)
        assert headers[core.TOKEN_HEADER] == "t" * 64
        assert core.headers(None) == {"Content-Type": "application/json"}

    def test_no_body_ever_carries_an_actor_or_token(self) -> None:
        bodies = [
            core.import_request("note.md", b"hello"),
            core.learning_event_request("card-1", True, "evt-1"),
            core.reference_request("card-1", "k_abc"),
            core.review_request("accepted", "owner"),
        ]
        for body in bodies:
            assert "actor" not in body, body
            assert core.TOKEN_HEADER not in body, body
            assert "launch_token" not in body, body


class TestRequestShapes:
    def test_import_sends_base64_content(self) -> None:
        body = core.import_request("note.md", b"hello 6371")
        assert body["name"] == "note.md"
        assert base64.b64decode(body["content_base64"]) == b"hello 6371"

    def test_import_refuses_an_empty_source(self) -> None:
        for bad in [("note.md", b""), ("", b"x")]:
            try:
                core.import_request(*bad)
            except ValueError:
                continue
            raise AssertionError(f"expected a refusal for {bad!r}")

    def test_search_can_ask_for_current_revisions_only(self) -> None:
        assert core.search_path("6371") == "/api/v1/search?q=6371"
        assert core.search_path("6371", active_only=True) == "/api/v1/search?q=6371&active_only=true"
        assert "a%20b" in core.search_path("a b"), "queries must be URL-encoded"

    def test_learning_events_require_a_persistent_event_id(self) -> None:
        body = core.learning_event_request("card-1", False, "evt-9", schedule_state={"stability": 3.0})
        assert body["client_event_id"] == "evt-9"
        assert body["correct"] is False
        assert body["schedule_state"] == {"stability": 3.0}
        try:
            core.learning_event_request("card-1", True, "   ")
        except ValueError:
            pass
        else:
            raise AssertionError("an event without a persistent id must be refused")

    def test_a_correction_is_a_modified_review_with_new_content(self) -> None:
        body = core.review_request("modified", "owner", new_body="radius 6371.0088 km", note="fix")
        assert body["action"] == "modified"
        assert body["new_body"] == "radius 6371.0088 km"
        assert "body" not in body, "acceptance must not overwrite the existing body"
        try:
            core.review_request("rewrite", "owner")
        except ValueError:
            pass
        else:
            raise AssertionError("an unknown review action must be refused")

    def test_calling_returns_an_error_status_instead_of_raising(self) -> None:
        # Nothing listens on this port: the call must report a status, not crash.
        status, payload = core.call("http://127.0.0.1:9", "GET", "/api/v1/system/version", None, timeout=2)
        assert status != 200
        assert payload is not None


class _FakeCore:
    """Records the calls a journey makes and answers with canned payloads."""

    def __init__(self, fail_step: str | None = None) -> None:
        self.calls: list[tuple[str, str, object]] = []
        self.fail_step = fail_step

    def __call__(self, base_url, method, path, token, body=None, timeout=30.0):
        self.calls.append((method, path, body))
        if self.fail_step and self.fail_step in path:
            return 503, {"error": "unavailable"}
        if path.endswith("/system/version"):
            return 200, {"runtime": "archeaxis-api"}
        if path.endswith("/imports"):
            return 202, {"source_id": "src-1"}
        if path.startswith("/api/v1/search"):
            return 200, {"count": 1, "items": [{"knowledge_id": "k_rev1", "active": True}]}
        if path.endswith("/learning/events"):
            return 201, {"event_id": 1, "duplicate": False}
        if "/references" in path:
            return 201, {"knowledge_id": "k_rev1"}
        return 404, {"error": "unexpected path"}


class TestJourney:
    def _run(self, fake: _FakeCore) -> dict:
        return core.run_journey(
            fake,
            "http://127.0.0.1:1",
            "t" * 64,
            "note.md",
            b"radius 6371 km",
            "6371",
            "card-1",
            "evt-1",
        )

    def test_the_journey_order_is_reachability_import_search_event_reference(self) -> None:
        fake = _FakeCore()
        result = self._run(fake)
        assert result["ok"] is True, result
        paths = [path for _method, path, _body in fake.calls]
        assert paths[0].endswith("/system/version")
        assert paths[1].endswith("/imports")
        assert paths[2].startswith("/api/v1/search")
        assert paths[3].endswith("/learning/events")
        assert paths[4].endswith("/learning/items/card-1/references")
        assert result["source_id"] == "src-1"
        assert result["referenced_revision"] == "k_rev1"
        # The journey never performs a human review by itself.
        assert not any("/review-decisions" in path for path in paths), paths
        assert "human action" in result["note"]

    def test_a_failed_step_stops_the_journey_and_is_reported(self) -> None:
        fake = _FakeCore(fail_step="/imports")
        result = self._run(fake)
        assert result["ok"] is False
        assert result["failed_step"] == "import"
        # Nothing after the failure was attempted.
        assert all(not path.startswith("/api/v1/search") for _m, path, _b in fake.calls), fake.calls

    def test_search_asks_for_current_revisions_only(self) -> None:
        fake = _FakeCore()
        self._run(fake)
        _method, search_call, _body = next(c for c in fake.calls if c[1].startswith("/api/v1/search"))
        assert "active_only=true" in search_call, search_call
