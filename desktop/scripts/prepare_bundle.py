"""Prepare the Python runtime embedded in the Windows desktop bundle."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from desktop.scripts.stage_runtime import stage_runtime
from scripts.runtime import dev as runtime_paths
from scripts.runtime.build_timing import BuildTimings


def _load_tool_paths(repository: Path):
    """The shared capability resolver, loaded by path (it is a worker-side module)."""
    path = repository / "services" / "python-workers" / "tool_paths.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("bundle_tool_paths", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def declared_asr_model(repository: Path) -> Path | None:
    """The transcript model the capability declaration names on this host, or None.

    Packaging copies an explicit donor. Resolving the declared one here is what makes the
    canonical build ship a model without a second hardcoded path in the build script; a host
    without it prints a named reason instead of producing a candidate that looks complete.
    """
    module = _load_tool_paths(repository)
    if module is None:
        print("asr model: tool_paths.py is missing; this candidate ships no transcript model",
              file=sys.stderr)
        return None
    try:
        resolved = module.tool_path("faster-whisper-base")
    except Exception as exc:  # noqa: BLE001 - a build reports what it could not resolve
        print(f"asr model: the declared donor did not resolve ({type(exc).__name__}: {exc}); "
              "this candidate ships no transcript model", file=sys.stderr)
        return None
    return Path(resolved)


def asr_model_name(donor: Path) -> str:
    """The directory name the model is bundled under, from an HF cache layout when it has one.

    A Hugging Face snapshot directory is named by commit sha; the model's own name is in the
    cache entry above it. Using the sha as the bundled name would make the identity unreadable
    and defeat the worker's preference order.
    """
    for part in reversed(donor.parts):
        if part.startswith("models--"):
            pieces = [piece for piece in part[len("models--"):].split("--") if piece]
            if pieces:
                return pieces[-1]
    return donor.name


def prepare_backend_candidate(*, repository: Path, destination: Path, core: Path,
                              asr_model: Path | None = None, vc_runtime: Path | None = None) -> Path:
    """Prepare locked Python, then delegate the complete layout to the authority."""
    repository = repository.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise RuntimeError(f"candidate destination already exists: {destination}")
    vc_runtime = resolve_vc_runtime(vc_runtime)
    donor = destination.with_name(destination.name + "-python-input")
    staged_python = prepare_bundle_runtime(repository=repository, destination=donor)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repository, text=True).strip()
    version = json.loads((repository / "frontend/package.json").read_text(encoding="utf-8"))["version"]
    command = [
        sys.executable, "-B", str(repository / "scripts/release/stage_backend_runtime.py"),
        "--core", str(core.resolve()), "--runtime", str(staged_python.parent),
        "--workers", str(repository / "services/python-workers"),
        "--shared", str(repository / "shared/learning_scheduler.py"),
        "--out", str(destination), "--version", version,
        "--source-commit", commit, "--source-tree", tree,
        "--vc-runtime", str(vc_runtime),
    ]
    if asr_model is not None:
        command += ["--asr-model", str(Path(asr_model).resolve()),
                    "--asr-model-name", asr_model_name(Path(asr_model))]
    subprocess.run(command, cwd=repository, check=True)
    clear_cached_bundle_resources(repository=repository)
    return destination / "runtime/python.exe"


def resolve_vc_runtime(explicit: Path | None = None) -> Path:
    """Builder-only official VS discovery; the stager never searches for donors."""
    spec = importlib.util.spec_from_file_location("desktop_vc_authority",
        Path(__file__).resolve().parents[2] / "scripts/release/stage_backend_runtime.py")
    authority = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(authority)
    def validated(path):
        path = Path(os.path.abspath(path))
        authority.validate_cpp_runtime(path)
        return path
    selected = explicit or os.environ.get("ARCHEAXIS_VC_RUNTIME_DIR")
    if selected:
        return validated(selected)
    program_files = os.environ.get("ProgramFiles(x86)")
    if not program_files:
        raise RuntimeError("VC runtime donor unavailable; pass --vc-runtime or ARCHEAXIS_VC_RUNTIME_DIR")
    vswhere = Path(program_files) / "Microsoft Visual Studio/Installer/vswhere.exe"
    authority.reject_links_along(vswhere)
    if not vswhere.is_file():
        raise RuntimeError("official vswhere missing; pass an explicit VC runtime donor")
    result = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                             "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                            check=True, capture_output=True, text=True, encoding="utf-8-sig", timeout=30)
    installations = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(installations) != 1 or not Path(installations[0]).is_absolute():
        raise RuntimeError("official vswhere did not return one absolute installationPath")
    vc = Path(installations[0]) / "VC"
    version_file = vc / "Auxiliary/Build/Microsoft.VCRedistVersion.default.txt"
    authority.reject_links_along(version_file)
    if version_file.stat().st_nlink != 1:
        raise RuntimeError("linked official VC Redist version file")
    version = version_file.read_text(encoding="utf-8-sig").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise RuntimeError("invalid official VC Redist default version")
    return validated(vc / "Redist/MSVC" / version / "x64/Microsoft.VC143.CRT")


def clear_cached_bundle_resources(*, repository: Path) -> None:
    """Remove only cached Tauri resources, never binaries, deps or user data."""
    target_text = os.environ.get("CARGO_TARGET_DIR")
    if not target_text:
        return
    target_text = os.environ.get("ARCHEAXIS_CARGO_TAURI_TARGET_DIR", target_text)
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


def _run(command: list[str], *, cwd: Path, env: dict[str, str], stage: str, timings: BuildTimings) -> None:
    with timings.stage(stage):
        subprocess.run(command, cwd=cwd, env=env, check=True)


def runtime_build_environment(repository: Path) -> dict[str, str]:
    """Share the owner's uv cache and isolate wheel-build discovery in this run."""
    repository = runtime_paths.safe_path(repository)
    inherited_root = os.environ.get("ARCHEAXIS_WORKTREE_ROOT")
    if inherited_root and runtime_paths.safe_path(Path(inherited_root)) != repository:
        raise RuntimeError("runtime preparation inherited a foreign worktree")
    inherited_run = os.environ.get("ARCHEAXIS_RUN_ROOT")
    paths = runtime_paths.layout(repository, Path(inherited_run).name if inherited_run else None)
    if inherited_run and runtime_paths.safe_path(Path(inherited_run)) != paths["run"]:
        raise RuntimeError("runtime preparation inherited a foreign run")
    env = os.environ.copy()
    if inherited_run:
        if not paths["run"].is_dir() or not paths["tmp"].is_dir():
            raise RuntimeError("runtime preparation inherited an unallocated run")
        env.update(runtime_paths.environment(paths))
    else:
        env.update(runtime_paths.prepare(paths))
    # This is a build environment, not the developer-owned root .venv, and not
    # another per-checkout dependency cache. Concurrent runs share uv's locked
    # cache while keeping their wheel build discovery separate.
    env["UV_PROJECT_ENVIRONMENT"] = str(paths["tmp"] / "runtime-build-venv")
    return env


