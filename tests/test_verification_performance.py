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
