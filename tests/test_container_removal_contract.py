from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_launch_is_not_coupled_to_removed_container_stack():
    assert (ROOT / "app" / "runtime_entrypoint.py").is_file()
    assert not (ROOT / "app" / "container_entrypoint.py").exists()
    assert not (ROOT / ".github" / "workflows" / "container.yml").exists()
    assert not (ROOT / "Dockerfile").exists()
    assert not (ROOT / "docker-compose.yml").exists()
    assert not (ROOT / "docker-compose.dev.yml").exists()

    cli = (ROOT / "app" / "cli.py").read_text(encoding="utf-8")
    assert "app.runtime_entrypoint" in cli
    assert "container_entrypoint" not in cli

    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python -m app.runtime_entrypoint migrate" in ci
    assert "app.container_entrypoint" not in ci
