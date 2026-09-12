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
import stat
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    ).strip()


def safe_path(path: Path) -> Path:
    """Reject links/junctions before resolving; never follow a redirected ancestor."""
    path = Path(os.path.abspath(path))
    if path.drive.upper() == "E:" or str(path).startswith("\\\\"):
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
    for path in paths.values():
        safe_path(path)
    return paths


def environment(paths: dict[str, Path]) -> dict[str, str]:
    cache, build = paths["cache"], paths["build"]
    result = {
        "ARCHEAXIS_DEV_ROOT": str(paths["dev"]),
        "ARCHEAXIS_RUN_ROOT": str(paths["run"]),
        "ARCHEAXIS_SOURCE_COMMIT": git(paths["root"], "rev-parse", "HEAD"),
        "ARCHEAXIS_RUN_ID": paths["run"].name,
        "ARCHEAXIS_PYTHON": sys.executable,
        "VNEXT_RECEIPT_OUT": str(paths["artifacts"] / "vnext-journey.json"),
        "ARCHEAXIS_BUILD_ROOT": str(build),
        "TMP": str(paths["tmp"]), "TEMP": str(paths["tmp"]),
        "TMPDIR": str(paths["tmp"]),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPYCACHEPREFIX": str(paths["run"] / "pycache"),
        "UV_CACHE_DIR": str(cache / "uv"),
        "UV_PROJECT_ENVIRONMENT": str(build / "venv"),
        "PIP_CACHE_DIR": str(cache / "pip"),
        "npm_config_cache": str(cache / "npm"),
        "PLAYWRIGHT_BROWSERS_PATH": str(cache / "playwright"),
        "CARGO_TARGET_DIR": str(build / "cargo"),
        "NUGET_PACKAGES": str(cache / "nuget"),
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
        ):
            safe_path(Path(value))
    return result


def prepare(paths: dict[str, Path]) -> dict[str, str]:
    values = environment(paths)
    # Exclusive run allocation prevents two callers from sharing writable results.
    paths["run"].mkdir(parents=True, exist_ok=False)
    for key in ("tmp", "logs", "artifacts", "cache", "build"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return values


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id")
    parser.add_argument("--pytest", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--github-env", action="store_true",
                        help="register paths through the GitHub runner environment file")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        paths = layout(args.root, args.run_id)
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
            return 0
        command = args.command
        if command[:1] == ["--"]:
            command = command[1:]
        if args.pytest:
            targets = ["tests", "knowledge_base/tests"] if args.full else ["tests"]
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
        started = datetime.now(timezone.utc).isoformat()
        record = {"source_commit": git(paths["root"], "rev-parse", "HEAD"),
                  "source_tree": git(paths["root"], "rev-parse", "HEAD^{tree}"),
                  "dirty": bool(git(paths["root"], "status", "--porcelain")),
                  "started_at": started, "run_root": str(paths["run"]),
                  "executable": command[0], "argument_count": len(command) - 1,
                  "python": sys.version, "boundary": "environment-routing-not-sandbox"}
        print(f"[dev] run={paths['run']}", flush=True)
        code = 1
        try:
            # No shell expansion or visible console for helper processes on Windows.
            child = subprocess.Popen(
                command, cwd=paths["root"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            assert child.stdout is not None
            for line in child.stdout:
                print(line, end="", flush=True)
            code = child.wait()
        finally:
            record.update(exit_code=code, ended_at=datetime.now(timezone.utc).isoformat())
            (paths["artifacts"] / "execution.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return code
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"development environment failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
