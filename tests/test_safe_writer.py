"""Tests for safe writer."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from shared.safe_writer import SafeWriter


class TestSafeWriter:
    def test_dry_run_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = SafeWriter(project_root=tmp, dry_run=True)
            item = writer.apply_write("test.md", "# Hello")
            assert item.action == "create"
            assert not Path(tmp, "test.md").exists()
            report = writer.write_report()
            assert report["plan"]["dry_run"] is True

    def test_apply_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = SafeWriter(project_root=tmp, dry_run=False)
            writer.apply_write("subdir/test.md", "# Hello World")
            target = Path(tmp, "subdir", "test.md")
            assert target.exists()
            assert target.read_text(encoding="utf-8") == "# Hello World"

    def test_overwrite_backs_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create initial file
            target = Path(tmp, "doc.md")
            target.write_text("original")

            writer = SafeWriter(project_root=tmp, dry_run=False)
            item = writer.apply_write("doc.md", "updated")
            assert item.action == "overwrite"
            assert item.backup_path is not None
            assert Path(item.backup_path).exists()
            assert "original" in Path(item.backup_path).read_text()
            assert target.read_text() == "updated"

    def test_path_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = SafeWriter(project_root=tmp, dry_run=True)
            with pytest.raises(ValueError, match="path traversal"):
                writer.apply_write("../outside.md", "evil")

    def test_absolute_path_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = SafeWriter(project_root=tmp, dry_run=True)
            with pytest.raises(ValueError, match="path traversal|absolute"):
                writer.apply_write("/etc/passwd", "evil")
