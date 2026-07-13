from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_uses_unified_authenticated_runtime_and_persistent_root():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert "knowledge-base" not in services
    for service_name in ("cognitive-os", "inspiration-research"):
        service = services[service_name]
        environment = set(service["environment"])
        assert "COGNITIVE_ENV=production" in environment
        assert "COGNITIVE_AUTH_ENABLED=true" in environment
        assert "COGNITIVE_DATA_DIR=/app/data" in environment
        assert any(item.startswith("COGNITIVE_API_KEY=${COGNITIVE_API_KEY:?") for item in environment)
        assert any(item.startswith("COGNITIVE_JWT_SECRET=${COGNITIVE_JWT_SECRET:?") for item in environment)
        assert any(item.startswith("COGNITIVE_CORS_ORIGINS=${COGNITIVE_CORS_ORIGINS:?") for item in environment)
        assert "cognitive-data:/app/data" in service["volumes"]
    assert "cognitive-data" in compose["volumes"]


def test_docker_and_launchers_reference_packaged_knowledge_base():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY pyproject.toml ." in dockerfile
    assert "COPY knowledge_base/ ./knowledge_base/" in dockerfile
    assert "USER cognitive" in dockerfile
    assert "USER cognitive" in (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    for name in ("run_all.sh", "run_all.bat"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "Knowledge-Base.api" not in text
        assert "8000/kb/docs" in text
    assert "D:\\All projects" not in (ROOT / "run_all.bat").read_text(encoding="utf-8")
