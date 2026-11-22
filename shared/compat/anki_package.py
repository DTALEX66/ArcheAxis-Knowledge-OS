"""Read Anki's package envelope. The collection itself belongs to the SQLite reader."""

from __future__ import annotations

import hashlib
import io
import json
from zipfile import ZipFile

COLLECTIONS = {1: "collection.anki2", 2: "collection.anki21", 3: "collection.anki21b"}
DEFAULT_LIMIT = 64 * 1024 * 1024


def _varint(data, offset):
    number = 0
    for shift in range(0, 70, 7):
        if offset == len(data):
            break
        byte = data[offset]
        offset += 1
        number |= (byte & 127) << shift
        if byte < 128:
            return number, offset
    raise ValueError("invalid Anki protobuf integer")


def _fields(data):
    """Yield the scalar and length-delimited fields in Anki's two envelope messages."""
    offset = 0
    while offset < len(data):
        key, offset = _varint(data, offset)
        tag, wire = divmod(key, 8)
        if not tag:
            raise ValueError("invalid Anki protobuf field")
        if wire == 0:
            value, offset = _varint(data, offset)
        else:
            if wire == 2:
                size, offset = _varint(data, offset)
            elif wire in (1, 5):
                size = 8 if wire == 1 else 4
            else:
                raise ValueError("unsupported Anki protobuf wire type")
            end = offset + size
            if end > len(data):
                raise ValueError("truncated Anki protobuf field")
            value = data[offset:end]
            offset = end
        yield tag, value


def zstd_module():
    try:
        from compression import zstd
    except ImportError:
        from backports import zstd
    return zstd


def _read(archive, name, compressed, limit):
    with archive.open(name) as member:
        if compressed:
            with zstd_module().ZstdFile(member) as stream:
                data = stream.read(limit + 1)
        else:
            data = member.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Anki member {name} exceeds the decoded byte budget")
    return data


def collection_bytes(archive: ZipFile, limit=DEFAULT_LIMIT):
    names = set(archive.namelist())
    if "meta" in names:
        version = dict(_fields(_read(archive, "meta", False, 65536))).get(1)
        if version not in COLLECTIONS:
            raise ValueError(f"unsupported Anki package version {version}")
    else:
        version = 2 if COLLECTIONS[2] in names else 1
    member = COLLECTIONS[version]
    if member not in names:
        raise ValueError(f"package carries no {member}")
    return version, member, _read(archive, member, version == 3, limit)


def media_entries(archive, version, limit=DEFAULT_LIMIT):
    if "media" not in archive.namelist():
        return []
    data = _read(archive, "media", version == 3, limit)
    if version != 3:
        return [(index, name, archive.getinfo(index).file_size, None)
                for index, name in json.loads(data).items()]
    entries = []
    for tag, value in _fields(data):
        if tag == 1:
            fields = dict(_fields(value))
            entries.append((str(len(entries)), fields[1].decode("utf-8"),
                            fields.get(2, 0), fields[3]))
    return entries


class MediaSource:
    """Expose native media names and decoded bytes to the existing member importer."""

    def __init__(self, archive, version, entries, limit):
        self.archive = archive
        self.version = version
        self.entries = entries
        self.limit = limit

    def open(self, info):
        slot, _, size, expected_sha1 = self.entries[info]
        data = _read(self.archive, slot, self.version == 3, min(size, self.limit))
        if len(data) != size or expected_sha1 is not None and hashlib.sha1(data).digest() != expected_sha1:
            raise ValueError(f"Anki media {slot} differs from the native media index")
        return io.BytesIO(data)
