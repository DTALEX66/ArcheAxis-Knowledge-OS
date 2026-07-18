"""Provider and model capability contract for Cognitive-OS.

Contract-first: define what a provider/model IS before wiring any specific implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProviderKind(str, Enum):
    LLM = "llm"
    EMBEDDING = "embedding"
    VISION = "vision"
    AUDIO = "audio"
    CRAWLER = "crawler"
    CONVERTER = "converter"
    VECTOR_DB = "vector_db"
    GRAPH_DB = "graph_db"
    EVALUATION = "evaluation"
    OBSERVABILITY = "observability"


class CapabilityStatus(str, Enum):
    SUPPORTED = "supported"
    PLANNED = "planned"
    CANDIDATE = "candidate"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ModelCapability:
    """One capability of a model: text generation, tool calling, vision, etc."""

    name: str
    status: CapabilityStatus = CapabilityStatus.CANDIDATE
    min_model: str | None = None
    notes: str = ""


@dataclass
class ProviderContract:
    """Canonical description of a provider or model service for intake evaluation."""

    provider_id: str
    name: str
    kind: ProviderKind
    status: CapabilityStatus = CapabilityStatus.CANDIDATE
    capabilities: list[ModelCapability] = field(default_factory=list)
    base_url: str | None = None
    api_requires_key: bool = True
    free_tier_available: bool = False
    local_execution_possible: bool = False
    requires_human_review: bool = True
    notes: str = ""


# --- Dry-run route registry (no live connection) ---

@dataclass(frozen=True)
class DryRunRoute:
    """A declared provider route that has NOT been live-verified."""

    provider_id: str
    model_id: str
    kind: ProviderKind
    status: CapabilityStatus = CapabilityStatus.CANDIDATE


DEFAULT_ROUTES: list[DryRunRoute] = []
