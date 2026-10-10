'''W18/Q25: a backup, a verification and a real restore must not touch the library they copy.

The rehearsal is copy-based on purpose: the point of restoring from a copy is that the original
keeps serving. Nothing in the existing backup tests asserted that, and it is the property a real
restore is judged by, so it is asserted here against a database rather than a text tree.
'''

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from app.exchange.backup import create_backup, restore_backup, verify_backup


def _fingerprint(root: Path) -> dict:
    '''Content, size and modification time of every file, so a rewrite or a touch is visible.'''
    out = {}
    for path in sorted(root.rglob('*')):
        if path.is_file():
            stat = path.stat()
            out[str(path.relative_to(root))] = (
                hashlib.sha256(path.read_bytes()).hexdigest(),
                stat.st_size,
                stat.st_mtime_ns,
            )
    return out


def _library(tmp_path: Path) -> Path:
    source = tmp_path / 'library'
    (source / 'docs').mkdir(parents=True)
    (source / 'docs' / 'note.md').write_text('# note', encoding='utf-8')
    connection = sqlite3.connect(source / 'workspace.sqlite')
    connection.execute('CREATE TABLE knowledge (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    connection.execute("INSERT INTO knowledge VALUES ('k1', 'the real body')")
    connection.commit()
    connection.close()
    return source


def test_backup_verify_and_restore_leave_the_library_untouched(tmp_path: Path) -> None:
    source = _library(tmp_path)
    before = _fingerprint(source)

    backup_dir = tmp_path / 'backup'
    create_backup(source=source, backup_dir=backup_dir)
    verify_backup(backup_dir)
    target = tmp_path / 'restored'
    restore_backup(backup_dir=backup_dir, target=target, dry_run=False)

    after = _fingerprint(source)
    assert after == before, (
        'the library changed while it was being backed up and restored; a rehearsal must not',
        ' write to the thing it is rehearsing against')

    # The restore has to have produced something, or the assertion above would also hold for a
    # restore that quietly did nothing. The data is read from the copy, not from the original.
    restored = sqlite3.connect(target / 'workspace.sqlite')
    row = restored.execute("SELECT body FROM knowledge WHERE id = 'k1'").fetchone()
    restored.close()
    assert row is not None and row[0] == 'the real body'
    assert (target / 'docs' / 'note.md').read_text(encoding='utf-8') == '# note'


def test_the_library_fingerprint_notices_a_touch(tmp_path: Path) -> None:
    '''The guard above is only worth its assertion if the fingerprint can detect a change.'''
    source = _library(tmp_path)
    before = _fingerprint(source)
    (source / 'docs' / 'note.md').write_text('# note ', encoding='utf-8')
    assert _fingerprint(source) != before, 'the fingerprint cannot see an edited file'
