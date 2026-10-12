"""Serial local CI profiles using existing checks; never installs or publishes.

NOT_RUN is a qualification gap, not a pass. Hosted workflow commands are also
saved verbatim so this runner cannot imply coverage of an omitted CI step.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
if __package__:
    from scripts.runtime import dev, frontend
else:
    import importlib.util
    # Direct CLI: load only these repository-owned modules without sys.path edits.
    for module_name in ('dev', 'frontend'):
        spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts/runtime" / (module_name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        globals()[module_name] = module


def now():
    return datetime.now(timezone.utc).isoformat()


def source_snapshot(root):
    dirty, patch = dev.worktree_identity(root)
    names = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    ).decode("utf-8").split("\0")
    hashes = {}
    for name in sorted(set(names)):
        relative = Path(name)
        if not name or relative.suffix.lower() not in {
            ".py", ".rs", ".tsx", ".ts", ".js", ".mjs", ".css", ".json",
            ".toml", ".lock", ".yaml", ".yml", ".ps1", ".sh", ".cs", ".csproj",
        }:
            continue
        if any(p.lower().startswith(".env") or p.lower() in {
            ".codex", ".hermes", ".dsh", ".zcode", ".agents", "private-agent-state",
        } for p in relative.parts):
            continue
        path = dev.safe_path(root / relative)
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"head": dev.git(root, "rev-parse", "HEAD"), "dirty": dirty,
            "patch_sha256": patch, "file_sha256": hashes,
            "status": dev.git(root, "status", "--short")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("quick", "full"), required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--node", default=shutil.which("node"))
    parser.add_argument("--cargo", default=shutil.which("cargo"))
    parser.add_argument("--tests", nargs="*", help="Explicit affected pytest targets for quick profile")
    args = parser.parse_args()
    paths = dev.layout(ROOT, args.run_id)
    env = dict(os.environ)
    env.update(dev.prepare(paths))
    # Use only this run's isolated data, never daily Green or recovery materials.
    env.update(ARCHEAXIS_DATA_ROOT=str(paths["tmp"] / "data"),
               ARCHEAXIS_DB_PATH=str(paths["tmp"] / "data/workspace.sqlite"),
               ARCHEAXIS_CAS_ROOT=str(paths["tmp"] / "cas"),
               PYTHONPYCACHEPREFIX=str(paths["tmp"] / "pycache"))
    lock = paths["build"] / "local-ci.lock"
    handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(handle, str(os.getpid()).encode())
    os.close(handle)
    report = {"schema": "archeaxis.local-ci/v1", "profile": args.profile,
              "started_at": now(), "source_before": source_snapshot(ROOT),
              "tools": {"python": sys.version}, "checks": [],
              "cloud": "CLOUD_BLOCKED_USER_REPORTED_NOT_REQUERIED",
              "evidence_boundary": "local execution; no installation or human acceptance"}
    destination = paths["artifacts"] / "local-ci.json"

    def save():
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def run(name, command, cwd=ROOT, child_env=None):
        item = {"name": name, "command": command, "cwd": str(cwd), "started_at": now()}
        report["checks"].append(item)
        log = paths["logs"] / f"{len(report['checks']):02d}-{name}.log"
        item["log"] = str(log)
        print(f"[local-ci] {name}: {command}", flush=True)
        try:
            with log.open("x", encoding="utf-8") as output:
                child = subprocess.Popen(dev._prepare_child_command(command), cwd=cwd,
                                         env=child_env or env, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                         errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                         start_new_session=os.name != "nt")
                try:
                    for line in child.stdout:
                        output.write(line)
                        output.flush()
                        print(line, end="", flush=True)
                    item["exit_code"] = child.wait()
                finally:
                    if child.poll() is None:
                        dev.stop_owned_process(child)
                    child.stdout.close()
            item["status"] = "LOCAL_PASS" if item["exit_code"] == 0 else "FAIL"
        except OSError as exc:
            item.update(status="NOT_RUN", exit_code=None, reason=str(exc))
        item["ended_at"] = now()
        save()

    def missing(name, reason):
        report["checks"].append({"name": name, "status": "NOT_RUN", "reason": reason,
                                 "exit_code": None, "started_at": now(), "ended_at": now()})
        save()

    py = [sys.executable, "-B"]
    try:
        import yaml
        inventory = {}
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
            inventory[path.name] = workflow["jobs"]
        (paths["artifacts"] / "workflow-jobs.json").write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for package in ("pytest", "ruff", "playwright", "PyYAML"):
            try:
                report["tools"][package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                report["tools"][package] = "MISSING"
        for name, executable in (("node", args.node), ("cargo", args.cargo)):
            if executable:
                version = subprocess.run([executable, "--version"], capture_output=True, text=True, env=env)
                report["tools"][name] = {"path": executable, "exit_code": version.returncode,
                                          "version": version.stdout.strip(), "error": version.stderr.strip()}
        for name, command in (
            ("conventions", ["scripts/check_repository_conventions.py", "--source", "worktree"]),
            ("architecture", ["scripts/check_architecture.py"]),
            ("language-boundaries", ["scripts/check_language_boundaries.py"]),
            ("format-matrix", ["scripts/check_format_matrix.py", "--matrix", "docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json"]),
            ("path-conventions", ["scripts/check_path_conventions.py"]),
            ("document-authority", ["scripts/ci/check_document_authority.py"]),
            ("h01-source-trace", ["scripts/ci/check_h01_source_trace.py"]),
            ("ui-design-increment", ["scripts/ci/check_ui_design_increment.py"]),
        ):
            run(name, py + command)
        run("ruff", py + ["-m", "ruff", "check", "app", "shared", "knowledge_base",
                            "inspiration_research", "Inspiration-Research", "shared-contracts/adapters",
                            "app/workflow", "integration-tests", "scripts", "--select", "E9,F63,F7,F82"])
        targets = args.tests if args.tests is not None else [
            "tests/test_ci_classifier.py", "tests/test_ci_a0_gates.py", "tests/test_local_ci_profiles.py",
            "tests/test_project_output_routing_contract.py", "tests/test_workspace_layout_contract.py"]
        if args.profile == "full":
            targets = ["tests", "knowledge_base/tests", "integration-tests"]
        run("python-suite", py + ["-m", "pytest", *targets, "-q", "--tb=short",
                                   f"--basetemp={paths['tmp'] / 'pytest'}", "-o",
                                   f"cache_dir={paths['run'] / 'pytest-cache'}"])
        for name, command in (
            ("contracts", ["scripts/ci/check_vnext_contracts.py"]),
            ("vocabulary", ["scripts/contracts/generate_vocabulary.py", "--check"]),
            ("teaching-drift", ["scripts/contracts/generate_core_teaching.py", "--check"]),
            ("expression-drift", ["scripts/contracts/generate_expression_contract.py", "--check"]),
            ("research-drift", ["scripts/contracts/generate_research_contract.py", "--check"]),
            ("ai-asset-drift", ["scripts/contracts/generate_ai_asset_contract.py", "--check"]),
            ("resource-catalog-drift", ["scripts/contracts/generate_resource_catalog.py", "--check"]),
            ("ui-working-state-drift", ["scripts/contracts/generate_ui_working_state.py", "--check"]),
            ("media-policy", ["scripts/contracts/check_media_window_policy.py", "--check"]),
            ("workers", ["scripts/ci/check_vnext_workers.py"]),
        ):
            run(name, py + command)
        if args.node:
            run("frontend-types", [args.node, "frontend/node_modules/typescript/bin/tsc", "--noEmit", "-p", "frontend/tsconfig.json"])
            run("frontend-unit", [args.node, "frontend/node_modules/vitest/vitest.mjs", "run", "--root", "frontend"])
        else:
            missing("frontend", "Node not found; supply --node with an existing toolchain")
        if args.cargo:
            run("rust-format", [args.cargo, "fmt", "--all", "--", "--check"])
            run("tauri-format", [args.cargo, "fmt", "--manifest-path", "src-tauri/Cargo.toml", "--", "--check"])
        else:
            missing("rust", "Cargo not found; supply --cargo with an existing toolchain")
        if args.profile == "full":
            run("workers-unit", py + ["-m", "unittest", "discover", "-s", "tests/workers", "-p", "test_*.py"])
            run("compat-current-python", py + ["-m", "compileall", "-q", "app", "shared", "knowledge_base", "scripts"])
            run("compat-imports", py + ["-m", "pytest", "tests/test_imported_modules.py", "-q",
                                       f"--basetemp={paths['tmp'] / 'compat-pytest'}", "-o", f"cache_dir={paths['run'] / 'compat-cache'}"])
            if args.node:
                run("frontend-build", py + ["scripts/runtime/frontend.py", "--node", args.node, "build"])
                run("browser-smoke", py + ["scripts/a0_browser_smoke.py"])
            if args.cargo:
                compiler_env = frontend.msvc_environment(env, paths, args.node)
                run("rust-workspace", [args.cargo, "test", "--workspace", "--locked", "--offline", "--release"], child_env=compiler_env)
                run("vnext-receipt", py + ["scripts/ci/check_vnext_receipt.py"])
                run("core-build", [args.cargo, "build", "-p", "archeaxis-api", "--locked", "--offline", "--release"], child_env=compiler_env)
            missing("python-compat-3.11-and-3.13-linux", "Requires each supported Linux interpreter; current Python alone is not the CI matrix")
            missing("wheel-smoke-linux", "Hosted wheel install strips packaging tools; requires a disposable locked environment, not the shared local interpreter")
            missing("linux-security-scans", "pip-audit/gitleaks hosted tool versions and online vulnerability database not provisioned; no automatic installation/network call")
            missing("desktop-vnext-and-green-donor", "Frozen Avalonia donor qualification requires .NET10 and isolated staged worker bundle; no daily Green reuse")
            missing("desktop-fast-runtime-probes", "Requires a fresh lock-bound staged candidate; existing recovery materials must not be used")
            missing("desktop-build-nsis", "Requires a fresh lock-bound staged candidate and installed offline NSIS dependencies; frontend/Core builds alone do not qualify it")
            missing("installer-lifecycle", "Manual acceptance candidate and user confirmation required before actual install/uninstall/native windows")
        report["source_after"] = source_snapshot(ROOT)
        consistent = report["source_before"] == report["source_after"]
        report["source_consistent"] = consistent
        if not consistent:
            for item in report["checks"]:
                if item["status"] == "LOCAL_PASS":
                    item["status"] = "INVALIDATED"
        states = {item["status"] for item in report["checks"]}
        report["status"] = "INVALIDATED" if not consistent else "FAIL" if "FAIL" in states else "PARTIAL" if "NOT_RUN" in states else "LOCAL_PASS"
        return 0 if report["status"] == "LOCAL_PASS" else 3 if not consistent else 1
    finally:
        report["ended_at"] = now()
        save()
        lock.unlink()
        print(f"[local-ci] receipt={destination}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
