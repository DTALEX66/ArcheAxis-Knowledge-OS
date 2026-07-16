"""Tests for file ingestion safety."""

import pytest

from app.ingestion import file as ingestion_file
from app.ingestion.file import IngestionError, ingest_file
from shared.approved_paths import ApprovedRoots


class TestIngestion:
    def test_rejects_outside_project(self):
        with pytest.raises(IngestionError):
            ingest_file("C:/Windows/System32/test.txt")

    def test_rejects_unsupported_extension(self):
        with pytest.raises(IngestionError):
            ingest_file("test.exe")

    def test_rejects_path_traversal(self):
        with pytest.raises(IngestionError):
            ingest_file("../../../etc/passwd")

    def test_rejects_symlink_escape(self, tmp_path, monkeypatch):
        source = tmp_path / "source"
        outside = tmp_path / "outside"
        source.mkdir()
        outside.mkdir()
        (outside / "secret.md").write_text("secret", encoding="utf-8")
        link = source / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"directory symlink unavailable: {exc}")

        monkeypatch.setattr(ingestion_file, "APPROVED_ROOTS", ApprovedRoots(source_roots=[source]))
        with pytest.raises(IngestionError):
            ingest_file(str(link / "secret.md"))
