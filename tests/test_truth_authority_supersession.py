import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_truth_spine_routes_current_execution_to_r6_m0_and_marks_august_contracts_historical() -> None:
    truth = (ROOT / 'docs/history/repository-consolidation-20261019/truth-snapshots/CURRENT_STATE_TRUTH.md').read_text(encoding="utf-8")
    index = (ROOT / "docs" / "truth" / "README.md").read_text(encoding="utf-8")

    assert "HISTORICAL SNAPSHOT" in truth
    assert "R6" in truth and "M0" in truth
    assert "not the current execution queue" in truth
    pointer = json.loads((ROOT / "docs/current/AAOS-ACTIVE-EXECUTION.json").read_text(encoding="utf-8"))
    assert "../current/AAOS-ACTIVE-EXECUTION.json" in index
    assert "../current/AAOS-AUTHORITY-ROUTES.json" in index
    assert "../" + pointer["active_progress"].removeprefix("docs/") in index
    assert "../history/repository-consolidation-20261019/MANIFEST.json" in index
    assert (ROOT / pointer["active_taskpack"] / "TASKPACK.md").is_file()
    assert (ROOT / pointer["active_progress"]).is_file()
    # The original explanatory claims belong to the preserved pre-move index.
    manifest = json.loads((ROOT / "docs/history/repository-consolidation-20261019/MANIFEST.json").read_text(encoding="utf-8"))
    snapshot = next(row for row in manifest["navigation_snapshots"] if row["original_path"] == "docs/truth/README.md")
    raw = (ROOT / snapshot["archive_path"]).read_bytes()
    assert len(raw) == snapshot["bytes"]
    assert hashlib.sha256(raw).hexdigest() == snapshot["sha256"]
    before = raw.decode("utf-8")
    assert "AUTHORITY_CONTRACT.md" in before
    assert "HISTORICAL / SUPERSEDED" in before
    assert "check_r6_taskpack_authority.py" in before
    assert "不校验全部 2026-08 冻结文档和增补包的 SHA-256" in before
