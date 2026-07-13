"""Durable file-level processing ledger adapted from Obsidian-Assistance.

The ledger records every attempt in JSONL. Resume decisions use the latest attempt
per source; a historical success never hides a newer failure.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUCCESS_STATUSES = frozenset({"converted", "linked"})
VALID_STATUSES = frozenset({"converted", "linked", "failed", "needs_review"})


@dataclass(frozen=True)
class ProcessingRecord:
    source: str
    status: str
    handler: str
    output: str = ""
    error: str = ""
    processed_at: str = ""
    metadata: dict[str, Any] | None = None


def _clean_stem(value: str) -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*]+", "_", value).strip(" ._")
    return cleaned or "untitled"


def source_artifact_key(path: str | Path, source_root: str | Path) -> str:
    """Create a deterministic collision-resistant key from a relative source path."""
    source = Path(path).resolve()
    root = Path(source_root).resolve()
    try:
        relative = source.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"source is outside source_root: {source}") from exc
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
    return f"{_clean_stem(source.stem)[:80]}__{digest}"


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ProcessingManifest:
    """Append-only JSONL manifest with latest-state and resume helpers."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def record(
        self,
        source: str,
        *,
        status: str,
        handler: str,
        output: str = "",
        error: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ProcessingRecord:
        if status not in VALID_STATUSES:
            raise ValueError(f"unsupported processing status: {status}")
        item = ProcessingRecord(
            source=source.replace("\\", "/"),
            status=status,
            handler=handler,
            output=output.replace("\\", "/"),
            error=error,
            processed_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        return item

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        items: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("source"):
                items.append(item)
        return items

    def latest(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for item in self.records():
            latest[str(item["source"])] = item
        return latest

    def resumable_sources(self) -> set[str]:
        """Return success candidates; durable converters must also call ``can_resume``."""
        return {
            source
            for source, item in self.latest().items()
            if item.get("status") in SUCCESS_STATUSES
        }

    def can_resume(self, source: str, source_path: str | Path) -> bool:
        """Verify source and durable output fingerprints before skipping work."""
        normalized = source.replace("\\", "/")
        item = self.latest().get(normalized)
        if not item or item.get("status") not in SUCCESS_STATUSES:
            return False
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            return False
        source_file = Path(source_path)
        output = Path(str(item.get("output", "")))
        if not source_file.is_file() or not output.is_file():
            return False
        try:
            return (
                metadata.get("source_sha256") == file_sha256(source_file)
                and metadata.get("output_sha256") == file_sha256(output)
            )
        except OSError:
            return False

    def history(self, source: str) -> list[dict[str, Any]]:
        normalized = source.replace("\\", "/")
        return [item for item in self.records() if item.get("source") == normalized]

    def summary(self) -> dict[str, int]:
        counts = Counter(item.get("status", "unknown") for item in self.latest().values())
        result = {key: counts[key] for key in sorted(counts)}
        result["total"] = sum(counts.values())
        return result
