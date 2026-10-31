"""One project-local development environment for shell, CI and pytest callers.

This is environment routing and evidence, not an operating-system sandbox.
Never changes HOME, provider configuration, product workspaces or toolchain homes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    ).strip()


def safe_path(path: Path) -> Path:
    """Reject links/junctions before resolving; never follow a redirected ancestor."""
    raw = os.fspath(path)
    # On POSIX runners, ``Path('F:/x')`` is treated as a relative path and
    # loses its Windows drive in ``Path.drive``.  Check the lexical form
    # before normalizing so the E:/F: boundary is enforced consistently.
    if re.match(r"^[A-Za-z]:[\\/]", raw) and raw[:1].upper() in {"E", "F"}:
        raise ValueError("protected drive or UNC development root")
    path = Path(os.path.abspath(path))
    if path.drive.upper() in {"E:", "F:"} or str(path).startswith("\\\\"):
        raise ValueError("protected drive or UNC development root")
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError(f"linked development path rejected: {part}")
    return path


def layout(root: Path, run_id: str | None = None) -> dict[str, Path]:
    root = safe_path(root)
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError("caller must name the exact Git worktree root")
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    owner = safe_path(common.parent)
    default = owner / ".project-local"
    dev = safe_path(Path(os.environ.get("ARCHEAXIS_DEV_ROOT", str(default))))
    # External-root adoption requires a separate reviewed ownership configuration.
    if dev != default:
        raise ValueError("ARCHEAXIS_DEV_ROOT must equal this project's .project-local")
    ignored = subprocess.run(
        ["git", "-C", str(owner), "check-ignore", "-q", "--", ".project-local/"],
        check=False,
    )
    if ignored.returncode:
        raise ValueError("development root must be Git-ignored before use")
    identity = hashlib.sha256(str(root).casefold().encode()).hexdigest()[:10]
    run_id = run_id or uuid.uuid4().hex[:12]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise ValueError("invalid run ID")
    run = dev / "runs" / identity / run_id
    paths = {"root": root, "dev": dev, "run": run,
             "tmp": run / "tmp", "logs": run / "logs",
             "artifacts": run / "artifacts", "cache": dev / "cache",
             "build": dev / "build" / identity}
    paths["frontend_dist"] = paths["artifacts"] / "frontend-dist"
    paths["tauri_config"] = paths["tmp"] / "tauri-build.json"
    # Main checkout shares the checked-in bare Cargo target; linked worktrees
    # retain independent outputs. Historical caches require an explicit reviewed
    # cleanup manifest; preservation does not exempt them from storage budgets.
    paths["cargo_build"] = (dev / "build" / "cargo" if root == owner
                            else paths["build"] / "cargo")
    paths["tauri_build"] = (dev / "build" / "tauri" if root == owner
                            else paths["build"] / "tauri")
    for path in paths.values():
        safe_path(path)
    return paths


def _indexed_external_root(repo_root: Path | None) -> str:
    """The root the tracked index records, when that path actually exists.

    The operator's environment stays authoritative. This is only a fallback, so a host
    whose root is recorded but not exported stops silently skipping the tests that need
    it -- nine tool-backed format cases were being skipped here for exactly that reason.
    A recorded path that is not a directory is ignored, so CI is unaffected.
    """
    if repo_root is None:
        return ""
    index = repo_root / "config" / "environment" / "external-resources-index.json"
    try:
        recorded = json.loads(index.read_text(encoding="utf-8")).get("external_root")
    except (OSError, ValueError):
        return ""
    if isinstance(recorded, str) and recorded.strip() and Path(recorded).is_dir():
        return recorded.strip()
    return ""


def _declared_resolver(repo_root: Path | None):
    """The worker tool resolver, loaded by file path from the tree being launched.

    `services/python-workers/tool_paths.py` is the single place the declaration is read.
    This loader used to derive tool paths itself, and named a Rust root
    (`toolchains/rust`) that the manifest (`10-toolchains/cargo/bin/rustc.exe`) and
    `scripts/ci/cargo_test.bat` (`RUSTUP_HOME` under `ARCHEAXIS_RUST_TOOLCHAINS`) did not
    name — three roots for one tool, and only the ones nobody declared were the ones that
    actually worked. Reading the declaration is now the only way discovery happens, so a
    path that is not declared cannot be exported by accident.
    """
    root = repo_root or Path(__file__).resolve().parents[2]
    module_path = root / "services" / "python-workers" / "tool_paths.py"
    if not module_path.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("dev_tool_paths", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Variables a resource may need for *its own* child process but that must never be set on
# every child this launcher spawns. `HOME` is the live case: antiword only finds its character
# maps in `$HOME/.antiword`, so the mapping directory's parent is handed to that engine by the
# conversion worker, and the docstring rule "never changes HOME" still holds here.
GLOBAL_ENV_DENYLIST = frozenset({
    "HOME", "USERPROFILE", "PATH", "TMP", "TEMP", "TMPDIR", "HOMEDRIVE", "HOMEPATH",
    # `CARGO_HOME` is the dependency cache this launcher routes to the project's own cache
    # directory a few lines below, and `scripts/ci/cargo_test.bat` derives the toolchain's
    # CARGO_HOME from `ARCHEAXIS_RUST_TOOLCHAINS` on its own. Exporting the declared value here
    # would silently move every Rust build onto the shared registry, so the declaration stays
    # available to probes and consumers while the launcher keeps its own cache routing.
    "CARGO_HOME",
})

# Resources whose consumers look them up by bare name (a worker calling `tesseract`, a shell
# calling `cargo`), so their declared directory belongs first on the child PATH.
# Promote existing entries too: a stale shim earlier on PATH must not shadow them.
PATH_LOOKUP_RESOURCES = ("tesseract", "ffmpeg")


def external_toolchain(repo_root: Path | None = None, run_tmp: Path | None = None) -> dict[str, str]:
    """Environment for the declared external toolchain, read from the declaration.

    `ARCHEAXIS_MSVC_VCVARS` and `ARCHEAXIS_RUST_TOOLCHAINS` are what the tracked Rust
    entry point `scripts/ci/cargo_test.bat` reads, and the OCR workers need tesseract
    on `PATH` with a `TESSDATA_PREFIX` that exists. This host has all of them under the
    registered external root, but nothing wired them together, so `cargo test` failed
    with ``linker `link.exe` not found`` and an OCR worker failed with
    ``AAK-WORKER-003`` even though every tool was installed. Discovery is deliberately
    conditional: with no registered root, or with a path that does not exist, nothing
    is set and CI is unaffected. A variable that is already set always wins, except
    `PATH`, where declared native directories are promoted without duplicate entries.
    """
    root_text = ""
    for name in ("OS_EXTERNAL_CONFIG", "ARCHEAXIS_EXTERNAL_ROOT"):
        root_text = os.environ.get(name, "").strip()
        if root_text:
            break
    if not root_text:
        root_text = _indexed_external_root(repo_root)
    if not root_text:
        return {}
    root = Path(root_text)
    if not root.is_dir():
        return {}
    discovered: dict[str, str] = {}
    # Give the child the root variable as well: the worker tool resolver reads it to locate
    # a declared ffmpeg, and without it the windowed and OCR cases skip rather than run.
    if not os.environ.get("ARCHEAXIS_EXTERNAL_ROOT", "").strip():
        discovered["ARCHEAXIS_EXTERNAL_ROOT"] = str(root)
    resolver = _declared_resolver(repo_root)
    if resolver is None:
        # No resolver to read the declaration with: the root is still correct to export, and
        # nothing else may be invented. A run tree without `services/python-workers/tool_paths.py`
        # gets a named root and no tool bindings, rather than a guessed layout.
        return discovered

    def usable(variable: str, value: str) -> bool:
        """An inherited value counts only when the location it names really exists."""
        if variable in {"ARCHEAXIS_MSVC_VCVARS"}:
            return Path(value).is_file()
        return bool(value.strip()) and (Path(value).is_file() or Path(value).is_dir())

    for name in resolver.declared_names():
        for variable, value in resolver.required_environment(name, root=root).items():
            if variable in GLOBAL_ENV_DENYLIST:
                continue
            inherited = os.environ.get(variable, "").strip()
            if inherited and usable(variable, inherited):
                continue
            discovered[variable] = value

    msvc = resolver.declared_location("msvc", root=root)
    if msvc and not Path(os.environ.get("ARCHEAXIS_MSVC_VCVARS", "")).is_file():
        discovered["ARCHEAXIS_MSVC_VCVARS"] = msvc

    # One Rust binding, shared with the manifest and cargo_test.bat: the declared rustc/cargo
    # live in `<root>/toolchains/rust/cargo/bin`, `RUSTUP_HOME` comes from the declaration, and
    # `ARCHEAXIS_RUST_TOOLCHAINS` is the directory holding both `cargo/` and `rustup/` — exactly
    # the contract cargo_test.bat:45-53 expands into `%ARCHEAXIS_RUST_TOOLCHAINS%\cargo` and
    # `\rustup`. `RUSTUP_HOME` is not decoration: without it the declared rustc dies with
    # ``Missing manifest in toolchain`` while the neighbouring cargo proxy quietly answers a
    # *different* version from the host default.
    rust_location = resolver.declared_location("rust", root=root)
    rust_rustup = discovered.get("RUSTUP_HOME") or os.environ.get("RUSTUP_HOME", "").strip()
    if rust_location and rust_rustup:
        common = Path(rust_location).parents[2]          # <root>/toolchains/rust (holds cargo/ and rustup/)
        if (Path(rust_rustup).parent == common
                and (common / "cargo" / "bin" / "cargo.exe").is_file()):
            inherited_rust = os.environ.get("ARCHEAXIS_RUST_TOOLCHAINS", "").strip()
            if not (inherited_rust and (Path(inherited_rust) / "cargo" / "bin" / "cargo.exe").is_file()):
                discovered["ARCHEAXIS_RUST_TOOLCHAINS"] = str(common)

    existing_path = os.environ.get("PATH", "")
    # The scoop shims on this host are stale - they point at a sibling `toolchains`
    # tree that does not exist, so a shim is present but cannot start its target. The
    # application trees themselves are intact, so expose those instead of the shims.
    declared_directories: list[str] = []
    for name in PATH_LOOKUP_RESOURCES:
        located = resolver.declared_location(name, root=root)
        if located:
            declared_directories.append(str(Path(located).parent))
    if rust_location:
        cargo_bin = str(Path(rust_location).parent)
        if (Path(cargo_bin) / "cargo.exe").is_file():
            declared_directories.append(cargo_bin)
    if declared_directories:
        def path_key(value: str) -> str:
            return os.path.normcase(os.path.normpath(value))

        prepend: list[str] = []
        declared_keys: set[str] = set()
        for directory in declared_directories:
            key = path_key(directory)
            if key not in declared_keys:
                prepend.append(directory)
                declared_keys.add(key)
        tail = [entry for entry in existing_path.split(os.pathsep)
                if path_key(entry) not in declared_keys] if existing_path else []
        child_path = os.pathsep.join([*prepend, *tail])
        if child_path != existing_path:
            discovered["PATH"] = child_path

    # The resource probe sample (a rendered OCR image the engine reads back) belongs to this
    # run, not to the machine temp, so a verification step cannot leave task-scoped residue.
    probe_tmp = run_tmp if run_tmp is not None else os.environ.get("ARCHEAXIS_RUN_TMP", "").strip()
    if probe_tmp:
        directory = Path(probe_tmp) if isinstance(probe_tmp, str) else probe_tmp
        # An explicitly named run directory is created by the consumer (`mkdir(parents=True)`),
        # so it is not required to exist yet here; an inherited string is checked.
        if (run_tmp is not None or directory.is_dir()) and not os.environ.get(
                "ARCHEAXIS_RESOURCE_PROBE_WORKDIR", ""):
            discovered["ARCHEAXIS_RESOURCE_PROBE_WORKDIR"] = str(directory / "resource-probe")

    return discovered


PRIVATE_SOURCE_PARTS = frozenset({
    '.codex', '.dsh', '.hermes', '.zcode', '.ssh', '.aws', '.azure',
    '.gnupg', '.claude', '.agents', '.npmrc', '.pypirc', '.netrc', '.hilo',
    'credentials', 'keychain', 'agent-private', 'private-agent-state',
})


def private_source_path(relative: Path) -> bool:
    """Path spelling only; never stat/read protected state to classify it."""
    return relative.as_posix().casefold() == 'test-results.log' or any(
        part.casefold() in PRIVATE_SOURCE_PARTS
        or part.casefold().startswith('.env') for part in relative.parts)


def _private_diff_exclusions() -> tuple[str, ...]:
    # Exclude before Git constructs a binary diff, not after reading its output.
    return (':(top,icase,exclude)test-results.log',) + tuple(
                 pattern for part in sorted(PRIVATE_SOURCE_PARTS | {'.env*'})
                 for pattern in (f':(glob,icase,exclude)**/{part}',
                                 f':(glob,icase,exclude)**/{part}/**'))


def worktree_identity(root: Path) -> tuple[bool, str]:
    """Identity of public working source; private runtime state is not source.

    Keep all Git access behind git() so callers can stub that single boundary.
    Tracked protected paths are an error: neither read nor silently qualify them.
    Untracked .hilo runtime files are excluded without opening them. Other
    protected untracked paths keep the existing explicit refusal behavior.
    """
    tracked = filter(None, git(root, 'ls-files', '--cached', '-z').split('\0'))
    for name in tracked:
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or private_source_path(relative):
            raise ValueError('protected source path cannot be included in run identity')
        # Reject tracked reparse points before Git can inspect working bytes.
        safe_path(root / relative)
    names = sorted(filter(None, git(root, 'ls-files', '--others',
                                    '--exclude-standard', '-z').split('\0')))
    public_files = []
    for name in names:
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('protected source path cannot be included in run identity')
        if private_source_path(relative):
            if any(part.casefold() == '.hilo' for part in relative.parts):
                continue
            raise ValueError('protected source path cannot be included in run identity')
        path = safe_path(root / relative)
        path.relative_to(root.absolute())
        public_files.append((name, path))
    diff = git(root, 'diff', 'HEAD', '--binary', '--', '.', *_private_diff_exclusions())
    digest = hashlib.sha256()
    digest.update(diff.encode('utf-8', 'surrogateescape'))
    for name, path in public_files:
        digest.update(name.encode('utf-8', 'surrogateescape'))
        if path.is_file():
            digest.update(str(path.stat().st_size).encode('ascii'))
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
    return bool(diff) or bool(public_files), digest.hexdigest()


def environment(paths: dict[str, Path]) -> dict[str, str]:
    cache, build = paths["cache"], paths["build"]
    dirty, patch_sha256 = worktree_identity(paths["root"])
    result = {
        "ARCHEAXIS_DEV_ROOT": str(paths["dev"]),
        "ARCHEAXIS_RUN_ROOT": str(paths["run"]),
        "ARCHEAXIS_SOURCE_COMMIT": git(paths["root"], "rev-parse", "HEAD"),
        "ARCHEAXIS_SOURCE_TREE": git(paths["root"], "rev-parse", "HEAD^{tree}"),
        # Must travel with the commit: a consumer that reads only the commit cannot
        # tell a committed qualification from a local working state.
        "ARCHEAXIS_SOURCE_DIRTY": "1" if dirty else "0",
        "ARCHEAXIS_SOURCE_PATCH_SHA256": patch_sha256,
        "ARCHEAXIS_WORKTREE_ROOT": str(paths["root"]),
        "ARCHEAXIS_RUN_ID": paths["run"].name,
        "ARCHEAXIS_PYTHON": sys.executable,
        "VNEXT_RECEIPT_OUT": str(paths["artifacts"] / "vnext-journey.json"),
        "ARCHEAXIS_BUILD_ROOT": str(build),
        "ARCHEAXIS_FRONTEND_DIST": str(paths["frontend_dist"]),
        "ARCHEAXIS_TAURI_CONFIG": str(paths["tauri_config"]),
        "TMP": str(paths["tmp"]), "TEMP": str(paths["tmp"]),
        "TMPDIR": str(paths["tmp"]),
        # An absolute Python script gets its own directory as ``sys.path[0]``;
        # expose the exact checkout root so imports such as ``shared`` and
        # ``app`` do not depend on an editable install or the caller's cwd.
        # Replace, rather than append to, an inherited PYTHONPATH so stale
        # checkouts and foreign modules cannot mask the current source tree.
        "PYTHONPATH": str(paths["root"]),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPYCACHEPREFIX": str(paths["run"] / "pycache"),
        "UV_CACHE_DIR": str(cache / "uv"),
        "UV_PROJECT_ENVIRONMENT": str(build / "venv"),
        "PIP_CACHE_DIR": str(cache / "pip"),
        "npm_config_cache": str(cache / "npm"),
        "PLAYWRIGHT_BROWSERS_PATH": str(cache / "playwright"),
        "CARGO_TARGET_DIR": str(paths["cargo_build"]),
        "ARCHEAXIS_CARGO_CORE_TARGET_DIR": str(paths["cargo_build"]),
        "ARCHEAXIS_CARGO_TAURI_TARGET_DIR": str(paths["tauri_build"]),
        # Retain reusable compiled dependencies, without accumulating per-edit
        # incremental object archives in this project's long-lived worktrees.
        "CARGO_INCREMENTAL": "0",
        "CARGO_HOME": str(cache / "cargo"),
        "NUGET_PACKAGES": str(cache / "nuget"),
        "NUGET_HTTP_CACHE_PATH": str(cache / "nuget-http"),
        "NUGET_PLUGINS_CACHE_PATH": str(cache / "nuget-plugins"),
        "NUGET_SCRATCH": str(paths["tmp"] / "nuget-scratch"),
        "DOTNET_CLI_HOME": str(paths["run"] / "dotnet"),
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_GENERATE_ASPNET_CERTIFICATE": "false",
        "DOTNET_CLI_UI_LANGUAGE": "en-US",
        "MSBUILDTERMINALLOGGER": "off",
    }
    for name, value in result.items():
        if name.endswith(("_DIR", "_ROOT", "_PATH", "_HOME", "_PACKAGES")) or name in (
            "TMP", "TEMP", "TMPDIR", "PYTHONPYCACHEPREFIX", "npm_config_cache",
            "UV_PROJECT_ENVIRONMENT",
            "NUGET_SCRATCH",
        ):
            safe_path(Path(value))
    # Applied after the validation above: the registered external root is a real
    # absolute path outside the checkout, and an already-set operator value wins.
    result.update(external_toolchain(paths["root"], paths["tmp"]))
    return result


def tauri_overlay(paths: dict[str, Path]) -> dict[str, dict[str, str]]:
    """Tauri parses a Windows drive path as a URL; use a directory-relative spelling."""
    directory = os.path.relpath(paths["frontend_dist"], paths["root"] / "src-tauri")
    if Path(directory).is_absolute() or ":" in directory:
        raise ValueError("Tauri frontend directory must be relative to its manifest")
    return {"build": {"frontendDist": directory.replace(os.sep, "/")}}


def prepare(paths: dict[str, Path]) -> dict[str, str]:
    values = environment(paths)
    # Exclusive run allocation prevents two callers from sharing writable results.
    paths["run"].mkdir(parents=True, exist_ok=False)
    for key in ("tmp", "logs", "artifacts", "cache", "build"):
        paths[key].mkdir(parents=True, exist_ok=True)
    with paths["tauri_config"].open("x", encoding="utf-8", newline="\n") as output:
        json.dump(tauri_overlay(paths), output)
        output.write("\n")
    # Every new run starts with a named ownership/retention record. Unknown
    # retention is preserved until reviewed, never expired by age alone.
    with (paths["run"] / "run-metadata.json").open("x", encoding="utf-8", newline="\n") as output:
        json.dump({"schema": "aaos.run-retention/v1", "owner": "ArcheAxis-Knowledge-OS",
                   "worktree_root": str(paths["root"]), "run_id": paths["run"].name,
                   "created_at": datetime.now(timezone.utc).isoformat(),
                   "source_commit": values["ARCHEAXIS_SOURCE_COMMIT"],
                   "source_patch_sha256": values["ARCHEAXIS_SOURCE_PATCH_SHA256"],
                   "class": "run-evidence", "retention": "UNCLASSIFIED_PRESERVE",
                   "review_after_days": 14, "automatic_deletion": False}, output, indent=2)
        output.write("\n")
    return values


def write_env_file(destination: Path, values: dict[str, str]) -> Path:
    """Persist a run's environment for a later step of the *same* run.

    CI learns the run identity through the runner-owned `GITHUB_ENV` file. A local
    shell has no equivalent, so a caller that must hand one run's identity to a
    following gate (for example `scripts/ci/check_vnext_receipt.py`) had to
    reconstruct `ARCHEAXIS_RUN_ROOT`/`VNEXT_RECEIPT_OUT`/`ARCHEAXIS_SOURCE_COMMIT`
    by hand - or fake `GITHUB_ACTIONS`. Writing the same mapping this launcher
    already computes keeps the two paths from drifting, and the gate keeps every
    identity check it had. An empty `destination` is a caller error, not a silent
    no-op, because `Path("")` is `Path(".")`.
    """
    target = safe_path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, value in values.items():
        if "\n" in value or "\r" in value:
            raise ValueError(f"invalid environment value for {name}")
        lines.append(f"{name}={value}\n")
    # Exclusive creation: a stale file from an earlier run must not be mistaken for
    # this run's identity, and silently overwriting would hide that mistake.
    with open(target, "x", encoding="utf-8", newline="\n") as output:
        output.writelines(lines)
    return target


def read_env_file(source: Path) -> dict[str, str]:
    """Read a `NAME=VALUE` file written by :func:`write_env_file`.

    Kept here (rather than only inside a consumer) so the local operator flow has
    one reader, while `scripts/ci/check_vnext_receipt.py` stays import-free: CI runs
    that gate as a script, so `sys.path[0]` is `scripts/ci` and a repository import
    would fail there. `tests/runtime-paths/test_vnext_receipt.py` pins the two
    implementations together.
    """
    mapping: dict[str, str] = {}
    for line in safe_path(source).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"invalid environment line: {name[:40]!r}")
        mapping[name] = value
    return mapping


def pytest_environment(root: Path) -> Path:
    inherited = os.environ.get("ARCHEAXIS_RUN_ROOT")
    if inherited:
        run = safe_path(Path(inherited))
        expected = layout(root)
        if run.parent != expected["run"].parent or not run.is_dir():
            raise ValueError("pytest run belongs to a different worktree")
        return run
    paths = layout(root)
    os.environ.update(prepare(paths))
    return paths["run"]


def artifact_directory(root: Path, namespace: str) -> Path:
    """Allocate one unique artifact directory inside the validated current run."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", namespace):
        raise ValueError("invalid artifact namespace")
    run = pytest_environment(root)
    directory = safe_path(run / "artifacts" / namespace / uuid.uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def state_path(root: Path, namespace: str, filename: str) -> Path:
    """Route persistent development metadata without allocating or writing a run."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", namespace):
        raise ValueError("invalid state namespace")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", filename):
        raise ValueError("invalid state filename")
    paths = layout(root)
    identity = paths["run"].parent.name
    return safe_path(paths["dev"] / "state" / identity / namespace / filename)


def stop_owned_process(child: subprocess.Popen) -> None:
    """Stop only the live process tree created by this launcher, then reap it."""
    if child.poll() is not None:
        return
    if os.name == "nt":
        result = subprocess.run(
            ["taskkill.exe", "/PID", str(child.pid), "/T", "/F"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=15, check=False,
        )
        if result.returncode and child.poll() is None:
            raise RuntimeError("owned process tree cleanup failed")
    else:
        with suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGKILL)
    child.wait(timeout=15)


def _prepare_child_command(command: list[str]) -> list[str]:
    """Make Windows batch entry points executable without enabling a shell."""
    if os.name == "nt" and command and Path(command[0]).suffix.lower() in {".bat", ".cmd"}:
        # Passing the executable and arguments as separate items lets the
        # Windows process builder quote the /c command correctly, including
        # paths with spaces, without enabling shell expansion globally.
        batch_command = [command[0].replace('/', '\\'), *command[1:]]
        return ["cmd.exe", "/d", "/c", *batch_command]
    return command


def configure_console_streams() -> None:
    """Keep UTF-8 child output lossless even when this launcher started in GBK."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def core_build_command(root: Path) -> list[str]:
    """The only command eligible for a measured Core release qualification."""
    return [str(safe_path(root / "scripts/ci/cargo_test.bat")),
            "build", "--release", "--locked", "--offline", "-p", "archeaxis-api"]


def build_file_identity(path: Path) -> dict:
    path = safe_path(path)
    if not path.is_file():
        raise ValueError(f"build output is missing: {path}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}


def read_core_build(receipt: Path, paths: dict[str, Path], env: dict[str, str]) -> dict:
    """Consume an output hash captured by the runner, never infer an old build."""
    receipt = safe_path(receipt)
    if (receipt.name != "execution.json" or receipt.parent.name != "artifacts"
            or receipt.parent.parent.parent != paths["run"].parent):
        raise ValueError("Core build receipt is outside this worktree's runs")
    value = json.loads(receipt.read_text(encoding="utf-8"))
    run = safe_path(Path(value.get("run_root", "")))
    expected = layout(paths["root"], run.name)
    if run != expected["run"] or receipt != run / "artifacts/execution.json":
        raise ValueError("Core build receipt has foreign run ownership")
    if (value.get("status") != "LOCAL_PASS" or value.get("exit_code") != 0
            or value.get("child_exit_code") != 0 or value.get("source_consistent") is not True
            or value.get("command") != core_build_command(paths["root"])
            or value.get("worktree_root") != str(paths["root"])
            or value.get("source_commit") != env["ARCHEAXIS_SOURCE_COMMIT"]
            or value.get("source_commit_after") != env["ARCHEAXIS_SOURCE_COMMIT"]
            or value.get("source_tree") != env["ARCHEAXIS_SOURCE_TREE"]
            or value.get("source_patch_sha256") != env["ARCHEAXIS_SOURCE_PATCH_SHA256"]
            or value.get("source_patch_sha256_after") != env["ARCHEAXIS_SOURCE_PATCH_SHA256"]):
        raise ValueError("Core receipt does not qualify this source and release command")
    qualification = value.get("core_build", {})
    if qualification.get("schema") != "archeaxis.core-build/v1":
        raise ValueError("Core receipt lacks a contemporaneous output hash")
    actual = build_file_identity(paths["cargo_build"] / "release/archeaxis-api.exe")
    if qualification.get("artifact") != actual:
        raise ValueError("Core output differs from its completed build")
    return actual


def main() -> int:
    configure_console_streams()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id")
    parser.add_argument("--pytest", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--qualify-core-build", action="store_true",
                        help="record the output hash of the fixed offline locked Core release build")
    parser.add_argument("--github-env", action="store_true",
                        help="register paths through the GitHub runner environment file")
    parser.add_argument("--env-file", type=Path,
                        help="also write this run's environment to a NAME=VALUE file for a "
                             "later step of the same run (local equivalent of --github-env)")
    parser.add_argument("--require-worktree", type=Path,
                        help="refuse to run unless the resolved Git worktree root is exactly "
                             "this path; makes 'ran against the wrong checkout' impossible "
                             "instead of a convention")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        paths = layout(args.root, args.run_id)
        if args.require_worktree is not None:
            required = safe_path(args.require_worktree)
            if paths["root"].resolve() != required.resolve():
                raise ValueError(
                    f"worktree guard: resolved root {paths['root']} is not the required "
                    f"{required}")
        env = dict(os.environ)
        env.update(prepare(paths))
        if args.github_env:
            # GITHUB_ENV is the runner-owned environment API, not project storage.
            # Never inspect its existing content or any authentication variables.
            destination = os.environ.get("GITHUB_ENV")
            if not destination or os.environ.get("GITHUB_ACTIONS") != "true":
                raise ValueError("--github-env requires the GitHub Actions runner")
            with open(destination, "a", encoding="utf-8") as output:
                for name, value in environment(paths).items():
                    if "\n" in value or "\r" in value:
                        raise ValueError("invalid environment path")
                    output.write(f"{name}={value}\n")
            print(f"[dev] GitHub environment initialized: {paths['run']}")
            for name in ("CARGO_HOME", "CARGO_TARGET_DIR", "ARCHEAXIS_CARGO_TAURI_TARGET_DIR", "UV_CACHE_DIR"):
                print(f"[dev] {name}={env[name]}")
            return 0
        if args.env_file is not None:
            # Recorded before the child starts so a run that fails or is cancelled
            # still leaves the identity its own receipts must be checked against.
            write_env_file(args.env_file, environment(paths))
            print(f"[dev] environment file written: {args.env_file}", flush=True)
        command = args.command
        if command[:1] == ["--"]:
            command = command[1:]
        if args.pytest:
            targets = ["tests", "knowledge_base/tests", "integration-tests"] if args.full else ["tests"]
            if any((paths["root"] / arg.split("::")[0]).exists()
                   for arg in command if not arg.startswith("-")):
                targets = []
            if any(arg.startswith("--basetemp") for arg in command):
                raise ValueError("basetemp is owned by the development launcher")
            command = [sys.executable, "-m", "pytest", *targets,
                       f"--basetemp={paths['tmp'] / 'pytest'}",
                       "-o", f"cache_dir={paths['run'] / 'pytest-cache'}", *command]
        if not command:
            raise ValueError("a child command or --pytest is required")
        if args.qualify_core_build:
            if command != core_build_command(paths["root"]):
                raise ValueError("Core qualification requires the exact canonical release command")
            # The tracked batch runner honors this override before CARGO_TARGET_DIR.
            env["ARCHEAXIS_CARGO_TARGET_DIR"] = str(paths["cargo_build"])
            env["CARGO_TARGET_DIR"] = str(paths["cargo_build"])
        started = datetime.now(timezone.utc).isoformat()
        started_tick = time.perf_counter()
        dirty, patch_sha256 = worktree_identity(paths["root"])
        record = {"source_commit": git(paths["root"], "rev-parse", "HEAD"),
                  "source_tree": git(paths["root"], "rev-parse", "HEAD^{tree}"),
                  # `dirty` used to be a bare boolean nobody consumed. It is now the
                  # discriminator the receipt gate binds against, so a run that tested
                  # HEAD plus uncommitted edits can no longer present itself as a
                  # committed-SHA qualification.
                  "dirty": dirty, "source_patch_sha256": patch_sha256,
                  "worktree_root": str(paths["root"]),
                  "started_at": started, "run_root": str(paths["run"]),
                  "executable": command[0], "argument_count": len(command) - 1,
                  "command": command,
                  "python": sys.version, "boundary": "environment-routing-not-sandbox"}
        print(f"[dev] run={paths['run']}", flush=True)
        code = 1
        child = None
        try:
            # No shell expansion or visible console for helper processes on Windows.
            child = subprocess.Popen(
                _prepare_child_command(command), cwd=paths["root"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                start_new_session=os.name != "nt",
            )
            assert child.stdout is not None
            with (paths["logs"] / "execution.log").open("x", encoding="utf-8") as log:
                for line in child.stdout:
                    log.write(line)
                    log.flush()
                    print(line, end="", flush=True)
            code = child.wait()
        except BaseException as exc:
            if isinstance(exc, KeyboardInterrupt):
                code = 130
                record["cancelled"] = True
            if child is not None:
                try:
                    stop_owned_process(child)
                    record["owned_process_cleanup"] = "completed"
                except (OSError, RuntimeError, subprocess.TimeoutExpired) as cleanup_error:
                    record["owned_process_cleanup"] = "failed"
                    code = 1
                    raise RuntimeError("owned process cleanup failed; inspect the run") from cleanup_error
            if not isinstance(exc, KeyboardInterrupt):
                raise
        finally:
            if child is not None and child.stdout is not None:
                child.stdout.close()
            record["child_exit_code"] = code
            if args.qualify_core_build and code == 0:
                try:
                    record["core_build"] = {
                        "schema": "archeaxis.core-build/v1",
                        "artifact": build_file_identity(paths["cargo_build"] / "release/archeaxis-api.exe"),
                    }
                except (OSError, ValueError) as error:
                    code = 2
                    record["qualification_error"] = str(error)
            after_head = git(paths["root"], "rev-parse", "HEAD")
            _, after_patch = worktree_identity(paths["root"])
            consistent = (after_head == record["source_commit"]
                          and after_patch == record["source_patch_sha256"])
            record.update(source_commit_after=after_head, source_patch_sha256_after=after_patch,
                          source_consistent=consistent,
                          status="INVALIDATED" if not consistent else "LOCAL_PASS" if code == 0 else "FAIL",
                          log=str(paths["logs"] / "execution.log"))
            if not consistent:
                code = 3
                record.pop("core_build", None)
            record.update(exit_code=code, ended_at=datetime.now(timezone.utc).isoformat(), seconds=time.perf_counter() - started_tick)
            (paths["artifacts"] / "execution.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return code
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"development environment failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
