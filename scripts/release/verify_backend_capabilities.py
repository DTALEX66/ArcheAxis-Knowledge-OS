"""Capability readiness of a staged backend runtime, checked before it ships.

A capability route is a promise. `backend_launcher` reads the routes a runtime
declares, the Core registers them, and a job is dispatched to the named worker - so if
the worker or its engine is not actually usable on the target interpreter, the failure
appears later as a failed job with an engine-shaped message, which is where two rounds
of this work were spent. This script turns that into a packaging-time answer.

For every declared route it checks two things against the runtime this profile names:

* **launch** - the worker starts under that interpreter and emits a protocol hello
  advertising exactly the capability being declared. This proves the interpreter runs
  the worker, the shared transport loads, and the declared capability is the one the
  worker actually serves.
* **engine** - the engine the capability needs is present: the Python modules are
  importable by that interpreter, and each external executable resolves through the
  declared capability manifest and answers a version probe.

A route that fails either check is reported by name and the run fails closed. Nothing
here installs anything.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# What each capability needs on the target interpreter. These follow the imports the
# workers actually perform (checked, not assumed): an import name that the worker never
# uses would invent a failure, and a missing one would hide a real one. `model` marks a
# capability that needs a served model this check cannot reach, reported as
# `unverifiable` rather than passed.
REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "archive.inventory": {},
    "canvas.structure": {},
    "html.structure": {},
    "image.caption": {"model": ["ollama vision model"]},
    "image.ocr": {
        # yaml is imported for the optional public OCR profile; without it an explicit
        # profile cannot be read and the declared-path resolver cannot read the
        # capability manifest either.
        "modules": ["yaml"],
        "executables": ["tesseract", "tesseract-languages"],
    },
    "media.probe": {},
    "office.structure": {"modules": ["openpyxl", "pptx", "pymupdf"]},
    "pdf.extract": {"modules": ["pymupdf"]},
    "subtitles.structure": {},
}

TIMEOUT_SECONDS = 120


def manifest_path(staged_root: Path) -> Path:
    """The manifest the staged tree ships; the workers resolve it from their own tree."""
    return staged_root / "config" / "environment" / "capability-requirements.yaml"


def run(argv: list[str], *, staged_root: Path, env: dict[str, str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(staged_root), env=env,
                          timeout=timeout)


def check_launch(worker: Path, capability: str, interpreter: Path, staged_root: Path,
                 env: dict[str, str]) -> dict:
    """Start the worker and require a hello advertising exactly this capability."""
    result: dict = {"worker": str(worker.relative_to(staged_root))}
    if not worker.is_file():
        result.update(ok=False, reason=f"worker script is missing: {worker}")
        return result
    with tempfile.TemporaryDirectory() as staging:
        try:
            done = run([str(interpreter), "-B", str(worker), "--staging-root", staging],
                       staged_root=staged_root, env=env, timeout=TIMEOUT_SECONDS)
        except (OSError, subprocess.SubprocessError) as error:
            result.update(ok=False, reason=f"worker could not be started: {error}")
            return result
    hello = None
    for line in (done.stdout or "").splitlines():
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("type") == "hello":
            hello = parsed
            break
    if hello is None:
        result.update(ok=False, reason="worker did not emit a protocol hello",
                      stderr_tail=(done.stderr or "")[-300:])
        return result
    advertised = hello.get("capabilities") or []
    if capability not in advertised:
        result.update(ok=False, advertised=advertised,
                      reason=f"worker advertises {advertised}, not {capability}")
        return result
    result.update(ok=True, advertised=advertised)
    return result


def check_engine(capability: str, interpreter: Path, staged_root: Path,
                 env: dict[str, str]) -> dict:
    """The engine this capability needs, on the interpreter and the declared paths."""
    needs = REQUIREMENTS.get(capability, {})
    modules = needs.get("modules", [])
    executables = needs.get("executables", [])
    models = needs.get("model", [])
    result: dict = {"ok": True, "modules": {}, "executables": {}}

    if modules:
        script = ";".join(
            f"import {name}" for name in modules
        ) + ";print('ok')"
        done = run([str(interpreter), "-c", script], staged_root=staged_root, env=env,
                   timeout=TIMEOUT_SECONDS)
        ok = done.returncode == 0 and "ok" in (done.stdout or "")
        result["modules"] = {"required": modules, "ok": ok,
                             "error": None if ok else (done.stderr or "").strip()[-300:]}
        result["ok"] = result["ok"] and ok

    if executables:
        # Resolve through the declared manifest, not PATH: the manifest is how a
        # declared engine is found, and PATH is what made a working engine look absent.
        script = (
            "import importlib.util,json\n"
            "spec=importlib.util.spec_from_file_location('tp',"
            + json.dumps(str(staged_root / "workers" / "tool_paths.py")) + ")\n"
            "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\n"
            "out={}\n"
            "for name in " + json.dumps(executables) + ":\n"
            "    try:\n"
            "        out[name]=m.tool_path(name)\n"
            "    except Exception as exc:\n"
            "        out[name]='ERROR: '+type(exc).__name__+': '+str(exc)\n"
            "print(json.dumps(out))\n"
        )
        done = run([str(interpreter), "-c", script], staged_root=staged_root, env=env,
                   timeout=TIMEOUT_SECONDS)
        resolved: dict = {}
        try:
            resolved = json.loads((done.stdout or "").strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            resolved = {name: "ERROR: resolver did not answer" for name in executables}
        for name, value in resolved.items():
            usable = isinstance(value, str) and not value.startswith("ERROR:")
            result["executables"][name] = {"path_or_error": value, "ok": usable}
            result["ok"] = result["ok"] and usable

    if models:
        # A served model cannot be verified by presence alone, so it is reported as
        # unverifiable rather than passed.
        result["unverifiable"] = models

    return result


def verify(staged_root: Path, interpreter: Path | None, manifest: Path | None,
           routes: list[dict]) -> dict:
    staged_root = staged_root.resolve()
    profile_path = staged_root / "worker-profile.json"
    report: dict = {
        "schema": "archeaxis.capability-readiness/v1",
        "staged_root": str(staged_root),
        "install_performed": False,
        "capabilities": [],
    }
    if not profile_path.is_file():
        report.update(ok=False, failure=f"worker profile is missing: {profile_path}")
        return report
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    interpreter = interpreter or Path(profile["python"])
    if not interpreter.is_file():
        report.update(ok=False, failure=f"runtime interpreter is missing: {interpreter}")
        return report
    manifest = manifest or manifest_path(staged_root)

    env = dict(os.environ)
    if manifest.is_file():
        # Pin the worker's resolver at this tree's own declaration.
        env["ARCHEAXIS_CAPABILITY_MANIFEST"] = str(manifest)

    report["interpreter"] = str(interpreter)
    report["manifest"] = str(manifest)
    report["manifest_present"] = manifest.is_file()
    declared = routes if routes is not None else profile.get("routes", [])
    report["declared_routes"] = len(declared)

    for route in declared:
        capability = str(route.get("capability", ""))
        worker = staged_root / str(route.get("script", ""))
        entry: dict = {"capability": capability}
        entry["launch"] = check_launch(worker, capability, interpreter, staged_root, env)
        entry["engine"] = check_engine(
            capability, interpreter, staged_root,
            {**env, "ARCHEAXIS_CAPABILITY_MANIFEST": str(manifest)})
        entry["ok"] = bool(entry["launch"].get("ok")) and bool(entry["engine"].get("ok"))
        report["capabilities"].append(entry)

    report["summary"] = {
        "total": len(report["capabilities"]),
        "ready": sum(1 for entry in report["capabilities"] if entry["ok"]),
        "not_ready": sum(1 for entry in report["capabilities"] if not entry["ok"]),
    }
    report["ok"] = report["summary"]["not_ready"] == 0
    report["requirements"] = requirements()
    report["missing"] = missing_requirements(report)
    return report


def requirements() -> list[dict]:
    """What the declared capabilities need, so the check can state its own preconditions.

    A runbook that says "provision the engines" is not reproducible; this is the list, per
    capability, so the gap between a runtime and a passing run is enumerable.
    """
    return [
        {"capability": capability,
         "python_modules": needs.get("modules", []),
         "declared_executables": needs.get("executables", []),
         "unverifiable_models": needs.get("model", [])}
        for capability, needs in REQUIREMENTS.items()
    ]


def missing_requirements(report: dict) -> dict:
    """The distinct modules and executables that are absent, across all routes."""
    modules: list[str] = []
    executables: list[str] = []
    models: list[str] = []
    for entry in report.get("capabilities", []):
        engine = entry.get("engine") or {}
        if not (engine.get("modules") or {}).get("ok", True):
            for name in (engine.get("modules") or {}).get("required", []):
                if name not in modules:
                    modules.append(name)
        for name, detail in (engine.get("executables") or {}).items():
            if not detail.get("ok") and name not in executables:
                executables.append(name)
        for name in engine.get("unverifiable") or []:
            if name not in models:
                models.append(name)
    return {"python_modules": modules, "declared_executables": executables,
            "unverifiable_models": models, "none": not (modules or executables)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staged_root", type=Path, nargs="?",
                        help="a staged runtime root; not needed with --requirements")
    parser.add_argument("--interpreter", type=Path, default=None,
                        help="defaults to the interpreter the profile names")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--requirements", action="store_true",
                        help="print what the declared capabilities need and stop; "
                             "does not start a worker or touch the runtime")
    args = parser.parse_args()
    if args.requirements:
        print(json.dumps({"schema": "archeaxis.capability-requirements/v1",
                          "capabilities": requirements()}, ensure_ascii=False, indent=2))
        return 0
    if args.staged_root is None:
        parser.error("staged_root is required unless --requirements is given")
    try:
        report = verify(args.staged_root, args.interpreter, args.manifest, None)
    except (OSError, ValueError, KeyError) as error:
        print(json.dumps({"schema": "archeaxis.capability-readiness/v1", "ok": False,
                          "failure": str(error)}, ensure_ascii=False))
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
