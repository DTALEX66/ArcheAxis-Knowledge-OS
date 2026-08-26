from __future__ import annotations

from app.ingestion import web_screenshot


def test_find_browser_uses_chrome_when_edge_is_not_available(monkeypatch) -> None:
    available = {"google-chrome": "/usr/bin/google-chrome"}
    monkeypatch.setattr(web_screenshot.shutil, "which", available.get)

    assert web_screenshot.find_browser() == "/usr/bin/google-chrome"
    assert web_screenshot.find_edge() == "/usr/bin/google-chrome"


def test_browser_environment_uses_short_project_hermes_root(tmp_path) -> None:
    output = tmp_path / ".hermes" / "task-runtime" / "pytest-tmp" / "deep" / "page.png"

    environment = web_screenshot._browser_environment(output)

    assert environment["TMP"] == str(tmp_path / ".hermes")
    assert environment["TEMP"] == str(tmp_path / ".hermes")
    assert environment["TMPDIR"] == str(tmp_path / ".hermes")


def test_browser_environment_uses_output_parent_outside_project_runtime(monkeypatch) -> None:
    output = web_screenshot.Path("outside-runtime/page.png")
    monkeypatch.setattr(web_screenshot.Path, "mkdir", lambda *args, **kwargs: None)

    environment = web_screenshot._browser_environment(output)

    assert environment["TMP"] == str(output.parent.resolve())
