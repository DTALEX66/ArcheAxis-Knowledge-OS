import copy
import json

import pytest

from app.adapters.deeptutor.custody import pack_notebook, unpack_notebook


def test_custody_preserves_question_metadata_and_unknown_upstream_fields():
    notebook = {'id': 'synthetic-1', 'records': [{'id': 'answer-1',
        'user_query': '原问题？', 'output': 'H₂O', 'metadata': {'anchor': 'p:1'},
        'future_field': {'items': [1, None, True]}}], 'created_at': 123.125}
    original = copy.deepcopy(notebook)
    archive = pack_notebook(notebook, '# 笔记\nH₂O\n')
    restored, markdown = unpack_notebook(archive)
    assert restored == original
    assert notebook == original
    assert markdown == '# 笔记\nH₂O\n'
    assert pack_notebook(restored, markdown) == archive


@pytest.mark.parametrize('field,value', [('notebook', {'id': 'changed', 'records': []}),
                                        ('markdown', 'changed')])
def test_custody_rejects_changed_content(field, value):
    archive = json.loads(pack_notebook({'id': 'n', 'records': []}, 'text'))
    archive[field] = value
    with pytest.raises(ValueError, match='digest'):
        unpack_notebook(json.dumps(archive).encode())


def test_custody_rejects_unknown_version_and_non_finite_values():
    archive = json.loads(pack_notebook({'id': 'n', 'records': []}, 'text'))
    archive['schema'] = 'unknown/v9'
    with pytest.raises(ValueError, match='schema'):
        unpack_notebook(json.dumps(archive).encode())
    with pytest.raises(ValueError):
        pack_notebook({'id': 'n', 'records': [], 'score': float('nan')}, 'text')
