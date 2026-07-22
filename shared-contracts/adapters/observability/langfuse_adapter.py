"""Optional Langfuse v4 event adapter with payload-free observability boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_ALLOWED_METADATA_KEYS = {
    "component",
    "operation",
    "outcome",
    "duration_ms",
    "release",
    "environment",
    "error_type",
}
_ALLOWED_LEVELS = {"DEBUG", "DEFAULT", "WARNING", "ERROR"}


@dataclass(frozen=True)
class ObservationQueued:
    """A local confirmation that an event was handed to the Langfuse SDK queue."""

    name: str
    status: str = "queued"


def _validated_metadata(metadata: Mapping[str, str | int | float | bool | None]) -> dict[str, Any]:
    unexpected = set(metadata) - _ALLOWED_METADATA_KEYS
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(f"Langfuse metadata keys are not allowed: {names}")
    if not metadata:
        raise ValueError("Langfuse metadata is required")
    return dict(metadata)


def _client_from_explicit_keys(*, public_key: str | None, secret_key: str | None, base_url: str | None):
    if not public_key or not secret_key:
        raise ValueError("an explicit client or both Langfuse keys are required")
    from langfuse import Langfuse

    return Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)


def queue_event(
    name: str,
    metadata: Mapping[str, str | int | float | bool | None],
    *,
    level: str = "DEFAULT",
    client: Any | None = None,
    public_key: str | None = None,
    secret_key: str | None = None,
    base_url: str | None = None,
) -> ObservationQueued:
    """Queue one metadata-only Langfuse event without exporting runtime payloads.

    The return value proves only local SDK handoff. It intentionally does not claim
    remote delivery; callers must use Langfuse's own delivery/flush telemetry for that.
    """
    if not name.strip():
        raise ValueError("Langfuse event name is required")
    if level not in _ALLOWED_LEVELS:
        raise ValueError(f"unsupported Langfuse level: {level}")
    safe_metadata = _validated_metadata(metadata)
    langfuse_client = client or _client_from_explicit_keys(
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
    )
    with langfuse_client.start_as_current_observation(
        name=name,
        as_type="event",
        metadata=safe_metadata,
        level=level,
    ):
        pass
    return ObservationQueued(name=name)
