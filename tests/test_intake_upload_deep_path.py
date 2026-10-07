"""An intake upload must hand its converters a name the operating system can still open.

`intake_upload` writes the upload to a temporary file next to the workspace database and gives that
file to third-party converters, which open the name they are handed. Under a deep workspace root a
plain name past the Windows limit does not fail as a path problem: the engine chain answers
"No engine could convert xlsx file", so a path limit is reported as a missing engine and an operator
goes looking for an engine that was never at fault.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.multi_format import ConversionTrace
from app.workspace import service
from shared.paths import native_path

MAX_PLAIN_DIRECTORY = 251


def _migrate(database: Path, tmp_path: Path) -> None:
    """A migrated workspace database, opened the way the product opens a deep one."""
    from shared.migration_runner import MigrationOperator

    Path(native_path(database)).touch()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups")
    operator.apply("research.sqlite")
    operator.apply("workspace.sqlite")


def _deep_database(tmp_path: Path) -> Path:
    node = tmp_path / "ws"
    if len(str(node)) > MAX_PLAIN_DIRECTORY:
        pytest.skip(f"the temporary base is already {len(str(node))} characters deep")
    Path(native_path(node)).mkdir(parents=True, exist_ok=True)
    while len(str(node / ("d" * 24))) <= MAX_PLAIN_DIRECTORY - 26:
        node = node / ("d" * 24)
        Path(native_path(node)).mkdir(parents=True, exist_ok=True)
    remainder = MAX_PLAIN_DIRECTORY - len(str(node)) - 1
    if remainder > 1:
        node = node / ("c" * (remainder - 1))
        Path(native_path(node)).mkdir(parents=True, exist_ok=True)
    database = node / "workspace.sqlite"
    assert len(str(node / "intake_uploads" / ".upload-abcdefgh.xlsx")) > 260, (
        "the conversion temp file must sit past the plain-open limit, which is what the "
        "converters are handed")
    return database


def _patch_converter(monkeypatch) -> list[str]:
    """Patch the engine seam itself, so the name the converters receive is observable."""
    seen: list[str] = []

    def fake(source: Path):
        seen.append(str(source))
        trace = ConversionTrace(attempted_engines=("fake",), fallback_used=False, fallback_reason="")
        return "converted paragraph content", "fake-engine", trace

    monkeypatch.setattr(service, "convert_file_with_trace", fake)
    return seen


def test_the_converter_receives_the_verbatim_name_of_the_temp_file(tmp_path: Path, monkeypatch) -> None:
    seen = _patch_converter(monkeypatch)
    database = _deep_database(tmp_path)
    _migrate(database, tmp_path)
    result = service.intake_upload(
        file_name="notes.txt", content=b"hello deep intake", db_path=database
    )
    assert seen, "no conversion happened, so the seam was not exercised"
    assert seen[0].startswith("\\\\?\\"), (
        f"the converters were handed an ordinary name, which past the limit they cannot open: {seen[0]}")
    assert result.get("raw_sha256"), result


def test_a_deep_upload_is_intaken_and_its_archive_copy_is_readable(tmp_path: Path, monkeypatch) -> None:
    _patch_converter(monkeypatch)
    database = _deep_database(tmp_path)
    _migrate(database, tmp_path)
    content = b"hello deep intake"
    result = service.intake_upload(file_name="notes.txt", content=content, db_path=database)
    stored = database.parent / "intake_uploads"
    names = [entry.name for entry in Path(native_path(stored)).iterdir()]
    assert any(name.endswith(".txt") for name in names), names
    assert result["source_type"] == "file"
