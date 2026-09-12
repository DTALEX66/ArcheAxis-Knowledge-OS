from __future__ import annotations

import subprocess

import pytest

from app.ingestion import web_screenshot


def test_find_browser_uses_chrome_when_edge_is_not_available(monkeypatch) -> None:
    available = {"google-chrome": "/usr/bin/google-chrome"}
    monkeypatch.setattr(web_screenshot.shutil, "which", available.get)

    assert web_screenshot.find_browser() == "/usr/bin/google-chrome"
    assert web_screenshot.find_edge() == "/usr/bin/google-chrome"


def test_browser_environment_uses_short_project_hermes_root(tmp_path) -> None:
    output = tmp_path / ".project-local" / "task-runtime" / "pytest-tmp" / "deep" / "page.png"

    environment = web_screenshot._browser_environment(output)

    assert environment["TMP"] == str(tmp_path / ".project-local")
    assert environment["TEMP"] == str(tmp_path / ".project-local")
    assert environment["TMPDIR"] == str(tmp_path / ".project-local")


def test_browser_environment_uses_output_parent_outside_project_runtime(monkeypatch) -> None:
    output = web_screenshot.Path("outside-runtime/page.png")
    monkeypatch.setattr(web_screenshot.Path, "mkdir", lambda *args, **kwargs: None)

    environment = web_screenshot._browser_environment(output)

    assert environment["TMP"] == str(output.parent.resolve())


def test_wait_for_screenshot_allows_edge_child_to_finish(monkeypatch, tmp_path) -> None:
    states = iter((False, True))
    monkeypatch.setattr(web_screenshot, "_has_nonempty_file", lambda _: next(states))
    monkeypatch.setattr(web_screenshot.time, "sleep", lambda _: None)

    assert web_screenshot._wait_for_screenshot(tmp_path / "page.png") is True


def test_screenshot_reports_browser_exit_code_when_no_png_is_written(monkeypatch, tmp_path) -> None:
    """A zero exit code without the requested PNG must remain diagnosable."""
    monkeypatch.setattr(web_screenshot, "find_browser", lambda: "browser-under-test")
    monkeypatch.setattr(
        web_screenshot.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"", stderr=b""),
    )
    monkeypatch.setattr(web_screenshot, "_wait_for_screenshot", lambda _: False)

    with pytest.raises(web_screenshot.WebScreenshotError, match=r"exit_code=0"):
        web_screenshot.screenshot_web("file:///fixture.html", tmp_path / "missing.png")
