"""Recover only the reviewed Record manifest into this project; never rescan Record.

Existing bytes are preserved. Large historical ZIPs use the existing byte-exact
compressed-segment format, streamed directly from their registered source paths.
This restores historical inputs, and does not activate their instructions.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import archive_record_materials as archive
import compact_record_archives as compact


def recover(root: Path):
    root = archive.safe(root)
    if root != archive.safe(archive.CANONICAL_ROOT):
        raise ValueError('canonical project only')
    manifest = json.loads((root / archive.MANIFEST_REL).read_text('utf-8'))
    rows = manifest['files']
    # Validate every selected path and size before writing; no excluded source is read.
    for row in rows:
        source = archive.bounded(archive.REVIEWED_SOURCE, row['source_relative_path'])
        if source != archive.safe(Path(row['source_path'])) or source.stat().st_size != row['bytes']:
            raise ValueError('registered source identity/size changed: ' + row['source_relative_path'])
        archive.bounded(root, row['archive_relative_path'])
    bundle = archive.bounded(root, manifest['consolidation']['bundle_relative_path'])
    if not bundle.exists():
        compact.consolidate(root, registered_sources=True)
    for filename, key in [('objects.pack', 'pack_sha256'), ('catalog.json', 'catalog_sha256')]:
        if archive.digest(bundle / filename) != manifest['consolidation'][key]:
            raise RuntimeError('historical bundle hash mismatch: ' + filename)
    for row in rows:
        target = archive.bounded(root, row['archive_relative_path'])
        if row.get('storage_kind') == 'SHARED_COMPRESSED_ZIP_RECIPE':
            recipe = json.loads(target.read_text('utf-8'))
            if recipe['original_sha256'] != row['sha256'] or recipe['original_bytes'] != row['bytes']:
                raise RuntimeError('recipe identity mismatch')
            compact.verify_recipe(bundle, recipe)
        else:
            print('RECOVER ' + row['source_relative_path'], flush=True)
            source = archive.bounded(archive.REVIEWED_SOURCE, row['source_relative_path'])
            if archive.digest(source) != row['sha256']:
                raise RuntimeError('source hash differs from historical registration: ' + row['source_relative_path'])
            archive.copy_verified(source, target)
    for derived in manifest.get('derived', []):
        original = next(row for row in rows if row['sha256'] == derived['source_sha256'])
        with zipfile.ZipFile(root / original['archive_relative_path']) as z:
            xml = ET.fromstring(z.read('word/document.xml'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text = '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in xml.findall('.//w:p', ns)) + '\n'
        target = archive.safe(Path(derived['path']))
        if not target.is_relative_to(root / archive.ARCHIVE_REL):
            raise ValueError('derived target escaped project archive')
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            # The original Windows derivation used native CRLF; preserve its exact hash.
            with target.open('x', encoding='utf-8') as f:
                f.write(text)
        if archive.digest(target) != derived['sha256']:
            raise RuntimeError('derived text hash mismatch')
    receipt = {'schema': 'archeaxis/record-recovery/v1', 'status': 'PASS',
               'completed_at': archive.now(), 'registered_files_verified': len(rows),
               'derived_files_verified': len(manifest.get('derived', [])),
               'manifest_sha256': archive.digest(root / archive.MANIFEST_REL),
               'pack_sha256': manifest['consolidation']['pack_sha256'],
               'scope': 'Registered project/shared historical inputs only; no source execution or authority activation.'}
    archive.write_json(root / archive.ARCHIVE_REL / 'RECOVERY-20261018.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    recover(archive.ROOT)
