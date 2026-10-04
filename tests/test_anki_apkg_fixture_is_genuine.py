'''The anki fixture has to be a real package, so a later round-trip cannot pass on a fake one.

The package is read from disk here rather than rebuilt, so these assertions are about the artifact
that is committed and not about the code that produced it.
'''

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/anki-apkg/review.apkg'
UNIT_SEPARATOR = '\x1f'


def _collection(tmp_path: Path):
    '''Anki keeps SQLite inside the package, so unpack it to read it as the database it is.'''
    assert FIXTURE.is_file(), f'the fixture is missing: {FIXTURE}'
    with zipfile.ZipFile(FIXTURE) as container:
        names = set(container.namelist())
        assert 'collection.anki2' in names, names
        assert 'media' in names, names
        media = json.loads(container.read('media'))
        for member in media:
            assert member in names, f'media names a member the package does not hold: {member}'
            assert container.read(member), f'media member {member} carries no bytes'
        target = tmp_path / 'collection.anki2'
        target.write_bytes(container.read('collection.anki2'))
    return target, names


def test_the_package_holds_an_anki_collection(tmp_path: Path) -> None:
    collection, _ = _collection(tmp_path)
    connection = sqlite3.connect(collection)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    connection.close()
    assert {'col', 'notes', 'cards'} <= tables, tables


def test_the_note_fields_are_stored_the_way_anki_stores_them(tmp_path: Path) -> None:
    collection, _ = _collection(tmp_path)
    connection = sqlite3.connect(collection)
    fields = connection.execute('SELECT flds FROM notes').fetchone()[0]
    connection.close()
    assert fields.split(UNIT_SEPARATOR) == ['front', 'back'], (
        "Anki joins a note's fields with the unit separator, so a fixture that used a comma would "
        'not exercise the reader that has to split them')


def test_the_card_carries_real_scheduling_rather_than_placeholders(tmp_path: Path) -> None:
    collection, _ = _collection(tmp_path)
    connection = sqlite3.connect(collection)
    note_id = connection.execute('SELECT id FROM notes').fetchone()[0]
    card = connection.execute('SELECT nid, type, queue, due, ivl, factor, reps FROM cards').fetchone()
    connection.close()
    assert card[0] == note_id, 'the card must point at the note it belongs to'
    # type 2 is review and queue 2 is review: the card has been answered at least once.
    assert card[1] == 2 and card[2] == 2, card
    assert card[3] > 0 and card[4] >= 1, card
    assert 1300 <= card[5] <= 5000, f'the ease factor lives in per-mille: {card[5]}'
    assert card[6] >= 1, card


def test_the_deck_and_note_type_are_declared_as_anki_declares_them(tmp_path: Path) -> None:
    collection, _ = _collection(tmp_path)
    connection = sqlite3.connect(collection)
    models, decks = connection.execute('SELECT models, decks FROM col').fetchone()
    connection.close()
    model = json.loads(models)['1']
    assert [field['name'] for field in model['flds']] == ['Front', 'Back'], model
    assert model['tmpls'][0]['qfmt'] == '{{Front}}', model
    assert json.loads(decks)['1']['name'] == 'Default'
