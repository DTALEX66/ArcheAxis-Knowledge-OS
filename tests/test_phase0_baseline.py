from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI

from scripts.generate_phase0_baseline import (
    REQUIRED_REPORTS,
    _as_non_blocking_diagnostic,
    _blocking_gate_failures,
    _extract_warnings,
    _read_head_blobs,
    _temporary_runtime,
    _tracked_paths,
    build_file_inventory,
    build_route_map,
    load_dependency_data,
    write_phase0_reports,
)


def test_file_inventory_is_sorted_and_content_addressed(tmp_path: Path) -> None:
    (tmp_path / "z.py").write_text("print('z')\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("data/\n", encoding="utf-8")

    rows = build_file_inventory(tmp_path, ["z.py", "a.md", ".gitignore"])

    assert [row["path"] for row in rows] == [".gitignore", "a.md", "z.py"]
    assert rows[1]["sha256"] == hashlib.sha256((tmp_path / "a.md").read_bytes()).hexdigest()
    assert rows[2]["bytes"] == len((tmp_path / "z.py").read_bytes())


def test_tracked_paths_preserve_unicode_names_and_ignore_index_and_reports(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    report_dir = tmp_path / "migrations" / "reports" / "phase-0"
    report_dir.mkdir(parents=True)
    (tmp_path / "中文文档.md").write_text("# 文档\n", encoding="utf-8")
    (report_dir / "old.md").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "中文文档.md", str(report_dir)], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=tmp_path, check=True)
    (tmp_path / "staged.md").write_text("staged\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.md"], cwd=tmp_path, check=True)
    (tmp_path / "中文文档.md").write_text("dirty worktree\n", encoding="utf-8")

    tracked = _tracked_paths(
        tmp_path, excluded_prefixes=("migrations/reports/phase-0/",)
    )

    assert tracked == ["中文文档.md"]
    assert _read_head_blobs(tmp_path, tracked) == {"中文文档.md": "# 文档\n".encode()}


def test_warning_extraction_removes_paths_addresses_and_duplicates() -> None:
    output = """D:\\repo\\test.py:1: StarletteDeprecationWarning: deprecated client
D:\\repo\\db.py:2: ResourceWarning: unclosed database in <sqlite3.Connection object at 0xABC123>
D:\\repo\\db.py:2: ResourceWarning: unclosed database in <sqlite3.Connection object at 0xDEF456>
"""

    assert _extract_warnings(output) == [
        "ResourceWarning: unclosed database in <sqlite3.Connection object>",
        "StarletteDeprecationWarning: deprecated client",
    ]


def test_non_blocking_diagnostics_do_not_fail_main_gates() -> None:
    gates = {
        "tests": {"status": "passed"},
        "mypy-baseline": {"status": "observed-failure", "blocking": False},
        "ruff": {"status": "failed", "blocking": True},
    }

    assert _blocking_gate_failures(gates) == ["ruff"]


def test_non_blocking_diagnostic_uses_singular_summary() -> None:
    result = _as_non_blocking_diagnostic(
        {"exit_code": 2, "error_count": 1, "error_file_count": 1}
    )

    assert result["summary"] == "1 error across 1 file; exit code 2"


def test_temporary_runtime_is_unique_cleaned_and_restores_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv("COGNITIVE_DATA_DIR", "original-runtime")

    with _temporary_runtime() as first:
        assert first.is_dir()
        assert Path(os.environ["COGNITIVE_DATA_DIR"]) == first
        (first / "marker.txt").write_text("isolated\n", encoding="utf-8")

    assert not first.exists()
    assert os.environ["COGNITIVE_DATA_DIR"] == "original-runtime"

    with _temporary_runtime() as second:
        assert second != first

    assert not second.exists()


def test_inventory_can_hash_explicit_head_blob_instead_of_dirty_worktree(
    tmp_path: Path,
) -> None:
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("dirty worktree\n", encoding="utf-8")

    rows = build_file_inventory(
        tmp_path,
        ["tracked.txt"],
        file_contents={"tracked.txt": b"HEAD content\n"},
    )

    assert rows[0]["bytes"] == len(b"HEAD content\n")
    assert rows[0]["lines"] == 1
    assert rows[0]["sha256"] == hashlib.sha256(b"HEAD content\n").hexdigest()


def test_route_map_recurses_into_mounted_apps() -> None:
    root = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    kb = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @root.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @kb.post("/cards")
    def create_card() -> dict[str, bool]:
        return {"ok": True}

    root.mount("/kb", kb)

    routes = build_route_map(root)

    assert [(route["path"], route["methods"]) for route in routes] == [
        ("/health", ["GET"]),
        ("/kb/cards", ["POST"]),
    ]


