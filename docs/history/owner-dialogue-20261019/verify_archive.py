"""只读核对对话快照、来源路由和接续导航；结构通过不代表产品通过。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat


ARCHIVE = Path(__file__).resolve().parent
REPO = ARCHIVE.parents[2]
ARCHIVE_REF = "docs/history/owner-dialogue-20261019"


def confined(base: Path, reference: str) -> Path:
    """在读取前拒绝越界、盘符、回退段及重解析点。"""
    pure = PurePosixPath(reference)
    if pure.is_absolute() or ".." in pure.parts or ":" in reference or "\\" in reference:
        raise ValueError(f"不安全的归档引用：{reference}")
    path = base.joinpath(*pure.parts)
    for candidate in (path, *path.parents):
        if candidate == base:
            break
        if candidate.exists() and (
            candidate.is_symlink()
            or getattr(candidate.lstat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError(f"归档路径包含重解析点：{reference}")
    path.resolve().relative_to(base.resolve())
    return path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def identity(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def verify(require_local_attachments: bool) -> dict:
    manifest = load(ARCHIVE / "MANIFEST.json")
    entries = manifest["members"]
    expected = {entry["path"] for entry in entries}
    if len(expected) != len(entries):
        raise ValueError("冻结成员重复")
    actual = {
        path.relative_to(ARCHIVE).as_posix()
        for path in ARCHIVE.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
        and "__pycache__" not in path.parts
    }
    if actual != expected:
        raise ValueError(f"冻结成员集合变化：{actual ^ expected}")
    for entry in entries:
        path = confined(ARCHIVE, entry["path"])
        if identity(path) != (entry["bytes"], entry["sha256"]):
            raise ValueError(f"冻结成员身份不符：{entry['path']}")

    coverage = load(ARCHIVE / "decision-coverage.json")
    records = coverage["records"]
    identifiers = [record["id"] for record in records]
    if identifiers != [f"OD-{i:03d}" for i in range(1, 40)]:
        raise ValueError("39项来源ID不连续或存在遗漏")
    source_text = (ARCHIVE / "SOURCE-EXCERPTS.md").read_text(encoding="utf-8")
    references = set()
    for record in records:
        if record["source_kind"] not in {"HISTORICAL_CLAIM", "REQUEST", "CONTEXT", "DECISION", "QUESTION"}:
            raise ValueError(f"来源类型无效：{record['id']}")
        if record["execution_status"] != "RESOLVE_LIVE_PROGRESS_AND_RECEIPTS":
            raise ValueError("快照不能定义独立产品进度")
        if source_text.count(f"## {record['id']} ") != 1 or record["excerpt"] not in source_text:
            raise ValueError(f"来源摘录缺失或重复：{record['id']}")
        if not record["current_references"]:
            raise ValueError(f"缺少现行入口：{record['id']}")
        for reference in record["current_references"]:
            if not confined(REPO, reference).is_file():
                raise ValueError(f"现行入口缺失：{reference}")
            references.add(reference)

    active = load(REPO / "docs/current/AAOS-ACTIVE-EXECUTION.json")
    navigation = active["continuation_context"]["resource_navigation"]
    if navigation.get("owner_dialogue_archive") != ARCHIVE_REF + "/README.md":
        raise ValueError("活动指针缺少归档入口")
    if navigation.get("owner_dialogue_coverage") != ARCHIVE_REF + "/decision-coverage.json":
        raise ValueError("活动指针缺少逐项来源路由")
    if active["active_progress"] != coverage["current_progress_source"]:
        raise ValueError("快照路由与唯一进度入口不一致；需后继迁移说明")
    for reference in [
        "AGENTS.md", "AAOS-资料索引.md", "docs/DOCUMENTATION_AUTHORITY_INDEX.md",
        "docs/current/AAOS-AGENT-HANDOFF-CURRENT.md", coverage["current_decision_source"],
    ]:
        text = confined(REPO, reference).read_text(encoding="utf-8-sig")
        if "owner-dialogue-20261019/README.md" not in text:
            raise ValueError(f"接续入口未链接归档：{reference}")

    checked_attachments = 0
    if require_local_attachments:
        for entry in load(ARCHIVE / "attachments.json")["files"]:
            if entry["status"] != "PASS_BYTE_COPY":
                raise ValueError(f"附件未保全：{entry['name']}")
            path = confined(REPO, entry["archive"])
            if identity(path) != (entry["bytes"], entry["sha256"]):
                raise ValueError(f"本地附件身份不符：{entry['name']}")
            checked_attachments += 1
    return dict(
        status="PASS", evidence_level="STRUCTURAL_READBACK_NOT_PRODUCT_QUALIFICATION",
        frozen_members=len(entries), source_records=len(records),
        current_reference_targets=len(references), local_attachments_checked=checked_attachments,
        local_attachment_status="PASS" if require_local_attachments else "NOT_EXECUTED",
        product_status="PARTIAL", full_private_transcript="UNVERIFIED",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-local-attachments", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.require_local_attachments), ensure_ascii=False, indent=2))
