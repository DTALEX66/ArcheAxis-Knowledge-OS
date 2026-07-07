"""Obsidian vault importer — bidirectional bridge: Obsidian ↔ Cognitive-OS KB.

Scans an Obsidian vault directory, discovers notes by folder/type,
parses YAML frontmatter, and imports them as KB documents, cards,
context packs, or machine knowledge units.

Safety: defaults to dry_run=True. All write operations respect the
project boundary (no E: writes without explicit vault_root).

Usage:
    from shared.obsidian_importer import scan_vault, import_vault

    inventory = scan_vault("/path/to/vault")
    report = import_vault("/path/to/vault", dry_run=True)
"""

from __future__ import annotations

import re
import sys
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "Knowledge-Base"))

# ── Vault folder → KB asset type mapping ────────────────

VAULT_FOLDER_MAP: dict[str, dict[str, str]] = {
    "02_课程库": {"asset_type": "document", "source_tag": "obsidian-course"},
    "03_知识卡片": {"asset_type": "card", "source_tag": "obsidian-card"},
    "04_复习卡片": {"asset_type": "card", "source_tag": "obsidian-review"},
    "50_领域知识": {"asset_type": "machine_knowledge", "source_tag": "obsidian-domain"},
    "80_索引数据库": {"asset_type": "document", "source_tag": "obsidian-index"},
}

# Frontmatter field → KB field mapping
FRONTMATTER_MAP: dict[str, str] = {
    "title": "title",
    "type": "kb_type",
    "course": "source_topic",
    "tags": "tags",
    "review_status": "review_status",
    "created": "created_at",
    "updated": "updated_at",
}


# ── Scanner ─────────────────────────────────────────────


def scan_vault(vault_root: str, max_files: int = 500) -> dict[str, Any]:
    """Scan an Obsidian vault and return a categorized inventory.

    Does NOT read file contents — just discovers structure.
    """
    root = Path(vault_root)
    if not root.exists():
        return {"error": f"vault not found: {vault_root}"}

    inventory: dict[str, list[dict]] = {
        "courses": [],
        "cards": [],
        "domain_knowledge": [],
        "indexes": [],
        "other": [],
        "total_files": 0,
    }

    count = 0
    for md_file in root.rglob("*.md"):
        if count >= max_files:
            break
        # Skip .obsidian, .trash, templates
        rel = md_file.relative_to(root)
        if any(p.startswith(".") for p in rel.parts):
            continue
        if "90_模板" in str(rel):
            continue
        if "93_导入报告" in str(rel):
            continue

        info = {
            "path": str(rel),
            "name": md_file.stem,
            "size": md_file.stat().st_size if md_file.exists() else 0,
        }

        # Classify by parent folder
        folder = rel.parts[0] if len(rel.parts) > 1 else ""
        if folder == "02_课程库":
            course_name = rel.parts[1] if len(rel.parts) > 2 else ""
            info["course"] = course_name
            inventory["courses"].append(info)
        elif folder == "03_知识卡片":
            inventory["cards"].append(info)
        elif folder == "50_领域知识":
            inventory["domain_knowledge"].append(info)
        elif folder in ("80_索引数据库", "04_复习卡片"):
            inventory["indexes"].append(info)
        else:
            inventory["other"].append(info)

        count += 1

    inventory["total_files"] = count
    return inventory


