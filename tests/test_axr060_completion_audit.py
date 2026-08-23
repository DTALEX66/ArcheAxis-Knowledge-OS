from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "current" / "AXR_060_COMPLETION_AUDIT_2026-08-23.md"
TASK_IDS = tuple(
    f"AXR-060-{number:03d}"
    for number in (
        1,
        2,
        3,
        101,
        102,
        103,
        201,
        202,
        203,
        204,
        301,
        302,
        303,
        304,
        401,
        402,
        403,
        404,
        501,
        502,
        503,
        601,
        602,
        603,
        604,
        701,
        702,
        703,
        704,
    )
)


def test_axr060_audit_covers_every_task_and_release_blocker_once() -> None:
    text = AUDIT.read_text(encoding="utf-8")

    found_tasks = re.findall(r"AXR-060-\d{3}", text)
    assert sorted(found_tasks) == sorted(TASK_IDS)
    for blocker in range(1, 13):
        assert text.count(f"B{blocker:02d}") == 1


def test_axr060_audit_keeps_release_and_product_completion_separate() -> None:
    text = AUDIT.read_text(encoding="utf-8")

    assert "整体结论：PARTIAL" in text
    assert "RELEASE_PUBLISHED：PASS" in text
    assert "不等于" in text
    assert "NOT_EXECUTED" in text


def test_tracked_current_surfaces_do_not_retain_stale_sha_snapshots() -> None:
    release = json.loads(
        (ROOT / "reports" / "release" / "v0.6.9" / "release-evidence.json").read_text(
            encoding="utf-8"
        )
    )
    allowed_sha = release["source"]["commit_sha"]
    surfaces = [ROOT / "SYSTEM_BOUNDARY.md"]
    surfaces.extend((ROOT / "docs" / "current").glob("*"))
    surfaces.extend((ROOT / "reports" / "current").glob("*"))
    found: set[str] = set()
    for path in surfaces:
        if not path.is_file():
            continue
        found.update(re.findall(r"\b[0-9a-f]{40}\b", path.read_text(encoding="utf-8")))

    assert found <= {allowed_sha}
    assert sorted(path.name for path in (ROOT / "reports" / "current").iterdir()) == [
        "README.md"
    ]
