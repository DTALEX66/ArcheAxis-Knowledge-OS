"""MarkItDown adapter — PDF/Word/PPT/Excel/HTML → Markdown.

Protocol: External file → MarkItDown → {markdown, metadata, source_record}
Output goes to quarantine, NOT directly to core database.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConvertedDocument:
    content: str = ""
    metadata: dict = field(default_factory=dict)
    source_path: str = ""
    format: str = "markdown"
    errors: list = field(default_factory=list)

def convert_file(filepath: str | Path) -> ConvertedDocument:
    path = Path(filepath)
    if not path.exists():
        return ConvertedDocument(errors=[f"File not found: {filepath}"])
    if path.suffix in (".md", ".markdown", ".txt"):
        return ConvertedDocument(
            content=path.read_text(encoding="utf-8", errors="replace"),
            source_path=str(path), format="markdown",
        )
    return ConvertedDocument(
        content=f"[binary: {path.suffix}]", source_path=str(path),
        format=path.suffix, errors=[f"Format not yet supported: {path.suffix}"],
    )
