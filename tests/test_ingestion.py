"""Tests for file ingestion safety."""
import pytest
from app.ingestion.file import ingest_file, IngestionError


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
