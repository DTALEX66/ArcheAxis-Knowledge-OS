"""AXW-022A: workspace HTTP endpoint serves content-addressed PDF bytes to the
PDF.js reader. Uses real PDF fixtures (text + images) from the desktop
attachments dir to prove end-to-end byte fidelity over the HTTP boundary.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.evidence.pdf_serve import build_pdf_serving_root, store_pdf_bytes

# Real user-supplied PDFs (text + illustrations). These live in the canonical
# workspace's runtime attachments dir, which is NOT part of any git worktree,
# so CI without local fixtures skips them (never fabricate). Only run locally.
_REAL_PDFS = [
    Path(r"D:/All projects/ArcheAxis-Knowledge-OS/.hermes/desktop-attachments/时间简史（插图本）.pdf"),
    Path(r"D:/All projects/ArcheAxis-Knowledge-OS/.hermes/desktop-attachments/牛津通识读本：缤纷的语言学（中文版）.pdf"),
]


def _client(tmp_path, monkeypatch):
    from app.main import app
    from app.workspace import router

    pdf_root = build_pdf_serving_root(tmp_path)
    monkeypatch.setattr(router, "PDF_ROOT", pdf_root)
    monkeypatch.setattr(router, "DB_PATH", tmp_path / "ws.sqlite")
    return TestClient(app), pdf_root


def _available_real_pdf() -> Path | None:
    for p in _REAL_PDFS:
        if p.is_file():
            return p
    return None


def test_pdf_endpoint_serves_real_pdf_bytes(monkeypatch, tmp_path) -> None:
    """Store a real PDF into the serving root, then read it back over the
    HTTP endpoint; the bytes must match exactly (content-addressed fidelity)."""
    real = _available_real_pdf()
    if real is None:
        import pytest

        pytest.skip("no real PDF fixture present in desktop-attachments")

    blob = real.read_bytes()
    client, pdf_root = _client(tmp_path, monkeypatch)
    key = store_pdf_bytes(pdf_root, blob)

    resp = client.get(f"/workspace/api/pdf/{key}")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    # Byte-for-byte identity of the served PDF vs the on-disk original.
    assert resp.content == blob
    assert hashlib.sha256(resp.content).hexdigest() == hashlib.sha256(blob).hexdigest()


def test_pdf_endpoint_rejects_non_sha256_key(monkeypatch, tmp_path) -> None:
    client, _ = _client(tmp_path, monkeypatch)
    resp = client.get("/workspace/api/pdf/not-a-sha256-key")
    # fail-closed: non-sha256 content key is rejected, never served.
    assert resp.status_code == 404


def test_pdf_endpoint_missing_content_404(monkeypatch, tmp_path) -> None:
    client, _ = _client(tmp_path, monkeypatch)
    digest = "sha256:" + "0" * 64
    resp = client.get(f"/workspace/api/pdf/{digest}")
    assert resp.status_code == 404


def test_pdf_endpoint_serves_both_real_pdfs(monkeypatch, tmp_path) -> None:
    """Both user-supplied PDFs (a 322-page illustrated book + a 120-page
    text book) must round-trip byte-exact over the HTTP endpoint."""
    present = [p for p in _REAL_PDFS if p.is_file()]
    if len(present) < 2:
        import pytest

        pytest.skip("need both real PDFs present")

    client, pdf_root = _client(tmp_path, monkeypatch)
    for real in present:
        blob = real.read_bytes()
        key = store_pdf_bytes(pdf_root, blob)
        resp = client.get(f"/workspace/api/pdf/{key}")
        assert resp.status_code == 200, real.name
        assert resp.content == blob, f"byte mismatch for {real.name}"
        assert resp.headers["content-type"] == "application/pdf"
