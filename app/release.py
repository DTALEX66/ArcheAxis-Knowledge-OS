"""Validated, packaged release truth for diagnostics and the local workspace."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_MANIFEST_PATH = Path(__file__).with_name("release-manifest.json")
_ARTIFACT_IDENTITY_PATH: Path | None = None
_RELEASE_REPOSITORY_URL = "https://github.com/DTALEX66/archeaxis-workspace"
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


def _require_repo_url(url: str, run_id: int) -> bool:
    return url == f"{_RELEASE_REPOSITORY_URL}/actions/runs/{run_id}"


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
        manifest["source"],
        {"commit", "tree", "verification_ci_run_id", "release_run_id", "reason"},
        "source",
    )
    for field in ("commit", "tree"):
        value = source[field]
        if value != "unavailable" and (
            not isinstance(value, str) or _HEX_40.fullmatch(value) is None
        ):
            raise RuntimeError(f"release manifest has invalid source.{field}")
    if not isinstance(source["reason"], str) or not source["reason"]:
        raise RuntimeError("release manifest source.reason must be non-empty")
    for field in ("verification_ci_run_id", "release_run_id"):
        value = source[field]
        if value != "unavailable" and (
            not isinstance(value, int) or value < 1
        ):
            raise RuntimeError(f"release manifest has invalid source.{field}")
    if release["public"] and any(
        source[field] == "unavailable"
        for field in ("commit", "tree", "verification_ci_run_id", "release_run_id")
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


def _validate_identity_source_v2(source: dict[str, Any]) -> None:
    if (
        not isinstance(source["commit"], str)
        or _HEX_40.fullmatch(source["commit"]) is None
        or not isinstance(source["tree"], str)
        or _HEX_40.fullmatch(source["tree"]) is None
        or not isinstance(source["verification_ci_run_id"], int)
        or source["verification_ci_run_id"] < 1
        or not isinstance(source["verification_ci_url"], str)
        or not _require_repo_url(source["verification_ci_url"], source["verification_ci_run_id"])
        or not isinstance(source["release_run_id"], int)
        or source["release_run_id"] < 1
        or not isinstance(source["release_run_url"], str)
        or not _require_repo_url(source["release_run_url"], source["release_run_id"])
        or source["verification_ci_run_id"] == source["release_run_id"]
    ):
        raise RuntimeError("artifact release identity has invalid v2 source fields")


def _validate_identity_source_v1(source: dict[str, Any]) -> None:
    if (
        not isinstance(source["commit"], str)
        or _HEX_40.fullmatch(source["commit"]) is None
        or not isinstance(source["tree"], str)
        or _HEX_40.fullmatch(source["tree"]) is None
        or not isinstance(source["ci_run"], int)
        or source["ci_run"] < 1
        or not isinstance(source["ci_url"], str)
        or not _require_repo_url(source["ci_url"], source["ci_run"])
    ):
        raise RuntimeError("artifact release identity has invalid v1 source fields")


def _validate_identity_release(release: dict[str, Any], version: str) -> None:
    if (
        release["tag"] != f"v{version}"
        or release["version"] != version
        or release["channel"] != "stable"
        or release["public"] is not True
        or not isinstance(release["url"], str)
        or release["url"] != f"{_RELEASE_REPOSITORY_URL}/releases/tag/{release['tag']}"
    ):
        raise RuntimeError("artifact release identity has invalid release fields")


@lru_cache(maxsize=1)
def load_artifact_release_identity() -> dict[str, Any] | None:
    """Read verified release identity packaged alongside a bundled runtime.

    Supports both schema v1 (legacy ``ci_run/ci_url``) and schema v2
    (``verification_ci_run_id`` / ``release_run_id`` separated). v2 requires
    the verification and release run IDs to differ, so a selective or
    main-bind run can never be mistaken for full release qualification.
    """
    identity_path = _ARTIFACT_IDENTITY_PATH or next(
        (parent / "release-identity.json" for parent in _MANIFEST_PATH.parents if (parent / "release-identity.json").is_file()),
        _MANIFEST_PATH.parent.parent / "release-identity.json",
    )
    if not identity_path.is_file():
        return None

    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    _require_exact_keys(identity, {"schema_version", "release", "source"}, "artifact identity")
    schema = identity["schema_version"]

    if schema == "2.0.0":
        release = _require_exact_keys(
            identity["release"], {"tag", "version", "channel", "public", "url"}, "artifact release"
        )
        source = _require_exact_keys(
            identity["source"],
            {
                "commit",
                "tree",
                "verification_ci_run_id",
                "verification_ci_url",
                "release_run_id",
                "release_run_url",
            },
            "artifact source",
        )
        version = load_release_manifest()["product"]["version"]
        _validate_identity_release(release, version)
        _validate_identity_source_v2(source)
        return identity

    if schema == "1.0.0":
        release = _require_exact_keys(
            identity["release"], {"tag", "version", "channel", "public", "url"}, "artifact release"
        )
        source = _require_exact_keys(
            identity["source"], {"commit", "tree", "ci_run", "ci_url"}, "artifact source"
        )
        version = load_release_manifest()["product"]["version"]
        _validate_identity_release(release, version)
        _validate_identity_source_v1(source)
        return identity

    raise RuntimeError("unsupported artifact release identity schema")


def safe_release_summary() -> dict[str, object]:
    """Expose no filesystem paths or unverifiable test-count claims."""
    manifest = load_release_manifest()
    identity = load_artifact_release_identity()
    if identity is not None:
        artifact_release = identity["release"]
        artifact_source = identity["source"]
        if identity["schema_version"] == "2.0.0":
            return {
                "status": "released",
                "version": artifact_release["version"],
                "channel": artifact_release["channel"],
                "source_commit": artifact_source["commit"],
                "tag": artifact_release["tag"],
                "verification_ci_run_id": artifact_source["verification_ci_run_id"],
                "release_run_id": artifact_source["release_run_id"],
                "url": artifact_release["url"],
            }
        return {
            "status": "released",
            "version": artifact_release["version"],
            "channel": artifact_release["channel"],
            "source_commit": artifact_source["commit"],
            "tag": artifact_release["tag"],
            "ci_run": artifact_source["ci_run"],
            "url": artifact_release["url"],
        }
    release = manifest["release"]
    source = manifest["source"]
    return {
        "status": release["status"],
        "version": manifest["product"]["version"],
        "channel": release["channel"],
        "source_commit": source["commit"],
    }


def effective_capabilities() -> dict[str, str]:
    """Report the installer capability only when bundled release identity verifies it."""
    capabilities = dict(load_release_manifest()["capabilities"])
    if load_artifact_release_identity() is not None:
        capabilities["public_installer"] = "available"
    return capabilities
