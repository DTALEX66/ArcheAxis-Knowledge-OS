"""Tests for app.workspace.vault.search_vault (H3 text search).

Uses real temp vault dirs + ImportSession (sqlite store). NOTE:
conftest redirects TMPDIR into the hidden .project-local/ tree; ImportSession
walks the vault root directly (no hidden-path skip), so real temp dirs
work here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.workspace.vault import VaultWorkbenchError, search_vault


def _make_vault(tmp_path: Path, files: dict[str, str]) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    for rel, content in files.items():
        p = vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    store = tmp_path / "compat.sqlite"
    return vault, store


def test_search_vault_finds_term(monkeypatch, tmp_path) -> None:
    vault, store = _make_vault(
        tmp_path,
        {
            "notes/intro.md": "# Intro\n\nSpaced repetition improves retention.\n",
            "notes/other.md": "No match here.\n",
            "cards/card.md": "## Card\n\nSpaced repetition is core.\n",
        },
    )
    # ImportSession validates vault root is a dir — temp dirs are real dirs, fine.
    result = search_vault(root=vault, store=store, query="spaced repetition")
    assert result["schema_version"] == "v1"
    assert result["query"] == "spaced repetition"
    paths = {r["relative_path"] for r in result["results"]}
    assert "notes/intro.md" in paths
    assert "cards/card.md" in paths
    assert "notes/other.md" not in paths
    # snippet contains the match, source_hash present
    for r in result["results"]:
        assert "spaced repetition" in r["snippet"].casefold()
        assert r["source_hash"]


def test_search_vault_case_insensitive(tmp_path) -> None:
    vault, store = _make_vault(tmp_path, {"a.md": "Machine Learning is FUN.\n"})
    result = search_vault(root=vault, store=store, query="machine learning")
    assert len(result["results"]) == 1
    assert result["results"][0]["relative_path"] == "a.md"


def test_search_vault_no_match(tmp_path) -> None:
    vault, store = _make_vault(tmp_path, {"a.md": "Nothing relevant.\n"})
    result = search_vault(root=vault, store=store, query="zzzznomatch")
    assert result["results"] == []


def test_search_vault_empty_query_rejected(tmp_path) -> None:
    vault, store = _make_vault(tmp_path, {"a.md": "content\n"})
    with pytest.raises(VaultWorkbenchError, match="must not be empty"):
        search_vault(root=vault, store=store, query="   ")


def test_search_vault_missing_dir_rejected(tmp_path) -> None:
    vault = tmp_path / "no_such_vault"
    store = tmp_path / "compat.sqlite"
    with pytest.raises(ValueError, match="existing directory"):
        search_vault(root=vault, store=store, query="anything")
