"""Run constrained Cargo fetches, offline checks or tests under storage review.

Invoke only inside a fresh ``dev.py`` run. Estimates are review projections,
not hard quotas or permission to delete existing artifacts.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

from scripts.release import tauri_portable_candidate as portable
from scripts.runtime import dev, storage_report


REPO = Path(__file__).resolve().parents[2]
INTEGRATION_CASES = frozenset({
    "archeaxis-domain:provider_learning",
    "archeaxis-domain:provider_question",
    "archeaxis-domain:openmaic_scene_persistence",
    "archeaxis-domain:template_lifecycle",
    "archeaxis-domain:portable_document",
    "archeaxis-domain:course_candidate",
    "archeaxis-domain:ingest_batches",
    "archeaxis-api:provider_learning_api",
    "archeaxis-api:deeptutor_practice_import",
    "archeaxis-api:openmaic_scene_runtime",
    "archeaxis-api:launch_auth",
    "archeaxis-api:openmaic_capabilities",
    "archeaxis-api:openmaic_configuration_plans",
    "archeaxis-application:openmaic_node",
    "archeaxis-archive:provider_learning_archive",
    "archeaxis-archive:template_lifecycle_archive",
    "archeaxis-store-sqlite:writer",
    "archeaxis-store-sqlite:teaching_schema12",
})
LIB_CASES = {
    "archeaxis-application:lib-deeptutor-import-cancel": (
        "archeaxis-application", "executor::deeptutor_practice_import::tests::cancellation_wins_before_dispatch_or_before_commit"),
    "archeaxis-application:lib-deeptutor-import-runner": (
        "archeaxis-application", "executor::deeptutor_practice_import::tests::private_protocol_requires_an_explicit_worker_and_bounded_frame"),
    "archeaxis-application:lib-openmaic-persistence-generation": (
        "archeaxis-application", "executor::derived::withdrawal_tests::openmaic_persistence_rejects_a_withdrawn_generation"),
    "archeaxis-application:lib-openmaic-persistence-disconnect": (
        "archeaxis-application", "executor::derived::withdrawal_tests::openmaic_queued_persistence_holds_admission_after_caller_disconnects"),
    "archeaxis-application:lib-openmaic-withdrawal": (
        "archeaxis-application", "executor::derived::withdrawal_tests::node_disable_then_reenable_does_not_revive_queued_work"),
    "archeaxis-application:lib-openmaic-receipt": (
        "archeaxis-application", "executor::derived::openmaic_receipt_tests::candidate_receipt_must_bind_input_version_identity_and_content"),
    "archeaxis-application:lib-openmaic-null": (
        "archeaxis-application", "executor::derived::openmaic_receipt_tests::upstream_null_is_preserved_as_a_failure_not_a_candidate"),
    "archeaxis-api:lib-openmaic-launch": (
        "archeaxis-api", "launch::tests::optional_openmaic_node_never_guesses_paths_or_blocks_old_launch_shape"),
}
CASES = INTEGRATION_CASES | frozenset(LIB_CASES)
CRATES_IO_SOURCE = "registry+https://github.com/rust-lang/crates.io-index"
CRATES_IO_CACHE = "index.crates.io-1949cf8c6b5b557f"
WINDOWS_TARGET = "x86_64-pc-windows-msvc"
FETCH_TIMEOUT_SECONDS = 1800
FETCH_TERMINATE_WAIT_SECONDS = 10


class CargoTestFailure(Exception):
    def __init__(self, case: str, exit_code: int, mode: str = "test"):
        self.case = case
        self.exit_code = exit_code
        super().__init__(f"Cargo {mode} {case} exited {exit_code}")


class CargoCoverageFailure(Exception):
    pass


class CargoFetchTimeout(Exception):
    pass


def _owned_run() -> dict:
    raw_run = os.environ.get("ARCHEAXIS_RUN_ROOT", "")
    if not raw_run:
        raise ValueError("a fresh dev.py run is required")
    run = dev.safe_path(Path(raw_run))
    paths = dev.layout(REPO, run.name)
    if (run != paths["run"] or not paths["artifacts"].is_dir()
            or os.environ.get("ARCHEAXIS_WORKTREE_ROOT") != str(REPO)):
        raise ValueError("foreign Cargo test run")
    meta = json.loads(dev.safe_path(run / "run-metadata.json").read_bytes())
    _, patch = dev.worktree_identity(REPO)
    if (meta.get("schema") != "aaos.run-retention/v1" or meta.get("run_id") != run.name
            or meta.get("worktree_root") != str(REPO)
            or meta.get("source_commit") != dev.git(REPO, "rev-parse", "HEAD")
            or meta.get("source_patch_sha256") != patch):
        raise ValueError("run source identity differs from current worktree")
    return paths


def _alternative_review(current: dict, baseline: dict, name: str, total: int) -> dict:
    """Conservatively allow the whole estimate in another possible output class."""
    projection = copy.deepcopy(current)
    projection["readable_bytes"] += total
    rows = [row for row in projection["dev_root"] if row["name"] == name]
    if len(rows) > 1:
        raise ValueError("duplicate projected storage class")
    if not rows:
        projection["dev_root"].append({"name": name, "bytes": 0,
            "budget_gb": storage_report.DEV_BUDGET_GB.get(name.rstrip("/")), "over_budget": False})
        rows = [projection["dev_root"][-1]]
    row = rows[0]
    row["bytes"] += total
    row["budgeted_bytes"] = row["bytes"]
    budget = row.get("budget_gb")
    row["over_budget"] = row["total_over_budget"] = bool(budget and row["bytes"] > budget * 1024 ** 3)
    row["gb"] = round(row["bytes"] / 1024 ** 3, 2)
    return storage_report.growth_review(projection, baseline)


def _command_processor() -> Path:
    if os.name != "nt":
        raise ValueError("the fixed Cargo test runner requires Windows")
    return dev.safe_path(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe")


def _require_target_coverage(current: dict, storage_class: str, target: Path) -> None:
    """Reject skipped or redirected paths within an exact Cargo-owned tree."""
    rows = [row for row in current["dev_root"] if row["name"] == storage_class]
    if len(rows) != 1:
        raise ValueError("Cargo class has no complete target measurement")
    row = rows[0]
    for field in ("errors", "excluded_private", "links"):
        if not isinstance(row.get(field), list):
            raise ValueError("Cargo class lacks coverage details")
        for item in row[field]:
            if field != "excluded_private" and not isinstance(item, dict):
                raise ValueError("Cargo class has invalid coverage details")
            raw = item if field == "excluded_private" else item.get("link" if field == "links" else "path")
            if not isinstance(raw, str) or not Path(raw).is_absolute():
                raise ValueError("Cargo class has invalid coverage details")
            path = Path(os.path.abspath(raw))
            if path == target or path.is_relative_to(target) or target.is_relative_to(path):
                raise ValueError("Cargo target has skipped, private or redirected paths")


def _present(path: Path) -> bool:
    """Check existence, including broken links, without opening the named file."""
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _config_ancestors(cwd: Path) -> tuple[Path, ...]:
    return (cwd, *cwd.parents)


def _fetch_inputs(cargo_home: Path, cwd: Path) -> str:
    """Fail closed on alternative sources, credentials and ambient Cargo config."""
    for name in ("config", "config.toml", "credentials", "credentials.toml"):
        path = dev.safe_path(cargo_home / name)
        if _present(path):
            raise ValueError("Cargo fetch requires a credential-free, unconfigured project Cargo home")
    # Cargo discovers configuration from its cwd and ancestors, not from the
    # --manifest-path. Permit only this repository's known build-target setting.
    expected = {"build": {"target-dir": ".project-local/build/cargo"}}
    for directory in _config_ancestors(cwd):
        config_dir = dev.safe_path(directory / ".cargo")
        for name in ("config", "config.toml"):
            path = dev.safe_path(config_dir / name)
            if not _present(path):
                continue
            if (directory != REPO or name != "config.toml"
                    or tomllib.loads(path.read_text(encoding="utf-8")) != expected):
                raise ValueError("Cargo fetch refuses an unapproved ancestor configuration")
    registry_config = dev.safe_path(cargo_home / "registry/index" / CRATES_IO_CACHE / "config.json")
    if _present(registry_config):
        config = json.loads(registry_config.read_text(encoding="utf-8"))
        if config != {"dl": "https://static.crates.io/crates", "api": "https://crates.io"}:
            raise ValueError("Cargo fetch refuses a non-official registry download configuration")

    lock_path = dev.safe_path(REPO / "Cargo.lock")
    lock_bytes = lock_path.read_bytes()
    lock = tomllib.loads(lock_bytes.decode("utf-8"))
    packages = lock.get("package")
    if not isinstance(packages, list) or not packages:
        raise ValueError("Cargo fetch requires a populated lockfile")
    locked_names = set()
    for package in packages:
        if not isinstance(package, dict) or not isinstance(package.get("name"), str):
            raise ValueError("Cargo fetch encountered an invalid lockfile package")
        source = package.get("source")
        checksum = package.get("checksum", "")
        if source is not None and (source != CRATES_IO_SOURCE or not isinstance(checksum, str)
                                   or len(checksum) != 64
                                   or any(c not in "0123456789abcdef" for c in checksum)):
            raise ValueError("Cargo fetch accepts only checksummed crates.io lockfile sources")
        if source == CRATES_IO_SOURCE:
            locked_names.add(package["name"])
    if not locked_names:
        raise ValueError("Cargo fetch requires locked crates.io dependencies")

    root_manifest = dev.safe_path(REPO / "Cargo.toml")
    root = tomllib.loads(root_manifest.read_text(encoding="utf-8"))
    workspace = root.get("workspace", {})
    members = workspace.get("members", [])
    workspace_dependencies = workspace.get("dependencies", {})
    if not isinstance(members, list) or not members:
        raise ValueError("Cargo fetch requires explicit workspace members")
    if not isinstance(workspace_dependencies, dict):
        raise ValueError("Cargo fetch encountered invalid workspace dependencies")
    manifests = [root_manifest]
    for member in members:
        if (not isinstance(member, str) or not member or any(c in member for c in "*?[]")
                or Path(member).is_absolute()):
            raise ValueError("Cargo fetch requires fixed project workspace members")
        manifest = dev.safe_path(REPO / member / "Cargo.toml")
        if not manifest.is_relative_to(REPO):
            raise ValueError("Cargo fetch workspace member escapes the repository")
        manifests.append(manifest)
    checked = set()
    while manifests:
        manifest = manifests.pop()
        if manifest in checked:
            continue
        checked.add(manifest)
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
        if "patch" in document or "replace" in document:
            raise ValueError("Cargo fetch refuses patched or replaced sources")
        tables = [document, document.get("workspace", {})]
        targets = document.get("target", {})
        if isinstance(targets, dict):
            tables.extend(targets.values())
        for table in tables:
            if not isinstance(table, dict):
                raise ValueError("Cargo fetch encountered an invalid manifest")
            for key in ("dependencies", "dev-dependencies", "build-dependencies"):
                dependencies = table.get(key, {})
                if not isinstance(dependencies, dict):
                    raise ValueError("Cargo fetch encountered invalid dependencies")
                for dependency_name, specification in dependencies.items():
                    if isinstance(specification, str):
                        if dependency_name not in locked_names:
                            raise ValueError("Cargo fetch refuses an unlocked registry dependency")
                        continue
                    if not isinstance(specification, dict):
                        raise ValueError("Cargo fetch encountered invalid dependency details")
                    if specification.get("workspace") is True:
                        specification = workspace_dependencies.get(dependency_name)
                        if isinstance(specification, str):
                            if dependency_name not in locked_names:
                                raise ValueError("Cargo fetch refuses an unlocked registry dependency")
                            continue
                        if not isinstance(specification, dict):
                            raise ValueError("Cargo fetch requires a declared workspace dependency")
                    if any(key in specification for key in ("git", "registry", "registry-index")):
                        raise ValueError("Cargo fetch refuses non-crates.io dependency sources")
                    if "path" in specification:
                        value = specification["path"]
                        if not isinstance(value, str) or Path(value).is_absolute():
                            raise ValueError("Cargo fetch refuses an external path dependency")
                        dependency = dev.safe_path(manifest.parent / value / "Cargo.toml")
                        if not dependency.is_relative_to(REPO):
                            raise ValueError("Cargo fetch refuses an external path dependency")
                        manifests.append(dependency)
                    elif specification.get("package", dependency_name) not in locked_names:
                        raise ValueError("Cargo fetch refuses an unlocked registry dependency")
    return hashlib.sha256(lock_bytes).hexdigest()


def _fetch_executable() -> Path:
    """Use the actual executable inside the registered read-only toolchain, not a rustup proxy."""
    index = json.loads(dev.safe_path(REPO / "config/environment/external-resources-index.json").read_bytes())
    matches = [row for row in index.get("entries", []) if row.get("resource_id") == "ext.toolchains.rust"]
    if len(matches) != 1 or not isinstance(index.get("external_root"), str):
        raise ValueError("registered Rust toolchain is unavailable")
    root = dev.safe_path(Path(index["external_root"]))
    registered = dev.safe_path(root / "toolchains/rust/cargo/bin/rustc.exe")
    if Path(matches[0].get("resolved_absolute", "")) != registered or not registered.is_file():
        raise ValueError("registered Rust toolchain identity differs")
    cargo = dev.safe_path(root / "toolchains/rust/rustup/toolchains/stable-x86_64-pc-windows-msvc/bin/cargo.exe")
    if not cargo.is_file() or not dev.safe_path(cargo.parent / "rustc.exe").is_file():
        raise ValueError("registered stable Windows Cargo executable is unavailable")
    return cargo


def _fetch_environment(cargo: Path, cargo_home: Path, target: Path, run: Path) -> tuple[dict, Path]:
    """Whitelist child variables; no inherited Cargo, proxy, provider or credential environment."""
    system = dev.safe_path(Path(os.environ["SystemRoot"]))
    temporary = dev.safe_path(run / "tmp")
    home = dev.safe_path(temporary / "cargo-fetch-home")
    if not temporary.is_dir() or _present(home):
        raise ValueError("Cargo fetch requires a fresh run-local home and temporary directory")
    env = {"SystemRoot": str(system), "WINDIR": str(system),
           "PATH": os.pathsep.join((str(cargo.parent), str(system / "System32"))),
           "HOME": str(home), "USERPROFILE": str(home), "APPDATA": str(home), "LOCALAPPDATA": str(home),
           "TMP": str(temporary), "TEMP": str(temporary), "TMPDIR": str(temporary),
           "CARGO_HOME": str(cargo_home), "CARGO_TARGET_DIR": str(target),
           "CARGO_REGISTRIES_CRATES_IO_PROTOCOL": "sparse"}
    return env, home


def _fetch_child(command: list[str], *, cwd: Path, env: dict) -> dict:
    """Bound the fixed fetch and retain its actual exit or termination status."""
    child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        return {"exit_code": child.wait(timeout=FETCH_TIMEOUT_SECONDS), "timed_out": False}
    except subprocess.TimeoutExpired:
        try:
            status = child.poll()
        except OSError:
            status = None
        if status is None:
            try:
                child.terminate()
            except OSError:
                pass
            try:
                status = child.wait(timeout=FETCH_TERMINATE_WAIT_SECONDS)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    child.kill()
                except OSError:
                    pass
                try:
                    status = child.wait(timeout=FETCH_TERMINATE_WAIT_SECONDS)
                except (subprocess.TimeoutExpired, OSError):
                    try:
                        status = child.poll()
                    except OSError:
                        status = None
        return {"exit_code": status, "timed_out": True, "timeout_seconds": FETCH_TIMEOUT_SECONDS,
                "termination_confirmed": status is not None}


def _test_coverage(output: str, *, exact: bool) -> dict:
    """Reject a successful Cargo process that executed no selected Rust tests."""
    plain = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    summaries = re.findall(r"^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;",
                           plain, flags=re.MULTILINE)
    if len(summaries) != 1:
        raise CargoCoverageFailure("Rust test output lacks one verifiable test summary")
    status, passed, failed, ignored = summaries[0]
    counts = {"tests_passed": int(passed), "tests_failed": int(failed), "tests_ignored": int(ignored)}
    if (status != "ok" or counts["tests_passed"] < 1 or counts["tests_failed"] != 0
            or (exact and (counts["tests_passed"] != 1 or counts["tests_ignored"] != 0))):
        raise CargoCoverageFailure("Rust test command did not execute the required selected tests")
    return counts


def _qualification(mode: str, cases: list[str]) -> str:
    if mode == "fetch":
        return "DEPENDENCY_FETCH_ONLY_NO_BUILD_OR_TEST"
    if mode == "check":
        if cases and all(case in LIB_CASES for case in cases):
            return "LIBRARY_CHECK_ONLY_NO_UNIT_TEST_CODE"
        return "COMPILE_CHECK_ONLY_NO_TEST_EXECUTION"
    return "TEST_COMMAND_EXECUTION"


def run(cases: list[str], estimate: int, estimate_basis: str, context: dict, *, mode: str = "test") -> list[dict]:
    if mode not in {"fetch", "check", "test"}:
        raise ValueError("Cargo mode must be fetch, check or test")
    if mode == "fetch" and cases:
        raise ValueError("Cargo fetch does not accept test cases")
    if mode != "fetch" and (not cases or len(cases) != len(set(cases)) or any(case not in CASES for case in cases)):
        raise ValueError("Cargo test case is not in the finite allowlist")
    if type(estimate) is not int or estimate <= 0:
        raise ValueError("Cargo generation requires an explicit positive byte estimate")
    if (not isinstance(estimate_basis, str) or not estimate_basis.strip() or len(estimate_basis) > 2000
            or estimate_basis.strip().casefold() in {"unknown", "unknown output"}
            or "\n" in estimate_basis or "\r" in estimate_basis):
        raise ValueError("Cargo generation estimate requires a bounded evidence basis")
    paths = context["paths"]
    canonical = dev.layout(REPO, paths["run"].name)
    if any(paths[key] != canonical[key] for key in ("root", "run", "artifacts", "cargo_build", "cache")):
        raise ValueError("foreign Cargo target or dependency cache")
    target = dev.safe_path(paths["cargo_build"])
    if not target.is_dir():
        raise ValueError("canonical shared Cargo target is unavailable")
    cargo_home = dev.safe_path(paths["cache"] / "cargo")
    if not dev.safe_path(cargo_home / "registry").is_dir():
        raise ValueError("canonical offline Cargo registry is unavailable")
    if mode == "fetch":
        cargo = _fetch_executable()
        lock_sha256 = _fetch_inputs(cargo_home, paths["run"])
        env, fetch_home = _fetch_environment(cargo, cargo_home, target, paths["run"])
    else:
        command_processor = _command_processor()
        # Use a fixed relative command under the fixed repository cwd; this avoids
        # cmd.exe quoting ambiguity when the repository path contains spaces.
        dev.safe_path(REPO / "scripts/ci/cargo_test.bat")
        runner = "scripts\\ci\\cargo_test.bat"
        env = dict(os.environ)
        env.update({"CARGO_TARGET_DIR": str(target), "ARCHEAXIS_CARGO_TARGET_DIR": str(target),
                    "CARGO_HOME": str(cargo_home), "ARCHEAXIS_CARGO_HOME": str(cargo_home),
                    "CARGO_INCREMENTAL": "0"})
    state = portable._storage_pre(target, estimate, context, formal_cargo=True)
    state["producer"] = "cargo-test-growth/v1"
    state["estimate_basis"] = estimate_basis
    state["projection_scope"] = ("caller-estimated generated bytes, independently projected into build/, runs/ and "
                                 "cache/ as conservative alternatives; not a hard quota")
    state["test_cases"] = cases
    state["command_mode"] = mode
    state["qualification"] = _qualification(mode, cases)
    if mode == "fetch":
        state["cargo_lock_sha256"] = lock_sha256
        state["fetch_target"] = WINDOWS_TARGET
        state["fetch_scope"] = ("official crates.io locked dependencies; no operating-system network sandbox; "
                                "timeout termination is limited to the direct child")
    state["child_results"] = []
    try:
        pre_path = dev.safe_path(REPO / state["pre"]["path"])
        raw, identity = portable._identity(pre_path)
        if any(identity[key] != state["pre"][key] for key in ("path", "bytes", "sha256")):
            raise ValueError("Cargo pre-measurement identity changed")
        current = portable._footprint(json.loads(raw))
        _require_target_coverage(current, "build/", target)
        _require_target_coverage(current, "cache/", cargo_home)
        alternatives = {name: _alternative_review(current, state["baseline_report"], name, estimate)
                        for name in ("runs/", "cache/")}
        state["alternative_projected_reviews"] = alternatives
        reviews = [state["pre_review"], state["projected_review"], *alternatives.values()]
        if any(review["status"] == "REVIEW_REQUIRED" for review in reviews):
            raise portable.GrowthReviewRequiredError("Cargo storage growth requires review before execution")
        if mode == "fetch":
            if _fetch_inputs(cargo_home, paths["run"]) != lock_sha256:
                raise ValueError("Cargo fetch inputs changed during preflight")
            fetch_home.mkdir(exist_ok=False)
            state["copy_outcome"] = "STARTED"
            command = [str(cargo), "fetch", "--locked", "--target", WINDOWS_TARGET,
                       "--manifest-path", str(REPO / "Cargo.toml")]
            completed = _fetch_child(command, cwd=paths["run"], env=env)
            state["child_results"].append({"case": "workspace", **completed})
            if completed["timed_out"]:
                state["copy_outcome"] = "TIMED_OUT"
                raise CargoFetchTimeout(f"Cargo fetch exceeded {FETCH_TIMEOUT_SECONDS} seconds")
            if completed["exit_code"] != 0:
                state["copy_outcome"] = "CHILD_FAILED"
                raise CargoTestFailure("workspace", completed["exit_code"], mode)
            if hashlib.sha256(dev.safe_path(REPO / "Cargo.lock").read_bytes()).hexdigest() != lock_sha256:
                state["copy_outcome"] = "INTEGRITY_FAILED"
                raise ValueError("Cargo.lock changed during the fetch")
        else:
            state["copy_outcome"] = "STARTED"
        for case in cases:
            library = case in LIB_CASES
            if library:
                package, test = LIB_CASES[case]
                selection = ["-p", package, "--lib"]
                if mode == "test":
                    selection.extend([test, "--", "--exact"])
            else:
                package, test = case.split(":", 1)
                selection = ["-p", package, "--test", test]
            command = [str(command_processor), "/d", "/c", runner, mode, "--offline", "--locked", *selection]
            options = {"cwd": REPO, "env": env, "stdin": subprocess.DEVNULL,
                       "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0), "check": False}
            if mode == "test":
                options.update({"stdout": subprocess.PIPE, "text": True, "encoding": "utf-8", "errors": "replace"})
            completed = subprocess.run(command, **options)
            output = getattr(completed, "stdout", "") or ""
            if output:
                sys.stdout.write(output)
                sys.stdout.flush()
            row = {"case": case, "exit_code": completed.returncode}
            if library and mode == "check":
                row["qualification"] = "LIBRARY_CHECK_ONLY_NO_UNIT_TEST_CODE"
            state["child_results"].append(row)
            if completed.returncode != 0:
                state["copy_outcome"] = "CHILD_FAILED"
                raise CargoTestFailure(case, completed.returncode, mode)
            if mode == "test":
                try:
                    row.update(_test_coverage(output, exact=library))
                except CargoCoverageFailure:
                    state["copy_outcome"] = "TEST_RESULT_UNVERIFIED"
                    raise
        state["copy_outcome"] = "PRODUCER_COMPLETED"
        return state["child_results"]
    finally:
        portable._storage_post(state, sys.exc_info()[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fetch", "check", "test"), default="test",
                        help="fetch downloads locked dependencies; check compiles; test executes selected tests")
    parser.add_argument("--case", action="append", default=[], choices=sorted(CASES))
    parser.add_argument("--storage-generated-bytes", type=int, required=True)
    parser.add_argument("--estimate-basis", required=True)
    parser.add_argument("--storage-purpose", required=True)
    parser.add_argument("--storage-sharing", required=True)
    parser.add_argument("--storage-retention-reason", required=True)
    args = parser.parse_args()
    if args.mode == "fetch" and args.case:
        parser.error("fetch does not accept test cases")
    if args.mode != "fetch" and not args.case:
        parser.error("check and test require an allowlisted case")
    try:
        paths = _owned_run()
        context = {"paths": paths, "purpose": args.storage_purpose, "sharing": args.storage_sharing,
                   "retention_reason": args.storage_retention_reason}
        results = run(args.case, args.storage_generated_bytes, args.estimate_basis, context, mode=args.mode)
        qualification = _qualification(args.mode, args.case)
        print(json.dumps({"schema": "cargo-test-growth/v1", "mode": args.mode,
                          "qualification": qualification, "results": results}))
        return 0
    except CargoTestFailure as error:
        print(str(error), file=sys.stderr)
        return error.exit_code if 0 < error.exit_code < 256 else 1
    except CargoFetchTimeout as error:
        print(str(error), file=sys.stderr)
        return 124
    except CargoCoverageFailure as error:
        print(str(error), file=sys.stderr)
        return 2
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
