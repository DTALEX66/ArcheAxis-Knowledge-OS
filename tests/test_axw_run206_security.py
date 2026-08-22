"""AXW-RUN-206: loopback security headers + CORS tightening."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_security_headers_present_on_every_response(client: TestClient) -> None:
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]


def test_cors_rejects_non_loopback_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/system/handshake",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_loopback_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/system/handshake",
        headers={
            "Origin": "http://127.0.0.1:43123",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:43123"


def test_cors_rejects_non_loopback_localhost_variant(client: TestClient) -> None:
    # only 127.0.0.1 / localhost are allowed, other hostnames are not
    response = client.options(
        "/api/v1/system/handshake",
        headers={
            "Origin": "http://myhost:43123",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400


def test_cors_allows_tauri_local_origin_and_launch_token_header(client: TestClient) -> None:
    response = client.options(
        "/workspace/api/v1/home",
        headers={
            "Origin": "http://tauri.localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-archeaxis-launch-token",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost:5173"
    assert "x-archeaxis-launch-token" in response.headers["access-control-allow-headers"].casefold()
