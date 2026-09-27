"""Contract tests for the same-run vNext journey receipt gate.

Two layers are pinned on purpose:

* `validate` - the receipt body: identity, tested working state, 12 steps, manifest;
* the `check_vnext_receipt.py` command line - the file/run binding a real caller
  depends on, exercised as a subprocess with a controlled environment so nothing
  leaks in from the pytest run.

Every negative case starts from the same accepted positive case and changes exactly one
condition, then asserts the *specific* rejection reason. An exit code alone would not
show which guard fired, and a matrix in which every case merely fails for a missing run
root would prove nothing about the commit, path and step checks.
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
PATCH = "c" * 64
RUN_ID = "currentrun01"


def steps():
    return {f"{i:02}_step": "PASS: checked" for i in range(1, 13)}


def receipt(**overrides):
    value = {"schema": "archeaxis.vnext/v01-closed-loop-receipt", "schema_version": 3,
             "source_commit": COMMIT, "source_tree": "b" * 40,
             "source_dirty": False, "source_patch_sha256": PATCH,
             "run_id": RUN_ID, "total_steps": 12,
             "steps": steps(), "manifest_sha256": "b" * 64}
    value.update(overrides)
    return value


def test_validate_rejects_stale_identity_failed_steps_and_unbound_working_state():
    from scripts.ci.check_vnext_receipt import validate

    validate(receipt(), COMMIT, RUN_ID, False, PATCH)
    cases = {
        "source_commit": ("c" * 40, "identity"),
        "run_id": ("previous", "identity"),
        "schema_version": (2, "schema_version"),
        "schema": ("other", "not a vNext closed-loop receipt"),
        "total_steps": (0, "steps"),
        "steps": ({"01_step": "PASS: old"}, "steps"),
        "steps_failed": ({**steps(), "05_step": "FAIL: failure"}, "steps"),
    }
    for key, (value, expected) in cases.items():
        bad = copy.deepcopy(receipt())
        bad[key if key != "steps_failed" else "steps"] = value
        with pytest.raises(ValueError) as error:
            validate(bad, COMMIT, RUN_ID, False, PATCH)
        assert expected in str(error.value)
    missing_field = copy.deepcopy(receipt())
    del missing_field["source_dirty"]
    with pytest.raises(ValueError, match="working state"):
        validate(missing_field, COMMIT, RUN_ID, False, PATCH)
    # A dirty receipt offered for a clean run, and a patch digest that disagrees.
    with pytest.raises(ValueError, match="working state"):
        validate(receipt(source_dirty=True), COMMIT, RUN_ID, False, PATCH)
    with pytest.raises(ValueError, match="patch identity"):
        validate(receipt(source_patch_sha256="d" * 64), COMMIT, RUN_ID, False, PATCH)
    # The dirty case is accepted once every part of the identity agrees.
    validate(receipt(source_dirty=True), COMMIT, RUN_ID, True, PATCH)


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


def write_run(tmp_path, body, *, directory=RUN_ID, filename="vnext-journey.json"):
    run = tmp_path / "runs" / directory
    artifacts = run / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    path = artifacts / filename
    path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return run, path


def accepted_clean(tmp_path):
    """Establish the accepted positive case every negative case starts from.

    It always writes a *valid* receipt: a negative case must begin from conditions
    under which the gate accepts, otherwise a rejection proves nothing about the guard
    it claims to exercise.
    """
    run, path = write_run(tmp_path, receipt())
    identity = {"ARCHEAXIS_RUN_ROOT": str(run), "VNEXT_RECEIPT_OUT": str(path),
                "ARCHEAXIS_SOURCE_COMMIT": COMMIT, "ARCHEAXIS_SOURCE_DIRTY": "0",
                "ARCHEAXIS_SOURCE_PATCH_SHA256": PATCH}
    result = run_checker(controlled_env(**identity))
    assert result.returncode == 0, "positive case broke: " + result.stdout + result.stderr
    return identity


def test_clean_current_run_is_accepted_and_says_so(tmp_path):
    identity = accepted_clean(tmp_path)
    result = run_checker(controlled_env(**identity))
    assert "committed" in result.stdout
    assert "UNCOMMITTED" not in result.stdout


def test_dirty_run_is_accepted_but_labelled_uncommitted(tmp_path):
    run, path = write_run(tmp_path, receipt(source_dirty=True, source_patch_sha256=PATCH))
    identity = {"ARCHEAXIS_RUN_ROOT": str(run), "VNEXT_RECEIPT_OUT": str(path),
                "ARCHEAXIS_SOURCE_COMMIT": COMMIT, "ARCHEAXIS_SOURCE_DIRTY": "1",
                "ARCHEAXIS_SOURCE_PATCH_SHA256": PATCH}
    result = run_checker(controlled_env(**identity))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "UNCOMMITTED" in result.stdout and "not a committed-source qualification" in result.stdout


def negative_cases(tmp_path):
    """(name, env overrides, receipt body, expected rejection reason)."""
    base = receipt()
    cases = [
        ("missing_run_root", {"ARCHEAXIS_RUN_ROOT": None}, base, "ARCHEAXIS_RUN_ROOT"),
        ("missing_receipt", {}, base, "No such file"),
        ("corrupt_receipt", {}, "{not json", "Expecting"),
        ("wrong_run_id", {}, receipt(run_id="someotherrun"),
         "receipt source/run identity mismatch"),
        ("wrong_source_commit", {}, receipt(source_commit="d" * 40),
         "receipt source/run identity mismatch"),
        ("failed_step", {}, receipt(steps={**steps(), "07_step": "FAIL: no rows"}),
         "receipt has incomplete or failed steps"),
        ("legacy_v2_receipt_no_working_state", {}, receipt(schema_version=2),
         "schema_version"),
        ("dirty_run_clean_receipt", {"ARCHEAXIS_SOURCE_DIRTY": "1"}, base,
         "receipt working state does not match this run"),
        ("clean_run_dirty_receipt", {}, receipt(source_dirty=True),
         "receipt working state does not match this run"),
        ("patch_mismatch", {}, receipt(source_patch_sha256="d" * 64),
         "receipt patch identity does not match this run"),
    ]
    return cases


@pytest.mark.parametrize("name", [c[0] for c in negative_cases(Path("."))])
def test_each_negative_case_is_rejected_for_its_own_reason(tmp_path, name):
    cases = {c[0]: c for c in negative_cases(tmp_path)}
    _, overrides, body, expected = cases[name]
    identity = accepted_clean(tmp_path)
    # Start from the accepted state, then change exactly the one intended condition.
    if body is not None:
        text = body if isinstance(body, str) else json.dumps(body)
        Path(identity["VNEXT_RECEIPT_OUT"]).write_text(text, encoding="utf-8")
    for key, value in overrides.items():
        if value is None:
            identity.pop(key, None)
        else:
            identity[key] = value
    if name == "missing_receipt":
        Path(identity["VNEXT_RECEIPT_OUT"]).unlink()
    result = run_checker(controlled_env(**identity))
    assert result.returncode == 1, f"{name} was accepted: {result.stdout}{result.stderr}"
    assert expected in result.stdout, f"{name} failed for the wrong reason: {result.stdout}"


def test_reused_previous_run_and_receipt_outside_artifacts_are_rejected(tmp_path):
    """Both are path-binding failures, and both name the path rule, not something else."""
    previous_run, previous_receipt = write_run(tmp_path, receipt(run_id="previous0001"),
                                               directory="previous0001")
    current = tmp_path / "runs" / RUN_ID
    current.mkdir(parents=True)
    result = run_checker(controlled_env(ARCHEAXIS_RUN_ROOT=str(current),
                                        VNEXT_RECEIPT_OUT=str(previous_receipt),
                                        ARCHEAXIS_SOURCE_COMMIT=COMMIT,
                                        ARCHEAXIS_SOURCE_DIRTY="0",
                                        ARCHEAXIS_SOURCE_PATCH_SHA256=PATCH))
    assert result.returncode == 1
    assert "inside this run's artifacts" in result.stdout

    outside = current / "vnext-journey.json"
    outside.write_text(json.dumps(receipt()), encoding="utf-8")
    result = run_checker(controlled_env(ARCHEAXIS_RUN_ROOT=str(current),
                                        VNEXT_RECEIPT_OUT=str(outside),
                                        ARCHEAXIS_SOURCE_COMMIT=COMMIT,
                                        ARCHEAXIS_SOURCE_DIRTY="0",
                                        ARCHEAXIS_SOURCE_PATCH_SHA256=PATCH))
    assert result.returncode == 1
    assert "inside this run's artifacts" in result.stdout


def test_env_file_carries_one_run_identity_to_the_gate(tmp_path):
    """The local path: dev.py writes the run environment, the gate reads it back."""
    from scripts.runtime.dev import read_env_file, write_env_file

    run, path = write_run(tmp_path, receipt())
    run_env = write_env_file(tmp_path / "last-run.env", {
        "ARCHEAXIS_RUN_ROOT": str(run),
        "VNEXT_RECEIPT_OUT": str(path),
        "ARCHEAXIS_SOURCE_COMMIT": COMMIT,
        "ARCHEAXIS_SOURCE_DIRTY": "0",
        "ARCHEAXIS_SOURCE_PATCH_SHA256": PATCH,
        "SOME_UNRELATED_PATH": str(tmp_path),
    })
    assert read_env_file(run_env)["ARCHEAXIS_RUN_ROOT"] == str(run)
    accepted = run_checker(controlled_env(), "--env-file", str(run_env))
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    missing = run_checker(controlled_env(), "--env-file", str(tmp_path / "absent.env"))
    assert missing.returncode == 1
    assert "unusable" in missing.stdout


def test_identity_conflict_between_environment_and_run_file_is_refused(tmp_path):
    """An identity disagreement may not be resolved by preferring one side silently."""
    from scripts.runtime.dev import write_env_file

    run, path = write_run(tmp_path, receipt())
    run_env = write_env_file(tmp_path / "run.env", {
        "ARCHEAXIS_RUN_ROOT": str(run),
        "VNEXT_RECEIPT_OUT": str(path),
        "ARCHEAXIS_SOURCE_COMMIT": COMMIT,
        "ARCHEAXIS_SOURCE_DIRTY": "0",
        "ARCHEAXIS_SOURCE_PATCH_SHA256": PATCH,
    })
    result = run_checker(controlled_env(ARCHEAXIS_SOURCE_COMMIT="e" * 40),
                         "--env-file", str(run_env))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "run identity conflict" in result.stdout
    assert "ARCHEAXIS_SOURCE_COMMIT" in result.stdout
    # Agreement is still fine: the same value on both sides is not a conflict.
    agree = run_checker(controlled_env(ARCHEAXIS_SOURCE_COMMIT=COMMIT),
                        "--env-file", str(run_env))
    assert agree.returncode == 0, agree.stdout + agree.stderr


def test_receipt_still_rejected_when_env_file_is_tampered(tmp_path):
    from scripts.runtime.dev import write_env_file

    run, path = write_run(tmp_path, receipt())
    original = write_env_file(tmp_path / "good.env", {
        "ARCHEAXIS_RUN_ROOT": str(run),
        "VNEXT_RECEIPT_OUT": str(path),
        "ARCHEAXIS_SOURCE_COMMIT": COMMIT,
        "ARCHEAXIS_SOURCE_DIRTY": "0",
        "ARCHEAXIS_SOURCE_PATCH_SHA256": PATCH,
    })
    tampered = tmp_path / "tampered.env"
    tampered.write_text(
        original.read_text(encoding="utf-8").replace(COMMIT, "f" * 40), encoding="utf-8")
    result = run_checker(controlled_env(), "--env-file", str(tampered))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "identity mismatch" in result.stdout
