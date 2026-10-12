"""Candidate interpreter routing regressions; no model inference qualification."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def module():
    spec = importlib.util.spec_from_file_location(
        "speech_candidate_runner_test", ROOT / "scripts/ci/run_common_speech_candidate.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def candidate(tmp_path):
    root = tmp_path / "candidate"
    (root / "runtime").mkdir(parents=True)
    (root / "runtime/python.exe").write_bytes(b"SYNTHETIC_NOT_EXECUTABLE")
    (root / "worker.py").write_text("# synthetic", encoding="utf-8")
    (root / "worker-profile.json").write_text(json.dumps({
        "schema": "archeaxis.worker-profile/v1", "python": "runtime/python.exe",
        "script": "worker.py", "staging": "staging"}), encoding="utf-8")
    return root


def test_runs_only_profile_interpreter_and_preserves_nonzero_exit(module, tmp_path, monkeypatch):
    root = candidate(tmp_path)
    observed = []
    monkeypatch.setenv("PYTHONPATH", "untrusted-host-packages")
    monkeypatch.setenv("PYTHONHOME", "untrusted-host-runtime")
    monkeypatch.setenv("FFMPEG_CMD", "explicit-ci-tool")
    def execute(command, **kwargs):
        observed.append((command, kwargs))
        return SimpleNamespace(returncode=7)
    monkeypatch.setattr(module.subprocess, "run", execute)
    assert module.run(root, ["--language", "en"], tmp_path / "preflight.json") == 7
    command, options = observed[0]
    assert command[0] == str((root / "runtime/python.exe").resolve())
    assert command[1:4] == ["-I", "-B", "-c"]
    assert command[5:8] == [command[0], str(module.PROBE), str(tmp_path / "preflight.json")]
    assert command[8:] == ["--candidate", str(root.resolve()), "--language", "en"]
    assert "PYTHONHOME" not in options["env"] and "PYTHONPATH" not in options["env"]
    assert options["env"]["FFMPEG_CMD"] == "explicit-ci-tool"


@pytest.mark.parametrize("mutation", ["missing", "wrong-profile", "different-host-selection", "duplicate"])
def test_preflight_refuses_bad_identity_before_child(module, tmp_path, monkeypatch, mutation):
    root = candidate(tmp_path)
    arguments = []
    if mutation == "missing":
        (root / "runtime/python.exe").unlink()
    elif mutation == "wrong-profile":
        (root / "worker-profile.json").write_text("{}", encoding="utf-8")
    elif mutation == "different-host-selection":
        (root / "runtime/python").mkdir()
        (root / "runtime/python/python.exe").write_bytes(b"SYNTHETIC_OTHER")
    else:
        arguments = ["--candidate=other"]
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: pytest.fail("child must not start"))
    with pytest.raises(Exception):
        module.run(root, arguments, tmp_path / "preflight.json")


@pytest.mark.parametrize("mode,expected", [("missing-yaml", 1), ("missing-asr", 1),
                                         ("outside", 1), ("mismatch", 1), ("synthetic-valid", 7)])
def test_actual_isolated_bootstrap_gate(module, tmp_path, mode, expected):
    # Real isolated child, synthetic import records; these are routing proofs,
    # not evidence that an installed candidate has real YAML/ASR dependencies.
    probe = tmp_path / "probe.py"
    marker = tmp_path / "started"
    probe.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('started')\nraise SystemExit(7)\n", encoding="utf-8")
    output = tmp_path / "preflight.json"
    executable = str(Path(sys.executable).resolve())
    setup = "import sys,types\n"
    for name in ("yaml", "faster_whisper"):
        if (mode == "missing-yaml" and name == "yaml") or (mode == "missing-asr" and name == "faster_whisper"):
            setup += f"sys.modules[{name!r}]=None\n"
        else:
            location = str(probe) if mode == "outside" else executable
            setup += f"m=types.ModuleType({name!r});m.__file__={location!r};sys.modules[{name!r}]=m\n"
    result = subprocess.run([sys.executable, "-I", "-B", "-c", setup + module.BOOTSTRAP,
                             str(probe) if mode == "mismatch" else executable,
                             str(probe), str(output)], capture_output=True, timeout=15)
    assert result.returncode == expected
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is (mode == "synthetic-valid")
    assert marker.exists() is (mode == "synthetic-valid")
    assert receipt["qualification"] != "INTEGRATED_SELECTED_PHRASE_AUDIO_CONTENT_TIME_REPARSE_RESTART"


def test_profile_failure_still_records_preflight(module, tmp_path, monkeypatch):
    original_load = module.load
    fake_dev = SimpleNamespace(layout=lambda _: {"artifacts": tmp_path}, prepare=lambda _: {})
    monkeypatch.setattr(module, "load", lambda name, path: fake_dev if name == "speech_candidate_dev" else original_load(name, path))
    assert module.main(["--candidate", str(tmp_path / "missing")]) == 1
    receipt = json.loads((tmp_path / "common-speech-preflight.json").read_text(encoding="utf-8"))
    assert receipt["ok"] is False and receipt["qualification"] == "NOT_EXECUTED"
    assert "error_type" in receipt


def test_duplicate_cli_selector_refused(module):
    with pytest.raises(SystemExit) as error:
        module.main(["--candidate", "first", "--candidate=second"])
    assert error.value.code == 2


def test_zero_exit_without_import_receipt_is_not_success(module, tmp_path, monkeypatch):
    original_load = module.load
    fake_dev = SimpleNamespace(layout=lambda _: {"artifacts": tmp_path}, prepare=lambda _: {})
    monkeypatch.setattr(module, "load", lambda name, path: fake_dev if name == "speech_candidate_dev" else original_load(name, path))
    monkeypatch.setattr(module, "run", lambda *args: 0)
    assert module.main(["--candidate", str(tmp_path)]) == 1
    receipt = json.loads((tmp_path / "common-speech-preflight.json").read_text(encoding="utf-8"))
    assert receipt["ok"] is False and receipt["probe_exit_code"] == 0
    assert receipt["error_type"] == "CandidatePreflightUnconfirmed"
