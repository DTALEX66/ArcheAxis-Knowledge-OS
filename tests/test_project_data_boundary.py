from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tests_do_not_write_tracked_current_reports() -> None:
    offenders: list[str] = []
    for test_root in (ROOT / "tests", ROOT / "integration-tests"):
        for path in test_root.rglob("*.py"):
            if path == Path(__file__):
                continue
            text = path.read_text(encoding="utf-8")
            if 'Path("reports/current")' in text or "Path('reports/current')" in text:
                offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_retrieval_evaluation_defaults_to_ignored_task_artifacts() -> None:
    script = (ROOT / "scripts" / "pipeline" / "eval_retrieval.py").read_text(
        encoding="utf-8"
    )

    assert '"task-artifacts" / "eval-retrieval"' in script
    assert '"reports" / "current"' not in script
