"""Authentication & authorization layer — JWT + API Key middleware.

Architecture:
    ┌─────────────────────────────────────────┐
    │  API Key (static, admin/dev)            │  ← X-API-Key header
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
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── API Key management ──────────────────────────────────


def _load_api_keys() -> dict[str, dict[str, str]]:
    """Load API keys from config file or environment."""
    # Default dev key (only for local development)
    keys: dict[str, dict[str, str]] = {
        "dev-key-change-me": {"role": "admin", "name": "default-dev-key"},
    }

    # Try config file
    config_path = _PROJECT_ROOT / "config" / "api_keys.json"
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text())
            if isinstance(loaded, dict):
                keys = loaded
        except Exception:
            pass

    # Override from env
    env_key = os.getenv("COGNITIVE_API_KEY", "")
    if env_key:
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


# ── JWT-like token (HMAC, zero-dependency) ───────────────


def _get_secret() -> str:
    """Get or generate signing secret."""
    secret = os.getenv("COGNITIVE_JWT_SECRET", "")
    if secret:
        return secret

    # Persistent secret file
    secret_path = _PROJECT_ROOT / "data" / ".jwt_secret"
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

    payload = {
        "sub": user_id,
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
        payload = json.loads(base64.urlsafe_b64decode(payload_b64_padded))
    except Exception:
        return None

    # Check expiration
    if payload.get("exp", 0) < time.time():
        return None

    payload["auth_method"] = "jwt"
    return payload


# ── No-auth allowlist ────────────────────────────────────

_AUTH_ALLOWLIST: set[str] = {
    "/health", "/version", "/docs", "/redoc", "/openapi.json",
    "/kb/docs", "/kb/redoc", "/kb/openapi.json",
    "/", "/dashboard", "/kb/", "/kb/dashboard",
}


def requires_auth(path: str) -> bool:
    """Check if a path requires authentication."""
    # Allow exact matches
    if path in _AUTH_ALLOWLIST:
        return False
    # Allow sub-paths of docs
    if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
        return False
    if path.startswith("/kb/docs") or path.startswith("/kb/redoc") or path.startswith("/kb/openapi"):
        return False
    return True