def test_dependency_loader_supports_project_and_optional_arrays(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
requires-python = ">=3.10"
authors = [
  { name = "Example" },
]
dependencies = [
  "fastapi>=0.1",
  "requests>=2",
]
[project.optional-dependencies]
dev = ["pytest>=7", "ruff>=0.5"]
""",
        encoding="utf-8",
    )

    data = load_dependency_data(pyproject)

    assert data["project"]["requires-python"] == ">=3.10"
    assert data["project"]["dependencies"] == ["fastapi>=0.1", "requests>=2"]
    assert data["project"]["optional-dependencies"]["dev"] == ["pytest>=7", "ruff>=0.5"]


def test_phase0_writer_creates_all_required_reports(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Repo\n", encoding="utf-8")
    output = repo / "migrations" / "reports" / "phase-0"

    written = write_phase0_reports(
        repo_root=repo,
        output_dir=output,
        tracked_paths=["README.md"],
        routes=[
            {
                "path": "/health",
                "methods": ["GET", "POST"],
                "name": "health",
                "service": "core",
            },
            {
                "path": "/ir/health",
                "methods": ["GET"],
                "name": "ir-health",
                "service": "inspiration-research",
            },
        ],
        git_head="abc123",
        dependency_data={"project": {"dependencies": ["fastapi>=0.1"]}},
        gate_results={
            "root-tests": {
                "status": "passed",
                "summary": "1 passed, 1 warning",
                "warnings": ["ResourceWarning: unclosed database"],
            },
            "knowledge-base-tests": {
                "status": "passed",
                "summary": "1 passed",
                "command": "python -m pytest tests -q",
                "working_directory": "knowledge_base",
            },
            "mypy-diagnostic": {
                "status": "observed-failure",
                "summary": "42 errors across 18 files",
                "blocking": False,
            },
            "inspiration-research-tests": {
                "status": "observed-failure",
                "summary": "1 error during collection",
                "command": "python -m pytest Inspiration-Research/tests -q",
                "blocking": False,
            },
        },
        security_findings=[],
    )

    assert {path.name for path in written} == set(REQUIRED_REPORTS)
    with (output / "FILE_INVENTORY.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["path"] for row in rows] == ["README.md"]
    route_map = json.loads((output / "API_ROUTE_MAP.json").read_text(encoding="utf-8"))
    assert route_map["git_head"] == "abc123"
    assert route_map["route_count"] == 2
    assert route_map["operation_count"] == 3
    assert route_map["services"]["core"]["operation_count"] == 2
    assert route_map["services"]["inspiration-research"]["operation_count"] == 1
    assert route_map["routes"][0]["path"] == "/health"
    test_baseline = (output / "TEST_BASELINE.md").read_text(encoding="utf-8")
    assert "工作目录：`knowledge_base`" in test_baseline
    assert "- ResourceWarning: unclosed database" in test_baseline
    assert "database\n\n### knowledge-base-tests" in test_baseline
    assert "database### knowledge-base-tests" not in test_baseline
    assert "最终 staged diff" in test_baseline
    assert "git diff --cached --check" in test_baseline
    assert "observed-failure" in test_baseline
    assert "42 errors across 18 files" in test_baseline
    assert "inspiration-research-tests" in test_baseline
    assert "1 error during collection" in test_baseline
    security_baseline = (output / "SECURITY_BASELINE.md").read_text(encoding="utf-8")
    assert "端点级 RBAC" in security_baseline
    assert "SSRF" in security_baseline
    assert "路径 containment" in security_baseline
    architecture_gaps = (output / "ARCHITECTURE_GAPS.md").read_text(encoding="utf-8")
    assert "app ↔ knowledge_base ↔ shared" in architecture_gaps
    assert "27 个非测试运行时文件" in architecture_gaps
    reuse_decisions = (output / "REUSE_DECISIONS.md").read_text(encoding="utf-8")
    assert "Crawl4AI" in reuse_decisions
    assert "MarkItDown" in reuse_decisions
    taskpack = (output / "PHASE_1_TASKPACK.md").read_text(encoding="utf-8")
    assert "TP1.0 基线可信度" in taskpack
    assert "Inspiration-Research \\\n  shared-contracts" in taskpack
    assert "Obsidian-Assistance" not in "\n".join(
        path.read_text(encoding="utf-8")
        for path in written
        if path.suffix in {".md", ".json", ".csv"}
    )
