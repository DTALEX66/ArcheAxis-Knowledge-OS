"""Shared test fixtures."""
import secrets
import sys
from pathlib import Path

import pytest

# Make app importable from tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def admin_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Provision an isolated, explicit administrator key for one test."""
    api_key = secrets.token_urlsafe(32)
    monkeypatch.setenv("COGNITIVE_API_KEY", api_key)
    return api_key
