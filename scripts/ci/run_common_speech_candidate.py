"""Run the speech qualification with the validated candidate's own dependencies."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "scripts/probes/aaos01_common_speech_runtime_loop.py"

# Third-party imports happen before adding the audited probe directory. Neither
# the host's packages nor checkout packages can satisfy candidate dependencies.
BOOTSTRAP = r'''
import hashlib, importlib, json, pathlib, runpy, sys
executable = pathlib.Path(sys.executable).resolve()
expected, probe, output = map(pathlib.Path, sys.argv[1:4])
record = {"ok": False, "qualification": "NOT_EXECUTED", "modules": []}
try:
    if executable != expected.resolve():
        raise RuntimeError("candidate interpreter identity mismatch")
    runtime = executable.parent
    record["interpreter"] = str(executable)
    record["interpreter_sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
    for name in ("yaml", "faster_whisper"):
        module = importlib.import_module(name)
        path = pathlib.Path(module.__file__).resolve()
        if not path.is_relative_to(runtime) or not path.is_file():
            raise RuntimeError(name + " imported outside candidate runtime")
        record["modules"].append({"name": name, "path": str(path)})
    record["pth_files"] = [{"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                           for p in runtime.glob("python*._pth")]
    record.update(ok=True, qualification="CANDIDATE_IMPORTS_VERIFIED_CORE_NOT_EXECUTED")
except Exception as error:
    record["error_type"] = type(error).__name__
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    raise
output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
sys.path.insert(0, str(probe.parent))
sys.argv = [str(probe), *sys.argv[4:]]
runpy.run_path(str(probe), run_name="__main__")
'''


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(candidate, arguments, output):
    boundary = load("speech_candidate_boundary", REPO / "scripts/ci/prepare_common_asr.py")
    candidate = boundary.owned_path(candidate, REPO)
    launcher = load("speech_candidate_launcher", REPO / "scripts/release/backend_launcher.py")
    profile = launcher.load_profile(candidate)
    executable = boundary.owned_path(profile["python"], REPO)
    nested = candidate / "runtime/python/python.exe"
    selected = nested if nested.is_file() else candidate / "runtime/python.exe"
    if executable != selected.resolve():
        raise ValueError("candidate interpreter differs from formal host selection")
    # One candidate selector only; callers cannot select a different child root.
    if "--candidate" in arguments or any(arg.startswith("--candidate=") for arg in arguments):
        raise ValueError("duplicate candidate selector")
    environment = launcher.build_environment(candidate)
    result = subprocess.run(
        [str(executable), "-I", "-B", "-c", BOOTSTRAP, str(executable), str(PROBE), str(output),
         "--candidate", str(candidate), *arguments],
        cwd=REPO, env=environment, check=False,
    )
    return result.returncode


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    if sum(arg == "--candidate" or arg.startswith("--candidate=") for arg in arguments) != 1:
        parser.error("exactly one candidate selector required")
    args, remainder = parser.parse_known_args(arguments)
    dev = load("speech_candidate_dev", REPO / "scripts/runtime/dev.py")
    paths = dev.layout(REPO)
    dev.prepare(paths)
    output = paths["artifacts"] / "common-speech-preflight.json"
    record = {"ok": False, "qualification": "NOT_EXECUTED", "stage": "CANDIDATE_PREFLIGHT"}
    output.write_text(json.dumps(record) + "\n", encoding="utf-8")
    try:
        code = run(args.candidate, remainder, output)
        record = json.loads(output.read_text(encoding="utf-8"))
        record["probe_exit_code"] = code
        if record.get("ok") is not True and code == 0:
            record["error_type"] = "CandidatePreflightUnconfirmed"
            code = 1
        # Import success cannot qualify the actual Core probe.
        record["core_qualification"] = "READ_INDEPENDENT_COMMON_SPEECH_RECEIPT"
    except Exception as error:
        record["error_type"] = type(error).__name__
        code = 1
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exit_code": code, "preflight_receipt": str(output)}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
