"""Prepare the Python runtime embedded in the Windows desktop bundle."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from desktop.scripts.stage_runtime import stage_runtime


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def prepare_bundle_runtime(*, repository: Path, destination: Path) -> Path:
    repository = repository.resolve()
    destination = destination.resolve()
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to prepare the desktop runtime")

    staged_python = stage_runtime(repository=repository, destination=destination)
    requirements = destination / "requirements.locked.txt"
    wheels = destination / "wheels"
    cache = repository / ".hermes/cache/uv-desktop"
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(cache)

    _run(
        [
            uv,
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-editable",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements),
        ],
        cwd=repository,
        env=env,
    )
    _run(
        [
            uv,
            "pip",
            "install",
            "--break-system-packages",
            "--python",
            str(staged_python),
            "--require-hashes",
            "--requirement",
            str(requirements),
        ],
        cwd=repository,
        env=env,
    )
    _run(
        [uv, "build", "--wheel", "--out-dir", str(wheels)],
        cwd=repository,
        env=env,
    )
    built_wheels = tuple(wheels.glob("archeaxis_workspace-*.whl"))
    if len(built_wheels) != 1:
        raise RuntimeError(f"expected exactly one Cognitive-OS wheel, found {len(built_wheels)}")
    _run(
        [
            uv,
            "pip",
            "install",
            "--break-system-packages",
            "--python",
            str(staged_python),
            "--no-deps",
            str(built_wheels[0]),
        ],
        cwd=repository,
        env=env,
    )
    _run(
        [
            str(staged_python),
            "-I",
            "-c",
            "import app.runtime_entrypoint, fastapi, uvicorn; print('installed runtime imports passed')",
        ],
        cwd=destination,
        env=env,
    )
    return staged_python


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(prepare_bundle_runtime(repository=args.repository, destination=args.destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
