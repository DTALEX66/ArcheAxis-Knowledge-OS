"""The raw-asset store must survive a deep workspace, and must not leak the prefix anywhere.

Reproduced at the shape the product actually builds: the store root itself is only ~194
characters - well under every limit - and it is the file the store generates for itself,
``.{64-character digest}.tmp``, that reaches 261 and is refused with ERROR_FILE_NOT_FOUND.
That is why `shared.paths.native_path` carries no length threshold: only the caller knows how
long the final name will be, and here the name is not known in advance at all.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

TEMP_SUFFIX_COST = 1 + 64 + 4  # ".{sha256}.tmp" before the prefix character


def _deep_store_root(tmp_path: Path) -> Path:
    """A store root a plain path can create, whose generated temporary file it cannot."""
    node = tmp_path / "workspace" / "source_archive"
    node.mkdir(parents=True, exist_ok=True)
    while len(str(node / "raw-assets")) + TEMP_SUFFIX_COST < 261:
        node = node / ("c" * 24)
        node.mkdir(parents=True, exist_ok=True)
    root = node / "raw-assets"
    assert len(str(root)) < 261, "the directory itself stays ordinary; only the name is long"
    return root


def test_the_store_writes_and_reads_at_the_depth_the_product_builds(tmp_path: Path) -> None:
    raw_asset = importlib.import_module("app.ingestion.raw_asset")
    paths = importlib.import_module("shared.paths")
    store = raw_asset.RawAssetStore(root=_deep_store_root(tmp_path))

    record = store.store_original(b"immutable source bytes", "notes.md")

    assert store.has(record.sha256)
    # resolve() hands out the plain path on purpose, so a consumer reads it through the same
    # IO boundary the store uses; the value itself must never be stored with a prefix.
    handle = store.resolve(record.sha256)
    assert handle == store.root / record.sha256
    assert paths.ordinary_path(handle) == handle
    assert Path(paths.native_path(handle)).read_bytes() == b"immutable source bytes"
    listed = store.list_records()
    assert [item.sha256 for item in listed] == [record.sha256], listed
    assert listed[0].source_name == "notes.md"
    # the failure sidecar is written by the same store, so it has to reach the same depth
    store._record_failure(record.sha256, "notes.md", "conversion exploded")
    assert store.has_failure(record.sha256)
    assert store._read_failure_reason(record.sha256) == "conversion exploded"


def test_no_verbatim_prefix_reaches_a_record_a_return_value_or_the_store_root(
    tmp_path: Path,
) -> None:
    raw_asset = importlib.import_module("app.ingestion.raw_asset")
    paths = importlib.import_module("shared.paths")
    root = _deep_store_root(tmp_path)
    store = raw_asset.RawAssetStore(root=root)

    record = store.store_original(b"projection bytes", "report.csv")

    assert store.root == root, "the store keeps the plain root it was given"
    assert store.resolve(record.sha256) == root / record.sha256
    assert paths.ordinary_path(store.resolve(record.sha256)) == store.resolve(record.sha256)
    assert not str(store._metadata_path(record.sha256)).startswith("\\\\?\\")


@pytest.mark.skipif(sys.platform != "win32", reason="the verbatim prefix is a Windows fact")
def test_the_helper_prefixes_without_a_threshold_and_round_trips(monkeypatch) -> None:
    paths = importlib.reload(importlib.import_module("shared.paths"))
    short = Path("C:/work/store")
    native = paths.native_path(short)
    assert native.startswith("\\\\?\\"), "a short directory must still be prefixed: the name is what crosses the limit"
    assert paths.ordinary_path(native) == short
    assert paths.native_path(native) == native, "a second pass must not double-prefix"
    assert paths.native_path(Path("relative/only")) == str(Path("relative/only")), \
        "a relative path has no meaning under the verbatim form"
    # a UNC name is not a drive path with a leading slash: the naive prefix produced
    # `\\?\\\server\...`, which SQLite then reported as `invalid uri authority: %3F`
    unc = paths.native_path(Path("\\\\server\\share\\store\\a.sqlite"))
    assert unc == "\\\\?\\UNC\\server\\share\\store\\a.sqlite", unc
    assert paths.ordinary_path(unc) == Path("\\\\server\\share\\store\\a.sqlite"), "the round trip must be exact"
    # a caller that built the verbatim name itself must still be opened by name, not as a URI
    target, is_uri = paths.sqlite_readonly_target("\\\\?\\D:\\deep\\workspace.sqlite")
    assert is_uri is False and target.startswith("\\\\?\\"), (target, is_uri)


@pytest.mark.skipif(sys.platform != "win32", reason="the refusal being guarded against is Windows-only")
def test_the_depth_alone_is_what_lost_the_write_without_the_prefix(tmp_path: Path, monkeypatch) -> None:
    """Disable the prefix and require the old failure back, or the tests above prove nothing."""
    raw_asset = importlib.import_module("app.ingestion.raw_asset")
    paths = importlib.import_module("shared.paths")
    root = _deep_store_root(tmp_path)
    store = raw_asset.RawAssetStore(root=root)
    monkeypatch.setattr(raw_asset, "native_path", lambda path: str(path))
    with pytest.raises((FileNotFoundError, OSError)):
        store.store_original(b"immutable source bytes", "notes.md")
    monkeypatch.setattr(raw_asset, "native_path", paths.native_path)
    assert store.store_original(b"immutable source bytes", "notes.md").sha256
