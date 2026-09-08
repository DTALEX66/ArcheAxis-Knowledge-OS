#!/usr/bin/env python3
"""Read-only task-package validation. Python 3.9+, standard library only.
No product execution, downloads, authorization changes, or filesystem writes.
Hashes detect damage relative to this manifest; they are not a digital signature.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

PLAN = "AAK-FOLLOWUP-20260908-R3"
BASE = "cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed"
IDS = {f"X{i:02d}" for i in range(15)} | {"Q00", "Q01"} | {f"F{i:02d}" for i in range(1, 7)}

def demand(condition, message):
    if not condition:
        raise ValueError(message)

def read_json(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))

def refs_ok(value, ids):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "mapped_tasks":
                demand(isinstance(item, list) and item and set(item) <= ids, "invalid mapped_tasks")
            refs_ok(item, ids)
    elif isinstance(value, list):
        for item in value:
            refs_ok(item, ids)

def validate(root):
    demand(root.is_dir(), "package root not found")
    demand(not root.is_symlink(), "package root cannot be a symlink")
    manifest = read_json(root, "MANIFEST.json")
    demand(manifest["plan_id"] == PLAN, "manifest plan mismatch")
    entries = manifest["files"]
    demand(entries and len({x["path"] for x in entries}) == len(entries), "manifest duplicate/empty")
    seen = set()
    for entry in entries:
        name = entry["path"]
        p = PurePosixPath(name)
        demand(not p.is_absolute() and ".." not in p.parts and "\\" not in name and ":" not in name,
               "unsafe manifest path")
        demand(name not in {"", ".", "MANIFEST.json"} and str(p) == name, "invalid manifest path")
        target = root / name
        demand(all(not q.is_symlink() for q in [target, *target.parents] if q != root.parent),
               "symlink not allowed")
        demand(target.is_file(), f"missing file: {name}")
        data = target.read_bytes()
        demand(len(data) == entry["bytes"], f"size mismatch: {name}")
        demand(hashlib.sha256(data).hexdigest() == entry["sha256"], f"hash mismatch: {name}")
        data.decode("utf-8")  # This package consists only of UTF-8 text.
        seen.add(name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    demand(actual == seen | {"MANIFEST.json"}, "unlisted or missing package files")
    for path in root.rglob("*"):
        demand(not path.is_symlink(), "symlink in package")

    plan = read_json(root, "TASKS.json")
    old = read_json(root, "frozen-r2/TASKS.json")
    demand(plan["plan_id"] == PLAN and plan["audit_base_sha"] == BASE, "plan identity mismatch")
    demand(plan["original_plan_audit_base_sha"] == old["audit_base_sha"], "lost original baseline")
    demand(plan["previous_plan_id"] == old["plan_id"], "lost original plan")
    demand(plan["plan_only"] is True and plan["issued_authorization"] is False, "planning boundary changed")
    demand(plan["product_implemented_in_this_turn"] is False, "false product claim")
    demand(plan["automatic_future_activation"] is False, "future activation prohibited")
    demand(plan["decisions"] == old["decisions"], "historical decision text changed")
    tasks = plan["tasks"]
    demand(len(tasks) == 23 and {t["id"] for t in tasks} == IDS, "task IDs/count mismatch")
    by_id = {t["id"]: t for t in tasks}
    old_by_id = {t["id"]: t for t in old["tasks"]}
    for task_id, t in by_id.items():
        source = old_by_id[task_id]
        for key, val in source.items():
            if key == "status":
                demand(t["original_status"] == val, f"{task_id}: lost old status")
            else:
                demand(t[key] == val, f"{task_id}: changed inherited {key}")
        demand(t["r3_work"] and t["r3_acceptance"], f"{task_id}: missing R3 work/acceptance")
        demand(t["implementation_completed_in_this_package"] is False and
               t["product_completion_claimed"] is False, "false implementation claim")
        demand(set(t["depends_on"]) <= IDS, "unknown dependency")
        if task_id.startswith("F"):
            demand(t["status"] == "DEFERRED_RETAINED", "future not frozen")
        else:
            demand(t["status"] not in {"DONE", "VERIFIED", "PASS"}, "unearned task completion")
    active, done = set(), set()
    def visit(task_id):
        demand(task_id not in active, "dependency cycle")
        if task_id in done:
            return
        active.add(task_id)
        for dep in by_id[task_id]["depends_on"]:
            visit(dep)
        active.remove(task_id)
        done.add(task_id)
    for task_id in by_id:
        visit(task_id)

    features = read_json(root, "FUNCTIONS.json")
    demand(features["plan_id"] == PLAN, "feature plan mismatch")
    fs = features["features"]
    demand(len(fs) == 29 and {f["id"] for f in fs} == {f"CF{i:02d}" for i in range(1, 30)},
           "feature IDs/count mismatch")
    refs_ok(features, IDS)
    required = ["name", "delivery_scope", "user_action", "input", "visible_output",
                "retained_records", "acceptance", "acceptance_case_ids"]
    for f in fs:
        demand(all(f.get(k) for k in required), "incomplete concrete feature")
        demand(f["implementation_claimed"] is False, "false feature implementation claim")
    cases = read_json(root, "ACCEPTANCE.json")
    demand(cases["plan_id"] == PLAN, "acceptance plan mismatch")
    scenarios = cases["scenarios"]
    case_ids = {s["id"] for s in scenarios}
    demand(len(scenarios) == len(case_ids) == 26, "scenario IDs/count mismatch")
    gates = set()
    for s in scenarios:
        demand(s["fixture"] and s["procedure"] and s["expected"], "incomplete scenario")
        demand(s["result"] == "NOT_RUN_IN_THIS_PACKAGE", "fabricated run")
        demand(set(s["gates"]) <= {f"G{i:02d}" for i in range(1,15)}, "unknown gate")
        gates.update(s["gates"])
    demand(gates == {f"G{i:02d}" for i in range(1,15)}, "gate coverage incomplete")
    for item in tasks + fs:
        demand(set(item["acceptance_case_ids"]) <= case_ids, "unknown acceptance reference")
    demand({c for t in tasks for c in t["audit_links"]} == {f"C{i:02d}" for i in range(1,11)},
           "C01-C10 mapping incomplete")

    for filename, key, count in [
        ("BLUEPRINT-COVERAGE.json", "capabilities", 16),
        ("FORMAT-COVERAGE.json", "formats", 16),
        ("ENHANCEMENT-COVERAGE.json", "items", 11),
    ]:
        current = read_json(root, filename)
        source = read_json(root, "frozen-r2/" + filename)
        demand(current["plan_id"] == PLAN, "coverage plan mismatch")
        demand(len(current[key]) == count, "coverage count mismatch")
        for k, v in source.items():
            if k not in {"plan_id", "source_file"}:
                demand(current[k] == v, f"lost retained coverage: {filename}:{k}")
        refs_ok(current, IDS)
    enhancement = read_json(root, "ENHANCEMENT-COVERAGE.json")
    source_bytes = (root / enhancement["source_file"]).read_bytes()
    demand(hashlib.sha256(source_bytes).hexdigest() == enhancement["source_sha256"],
           "enhancement source hash mismatch")
    for f in ["EXECUTOR-START.md", "TASKPACK.md", "CORE-FUNCTIONS.md", "AUDIT-DELTA.md",
              "ACCEPTANCE.md", "LIBRARY-ADOPTION.md", "LIBRARY-INTEGRATION-REFERENCE.md",
              "EXECUTION-TEMPLATE.md", "SOURCE-PROVENANCE.json", "VALIDATION.md",
              "frozen-r2/INDEPENDENT-AUDIT.md"]:
        demand(f in seen, f"missing required companion: {f}")
    demand(plan["package_revision"] == "R3.1", "missing governance revision")
    gov = read_json(root, plan["governance_migration_spec"])
    demand(gov["plan_id"] == PLAN and gov["package_revision"] == "R3.1", "governance identity mismatch")
    expected_gov = {f"GOV{i:02d}" for i in range(1, 6)} | {f"LANG{i:02d}" for i in range(1, 8)}
    demand(len(gov["slices"]) == 12 and {s["id"] for s in gov["slices"]} == expected_gov,
           "governance/migration slices lost")
    refs_ok(gov, IDS)
    for s in gov["slices"]:
        demand(all(s.get(k) for k in ["phase", "work", "deliverable", "acceptance"]),
               "incomplete governance slice")
        demand(s["status"] == "PLANNED_NOT_IMPLEMENTED", "false migration completion")
        demand(set(s["acceptance_case_ids"]) <= case_ids, "unknown governance acceptance case")
    for t in tasks:
        expected = [s["id"] for s in gov["slices"] if t["id"] in s["mapped_tasks"]]
        demand(t["governance_migration_slices"] == expected, "governance binding mismatch")
    demand("GOVERNANCE-MIGRATION.md" in seen, "missing governance guide")
    prov = read_json(root, "SOURCE-PROVENANCE.json")
    demand(prov["audited_sha"] == BASE, "provenance base mismatch")
    for item in prov["packaged_sources"]:
        data = (root / item["path"]).read_bytes()
        demand(hashlib.sha256(data).hexdigest() == item["sha256"], "source provenance mismatch")
    return {"result": "PASS", "tasks": len(tasks), "features": len(fs), "scenarios": len(scenarios),
            "capabilities": 16, "format_groups": 16, "enhancements": 11, "gates": 14,
            "governance_migration_slices": 12,
            "packaged_files": len(actual), "product_tests_run": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        result = validate(args.root.absolute())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Task-package integrity only; not a product audit or implementation claim.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
