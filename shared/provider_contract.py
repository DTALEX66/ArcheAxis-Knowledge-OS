"""Provider and model capability contract for ArcheAxis.

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

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("model capability name is required")
        if not isinstance(self.status, CapabilityStatus):
            raise ValueError("model capability status must be a CapabilityStatus")
        if self.min_model is not None and (
            not isinstance(self.min_model, str) or not self.min_model.strip()
        ):
            raise ValueError("model capability min_model must be non-empty when set")


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

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id is required")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("provider name is required")
        if not isinstance(self.kind, ProviderKind):
            raise ValueError("provider kind must be a ProviderKind")
        if not isinstance(self.status, CapabilityStatus):
            raise ValueError("provider status must be a CapabilityStatus")
        if not isinstance(self.capabilities, list):
            raise ValueError("provider capabilities must be a list")
        names = [capability.name.strip() for capability in self.capabilities]
        if len(names) != len(set(names)):
            raise ValueError("provider capabilities must have unique names")
        if self.base_url is not None and (
            not isinstance(self.base_url, str) or not self.base_url.strip()
        ):
            raise ValueError("provider base_url must be non-empty when set")


# --- Dry-run route registry (no live connection) ---

@dataclass(frozen=True)
class DryRunRoute:
    """A declared provider route that has NOT been live-verified."""

    provider_id: str
    model_id: str
    kind: ProviderKind
    status: CapabilityStatus = CapabilityStatus.CANDIDATE

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("dry-run route provider_id is required")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("dry-run route model_id is required")
        if not isinstance(self.kind, ProviderKind):
            raise ValueError("dry-run route kind must be a ProviderKind")
        if not isinstance(self.status, CapabilityStatus):
            raise ValueError("dry-run route status must be a CapabilityStatus")


DEFAULT_ROUTES: list[DryRunRoute] = []