# ── Frontmatter parser ──────────────────────────────────


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown text.

    Returns (frontmatter_dict, body_text).
    """
    fm: dict[str, Any] = {}
    body = text

    # Match YAML frontmatter: ---\n...\n---
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return fm, text

    raw_fm = match.group(1)
    body = text[match.end() :]

    # Simple YAML-like parser (tags, lists, key: value)
    for line in raw_fm.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # tags: [tag1, tag2] or tags:\n  - tag1
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()

            if val.startswith("[") and val.endswith("]"):
                # List syntax: [a, b, c]
                items = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
                fm[key] = items
            elif val:
                fm[key] = val.strip("\"'")

    return fm, body


# ── Importer ────────────────────────────────────────────


def import_file(
    vault_root: str,
    rel_path: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Import a single Obsidian note into KB.

    Returns:
        Dict with status, asset_type, kb_id (if not dry_run).
    """
    full_path = Path(vault_root) / rel_path
    if not full_path.exists():
        return {"error": "file not found", "path": str(rel_path)}

    text = full_path.read_text(encoding="utf-8", errors="replace")
    fm, body = _parse_frontmatter(text)
    folder = Path(rel_path).parts[0] if "/" in rel_path or "\\" in rel_path else ""
    mapping = VAULT_FOLDER_MAP.get(
        folder, {"asset_type": "document", "source_tag": "obsidian-note"}
    )

    asset_type = mapping["asset_type"]
    title = fm.get("title") or full_path.stem
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tags.append(mapping["source_tag"])

    result = {
        "path": str(rel_path),
        "asset_type": asset_type,
        "title": title,
        "frontmatter": fm,
        "body_length": len(body),
        "dry_run": dry_run,
    }

    if dry_run:
        result["status"] = "dry_run"
        result["preview"] = body[:300]
        return result

    # ── Actually import ──
    import uuid

    from shared.storage import fts5_sync, insert

    now = datetime.now(timezone.utc).isoformat()

    if asset_type == "card":
        kb_id = f"card_{uuid.uuid4().hex[:12]}"
        card = {
            "id": kb_id,
            "title": title,
            "content": body[:5000],
            "source_ids": [str(rel_path)],
            "tags": tags,
            "review_status": fm.get("review_status", "draft"),
            "created_at": now,
        }
        insert("kb_cards", card)
        with suppress(Exception):
            fts5_sync("kb_cards", {"id": kb_id, "title": title, "content": body[:5000]})
        result["kb_id"] = kb_id

    elif asset_type == "machine_knowledge":
        kb_id = f"mku_{uuid.uuid4().hex[:12]}"
        unit = {
            "id": kb_id,
            "title": title,
            "content": body[:5000],
            "unit_type": "rule",
            "tags": tags,
            "confidence": 0.7,
            "source_type": "obsidian",
            "source_id": str(rel_path),
            "active": 1,
            "created_at": now,
            "updated_at": now,
        }
        insert("machine_knowledge_units", unit)
        result["kb_id"] = kb_id

    else:
        # Default: import as document
        kb_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc = {
            "id": kb_id,
            "title": title,
            "content": body[:10000],
            "source": f"obsidian:{rel_path}",
            "tags": tags,
            "created_at": now,
        }
        insert("kb_documents", doc)
        with suppress(Exception):
            fts5_sync("kb_documents", {"id": kb_id, "title": title, "content": body[:10000]})
        result["kb_id"] = kb_id

    result["status"] = "imported"
    return result


def import_vault(
    vault_root: str,
    folders: list[str] | None = None,
    max_files: int = 100,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Batch-import notes from an Obsidian vault.

    Args:
        vault_root: absolute path to the vault root.
        folders: which top-level folders to import (default: all mapped).
        max_files: safety cap.
        dry_run: if True, preview only.

    Returns:
        Report with items and summary counts.
    """
    if folders is None:
        folders = list(VAULT_FOLDER_MAP)

    inventory = scan_vault(vault_root, max_files=max_files)
    if "error" in inventory:
        return inventory

    report = {
        "vault": vault_root,
        "dry_run": dry_run,
        "items": [],
        "summary": {
            "imported": 0,
            "skipped": 0,
            "errors": 0,
            "total_scanned": inventory["total_files"],
        },
    }

    # Collect files from requested folders
    candidates: list[dict] = []
    for cat in ["courses", "cards", "domain_knowledge", "indexes"]:
        for entry in inventory.get(cat, []):
            folder = Path(entry["path"]).parts[0]
            if folder in folders:
                candidates.append(entry)

    # Also include top-level .md files (like dashboard)
    for entry in inventory.get("other", []):
        if "00_主页" in entry["path"] or len(Path(entry["path"]).parts) == 1:
            candidates.append(entry)

    # Import each
    for i, entry in enumerate(candidates):
        if i >= max_files:
            break
        result = import_file(vault_root, entry["path"], dry_run=dry_run)
        report["items"].append(result)
        if result.get("status") == "imported":
            report["summary"]["imported"] += 1
        elif "error" in result:
            report["summary"]["errors"] += 1

    report["summary"]["skipped"] = (
        report["summary"]["total_scanned"] - report["summary"]["imported"]
    )
    return report


def import_course_to_cards(
    vault_root: str,
    course_path: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Import a single Obsidian course folder as KB cards.

    Reads all .md files in the course folder, splits long files
    by headings, and creates knowledge cards.
    """
    course_dir = Path(vault_root) / course_path
    if not course_dir.exists():
        return {"error": f"course not found: {course_path}"}

    from Knowledge_Base.cards.generator import generate_from_markdown

    from shared.storage import fts5_sync, insert

    results = []
    for md_file in sorted(course_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        _fm, body = _parse_frontmatter(text)

        cards = generate_from_markdown(body, source_doc_id=str(md_file), max_cards=5)

        for card in cards:
            if dry_run:
                results.append({"title": card.title, "preview": card.content[:200]})
            else:
                cd = card.to_dict()
                cd["id"] = cd.pop("card_id")
                insert("kb_cards", cd)
                with suppress(Exception):
                    fts5_sync(
                        "kb_cards", {"id": cd["id"], "title": card.title, "content": card.content}
                    )
                results.append({"title": card.title, "kb_id": cd["id"]})

    return {
        "course": course_path,
        "file_count": len(list(course_dir.glob("*.md"))),
        "cards_generated": len(results),
        "dry_run": dry_run,
        "items": results[:20],
    }
