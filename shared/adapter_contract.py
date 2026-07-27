"""Adapter capability contract — typed contract for document/webpage/media adapters.

Separates declared capability from runtime availability. Every adapter has an
AdapterCapability record that classifies it into: installed, importable-but-not-wired,
fallback-only, or explicitly unavailable.

Usage:
    from shared.adapter_contract import (
        AdapterKind, AdapterStatus, AdapterCapability,
        AdapterInput, AdapterResult,
        get_adapter_registry, register_adapter,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Enums ──


class AdapterKind(str, Enum):
    """Broad category of adapter capability."""

    DOCUMENT = "document"  # PDF, DOCX, PPTX, XLSX, CSV
    WEBPAGE = "webpage"  # HTML, URL fetch
    MEDIA_VIDEO = "media_video"  # Video keyframe extraction
    MEDIA_AUDIO = "media_audio"  # Audio track extraction
    OCR = "ocr"  # Image text extraction
    YOUTUBE = "youtube"  # YouTube transcript fetch
    PLAINTEXT = "plaintext"  # TXT, MD passthrough
    IMAGE = "image"  # Image metadata / processing


class AdapterStatus(str, Enum):
    """Runtime status of an adapter capability.

    installed    — the engine binary/library is present and has been exercised.
    importable   — the Python module exists on PYTHONPATH but has not been
                   wired into the product's adapter chain.
    fallback     — only a placeholder handler exists (returns error or defaults).
    unavailable  — the engine is not installed and no fallback is provided.
    """

    INSTALLED = "installed"
    IMPORTABLE = "importable"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"


# ── Contract dataclasses ──


@dataclass(frozen=True)
class AdapterCapability:
    """Canonical description of one adapter engine capability.

    Fields:
        kind: broad category (document, webpage, media_video, …).
        format: specific format key (pdf, docx, html, mp4, …).
        engine: engine name (markitdown, ffmpeg, tesseract, youtube-transcript-api, …).
        status: runtime availability classification.
        priority: lower number = preferred in a fallback chain (1 = highest priority).
        requires_network: true if engine fetches remote data.
        requires_external_binary: true if engine requires a non-Python executable.
        max_size_bytes: suggested file/response size limit.
        notes: human-readable remarks (licence, installation command, …).
    """

    kind: AdapterKind
    format: str
    engine: str
    status: AdapterStatus = AdapterStatus.UNAVAILABLE
    priority: int = 100
    requires_network: bool = False
    requires_external_binary: bool = False
    max_size_bytes: int = 50_000_000
    notes: str = ""


@dataclass(frozen=True)
class AdapterInput:
    """Input to an adapter conversion call.

    Fields:
        source: source URL, file path, or raw content identifier.
        format: explicit format key override (auto-detected if None).
        options: engine-specific options dict (dpi, language, max_frames, …).
    """

    source: str
    format: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterResult:
    """Result from a successful or failed adapter call.

    Fields:
        success: true if the conversion completed.
        content: extracted text, markdown, or other structured content.
        engine: name of the engine that produced this result.
        metadata: extra info (char_count, page_count, frames_extracted, …).
        error: human-readable error message when success is false.
    """

    success: bool
    content: str
    engine: str
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# ── Registry ──


_ADAPTER_REGISTRY: dict[str, AdapterCapability] = {}


def register_adapter(*capabilities: AdapterCapability) -> None:
    """Register one or more adapter capabilities."""
    for cap in capabilities:
        key = f"{cap.kind.value}:{cap.format}:{cap.engine}"
        _ADAPTER_REGISTRY[key] = cap


def get_adapter_registry() -> dict[str, AdapterCapability]:
    """Return a copy of the current adapter registry."""
    return dict(_ADAPTER_REGISTRY)


def lookup_adapter(kind: AdapterKind | str, format: str, engine: str) -> AdapterCapability | None:
    """Look up a specific adapter by kind, format, and engine."""
    key = f"{kind.value if isinstance(kind, AdapterKind) else kind}:{format}:{engine}"
    return _ADAPTER_REGISTRY.get(key)


def lookup_adapters(kind: AdapterKind | str, format: str) -> list[AdapterCapability]:
    """Return all registered adapters for a given kind and format, sorted by priority."""
    kind_str = kind.value if isinstance(kind, AdapterKind) else kind
    matches = [
        cap for key, cap in _ADAPTER_REGISTRY.items()
        if key.startswith(f"{kind_str}:{format}:")
    ]
    matches.sort(key=lambda c: c.priority)
    return matches
