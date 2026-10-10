import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

import pytest

WORKER = Path(__file__).parents[1] / "services/python-workers/course/worker_general_course.py"
spec = importlib.util.spec_from_file_location("general_course_worker", WORKER)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def request():
    artifact = {"artifact_id": "lesson-1", "artifact_type": "lesson", "title": "Evidence lesson",
                "domain_pack_id": "general", "source_ids": ["source-1"], "knowledge_ids": ["kc-1"],
                "renderer": "native-lesson", "renderer_version": "1.0.0", "status": "candidate",
                "interactive": False}
    return {"schema": worker.SCHEMA, "operation": "render", "artifact": copy.deepcopy(artifact),
            "manifest": {"manifest_id": "course-1", "title": "Evidence", "domain_pack_id": "general",
                         "status": "candidate", "artifacts": [artifact], "knowledge_components": [
                             {"component_id": "kc-1", "kind": "fact", "title": "Anchor",
                              "statement": "An anchor identifies a source location.", "source_ids": ["source-1"]}],
                         "learning_objectives": [{"objective_id": "obj-1", "title": "Use evidence",
                                                  "statement": "Locate an anchor.", "knowledge_component_ids": ["kc-1"]}]}}


def test_donor_projection_is_derived_and_bound_without_canonical_claim():
    result = worker.process(request())
    assert result["status"] == "DERIVED"
    assert result["canonical_bindings_verified"] is False
    assert result["human_review_required"] is True
    assert result["lesson"]["write_policy"] == "dry_run"
    assert result["lesson"]["source"] == "courseware:course-1:lesson-1"
    assert "An anchor identifies" in result["lesson"]["content"]
    assert result["lesson"]["frontmatter"]["knowledge_ids"] == ["kc-1"]


@pytest.mark.parametrize("case", ["unbound", "cycle", "unknown_component", "interactive", "domain", "promoted", "no_review", "oversized"])
def test_invalid_or_unreviewed_course_rejected(case):
    payload = request()
    if case == "unbound": payload["artifact"]["title"] = "changed"
    if case == "cycle": payload["manifest"]["knowledge_components"][0]["prerequisite_ids"] = ["kc-1"]
    if case == "unknown_component": payload["manifest"]["artifacts"][0]["knowledge_ids"] = ["unknown"]
    if case == "interactive":
        payload["artifact"]["interactive"] = True
        payload["manifest"]["artifacts"][0]["interactive"] = True
    if case == "domain": payload["manifest"]["domain_pack_id"] = "math"
    if case == "promoted": payload["manifest"]["status"] = "ready"
    if case == "no_review": payload["manifest"]["artifacts"][0]["human_review_required"] = False
    if case == "oversized": payload["manifest"]["title"] = "X" * worker.MAX_INPUT
    assert worker.process(payload)["status"] == "INVALID_REQUEST"


def test_missing_donor_explicitly_unavailable(monkeypatch):
    def missing():
        raise ImportError("donor not bundled")
    monkeypatch.setattr(worker, "_donors", missing)
    assert worker.process(request())["status"] == "UNAVAILABLE"


def test_real_subprocess_reads_one_json_and_creates_no_output_files(tmp_path):
    before = list(tmp_path.iterdir())
    # The worker's contract output is UTF-8 JSON, so the journey declares it on both ends instead
    # of inheriting the host codepage twice: an em dash kills a cp936 pipe on the read side.
    result = subprocess.run([sys.executable, "-B", str(WORKER)], cwd=tmp_path,
                            input=json.dumps(request()) + "\n", text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONUTF8": "1"},
                            capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "DERIVED"
    assert list(tmp_path.iterdir()) == before


def test_validate_does_not_render():
    payload = request()
    payload["operation"] = "validate"
    payload.pop("artifact")
    result = worker.process(payload)
    assert result["status"] == "VALIDATED"
    assert "lesson" not in result


def test_packaged_worker_uses_its_interpreters_locked_wheel(tmp_path):
    """Actual subprocess: sibling worker + site-packages, without repo/app."""
    root = WORKER.parents[3]
    packaged = tmp_path / "portable/workers/course/worker_general_course.py"
    packaged.parent.mkdir(parents=True)
    shutil.copyfile(WORKER, packaged)
    purelib = tmp_path / "portable/runtime/Lib/site-packages"
    for relative in ("app/contracts/courseware_v1.py", "app/contracts/general_learning_v1.py",
                     "app/adapters/courseware_lesson.py", "shared/approved_paths.py", "shared/obsidian_projection.py"):
        target = purelib / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    launcher = "import runpy,sys,sysconfig; sysconfig.get_path=lambda key:sys.argv[2]; runpy.run_path(sys.argv[1],run_name='__main__')"
    child = subprocess.run([sys.executable, "-I", "-X", "utf8", "-B", "-c", launcher, str(packaged), str(purelib)],
                           input=json.dumps(request()) + "\n", text=True, encoding="utf-8",
                           capture_output=True, cwd=tmp_path, timeout=15)
    assert child.returncode == 0, child.stderr + child.stdout
    result = json.loads(child.stdout)
    assert result["status"] == "DERIVED" and result["canonical_bindings_verified"] is False
    assert "An anchor identifies" in result["lesson"]["content"]
    assert not (tmp_path / "portable/app").exists()


def test_hello_stdlib_only_without_donors_or_network(tmp_path):
    isolated = tmp_path / "worker.py"
    isolated.write_bytes(WORKER.read_bytes())
    launcher = (
        "import runpy,sys; "
        "sys.addaudithook(lambda event,args: (_ for _ in ()).throw(AssertionError('network forbidden')) if event.startswith('socket.') else None); "
        "sys.argv=[sys.argv[1],'--hello']; runpy.run_path(sys.argv[0],run_name='__main__')"
    )
    child = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", launcher, str(isolated)],
                           cwd=tmp_path, text=True, capture_output=True, timeout=5)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == {
        "schema": "archeaxis.derived-worker-hello/v1", "capability": "course.general", "version": 1}
