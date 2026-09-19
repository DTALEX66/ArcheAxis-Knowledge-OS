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
    projection = result["derived_projection"]
    assert result["derived_projection_status"] == "available"
    assert projection["schema"] == "archeaxis.derived-projection/v1"
    assert projection["projection_kind"] == "fts"
    assert projection["algorithm"] == "vault-substring"
    assert len(projection["items"]) == 2
    assert all(item["score"] == 1.0 for item in projection["items"])
    result_by_source = {item["source_id"]: item for item in result["results"]}
    assert set(projection["canonical_source_ids"]) == set(result_by_source)
    assert all("/" not in source_id and "\\" not in source_id for source_id in result_by_source)
    assert all(
        result_by_source[item["source_id"]]["source_hash"] == item["source_revision"]
        for item in projection["items"]
    )


def test_search_vault_projection_source_id_is_independent_of_absolute_vault_path(tmp_path) -> None:
    first_base = tmp_path / "first"
    second_base = tmp_path / "second"
    first_base.mkdir()
    second_base.mkdir()
    first_vault, first_store = _make_vault(first_base, {"a.md": "Stable match.\n"})
    second_vault, second_store = _make_vault(second_base, {"a.md": "Stable match.\n"})

    first = search_vault(root=first_vault, store=first_store, query="stable")
    second = search_vault(root=second_vault, store=second_store, query="stable")

    assert first["derived_projection"]["canonical_source_ids"] == second["derived_projection"]["canonical_source_ids"]
    assert first["derived_projection"]["items"][0]["source_revision"] == second["derived_projection"]["items"][0]["source_revision"]


def test_search_vault_case_insensitive(tmp_path) -> None:
    vault, store = _make_vault(tmp_path, {"a.md": "Machine Learning is FUN.\n"})
    result = search_vault(root=vault, store=store, query="machine learning")
    assert len(result["results"]) == 1
    assert result["results"][0]["relative_path"] == "a.md"


def test_search_vault_no_match(tmp_path) -> None:
    vault, store = _make_vault(tmp_path, {"a.md": "Nothing relevant.\n"})
    result = search_vault(root=vault, store=store, query="zzzznomatch")
    assert result["results"] == []
    assert result["derived_projection"] is None
    assert result["derived_projection_status"] == "empty"


def test_search_vault_empty_query_rejected(tmp_path) -> None:
    vault, store = _make_vault(tmp_path, {"a.md": "content\n"})
    with pytest.raises(VaultWorkbenchError, match="must not be empty"):
        search_vault(root=vault, store=store, query="   ")


def test_search_vault_missing_dir_rejected(tmp_path) -> None:
    vault = tmp_path / "no_such_vault"
    store = tmp_path / "compat.sqlite"
    with pytest.raises(ValueError, match="existing directory"):
        search_vault(root=vault, store=store, query="anything")
