'''Build the committed anki-apkg fixture, so its provenance is reproducible.

Anki stores a note's fields joined by the unit separator, and a card carries real scheduling
numbers rather than placeholders, because those columns are exactly what a later slice has to keep
honest. Run: python build_fixture.py <out.apkg>
'''

from __future__ import annotations

import json
import sqlite3
import sys
import zipfile
from pathlib import Path

SCHEMA = [
    'CREATE TABLE col (id integer primary key, crt integer not null, mod integer not null,'
    ' scm integer not null, ver integer not null, dty integer not null, usn integer not null,'
    ' ls integer not null, conf text not null, models text not null, decks text not null,'
    ' dconf text not null, tags text not null)',
    'CREATE TABLE notes (id integer primary key, guid text not null, mid integer not null,'
    ' mod integer not null, usn integer not null, tags text not null, flds text not null,'
    ' sfld integer not null, csum integer not null, flags integer not null, data text not null)',
    'CREATE TABLE cards (id integer primary key, nid integer not null, did integer not null,'
    ' ord integer not null, mod integer not null, usn integer not null, type integer not null,'
    ' queue integer not null, due integer not null, ivl integer not null, factor integer not null,'
    ' reps integer not null, lapses integer not null, left integer not null, odue integer not null,'
    ' odid integer not null, flags integer not null, data text not null)',
]

MODEL = {
    '1': {
        'id': 1, 'name': 'Basic', 'type': 0, 'mod': 1660000000, 'usn': 0, 'sortf': 0, 'did': 1,
        'tmpls': [{'name': 'Card 1', 'ord': 0, 'qfmt': '{{Front}}',
                   'afmt': '{{FrontSide}}<hr id=answer>{{Back}}'}],
        'flds': [{'name': 'Front', 'ord': 0}, {'name': 'Back', 'ord': 1}],
        'css': '.card { font-family: arial; }',
    },
}
DECKS = {'1': {'id': 1, 'name': 'Default', 'mod': 1660000000, 'usn': 0, 'desc': '', 'dyn': 0,
               'collapsed': False, 'conf': 1, 'extendNew': 10, 'extendRev': 50}}
DCONF = {'1': {'id': 1, 'name': 'Default', 'mod': 0, 'usn': 0, 'maxTaken': 60, 'autoplay': True,
               'timer': 0, 'replayq': True,
               'new': {'delays': [1, 10], 'ints': [1, 4, 7], 'initialFactor': 2500,
                       'separate': True, 'order': 1, 'perDay': 20},
               'rev': {'perDay': 200, 'ease4': 1.3, 'ivlFct': 1, 'maxIvl': 36500, 'bury': True,
                       'minSpace': 1, 'fuzz': 0.05, 'hardFactor': 1.2},
               'lapse': {'delays': [10], 'mult': 0, 'minInt': 1, 'leechFails': 8,
                         'leechAction': 0}}}

NOTE_ID = 1660000000001
CARD_ID = 1660000000002


def build(target: Path) -> None:
    database = target.with_name('collection.anki2')
    if database.exists():
        database.unlink()
    connection = sqlite3.connect(database)
    for statement in SCHEMA:
        connection.execute(statement)
    connection.execute(
        'INSERT INTO col VALUES (1,1660000000,1660000000,1660000000,11,0,0,0,?,?,?,?,?)',
        (json.dumps({'activeDecks': [1], 'curDeck': 1, 'newSpread': 0}), json.dumps(MODEL),
         json.dumps(DECKS), json.dumps(DCONF), '{}'),
    )
    connection.execute(
        'INSERT INTO notes VALUES (?,?,1,1660000000,0,?,?,?,?,0,?)',
        (NOTE_ID, 'guid00000001', '', 'front' + chr(31) + 'back', 'front', 1234567890, ''),
    )
    connection.execute(
        'INSERT INTO cards VALUES (?,?,1,0,1660000000,0,2,2,7,4,2500,3,0,0,0,0,0,?)',
        (CARD_ID, NOTE_ID, ''),
    )
    connection.commit()
    connection.close()

    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as container:
        container.write(database, 'collection.anki2')
        container.writestr('media', json.dumps({'0': 'diagram.png'}))
        container.writestr('0', b'\x89PNG\r\n\x1a\n' + b'\x00' * 32)
    database.unlink()


if __name__ == '__main__':
    build(Path(sys.argv[1] if len(sys.argv) > 1 else 'review.apkg'))
    print('built')
