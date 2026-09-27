"""Contract tests for the same-run vNext journey receipt gate.

Two layers are pinned here on purpose:

* `validate` - the receipt body itself (identity, 12 steps, manifest digest);
* the `check_vnext_receipt.py` command line - the file/run binding a real caller
  depends on, exercised as a subprocess with a controlled environment so nothing
  leaks in from the pytest run.

The local entry point (`dev.py --env-file` -> `check_vnext_receipt.py --env-file`)
is covered end to end as well, because before it existed the only supported way to
hand one run's identity to the gate was the runner-owned `GITHUB_ENV` file, which a
local shell does not have.
"""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CHECKER = REPO / "scripts" / "ci" / "check_vnext_receipt.py"
COMMIT = "a" * 40
RUN_ID = "currentrun01"


def steps():
    return {f"{i:02}_step": "PASS: checked" for i in range(1, 13)}


def receipt(**overrides):
    value = {"schema": "archeaxis.vnext/v01-closed-loop-receipt", "schema_version": 2,
             "source_commit": COMMIT, "run_id": RUN_ID, "total_steps": 12,
             "steps": steps(), "manifest_sha256": "b" * 64}
    value.update(overrides)
    return value


def test_receipt_rejects_stale_identity_failed_or_missing_steps():
    from scripts.ci.check_vnext_receipt import validate

    validate(receipt(), COMMIT, RUN_ID)
    for key, value in (("source_commit", "c" * 40), ("run_id", "previous"),
                       ("total_steps", 0), ("steps", {"01_step": "PASS: old"}),
                       ("steps", {**steps(), "05_step": "FAIL: failure"})):
        bad = copy.deepcopy(receipt())
        bad[key] = value
        with pytest.raises(ValueError):
            validate(bad, COMMIT, RUN_ID)


