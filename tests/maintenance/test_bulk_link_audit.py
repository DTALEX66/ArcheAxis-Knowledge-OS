"""BULK-0907 P04: tests for scripts/maintenance/bulk_link_audit.py."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/maintenance/bulk_link_audit.py"


def _audit(root: Path, docs: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--root", str(root), *docs],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_present_missing_external_and_fragment_are_separate(tmp_path):
    (tmp_path / "target.md").write_text("# Intro\nbody\n", encoding="utf-8")
    (tmp_path / "doc1.md").write_text(
        "# Intro\n[ok](target.md)\n[bad](missing.md)\n[web](https://example.com/a)\n"
        "[a](#Intro)\n[no](#Nope)\n[cross](target.md#Nope)\n",
        encoding="utf-8",
    )
    report = _audit(tmp_path, ["doc1.md"])
    kinds = {row["kind"] for row in report["rows"]}
    assert "PRESENT" in kinds
    assert "MISSING_PATH" in kinds
    assert "EXTERNAL_NOT_CHECKED" in kinds
    assert "ANCHOR_LOCAL" in kinds
    assert "MISSING_FRAGMENT" in kinds
    missing_fragment = [r for r in report["rows"] if r["kind"] == "MISSING_FRAGMENT"]
    assert len(missing_fragment) == 2
    assert any("#Nope" in row["target"] for row in missing_fragment)


def test_code_fence_fake_links_are_not_counted(tmp_path):
    (tmp_path / "real.md").write_text("real", encoding="utf-8")
    (tmp_path / "doc2.md").write_text(
        "[ok](real.md)\n```md\n[fake](missing.md)\n```\n", encoding="utf-8"
    )
    report = _audit(tmp_path, ["doc2.md"])
    kinds = [row["kind"] for row in report["rows"]]
    assert kinds.count("PRESENT") == 1
    assert "MISSING_PATH" not in kinds


def test_same_name_in_different_dirs_resolves_in_own_dir(tmp_path):
    (tmp_path / "sub1").mkdir()
    (tmp_path / "sub2").mkdir()
    (tmp_path / "sub1" / "leaf.md").write_text("a", encoding="utf-8")
    (tmp_path / "sub2" / "leaf.md").write_text("b", encoding="utf-8")
    (tmp_path / "sub1" / "a.md").write_text("[x](leaf.md)\n", encoding="utf-8")
    report = _audit(tmp_path, ["sub1/a.md"])
    present = [r for r in report["rows"] if r["kind"] == "PRESENT"]
    assert present and present[0]["file"] == "sub1/leaf.md"


def test_outside_repo_target_is_marked(tmp_path):
    (tmp_path / "a.md").write_text("[x](../secret.md)\n", encoding="utf-8")
    report = _audit(tmp_path, ["a.md"])
    assert report["rows"][0]["kind"] == "OUTSIDE_REPO"


def test_percent_encoded_space_target_decodes(tmp_path):
    (tmp_path / "dir name").mkdir()
    (tmp_path / "dir name" / "file.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("[x](dir%20name/file.txt)\n", encoding="utf-8")
    report = _audit(tmp_path, ["b.md"])
    present = [r for r in report["rows"] if r["kind"] == "PRESENT"]
    assert present and present[0]["file"] == "dir name/file.txt"


def test_reference_definition_target_is_checked(tmp_path):
    (tmp_path / "ref.md").write_text("r", encoding="utf-8")
    (tmp_path / "c.md").write_text("[ref]: ref.md\nsee [a][ref] end\n", encoding="utf-8")
    report = _audit(tmp_path, ["c.md"])
    kinds = [row["kind"] for row in report["rows"]]
    assert "PRESENT" in kinds  # definition target resolved
    assert report["unsupported_syntax_lines"] >= 1  # reference usage [a][ref] not resolved
