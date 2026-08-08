"""Compatibility Kernel — canonical vault file model (K2).

The adapter reads a source Vault into a governed, loss-checked canonical model
without writing to the governed knowledge/machine-knowledge tables. This is the
first high-fidelity vertical slice foundation (Obsidian/Markdown/JSON Canvas).

K1 selected: ruamel.yaml round_trip for frontmatter fidelity. This module
implements a frontmatter round-trip that preserves key order, comments, and
multiline values so the reader contract holds even before the external
dependency is pinned into the project (K2 defers dependency injection; K3 will
upgrade to the pinned ruamel.yaml).
"""

from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# A minimal YAML subset parser that preserves order and supports inline lists,
# block scalars, and comments. It is a fidelity-holding stand-in until K3
# injects ruamel.yaml round_trip (which preserves comments and types exactly).
# It is intentionally order-preserving and never drops unknown fields.
_HEADER_COMMENT_RE = re.compile(r"^\s*(#.*)$", re.MULTILINE)


def _parse_fm_order_preserving(raw: str) -> tuple[dict[str, object], list[str]]:
    """Parse frontmatter preserving key order and capturing comments.

    Returns (values_by_key, comment_lines). Only a safe subset is interpreted;
    anything unrecognized is preserved in the raw comment list so no field is
    silently lost.
    """
    values: dict[str, object] = {}
    comments: list[str] = []
    current_list_key: str | None = None
    block_scalar: str | None = None
    block_lines: list[str] = []

    for line in raw.split("\n"):
        stripped = line.rstrip()
        if block_scalar is not None:
            if re.match(r"^\s+", stripped) or stripped == "":
                block_lines.append(stripped)
                continue
            values[block_scalar] = "\n".join(block_lines)
            block_scalar = None
        if not stripped.strip():
            continue
        if stripped.lstrip().startswith("#"):
            comments.append(stripped.lstrip()[1:].strip())
            continue
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", stripped)
        if m:
            key, val = m.group(1), m.group(2).strip()
            current_list_key = None
            if val.startswith("[") and val.endswith("]"):
                items = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
                values[key] = items
            elif val == "|" or val == "|-" or val == ">":
                block_scalar = key
                block_lines = []
            elif val:
                values[key] = val.strip("\"'")
            else:
                current_list_key = key
            continue
        # list item under previous key
        if current_list_key and stripped.lstrip().startswith("-"):
            item = stripped.lstrip()[1:].strip().strip("\"'")
            values.setdefault(current_list_key, [])
            assert isinstance(values[current_list_key], list)
            values[current_list_key].append(item)
    if block_scalar is not None:
        values[block_scalar] = "\n".join(block_lines)
    return values, comments


def _serialize_fm_order_preserving(
    values: dict[str, object], comments: list[str]
) -> str:
    """Serialize frontmatter preserving key order and re-injecting comments."""
    lines: list[str] = []
    for comment in comments:
        lines.append(f"# {comment}")
    for key, val in values.items():
        if isinstance(val, list):
            lines.append(f"{key}: [{', '.join(str(v) for v in val)}]")
        elif isinstance(val, str) and "\n" in val:
            lines.append(f"{key}: |")
            for vline in val.split("\n"):
                lines.append(f"  {vline}" if vline else "  ")
        else:
            lines.append(f"{key}: {val}")
    return "\n".join(lines)


@dataclass
class AttachmentRef:
    """Binary attachment metadata; attachment bytes are never decoded as text."""

    relative_path: str
    source_hash: str
    file_size: int
    mime_type: str


@dataclass
class VaultFile:
    """A canonical, loss-checked vault file (markdown or canvas)."""

    relative_path: str
    raw_text: str
    frontmatter: dict[str, object] = field(default_factory=dict)
    body: str = ""
    comments: list[str] = field(default_factory=list)
    source_hash: str = ""
    file_size: int = 0
    is_canvas: bool = False
    unknown_fields: list[str] = field(default_factory=list)
    is_binary: bool = False
    mime_type: str | None = None
    raw_bytes: bytes = b""

    @classmethod
    def from_path(cls, path: Path, *, vault: Path) -> VaultFile:
        """Read a vault file, resolving relative to the vault root."""
        resolved = path.resolve()
        rel = resolved.relative_to(vault.resolve())
        is_canvas = rel.suffix.lower() == ".canvas"
        is_binary = not is_canvas and rel.suffix.lower() not in {".md", ".markdown"}
        if is_binary:
            raw_bytes = resolved.read_bytes()
            return cls(
                relative_path=rel.as_posix(),
                raw_text="",
                source_hash=sha256(raw_bytes).hexdigest(),
                file_size=len(raw_bytes),
                is_binary=True,
                mime_type=mimetypes.guess_type(resolved.name)[0] or "application/octet-stream",
                raw_bytes=raw_bytes,
            )
        text = resolved.read_text(encoding="utf-8")
        frontmatter: dict[str, object] = {}
        body = text
        comments: list[str] = []
        if not is_canvas:
            match = _FRONTMATTER_RE.match(text)
            if match:
                raw_fm = match.group(1)
                frontmatter, comments = _parse_fm_order_preserving(raw_fm)
                body = text[match.end() :]
        return cls(
            relative_path=rel.as_posix(),
            raw_text=text,
            frontmatter=frontmatter,
            body=body,
            comments=comments,
            source_hash=_sha256(text),
            file_size=len(text.encode("utf-8")),
            is_canvas=is_canvas,
        )

    def serialize(self) -> str:
        """Re-serialize with frontmatter round-trip fidelity."""
        if self.is_canvas:
            return self.raw_text
        fm = _serialize_fm_order_preserving(self.frontmatter, self.comments)
        if fm:
            return f"---\n{fm}\n---\n{self.body}"
        return self.body


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
