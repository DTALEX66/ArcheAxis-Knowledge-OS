"""Legacy HTTP compatibility journeys over an isolated, test-owned service.

The card router and AI reply here are legacy contracts. This suite verifies those
handlers through real loopback HTTP; it does not qualify the current product host
or a model call.
"""
from __future__ import annotations

import hashlib
import os
import socket
import threading
import time
from pathlib import Path

import pytest
import requests
import uvicorn
from fastapi import FastAPI


@pytest.fixture(scope="module")
def legacy_base_url(tmp_path_factory: pytest.TempPathFactory):
    # pytest's task-owned temp root comes from tests/conftest.py in the OS job.
    root = tmp_path_factory.mktemp("legacy-e2e")
    # Context rolls back every mutation even if an import or startup fails.
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ARCHEAXIS_DATA_DIR", str(root / "data"))
        patch.chdir(root)  # Legacy upload module creates its relative directory on import.
        from app.api import ai_chat, upload
        from app.workspace import system
        from archeaxis.learning import api as cards

        patch.setattr(upload, "UPLOAD_DIR", root / "uploads")
        upload.UPLOAD_DIR.mkdir()
        patch.setattr(cards, "cards_db", {})
        patch.setattr(system, "DB_PATH", root / "data" / "legacy-handshake.sqlite")

        app = FastAPI(title="ArcheAxis legacy compatibility test service")
        for router in (system.router, upload.router, cards.router, ai_chat.router):
            app.include_router(router)

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        session = requests.Session()
        session.trust_env = False  # Loopback must never follow user or CI proxy settings.
        thread = None
        server = None
        port = None
        try:
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            port = listener.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="off", log_level="warning", access_log=False))
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
            thread.start()
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started, "isolated legacy service did not start"
            yield f"http://127.0.0.1:{port}", session
        finally:
            if server is not None:
                server.should_exit = True
            if thread is not None:
                thread.join(timeout=10)
            session.close()
            listener.close()
            assert thread is None or not thread.is_alive(), "isolated legacy service did not stop"
            if port is not None:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    probe.settimeout(0.2)
                    assert probe.connect_ex(("127.0.0.1", port)) != 0, "isolated legacy port still accepts connections"


class TestEndToEnd:
    """Legacy compatibility workflow checks against actual HTTP handlers."""

    def test_system_handshake(self, legacy_base_url):
        base_url, client = legacy_base_url
        response = client.get(f"{base_url}/api/v1/system/handshake", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == "archeaxis-workspace"
        assert "backend_version" in data

    def test_file_upload_workflow(self, legacy_base_url):
        base_url, client = legacy_base_url
        test_content = b"Test PDF content for upload test"
        test_hash = hashlib.sha256(test_content).hexdigest()
        files = {"file": ("test.pdf", test_content, "application/pdf")}
        response = client.post(f"{base_url}/api/v1/upload/document", files=files, timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["file_id"] == test_hash
        assert data["type"] == "pdf"
        assert (Path(data["path"])).is_relative_to(Path(os.environ["ARCHEAXIS_DATA_DIR"]).parent / "uploads")

    def test_learning_card_workflow(self, legacy_base_url):
        base_url, client = legacy_base_url
        card_id = "test-card-001"
        response = client.post(f"{base_url}/api/v1/learning/cards?card_id={card_id}", timeout=5)
        assert response.status_code == 200
        response = client.get(f"{base_url}/api/v1/learning/cards/{card_id}", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["card_id"] == card_id
        assert data["reps"] == 0
        review_data = {"card_id": card_id, "rating": 3}
        response = client.post(f"{base_url}/api/v1/learning/cards/{card_id}/review", json=review_data, timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["next_interval_days"] > 0
        assert data["stability"] > 0

    def test_ai_chat_workflow(self, legacy_base_url):
        base_url, client = legacy_base_url
        chat_data = {"message": "你好，小栖", "context": "测试对话", "history": []}
        response = client.post(f"{base_url}/api/v1/ai/chat", json=chat_data, timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
        assert data["state"] in ["idle", "thinking"]

    def test_learning_stats(self, legacy_base_url):
        base_url, client = legacy_base_url
        response = client.get(f"{base_url}/api/v1/learning/stats", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "total_cards" in data
        assert "due_today" in data

    def test_upload_status_check(self, legacy_base_url):
        base_url, client = legacy_base_url
        test_file_id = "abc123"
        response = client.get(f"{base_url}/api/v1/upload/status/{test_file_id}", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "exists" in data

    def test_ai_status(self, legacy_base_url):
        base_url, client = legacy_base_url
        response = client.get(f"{base_url}/api/v1/ai/status", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "capabilities" in data
