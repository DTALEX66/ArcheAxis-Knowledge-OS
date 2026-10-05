"""Prepare the Python runtime embedded in the Windows desktop bundle."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from desktop.scripts.stage_runtime import stage_runtime


def prepare_backend_candidate(*, repository: Path, destination: Path, core: Path) -> Path:
    """Prepare locked Python, then delegate the complete layout to the authority."""
    repository = repository.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise RuntimeError(f"candidate destination already exists: {destination}")
    donor = destination.with_name(destination.name + "-python-input")
    staged_python = prepare_bundle_runtime(repository=repository, destination=donor)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repository, text=True).strip()
    version = json.loads((repository / "frontend/package.json").read_text(encoding="utf-8"))["version"]
    subprocess.run([
        sys.executable, "-B", str(repository / "scripts/release/stage_backend_runtime.py"),
        "--core", str(core.resolve()), "--runtime", str(staged_python.parent),
        "--workers", str(repository / "services/python-workers"),
        "--shared", str(repository / "shared/learning_scheduler.py"),
        "--out", str(destination), "--version", version,
        "--source-commit", commit, "--source-tree", tree,
    ], cwd=repository, check=True)
    clear_cached_bundle_resources(repository=repository)
    return destination / "runtime/python.exe"


def clear_cached_bundle_resources(*, repository: Path) -> None:
    """Remove only cached Tauri resources, never binaries, deps or user data."""
    target_text = os.environ.get("CARGO_TARGET_DIR")
    if not target_text:
        return
    target = Path(target_text).resolve()
    common = Path(subprocess.check_output(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=repository, text=True,
    ).strip()).parent
    if not any(target.is_relative_to(root / ".project-local") for root in (repository, common)):
        raise RuntimeError(f"refusing resource cleanup outside project-local target: {target}")
    spec = importlib.util.spec_from_file_location("bundle_stager", repository / "scripts/release/stage_backend_runtime.py")
    assert spec and spec.loader
    stager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stager)
    for name in ("runtime", "core", "workers", "shared", *CANDIDATE_ROOT_FILES):
        path = target / "release" / name
        stager.reject_links_along(path)
        if path.is_dir():
            stager.reject_nested_links(path)
            print(f"remove cached resource: {path}")
            shutil.rmtree(stager.filesystem_path(path))
        elif path.is_file():
            print(f"remove cached resource: {path}")
            stager.filesystem_path(path).unlink()


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
            "--quiet",
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
        [uv, "build", "--quiet", "--python", str(staged_python), "--wheel", "--out-dir", str(wheels)],
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


CANDIDATE_ROOT_FILES = (
    "worker-profile.json",
    "start-backend.py",
    "start-backend.cmd",
    "backend-runtime-manifest.json",
)


def install_core(
    *,
    destination: Path,
    core: Path,
    workers: Path | None = None,
    candidate_root: Path | None = None,
) -> Path:
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
    if candidate_root is not None:
        # These sit at the candidate root, not inside a directory, so a resource map that
        # names directories cannot carry them. The Core reads its scheduler interpreter from
        # the worker profile, so a bundle without it starts a Core that cannot resolve its
        # worker and does not stay up.
        for name in CANDIDATE_ROOT_FILES:
            source = candidate_root / name
            if not source.is_file():
                raise RuntimeError(f"candidate root is missing {name}: {source}")
            shutil.copy2(source, destination / name)
    return staged / core.name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Not required by the parser: the Core-only path never touches the repository, and the
    # runtime path needs it. Requiring it here would force a repository just to copy one file.
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--core", type=Path,
                        help="built canonical Core to place beside the runtime")
    parser.add_argument("--backend-candidate", action="store_true",
                        help="delegate the complete runtime to the authoritative backend stager")
    parser.add_argument("--core-only", action="store_true",
                        help="place the Core and workers only; do not reinstall the runtime")
    parser.add_argument("--workers", type=Path,
                        help="workers tree to place beside the runtime")
    parser.add_argument("--candidate-root", type=Path,
                        help="candidate root holding the worker profile and launcher files")
    args = parser.parse_args()
    if args.workers is not None and args.core is None:
        parser.error("--workers requires --core")
    if args.core_only and args.core is None:
        parser.error("--core-only requires --core")
    if not args.core_only and args.repository is None:
        parser.error("--repository is required unless --core-only is given")
    destination = args.destination.resolve()
    if args.backend_candidate:
        if args.core is None or args.repository is None or args.core_only:
            parser.error("--backend-candidate requires --repository and --core, without --core-only")
        print(prepare_backend_candidate(repository=args.repository, destination=destination, core=args.core))
        return 0
    # Placing the Core beside an already-prepared runtime must not reinstall the runtime:
    # the install resolves and builds the whole locked dependency set, and a packaging step
    # that only needs to copy one executable should not pay for that or risk changing it.
    if args.core_only:
        print(install_core(
            destination=destination,
            core=args.core,
            workers=args.workers,
            candidate_root=args.candidate_root,
        ))
        return 0
    staged_python = prepare_bundle_runtime(repository=args.repository, destination=destination)
    if args.core is not None:
        install_core(destination=destination, core=args.core, workers=args.workers)
    print(staged_python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
