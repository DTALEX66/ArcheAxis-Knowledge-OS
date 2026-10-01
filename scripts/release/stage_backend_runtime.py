"""Stage a complete backend runtime root with measured bytes and asserted provenance.

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
import stat
import subprocess
import zipfile
from pathlib import Path

PROFILE_SCHEMA = "archeaxis.worker-profile/v1"
MANIFEST_SCHEMA = "archeaxis.backend-runtime/v1"
TEXT_WORKER_RELATIVE = "workers/transport/text_ndjson.py"
SCHEDULER_WORKER_RELATIVE = "workers/learning/worker_schedule.py"

# Capability -> worker scripts that implement it, in preference order, relative to
# the staged root. Each of these workers advertises the capability itself and
# refuses anything it did not advertise, so the Core can only dispatch a route that
# a real worker serves. Only the first *existing* path is declared: the profile
# states what this runtime actually ships, and a capability with no worker present is
# left out rather than declared and then failing at job time.
ROUTE_SCRIPTS: dict[str, tuple[str, ...]] = {
    "archive.inventory": ("workers/document/worker_archive.py",),
    "canvas.structure": ("workers/document/worker_canvas.py",),
    "html.structure": ("workers/web/worker_html.py",),
    "image.caption": ("workers/vision/worker_caption.py",),
    "image.ocr": ("workers/vision/worker_ocr.py",),
    "media.probe": ("workers/document/worker_media.py",),
    "media.transcribe": ("workers/media/worker_transcribe.py",),
    "office.structure": ("workers/document/worker_office.py",),
    "pdf.extract": ("workers/document/worker_pdf.py",),
    "subtitles.structure": ("workers/document/worker_subtitles.py",),
}
PRIVATE_NAMES = set([".git", ".codex", ".dsh", ".zcode", ".hermes", ".openhuman", ".claude", ".agents", ".agent", ".cursor", ".continue", ".aider", ".gemini", ".opencode", ".openhands", ".cline", ".roo", ".kilocode", ".windsurf", ".copilot", ".ssh", ".aws", ".azure", ".gnupg", "agent-private", "private-agent-state", "sessions", "memories", "keychain", "credentials", "auth", "browser-data", ".npmrc", ".pypirc", ".netrc"])


def present_routes(root: Path) -> list[dict[str, str]]:
    """Declare the capability routes this staged tree can actually serve.

    Only a capability whose worker script is present is declared. A route that named
    an absent script would make the Core refuse the whole profile, and a route
    declared without a worker would fail at job time instead of at packaging time.
    """
    declared: list[dict[str, str]] = []
    for capability in sorted(ROUTE_SCRIPTS):
        for relative in ROUTE_SCRIPTS[capability]:
            if (root / relative).is_file():
                declared.append({"capability": capability, "script": relative})
                break
    return declared


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def packager_identity() -> str:
    """The commit of the tooling that decided this layout, dirty state included.

    An uncommitted stager or launcher means the artifact used logic no commit
    describes, which is the condition this field exists to expose.
    """
    directory = Path(__file__).resolve().parent
    inputs = [str(directory / name) for name in ("stage_backend_runtime.py", "backend_launcher.py")]
    try:
        commit = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(directory), "status", "--porcelain",
                                "--", *inputs],
                               capture_output=True, text=True, check=True).stdout.strip()
        tracked = subprocess.run(["git", "-C", str(directory), "ls-files", "--error-unmatch",
                                  "--", *inputs], capture_output=True, text=True, check=False)
    except (OSError, subprocess.CalledProcessError):
        return ""
    return f"{commit}+dirty" if dirty or tracked.returncode else commit


def reject_reparse(path: Path) -> None:
    """A staged runtime must not follow a link out of its own tree."""
    raw = str(path).replace("\\", "/").lower()
    if raw.startswith(("e:", "//")) or ".." in raw.split("/"):
        raise ValueError("unsafe staging path")
    path = Path(os.path.abspath(path))
    full = str(path).replace("\\", "/").lower()
    if full.startswith(("e:", "//")) or any(part in PRIVATE_NAMES or part.startswith(".env") for part in full.split("/")) or "/.project-local/agents/" in full:
        raise ValueError("protected staging path")
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked staging path rejected")


def validate_tree(source: Path) -> None:
    reject_reparse(source)
    if source.is_dir():
        for entry in source.iterdir():
            validate_tree(entry)


def copy_tree(source: Path, target: Path) -> None:
    validate_tree(source)
    validate_tree(target)
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

    reject_reparse(site_packages)
    members = [entry for entry in sorted(site_packages.iterdir()) if key(entry.name) == wanted]
    if not members:
        raise ValueError(f"dependency not present in {site_packages}: {name}")
    for member in members:
        validate_tree(member)
    reject_reparse(target_site_packages)
    has_module = any(entry.is_file() or (entry.is_dir() and not entry.name.endswith(".dist-info"))
                     for entry in members)
    if not has_module:
        raise ValueError(f"dependency {name} has metadata but no importable member in "
                         f"{site_packages}")
    target_site_packages.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for member in members:
        destination = target_site_packages / member.name
        reject_reparse(destination)
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
        "set PYTHONPATH=\r\n"
        "set PYTHONHOME=\r\n"
        "set PYTHONNOUSERSITE=1\r\n"
        "rem cmd.exe answers 9009 for a missing program, which names nothing. Check the\r\n"
        "rem interpreter here so a broken runtime says which component is missing.\r\n"
        'if not exist \"%~dp0runtime\\python.exe\" (\r\n'
        "  echo {\"ok\": false, \"failure\": \"runtime interpreter is missing: %~dp0runtime\\python.exe\"}\r\n"
        "  exit /b 2\r\n"
        ")\r\n"
        'if not exist \"%~dp0start-backend.py\" (\r\n'
        "  echo {\"ok\": false, \"failure\": \"launcher script is missing: %~dp0start-backend.py\"}\r\n"
        "  exit /b 2\r\n"
        ")\r\n"
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
                        help="asserted tooling commit (recorded separately from detected Git identity)")
    parser.add_argument("--archive", type=Path, help="also write a zip beside the root")
    args = parser.parse_args()

    detected_packager_commit = packager_identity()
    packager_commit = detected_packager_commit or args.packager_commit
    if not packager_commit:
        raise ValueError("packager commit is unknown; pass --packager-commit so the "
                         "artifact records which staging logic produced it")

    shared_donor = args.shared or args.workers.parent.parent / "shared" / "learning_scheduler.py"
    for candidate in (args.core, args.runtime, args.workers, shared_donor, args.out,
                      args.dep_source, args.archive):
        if candidate is not None:
            reject_reparse(candidate)
    # Preflight all recursive donors before producing even a partial output root.
    for candidate in (args.runtime, args.workers, args.dep_source):
        if candidate is not None:
            validate_tree(candidate)
    if not shared_donor.is_file():
        raise ValueError(f"scheduler donor is missing: {shared_donor}")
    if not args.core.is_file():
        raise ValueError("Core executable is missing")
    if args.dep and args.dep_source is None:
        raise ValueError("--dep requires --dep-source")
    if args.archive and args.archive.exists():
        raise ValueError("refusing to overwrite an existing archive")
    root = args.out.absolute()
    if root.exists():
        raise ValueError(f"refusing to overwrite an existing runtime root: {root}")
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
    (root / "shared").mkdir()
    shutil.copy2(shared_donor, root / "shared" / "learning_scheduler.py")

    site_packages = root / "runtime" / "Lib" / "site-packages"
    dependencies = []
    if args.dep:
        if args.dep_source is None:
            raise ValueError("--dep requires --dep-source")
        for name in args.dep:
            dependencies.append(copy_distribution(name, args.dep_source, site_packages))

    profile = {
        "schema": PROFILE_SCHEMA,
        "python": "runtime/python.exe",
        "script": TEXT_WORKER_RELATIVE,
        "staging": "data/worker-staging",
    }
    declared_routes = present_routes(root)
    if declared_routes:
        profile["routes"] = declared_routes
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
            "evidence": "ASSERTED_NOT_VERIFIED",
            "note": "caller-declared build provenance; not verified against the supplied Core or workers",
        },
        "packager_source": {
            "commit": packager_commit,
            "asserted_commit": args.packager_commit,
            "evidence": "GIT_CHECKOUT_OBSERVED" if detected_packager_commit else "ASSERTED_NOT_VERIFIED",
            "inputs_sha256": {
                "stage_backend_runtime.py": sha256(Path(__file__)),
                "backend_launcher.py": files["start-backend.py"]["sha256"],
            },
            "note": "detected tooling checkout HEAD and dirty state; byte hashes identify actual inputs",
        },
        "built_from": {"source_commit": args.source_commit, "source_tree": args.source_tree,
                       "evidence": "ASSERTED_NOT_VERIFIED"},
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
        archive_path = args.archive.absolute()
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
