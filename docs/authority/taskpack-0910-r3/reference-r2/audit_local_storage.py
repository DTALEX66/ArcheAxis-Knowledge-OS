#!/usr/bin/env python3
"""Read-only project storage census. No deletion, content reads or external walk.

Outputs private reports under <repo>/.project-local/inventory/<unique-run>/.
Classifications are review hints, never a deletion authorization.
"""
from __future__ import annotations

import argparse
import datetime as dt
import heapq
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid
from collections import defaultdict

REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)
BUILD_PREFIXES = ('target/', 'src-tauri/target/', 'desktop/src-tauri/target/',
                  'desktop/node_modules/', 'frontend/node_modules/', 'node_modules/')


def no_link_path(path: Path) -> None:
    """Check each existing component without following a link or junction."""
    if os.name == 'nt' and path.drive.upper().startswith('E:'):
        raise ValueError('E drive is outside the authorized scope')
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & REPARSE:
            raise ValueError('Root/output path contains a link or reparse point: ' + str(part))


def classify(rel: str, tracked: set[str]) -> str:
    if rel in tracked or rel == '.git' or rel.startswith('.git/'):
        return 'KEEP_TRACKED_OR_GIT'
    if rel.startswith('.hermes/'):
        return 'REVIEW_HERMES_MIXED_NO_AUTO_DELETE'
    if rel.startswith(('data/', 'workspace/', 'verified-knowledge/')):
        return 'KEEP_DATA_OR_UNKNOWN'
    if rel.startswith(BUILD_PREFIXES):
        return 'REVIEW_REBUILDABLE_CANDIDATE'
    if rel.startswith('apps/') and any(p in ('bin', 'obj') for p in rel.split('/')[2:-1]):
        return 'REVIEW_REBUILDABLE_CANDIDATE'
    if rel.startswith(('.venv/', 'venv/')):
        return 'REVIEW_ENVIRONMENT_REBUILD_REQUIRED'
    if rel.startswith('.project-local/'):
        return 'REVIEW_PROJECT_RUNTIME_MIXED'
    return 'KEEP_UNCLASSIFIED'


def scan(repo: Path) -> dict:
    repo = Path(os.path.abspath(repo))
    no_link_path(repo)
    if not repo.is_dir():
        raise ValueError('Repository directory does not exist')
    no_link_path(repo / '.git')
    if not (repo / '.git').is_dir():
        raise ValueError('Run the census at the main checkout root with a local .git directory; linked worktree metadata is outside this scan scope')
    top = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--show-toplevel'],
                         capture_output=True, text=True, check=True).stdout.strip()
    if os.path.normcase(os.path.abspath(top)) != os.path.normcase(str(repo)):
        raise ValueError('--repo must be the exact Git worktree root')
    listed = subprocess.run(['git', '-C', str(repo), 'ls-files', '-z'],
                            capture_output=True, check=True).stdout
    tracked = {os.fsdecode(p).replace('\\', '/') for p in listed.split(b'\0') if p}
    run = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    output = repo / '.project-local' / 'inventory' / run
    no_link_path(output)
    ignored = subprocess.run(['git', '-C', str(repo), 'check-ignore', '-q', '--',
                              output.relative_to(repo).as_posix() + '/summary.json'])
    if ignored.returncode != 0:
        raise ValueError('Private inventory output is not Git-ignored; complete X01 runtime-root configuration first')
    output.mkdir(parents=True, exist_ok=False)
    by_top = defaultdict(int)
    by_category = defaultdict(int)
    by_two = defaultdict(int)
    seen_objects: set[tuple[int, int]] = set()
    unique_bytes = total_bytes = count = 0
    largest: list[tuple[int, str]] = []
    skipped, errors, hardlinked = [], [], 0
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    stack = [repo]
    with (output / 'files.jsonl').open('w', encoding='utf-8') as sink:
        while stack:
            directory = stack.pop()
            try:
                # Do not follow directories replaced with reparse points during the scan.
                info = directory.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & REPARSE:
                    skipped.append(str(directory.relative_to(repo)))
                    continue
                with os.scandir(directory) as entries:
                    for entry in entries:
                        p = Path(entry.path)
                        rel = p.relative_to(repo).as_posix()
                        if p == output:
                            continue
                        try:
                            st = entry.stat(follow_symlinks=False)
                            if stat.S_ISLNK(st.st_mode) or getattr(st, 'st_file_attributes', 0) & REPARSE:
                                skipped.append(rel)
                                continue
                            if stat.S_ISDIR(st.st_mode):
                                stack.append(p)
                                continue
                            if not stat.S_ISREG(st.st_mode):
                                skipped.append(rel)
                                continue
                            category = classify(rel, tracked)
                            count += 1
                            total_bytes += st.st_size
                            by_top[rel.split('/')[0]] += st.st_size
                            by_two['/'.join(rel.split('/')[:2])] += st.st_size
                            by_category[category] += st.st_size
                            identity = (st.st_dev, st.st_ino)
                            if st.st_ino == 0 or identity not in seen_objects:
                                unique_bytes += st.st_size
                                if st.st_ino:
                                    seen_objects.add(identity)
                            if st.st_nlink > 1:
                                hardlinked += 1
                            heapq.heappush(largest, (st.st_size, rel))
                            if len(largest) > 30:
                                heapq.heappop(largest)
                            sink.write(json.dumps({'path': rel, 'bytes': st.st_size,
                                'mtime_ns': st.st_mtime_ns, 'link_count': st.st_nlink,
                                'tracked': rel in tracked, 'category': category}, ensure_ascii=False) + '\n')
                        except OSError as exc:
                            errors.append({'path': rel, 'error': str(exc)})
            except OSError as exc:
                errors.append({'path': str(directory.relative_to(repo)), 'error': str(exc)})
    summary = {'schema': 'archeaxis.storage-census/v1', 'mode': 'READ_ONLY_NO_DELETE',
        'started_at': started, 'ended_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'file_count': count, 'logical_bytes': total_bytes,
        'logical_gib': round(total_bytes / 1024**3, 3),
        'unique_regular_file_object_bytes': unique_bytes,
        'allocation_or_reclaimable_bytes_measured': False,
        'hardlinked_files': hardlinked,
        'top_level_bytes': dict(sorted(by_top.items(), key=lambda item: -item[1])),
        'top_two_level_bytes': dict(sorted(by_two.items(), key=lambda item: -item[1])),
        'category_bytes': dict(by_category), 'largest_files': [
            {'path': p, 'bytes': size} for size, p in sorted(largest, reverse=True)],
        'skipped_links_or_special_paths': skipped, 'errors': errors,
        'complete_regular_file_scan': not errors and not skipped,
        'not_a_filesystem_snapshot': True,
        'notes': ['Current report directory excluded; prior inventory reports counted.',
                  'No file bodies were opened or hashed.',
                  'Hardlink totals do not measure allocated disk space or reclaimable space.',
                  'Review categories are not deletion instructions.',
                  'Pause project writers before scan; this script is not an OS sandbox.']}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report_directory': str(output), 'logical_gib': summary['logical_gib'],
                      'file_count': count, 'errors': len(errors), 'skipped_paths': len(skipped),
                      'deleted_files': 0}, ensure_ascii=False))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = scan(args.repo)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('Census stopped: ' + str(exc), file=sys.stderr)
        return 2
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
