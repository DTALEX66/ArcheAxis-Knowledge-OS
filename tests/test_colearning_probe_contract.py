"""The real-model co-learning probe: it exists, it declares what is real, and it fails closed.

The probe itself is run by hand because it needs a live Core and a local model, so what is asserted
here is the part that can be checked without either: that the script is present, that it is honest
about which parts of its evidence are real, and that its verdict logic cannot report a pass for a run
that stopped short.

The honesty labels matter more than usual. `m0_full_loop_smoke.py` covers the same chain and says of
itself that the model failure is a fixture. If this probe ever loses that distinction, a run of it
would look like evidence of human judgement that nobody exercised.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "colearning_real_model_smoke.py"


def _module():
    spec = importlib.util.spec_from_file_location("colearning_probe_under_test", PROBE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_probe_exists_and_drives_the_routes_that_run_a_model():
    source = PROBE.read_text(encoding="utf-8")
    # The three routes that make this different from the synthetic probe.
    for route in ("/api/v1/machine/answers", "/api/v1/machine/corrections",
                  "/api/v1/machine/retests"):
        assert route in source, f"the probe does not drive {route}"


def test_the_probe_declares_what_is_real_and_what_is_still_a_fixture():
    probe = _module()
    receipt = probe.Receipt().document()
    assert receipt["evidence_class"] == "REAL_MODEL"
    real = " ".join(receipt["what_is_real"]).lower()
    fixture = " ".join(receipt["what_is_still_a_fixture"]).lower()
    # the model inference is claimed as real...
    assert "model inference" in real, receipt["what_is_real"]
    # ...and the person is explicitly not
    assert "the person" in fixture, receipt["what_is_still_a_fixture"]
    assert "not evidence that a human reviewed" in fixture


def test_the_probe_needs_the_interpreter_before_it_can_claim_to_have_observed_the_loop(monkeypatch):
    probe = _module()
    monkeypatch.delenv("ARCHEAXIS_PYTHON", raising=False)
    missing = probe.unmet_prerequisites()
    assert "ARCHEAXIS_PYTHON" in missing
    # the reason says why the loop could not be observed, not merely that a variable is unset
    assert "scheduler" in missing["ARCHEAXIS_PYTHON"]
    monkeypatch.setenv("ARCHEAXIS_PYTHON", "python")
    assert probe.unmet_prerequisites() == {}


def test_a_run_that_stopped_short_is_never_a_pass():
    """The verdict logic, exercised directly rather than only through a live run."""
    probe = _module()

    complete = probe.Receipt()
    complete.stage("import_source", status=202)
    complete.stage("machine_cannot_accept_correction", status=403)
    # a prerequisite noted along the way does not demote a run that reached the end
    assert not complete.failed_stage
    assert any(entry["stage"] == "machine_cannot_accept_correction" for entry in complete.stages)

    stopped = probe.Receipt()
    stopped.stage("import_source", status=202)
    stopped.stage("machine_answer", status=503, problem="no worker is registered")
    assert stopped.failed_stage == "machine_answer"

    blocked = probe.Receipt()
    blocked.stage("import_source", status=202)
    blocked.block("machine_principal", "no machine credential in this launch")
    assert blocked.blocked


def test_the_probe_fails_closed_on_a_problem_stage():
    """A stage carrying `problem` has to decide the verdict, or a partial run reads as a pass."""
    probe = _module()
    receipt = probe.Receipt()
    receipt.stage("ok", status=200)
    assert receipt.failed_stage is None
    receipt.stage("bad", status=500, problem="something went wrong")
    assert receipt.failed_stage == "bad"


def test_the_probe_does_not_import_anything_outside_the_standard_library():
    """A probe runs on whatever interpreter is at hand, so its imports have to be stdlib plus the
    repository's own modules."""
    tree = ast.parse(PROBE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    third_party = imported - {
        "__future__", "importlib", "json", "os", "shutil", "sys", "time", "uuid",
        "datetime", "pathlib",
    }
    assert not third_party, f"the probe imports third-party modules: {sorted(third_party)}"


def test_report_rejects_incomplete_or_wrong_final_status():
    probe = _module()
    incomplete = probe.Receipt()
    incomplete.stage("import_source", status=202)
    assert probe.report(incomplete) == 1
    incorrect = probe.Receipt()
    incorrect.stage("machine_cannot_accept_correction", status=200)
    assert probe.report(incorrect) == 1


def test_retest_readback_must_match_the_failure():
    probe = _module()
    receipt = probe.Receipt()
    receipt.stage("retest_readback", status=200, links_to_failure=False)
    receipt.stage("machine_cannot_accept_correction", status=403)
    assert probe.report(receipt) == 1
