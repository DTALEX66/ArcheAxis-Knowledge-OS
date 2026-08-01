"""Unified configuration loader — reads config/settings.yaml + env overrides.

Architecture:
    config/settings.yaml (base)  →  env vars (override)  →  singleton Config

Usage:
    from shared.config import config
    db_path = config.get("database.path")
    log_level = config.get("logging.level", "INFO")
"""

from __future__ import annotations

import copy
import json
import os
from ipaddress import ip_network
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── Default configuration ────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "app": {
        "name": "Cognitive-Loop-OS",
        "version": "0.4.1",
        "environment": "development",
        "port": 8000,
        "host": "0.0.0.0",
    },
    "database": {
        "path": "data/cognitive_os.sqlite",
        "journal_mode": "WAL",
        "backup_dir": "data/backups",
    },
    "logging": {
        "level": "INFO",
        "console": True,
        "file": True,
        "file_dir": "data/logs",
        "rotation": "10 MB",
        "retention": "7 days",
    },
    "auth": {
        "enabled": False,  # set True in production
        "token_expire_hours": 24,
        "api_key_file": "config/api_keys.json",
    },
    "rate_limit": {
        "enabled": True,
        "window_seconds": 60,
        "ordinary_read": 200,
        "sensitive_write": 30,
        "auth_token": 5,
        "max_buckets_per_policy": 10_000,
        "trusted_proxies": [],
    },
    "pipeline": {
        "max_content_chars": 10000,
        "default_actions": ["extract", "tag", "summarize", "index"],
        "auto_ingest": True,
    },
    "search": {
        "fts5_enabled": True,
        "vector_enabled": True,
        "vector_dim": 384,
        "default_top_k": 5,
    },
    "cors": {
        "allow_origins": ["*"],
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    },
}


