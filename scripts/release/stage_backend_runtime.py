"""Stage a complete backend runtime root from committed source.

The repository already defines how the backend is distributed, and it is not one
Python wheel. `scripts/release/assemble_green_candidate.py` and
`scripts/release/verify_green_candidate.py` fix the runtime layout as sibling
components:

    core/archeaxis-api.exe     the canonical writer
    runtime/python.exe         the interpreter the workers run under
    workers/**                 services/python-workers content
    worker-profile.json        archeaxis.worker-profile/v1 (python, script, staging)
    data/                      workspace, objects and staging

That assembler requires a built desktop, because a *product* candidate needs the
Avalonia shell. The backend half does not, and waiting for the shell is what left
"the wheel installs" standing in for "the backend runs from what was installed".
This script stages only the backend components, using the same layout, the same
profile schema and the same environment names the desktop supervisor already reads,
so it adds no second architecture.

It never downloads anything: the interpreter and every dependency come from
locations that are already registered and approved on this host, and each one is
recorded by version and content hash in the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROFILE_SCHEMA = "archeaxis.worker-profile/v1"
MANIFEST_SCHEMA = "archeaxis.backend-runtime/v1"
TEXT_WORKER_RELATIVE = "workers/transport/text_ndjson.py"
SCHEDULER_WORKER_RELATIVE = "workers/learning/worker_schedule.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def packager_identity() -> str:
    """The commit of the tooling that decided this layout, dirty state included.

    An uncommitted stager means the artifact was assembled by logic no commit
    describes, which is the condition this field exists to expose.
    """
    directory = Path(__file__).resolve().parent
    try:
        commit = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(directory), "status", "--porcelain",
                                "--", str(Path(__file__).resolve())],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
    return f"{commit}+dirty" if dirty else commit


def reject_reparse(path: Path) -> None:
    """A staged runtime must not follow a link out of its own tree."""
    for part in (path, *path.parents):
        if not part.exists():
            continue
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError(f"linked path rejected: {part}")


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


def copy_distribution(name: str, site_packages: Path, target_site_packages: Path) -> dict:
    """Copy one installed distribution byte for byte.

    A distribution is not always a package directory: `typing_extensions` installs a
    single `typing_extensions.py` module, and matching only on directory names copied
    its dist-info while silently leaving the module behind - which surfaced later as
    `ModuleNotFoundError` from the worker instead of here.
    """
    wanted = name.replace("-", "_").replace("_", "").lower()

    def key(entry_name: str) -> str:
        stem = entry_name.split("-")[0]
        if stem.endswith((".py", ".pyi")):
            stem = stem.rsplit(".", 1)[0]
        return stem.replace("_", "").lower()

    members = [entry for entry in sorted(site_packages.iterdir()) if key(entry.name) == wanted]
    if not members:
        raise ValueError(f"dependency not present in {site_packages}: {name}")
    has_module = any(entry.is_file() or (entry.is_dir() and not entry.name.endswith(".dist-info"))
                     for entry in members)
    if not has_module:
        raise ValueError(f"dependency {name} has metadata but no importable member in "
                         f"{site_packages}")
    target_site_packages.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for member in members:
        destination = target_site_packages / member.name
        if member.is_dir():
            copy_tree(member, destination)
        else:
            shutil.copy2(member, destination)
        copied.append(member.name)
    return {"name": name, "members": sorted(copied)}


def write_launcher(root: Path) -> Path:
    """The formal entry point: it resolves everything from the runtime root.

    It does not export ARCHEAXIS_PYTHON; the Core reads the interpreter out of
    worker-profile.json. A developer shell's stale variables are removed by
    start-backend.py so a broken runtime cannot be masked by the environment.
    """
    launcher = root / "start-backend.cmd"
    launcher.write_text(
        "@echo off\r\n"
        "rem Formal backend launcher for a staged runtime. Everything it needs is\r\n"
        "rem resolved from this directory; no checkout, virtualenv or manual\r\n"
        "rem interpreter configuration is involved.\r\n"
        "setlocal\r\n"
        '"%~dp0runtime\\python.exe" "%~dp0start-backend.py" %*\r\n'
        "exit /b %ERRORLEVEL%\r\n",
        encoding="utf-8", newline="\r\n")
    return launcher


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path,
                        help="portable interpreter directory containing python.exe")
    parser.add_argument("--workers", required=True, type=Path)
    parser.add_argument("--shared", type=Path,
                        help="scheduler donor; defaults to <workers>/../shared/learning_scheduler.py")
    parser.add_argument("--dep-source", type=Path,
                        help="site-packages the approved dependencies are copied from")
    parser.add_argument("--dep", action="append", default=[],
                        help="distribution name to stage into the runtime (repeatable)")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--runtime-commit",
                        help="commit the Core/workers were built from; defaults to --source-commit")
    parser.add_argument("--runtime-tree")
    parser.add_argument("--packager-commit",
                        help="commit of the staging tooling that decided this layout; "
                             "defaults to the current commit of this script's checkout")
    parser.add_argument("--archive", type=Path, help="also write a zip beside the root")
    args = parser.parse_args()

    packager_commit = args.packager_commit or packager_identity()
    if not packager_commit:
        raise ValueError("packager commit is unknown; pass --packager-commit so the "
                         "artifact records which staging logic produced it")

    root = args.out.resolve()
    if root.exists():
        raise ValueError(f"refusing to overwrite an existing runtime root: {root}")
    for candidate in (args.core, args.runtime, args.workers):
        reject_reparse(candidate.resolve())
    if not (args.runtime / "python.exe").is_file():
        raise ValueError(f"runtime has no python.exe: {args.runtime}")
    if not (args.workers / "transport" / "text_ndjson.py").is_file():
        raise ValueError(f"workers has no transport/text_ndjson.py: {args.workers}")

    (root / "core").mkdir(parents=True)
    shutil.copy2(args.core, root / "core" / "archeaxis-api.exe")
    copy_tree(args.runtime, root / "runtime")
    copy_tree(args.workers, root / "workers")
    (root / "data").mkdir()

    # The scheduler worker imports the repository's shared donor rather than carrying a
    # copy, and assemble_green_candidate stages exactly this one file at this exact
    # relative path; the worker resolves it as <root>/shared/learning_scheduler.py.
    # Without it the worker starts and then reports FileNotFoundError, which reads like
    # a broken worker instead of a missing component.
    shared_donor = args.shared or args.workers.resolve().parents[1] / "shared" / "learning_scheduler.py"
    if not shared_donor.is_file():
        raise ValueError(f"scheduler donor is missing: {shared_donor}")
    (root / "shared").mkdir()
    shutil.copy2(shared_donor, root / "shared" / "learning_scheduler.py")

    site_packages = root / "runtime" / "Lib" / "site-packages"
    dependencies = []
    if args.dep:
        if args.dep_source is None:
            raise ValueError("--dep requires --dep-source")
        for name in args.dep:
            dependencies.append(copy_distribution(name, args.dep_source.resolve(), site_packages))

    profile = {
        "schema": PROFILE_SCHEMA,
        "python": "runtime/python.exe",
        "script": TEXT_WORKER_RELATIVE,
        "staging": "data/worker-staging",
    }
    profile_path = root / "worker-profile.json"
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8", newline="\n")
    launcher = write_launcher(root)
    # The formal launcher is part of the artifact, so a candidate cannot be rebuilt
    # with different startup logic and still look identical.
    shutil.copy2(Path(__file__).resolve().parent / "backend_launcher.py",
                 root / "start-backend.py")

    def interpreter_version() -> str:
        result = os.popen(f'"{root / "runtime" / "python.exe"}" -c '
                          f'"import sys;print(sys.version.split()[0])"').read().strip()
        return result or "unknown"

    files: dict[str, dict[str, object]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        files[relative] = {"bytes": path.stat().st_size, "sha256": sha256(path)}

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "version": args.version,
        # Two identities, kept apart on purpose. The staging tool decides which
        # components exist, where they sit and which dependencies are copied, so
        # treating a change to it as "documentation" is exactly how a candidate ends
        # up assembled by logic nobody tested.
        "runtime_source": {
            "commit": args.runtime_commit or args.source_commit,
            "tree": args.runtime_tree or args.source_tree,
            "note": "commit the Core and workers were built from",
        },
        "packager_source": {
            "commit": packager_commit,
            "note": "commit of scripts/release/stage_backend_runtime.py and backend_launcher.py "
                    "that produced this layout",
        },
        "built_from": {"source_commit": args.source_commit, "source_tree": args.source_tree},
        "components": [
            {"component": "core", "path": "core/archeaxis-api.exe",
             "sha256": files["core/archeaxis-api.exe"]["sha256"],
             "install_location": "core/", "protocol": "archeaxis.desktop-launch/v2 over stdin, HTTP on 127.0.0.1",
             "version": args.version},
            {"component": "python-runtime", "path": "runtime/python.exe",
             "sha256": files["runtime/python.exe"]["sha256"], "install_location": "runtime/",
             "protocol": "subprocess", "version": interpreter_version()},
            {"component": "python-workers", "path": "workers/",
             "files": sum(1 for name in files if name.startswith("workers/")),
             "install_location": "workers/", "protocol": "archeaxis.sidecar-protocol over NDJSON",
             "version": args.version},
            {"component": "worker-profile", "path": "worker-profile.json",
             "sha256": files["worker-profile.json"]["sha256"], "install_location": ".",
             "protocol": PROFILE_SCHEMA, "version": "1"},
        ],
        "dependencies": dependencies,
        "startup_order": [
            "1. set ARCHEAXIS_WORKER_PROFILE to <root>/worker-profile.json",
            "2. launch core/archeaxis-api.exe with the workspace db and port",
            "3. write the archeaxis.desktop-launch/v2 launch JSON on stdin, including text_worker",
            "4. the Core resolves its scheduler interpreter from worker-profile.json",
        ],
        "health_check": {
            "core_readiness": "stdout line 'archeaxis-api ready on http://127.0.0.1:<port>'",
            "first_exchange": "GET /api/v1/system/version",
            "scheduler": "POST /api/v1/learning/reviews reports schedule_authority",
        },
        "shutdown": "close stdin and terminate the Core process; the workspace writer lock is released on exit",
        "data_root": "data/ (created empty; the workspace database and objects live here)",
        "rollback_scope": "delete this runtime root; it is self-contained and writes only under data/",
        "manual_environment_required": False,
        "files": files,
    }
    manifest_path = root / "backend-runtime-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")

    archive_path = None
    if args.archive:
        archive_path = args.archive.resolve()
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                archive.write(path, (root.name / path.relative_to(root)).as_posix())

    print(json.dumps({
        "root": str(root), "manifest": str(manifest_path), "launcher": str(launcher),
        "archive": str(archive_path) if archive_path else None,
        "files": len(files),
        "manifest_sha256": sha256(manifest_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
