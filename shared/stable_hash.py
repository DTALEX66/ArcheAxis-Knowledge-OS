"""Versioned deterministic hashes for persisted identifiers and fingerprints."""

from __future__ import annotations

import hashlib

STABLE_HASH_ALGORITHM = "sha256-v1"
_DEFAULT_NAMESPACE = "default"


def _validate_namespace(namespace: str) -> str:
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("hash namespace must be non-empty")
    return namespace.strip()


def stable_hash_bytes(payload: bytes, *, namespace: str = _DEFAULT_NAMESPACE) -> str:
    """Return a deterministic SHA-256 digest for a namespaced byte payload."""
    if not isinstance(payload, bytes):
        raise TypeError("hash payload must be bytes")
    scope = _validate_namespace(namespace).encode("utf-8")
    return hashlib.sha256(scope + b"\0" + payload).hexdigest()


def stable_hash_text(text: str, *, namespace: str = _DEFAULT_NAMESPACE) -> str:
    """Return the UTF-8 stable hash for text using the versioned algorithm."""
    if not isinstance(text, str):
        raise TypeError("hash text must be str")
    return stable_hash_bytes(text.encode("utf-8"), namespace=namespace)
