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
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

_worker_routes_spec = importlib.util.spec_from_file_location(
    "stage_worker_routes", Path(__file__).with_name("worker_routes.py")
)
assert _worker_routes_spec and _worker_routes_spec.loader
worker_routes = importlib.util.module_from_spec(_worker_routes_spec)
_worker_routes_spec.loader.exec_module(worker_routes)

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
# Loaded from services/python-workers/routes.json - the single mapping. See worker_routes.py for
# why the three hand-written copies were removed.
ROUTE_SCRIPTS: dict[str, tuple[str, ...]] = worker_routes.load(prefix="workers/")
PRIVATE_NAMES = set([".git", ".codex", ".dsh", ".zcode", ".hermes", ".openhuman", ".claude", ".agents", ".agent", ".cursor", ".continue", ".aider", ".gemini", ".opencode", ".openhands", ".cline", ".roo", ".kilocode", ".windsurf", ".copilot", ".ssh", ".aws", ".azure", ".gnupg", "agent-private", "private-agent-state", "sessions", "memories", "keychain", "credentials", "auth", "browser-data", ".npmrc", ".pypirc", ".netrc"])


def filesystem_path(path: Path) -> Path:
    """Use extended paths for Windows file I/O only, never in launch contracts."""
    absolute = os.path.abspath(path)
    return Path("\\\\?\\" + absolute) if os.name == "nt" and not absolute.startswith("\\\\") else Path(absolute)


def ordinary_path(path: Path) -> Path:
    raw = str(path)
    return Path(raw[4:] if raw.startswith("\\\\?\\") else raw)


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
    with filesystem_path(path).open("rb") as handle:
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
            info = filesystem_path(part).lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked staging path rejected")


def validate_tree(source: Path) -> None:
    reject_reparse(source)
    if filesystem_path(source).is_dir():
        for entry in filesystem_path(source).iterdir():
            validate_tree(ordinary_path(entry))


def validate_runtime_tree(source: Path) -> None:
    """Allow recorded upstream package files, while rejecting private extras/links.

    Runtime roots and stdlib still face the full path rule. Only paths listed in
    an installed distribution's RECORD (and their parent directories) bypass
    package-internal name checks, as copy_distribution already does.
    """
    reject_reparse(source)
    source = Path(os.path.abspath(source))
    packages = source / "Lib" / "site-packages"
    allowed: set[Path] = set()
    if packages.is_dir():
        reject_reparse(packages)
        reject_nested_links(packages)
        for info in packages.glob("*.dist-info"):
            reject_reparse(info)
            record = info / "RECORD"
            if not record.is_file():
                continue
            for row in csv.reader(record.read_text(encoding="utf-8").splitlines()):
                if not row or not row[0]:
                    continue
                relative = Path(row[0])
                if not relative.parts:
                    continue
                if relative.is_absolute() or relative.drive or ".." in relative.parts:
                    continue  # Scripts outside site-packages keep the full rule.
                member = packages / relative
                # A top-level private name never becomes an approved donor.
                reject_reparse(packages / relative.parts[0])
                allowed.add(member)
                allowed.update(parent for parent in member.parents if parent.is_relative_to(packages))

    def visit(path: Path) -> None:
        if path in allowed:
            reject_links_along(path)
        else:
            reject_reparse(path)
        if filesystem_path(path).is_dir():
            for entry in filesystem_path(path).iterdir():
                visit(ordinary_path(entry))

    visit(source)


def reject_nested_links(member: Path) -> None:
    """Reject links anywhere inside a distribution, without re-judging its module names.

    A distribution's own tree is upstream code. Names inside it that collide with the
    protected set - fastapi ships a directory called `.agents`, litellm ships `auth`
    directories - are modules of that package, not agent state or credentials. The
    protected-name rule still applies to the entry itself and to every path above it,
    which is where private state would actually sit; inside a distribution only the
    link rule is meaningful, because a link is what could leave the staged tree.
    """
    for dirpath, dirnames, filenames in os.walk(filesystem_path(member)):
        for entry in (*dirnames, *filenames):
            full = Path(dirpath) / entry
            try:
                info = full.lstat()
            except OSError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("linked staging path rejected")


def reject_links_along(path: Path) -> None:
    """Reject a link on any component of an absolute path, without judging its names.

    This is the link half of the path rule, which stays meaningful for upstream files;
    the name half is only meaningful at a root location. Judging a package's internals by
    name re-rejects modules that legitimately share a protected name.
    """
    resolved = Path(os.path.abspath(path))
    for part in (*reversed(resolved.parents), resolved):
        try:
            info = filesystem_path(part).lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked staging path rejected")


