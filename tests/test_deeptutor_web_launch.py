"""Project-side DeepTutor Web launch contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "launch" / "deeptutor_web.py"
spec = importlib.util.spec_from_file_location("deeptutor_web_under_test", MODULE)
assert spec and spec.loader
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stub", encoding="utf-8")
    return path


def test_resolve_installation_requires_the_pinned_version_and_runtime_files(tmp_path: Path):
    python = _touch(tmp_path / "python.exe")
    node = _touch(tmp_path / "node.exe")
    server = _touch(tmp_path / "deeptutor_web" / "server.js")

    result = web.resolve_installation(
        python=python, node=node, server=server,
        version_reader=lambda _: "1.5.17",
    )

    assert result == {"python": python, "node": node, "server": server}


def test_resolve_installation_rejects_drifted_version(tmp_path: Path):
    python = _touch(tmp_path / "python.exe")
    node = _touch(tmp_path / "node.exe")
    server = _touch(tmp_path / "server.js")

    with pytest.raises(web.LaunchError, match="requires DeepTutor 1.5.17"):
        web.resolve_installation(
            python=python, node=node, server=server,
            version_reader=lambda _: "1.6.0",
        )


def test_environment_is_loopback_and_does_not_forward_provider_state(tmp_path: Path):
    env = web.build_environment(
        {"PATH": "x", "OPENAI_API_KEY": "secret", "ANTHROPIC_API_KEY": "secret2",
         "DEEPTUTOR_HOME": "old", "PORT": "9999"},
        runtime_home=tmp_path / "home", backend_port=18001, frontend_port=13782,
    )

    assert env["DEEPTUTOR_HOME"] == str(tmp_path / "home")
    assert env["HOSTNAME"] == "127.0.0.1"
    assert env["BACKEND_PORT"] == "18001" and env["FRONTEND_PORT"] == "13782"
    assert "OPENAI_API_KEY" not in env and "ANTHROPIC_API_KEY" not in env
    assert env["DEEPTUTOR_API_BASE_URL"] == "http://127.0.0.1:18001"


def test_command_uses_external_interpreters_without_shell(tmp_path: Path):
    command = web.build_command(
        python=tmp_path / "python.exe", node=tmp_path / "node.exe",
        server=tmp_path / "server.js", runtime_home=tmp_path / "home",
    )
    assert command[:3] == [str(tmp_path / "python.exe"), "-c", web.START_SNIPPET]
    assert command[3] == str(tmp_path / "home")
