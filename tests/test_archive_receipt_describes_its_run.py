'''The loss receipt must describe the run it belongs to, not a run it wishes had happened.'''

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'services/python-workers/document/worker_archive.py'


def _worker():
    spec = importlib.util.spec_from_file_location('archive_worker_under_test', WORKER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _container(tmp_path: Path) -> Path:
    source = tmp_path / 'container.zip'
    with zipfile.ZipFile(source, 'w') as container:
        container.writestr('a.txt', 'alpha')
        container.writestr('b.txt', 'beta')
    return source


def _note(result: dict) -> str:
    receipt = result.get('loss_receipt', result)
    return receipt['params']['projection_note']


def test_the_receipt_does_not_deny_an_extraction_it_performed(tmp_path: Path) -> None:
    '''It said no member was extracted while the members sat in the destination.'''
    source = _container(tmp_path)
    destination = tmp_path / 'members'
    result = _worker().extract(str(source), destination)
    note = _note(result)
    # the honesty the note exists for is kept in both cases
    assert "NOT the members' contents" in note, note
    # and the extraction that really happened is not denied
    written = sorted(path.name for path in destination.iterdir())
    assert len(written) == 2, f'the members really were written out: {written}'
    assert 'no member was extracted' not in note, note
    assert '2 of 2 member(s) were also written out' in note, note


def test_the_receipt_still_says_nothing_was_extracted_when_nothing_was(tmp_path: Path) -> None:
    '''The other half: with no destination the original claim is true and must remain.'''
    source = _container(tmp_path)
    result = _worker().extract(str(source), None)
    note = _note(result)
    assert "NOT the members' contents" in note, note
    assert 'no member was extracted' in note, note


def test_the_container_is_untouched_by_an_extraction(tmp_path: Path) -> None:
    '''The archive is opened for reading; the source of record must survive being mined.'''
    source = _container(tmp_path)
    before = source.read_bytes()
    _worker().extract(str(source), tmp_path / 'members')
    assert source.read_bytes() == before, 'the container must be read, never rewritten'
