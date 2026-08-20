from __future__ import annotations

from app.ingestion import web_screenshot


def test_find_browser_uses_chrome_when_edge_is_not_available(monkeypatch) -> None:
    available = {"google-chrome": "/usr/bin/google-chrome"}
    monkeypatch.setattr(web_screenshot.shutil, "which", available.get)

    assert web_screenshot.find_browser() == "/usr/bin/google-chrome"
    assert web_screenshot.find_edge() == "/usr/bin/google-chrome"
