"""Local H01 source-preservation gate; never proves semantic or product qualification."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

PACK = "docs/taskpacks/aaos-ui-first-20261009"
POINTER = "docs/current/AAOS-ACTIVE-EXECUTION.json"
PROGRESS = "docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md"
TRACE = "docs/current/AAOS-H01-SOURCE-TRACE-20261009.json"
PRIVATE = {".codex", ".hermes", ".git", ".ssh", "sessions", "session", "memory", "memories", "credentials", "cookies"}


def owning_root(repo: Path) -> Path:
    if repo.parent.name == "worktrees" and repo.parent.parent.name == ".project-local":
        return repo.parent.parent.parent
    return repo


def safe_path(path: Path, root: Path) -> Path:
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    relative = path.relative_to(root)
    if ".." in relative.parts or any(p.casefold() in PRIVATE or p.casefold().startswith(".env") or ":" in p for p in relative.parts):
        raise ValueError("private/traversal source excluded")
    current = root
    for part in relative.parts:
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("reparse source excluded")
    return path


def byte_hash(path: Path, root: Path) -> str:
    return hashlib.sha256(safe_path(path, root).read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load(path: Path, root: Path) -> dict:
    return json.loads(safe_path(path, root).read_text(encoding="utf-8-sig"))


def csv_rows(path: Path, root: Path) -> list[dict]:
    with safe_path(path, root).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate(document: dict, repo: Path, source_root: Path | None = None) -> list[str]:
    """Compare projection against real immutable input rows, not copied fixture totals."""
    scope = source_root or owning_root(repo)
    if scope != owning_root(repo):
        raise ValueError("source-root must be the repository's project owning root")
    problems: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    require(document.get("schema") == "aaos.h01-source-trace/v1", "trace schema")
    require(document.get("role") == "DERIVED_SOURCE_TRACE_NOT_PROGRESS_DATABASE", "trace role")
    authority = document.get("current_authority", {})
    require(authority == {"pointer": POINTER, "active_taskpack": PACK, "active_progress": PROGRESS}, "current authority routing")
    pointer = load(repo / POINTER, scope)
    require(pointer.get("active_taskpack") == PACK and pointer.get("active_progress") == PROGRESS, "owner-selected pointer mismatch")
    for name in (PROGRESS, "docs/current/AAOS-GOVERNANCE-ALIGNMENT-20261009.md"):
        require(safe_path(repo / name, scope).is_file(), "existing execution/G01 reference: " + name)
    plan = repo / PACK
    old = load(plan / "OLD-TASK-DISPOSITION.json", scope)
    crosswalk = csv_rows(plan / "REQUIREMENT-CROSSWALK.csv", scope)
    detail = csv_rows(plan / "DESIGN-DETAIL-CROSSWALK.csv", scope)
    pages = csv_rows(plan / "PAGE-PLAN.csv", scope)
    tasks = load(plan / "TASKS.json", scope)
    task_ids = {row["id"] for row in tasks["tasks"]}
    register = load(plan / "SOURCE-REGISTER.json", scope)
    members = {row["member"]: row for row in register["extracted_members"]}
    original96 = members["AAOS_Final_Task_Package_20261009/04_需求与能力保留矩阵.csv"]
    raw96 = csv_rows(Path(original96["file"]), scope)
    require(byte_hash(Path(original96["file"]), scope) == original96["sha256"], "original96 source byte preservation")
    expected96 = {f"R{n:03}" for n in range(1, 50)} | {f"CAP-{n:04}" for n in range(10, 161, 10)} | {f"Q{n:02}" for n in range(16)} | {f"F{n:02}" for n in range(15)}
    require(len(raw96) == 96 and {row["包内追踪ID"] for row in raw96} == expected96, "original96 exact source identity coverage")
    by96 = {row["包内追踪ID"]: row for row in raw96}
    require(len(crosswalk) == 96 and {row["包内追踪ID"] for row in crosswalk} == expected96, "96 crosswalk source IDs")
    require(all(all(row.get(k) == v for k, v in by96.get(row["包内追踪ID"], {}).items()) for row in crosswalk), "96 original columns retained")
    original270 = next(row for row in register["snapshot"] if row["relative_path"] == "docs/current/AAOS-ALL-TASKS-LEDGER-20261001.json" and row["root"].endswith("gov-ui-20261008"))
    old_path = Path(original270["root"]) / original270["relative_path"]
    raw270 = load(old_path, scope)["task_rows"]
    require(len(raw270) == 270 and byte_hash(old_path, scope) == old["original_source_sha256"], "270 original source bytes/row coverage")
    by_old = {row["key"]: row for row in old["rows"]}
    require(len(by_old) == len(old["rows"]) == 330 and all(":" in key for key in by_old), "330 original namespaced keys")
    require(all(all(by_old.get(row["key"], {}).get(k) == v for k, v in row.items()) for row in raw270), "270 full original row fields preserved")
    source_rows = document.get("source_locators", [])
    by_trace = {row["source_locator_key"]: row for row in source_rows}
    expected_keys = set(by_old) | {"FINAL-20261009:" + key for key in expected96}
    require(len(by_trace) == len(source_rows) and set(by_trace) == expected_keys, "426 unique source-locator exact coverage")
    source_refs = {
        "old_disposition": (plan / "OLD-TASK-DISPOSITION.json", PACK + "/OLD-TASK-DISPOSITION.json"),
        "requirement_crosswalk": (plan / "REQUIREMENT-CROSSWALK.csv", PACK + "/REQUIREMENT-CROSSWALK.csv"),
        "page_plan": (plan / "PAGE-PLAN.csv", PACK + "/PAGE-PLAN.csv"),
        "design_crosswalk": (plan / "DESIGN-DETAIL-CROSSWALK.csv", PACK + "/DESIGN-DETAIL-CROSSWALK.csv"),
        "source_register": (plan / "SOURCE-REGISTER.json", PACK + "/SOURCE-REGISTER.json"),
    }
    for key, (path, relative) in source_refs.items():
        require(document.get("input_bindings", {}).get(key) == {"path": relative, "sha256": byte_hash(path, scope)}, "source binding: " + key)
    old_file_hash = byte_hash(plan / "OLD-TASK-DISPOSITION.json", scope)
    original270_keys = {row["key"] for row in raw270}
    for row in old["rows"]:
        projected = by_trace.get(row["key"], {})
        require(projected.get("source_namespace") == row["source"] and projected.get("original_source_id") == row["source_id"] and projected.get("title") == row["title"], "old namespace/source identity: " + row["key"])
        require(projected.get("source_row_sha256") == canonical_hash(row), "old source row hash: " + row["key"])
        require(projected.get("source_file_sha256") == old_file_hash, "old source file hash: " + row["key"])
        require(projected.get("source_file") == PACK + "/OLD-TASK-DISPOSITION.json", "old source locator path: " + row["key"])
        if row["key"] in original270_keys:
            require(projected.get("inherited_original_source_sha256") == old["original_source_sha256"], "270 inherited source hash: " + row["key"])
        require(projected.get("target_slices") == row["planning_targets"] and projected.get("disposition") == row["planning_disposition"] and projected.get("reason") == row["planning_reason"], "old destination/reason preservation: " + row["key"])
    for row in crosswalk:
        key = row["包内追踪ID"]
        projected = by_trace.get("FINAL-20261009:" + key, {})
        require(projected.get("source_namespace") == "FINAL-20261009" and projected.get("original_source_id") == key and projected.get("title") == row["主题"], "original96 namespace/source identity: " + key)
        require(projected.get("source_row_sha256") == canonical_hash(by96[key]), "original96 row hash: " + key)
        require(projected.get("source_file_sha256") == original96["sha256"], "original96 source file hash: " + key)
        require(projected.get("source_file") == original96["member"], "original96 source locator path: " + key)
        require(projected.get("crosswalk_row_sha256") == canonical_hash(row), "crosswalk row hash: " + key)
        require(projected.get("target_slices") == row["后续切片"].split(";") and projected.get("disposition") == row["本轮处理"] and bool(projected.get("reason")), "96 destination/reason: " + key)
    for row in source_rows:
        require(all(target in task_ids for target in row.get("target_slices", [])) and bool(row.get("target_slices")), "unknown target slice: " + row["source_locator_key"])
        require(row.get("independent_semantic_coverage") == "UNVERIFIED" and row.get("implementation_qualification") == "UNKNOWN", "source row false qualification: " + row["source_locator_key"])
        require(not any(key in row for key in ("progress", "completed", "execution_status")), "second progress database field")
    require(sorted(row["页面ID"] for row in pages) == [f"{n:02}" for n in range(1, 23)], "22 exact input page IDs")
    require(document.get("page_coverage") == [{"page_id": row["页面ID"], "target_slices": row["后续切片"].split(";"), "source_row_sha256": canonical_hash(row)} for row in pages], "22 original page-row projection")
    raw_design_source = members["AAOS_UI_Frontend_20261009/reference/capability-details.json"]
    raw_design = load(Path(raw_design_source["file"]), scope)
    require(byte_hash(Path(raw_design_source["file"]), scope) == raw_design_source["sha256"], "original186 source bytes")
    expected_design = {(f"CAP-{parent}", index): phrase for parent, phrases in raw_design.items() for index, phrase in enumerate(phrases, 1)}
    require(len(expected_design) == 186 and len(raw_design) == 16, "186/16 independent original design structure")
    require({(row["父CAP"], int(row["源内顺序"])): row["设计细项原文"] for row in detail} == expected_design, "186 original crosswalk text preservation")
    child_rows = document.get("design_source_signals", [])
    by_child = {(row["parent_cap"], row["source_order"]): row for row in child_rows}
    require(len(by_child) == len(child_rows) and set(by_child) == set(expected_design), "186 source-signal locator uniqueness/coverage")
    for key, phrase in expected_design.items():
        row = by_child.get(key, {})
        require(row.get("source_locator_key") == f"UI-DESIGN-20261009:{key[0]}:{key[1]:03}", "design namespaced source key: " + repr(key))
        require(row.get("design_text") == phrase and row.get("source_sha256") == raw_design_source["sha256"], "design source text/hash: " + repr(key))
        require(row.get("independent_semantic_coverage") == "UNVERIFIED" and row.get("implementation_qualification") == "UNKNOWN" and row.get("signal_qualification") == "EXACT_TEXT_MATCH_ONLY_NOT_SEMANTIC_COVERAGE", "design false qualification: " + repr(key))
    six = [row for row in members.values() if "/sources/" in row["member"] and "补齐" in row["member"]]
    six_trace = {row["member"]: row for row in document.get("independent_source_readback", [])}
    require(len(six) == len(six_trace) == 6 and set(six_trace) == {row["member"] for row in six}, "six independent source identity coverage")
    for row in six:
        actual = byte_hash(Path(row["file"]), scope)
        require(actual == row["sha256"] and six_trace.get(row["member"], {}).get("sha256") == actual, "six source byte preservation: " + row["member"])
        require(six_trace.get(row["member"], {}).get("registered_sha256") == row["sha256"] and six_trace.get(row["member"], {}).get("byte_hash_match") is True, "six registered hash/readback claim: " + row["member"])
    independent_texts: dict[str, str] = {}
    paragraphs: list[str] = []
    for row in six:
        path = safe_path(Path(row["file"]), scope)
        if path.suffix == ".md":
            independent_texts[row["member"]] = path.read_text(encoding="utf-8-sig")
        elif path.suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                xml = ET.fromstring(archive.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = ["".join(text.text or "" for text in p.findall(".//w:t", ns)) for p in xml.findall(".//w:body//w:p", ns)]
            independent_texts[row["member"]] = "\n".join(paragraphs)
    for key, phrase in expected_design.items():
        row = by_child.get(key, {})
        require(row.get("independent_exact_text_sources") == [name for name, text in independent_texts.items() if phrase in text], "independent lexical signal: " + repr(key))
        require(row.get("blueprint_paragraph_signals") == [f"P{n:04}" for n, text in enumerate(paragraphs, 1) if phrase in text], "independent paragraph signal: " + repr(key))
    raw97_source = next(row for row in six if "AAOS_SOURCE_BASELINE_97" in row["member"])
    raw97 = csv_rows(Path(raw97_source["file"]), scope)
    require(document.get("asset_read_scope", {}).get("source_member") == raw97_source["member"] and document.get("asset_read_scope", {}).get("source_sha256") == raw97_source["sha256"], "97 original source binding")
    require(len(raw97) == len({row["stable_id"] for row in raw97}) == 97, "97 original asset identities")
    require(document.get("asset_read_scope", {}).get("asset_identities") == [{"stable_id": row["stable_id"], "scope": row["scope"], "index": row["index"], "source_row_sha256": canonical_hash(row)} for row in raw97], "97 original identity-row preservation")
    require(document.get("asset_read_scope", {}).get("all97_original_bodies_verified") is False, "97 false body verification")
    qualification = document.get("qualification", {})
    require(qualification.get("semantic_audit") == "UNVERIFIED" and qualification.get("product_implementation") == "UNKNOWN", "trace false global qualification")
    require(not any(key in document for key in ("progress", "completed", "execution_status")), "second progress database root field")
    for evidence in document.get("evidence_references", []):
        require(evidence.get("publication") == "NOT_PUBLICLY_VERIFIED", "local artifact claimed public")
        if evidence.get("sha256"):
            require(evidence.get("resolution_root") == "PROJECT_OWNING_ROOT", "local evidence root")
            require(byte_hash(scope / evidence["path"], scope) == evidence["sha256"], "local evidence source hash: " + evidence["path"])
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--trace", type=Path)
    args = parser.parse_args()
    scope = args.source_root or owning_root(args.repo)
    try:
        if scope != owning_root(args.repo):
            raise ValueError("source-root cannot widen the project boundary")
        document = load(args.trace or args.repo / TRACE, scope)
        problems = validate(document, args.repo, scope)
    except (OSError, ValueError, KeyError, TypeError) as error:
        problems = ["source unavailable/unsafe or invalid trace: " + str(error)]
    print(json.dumps({"local_structure": "FAIL" if problems else "PASS", "semantic_audit": "UNVERIFIED", "product_implementation": "UNKNOWN", "errors": problems}, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
