"""DOM harness failures must explain missing setup or broken probe predicates."""
import pytest

from tests import dom_harness


def test_missing_locked_dependencies_fail_before_starting_node(tmp_path, monkeypatch):
    monkeypatch.setattr(dom_harness, "REPO", tmp_path)
    monkeypatch.setattr(dom_harness.subprocess, "run", lambda *a, **k: pytest.fail("Node must not start"))
    with pytest.raises(RuntimeError, match="npm ci --prefix frontend"):
        dom_harness.evaluate("return true", "<p>fixture</p>")


def test_broken_predicate_reports_node_error_instead_of_hiding_stderr():
    with pytest.raises(RuntimeError, match="synthetic predicate failure"):
        dom_harness.evaluate("throw new Error('synthetic predicate failure')", "<p>fixture</p>")
