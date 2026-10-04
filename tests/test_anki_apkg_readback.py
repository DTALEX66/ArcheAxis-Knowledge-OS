'''The Anki reader keeps the source's scheduling the source's, and never launders it into a review.

W27/Q36: a foreign collection's scores and scheduling must not be presented as human review, and
importing it must not create a review this workspace never performed.
'''

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from app.adapters.anki_zotero import AdapterError, parse_apkg

FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/anki-apkg/review.apkg'


def test_it_reads_the_fields_the_way_anki_stored_them() -> None:
    units = parse_apkg(FIXTURE)
    assert len(units) == 1
    assert units[0]['fields'] == ['front', 'back'], units[0]
    assert units[0]['note_type'] == 'Basic', units[0]
    assert units[0]['tags'] == []


def test_it_reads_the_scheduling_the_collection_recorded() -> None:
    card = parse_apkg(FIXTURE)[0]['cards'][0]
    assert card['state'] == 'review' and card['queue'] == 'review', card
    assert card['interval_days'] == 4, card
    assert card['ease_per_mille'] == 2500, card
    assert card['reviews'] == 3 and card['lapses'] == 0, card


def test_the_scheduling_is_marked_as_the_sources_and_not_a_review_here() -> None:
    '''The number belongs to the collection; nothing in this workspace graded the card.'''
    unit = parse_apkg(FIXTURE)[0]
    assert unit['scheduling_origin'] == 'imported_from_source', unit
    assert unit['authority_effect'] == 'candidate_or_measurement_only', unit
    rendered = json.dumps(unit)
    for claim in ('reviewed_by', 'graded_by', 'correct', 'mastery', 'score'):
        assert claim not in rendered, f'importing must not assert {claim}: {rendered}'


def test_an_unanswered_card_reports_no_interval_rather_than_zero(tmp_path: Path) -> None:
    '''A new card has no interval; a zero would read as "answered, and due now".'''
    with zipfile.ZipFile(FIXTURE) as container:
        payload = container.read('collection.anki2')
        media = container.read('media')
        blob = container.read('0')
    connection = sqlite3.connect(':memory:')
    connection.deserialize(payload)
    connection.execute('UPDATE cards SET type=0, queue=0, ivl=0, factor=0, reps=0')
    connection.commit()
    patched = connection.serialize()
    connection.close()
    scratch = tmp_path / 'unanswered.apkg'
    with zipfile.ZipFile(scratch, 'w') as container:
        container.writestr('collection.anki2', patched)
        container.writestr('media', media)
        container.writestr('0', blob)
    card = parse_apkg(scratch)[0]['cards'][0]
    assert card['state'] == 'new', card
    assert card['interval_days'] is None, card
    assert card['ease_per_mille'] is None, card


def test_a_file_that_is_not_a_package_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / 'broken.apkg'
    broken.write_bytes(b'not a zip at all')
    with pytest.raises(AdapterError, match='unreadable package'):
        parse_apkg(broken)


def test_a_zip_without_a_collection_is_refused(tmp_path: Path) -> None:
    empty = tmp_path / 'empty.apkg'
    with zipfile.ZipFile(empty, 'w') as container:
        container.writestr('media', '{}')
    with pytest.raises(AdapterError, match='no collection.anki2'):
        parse_apkg(empty)
