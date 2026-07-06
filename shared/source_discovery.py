"""Source discovery assistant — adapted from Obsidian-Assistance v6.

Scans local directories for evidence sources (PDF, video, images, slides)
and generates a structured discovery report for KB ingestion.

Adapted from: scripts/v6/source_discovery_assistant.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

SOURCE_EXTENSIONS: dict[str, str] = {
    ".pdf": "pdf", ".mp4": "video", ".mov": "video", ".mkv": "video",
    ".avi": "video", ".webm": "video",
    ".ppt": "slides", ".pptx": "slides", ".key": "slides",
    ".doc": "document", ".docx": "document",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".flac": "audio",
    ".csv": "data", ".json": "data", ".xml": "data",
}
SKIP_DIRS: set[str] = {".git", "__pycache__", "node_modules", ".obsidian", "venv", "outputs"}


def discover_sources(
    root_dir: str,
    max_files: int = 200,
    size_threshold_mb: float = 500,
) -> dict[str, Any]:
    """Scan a directory tree for evidence source files.

    Args:
        root_dir: root directory to scan.
        max_files: max files to report.
        size_threshold_mb: skip files larger than this.

    Returns:
        {root, total_found, by_type: {pdf: N, video: N, ...}, files: [...]}.
    """
    root = Path(root_dir)
    if not root.exists():
        return {"error": f"directory not found: {root_dir}"}

    by_type: dict[str, list[dict]] = {}
    total = 0

    for fpath in root.rglob("*"):
        if total >= max_files:
            break
        # Skip hidden and excluded dirs
        if any(p.startswith(".") for p in fpath.parts):
            continue
        if any(d in SKIP_DIRS for d in fpath.parts):
            continue
        if not fpath.is_file():
            continue

        ext = fpath.suffix.lower()
        if ext not in SOURCE_EXTENSIONS:
            continue

        size_mb = fpath.stat().st_size / (1024 * 1024)
        if size_mb > size_threshold_mb:
            continue

        stype = SOURCE_EXTENSIONS[ext]
        if stype not in by_type:
            by_type[stype] = []

        by_type[stype].append({
            "path": str(fpath),
            "name": fpath.name,
            "size_mb": round(size_mb, 2),
            "type": stype,
        })
        total += 1

    return {
        "root": str(root),
        "total_found": total,
        "by_type": {k: len(v) for k, v in by_type.items()},
        "files": [
            {"type": stype, "path": f["path"], "size_mb": f["size_mb"]}
            for files in by_type.values()
            for f in files[:5]
        ][:50],
    }


def match_sources_to_cards(
    source_dir: str,
) -> dict[str, Any]:
    """Try to match discovered sources to existing KB cards by filename.

    Returns:
        {matched: [{card_title, source_path, confidence}], unmatched: [...]}.
    """
    from shared.storage import select_all

    discovery = discover_sources(source_dir, max_files=100)
    cards = select_all("kb_cards", limit=500)

    matched = []
    unmatched = []

    for files in discovery.get("by_type", {}):
        for fitem in discovery.get("files", []):
            fname = Path(fitem["path"]).stem.lower()
            found = False
            for card in cards:
                title = (card.get("title", "")).lower()
                # Simple fuzzy match
                if fname[:10] in title or title[:10] in fname:
                    matched.append({
                        "card_id": card.get("id") or card.get("card_id"),
                        "card_title": card.get("title", ""),
                        "source_path": fitem["path"],
                        "confidence": "medium",
                    })
                    found = True
                    break
            if not found:
                unmatched.append(fitem)

    return {
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "matched": matched[:20],
        "unmatched": unmatched[:20],
    }
