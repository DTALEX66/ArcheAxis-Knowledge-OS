"""The recovery reads only registered ZIPs and preserves their opaque bytes."""
from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parents[2] / 'scripts' / 'maintenance'


def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT_ROOT))
    import archive_record_materials as archive
    import compact_record_archives as compact
    return archive, compact


@pytest.fixture
def archive_tmp():
    # The launcher supplies a project-owned TEMP; avoid pytest's extra nested names
    # making the immutable 64-character recipe filename exceed Windows MAX_PATH.
    temp_root = Path(os.environ['TEMP']).resolve()
    assert temp_root.is_relative_to(Path(__file__).resolve().parents[2] / '.project-local')
    with tempfile.TemporaryDirectory(prefix='rc', dir=temp_root) as directory:
        yield Path(directory)


def test_compact_recovery_reads_registered_sources_without_local_zip_copies(archive_tmp, monkeypatch):
    archive, compact = modules(monkeypatch)
    root, source = archive_tmp / 'p', archive_tmp / 's'
    root.mkdir()
    source.mkdir()
    monkeypatch.setattr(archive, 'CANONICAL_ROOT', root)
    monkeypatch.setattr(archive, 'REVIEWED_SOURCE', source)
    # Keep the controlled fixture short enough for Windows without global path changes.
    monkeypatch.setattr(archive, 'ARCHIVE_REL', Path('a'))
    monkeypatch.setattr(archive, 'MANIFEST_REL', Path('m/MANIFEST.json'))
    rows = []
    originals = {}
    for name in ['one.zip', 'two.zip']:
        with zipfile.ZipFile(source / name, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('common.txt', b'unchanged historical payload' * 100)
            z.writestr('unique.txt', name)
        originals[name] = (source / name).read_bytes()
        rows.append({'role': 'AAOS_RECOVERY_OR_HISTORICAL_ARTIFACT', 'source_relative_path': name,
                     'archive_relative_path': str(archive.ARCHIVE_REL / 'originals' / 'Record' / name),
                     'sha256': archive.digest(source / name), 'bytes': len(originals[name])})
    manifest = root / archive.MANIFEST_REL
    manifest.parent.mkdir(parents=True)
    archive.write_json(manifest, {'files': rows})
    historical = manifest.parent / 'CONSOLIDATION.json'
    historical.write_bytes(b'historical receipt must not change')
    compact.consolidate(root, registered_sources=True)
    bundle = root / archive.ARCHIVE_REL / 'compact-recovery-v1'
    for recipe in (bundle / 'recipes').iterdir():
        value = json.loads(recipe.read_text('utf-8'))
        assert b''.join(compact.iter_original(bundle, value)) == originals[value['source_relative_path']]
        assert not (root / archive.ARCHIVE_REL / 'originals' / 'Record' / value['source_relative_path']).exists()
    assert historical.read_bytes() == b'historical receipt must not change'
    # A wrong segment must fail reconstruction, not silently produce a historical PASS.
    pack = bundle / 'objects.pack'
    raw = bytearray(pack.read_bytes())
    raw[-1] ^= 1
    pack.write_bytes(raw)
    with pytest.raises((RuntimeError, OSError, EOFError)):
        for recipe in (bundle / 'recipes').iterdir():
            compact.verify_recipe(bundle, json.loads(recipe.read_text('utf-8')))


def test_manifest_path_cannot_escape_registered_source_root(tmp_path, monkeypatch):
    archive, _ = modules(monkeypatch)
    with pytest.raises(ValueError, match='non-relative'):
        archive.bounded(tmp_path, '../another-project/private.txt')
