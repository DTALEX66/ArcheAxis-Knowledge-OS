from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _init_repo(path: Path, file_count: int = 4) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=path,
        check=True,
    )
    for index in range(file_count):
        (path / f"tracked-{index}.txt").write_text(
            f"content {index}\n", encoding="utf-8", newline="\n"
        )
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=path, check=True)


def test_pytest_session_uses_an_isolated_runtime_root() -> None:
    runtime = Path(os.environ["COGNITIVE_DATA_DIR"]).resolve()

    assert runtime.name.startswith("cognitive-pytest-")
    assert runtime.is_dir()

    from shared import storage

    assert storage.DB_PATH.parent == runtime


def test_ci_test_jobs_use_minimal_uv_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    ci_requirements_path = root / "requirements-ci.txt"

    assert ci_requirements_path.is_file()
    ci_requirements = ci_requirements_path.read_text(encoding="utf-8").lower()
    assert "astral-sh/setup-uv" in workflow
    assert workflow.count("uv pip install --system -r requirements-ci.txt") >= 2
    assert 'pip install -e ".[dev]"' not in workflow
    assert "uv export --frozen --no-dev --no-emit-project" in workflow
    assert "python -m pip install --require-hashes -r locked-runtime.txt" in workflow
    assert "python -m pip install -r requirements.txt" not in workflow
    assert "defusedxml" in ci_requirements
    for heavy_dependency in ("litellm", "markitdown", "trafilatura"):
        assert heavy_dependency not in ci_requirements


def test_head_convention_scan_batches_git_blob_reads(tmp_path: Path, monkeypatch) -> None:
    import scripts.check_repository_conventions as conventions

    _init_repo(tmp_path)
    real_run = conventions.subprocess.run
    git_calls: list[tuple[str, ...]] = []

    def counting_run(command, *args, **kwargs):
        if command and command[0] == "git":
            git_calls.append(tuple(command))
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(conventions.subprocess, "run", counting_run)

    assert conventions.scan_git_repository(tmp_path, source="head") == []
    assert len(git_calls) == 2
    assert git_calls[0][:3] == ("git", "ls-tree", "-r")
    assert git_calls[1] == ("git", "cat-file", "--batch")
