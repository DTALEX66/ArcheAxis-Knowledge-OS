"""Exercise the tracked Windows runner without invoking an installed toolchain."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows batch runner")
RUNNER = Path(__file__).resolve().parents[1] / "scripts/ci/cargo_test.bat"


def run_fake(tmp_path: Path, *, inherited: str = "", override: str = "", args=()):
    toolchain = tmp_path / "fake toolchain"
    binary = toolchain / "cargo/bin"
    binary.mkdir(parents=True)
    (binary / "cargo.bat").write_text(
        "@echo off\n"
        "echo FAKE_TARGET=%CARGO_TARGET_DIR%\n"
        "echo FAKE_ARGS=%*\n"
        "exit /b 7\n",
        encoding="ascii",
    )
    env = os.environ.copy()
    for name in (
        "ARCHEAXIS_MSVC_VCVARS",
        "ARCHEAXIS_CARGO_TARGET_DIR",
        "CARGO_TARGET_DIR",
    ):
        env.pop(name, None)
    env.update(ARCHEAXIS_RUST_TOOLCHAINS=str(toolchain), PATH="")
    if inherited:
        env["CARGO_TARGET_DIR"] = inherited
    if override:
        env["ARCHEAXIS_CARGO_TARGET_DIR"] = override
    command = Path(env["SYSTEMROOT"]) / "System32/cmd.exe"
    # cmd /s /c needs an outer quoted command when both the batch path and
    # an argument contain spaces. Popen's argv-to-string quoting alone drops
    # the batch path's opening quote in that case (attempting to run D:\\All).
    batch_command = subprocess.list2cmdline([str(RUNNER), *args])
    return subprocess.run(
        f'"{command}" /d /s /c "{batch_command}"',
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=15,
        check=False,
    )


@pytest.mark.parametrize("override", [False, True])
def test_runner_preserves_canonical_target_unless_explicitly_overridden(tmp_path, override):
    inherited = str(tmp_path / "common build/worktree identity")
    explicit = str(tmp_path / "explicit target") if override else ""
    result = run_fake(
        tmp_path, inherited=inherited, override=explicit,
        args=("-p", "archeaxis-domain", "--offline"),
    )
    assert result.returncode == 7, (result.stdout, result.stderr)
    assert f"FAKE_TARGET={explicit or inherited}" in result.stdout
    assert "FAKE_ARGS=test -p archeaxis-domain --offline" in result.stdout


def test_runner_forwards_subcommand_and_quoted_argument(tmp_path):
    result = run_fake(
        tmp_path, args=("check", "--manifest-path", "path with spaces/Cargo.toml"),
    )
    assert result.returncode == 7, (result.stdout, result.stderr)
    assert 'FAKE_ARGS=check --manifest-path "path with spaces/Cargo.toml"' in result.stdout


def test_runner_default_arguments_and_documented_local_fallback(tmp_path):
    result = run_fake(tmp_path)
    assert result.returncode == 7, (result.stdout, result.stderr)
    assert "FAKE_ARGS=test --workspace --offline" in result.stdout
    assert f"FAKE_TARGET={RUNNER.parents[2] / '.project-local/build/cargo'}" in result.stdout
