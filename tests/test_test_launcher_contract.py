from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_test_launcher_accepts_git_worktrees() -> None:
    launcher = (ROOT / "scripts" / "ci" / "run_tests.sh").read_text(encoding="utf-8")

    assert '[ ! -e "$ROOT_UNIX/.git" ]' in launcher
    assert '[ ! -d "$ROOT_UNIX/.git" ]' not in launcher


def test_project_test_launcher_uses_short_windows_safe_basetemp() -> None:
    launcher = (ROOT / "scripts" / "ci" / "run_tests.sh").read_text(encoding="utf-8")

    assert "git -C \"$ROOT_UNIX\" rev-parse --path-format=absolute --git-common-dir" in launcher
    assert 'RUNTIME="$PROJECT_DATA_ROOT/.hermes/task-runtime"' in launcher
    assert 'BASETEMP="$RUNTIME/t-$BASHPID"' in launcher
    assert 'BASETEMP="$TMPDIR_RUNTIME/pytest-$(date' not in launcher


def test_project_test_launcher_keeps_uv_cache_in_the_project() -> None:
    launcher = (ROOT / "scripts" / "ci" / "run_tests.sh").read_text(encoding="utf-8")

    assert 'UV_CACHE_DIR="$PROJECT_DATA_ROOT/.hermes/cache/uv"' in launcher
    assert "export UV_CACHE_DIR" in launcher
