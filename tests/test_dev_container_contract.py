from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dev_container_uses_repo_mount_and_separate_runtime_data():
    compose = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")

    assert "dockerfile: Dockerfile.dev" in compose
    assert "- .:/workspace" in compose
    assert "cognitive-dev-data:/workspace/data" in compose
    assert "docker.sock" not in compose
    assert "cognitive-sqlite" not in compose
    assert "COGNITIVE_ENV: development" in compose


def test_dev_container_builds_dependencies_from_locked_project_inputs():
    dockerfile = (ROOT / "Dockerfile.dev").read_text(encoding="utf-8")

    assert "COPY pyproject.toml uv.lock README.md ./" in dockerfile
    assert "uv sync --frozen --extra dev --no-install-project" in dockerfile
    assert "UV_PROJECT_ENVIRONMENT=/opt/venv" in dockerfile
    assert "git openssh-client ca-certificates" in dockerfile
    assert "USER cognitive" in dockerfile


def test_dev_container_does_not_send_runtime_or_secret_files_to_build_context():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    for pattern in (".git", ".venv", "*.sqlite", "data", ".env", "logs"):
        assert pattern in dockerignore


def test_windows_dev_entrypoint_runs_only_the_dev_compose_stack():
    script = (ROOT / "run_dev_container.ps1").read_text(encoding="utf-8")

    assert "docker-compose.dev.yml" in script
    assert "docker compose" not in script
    assert "docker.sock" not in script
    assert "COGNITIVE-LOOP-OS" not in script
