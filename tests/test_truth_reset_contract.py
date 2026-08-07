from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agents_doc_uses_learning_workspace_positioning() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    # The agent-facing entry must not claim the legacy "Cognitive-OS cognition
    # loop" identity as the project mission.
    assert "Human" in agents or "Learning Workspace" in agents
    assert "learning" in agents.lower()
    # The legacy mission framing must not be the leading identity.
    assert not agents.lstrip().startswith("# AGENTS.md - Cognitive-OS")
    assert "information -> attention -> understanding -> structure" not in agents


def test_bad_projection_endpoints_fail_closed_with_501() -> None:
    """Unimplemented renderers must 501, not raise ImportError at runtime."""
    api = (ROOT / "knowledge_base" / "api.py").read_text(encoding="utf-8")
    projection = (ROOT / "shared" / "obsidian_projection.py").read_text(encoding="utf-8")

    # The renderers referenced by the endpoints must exist in the projection
    # module, OR the endpoint must explicitly return 501 capability_unavailable.
    for _endpoint_import, required in (
        ("render_card", "render_card"),
        ("render_review_card", "render_review_card"),
        ("render_machine_knowledge", "render_machine_knowledge"),
    ):
        defined = f"def {required}(" in projection
        if not defined:
            # If the renderer is missing, the endpoint must return 501.
            assert "capability_unavailable" in api, f"{required} missing and not gated"
            assert "501" in api or "status_code=501" in api or "HTTPException" in api
