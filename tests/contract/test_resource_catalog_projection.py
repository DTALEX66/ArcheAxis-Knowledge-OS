import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("resource_projection", ROOT / "scripts/contracts/generate_resource_catalog.py")
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


def test_lossless_original_surface_overlay_ledger_and_all_conflicts():
    result = projection.build(ROOT)
    original = json.loads((ROOT / projection.CROSSWALK).read_bytes())
    overlay = json.loads((ROOT / projection.QUALIFICATION).read_bytes())
    assert [row["original_surface"] for row in result["entries"]] == original["entries"]
    assert {row["stable_key"]: row["qualification"] for row in result["entries"]} == {row["stable_key"]: row for row in overlay["entries"]}
    assert len(result["entries"]) == 68
    assert sum(len(row["original_surface"]["conflicts"]) for row in result["entries"]) == 115
    for source in result["sources"]:
        assert hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    assert projection.generate(result) == (ROOT / projection.TARGET).read_text(encoding="utf-8")


def fixture_root(tmp_path):
    for name in [projection.CROSSWALK, projection.QUALIFICATION, projection.LEDGER, projection.FREEZE]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    # Copy only actual public reference bytes; normalize the fixture's pointers to
    # those exact bytes, so production stale-pointer failures stay independent.
    path = tmp_path / projection.QUALIFICATION
    qualification = json.loads(path.read_bytes())
    for ref in projection.qualification_source_refs(qualification):
        source = projection.public_source_path(ROOT, ref["path"])
        target = tmp_path / ref["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        target.write_bytes(raw)
        ref["sha256"] = hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(qualification, ensure_ascii=False), encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("kind", ["duplicate", "missing", "unexpected"])
def test_refuses_overlay_coverage_drift(tmp_path, kind):
    root = fixture_root(tmp_path)
    path = root / projection.QUALIFICATION
    data = json.loads(path.read_bytes())
    if kind == "duplicate":
        data["entries"].append(copy.deepcopy(data["entries"][0]))
    elif kind == "missing":
        data["entries"].pop()
    else:
        data["entries"][0]["stable_key"] = "not_a_donor"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly once"):
        projection.build(root)


def test_refuses_original_conflict_loss_or_qualification_without_value(tmp_path):
    root = fixture_root(tmp_path)
    path = root / projection.CROSSWALK
    data = json.loads(path.read_bytes())
    next(row for row in data["entries"] if row["conflicts"])["conflicts"].pop()
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="115 conflicts"):
        projection.build(root)
    path.write_bytes((ROOT / projection.CROSSWALK).read_bytes())
    path = root / projection.QUALIFICATION
    data = json.loads(path.read_bytes())
    del data["entries"][0]["evidence"]["license"]["value"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="silently dropped"):
        projection.build(root)


@pytest.mark.parametrize("location", ["top", "nested"])
def test_refuses_stale_qualification_source_pointer(tmp_path, location):
    root = fixture_root(tmp_path)
    path = root / projection.QUALIFICATION
    data = json.loads(path.read_bytes())
    ref = data["sources"][0] if location == "top" else data["entries"][0]["evidence"]["version"]["source_refs"][0]
    ref["sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Qualification source drift"):
        projection.build(root)


def test_refuses_missing_public_source(tmp_path):
    root = fixture_root(tmp_path)
    data = json.loads((root / projection.QUALIFICATION).read_bytes())
    ref = next(ref for ref in projection.qualification_source_refs(data)
               if ref["path"] not in {projection.CROSSWALK, projection.QUALIFICATION, projection.LEDGER, projection.FREEZE})
    (root / ref["path"]).unlink()
    with pytest.raises(ValueError, match="Qualification source missing"):
        projection.build(root)


@pytest.mark.parametrize("name", ["/tmp/file", "C:/private/file", "docs/../LICENSE", ".env", "docs/.codex/session.json", "docs/private/a.json", "docs/secrets.pem", "docs\\private.json"])
def test_refuses_non_public_source_before_read(tmp_path, name):
    root = fixture_root(tmp_path)
    path = root / projection.QUALIFICATION
    data = json.loads(path.read_bytes())
    data["sources"][0]["path"] = name
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="public project-relative"):
        projection.build(root)
