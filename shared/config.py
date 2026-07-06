"""Unified configuration loader — reads config/settings.yaml + env overrides.

Architecture:
    config/settings.yaml (base)  →  env vars (override)  →  singleton Config

Usage:
    from shared.config import config
    db_path = config.get("database.path")
    log_level = config.get("logging.level", "INFO")
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── Default configuration ────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "app": {
        "name": "Cognitive-Loop-OS",
        "version": "0.4.0",
        "port": 8000,
        "host": "0.0.0.0",
    },
    "database": {
        "path": str(_PROJECT_ROOT / "data" / "cognitive_os.sqlite"),
        "journal_mode": "WAL",
        "backup_dir": str(_PROJECT_ROOT / "data" / "backups"),
    },
    "logging": {
        "level": "INFO",
        "console": True,
        "file": True,
        "file_dir": str(_PROJECT_ROOT / "data" / "logs"),
        "rotation": "10 MB",
        "retention": "7 days",
    },
    "auth": {
        "enabled": False,  # set True in production
        "token_expire_hours": 24,
        "api_key_file": str(_PROJECT_ROOT / "config" / "api_keys.json"),
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
    """Singleton configuration with YAML + env override."""

    def __init__(self) -> None:
        self._data = dict(_DEFAULTS)
        self._load_yaml()
        self._apply_env()

    def _load_yaml(self) -> None:
        config_path = _PROJECT_ROOT / "config" / "settings.yaml"
        if not config_path.exists():
            return
        try:
            import yaml
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                self._deep_merge(self._data, data)
        except Exception:
            pass

    def _apply_env(self) -> None:
        """Override config from environment variables."""
        env_map: dict[str, list[str]] = {
            "COGNITIVE_PORT": ["app", "port"],
            "COGNITIVE_DB_PATH": ["database", "path"],
            "COGNITIVE_LOG_LEVEL": ["logging", "level"],
            "COGNITIVE_AUTH_ENABLED": ["auth", "enabled"],
            "COGNITIVE_JWT_SECRET": ["auth", "jwt_secret"],
        }
        for env_key, path in env_map.items():
            val = os.getenv(env_key, "")
            if val:
                self._set_nested(self._data, path, self._coerce(val))

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
        data = self._data
        for k in keys:
            if isinstance(data, dict):
                data = data.get(k)
            else:
                return default
        return data if data is not None else default

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


# Singleton
config = Config()
