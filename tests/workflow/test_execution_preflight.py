from pathlib import Path

from scripts.workflow.execution_preflight import run


def test_preflight_reports_interpreter_and_git_fields(monkeypatch, tmp_path: Path):
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        "scripts.workflow.execution_preflight._git",
        lambda root, *args: "main" if args[:2] == ("branch", "--show-current") else "sha",
    )
    monkeypatch.setattr(
        "scripts.workflow.execution_preflight._markdown_files", lambda root: []
    )
    report = run(tmp_path, [])
    assert report["schema"] == "archeaxis.execution-preflight/v1"
    assert report["interpreter"]
    assert report["private_state_opened"] is False
    assert report["passed"] is True


def test_preflight_fails_for_non_git_directory(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "scripts.workflow.execution_preflight._markdown_files", lambda root: []
    )
    monkeypatch.setattr(
        "scripts.workflow.execution_preflight._git", lambda root, *args: "sha"
    )
    report = run(tmp_path, [])
    assert report["git"]["is_repository"] is False
    assert report["passed"] is False


def test_preflight_fails_on_missing_relative_link(monkeypatch, tmp_path: Path):
    document = tmp_path / "guide.md"
    document.write_text("[missing](no-such-file.md)\n", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.workflow.execution_preflight._markdown_files", lambda root: [document]
    )
    monkeypatch.setattr(
        "scripts.workflow.execution_preflight._git", lambda root, *args: "value"
    )
    report = run(tmp_path, [])
    assert report["markdown_links"]["broken_count"] == 1
    assert report["passed"] is False