def copy_distribution_tree(source: Path, target: Path) -> None:
    """Copy one distribution directory, checking links but not its module names.

    Its entry has already faced the full rule, so re-judging every nested name here
    would only re-reject upstream modules that happen to share a protected name.
    """
    reject_nested_links(source)
    shutil.copytree(filesystem_path(source), filesystem_path(target), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


def copy_tree(source: Path, target: Path) -> None:
    validate_tree(source)
    validate_tree(target)
    shutil.copytree(filesystem_path(source), filesystem_path(target), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


def canonical_distribution_name(name: str) -> str:
    """The normalisation the packaging tooling itself uses for comparison.

    Runs of dashes, underscores and dots are equivalent, and case is ignored. Without
    this, a distribution declared as `typing-extensions` and installed as
    `typing_extensions` would not be recognised as the same thing.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def distribution_files(name: str, site_packages: Path) -> list[Path] | None:
    """The files a distribution actually installed, from its own RECORD.

    A distribution's name is not the name of the module or directory it installs, and
    guessing from the name - as matching a directory called after it does - both misses
    single-module distributions and drags in entries that only look similar. The RECORD
    the installer wrote is the authoritative statement of what belongs to it, so the
    declared name is resolved through the distribution metadata instead.

    Returns None when no matching distribution is installed, and None when it is
    installed but recorded no RECORD, so the caller can fall back deliberately.
    """
    wanted = canonical_distribution_name(name)
    for dist_info in sorted(site_packages.glob("*.dist-info")):
        metadata = dist_info / "METADATA"
        if not metadata.is_file():
            continue
        declared = None
        for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Name:"):
                declared = line.split(":", 1)[1].strip()
                break
        if declared is None or canonical_distribution_name(declared) != wanted:
            continue
        record = dist_info / "RECORD"
        if not record.is_file():
            return None
        installed = []
        for line in record.read_text(encoding="utf-8", errors="replace").splitlines():
            relative = line.split(",", 1)[0].strip()
            if relative:
                installed.append(site_packages / relative.replace("/", os.sep))
        return installed
    return None


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
    # The RECORD is authoritative, so prefer it over matching names. A distribution's name
    # is not the name it imports as - pymupdf installs `fitz`, and copying only entries
    # named after the distribution leaves that behind, which surfaces later as a
    # ModuleNotFoundError from the worker rather than here.
    recorded = distribution_files(name, site_packages)
    if recorded is not None:
        resolved_root = site_packages.resolve()
        chosen: list[tuple[Path, Path]] = []
        for path in recorded:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            # A recorded path may sit outside the package root, and a `..` in one must
            # not be followed out of the tree. Only files inside it are staged; console
            # scripts are not importable modules and do not belong in a package directory.
            if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
                continue
            chosen.append((resolved, resolved.relative_to(resolved_root)))
        if not chosen:
            raise ValueError(f"dependency {name} records no files inside {site_packages}")
        target_site_packages.mkdir(parents=True, exist_ok=True)
        reject_reparse(target_site_packages)
        staged_files: list[str] = []
        for source, relative in chosen:
            reject_links_along(source)
            destination = target_site_packages / relative
            reject_links_along(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            staged_files.append(relative.as_posix())
        return {"name": name, "members": sorted(staged_files)}
    members = [entry for entry in sorted(site_packages.iterdir()) if key(entry.name) == wanted]
    if not members:
        raise ValueError(f"dependency not present in {site_packages}: {name}")
    for member in members:
        # The entry itself still faces the full rule, so a distribution named after a
        # protected path is refused. Inside it, only links are rejected: its own module
        # names are upstream code and are not re-judged.
        reject_reparse(member)
        reject_nested_links(member)
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
            copy_distribution_tree(member, destination)
        else:
            shutil.copy2(member, destination)
        copied.append(member.name)
    # The RECORD the installer wrote is the authoritative statement of what belongs to a
    # distribution, and matching by name is only a guess at it. Cross-check the two, so a
    # distribution that installs a module outside the directory named after it is reported
    # here rather than surfacing later as a ModuleNotFoundError from the worker.
    recorded = distribution_files(name, site_packages)
    if recorded is not None:
        # A RECORD may name files outside the package root - fastapi records a console
        # script under the environment's Scripts directory. Those are not importable
        # modules, must not be staged into a package directory, and resolving them is how
        # a `..` in a recorded path would otherwise be followed out of the tree.
        resolved_root = site_packages.resolve()
        expected: set[str] = set()
        for path in recorded:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if not resolved.is_relative_to(resolved_root):
                continue
            expected.add(resolved.relative_to(resolved_root).as_posix())
        staged: set[str] = set()
        for member in members:
            if member.is_dir():
                for entry in member.rglob("*"):
                    if entry.is_file() and "__pycache__" not in entry.parts:
                        staged.add(entry.relative_to(site_packages).as_posix())
            else:
                staged.add(member.relative_to(site_packages).as_posix())
        missing = sorted(
            [
                recorded_name
                for recorded_name in expected
                if recorded_name not in staged
                and not recorded_name.endswith((".pyc", ".pyo"))
            ]
        )
        if missing:
            raise ValueError(
                f"dependency {name} records files that were not staged: {missing[:5]}"
            )
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


def stage_capability_manifest(root: Path, external_root: Path | None) -> dict:
    """Carry declared tools with the workers resource; pin only declared OCR paths.

    No directory search or external bytes are copied. A local candidate may record
    its explicitly selected shared root; portable CI candidates keep declarations.
    """
    source = Path(__file__).resolve().parents[2] / "config/environment/capability-requirements.yaml"
    reject_reparse(source)
    text = source.read_text(encoding="utf-8")
    measured = {}
    if external_root is not None:
        external_root = Path(os.path.abspath(external_root))
        reject_reparse(external_root)
        if not external_root.is_dir():
            raise ValueError("declared external tool root does not exist")
        for name, relative in {
            "tesseract": "10-toolchains/scoop/apps/tesseract/current/tesseract.exe",
            "tesseract-languages": "10-toolchains/scoop/apps/tesseract-languages/current",
        }.items():
            declared = external_root / relative
            if not declared.exists():
                measured[name] = {"status": "MISSING", "declared_path": relative}
                continue
            resolved = declared.resolve()
            try:
                pinned = resolved.relative_to(external_root).as_posix()
            except ValueError as error:
                raise ValueError("declared OCR path resolves outside selected external root") from error
            text = text.replace('"' + relative + '"', '"' + pinned + '"')
            entry = {"status": "PATH_RESOLVED_NOT_RUNTIME_VERIFIED", "path": str(resolved),
                     "relative_path": pinned}
            witness = resolved if resolved.is_file() else resolved / "eng.traineddata"
            if witness.is_file():
                entry["witness_sha256"] = sha256(witness)
            measured[name] = entry
        text += "\nartifact_external_root: " + json.dumps(str(external_root)) + "\n"
    target = root / "workers/capability-requirements.yaml"
    target.write_text(text, encoding="utf-8", newline="\n")
    return {"source_sha256": sha256(source), "artifact_path": "workers/capability-requirements.yaml",
            "artifact_sha256": sha256(target), "external_root": str(external_root) if external_root else None,
            "ocr_paths": measured}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path,
                        help="portable interpreter directory containing python.exe")
    parser.add_argument("--workers", required=True, type=Path)
    parser.add_argument("--external-root", type=Path,
                        help="explicit existing local shared tool root; referenced, never bundled")
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
    #
    # The dependency source is deliberately NOT scanned recursively. It is a shared
    # site-packages holding every installed distribution, most of them irrelevant to
    # this slice, and judging each of their internal module names reads upstream code
    # as if it were private state - litellm ships `auth` directories, fastapi ships
    # `.agents`, and neither holds a credential. Only the distributions actually being
    # copied are inspected, each at copy time, where its own tree is known to be the
    # thing being staged. The source root itself still faces the full rule above.
    validate_runtime_tree(args.runtime)
    validate_tree(args.workers)
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
    shutil.copytree(filesystem_path(args.runtime), filesystem_path(root / "runtime"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    copy_tree(args.workers, root / "workers")
    capability_manifest = stage_capability_manifest(root, args.external_root)
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
    for path in sorted(ordinary_path(p) for p in filesystem_path(root).rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        files[relative] = {"bytes": filesystem_path(path).stat().st_size, "sha256": sha256(path)}

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
        "capability_manifest": capability_manifest,
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
            for path in sorted(p for p in filesystem_path(root).rglob("*") if p.is_file()):
                archive.write(path, (root.name / ordinary_path(path).relative_to(root)).as_posix())

    print(json.dumps({
        "root": str(root), "manifest": str(manifest_path), "launcher": str(launcher),
        "archive": str(archive_path) if archive_path else None,
        "files": len(files),
        "manifest_sha256": sha256(manifest_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
