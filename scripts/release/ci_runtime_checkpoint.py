"""Initialize one isolated CI job's fixed runtime checkpoint; never roll local baselines.

CI environment variables declare a context, not a cryptographic runner attestation.
Only a clean primary checkout with one newly allocated run can initialize it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from scripts.runtime import dev, storage_report

SCHEMA = "aaos.ci-runtime-checkpoint/v1"
NAME = "ci-runtime-checkpoint.json"
CLAIM = "ci-runtime-initialization.json"
SEAL = "ci-runtime-seal.json"
EXPORT = ["export", "--quiet", "--frozen", "--no-dev", "--no-emit-project", "--no-editable", "--no-header",
          "--format", "requirements-txt"]
PYTHON_INFO = """import importlib.metadata,json,platform,sys,sysconfig
print(json.dumps({'version':list(sys.version_info[:3]),'base':sys.base_prefix,
 'architecture':platform.machine(),'platform':sys.platform,
 'purelib':sysconfig.get_path('purelib'),
 'distributions':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())}))
"""


def _safe(path):
    path = dev.safe_path(path)
    for part in (*reversed(path.parents), path):
        try:
            info = Path(storage_report.io_path(part)).lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked CI input/evidence path rejected")
    return path


def _bytes(path, *, hardlinks=False):
    path = _safe(path)
    native = Path(storage_report.io_path(path))
    info = native.stat()
    if not stat.S_ISREG(info.st_mode) or (not hardlinks and info.st_nlink != 1):
        raise ValueError("CI evidence/source must be a regular independent file")
    digest = hashlib.sha256()
    remaining = info.st_size
    with native.open("rb") as stream:
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError("CI input shortened while measuring")
            digest.update(chunk)
            remaining -= len(chunk)
        if stream.read(1):
            raise ValueError("CI input grew while measuring")
    return {"bytes": info.st_size, "sha256": digest.hexdigest()}


def _tree(root):
    root = _safe(root)
    result = {}
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(storage_report.io_path(root), followlinks=False, onerror=fail):
        directory = Path(storage_report.display_path(directory))
        for name in dirs:
            _safe(Path(directory) / name)
        for name in files:
            path = Path(directory) / name
            result[path.relative_to(root).as_posix()] = _bytes(path, hardlinks=True)
    if not result:
        raise ValueError("CI installed environment is empty")
    return result


def _write(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    with dev.safe_path(path).open("xb") as stream:
        stream.write(raw)
    return {"path": str(path), **_bytes(path)}


def _read(identity):
    path = dev.safe_path(Path(identity["path"]))
    if _bytes(path) != {key: identity[key] for key in ("bytes", "sha256")}:
        raise ValueError("CI checkpoint raw byte identity changed")
    return json.loads(path.read_bytes())


def _context(repo, paths):
    repo = dev.safe_path(repo)
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("GITHUB_REPOSITORY") != "DTALEX66/ArcheAxis-Knowledge-OS"):
        raise ValueError("CI initialization requires the explicit hosted-job context")
    if dev.safe_path(Path(os.environ.get("GITHUB_WORKSPACE", ""))) != repo:
        raise ValueError("CI workspace differs from the exact checkout")
    if (not (repo / ".git").is_dir()
            or Path(dev.git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")) != repo / ".git"
            or dev.git(repo, "worktree", "list", "--porcelain").count("worktree ") != 1):
        raise ValueError("CI requires a primary isolated checkout, never a linked owner")
    dirty, patch = dev.worktree_identity(repo)
    head = dev.git(repo, "rev-parse", "HEAD")
    if dirty or os.environ.get("GITHUB_SHA") != head:
        raise ValueError("CI initialization requires clean exact-job source")
    canonical = dev.layout(repo, paths["run"].name)
    if any(paths[key] != canonical[key] for key in ("root", "run", "artifacts")):
        raise ValueError("CI checkpoint has a foreign canonical run")
    if (dev.safe_path(Path(os.environ.get("ARCHEAXIS_RUN_ROOT", ""))) != paths["run"]
            or dev.safe_path(Path(os.environ.get("ARCHEAXIS_WORKTREE_ROOT", ""))) != repo):
        raise ValueError("CI run environment differs from allocated ownership")
    metadata = paths["run"] / "run-metadata.json"
    _bytes(metadata)
    value = json.loads(metadata.read_bytes())
    if (value.get("schema") != "aaos.run-retention/v1" or value.get("worktree_root") != str(repo)
            or value.get("run_id") != paths["run"].name or value.get("source_commit") != head
            or value.get("source_patch_sha256") != patch):
        raise ValueError("CI run was not allocated against this clean source")
    job = {key: os.environ.get(key, "") for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB")}
    if (not re.fullmatch(r"[0-9]+", job["GITHUB_RUN_ID"])
            or not re.fullmatch(r"[1-9][0-9]*", job["GITHUB_RUN_ATTEMPT"])
            or not re.fullmatch(r"[A-Za-z0-9_-]+", job["GITHUB_JOB"])):
        raise ValueError("CI job identity is missing")
    runner_temp = dev.safe_path(Path(os.environ.get("RUNNER_TEMP", "")))
    env_file = dev.safe_path(Path(os.environ.get("GITHUB_ENV", "")))
    if runner_temp.is_relative_to(repo) or not env_file.is_relative_to(runner_temp):
        raise ValueError("CI runner command file must be outside the checkout")
    info = env_file.stat()  # Do not read or print its environment contents.
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("CI runner command file must be independent and regular")
    return {"repository": str(repo), "run": str(paths["run"]), "source_commit": head,
            "source_tree": dev.git(repo, "rev-parse", "HEAD^{tree}"), "source_patch_sha256": patch,
            "job": job, "lock": _bytes(repo / "uv.lock"), "pyproject": _bytes(repo / "pyproject.toml")}


def _interpreter():
    import platform
    if sys.version_info[:2] != (3, 12):
        raise ValueError("CI runtime forecast requires the producer Python 3.12")
    # This is the same narrowly allowed implicit interpreter-root binding.
    return {"version": list(sys.version_info[:3]), "base": str(dev.safe_path(Path(sys.base_prefix).resolve(strict=True))),
            "architecture": platform.machine(), "platform": sys.platform}


def _installed(repo, paths):
    root = dev.safe_path(Path(os.environ.get("UV_PROJECT_ENVIRONMENT", "")))
    if root != paths["build"] / "venv":
        raise ValueError("CI forecast must use this job's canonical uv sync environment")
    python = dev.safe_path(root / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    _bytes(python, hardlinks=True)
    uv = shutil.which("uv")
    if uv is None:
        raise ValueError("uv is required to verify the installed forecast")
    # No resolver mutation, installation, Python download or network fallback.
    check = [uv, "sync", "--frozen", "--check", "--offline", "--no-python-downloads",
             "--no-install-project", "--python", sys.executable]
    subprocess.run(check, cwd=repo, check=True, capture_output=True)
    done = subprocess.run([str(python), "-I", "-B", "-c", PYTHON_INFO], cwd=repo,
                          check=True, capture_output=True, text=True, encoding="utf-8")
    installed = json.loads(done.stdout)
    identity = _interpreter()
    physical = str(dev.safe_path(Path(installed["base"]).resolve(strict=True)))
    if {**{key: installed[key] for key in identity}, "base": physical} != identity:
        raise ValueError("uv sync environment differs from producer Python/platform")
    purelib = dev.safe_path(Path(installed["purelib"]))
    if not purelib.is_relative_to(root) or not installed["distributions"]:
        raise ValueError("CI installed distribution inventory is missing or foreign")
    if any(os.environ.get(key, "") not in {"", "0", "false"} for key in
           ("UV_COMPILE_BYTECODE", "UV_NO_DEV", "UV_NO_DEFAULT_GROUPS", "UV_NO_INSTALL_PROJECT")):
        raise ValueError("CI dependency/bytecode options differ from the reviewed default sync")
    for key in ("UV_GROUP", "UV_ONLY_GROUP", "UV_EXTRA", "UV_ALL_EXTRAS", "UV_PYTHON_PLATFORM", "UV_NO_GROUP",
                "UV_NO_EXTRA", "UV_ONLY_DEV", "UV_ALL_GROUPS", "UV_PACKAGE", "UV_ALL_PACKAGES", "UV_PROJECT",
                "UV_WORKING_DIR", "UV_CONFIG_FILE", "UV_NO_SOURCES", "UV_NO_EMIT_PACKAGE",
                "UV_NO_EMIT_LOCAL", "UV_NO_EMIT_WORKSPACE"):
        if os.environ.get(key):
            raise ValueError("CI dependency selection override is unsupported")
    return root, installed, identity


def _glob(parts, pattern):
    """Match declared package-data globs, including ** with zero directories."""
    if not pattern:
        return not parts
    if pattern[0] == "**":
        return any(_glob(parts[index:], pattern[1:]) for index in range(len(parts) + 1))
    return bool(parts and fnmatchcase(parts[0], pattern[0]) and _glob(parts[1:], pattern[1:]))


def wheel_inputs(repo):
    """Read the supported setuptools declaration; unrelated archives are not wheels."""
    project = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    setup = project.get("tool", {}).get("setuptools", {})
    finder = setup.get("packages", {}).get("find", {})
    if (project.get("build-system", {}).get("build-backend") != "setuptools.build_meta"
            or project.get("build-system", {}).get("requires") != ["setuptools==83.0.0"]
            or set(setup) - {"packages", "package-data"}
            or set(setup.get("packages", {})) != {"find"}
            or set(finder) - {"include", "exclude", "namespaces", "where"}
            or finder.get("namespaces") is not True or finder.get("where", ["."]) != ["."]
            or project["project"].get("dynamic")):
        raise ValueError("unsupported wheel input declaration; review the forecast adapter")
    include, exclude = finder.get("include"), finder.get("exclude", [])
    data = setup.get("package-data", {})
    if (not isinstance(include, list) or not include or not isinstance(exclude, list)
            or any(not isinstance(value, str) or not value or "/" in value or "\\" in value
                   for value in include + exclude)
            or not isinstance(data, dict)):
        raise ValueError("invalid setuptools package selection")
    tracked = set(filter(None, dev.git(repo, "ls-files", "-z").split("\0")))
    if tracked & {"MANIFEST.in", "setup.py", "setup.cfg"}:
        raise ValueError("additional wheel input mechanism requires explicit forecast support")
    packages = {}
    for name in tracked:
        for directory in PurePosixPath(name).parents:
            if directory == PurePosixPath(".") or not all(part.isidentifier() for part in directory.parts):
                continue
            package = ".".join(directory.parts)
            ancestors = [".".join(directory.parts[:index]) for index in range(1, len(directory.parts) + 1)]
            if (any(fnmatchcase(package, pattern) for pattern in include)
                    and not any(fnmatchcase(ancestor, pattern) for ancestor in ancestors for pattern in exclude)):
                packages[package] = directory
    selected = {name for name in tracked if str(PurePosixPath(name).parent).replace("/", ".") in packages
                and (PurePosixPath(name).suffix in {".py", ".pyi"} or PurePosixPath(name).name == "py.typed")}
    for package, patterns in data.items():
        if (not isinstance(package, str) or not isinstance(patterns, list)
                or any(not isinstance(pattern, str) or not pattern or "\\" in pattern
                       or PurePosixPath(pattern).is_absolute() or ".." in PurePosixPath(pattern).parts for pattern in patterns)):
            raise ValueError("invalid setuptools package-data declaration")
        for key, directory in packages.items():
            if package not in {key, "*"}:
                continue
            for name in tracked:
                member = PurePosixPath(name)
                if member.is_relative_to(directory) and any(
                        _glob(member.relative_to(directory).parts, PurePosixPath(pattern).parts) for pattern in patterns):
                    selected.add(name)
    metadata = {"pyproject.toml"}
    readme = project["project"].get("readme")
    if isinstance(readme, str):
        metadata.add(readme)
    elif isinstance(readme, dict) and set(readme) <= {"file", "content-type"} and "file" in readme:
        metadata.add(readme["file"])
    elif readme is not None:
        raise ValueError("unsupported project readme input")
    license_value = project["project"].get("license")
    if isinstance(license_value, dict):
        if set(license_value) == {"file"}:
            metadata.add(license_value["file"])
        elif set(license_value) != {"text"}:
            raise ValueError("unsupported project license metadata")
    licenses = project["project"].get("license-files", ["LICEN[CS]E*", "COPYING*", "NOTICE*", "AUTHORS*"])
    if not isinstance(licenses, list) or any(not isinstance(value, str) for value in licenses):
        raise ValueError("unsupported project license input")
    metadata.update(name for name in tracked if any(_glob(PurePosixPath(name).parts, PurePosixPath(pattern).parts)
                                                   for pattern in licenses))
    if not metadata <= tracked or not selected:
        raise ValueError("wheel metadata/package inputs are absent from clean tracked source")
    return {name: _bytes(repo / name) for name in sorted(selected | metadata)}


def _forecast(repo, paths, requirements):
    root, installed, identity = _installed(repo, paths)
    environment = _tree(root)
    source = wheel_inputs(repo)
    installed_bytes = sum(row["bytes"] for row in environment.values())
    source_bytes = sum(row["bytes"] for row in source.values())
    # Observed installed files include scripts/metadata and any development surplus.
    # Three source payload copies represent build/lib, wheel and installed project.
    # This is an evidenced estimate, not an upper bound on setuptools/uv/cache growth.
    total = installed_bytes + 3 * source_bytes + _bytes(requirements)["bytes"]
    if total <= 0:
        raise ValueError("CI forecast is empty")
    return {"schema": "aaos.ci-runtime-forecast/v1", "interpreter": identity,
            "installed_root": str(root), "installed_inventory": installed,
            "environment_files": environment, "tracked_source_files": source,
            "requirements": {"path": str(requirements), **_bytes(requirements)},
            "installed_bytes": installed_bytes, "tracked_source_bytes": source_bytes,
            "source_payload_copies": 3, "generated_bytes": total,
            "scope": "observed complete synced environment plus three selected setuptools package/package-data/public-metadata payload copies for build/lib, wheel and installed project; clean HEAD binds other tracked source without projecting its archives",
            "limitations": "not a hard upper bound: installer metadata, compression, platform/build outputs and shared uv cache may differ; known Core/model/VC inputs are projected separately; post measures actual growth"}


def reserve(repo, paths):
    identity = _context(repo, paths)
    dev_root = paths["dev"]
    if (dev_root / "rt").exists() or (dev_root / "rt").is_symlink():
        raise ValueError("CI runtime already exists; do not reset its baseline")
    runs = dev_root / "runs"
    if list(runs.iterdir()) != [paths["run"].parent] or list(paths["run"].parent.iterdir()) != [paths["run"]]:
        raise ValueError("CI initialization requires one fresh run, not retained local run history")
    claim = dev.safe_path(dev_root / "task-runtime" / CLAIM)
    claim.parent.mkdir(exist_ok=True)
    return _write(claim, {"schema": SCHEMA, "identity": identity,
                          "reserved_at": datetime.now(timezone.utc).isoformat()})


def _seal_baseline(repo, paths, portable):
    # Preserve the full observation before validation; rejected evidence is never
    # an adoptable baseline and never opens another initialization attempt.
    report = portable.storage_report.measure(repo)
    measured = None
    measurement_error = None
    try:
        measured = _write(paths["artifacts"] / "ci-runtime-pre-seal.json", report)
    except Exception as error:
        measurement_error = error
    details = {"schema": "aaos.ci-runtime-seal-review/v1", "status": "REJECTED",
               "measurement": measured,
               **{key: report.get(key) for key in ("measurement_status", "measurement_errors",
                  "excluded_private", "excluded_checkouts", "out_of_layout")}}
    review_path = paths["artifacts"] / "ci-runtime-seal-review.json"
    if measurement_error is not None:
        details["measurement_evidence_error"] = {"type": type(measurement_error).__name__,
                                                 "message": str(measurement_error)}
        details["unsealed_measurement"] = report
    try:
        baseline = portable._footprint(report)
    except Exception as error:
        if measurement_error is not None:
            error.add_note("CI seal raw measurement could not be written: " + str(measurement_error))
        details["validation_error"] = {"type": type(error).__name__, "message": str(error)}
        try:
            _write(review_path, details)
        except Exception as evidence_error:
            error.add_note("CI seal diagnostic could not be written: " + str(evidence_error))
        raise
    review = portable.storage_report.growth_review(baseline)
    details["growth_review"] = review
    details["over_budget_classes"] = [row for row in baseline["dev_root"] if row["over_budget"]]
    rejected = (baseline["measurement_status"] != "PASS" or baseline["out_of_layout"]
                or review["status"] == "REVIEW_REQUIRED")
    details["status"] = "REJECTED" if rejected or measurement_error is not None else "ACCEPTED"
    problem = None
    if rejected:
        summary = {"measurement_status": baseline["measurement_status"],
                   "measurement_errors": len(baseline["measurement_errors"]),
                   "excluded_private": len(baseline["excluded_private"]),
                   "excluded_checkouts": len(baseline["excluded_checkouts"]),
                   "out_of_layout": baseline["out_of_layout"],
                   "over_budget_classes": details["over_budget_classes"]}
        problem = ValueError("CI baseline must have complete clean coverage and remain within existing class budgets; "
                             + json.dumps(summary, ensure_ascii=False) + "; full evidence: " + str(review_path))
    if measurement_error is not None:
        if problem is None:
            problem = measurement_error
        else:
            problem.add_note("CI seal raw measurement could not be written: " + str(measurement_error))
    try:
        _write(review_path, details)
    except Exception as evidence_error:
        if problem is not None:
            problem.add_note("CI seal diagnostic could not be written: " + str(evidence_error))
            raise problem from evidence_error
        raise
    if problem is not None:
        raise problem
    return baseline


def seal(repo, paths):
    from scripts.release import tauri_portable_candidate as portable
    identity = _context(repo, paths)
    claim = dev.safe_path(paths["dev"] / "task-runtime" / CLAIM)
    _bytes(claim)
    reservation = json.loads(claim.read_bytes())
    if reservation.get("schema") != SCHEMA or reservation.get("identity") != identity:
        raise ValueError("CI reservation belongs to another job/run/source")
    if dev.safe_path(paths["dev"] / "rt").exists():
        raise ValueError("CI runtime producer already started")
    reserved_at = datetime.fromisoformat(reservation["reserved_at"])
    # Core's dev.py build owns another exclusive run. Only new clean-source runs
    # created after this job's reservation may precede the one baseline seal.
    if list((paths["dev"] / "runs").iterdir()) != [paths["run"].parent]:
        raise ValueError("CI has a foreign checkout run identity")
    for run in paths["run"].parent.iterdir():
        dev.safe_path(run)
        if run == paths["run"]:
            continue
        metadata = run / "run-metadata.json"
        _bytes(metadata)
        value = json.loads(metadata.read_bytes())
        if (dev.layout(repo, run.name)["run"] != run
                or value.get("worktree_root") != str(repo) or value.get("run_id") != run.name
                or value.get("source_commit") != identity["source_commit"]
                or value.get("source_patch_sha256") != identity["source_patch_sha256"]
                or datetime.fromisoformat(value["created_at"]) < reserved_at):
            raise ValueError("CI cannot adopt a preexisting or foreign build run")
    seal_path = dev.safe_path(paths["dev"] / "task-runtime" / SEAL)
    # Reserve before checks/exports/measurement; even failure cannot roll a baseline.
    with seal_path.open("xb") as output:
        requirements = paths["artifacts"] / "ci-runtime-requirements.txt"
        if requirements.exists():
            raise ValueError("CI requirements evidence already exists")
        uv = shutil.which("uv")
        if uv is None:
            raise ValueError("uv is required for CI initialization")
        subprocess.run([uv, *EXPORT, "--offline", "--no-python-downloads", "--output-file", str(requirements)],
                       cwd=repo, check=True, capture_output=True)
        forecast = _forecast(repo, paths, requirements)
        forecast_id = _write(paths["artifacts"] / "ci-runtime-forecast.json", forecast)
        baseline = _seal_baseline(repo, paths, portable)
        baseline_id = _write(paths["artifacts"] / "ci-runtime-baseline.json", baseline)
        if _context(repo, paths) != identity:
            raise ValueError("CI source changed during initialization")
        descriptor = {"schema": SCHEMA, "identity": identity, "baseline": baseline_id, "forecast": forecast_id}
        descriptor_id = _write(paths["artifacts"] / NAME, descriptor)
        output.write((json.dumps({"schema": SCHEMA, "identity": identity,
                                 "reservation": {"path": str(claim), **_bytes(claim)}, "descriptor": descriptor_id},
                                sort_keys=True, indent=2) + "\n").encode())
    return paths["artifacts"] / NAME


def initialize(repo, paths):
    reserve(repo, paths)
    return seal(repo, paths)


def load(repo, paths, path):
    from scripts.release import tauri_portable_candidate as portable
    identity = _context(repo, paths)
    path = dev.safe_path(path)
    if path != paths["artifacts"] / NAME:
        raise ValueError("CI checkpoint must belong to this exact run")
    seal_path = dev.safe_path(paths["dev"] / "task-runtime" / SEAL)
    _bytes(seal_path)
    sealed = json.loads(seal_path.read_bytes())
    if sealed.get("schema") != SCHEMA or sealed.get("identity") != identity or sealed["descriptor"]["path"] != str(path):
        raise ValueError("CI singleton claim belongs to another job/run/source")
    if sealed["reservation"]["path"] != str(paths["dev"] / "task-runtime" / CLAIM):
        raise ValueError("CI reservation path differs")
    reservation = _read(sealed["reservation"])
    if reservation.get("schema") != SCHEMA or reservation.get("identity") != identity:
        raise ValueError("CI initialization reservation changed")
    descriptor = _read(sealed["descriptor"])
    if descriptor.get("schema") != SCHEMA or descriptor.get("identity") != identity:
        raise ValueError("CI checkpoint belongs to another job/run/source")
    for key, name in (("baseline", "ci-runtime-baseline.json"), ("forecast", "ci-runtime-forecast.json")):
        if descriptor[key]["path"] != str(paths["artifacts"] / name):
            raise ValueError("CI checkpoint evidence is outside its exact run")
    baseline = portable._footprint(_read(descriptor["baseline"]))
    forecast = _read(descriptor["forecast"])
    requirements = paths["artifacts"] / "ci-runtime-requirements.txt"
    if forecast != _forecast(repo, paths, requirements):
        raise ValueError("CI forecast no longer matches actual installed/source inputs")
    return baseline, {"descriptor": sealed["descriptor"], "identity": identity,
                      "forecast": descriptor["forecast"]}, forecast


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    phases = parser.add_mutually_exclusive_group()
    phases.add_argument("--reserve", action="store_true", help="claim the fresh job once, before nested Core build runs")
    phases.add_argument("--seal", action="store_true", help="seal once after prerequisite builds, immediately before runtime generation")
    args = parser.parse_args()
    repo = dev.safe_path(args.repository)
    paths = dev.layout(repo, args.run_id)
    print(reserve(repo, paths) if args.reserve else seal(repo, paths) if args.seal else initialize(repo, paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
