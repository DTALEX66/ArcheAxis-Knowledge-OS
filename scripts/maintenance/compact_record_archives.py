"""Byte-exact ZIP consolidation using shared already-compressed payloads.

No ZIP member is extracted or executed. Original ZIPs reconstruct exactly, including
headers, extras, descriptors and central directory. Gaps are gzip compressed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import struct
import sys
import zipfile
from pathlib import Path

if __package__:
    from . import archive_record_materials as archive
else:
    import archive_record_materials as archive


def load(path):
    return json.loads(path.read_text('utf-8'))


def iter_original(bundle, recipe):
    catalog = load(archive.safe(bundle / 'catalog.json'))['objects']
    with archive.safe(bundle / 'objects.pack').open('rb') as pack:
        for key in recipe['segments']:
            obj = catalog[key]
            pack.seek(obj['offset'])
            h = hashlib.sha256()
            if obj['codec'] == 'gzip':
                raw = gzip.decompress(pack.read(obj['stored_bytes']))
                if len(raw) != obj['raw_bytes']:
                    raise RuntimeError('gap length mismatch')
                h.update(raw)
                yield raw
            else:
                remaining = obj['stored_bytes']
                while remaining:
                    chunk = pack.read(min(4 * 1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError('truncated pack')
                    remaining -= len(chunk)
                    h.update(chunk)
                    yield chunk
            if h.hexdigest() != key:
                raise RuntimeError('shared segment SHA256 mismatch')


def verify_recipe(bundle, recipe):
    h = hashlib.sha256()
    total = 0
    for chunk in iter_original(bundle, recipe):
        total += len(chunk)
        h.update(chunk)
    if total != recipe['original_bytes'] or h.hexdigest() != recipe['original_sha256']:
        raise RuntimeError('original ZIP reconstruction failed: ' + recipe['source_relative_path'])
    return total


def consolidate(root):
    root = archive.safe(root)
    if root != archive.safe(archive.CANONICAL_ROOT):
        raise ValueError('canonical project only')
    manifest_path = root / archive.MANIFEST_REL
    report = load(manifest_path)
    rows = [r for r in report['files'] if r['role'] == 'AAOS_RECOVERY_OR_HISTORICAL_ARTIFACT'
            and Path(r['source_relative_path']).suffix.lower() == '.zip']
    bundle = archive.bounded(root, archive.ARCHIVE_REL / 'compact-recovery-v1')
    if bundle.exists():
        raise ValueError('existing bundle preserved; do not overwrite')
    bundle.mkdir(parents=True)
    (bundle / 'recipes').mkdir()
    objects = {}
    recipes = []
    total_input = 0
    started = archive.now()
    with (bundle / 'objects.pack.pending').open('xb') as pack:
        def put(source, offset, length, codec):
            source.seek(offset)
            h = hashlib.sha256()
            # Hash opaque compressed bytes; never decode archived business data.
            left = length
            while left:
                b = source.read(min(4 * 1024 * 1024, left))
                if not b:
                    raise RuntimeError('truncated original segment')
                h.update(b)
                left -= len(b)
            key = h.hexdigest()
            if key in objects:
                if objects[key]['raw_bytes'] != length:
                    raise RuntimeError('segment length collision')
                return key
            start = pack.tell()
            source.seek(offset)
            if codec == 'gzip':
                # ZIP directory/header gaps are small. Bound memory even for unusual padding.
                if length > 32 * 1024 * 1024:
                    codec = 'raw'
                else:
                    pack.write(gzip.compress(source.read(length), compresslevel=9, mtime=0))
            if codec == 'raw':
                left = length
                while left:
                    b = source.read(min(4 * 1024 * 1024, left))
                    pack.write(b)
                    left -= len(b)
            objects[key] = {'offset': start, 'stored_bytes': pack.tell() - start,
                            'raw_bytes': length, 'codec': codec}
            return key

        for row in rows:
            path = archive.bounded(root, row['archive_relative_path'])
            print('CONSOLIDATE ' + row['source_relative_path'], flush=True)
            before = path.stat()
            if archive.digest(path) != row['sha256']:
                raise RuntimeError('original archive changed')
            with zipfile.ZipFile(path) as z:
                infos = sorted(z.infolist(), key=lambda i: i.header_offset)
            segments = []
            previous = 0
            with path.open('rb') as source:
                for info in infos:
                    source.seek(info.header_offset)
                    header = source.read(30)
                    if len(header) != 30 or header[:4] != b'PK\x03\x04':
                        raise RuntimeError('unexpected local header')
                    name_length, extra_length = struct.unpack_from('<HH', header, 26)
                    payload = info.header_offset + 30 + name_length + extra_length
                    if payload < previous or payload + info.compress_size > before.st_size:
                        raise RuntimeError('overlapping or out-of-bounds ZIP segments')
                    if payload > previous:
                        segments.append(put(source, previous, payload - previous, 'gzip'))
                    if info.compress_size:
                        segments.append(put(source, payload, info.compress_size, 'raw'))
                    previous = payload + info.compress_size
                if previous < before.st_size:
                    segments.append(put(source, previous, before.st_size - previous, 'gzip'))
            if path.stat().st_mtime_ns != before.st_mtime_ns:
                raise RuntimeError('INVALIDATED original changed')
            recipe = {'schema': 'archeaxis/byte-exact-zip-recipe/v1',
                      'source_relative_path': row['source_relative_path'],
                      'original_bytes': row['bytes'], 'original_sha256': row['sha256'],
                      'segments': segments, 'original_project_copy': str(path)}
            recipe_path = bundle / 'recipes' / (row['sha256'] + '.json')
            archive.write_json(recipe_path, recipe)
            recipes.append({'recipe_path': str(recipe_path), 'source_relative_path': row['source_relative_path'],
                            'original_project_copy': str(path), 'original_bytes': row['bytes'],
                            'original_sha256': row['sha256']})
            total_input += row['bytes']
        pack.flush()
        os.fsync(pack.fileno())
    os.replace(bundle / 'objects.pack.pending', bundle / 'objects.pack')
    catalog = {'schema': 'archeaxis/shared-compressed-segments/v1', 'objects': objects}
    archive.write_json(bundle / 'catalog.json', catalog)
    verified = 0
    for item in recipes:
        print('RECONSTRUCTION_VERIFY ' + item['source_relative_path'], flush=True)
        verified += verify_recipe(bundle, load(Path(item['recipe_path'])))
    stored = sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file())
    summary = {'schema': 'archeaxis/archive-consolidation/v1', 'started_at': started,
               'completed_at': archive.now(), 'status': 'PASS', 'bundle_root': str(bundle),
               'original_zip_count': len(recipes), 'original_bytes': total_input,
               'reconstruction_verified_bytes': verified, 'stored_bytes': stored,
               'saved_bytes': total_input - stored, 'unique_segments': len(objects),
               'segment_references': sum(len(load(Path(x['recipe_path']))['segments']) for x in recipes),
               'pack_sha256': archive.digest(bundle / 'objects.pack'),
               'catalog_sha256': archive.digest(bundle / 'catalog.json'), 'recipes': recipes,
               'key_information': '历史安装、构建、UI验收与缓存恢复包；原README/来源/恢复边界另存索引；不作为当前安装或完成状态。'}
    archive.write_json(bundle / 'CONSOLIDATION.json', summary)
    archive.write_json(root / archive.MANIFEST_REL.parent / 'CONSOLIDATION.json', summary)
    print(json.dumps({k: summary[k] for k in ['status', 'original_zip_count', 'original_bytes', 'stored_bytes', 'saved_bytes', 'unique_segments', 'segment_references']}, ensure_ascii=False), flush=True)
    return 0


def restore(root, original_sha256, output):
    report = load(root / archive.MANIFEST_REL.parent / 'CONSOLIDATION.json')
    item = next(x for x in report['recipes'] if x['original_sha256'] == original_sha256)
    output = archive.safe(output)
    if not output.is_relative_to(archive.safe(root / '.project-local')):
        raise ValueError('restore output must be inside project .project-local')
    if output.exists():
        raise ValueError('restore does not overwrite existing paths')
    output.parent.mkdir(parents=True, exist_ok=True)
    recipe = load(Path(item['recipe_path']))
    with output.open('xb') as target:
        for chunk in iter_original(Path(report['bundle_root']), recipe):
            target.write(chunk)
    if archive.digest(output) != original_sha256:
        raise RuntimeError('restore hash failed')
    print('RESTORE_PASS ' + str(output))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['consolidate', 'restore'])
    parser.add_argument('--sha256')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    return consolidate(archive.ROOT) if args.action == 'consolidate' else restore(archive.ROOT, args.sha256, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
