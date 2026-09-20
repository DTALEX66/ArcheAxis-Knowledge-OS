"""Fail-closed provider routing snapshot contract for the formal Core host."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "archeaxis.provider-routing/v1"
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_DRIVE = re.compile(r"^[A-Za-z]:")
_ALLOWED_TOP = {"schema_version", "generation", "providers", "routes"}


class ProviderRoutingError(ValueError):
    """Raised when a routing snapshot cannot be safely consumed."""


@dataclass(frozen=True)
class HealthReceipt:
    status: str
    receipt_ref: str | None

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy" and self.receipt_ref is not None


@dataclass(frozen=True)
class ProviderRecord:
    provider_id: str
    version: str
    manifest_version: str
    manifest_sha256: str
    manifest_ref: str
    installed: bool
    enabled: bool
    health: HealthReceipt


@dataclass(frozen=True)
class RouteRecord:
    capability: str
    default_provider: str
    fallback_providers: tuple[str, ...]


@dataclass(frozen=True)
class ProviderRoutingSnapshot:
    schema_version: str
    generation: int
    providers: dict[str, ProviderRecord]
    routes: dict[str, RouteRecord]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ProviderRoutingSnapshot:
        if not isinstance(data, Mapping):
            raise ProviderRoutingError("routing snapshot must be an object")
        unknown = set(data) - _ALLOWED_TOP
        if unknown or set(data) != _ALLOWED_TOP:
            raise ProviderRoutingError("routing snapshot fields are incomplete or unknown")
        if data["schema_version"] != SCHEMA_VERSION:
            raise ProviderRoutingError("unsupported routing schema version")
        generation = data["generation"]
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ProviderRoutingError("generation must be a non-negative integer")
        raw_providers = data["providers"]
        raw_routes = data["routes"]
        if not isinstance(raw_providers, Mapping) or not raw_providers:
            raise ProviderRoutingError("providers must be a non-empty object")
        if not isinstance(raw_routes, Mapping) or not raw_routes:
            raise ProviderRoutingError("routes must be a non-empty object")
        providers: dict[str, ProviderRecord] = {}
        for provider_id, raw in raw_providers.items():
            _identity(provider_id, "provider id")
            if not isinstance(raw, Mapping):
                raise ProviderRoutingError(f"provider {provider_id} must be an object")
            expected = {"version", "manifest_version", "manifest_sha256", "manifest_ref", "installed", "enabled", "health"}
            if set(raw) != expected:
                raise ProviderRoutingError(f"provider {provider_id} fields are incomplete or unknown")
            version = _text(raw["version"], f"provider {provider_id} version")
            manifest_version = _text(raw["manifest_version"], f"provider {provider_id} manifest version")
            manifest_sha256 = _text(raw["manifest_sha256"], f"provider {provider_id} manifest SHA")
            if not _SHA256.fullmatch(manifest_sha256):
                raise ProviderRoutingError(f"provider {provider_id} manifest SHA must be 64 hex characters")
            manifest_ref = _reference(raw["manifest_ref"], f"provider {provider_id} manifest reference")
            installed = _boolean(raw["installed"], f"provider {provider_id} installed")
            enabled = _boolean(raw["enabled"], f"provider {provider_id} enabled")
            if enabled and not installed:
                raise ProviderRoutingError(f"provider {provider_id} enabled state requires installed")
            health = _health(raw["health"], provider_id)
            providers[provider_id] = ProviderRecord(provider_id, version, manifest_version, manifest_sha256.lower(), manifest_ref, installed, enabled, health)
        routes: dict[str, RouteRecord] = {}
        for capability, raw in raw_routes.items():
            _identity(capability, "capability")
            if not isinstance(raw, Mapping) or set(raw) != {"default_provider", "fallback_providers"}:
                raise ProviderRoutingError(f"route {capability} fields are incomplete or unknown")
            default = _identity(raw["default_provider"], f"route {capability} default provider")
            fallback = raw["fallback_providers"]
            if not isinstance(fallback, list) or any(not isinstance(item, str) or not item.strip() for item in fallback):
                raise ProviderRoutingError(f"route {capability} fallback providers must be a list of IDs")
            if len(fallback) != len(set(fallback)):
                raise ProviderRoutingError(f"route {capability} fallback providers contain duplicate IDs")
            if default in fallback:
                raise ProviderRoutingError(f"route {capability} fallback providers repeat the default provider")
            refs = [default, *fallback]
            missing = [provider for provider in refs if provider not in providers]
            if missing:
                raise ProviderRoutingError(f"route {capability} references unknown provider {missing[0]}")
            for provider in refs:
                if not providers[provider].installed or not providers[provider].enabled:
                    raise ProviderRoutingError(f"route {capability} references provider {provider} that is not installed and enabled")
            routes[capability] = RouteRecord(capability, default, tuple(fallback))
        return cls(SCHEMA_VERSION, generation, providers, routes)

    def eligible_providers(self, capability: str) -> tuple[ProviderRecord, ...]:
        """Return healthy providers in default→fallback order; unknown health never runs."""
        route = self.routes.get(capability)
        if route is None:
            raise ProviderRoutingError(f"unknown capability {capability}")
        ordered = (route.default_provider, *route.fallback_providers)
        return tuple(self.providers[provider] for provider in ordered if self.providers[provider].health.is_healthy)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderRoutingError(f"{label} is required")
    return value.strip()


def _identity(value: Any, label: str) -> str:
    text = _text(value, label)
    if "/" in text or "\\" in text or ":" in text:
        raise ProviderRoutingError(f"{label} contains an unsafe identity")
    return text


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ProviderRoutingError(f"{label} must be boolean")
    return value


def _reference(value: Any, label: str) -> str:
    text = _text(value, label)
    if text.startswith("/") or text.startswith("//") or _DRIVE.match(text):
        raise ProviderRoutingError(f"{label} is not a safe relative reference")
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts) or "\x00" in text or "\\" in text:
        raise ProviderRoutingError(f"{label} is not a safe relative reference")
    return "/".join(parts)


def _health(value: Any, provider_id: str) -> HealthReceipt:
    if not isinstance(value, Mapping) or set(value) - {"status", "receipt_ref"} or "status" not in value:
        raise ProviderRoutingError(f"provider {provider_id} health is incomplete")
    status = _text(value["status"], f"provider {provider_id} health status")
    if status not in {"unknown", "healthy", "unhealthy"}:
        raise ProviderRoutingError(f"provider {provider_id} health status is invalid")
    receipt = value.get("receipt_ref")
    if receipt is not None:
        receipt = _reference(receipt, f"provider {provider_id} health receipt reference")
    if status in {"healthy", "unhealthy"} and receipt is None:
        raise ProviderRoutingError(f"provider {provider_id} health receipt reference is required")
    return HealthReceipt(status, receipt)
