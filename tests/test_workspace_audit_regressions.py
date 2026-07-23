from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request


def test_workspace_product_intake_response_hides_internal_ids(monkeypatch) -> None:
    from app.main import app
    from app.workspace import router

    monkeypatch.setattr(
        router.service,
        "intake_url",
        lambda **_kwargs: {
            "source_type": "web",
            "source": "https://example.com/article",
            "package_id": "pkg_internal",
            "job_id": "job_internal",
            "status": "candidate",
            "requires_human_review": True,
            "source_count": 1,
            "claim_count": 2,
            "evidence_count": 3,
        },
    )

    response = TestClient(app).post(
        "/workspace/api/intake/url",
        json={"url": "https://example.com/article"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "source_type": "web",
        "requires_human_review": True,
        "source_count": 1,
        "claim_count": 2,
        "evidence_count": 3,
    }


def test_workspace_upload_reads_only_one_byte_beyond_the_limit(monkeypatch) -> None:
    from app.workspace import router, service

    requested_sizes: list[int] = []

    class OversizedUpload:
        filename = "oversized.txt"

        async def read(self, size: int = -1) -> bytes:
            requested_sizes.append(size)
            return b"x" * size

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/workspace/api/intake/upload",
            "headers": [(b"host", b"testserver")],
            "client": ("testclient", 50000),
        }
    )
    monkeypatch.setattr(
        router.service,
        "intake_upload",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("service must not receive oversized data")
        ),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(router.intake_upload(request=request, file=OversizedUpload()))

    assert error.value.status_code == 422
    assert requested_sizes == [service.MAX_INTAKE_UPLOAD_BYTES + 1]


def test_workspace_research_queue_and_approval_use_only_user_readable_source(monkeypatch) -> None:
    from app.main import app
    from app.workspace import router

    source = "https://example.com/research"
    monkeypatch.setattr(
        router.service, "research_review_queue", lambda **_kwargs: {"schema_version": "v1", "items": [
            {"source": source, "claim_count": 2, "evidence_count": 3,
             "verification": "unverified", "created_at": "2026-07-23T00:00:00Z"}
        ]},
    )
    received = {}
    monkeypatch.setattr(router.service, "promote_research_source", lambda **kwargs: received.update(kwargs) or {"status": "candidate"})
    client = TestClient(app)

    queue = client.get("/workspace/api/research")
    assert queue.status_code == 200
    assert queue.json()["items"][0]["source"] == source
    assert not ({"package_id", "unit_id", "artifact_id", "command_id"} & queue.json()["items"][0].keys())
    approved = client.post("/workspace/api/research/approve", json={
        "command_id": "ui-review-1", "source": source,
    })
    assert approved.status_code == 200
    assert received["source"] == source
    assert "package_id" not in received
