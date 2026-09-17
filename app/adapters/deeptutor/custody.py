"""Lossless custody of upstream notebook data; never a Core truth import.

DeepTutor's Markdown is a reading view and omits original questions/metadata.
Keep the complete upstream JSON alongside that view, with separate digests.
Unknown upstream fields are preserved without interpreting or granting authority.
"""
from __future__ import annotations

import hashlib
import json

SCHEMA = 'archeaxis.deeptutor-notebook-custody/v1'


def _bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def _check(notebook: object, markdown: object) -> None:
    if (not isinstance(notebook, dict) or not isinstance(notebook.get('id'), str)
            or not notebook['id'] or not isinstance(notebook.get('records'), list)
            or any(not isinstance(record, dict) for record in notebook['records'])):
        raise ValueError('invalid upstream notebook shape')
    if not isinstance(markdown, str):
        raise ValueError('Markdown must be text')


def pack_notebook(notebook: dict, markdown: str) -> bytes:
    """Serialize a complete inert upstream snapshot without changing it."""
    _check(notebook, markdown)
    return _bytes({'schema': SCHEMA, 'notebook': notebook, 'markdown': markdown,
        'notebook_sha256': hashlib.sha256(_bytes(notebook)).hexdigest(),
        'markdown_sha256': hashlib.sha256(markdown.encode('utf-8')).hexdigest()})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def unpack_notebook(archive: bytes) -> tuple[dict, str]:
    """Verify and read custody data. Does not write a database or approve claims."""
    value = json.loads(archive, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or value.get('schema') != SCHEMA:
        raise ValueError('unsupported custody schema')
    if set(value) != {'schema', 'notebook', 'markdown', 'notebook_sha256', 'markdown_sha256'}:
        raise ValueError('invalid custody envelope fields')
    notebook, markdown = value['notebook'], value['markdown']
    _check(notebook, markdown)
    if (hashlib.sha256(_bytes(notebook)).hexdigest() != value['notebook_sha256']
            or hashlib.sha256(markdown.encode('utf-8')).hexdigest() != value['markdown_sha256']):
        raise ValueError('custody digest mismatch')
    return notebook, markdown
