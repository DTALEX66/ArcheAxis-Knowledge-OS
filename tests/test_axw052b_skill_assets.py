"""AXW-052B: low-risk skill/prompt asset tests.

Verifies:
- assets carry version / source / license / contracts / rollback;
- unreviewed assets are never active (candidate by default);
- review flips an asset into the active projection;
- superseded versions preserve history (append-only);
- task allow/forbid gating works;
- high-risk auto-activation is forbidden; only reviewed active assets
  can authorize tools.
"""

from __future__ import annotations

from app.knowledge.skill_assets import (
    SkillAssetError,
    active_assets,
    authorize_tool,
    register_skill_asset,
    review_asset,
    task_is_allowed,
)

_CONTRACT = {"role": "assistant", "max_tokens": 2000}


def _mkdb(tmp_path) -> str:
    return str(tmp_path / "skill_assets.sqlite")


def _register(db: str, name: str = "summarizer", version: str = "1.0.0", **kw) -> object:
    return register_skill_asset(
        db,
        name=name,
        version=version,
        source_url="https://example.com/summarizer",
        allowed_tasks=["summarize"],
        forbidden_tasks=["execute", "delete"],
        input_contract=_CONTRACT,
        output_contract=_CONTRACT,
        license="MIT",
        rollback_path="data/output/rollback",
        **kw,
    )


def test_register_candidate_by_default(tmp_path) -> None:
    db = _mkdb(tmp_path)
    asset = _register(db)
    assert asset.reviewed is False
    assert asset.active is True  # not superseded, but still unreviewed
    assert active_assets(db) == []  # unreviewed → not projected


def test_review_flips_into_active(tmp_path) -> None:
    db = _mkdb(tmp_path)
    asset = _register(db)
    review_asset(db, asset_id=asset.asset_id, reviewer="human")
    active = active_assets(db)
    assert len(active) == 1
    assert active[0].reviewer == "human"
    assert active[0].version == "1.0.0"


def test_supersede_preserves_history(tmp_path) -> None:
    db = _mkdb(tmp_path)
    v1 = _register(db, version="1.0.0")
    v2 = _register(db, version="2.0.0", supersede=v1.asset_id)
    review_asset(db, asset_id=v2.asset_id, reviewer="human")
    active = active_assets(db, name="summarizer")
    assert [a.asset_id for a in active] == [v2.asset_id]
    # The superseded state is persisted: re-read the version-1 row from a
    # fresh connection (the returned dataclass is an insert-time snapshot).
    import sqlite3

    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT superseded_by FROM skill_assets WHERE asset_id=?", (v1.asset_id,)
        ).fetchone()
    assert row["superseded_by"] == v2.asset_id


def test_task_gating(tmp_path) -> None:
    db = _mkdb(tmp_path)
    asset = _register(db)
    assert task_is_allowed(asset, "summarize") is True
    assert task_is_allowed(asset, "execute") is False
    assert task_is_allowed(asset, "delete files") is False
    assert task_is_allowed(asset, "translate") is False


def test_high_risk_registration_forbidden(tmp_path) -> None:
    db = _mkdb(tmp_path)
    try:
        _register(db, risk_level="high")
        raise AssertionError("expected SkillAssetError")
    except SkillAssetError as exc:
        assert "high-risk" in str(exc)


def test_auto_activation_forbidden_for_medium_risk(tmp_path) -> None:
    db = _mkdb(tmp_path)
    asset = _register(db, risk_level="medium")
    review_asset(db, asset_id=asset.asset_id, reviewer="human")
    try:
        authorize_tool(db, asset_id=asset.asset_id, tool_name="safe_write", actor="agent", auto=True)
        raise AssertionError("expected SkillAssetError")
    except SkillAssetError as exc:
        assert "auto-activation is forbidden" in str(exc)
    # Explicit (non-auto) authorization works.
    result = authorize_tool(db, asset_id=asset.asset_id, tool_name="safe_write", actor="human", auto=False)
    assert result["tool_name"] == "safe_write"


def test_unreviewed_asset_cannot_authorize_tool(tmp_path) -> None:
    db = _mkdb(tmp_path)
    asset = _register(db)
    try:
        authorize_tool(db, asset_id=asset.asset_id, tool_name="safe_write", actor="human")
        raise AssertionError("expected SkillAssetError")
    except SkillAssetError as exc:
        assert "reviewed" in str(exc)
