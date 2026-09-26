from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_truth_spine_routes_current_execution_to_r6_m0_and_marks_august_contracts_historical() -> None:
    truth = (ROOT / "docs" / "truth" / "CURRENT_STATE_TRUTH.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "truth" / "README.md").read_text(encoding="utf-8")

    assert "HISTORICAL SNAPSHOT" in truth
    assert "R6" in truth and "M0" in truth
    assert "not the current execution queue" in truth
    assert "AUTHORITY_CONTRACT.md" in index
    assert "HISTORICAL / SUPERSEDED" in index
    assert "check_r6_taskpack_authority.py" in index
    assert "全部 2026-08 冻结文档和增补包的 SHA-256" in index
