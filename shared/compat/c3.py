"""Obsidian C3 semantic analysis for Markdown and JSON Canvas fixtures.

This module is deliberately a pure adapter: it reports source semantics and
losses without writing to the governed knowledge or machine-knowledge stores.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class VaultLink:
    target: str
    kind: str


@dataclass
class MarkdownC3Report:
    links: list[VaultLink] = field(default_factory=list)
    embeds: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    missing_links: list[str] = field(default_factory=list)
    missing_attachments: list[str] = field(default_factory=list)


@dataclass
class CanvasC3Report:
    valid: bool
    node_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


_WIKILINK_RE = re.compile(r"!?(?:\[\[)([^\]|]+)(?:\|[^\]]+)?\]\]")
_MARKDOWN_LINK_RE = re.compile(r"(!?)\[[^\]]*\]\(([^)]+)\)")
_TAG_RE = re.compile(r"(?<![\w#])#([A-Za-z0-9_][A-Za-z0-9_/-]*)")



def analyze_markdown(path: Path, *, vault_root: Path) -> MarkdownC3Report:
    """Extract C3 semantics and report missing local targets for one note."""
    root = vault_root.resolve()
    note = path.resolve()
    _inside(note, root)
    text = note.read_text(encoding="utf-8")
    report = MarkdownC3Report()

    for match in _WIKILINK_RE.finditer(text):
        target = match.group(1).strip()
        if not target:
            continue
        if match.group(0).startswith("!"):
            report.embeds.append(target)
            continue
        report.links.append(VaultLink(target=target, kind="wikilink"))
        if _is_missing_note(target, note, root):
            report.missing_links.append(target)

    for match in _MARKDOWN_LINK_RE.finditer(text):
        target = unquote(match.group(2).strip().split("#", 1)[0])
        if not target or _is_external(target):
            continue
        _local_target(target, note, root)
        if match.group(1):
            report.embeds.append(target)
            if not _exists_target(target, note, root):
                report.missing_attachments.append(target)
        else:
            report.links.append(VaultLink(target=target, kind="markdown"))
            if _is_missing_note(target, note, root):
                report.missing_links.append(target)

    for line in text.splitlines():
        stripped = line.strip()
        if (
            len(stripped) >= 7
            and stripped[0] in "-*"
            and stripped[2:6] in ("[ ] ", "[x] ", "[X] ")
        ):
            report.tasks.append(stripped[6:].strip())
        if re.match(r"^\s*#{1,6}\s", line):
            continue
        report.tags.extend(_TAG_RE.findall(line))

    for match in _WIKILINK_RE.finditer(text):
        if not match.group(0).startswith("!"):
            continue
        target = match.group(1).strip()
        _local_target(target, note, root)
        if not _exists_target(target, note, root):
            report.missing_attachments.append(target)

    report.tags = _unique(report.tags)
    report.missing_links = _unique(report.missing_links)
    report.missing_attachments = _unique(report.missing_attachments)
    return report


def analyze_canvas(path: Path) -> CanvasC3Report:
    """Validate the portable JSON Canvas v1 shape and graph references."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return CanvasC3Report(valid=False, errors=["invalid JSON"])
    if not isinstance(value, dict) or not isinstance(value.get("nodes"), list) or not isinstance(value.get("edges"), list):
        return CanvasC3Report(valid=False, errors=["canvas requires nodes and edges arrays"])

    errors: list[str] = []
    nodes = value["nodes"]
    edges = value["edges"]
    node_ids: list[str] = []
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not isinstance(node.get("type"), str):
            errors.append("node requires string id and type")
            continue
        if node["id"] in node_ids:
            errors.append(f"duplicate node id {node['id']}")
        node_ids.append(node["id"])
    edge_ids: list[str] = []
    for edge in edges:
        if not isinstance(edge, dict) or not isinstance(edge.get("id"), str):
            errors.append("edge requires string id")
            continue
        edge_ids.append(edge["id"])
        for endpoint in ("fromNode", "toNode"):
            target = edge.get(endpoint)
            if target not in node_ids:
                errors.append(f"edge {edge['id']} references missing node {target}")
    return CanvasC3Report(valid=not errors, node_ids=node_ids, edge_ids=edge_ids, errors=errors)


def canvas_semantic_diff(before: dict, after: dict) -> dict[str, list[str]]:
    """Compare canvas objects by IDs, independent of array ordering."""
    result: dict[str, list[str]] = {}
    for kind, id_key in (("nodes", "nodes"), ("edges", "edges")):
        old = {item.get("id"): item for item in before.get(kind, []) if isinstance(item, dict) and item.get("id")}
        new = {item.get("id"): item for item in after.get(kind, []) if isinstance(item, dict) and item.get("id")}
        result[f"added_{id_key}"] = sorted(set(new) - set(old))
        result[f"removed_{id_key}"] = sorted(set(old) - set(new))
        result[f"changed_{id_key}"] = sorted(key for key in set(old) & set(new) if old[key] != new[key])
    return result


def _inside(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes vault root: {path}") from exc


def _local_target(target: str, note: Path, root: Path) -> Path | None:
    if _is_external(target) or target.startswith("#"):
        return None
    candidate = (note.parent / target).resolve()
    _inside(candidate, root)
    return candidate


def _exists_target(target: str, note: Path, root: Path) -> bool:
    candidate = _local_target(target, note, root)
    if candidate is None:
        return True
    if candidate.exists():
        return True
    return any(item.name == candidate.name for item in root.rglob(candidate.name))


def _is_missing_note(target: str, note: Path, root: Path) -> bool:
    target = target.split("#", 1)[0].strip()
    if not target or _is_external(target):
        return False
    if target.startswith("^"):
        return False
    if "/" in target or "\\" in target or Path(target).suffix:
        return not _exists_target(target, note, root)
    return not any(item.stem == target for item in root.rglob("*.md"))


def _is_external(target: str) -> bool:
    return bool(urlparse(target).scheme) or target.startswith(("//", "mailto:"))


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
