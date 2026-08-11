"""AXW-022B tests: evidence anchor HTTP API (create + resolve + fail-closed).

Verifies the content-addressed evidence anchor endpoints:
- POST /api/evidence/anchor creates a stable anchor_id from raw_sha256 +
  source_revision + locator.
- GET /api/evidence/anchor/{anchor_id} resolves it back (jump-back).
- Invalid input (missing fields) is rejected (fail-closed).
"""

from fastapi.testclient import TestClient

from app.main import app

_CLIENT = TestClient(app)
_SHA = "9d35e2a6a29d81d117b223298f94fd228003599e54462adcc796fada6ad284c5"


def test_create_and_resolve_anchor_roundtrip() -> None:
    resp = _CLIENT.post(
        "/workspace/api/evidence/anchor",
        json={
            "raw_sha256": _SHA,
            "source_revision": "main@ebf7124",
            "locator": {"page": 1, "char_start": 0, "char_end": 42},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    anchor_id = body["anchor_id"]
    assert isinstance(anchor_id, str) and anchor_id.startswith("ev")

    resolved = _CLIENT.get(f"/workspace/api/evidence/anchor/{anchor_id}")
    assert resolved.status_code == 200, resolved.text
    r = resolved.json()
    assert r["raw_sha256"] == _SHA
    assert r["source_revision"] == "main@ebf7124"
    assert r["locator"]["page"] == 1


def test_create_anchor_missing_fields_fail_closed() -> None:
    resp = _CLIENT.post(
        "/workspace/api/evidence/anchor",
        json={"raw_sha256": _SHA, "locator": {"page": 1}},
    )
    # Missing source_revision must be rejected, not silently stored.
    assert resp.status_code in (400, 422)


def test_resolve_missing_anchor_returns_404() -> None:
    resp = _CLIENT.get("/workspace/api/evidence/anchor/ev-does-not-exist-000000")
    assert resp.status_code == 404


def test_anchor_rejects_bad_sha_shape() -> None:
    resp = _CLIENT.post(
        "/workspace/api/evidence/anchor",
        json={
            "raw_sha256": "too-short",
            "source_revision": "main",
            "locator": {"page": 1},
        },
    )
    # raw_sha256 must be >= 40 chars (sha256 length).
    assert resp.status_code in (400, 422)
