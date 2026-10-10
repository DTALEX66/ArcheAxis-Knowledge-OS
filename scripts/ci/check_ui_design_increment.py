"""Verify archived UI-design input and its derived task/page overlay, not product maturity."""
from __future__ import annotations
import csv
import hashlib
import json
import re
import stat
import io
import zipfile
from pathlib import Path

OVERLAY = "docs/current/AAOS-UI-DESIGN-INCREMENT-20261010.json"
PRIVATE = {".git", ".codex", ".hermes", ".ssh", "sessions", "memory", "memories", "credentials", "cookies"}

def local_file(repo: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or path.drive or ".." in path.parts or any(
        part.casefold() in PRIVATE or part.casefold().startswith(".env") or ":" in part for part in path.parts
    ):
        raise ValueError("unsafe design source locator")
    current = repo
    for part in path.parts:
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("reparse design source excluded")
    if not current.is_file():
        raise ValueError("design source is not a file")
    return current

def read_json(repo: Path, relative: str) -> dict:
    return json.loads(local_file(repo, relative).read_text(encoding="utf-8-sig"))

def validate(repo: Path, document: dict) -> list[str]:
    errors: list[str] = []
    def require(test: bool, label: str) -> None:
        if not test:
            errors.append(label)
    try:
        require(document["schema"] == "aaos.ui-design-increment/v1", "design overlay schema")
        require(document["role"] == "DESIGN_REQUIREMENTS_OVERLAY_NOT_REPLACEMENT_TASKPACK", "source elevated into product authority")
        pointer = read_json(repo, "docs/current/AAOS-ACTIVE-EXECUTION.json")
        require(OVERLAY in pointer.get("design_overlays", []), "design overlay missing from active pointer")
        require(document["active_taskpack"] == pointer["active_taskpack"], "design overlay replaced selected taskpack")
        require(document["progress_record"] == pointer["active_progress"], "design overlay introduced second progress record")
        taskpack = read_json(repo, pointer["active_taskpack"] + "/TASKS.json")
        tasks = {row["id"] for row in taskpack["tasks"]}
        manifest = read_json(repo, document["source_archive_manifest"])
        require(document["sources"] == manifest["files"] and len(manifest["files"]) == 3, "archive identity/count drift")
        originals: dict[str, tuple[bytes, dict]] = {}
        for row in manifest["files"]:
            data = local_file(repo, row["archive_path"]).read_bytes()
            require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"], "archived source byte/hash drift")
            require(row["byte_preservation"] == "PASS", "archive unverified preservation")
            originals[Path(row["archive_path"]).name] = (data, row)
        text_name = "AAOS_UI_成熟落地深化方案_20261009.txt"
        checksum_name = "AAOS_UI_深化设计增量_SHA256_20261009.txt"
        text, row = originals[text_name]
        checksum = originals[checksum_name][0].decode("utf-8-sig")
        match = re.search(re.escape(text_name) + r"\s+bytes=(\d+)\s+SHA256=([0-9a-f]{64})", checksum)
        require(bool(match) and (int(match[1]), match[2]) == (len(text), row["sha256"]), "original checksum statement mismatch")
        zip_state = manifest["source_zip"]
        require(zip_state["actual_status"] == "PRESENT_HASH_VERIFIED" and zip_state["member_readback"] == "PASS", "supplied ZIP not verified")
        zip_data, zip_row = originals[zip_state["declared_filename"]]
        match = re.search(re.escape(zip_state["declared_filename"]) + r"\s+bytes=(\d+)\s+SHA256=([0-9a-f]{64})", checksum)
        require(bool(match) and (int(match[1]), match[2]) == (len(zip_data), zip_row["sha256"]), "ZIP checksum statement mismatch")
        require((len(zip_data),zip_row["sha256"]) == (zip_state["declared_bytes"],zip_state["declared_sha256"]), "ZIP declared identity mismatch")
        with zipfile.ZipFile(io.BytesIO(zip_data)) as archive:
            require(archive.testzip() is None, "ZIP CRC failure")
            members = zip_state["members"]
            require(len(members) == 10 and {r["zip_member"] for r in members} == set(archive.namelist()), "ZIP member coverage drift")
            payload = {}
            for member in members:
                raw = local_file(repo, member["archive_path"]).read_bytes()
                require(raw == archive.read(member["zip_member"]) and len(raw) == member["bytes"] and hashlib.sha256(raw).hexdigest() == member["sha256"], "ZIP member byte/hash drift")
                require(member["byte_preservation"] == "PASS", "ZIP member preservation unverified")
                payload[Path(member["archive_path"]).name] = raw
            sums = payload["SHA256SUMS.txt"].decode("utf-8-sig").splitlines()
            require(len(sums) == 9, "ZIP internal checksum coverage")
            for line in sums:
                digest, name = line.split("  ", 1)
                require(hashlib.sha256(payload[name]).hexdigest() == digest, "ZIP internal checksum mismatch")
            cross = read_json(repo,document["zip_spec_crosswalk"])
            require(cross["role"] == "SOURCE_REQUIREMENTS_MAPPING_NOT_PROGRESS_LEDGER" and len(cross["rows"]) == cross["source_records"] == 107, "ZIP specifications coverage/role")
            expected = []
            for member in members:
                if member["archive_path"].endswith(".csv"):
                    source_rows = list(csv.DictReader(io.StringIO(payload[Path(member["archive_path"]).name].decode("utf-8-sig"))))
                    require(len(source_rows) == member["csv_records"], "ZIP CSV count drift")
                    expected.extend((member["archive_path"],n,row) for n,row in enumerate(source_rows,1))
            require([(r["source"],r["csv_record"],r["source_fields"]) for r in cross["rows"]] == expected, "ZIP source rows lost or changed")
            for row in cross["rows"]:
                require(bool(row["tasks"]) and set(row["tasks"]) <= tasks, "ZIP source references unknown task")
                require(row["implementation"] == "NOT_QUALIFIED_BY_SOURCE", "ZIP design promoted into implementation")
        lines = text.decode("utf-8-sig").splitlines()
        rows = document["requirements"]
        require(len(rows) == 18 and len({row["topic"] for row in rows}) == 18, "design requirement coverage/uniqueness")
        for row in rows:
            number = row["source_line"]
            require(isinstance(number, int) and 1 <= number <= len(lines) and row["source_phrase"] in lines[number-1], "design source anchor drift")
            require(bool(row["tasks"]) and set(row["tasks"]) <= tasks, "design requirement references unknown task")
            require(row["implementation"] == "NOT_EXECUTED_BY_THIS_ANALYSIS", "analysis promoted to implementation PASS")
            require(all(row.get(key) for key in ("requirement", "acceptance", "current_readback")), "design requirement lacks acceptance/gap")
        with local_file(repo, pointer["active_taskpack"] + "/PAGE-PLAN.csv").open(encoding="utf-8-sig", newline="") as file:
            pages = {row["页面ID"]: row for row in csv.DictReader(file)}
        with local_file(repo, document["navigation_mapping"]).open(encoding="utf-8-sig", newline="") as file:
            mapped = list(csv.DictReader(file))
        require(len(mapped) == 22 and len({row["原页面ID"] for row in mapped}) == 22 and {row["原页面ID"] for row in mapped} == set(pages), "22 page mapping loss/duplicate")
        for row in mapped:
            old = pages.get(row["原页面ID"], {})
            for new_key, old_key in [("原页面名称", "页面名称"), ("原参考路由", "原参考路由"), ("原CAP映射", "CAP保留映射"), ("承接原切片", "后续切片")]:
                require(row[new_key] == old.get(old_key), "original page responsibility/identity drift")
            require(row["新主入口"] in {"工作台", "知识", "学习", "AI", "资源", "全部能力", "设置"}, "navigation proposal outside accepted grouping")
            require(row["现有深链接"] == "#page=" + row["原页面ID"], "existing deep link lost")
            require(row["迁移/旧行为核验"] == "NOT_EXECUTED_BY_THIS_ANALYSIS", "mapping promoted into route qualification")
        local_file(repo, document["analysis"])
        require(document["policy"]["v01"] == "PAUSED" and document["policy"]["ft01_ft04"] == "FROZEN", "design input revived frozen work")
    except (OSError, ValueError, TypeError, KeyError, IndexError, zipfile.BadZipFile) as error:
        errors.append("invalid/unavailable design input: " + str(error))
    return errors

def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    try:
        errors = validate(repo, read_json(repo, OVERLAY))
    except (OSError, ValueError, KeyError) as error:
        errors = [str(error)]
    print(json.dumps({"archive_and_overlay": "FAIL" if errors else "PASS", "product_implementation": "NOT_QUALIFIED_BY_THIS_GATE", "errors": errors}, ensure_ascii=False))
    return bool(errors)

if __name__ == "__main__":
    raise SystemExit(main())
