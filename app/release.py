"""Validated, packaged release truth for diagnostics and the local workspace."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_MANIFEST_PATH = Path(__file__).with_name("release-manifest.json")
_ALLOWED_CAPABILITY_STATES = {"available", "dependency_required", "not_implemented"}
_CAPABILITY_KEYS = {
    "local_url_file_github_intake",
    "workspace_job_outbox_receipts",
    "strict_governance_readback",
    "audio_track_and_video_keyframes",
    "image_ocr",
    "asr_transcription",
    "asynchronous_worker",
    "outbox_dispatcher",
    "server_sent_events",
    "interactive_job_center",
    "postgresql_runtime",
    "qdrant_runtime",
    "public_installer",
}
_HEX_40 = re.compile(r"[0-9a-f]{40}")
_HEX_64 = re.compile(r"[0-9a-f]{64}")


def _require_exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise RuntimeError(f"release manifest has invalid {label} fields")
    return value


@lru_cache(maxsize=1)
def load_release_manifest() -> dict[str, Any]:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    _require_exact_keys(
        manifest,
        {
            "schema_version",
            "product",
            "release",
            "source",
            "dependency_lock",
            "migrations",
            "capabilities",
            "verification",
        },
        "top-level",
    )
    if manifest.get("schema_version") != "1.0.0":
        raise RuntimeError("unsupported release manifest schema")
    product = _require_exact_keys(
        manifest["product"],
        {
            "id",
            "name",
            "english_name",
            "workspace_name",
            "workspace_english_name",
            "version",
            "requires_python",
        },
        "product",
    )
    if not all(isinstance(value, str) and value for value in product.values()):
        raise RuntimeError("release manifest product values must be non-empty strings")
    release = _require_exact_keys(
        manifest["release"], {"status", "channel", "public"}, "release"
    )
    if (
        release["status"] not in {"unreleased", "released"}
        or release["channel"] not in {"development", "alpha", "beta", "stable"}
        or not isinstance(release["public"], bool)
        or release["public"] != (release["status"] == "released")
    ):
        raise RuntimeError("release manifest has invalid release state")
    source = _require_exact_keys(
        manifest["source"], {"commit", "tree", "ci_run", "reason"}, "source"
    )
    for field in ("commit", "tree"):
        value = source[field]
        if value != "unavailable" and (
            not isinstance(value, str) or _HEX_40.fullmatch(value) is None
        ):
            raise RuntimeError(f"release manifest has invalid source.{field}")
    if not isinstance(source["reason"], str) or not source["reason"]:
        raise RuntimeError("release manifest source.reason must be non-empty")
    if source["ci_run"] != "unavailable" and (
        not isinstance(source["ci_run"], int) or source["ci_run"] < 1
    ):
        raise RuntimeError("release manifest has invalid source.ci_run")
    if release["public"] and any(
        source[field] == "unavailable" for field in ("commit", "tree", "ci_run")
    ):
        raise RuntimeError("public release manifest requires exact source and CI identity")
    dependency_lock = _require_exact_keys(
        manifest["dependency_lock"],
        {"path", "algorithm", "digest", "format_version", "revision"},
        "dependency_lock",
    )
    if (
        dependency_lock["path"] != "uv.lock"
        or dependency_lock["algorithm"] != "sha256"
        or not isinstance(dependency_lock["digest"], str)
        or _HEX_64.fullmatch(dependency_lock["digest"]) is None
        or not isinstance(dependency_lock["format_version"], int)
        or not isinstance(dependency_lock["revision"], int)
    ):
        raise RuntimeError("release manifest has invalid dependency lock")
    capabilities = _require_exact_keys(manifest["capabilities"], _CAPABILITY_KEYS, "capabilities")
    invalid_states = sorted(set(capabilities.values()) - _ALLOWED_CAPABILITY_STATES)
    if invalid_states:
        raise RuntimeError(
            "release manifest has unsupported capability states: " + ", ".join(invalid_states)
        )
    migrations = _require_exact_keys(manifest["migrations"], {"owners"}, "migrations")
    owners = migrations["owners"]
    required_owner_fields = {"owner", "version", "target", "kind", "steps"}
    if (
        not isinstance(owners, list)
        or not owners
        or any(not isinstance(owner, dict) or set(owner) != required_owner_fields for owner in owners)
    ):
        raise RuntimeError("release manifest has invalid migration owners")
    owner_names: set[str] = set()
    for owner in owners:
        if (
            not isinstance(owner["owner"], str)
            or not owner["owner"]
            or not isinstance(owner["version"], int)
            or owner["version"] < 1
            or not isinstance(owner["target"], str)
            or not owner["target"]
            or not isinstance(owner["kind"], str)
            or not owner["kind"]
            or not isinstance(owner["steps"], list)
            or not all(isinstance(step, str) and step for step in owner["steps"])
            or owner["owner"] in owner_names
        ):
            raise RuntimeError("release manifest has invalid migration owner values")
        owner_names.add(owner["owner"])
    verification = _require_exact_keys(
        manifest["verification"], {"embedded_test_counts", "evidence_policy"}, "verification"
    )
    if verification["embedded_test_counts"] is not False or not isinstance(
        verification["evidence_policy"], str
    ):
        raise RuntimeError("release manifest has invalid verification policy")
    return manifest


def safe_release_summary() -> dict[str, object]:
    """Expose no filesystem paths or unverifiable test-count claims."""
    manifest = load_release_manifest()
    release = manifest["release"]
    source = manifest["source"]
    return {
        "status": release["status"],
        "version": manifest["product"]["version"],
        "channel": release["channel"],
        "source_commit": source["commit"],
    }
