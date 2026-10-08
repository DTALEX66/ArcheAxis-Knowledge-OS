"""The saved-snapshot route uses one extractor and records fallback honestly."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "html_absorption", ROOT / "services/python-workers/web/worker_html.py"
)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

ARTICLE = "A measured result must remain bound to the original source and its revision. " * 12


def test_real_article_extractor_removes_navigation_and_keeps_bound_offsets(tmp_path):
    source = tmp_path / "article.html"
    source.write_text(
        f"<html><body><nav>NOISE_NAV</nav><article><h1>Experiment</h1>"
        f"<p>{ARTICLE}</p><p>{ARTICLE}</p></article><footer>NOISE_FOOTER</footer>"
        "<script>DO_NOT_EXECUTE</script></body></html>", encoding="utf-8"
    )
    result = worker.extract(str(source))
    assert result["loss_receipt"]["params"]["extraction"]["selected_engine"] == "trafilatura"
    assert "NOISE_NAV" not in result["text"]
    assert "NOISE_FOOTER" not in result["text"]
    assert "DO_NOT_EXECUTE" not in result["text"]
    assert ARTICLE.strip() in result["text"]
    for anchor in result["structure"]:
        assert result["text"][anchor["char_start"]:anchor["char_end"]].strip()


def test_missing_dependency_is_explicit_and_stdlib_preserves_snapshot(tmp_path, monkeypatch):
    source = tmp_path / "fragment.html"
    source.write_text("<p>Retained note</p>", encoding="utf-8")
    def missing(_html):
        raise ImportError("synthetic missing dependency")
    monkeypatch.setattr(worker, "_article_text", missing)
    result = worker.extract(str(source))
    assert result["text"] == "Retained note"
    extraction = result["loss_receipt"]["params"]["extraction"]
    assert extraction["selected_engine"] == "stdlib-html-parser"
    assert extraction["fallback_used"] is True
    assert extraction["attempts"][0]["status"] == "missing_dependency"
    assert result["format_execution_receipt"]["fallback"]["used"] is True


def test_empty_or_broken_donor_is_not_silent_success(tmp_path, monkeypatch):
    source = tmp_path / "fragment.html"
    source.write_text("<p>Retained note</p>", encoding="utf-8")
    monkeypatch.setattr(worker, "_article_text", lambda _html: (None, "test-version"))
    result = worker.extract(str(source))
    assert result["text"] == "Retained note"
    assert result["loss_receipt"]["params"]["extraction"]["attempts"][0]["status"] == "empty"
