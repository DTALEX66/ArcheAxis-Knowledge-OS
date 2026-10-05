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
    cache = repository / ".project-local/cache/uv-desktop"
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(cache)
    # Keep wheel build discovery out of a developer-owned root .venv. The
    # bundle staging environment is ephemeral project runtime state.
    env["UV_PROJECT_ENVIRONMENT"] = str(cache / "build-project-venv")

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


def install_core(*, destination: Path, core: Path, workers: Path | None = None) -> Path:
    """Place a built canonical Core, and optionally its workers, beside the runtime.

    A bundle resource map can only name directories that exist when the bundle is built,
    and this script otherwise prepares the Python runtime alone. Without a Core in the
    staged tree the shell's discovery finds nothing and keeps the legacy entrypoint,
    silently - so putting one here is what actually changes which backend ships.
    """
    if not core.is_file():
        raise RuntimeError(f"core executable is missing: {core}")
    staged = destination / "core"
    staged.mkdir(parents=True, exist_ok=True)
    shutil.copy2(core, staged / core.name)
    if workers is not None:
        if not workers.is_dir():
            raise RuntimeError(f"workers directory is missing: {workers}")
        shutil.copytree(
            workers,
            destination / "workers",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    return staged / core.name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--core", type=Path,
                        help="built canonical Core to place beside the runtime")
    parser.add_argument("--workers", type=Path,
                        help="workers tree to place beside the runtime")
    args = parser.parse_args()
    if args.workers is not None and args.core is None:
        parser.error("--workers requires --core")
    destination = args.destination.resolve()
    staged_python = prepare_bundle_runtime(repository=args.repository, destination=destination)
    if args.core is not None:
        install_core(destination=destination, core=args.core, workers=args.workers)
    print(staged_python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
