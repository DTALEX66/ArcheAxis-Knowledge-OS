from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_uses_unified_authenticated_runtime_and_persistent_root():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert "knowledge-base" not in services
    assert "research" not in services
    service = services["core"]
    environment = service["environment"]
    assert environment["COGNITIVE_ENV"] == "production"
    assert environment["COGNITIVE_AUTH_ENABLED"] == "true"
    assert environment["COGNITIVE_DATA_DIR"] == "/app/data"
    assert environment["COGNITIVE_API_KEY"].startswith("${COGNITIVE_API_KEY:?")
    assert environment["COGNITIVE_JWT_SECRET"].startswith("${COGNITIVE_JWT_SECRET:?")
    assert environment["COGNITIVE_CORS_ORIGINS"].startswith("${COGNITIVE_CORS_ORIGINS:?")
    assert "cognitive-sqlite:/app/data" in service["volumes"]
    assert "ports" not in service
    assert services["caddy"]["depends_on"]["core"]["condition"] == "service_healthy"
    assert "research" not in services["caddy"].get("depends_on", {})
    assert "cognitive-sqlite" in compose["volumes"]


def test_docker_and_launchers_reference_packaged_knowledge_base():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY pyproject.toml uv.lock README.md ./" in dockerfile
    assert "COPY knowledge_base/ ./knowledge_base/" in dockerfile
    assert "uv build --python /usr/local/bin/python --wheel --no-build-isolation" in dockerfile
    assert "USER cognitive" in dockerfile
    assert not (ROOT / "docker" / "Dockerfile").exists()
    assert "app.main:app" in (ROOT / "app" / "container_entrypoint.py").read_text(encoding="utf-8")
    for name in ("run_all.sh", "run_all.bat"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "Knowledge-Base.api" not in text
        assert "8000/kb/docs" in text
    assert "D:\\All projects" not in (ROOT / "run_all.bat").read_text(encoding="utf-8")
