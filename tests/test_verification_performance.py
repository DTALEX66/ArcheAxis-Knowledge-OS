from __future__ import annotations

import hashlib
import json
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
    runtime = Path(os.environ["ARCHEAXIS_DATA_DIR"]).resolve()

    assert runtime.name.startswith("archeaxis-pytest-")
    assert runtime.is_dir()

    from shared import storage

    assert storage.DB_PATH.parent == runtime


def test_ci_test_jobs_use_minimal_uv_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    import tomllib

    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    ci_requirements = project["dependency-groups"]["ci"]

    assert "astral-sh/setup-uv" in workflow
    # The ci dependency group is exported (at least once) for test/lint jobs.
    assert "uv export --frozen --only-group ci" in workflow
    # Dependency layers are separated: browser, build, adapters, runtime are not
    # forced onto the test/lint job as a single monolithic ci group.
    assert 'pip install -e ".[dev]"' not in workflow
    assert "python -m pip install --require-hashes -r locked-runtime.txt" in workflow
    assert "python -m pip install -r requirements.txt" not in workflow
    assert "defusedxml>=0.7.1" in ci_requirements
    for heavy_dependency in ("litellm", "markitdown", "trafilatura"):
        assert not any(heavy_dependency in requirement for requirement in ci_requirements)


def test_head_convention_scan_batches_git_blob_reads(tmp_path: Path, monkeypatch) -> None:
    import scripts.check_repository_conventions as conventions

    _init_repo(tmp_path)
    # This temporary repository has its own reviewed preservation set; use a
    # real manifest/member pair so batching still includes preservation checks.
    manifest_path = "docs/history/performance-fixture/MANIFEST.json"
    member = b"preserved performance fixture\n"
    manifest = json.dumps({
        "schema": "performance-fixture/v1",
        "files": [{"path": "original.txt", "bytes": len(member),
                   "sha256": hashlib.sha256(member).hexdigest()}],
    }).encode("utf-8")
    target = tmp_path / manifest_path
    target.parent.mkdir(parents=True)
    target.write_bytes(manifest)
    target.with_name("original.txt").write_bytes(member)
    subprocess.run(["git", "add", "docs/history/performance-fixture"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "preservation fixture"], cwd=tmp_path, check=True)
    monkeypatch.setattr(conventions, "_PRESERVED_MANIFESTS", {manifest_path: {
        "schema": "performance-fixture/v1", "bytes": len(manifest),
        "sha256": hashlib.sha256(manifest).hexdigest(),
    }})
    monkeypatch.setattr(conventions, "_PRESERVED_HASH_ONLY_MEMBER_SIZES", {})
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
