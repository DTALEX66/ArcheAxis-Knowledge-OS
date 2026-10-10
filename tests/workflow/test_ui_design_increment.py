"""Falsify design-source preservation, task mapping and analysis/implementation boundaries."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ui_design_gate", ROOT / "scripts/ci/check_ui_design_increment.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def document():
    return json.loads((ROOT / gate.OVERLAY).read_text(encoding="utf-8"))

def test_real_archived_sources_and_page_mapping_pass():
    assert gate.validate(ROOT, document()) == []

@pytest.mark.parametrize("fault", ["hash", "source_line", "task", "implementation", "role", "progress", "count", "duplicate", "private", "traversal", "frozen"])
def test_design_input_faults_cannot_qualify(fault):
    value = copy.deepcopy(document())
    if fault == "hash":
        value["sources"][0]["sha256"] = "0" * 64
    elif fault == "source_line":
        value["requirements"][0]["source_line"] = 1
    elif fault == "task":
        value["requirements"][0]["tasks"] = ["INVENTED_PRODUCTION_TASK"]
    elif fault == "implementation":
        value["requirements"][0]["implementation"] = "PASS"
    elif fault == "role":
        value["role"] = "PRODUCT_AUTHORITY"
    elif fault == "progress":
        value["progress_record"] = "docs/current/NEW-PROGRESS.json"
    elif fault == "count":
        value["requirements"].pop()
    elif fault == "duplicate":
        value["requirements"][1] = copy.deepcopy(value["requirements"][0])
    elif fault == "private":
        value["source_archive_manifest"] = ".codex/secret.json"
    elif fault == "traversal":
        value["source_archive_manifest"] = "../other-repo/manifest.json"
    elif fault == "frozen":
        value["policy"]["ft01_ft04"] = "ACTIVE"
    assert gate.validate(ROOT, value)

@pytest.mark.parametrize("path", [".codex/never-read", "../never-read", "D:/All projects/Record/never-read", "E:/never-read"])
def test_private_and_external_paths_rejected_before_io(path):
    with pytest.raises(ValueError, match="unsafe design source locator"):
        gate.local_file(ROOT, path)

@pytest.mark.parametrize("fault", ["member_hash", "member_missing", "cross_loss", "cross_status", "cross_task"])
def test_zip_member_and_spec_tampering_rejected(monkeypatch, fault):
    value = document()
    original = gate.read_json
    def altered(repo, relative):
        data = copy.deepcopy(original(repo, relative))
        if relative == value["source_archive_manifest"]:
            if fault == "member_hash":
                data["source_zip"]["members"][0]["sha256"] = "0" * 64
            elif fault == "member_missing":
                data["source_zip"]["members"].pop()
        if relative == value["zip_spec_crosswalk"]:
            if fault == "cross_loss":
                data["rows"].pop()
            elif fault == "cross_status":
                data["rows"][0]["implementation"] = "PASS"
            elif fault == "cross_task":
                data["rows"][0]["tasks"] = ["INVENTED"]
        return data
    monkeypatch.setattr(gate, "read_json", altered)
    assert gate.validate(ROOT,value)
