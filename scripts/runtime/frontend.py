"""Run-scoped frontend and Tauri builds; no installation or publication."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__:
    from . import dev
    from .build_timing import BuildTimings
else:
    import dev
    from build_timing import BuildTimings

ROOT = Path(__file__).absolute().parents[2]


def msvc_environment(env: dict[str, str], paths: dict[str, Path], node: str | None = None) -> dict[str, str]:
    """Initialize the declared compiler for this child; read only tool search variables."""
    if os.name != "nt" or not env.get("ARCHEAXIS_MSVC_VCVARS"):
        return env
    vcvars = dev.safe_path(Path(env["ARCHEAXIS_MSVC_VCVARS"]))
    if any(char in str(vcvars) for char in '\n\r"%'):
        raise ValueError("invalid declared MSVC path")
    batch = paths["tmp"] / "frontend-msvc.cmd"
    # Keep the command file ASCII; Windows passes this path through its Unicode
    # environment block, including checkout paths containing Chinese characters.
    batch.write_text('@echo off\ncall "%ARCHEAXIS_MSVC_INIT_SCRIPT%" >nul 2>&1\nif errorlevel 1 exit /b 1\nset PATH\nset INCLUDE\nset LIB\nset LIBPATH\nexit /b 0\n', encoding="ascii")
    # cmd.exe loses executable lookup with an oversized inherited PATH. In particular,
    # vcvars can return 0 while its suppressed `reg query` fails to discover the SDK.
    windows_root = next((value for key, value in env.items()
                         if key.casefold() in {"systemroot", "windir"}), None)
    if not windows_root:
        raise ValueError("Windows root is missing from the declared environment")
    windows = dev.safe_path(Path(windows_root))
    search = [windows / "System32", windows]
    if env.get("ARCHEAXIS_RUST_TOOLCHAINS"):
        search.append(dev.safe_path(Path(env["ARCHEAXIS_RUST_TOOLCHAINS"])) / "cargo/bin")
    if node:
        executable = dev.safe_path(Path(node))
        if not executable.is_file():
            raise ValueError("declared Node executable is missing")
        search.append(executable.parent)
    git = shutil.which("git", path=next((v for k, v in env.items() if k.casefold() == "path"), ""))
    if not git:
        raise ValueError("Git executable is missing from the build environment")
    search.append(dev.safe_path(Path(git)).parent)
    child = {k: v for k, v in env.items() if k.casefold() != "path"}
    child["ARCHEAXIS_MSVC_INIT_SCRIPT"] = str(vcvars)
    child["PATH"] = os.pathsep.join(dict.fromkeys(str(dev.safe_path(p)) for p in search))
    result = subprocess.run([str(windows / "System32/cmd.exe"),
                             "/d", "/c", str(batch)], env=child, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", cwd=vcvars.parent)
    if result.returncode:
        raise ValueError("declared MSVC initialization failed")
    values = dict(child)
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator and name.casefold() in {"path", "include", "lib", "libpath"}:
            # Windows environment keys are case-insensitive; eliminate duplicate spellings.
            values = {k: v for k, v in values.items() if k.casefold() != name.casefold()}
            values[name.upper()] = value
    for variable, filenames in (("LIB", ("kernel32.lib", "ucrt.lib")),
                                ("INCLUDE", ("Windows.h", "corecrt.h"))):
        directories = [dev.safe_path(Path(p)) for p in values.get(variable, "").split(os.pathsep) if p]
        for filename in filenames:
            candidates = [dev.safe_path(p / filename) for p in directories]
            if not any(p.is_file() and (variable != "LIB" or p.parent.name.casefold() == "x64") for p in candidates):
                raise ValueError(f"declared MSVC initialization lacks SDK {filename}")
    if len(values.get("PATH", "")) >= 8191:
        raise ValueError("declared MSVC child PATH exceeds cmd.exe lookup limit")
    return values


def validate_inherited(root: Path) -> None:
    """An inherited router must belong to this checkout, before allocating anything."""
    if os.environ.get("ARCHEAXIS_WORKTREE_ROOT"):
        if dev.safe_path(Path(os.environ["ARCHEAXIS_WORKTREE_ROOT"])) != root:
            raise ValueError("foreign inherited worktree root")
    if os.environ.get("ARCHEAXIS_RUN_ROOT"):
        run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
        paths = dev.layout(root, run.name)
        for variable, key in (("ARCHEAXIS_RUN_ROOT", "run"), ("ARCHEAXIS_BUILD_ROOT", "build"),
                              ("ARCHEAXIS_FRONTEND_DIST", "frontend_dist"), ("ARCHEAXIS_TAURI_CONFIG", "tauri_config")):
            if os.environ.get(variable) and dev.safe_path(Path(os.environ[variable])) != paths[key]:
                raise ValueError(f"foreign inherited {variable}")
    elif any(os.environ.get(name) for name in ("ARCHEAXIS_FRONTEND_DIST", "ARCHEAXIS_TAURI_CONFIG", "ARCHEAXIS_BUILD_ROOT")):
        raise ValueError("inherited build paths require a canonical run")


def tauri_commands(node, cli, arguments, overlay, separate_bundle):
    split = arguments.index("--") if "--" in arguments else len(arguments)
    normal = [node, str(cli), *arguments[:split], "--config", str(overlay), *arguments[split:]]
    if not separate_bundle:
        return [("tauri-with-bundle", normal)]
    if split != len(arguments):
        raise ValueError("separate bundle timing cannot forward raw Cargo arguments")
    shared = []
    bundles = None
    index = 1
    while index < len(arguments):
        flag = arguments[index]
        if flag in {"--config", "--target", "--features", "--bundles"}:
            if index + 1 >= len(arguments) or arguments[index + 1].startswith("-"):
                raise ValueError("missing Tauri option value")
            if flag == "--bundles":
                bundles = arguments[index + 1]
            else:
                shared.extend(arguments[index:index + 2])
            index += 2
        elif flag in {"--debug", "--ci", "--no-sign", "--verbose"}:
            shared.append(flag)
            index += 1
        else:
            raise ValueError(f"unsupported option for separate bundle timing: {flag}")
    if bundles != "nsis":
        raise ValueError("separate bundle timing requires explicit nsis target")
    shared += ["--config", str(overlay)]
    return [("tauri-compile-with-frontend-hook", [node, str(cli), "build", *shared, "--no-bundle"]),
            ("nsis-bundle", [node, str(cli), "bundle", *shared, "--bundles", bundles])]


def build(root: Path, node: str, mode: str, arguments: list[str], receipt: Path | None = None, separate_bundle: bool = False,
          core_build_receipt: Path | None = None) -> int:
    root = dev.safe_path(root)
    validate_inherited(root)
    nested = os.environ.get("ARCHEAXIS_FRONTEND_BUILD_CONTEXT")
    if nested:
        if mode != "build" or nested != os.environ.get("ARCHEAXIS_RUN_ROOT"):
            raise ValueError("invalid nested frontend build context")
        paths = dev.layout(root, Path(nested).name)
        overlay = json.loads(paths["tauri_config"].read_text(encoding="utf-8"))
        if overlay != dev.tauri_overlay(paths):
            raise ValueError("frontend overlay mismatch")
        env = dict(os.environ)
    else:
        if mode == "build" and os.environ.get("TAURI_CONFIG"):
            raise ValueError("Use npm run tauri -- build: a raw Tauri hook cannot route its parent configuration")
        paths = dev.layout(root)
        env = dict(os.environ)
        inherited_cargo = env.get("CARGO_TARGET_DIR")
        if inherited_cargo:
            cargo = dev.safe_path(Path(inherited_cargo))
            if cargo not in {paths["cargo_build"], paths["tauri_build"], paths["dev"] / "build" / "tauri"}:
                raise ValueError("foreign inherited CARGO_TARGET_DIR")
        env.update(dev.prepare(paths))
        if inherited_cargo:
            env["CARGO_TARGET_DIR"] = str(cargo)
        if mode == "tauri" and (not inherited_cargo or cargo == paths["cargo_build"]):
            env["CARGO_TARGET_DIR"] = str(paths["tauri_build"])
    env["ARCHEAXIS_FRONTEND_BUILD_CONTEXT"] = str(paths["run"])
    destination = dev.safe_path(receipt) if receipt else paths["artifacts"] / "frontend-build.json"
    destination.relative_to(paths["dev"] / "runs")
    if any(part.casefold().startswith(".env") or part.casefold() in {".codex", ".hermes", ".dsh", ".zcode", "private-agent-state"}
           for part in destination.parts):
        raise ValueError("protected frontend receipt path")
    if destination.exists():
        raise ValueError("frontend receipt already exists")
    if mode == "build":
        commands = [("frontend-typecheck", [node, str(root / "frontend/node_modules/typescript/bin/tsc"), "--noEmit"]),
                    ("frontend-vite", [node, str(root / "frontend/node_modules/vite/bin/vite.js"), "build", "--base", "./", *arguments])]
        if any(arg == "--outDir" or arg.startswith("--outDir=") for arg in arguments):
            raise ValueError("frontend output is owned by the run router")
    else:
        if not arguments or arguments[0] != "build":
            raise ValueError("npm run tauri supports build only")
        cli = root / "frontend/node_modules/@tauri-apps/cli/tauri.js"
        commands = tauri_commands(node, cli, arguments, paths["tauri_config"], separate_bundle)
        env["TAURI_CONFIG"] = paths["tauri_config"].read_text(encoding="utf-8")
    code = 1
    after = None
    qualification = {}
    timings = BuildTimings(paths["artifacts"], env)
    try:
        if core_build_receipt is not None:
            if (mode != "tauri" or separate_bundle
                    or arguments != ["build", "--no-bundle", "--", "--offline", "--locked"]
                    or dev.safe_path(Path(env["CARGO_TARGET_DIR"])) != paths["tauri_build"]):
                raise ValueError("portable qualification requires the canonical offline locked native release command")
            core_input = dev.read_core_build(core_build_receipt, paths, env)
            staged = root / ".project-local/rt"
            staged_core = dev.build_file_identity(staged / "core/archeaxis-api.exe")
            if any(staged_core[key] != core_input[key] for key in ("bytes", "sha256")):
                raise ValueError("staged Core differs from qualified Core build")
            staged_manifest = dev.build_file_identity(staged / "backend-runtime-manifest.json")
            core_receipt_identity = dev.build_file_identity(core_build_receipt)
        if mode == "tauri":
            env = msvc_environment(env, paths, node)
        for name, command in commands:
            with timings.stage(name) as stage:
                code = subprocess.call(command, cwd=root if mode == "tauri" else root / "frontend", env=env)
                stage["exit_code"] = code
            if code:
                break
        _, after = dev.worktree_identity(root)
        if after != env["ARCHEAXIS_SOURCE_PATCH_SHA256"]:
            code = 2
            raise ValueError("frontend source changed during build; receipt cannot qualify one tree")
        if code == 0 and not dev.safe_path(paths["frontend_dist"] / "index.html").is_file():
            code = 2
            raise ValueError("frontend command returned success without this run's index.html")
        if code == 0 and core_build_receipt is not None:
            host = paths["tauri_build"] / "release/ArcheAxis.exe"
            actual_core = dev.build_file_identity(host.parent / "core/archeaxis-api.exe")
            actual_manifest = dev.build_file_identity(host.parent / "backend-runtime-manifest.json")
            if (dev.read_core_build(core_build_receipt, paths, env) != core_input
                    or dev.build_file_identity(core_build_receipt) != core_receipt_identity
                    or dev.build_file_identity(staged / "core/archeaxis-api.exe") != staged_core
                    or dev.build_file_identity(staged / "backend-runtime-manifest.json") != staged_manifest
                    or any(actual_core[key] != core_input[key] for key in ("bytes", "sha256"))
                    or actual_manifest["sha256"] != staged_manifest["sha256"]):
                raise ValueError("runtime input changed or stale Tauri resources were copied")
            qualification = {
                "status": "PASS", "host": str(host), "core": actual_core["path"],
                "portable_build_arguments": arguments,
                "host_sha256": dev.build_file_identity(host)["sha256"],
                "core_sha256": actual_core["sha256"],
                "backend_manifest_sha256": actual_manifest["sha256"],
                "core_build_receipt": core_receipt_identity,
                "build_timings": dev.build_file_identity(timings.path),
            }
            _, after = dev.worktree_identity(root)
            if after != env["ARCHEAXIS_SOURCE_PATCH_SHA256"] or dev.git(root, "rev-parse", "HEAD") != env["ARCHEAXIS_SOURCE_COMMIT"]:
                raise ValueError("source changed during output qualification")
        return code
    except BaseException:
        qualification = {}
        if code == 0:
            code = 2
        raise
    finally:
        # The beforeBuild hook leaves the receipt to its parent Tauri invocation.
        if not nested:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8", newline="\n") as output:
                json.dump({"schema": "archeaxis.frontend-build/v1", "mode": mode, "exit_code": code,
                           "worktree_root": str(root), "run_root": str(paths["run"]),
                           "frontend_dist": str(paths["frontend_dist"]), "tauri_config": str(paths["tauri_config"]),
                           "source_commit": env["ARCHEAXIS_SOURCE_COMMIT"],
                           "source_tree": env["ARCHEAXIS_SOURCE_TREE"],
                           "source_patch_sha256": env["ARCHEAXIS_SOURCE_PATCH_SHA256"],
                           "source_patch_sha256_after": after,
                           "source_consistent": None if after is None else after == env["ARCHEAXIS_SOURCE_PATCH_SHA256"],
                           **qualification}, output, indent=2)
                output.write("\n")
            print(f"[frontend] receipt={destination}; dist={paths['frontend_dist']}", flush=True)


def main() -> int:
    dev.configure_console_streams()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", required=True)
    parser.add_argument("mode", choices=("build", "tauri", "verify"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--separate-bundle", action="store_true")
    parser.add_argument("--core-build-receipt", type=Path,
                        help="dev.py --qualify-core-build execution.json; use tauri -- build --no-bundle -- --offline --locked")
    args, arguments = parser.parse_known_args()
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    try:
        if args.mode == "verify":
            for name in ("ARCHEAXIS_WORKTREE_ROOT", "ARCHEAXIS_RUN_ROOT", "ARCHEAXIS_FRONTEND_DIST", "ARCHEAXIS_TAURI_CONFIG"):
                if not os.environ.get(name):
                    raise ValueError(f"missing canonical frontend environment: {name}")
            validate_inherited(dev.safe_path(ROOT))
            overlay = json.loads(dev.safe_path(Path(os.environ["ARCHEAXIS_TAURI_CONFIG"])).read_text(encoding="utf-8"))
            if overlay != dev.tauri_overlay(dev.layout(ROOT, Path(os.environ["ARCHEAXIS_RUN_ROOT"]).name)):
                raise ValueError("frontend overlay mismatch")
            return 0
        return build(ROOT, args.node, args.mode, arguments, args.receipt, args.separate_bundle, args.core_build_receipt)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"[frontend] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
