"""Pure Markdown quality audit adapted from Obsidian-Assistance governance checks."""

from __future__ import annotations

import re
from typing import Any

_MOJIBAKE = re.compile(
    r"(?:�|锟斤拷|烫烫烫|屯屯屯|Ã.|Â.|鐆|櫎|抴翍|閔窅|勝跀躌|遖窹|忲唡)"
)
_WATERMARK = re.compile(
    r"(?:瑞客论坛(?:\s*www\.ruike1\.com)?|爱给网|试读样张|请勿外传)", re.IGNORECASE
)
_MISLEADING = re.compile(r"(?:完成度|准确率|精确度)\s*[:：]\s*100%", re.IGNORECASE)
_WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")


def _wikilink_target(raw: str) -> str:
    return raw.split("|", 1)[0].split("#", 1)[0].strip().replace("\\", "/")


def audit_markdown_quality(
    text: str,
    known_targets: set[str] | None = None,
) -> dict[str, Any]:
    """Detect corruption, promotional watermarks, false 100% claims and broken links."""
    mojibake_hits = len(_MOJIBAKE.findall(text))
    watermark_hits = len(_WATERMARK.findall(text))
    misleading = len(_MISLEADING.findall(text))
    links = list(dict.fromkeys(_wikilink_target(item) for item in _WIKILINK.findall(text)))
    links = [link for link in links if link and not link.startswith(("http://", "https://"))]
    broken = []
    if known_targets is not None:
        normalized = {target.replace("\\", "/") for target in known_targets}
        stems = {target.rsplit("/", 1)[-1].removesuffix(".md") for target in normalized}
        for link in links:
            no_suffix = link.removesuffix(".md")
            if link not in normalized and no_suffix not in normalized and no_suffix.rsplit("/", 1)[-1] not in stems:
                broken.append(link)

    issue_count = mojibake_hits + watermark_hits + misleading + len(broken)
    return {
        "status": "needs_review" if issue_count else "clean_by_static_rules",
        "mojibake_hits": mojibake_hits,
        "watermark_hits": watermark_hits,
        "misleading_completion_claims": misleading,
        "wikilinks_checked": len(links),
        "broken_wikilinks": broken,
        "limitations": "static rules do not prove OCR/ASR accuracy or factual correctness",
    }