def prepare_bundle_runtime(*, repository: Path, destination: Path) -> Path:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(
            "请使用 Python 3.12 制备桌面运行时；当前执行解释器为 "
            f"Python {sys.version_info[0]}.{sys.version_info[1]}。"
        )
    repository = repository.resolve()
    destination = destination.resolve()
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to prepare the desktop runtime")

    env = runtime_build_environment(repository)
    timings = BuildTimings(Path(env["ARCHEAXIS_RUN_ROOT"]) / "artifacts", env)
    with timings.stage("python-copy") as copy:
        staged_python = stage_runtime(repository=repository, destination=destination)
        copy["bytes"] = sum(path.stat().st_size for path in staged_python.parent.rglob("*") if path.is_file())
    requirements = destination / "requirements.locked.txt"
    wheels = destination / "wheels"
    # The pinned setuptools backend builds in place even when uv's wheel output
    # and isolated environment are routed elsewhere. Its command options must
    # also route egg_info and build intermediates; otherwise root drift returns.
    wheel_build = runtime_paths.safe_path(Path(env["UV_PROJECT_ENVIRONMENT"]).parent / "setuptools")
    egg_base = wheel_build / "egg-info"
    build_base = wheel_build / "build"
    egg_base.mkdir(parents=True, exist_ok=True)
    build_base.mkdir(parents=True, exist_ok=True)
    settings = ["--config-setting=--global-option=" + option for option in (
        "egg_info", "--egg-base=" + str(egg_base),
        "build", "--build-base=" + str(build_base),
    )]

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
        stage="dependency-export", timings=timings,
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
        stage="dependency-install", timings=timings,
    )
    _run(
        [uv, "build", "--quiet", "--python", str(staged_python), "--wheel", "--out-dir", str(wheels), *settings],
        cwd=repository,
        env=env,
        stage="wheel-build", timings=timings,
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
        stage="wheel-install", timings=timings,
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
        stage="runtime-import-check", timings=timings,
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
    parser.add_argument("--asr-model", type=Path,
                        help="explicit transcript model directory to bundle inside runtime/models/asr; "
                             "defaults to the model the capability declaration names")
    parser.add_argument("--vc-runtime", type=Path,
                        help="explicit reviewed x64 VC donor; defaults to build-local environment or official VS registration")
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
        print(prepare_backend_candidate(
            repository=args.repository, destination=destination, core=args.core,
            vc_runtime=args.vc_runtime,
            asr_model=args.asr_model or declared_asr_model(args.repository.resolve())))
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
