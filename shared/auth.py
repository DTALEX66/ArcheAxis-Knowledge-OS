"""Authentication & authorization layer — JWT + API Key middleware.

Architecture:
    ┌─────────────────────────────────────────┐
    │  API Key (provisioned administrator)    │  ← X-API-Key header
    │  JWT Token (dynamic, user sessions)     │  ← Authorization: Bearer
    │  No-auth allowlist (health, docs)       │  ← /health, /docs, /openapi
    └─────────────────────────────────────────┘

Usage:
    from shared.auth import AuthMiddleware, create_token, verify_token

    # Generate token
    token = create_token(user_id="admin", role="admin", expires_hours=24)

    # Verify
    payload = verify_token(token)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

# ── API Key management ──────────────────────────────────


def _load_api_keys() -> dict[str, dict[str, str]]:
    """Load API keys from config file or environment."""
    from shared.config import (
        _is_strong_secret,
        _read_valid_api_key_file,
        config,
        resolve_runtime_path,
    )

    keys: dict[str, dict[str, str]] = {}

    # Try config file
    config_path = resolve_runtime_path(str(config.get("auth.api_key_file", "config/api_keys.json")))
    loaded = _read_valid_api_key_file(config_path)
    if loaded:
        keys.update(loaded)

    # Every environment requires explicit, strong administrator provisioning.
    env_key = os.getenv("COGNITIVE_API_KEY", "")
    if _is_strong_secret(env_key):
        keys[env_key] = {"role": "admin", "name": "env-admin"}

    return keys


def validate_api_key(api_key: str) -> dict[str, str] | None:
    """Validate an API key. Returns {role, name} or None."""
    keys = _load_api_keys()
    return keys.get(api_key)


def get_user_from_key(api_key: str) -> str | None:
    """Get user name from valid API key."""
    info = validate_api_key(api_key)
    return info["name"] if info else None


def authenticate_request(path: str, api_key: str = "", authorization: str = "") -> dict[str, Any] | None:
    """Authenticate one HTTP request, returning an anonymous identity for public paths."""
    if not requires_auth(path):
        return {"sub": "anonymous", "role": "anonymous", "auth_method": "none"}
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    return verify_token(token or api_key)


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_ADMIN_ONLY_PREFIXES = (
    "/auth/token",
    "/backup",
    "/convert/directory",
    "/convert/file",
    "/ingest/directory",
    "/ingest/file",
    "/internal/",
    "/kb/bulk/",
    "/kb/cron/",
    "/kb/obsidian/",
    "/kb/pipeline",
    "/kb/project/",
    "/kb/projects/",
    "/project/",
    "/projects/",
    "/kb/search/rebuild",
    "/kb/sources",
    "/run",
    "/sleep-loop",
)


def authorize_request(identity: dict[str, Any], method: str, path: str) -> bool:
    """Apply the production role matrix after authentication."""
    if identity.get("auth_method") == "none":
        return True
    role = identity.get("role")
    if role == "admin":
        return True
    if role == "readonly":
        return method.upper() in _SAFE_METHODS
    if role != "user":
        return False
    return not any(path == prefix or path.startswith(prefix) for prefix in _ADMIN_ONLY_PREFIXES)


# ── JWT-like token (HMAC, zero-dependency) ───────────────


def _get_secret() -> str:
    """Get or generate signing secret."""
    secret = os.getenv("COGNITIVE_JWT_SECRET", "")
    if secret:
        return secret

    from shared.config import resolve_runtime_path

    secret_path = resolve_runtime_path("data/.jwt_secret")
    if secret_path.exists():
        return secret_path.read_text().strip()

    # Generate new secret
    new_secret = secrets.token_hex(32)
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    secret_path.write_text(new_secret)
    return new_secret


def create_token(user_id: str, role: str = "user", expires_hours: int = 24) -> str:
    """Create a signed token (HMAC-SHA256, zero-dependency JWT-like).

    Args:
        user_id: user identifier.
        role: 'admin' | 'user' | 'readonly'.
        expires_hours: token lifetime in hours.

    Returns:
        Base64-encoded token string.
    """
    import base64

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id is required")
    if role not in {"admin", "user", "readonly"}:
        raise ValueError("invalid role")
    if not isinstance(expires_hours, int) or not 1 <= expires_hours <= 168:
        raise ValueError("expires_hours must be between 1 and 168")

    payload = {
        "sub": user_id.strip(),
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time() + expires_hours * 3600),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(
        _get_secret().encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify a token and return payload if valid. Returns None if invalid/expired."""
    import base64

    parts = token.split(".")
    if len(parts) != 2:
        # Not our token format — try as raw API key
        info = validate_api_key(token)
        if info:
            return {"sub": info["name"], "role": info["role"], "auth_method": "api_key"}
        return None

    payload_b64, signature = parts
    # Verify signature
    expected = hmac.new(
        _get_secret().encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return None

    # Decode payload
    try:
        payload_b64_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload_b64_padded))
    except Exception:
        return None
    if not isinstance(decoded, dict):
        return None
    payload: dict[str, Any] = decoded

    now = time.time()
    subject = payload.get("sub")
    role = payload.get("role")
    issued_at = payload.get("iat")
    expires_at = payload.get("exp")
    if not isinstance(subject, str) or not subject.strip():
        return None
    if role not in {"admin", "user", "readonly"}:
        return None
    if not isinstance(issued_at, (int, float)) or not isinstance(expires_at, (int, float)):
        return None
    if issued_at > now + 60 or expires_at <= now or expires_at <= issued_at:
        return None
    if expires_at - issued_at > 168 * 3600 + 60:
        return None

    payload["auth_method"] = "jwt"
    return payload


# ── No-auth allowlist ────────────────────────────────────

_AUTH_ALLOWLIST: set[str] = {
    "/health",
    "/version",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/kb/docs",
    "/kb/redoc",
    "/kb/openapi.json",
}


def requires_auth(path: str) -> bool:
    """Check if a path requires authentication."""
    from shared.config import config

    if not bool(config.get("auth.enabled", False)):
        return False
    # Workspace uses a separate mandatory local-only boundary and never accepts browser secrets.
    workspace_prefix = "/" + "workspace"
    if path == workspace_prefix or path.startswith(f"{workspace_prefix}/"):
        return False
    # Allow exact matches
    if path in _AUTH_ALLOWLIST:
        return False
    # Allow sub-paths of docs
    if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
        return False
    return not (
        path.startswith("/kb/docs")
        or path.startswith("/kb/redoc")
        or path.startswith("/kb/openapi")
    )