class Config:
    """Runtime configuration with public YAML layers and env overrides.

    Load order is intentionally explicit and backward-compatible:
    built-in defaults -> config/defaults.yaml -> config/settings.yaml
    (legacy active source) -> config/profiles/<profile>.yaml -> env overrides.
    """

    _SUPPORTED_PROFILES = {"desktop", "development", "test", "production"}

    def __init__(self, profile: str | None = None) -> None:
        selected = profile if profile is not None else os.getenv("COGNITIVE_PROFILE", "development")
        self.profile = selected.strip().lower() or "development"
        if self.profile not in self._SUPPORTED_PROFILES:
            supported = ", ".join(sorted(self._SUPPORTED_PROFILES))
            raise ValueError(f"unknown configuration profile: {self.profile}; expected one of {supported}")
        self._data = copy.deepcopy(_DEFAULTS)
        self._load_yaml("defaults.yaml")
        self._load_yaml("settings.yaml")
        self._load_yaml(Path("profiles") / f"{self.profile}.yaml")
        self._apply_env()

    def _load_yaml(self, relative_path: str | Path) -> None:
        config_path = _PROJECT_ROOT / "config" / relative_path
        if not config_path.exists():
            return
        try:
            import yaml

            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as exc:
            raise RuntimeError(f"unable to load runtime configuration: {config_path}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"runtime configuration must be a mapping: {config_path}")
        self._deep_merge(self._data, data)

    def _apply_env(self) -> None:
        """Override config from environment variables."""
        env_map: dict[str, list[str]] = {
            "COGNITIVE_ENV": ["app", "environment"],
            "COGNITIVE_PORT": ["app", "port"],
            "COGNITIVE_RELEASE_VERSION": ["app", "release_version"],
            "COGNITIVE_DB_PATH": ["database", "path"],
            "COGNITIVE_LOG_LEVEL": ["logging", "level"],
            "COGNITIVE_AUTH_ENABLED": ["auth", "enabled"],
            "COGNITIVE_JWT_SECRET": ["auth", "jwt_secret"],
            "COGNITIVE_RATE_LIMIT_ENABLED": ["rate_limit", "enabled"],
            "COGNITIVE_RATE_LIMIT_WINDOW_SECONDS": ["rate_limit", "window_seconds"],
            "COGNITIVE_RATE_LIMIT_READ": ["rate_limit", "ordinary_read"],
            "COGNITIVE_RATE_LIMIT_WRITE": ["rate_limit", "sensitive_write"],
            "COGNITIVE_RATE_LIMIT_TOKEN": ["rate_limit", "auth_token"],
            "COGNITIVE_RATE_LIMIT_MAX_BUCKETS": ["rate_limit", "max_buckets_per_policy"],
        }
        for env_key, path in env_map.items():
            val = os.getenv(env_key, "")
            if val:
                self._set_nested(self._data, path, self._coerce(val))

        list_env_map = {
            "COGNITIVE_CORS_ORIGINS": ["cors", "allow_origins"],
            "COGNITIVE_CORS_METHODS": ["cors", "allow_methods"],
            "COGNITIVE_CORS_HEADERS": ["cors", "allow_headers"],
            "COGNITIVE_TRUSTED_PROXIES": ["rate_limit", "trusted_proxies"],
        }
        for env_key, path in list_env_map.items():
            value = os.getenv(env_key, "")
            if value:
                items = [item.strip() for item in value.split(",") if item.strip()]
                self._set_nested(self._data, path, items)

    @staticmethod
    def _coerce(val: str) -> Any:
        if val.lower() in ("true", "yes", "1"):
            return True
        if val.lower() in ("false", "no", "0"):
            return False
        try:
            return int(val)
        except ValueError:
            pass
        return val

    @staticmethod
    def _set_nested(data: dict, path: list[str], value: Any) -> None:
        for key in path[:-1]:
            data = data.setdefault(key, {})
        data[path[-1]] = value

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get config by dot-separated path. e.g. 'database.path'."""
        keys = key_path.split(".")
        data: Any = self._data
        for k in keys:
            if isinstance(data, dict):
                data = data.get(k)
            else:
                return default
        return data if data is not None else default

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)


# Singleton
config = Config()


def resolve_runtime_path(value: str | Path) -> Path:
    """Resolve paths without falling back to an uncontrolled user-home directory."""
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    configured_root = os.getenv("COGNITIVE_DATA_DIR", "").strip()
    if configured_root:
        base = Path(configured_root).expanduser()
        parts = (
            candidate.parts[1:]
            if candidate.parts and candidate.parts[0] in {"data", "config"}
            else candidate.parts
        )
        return base.joinpath(*parts)
    if (_PROJECT_ROOT / "pyproject.toml").exists():
        return _PROJECT_ROOT / candidate
    raise RuntimeError(
        "runtime data root is not configured; set COGNITIVE_DATA_DIR "
        "before using an installed or relocated runtime"
    )


_ALLOWED_ROLES = {"admin", "user", "readonly"}
_FORBIDDEN_SECRETS = {"change-me", "changeme", "secret"}
_FORBIDDEN_SECRET_PATTERNS = (
    "replace-with",
    "placeholder",
    "example-secret",
    "strong-random-api-key",
    "strong-random-jwt-secret",
)


def _is_strong_secret(value: str) -> bool:
    normalized = value.lower()
    return (
        len(value) >= 32
        and normalized not in _FORBIDDEN_SECRETS
        and not any(pattern in normalized for pattern in _FORBIDDEN_SECRET_PATTERNS)
        and len(set(value)) >= 8
    )


def _read_valid_api_key_file(path: Path) -> dict[str, dict[str, str]] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    valid = isinstance(data, dict) and bool(data) and all(
        isinstance(key, str)
        and _is_strong_secret(key)
        and isinstance(value, dict)
        and value.get("role") in _ALLOWED_ROLES
        and isinstance(value.get("name"), str)
        and bool(value.get("name", "").strip())
        for key, value in data.items()
    )
    return data if valid else None


def _has_valid_api_key_file(path: Path) -> bool:
    return _read_valid_api_key_file(path) is not None


def validate_runtime_config(current: Config = config) -> None:
    """Fail fast when runtime safety settings are invalid or unsafe in production."""
    enabled = current.get("rate_limit.enabled", True)
    if not isinstance(enabled, bool):
        raise RuntimeError("rate_limit.enabled must be a boolean")
    limits: dict[str, int] = {}
    for name in (
        "window_seconds",
        "ordinary_read",
        "sensitive_write",
        "auth_token",
        "max_buckets_per_policy",
    ):
        value = current.get(f"rate_limit.{name}")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise RuntimeError(f"rate_limit.{name} must be a positive integer")
        limits[name] = value
    if not (
        limits["sensitive_write"] < limits["ordinary_read"]
        and limits["auth_token"] < limits["ordinary_read"]
    ):
        raise RuntimeError("sensitive write and auth token limits must be stricter than ordinary reads")
    trusted_proxies = current.get("rate_limit.trusted_proxies", [])
    if not isinstance(trusted_proxies, list) or not all(
        isinstance(item, str) and item == item.strip() and bool(item) for item in trusted_proxies
    ):
        raise RuntimeError("rate_limit.trusted_proxies must be a list of IP addresses or CIDRs")
    try:
        for item in trusted_proxies:
            ip_network(item, strict=False)
    except ValueError as exc:
        raise RuntimeError(
            "rate_limit.trusted_proxies must contain only valid IP addresses or CIDRs"
        ) from exc

    environment = str(current.get("app.environment", "development")).lower()
    if environment not in {"production", "prod"}:
        return
    if not enabled:
        raise RuntimeError("production requires gateway rate limiting")
    if not bool(current.get("auth.enabled", False)):
        raise RuntimeError("production requires auth.enabled=true")
    origins = current.get("cors.allow_origins", ["*"])
    if not isinstance(origins, list) or not origins or not all(
        isinstance(item, str) and item == item.strip() and bool(item) for item in origins
    ):
        raise RuntimeError("production CORS origins must be a non-empty list of strings")
    if "*" in origins:
        raise RuntimeError("production requires an explicit CORS origin allowlist")
    methods = current.get("cors.allow_methods", [])
    allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
    if not isinstance(methods, list) or not methods or not all(item in allowed_methods for item in methods):
        raise RuntimeError("production CORS methods must be an explicit supported-method list")
    headers = current.get("cors.allow_headers", [])
    if not isinstance(headers, list) or not headers or not all(
        isinstance(item, str) and item == item.strip() and bool(item) and item != "*" for item in headers
    ):
        raise RuntimeError("production CORS headers must be a non-empty list of strings")
    key_file = resolve_runtime_path(str(current.get("auth.api_key_file", "config/api_keys.json")))
    api_key = os.getenv("COGNITIVE_API_KEY", "")
    jwt_secret = os.getenv("COGNITIVE_JWT_SECRET", "")
    file_keys = _read_valid_api_key_file(key_file)
    if key_file.exists() and file_keys is None:
        raise RuntimeError("production auth.api_key_file contains invalid or weak records")
    if not _is_strong_secret(api_key) and file_keys is None:
        raise RuntimeError("production requires a strong COGNITIVE_API_KEY or auth.api_key_file")
    if not _is_strong_secret(jwt_secret):
        raise RuntimeError("production requires a strong COGNITIVE_JWT_SECRET")
    if api_key and api_key == jwt_secret:
        raise RuntimeError("production API key and JWT secret must be different")
    if file_keys and any(key == jwt_secret for key in file_keys):
        raise RuntimeError("production API keys and JWT secret must be different")
