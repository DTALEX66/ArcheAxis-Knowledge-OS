from pathlib import Path
import subprocess
import sys

from scripts import taskpack_paths


def test_default_taskpack_is_current_r5():
    assert taskpack_paths.DEFAULT_PACK_RELATIVE == Path("docs/authority/taskpack-0912-r5")
    assert taskpack_paths.default_pack_root(Path("D:/repo")) == Path(
        "D:/repo/docs/authority/taskpack-0912-r5"
    )


def test_historical_pack_can_be_selected_explicitly():
    root = Path("D:/repo")
    assert taskpack_paths.resolve_pack_root(root, Path("docs/authority/taskpack-0910-r3")) == Path(
        "D:/repo/docs/authority/taskpack-0910-r3"
    )


def test_relative_paths_resolve_against_repo_root():
    root = Path("D:/repo")
    assert taskpack_paths.resolve_pack_root(root, Path("taskpack")) == Path("D:/repo/taskpack")


def test_historical_checkers_refuse_an_implicit_pack():
    checker = Path(__file__).parents[1] / "scripts" / "check_format_matrix.py"
    result = subprocess.run([sys.executable, str(checker)], capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "pass --matrix" in result.stderr