def controlled_env(**identity):
    """A minimal environment: no pytest or launcher variables can leak in."""
    env = {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
           "PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
    env.update(identity)
    return env


def run_checker(env, *arguments):
    return subprocess.run([sys.executable, "-B", str(CHECKER), *arguments],
                          cwd=REPO, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def write_run(tmp_path, body, *, directory=RUN_ID):
    """Create <tmp>/runs/<directory>/artifacts/vnext-journey.json and return the root."""
    run = tmp_path / "runs" / directory
    artifacts = run / "artifacts"
    artifacts.mkdir(parents=True)
    path = artifacts / "vnext-journey.json"
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return run, path


def test_current_run_receipt_is_accepted(tmp_path):
    run, path = write_run(tmp_path, receipt())
    result = run_checker(controlled_env(ARCHEAXIS_RUN_ROOT=str(run),
                                        VNEXT_RECEIPT_OUT=str(path),
                                        ARCHEAXIS_SOURCE_COMMIT=COMMIT))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


@pytest.mark.parametrize(
    "case",
    ["missing_run_root", "missing_receipt", "corrupt_receipt", "wrong_run_id",
     "wrong_source_commit", "reused_previous_run", "failed_step", "receipt_outside_artifacts"],
)
def test_every_incomplete_run_is_rejected(tmp_path, case):
    body = receipt()
    identity = {}
    if case == "missing_run_root":
        run, path = write_run(tmp_path, body)
        identity = {"VNEXT_RECEIPT_OUT": str(path), "ARCHEAXIS_SOURCE_COMMIT": COMMIT}
    elif case == "missing_receipt":
        run = tmp_path / "runs" / RUN_ID
        (run / "artifacts").mkdir(parents=True)
        identity = {"ARCHEAXIS_RUN_ROOT": str(run),
                    "VNEXT_RECEIPT_OUT": str(run / "artifacts" / "vnext-journey.json"),
                    "ARCHEAXIS_SOURCE_COMMIT": COMMIT}
    elif case == "corrupt_receipt":
        run, path = write_run(tmp_path, "{not json")
        identity = {"ARCHEAXIS_RUN_ROOT": str(run), "VNEXT_RECEIPT_OUT": str(path),
                    "ARCHEAXIS_SOURCE_COMMIT": COMMIT}
    elif case == "wrong_run_id":
        run, path = write_run(tmp_path, receipt(run_id="someotherrun"))
        identity = {"ARCHEAXIS_RUN_ROOT": str(run), "VNEXT_RECEIPT_OUT": str(path),
                    "ARCHEAXIS_SOURCE_COMMIT": COMMIT}
    elif case == "wrong_source_commit":
        run, path = write_run(tmp_path, receipt(source_commit="d" * 40))
        identity = {"ARCHEAXIS_RUN_ROOT": str(run), "VNEXT_RECEIPT_OUT": str(path),
                    "ARCHEAXIS_SOURCE_COMMIT": COMMIT}
    elif case == "reused_previous_run":
        # A previous run's receipt, still on disk, offered for the current run.
        previous, previous_path = write_run(tmp_path, receipt(run_id="previous0001"),
                                            directory="previous0001")
        current = tmp_path / "runs" / RUN_ID
        current.mkdir(parents=True)
        identity = {"ARCHEAXIS_RUN_ROOT": str(current),
                    "VNEXT_RECEIPT_OUT": str(previous_path),
                    "ARCHEAXIS_SOURCE_COMMIT": COMMIT}
        assert previous.is_dir()
    elif case == "failed_step":
        run, path = write_run(tmp_path, receipt(steps={**steps(), "07_step": "FAIL: no rows"}))
        identity = {"ARCHEAXIS_RUN_ROOT": str(run), "VNEXT_RECEIPT_OUT": str(path),
                    "ARCHEAXIS_SOURCE_COMMIT": COMMIT}
    else:  # receipt_outside_artifacts
        run = tmp_path / "runs" / RUN_ID
        run.mkdir(parents=True)
        outside = run / "vnext-journey.json"
        outside.write_text(json.dumps(receipt()), encoding="utf-8")
        identity = {"ARCHEAXIS_RUN_ROOT": str(run), "VNEXT_RECEIPT_OUT": str(outside),
                    "ARCHEAXIS_SOURCE_COMMIT": COMMIT}

    result = run_checker(controlled_env(**identity))
    assert result.returncode == 1, f"{case} was accepted: {result.stdout}{result.stderr}"
    assert "rejected" in result.stdout


def test_env_file_carries_one_run_identity_to_the_gate(tmp_path):
    """The local path: dev.py writes the run environment, the gate reads it back."""
    from scripts.runtime.dev import read_env_file, write_env_file

    run, path = write_run(tmp_path, receipt())
    run_env = write_env_file(tmp_path / "last-run.env", {
        "ARCHEAXIS_RUN_ROOT": str(run),
        "VNEXT_RECEIPT_OUT": str(path),
        "ARCHEAXIS_SOURCE_COMMIT": COMMIT,
        "SOME_UNRELATED_PATH": str(tmp_path),
    })
    assert read_env_file(run_env)["ARCHEAXIS_RUN_ROOT"] == str(run)

    accepted = run_checker(controlled_env(), "--env-file", str(run_env))
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr

    # An explicit operator value still wins over the recorded one.
    winning = run_checker(controlled_env(ARCHEAXIS_SOURCE_COMMIT="e" * 40),
                          "--env-file", str(run_env))
    assert winning.returncode == 1, winning.stdout + winning.stderr

    missing = run_checker(controlled_env(), "--env-file", str(tmp_path / "absent.env"))
    assert missing.returncode == 1, missing.stdout + missing.stderr


def test_receipt_still_rejected_when_env_file_is_tampered(tmp_path):
    from scripts.runtime.dev import write_env_file

    run, path = write_run(tmp_path, receipt())
    original = write_env_file(tmp_path / "good.env", {
        "ARCHEAXIS_RUN_ROOT": str(run),
        "VNEXT_RECEIPT_OUT": str(path),
        "ARCHEAXIS_SOURCE_COMMIT": COMMIT,
    })
    tampered = tmp_path / "tampered.env"
    tampered.write_text(
        original.read_text(encoding="utf-8").replace(COMMIT, "f" * 40), encoding="utf-8")
    result = run_checker(controlled_env(), "--env-file", str(tampered))
    assert result.returncode == 1, result.stdout + result.stderr
