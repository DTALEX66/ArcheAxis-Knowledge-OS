"""Regression cases for copied live status and broken native rule imports."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def gate(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / 'scripts/ci/check_document_authority.py'
    spec = importlib.util.spec_from_file_location('rules_entry_gate', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'REPO', tmp_path)
    pointer = 'docs/current/AAOS-ACTIVE-EXECUTION.json'
    for name in ('AGENTS.md', 'AUTHORITY.md', 'docs/DOCUMENTATION_AUTHORITY_INDEX.md'):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Read ' + pointer + '\n', encoding='utf-8')
    path = tmp_path / pointer
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{}', encoding='utf-8')
    for name, prefix in [('CLAUDE.md', ''), ('GEMINI.md', './')]:
        (tmp_path / name).write_text(
            f'Read {pointer}\n@{prefix}AGENTS.md\n@{prefix}AUTHORITY.md\n', encoding='utf-8')
    return module, tmp_path


def test_rule_entries_accept_native_adapters_and_historical_explanation(gate):
    module, root = gate
    with (root / 'AGENTS.md').open('a', encoding='utf-8') as stream:
        stream.write('历史 RUNNING_BY_OWNER 不产生当前授权。\n')
    assert module.check_rule_entries() == []


@pytest.mark.parametrize('statement', [
    '当前产品执行 RUNNING_BY_OWNER / PARTIAL；历史暂停不适用。',
    '> **2026-10-23 最新权限 PERMISSIONS_RECOVERED**。',
    'Current state: PAUSED_BY_OWNER.',
])
def test_rule_entries_reject_copied_live_assertions(gate, statement):
    module, root = gate
    with (root / 'AGENTS.md').open('a', encoding='utf-8') as stream:
        stream.write(statement + '\n')
    assert any('copied live state' in problem for problem in module.check_rule_entries())


def test_retired_dependency_is_rejected_only_in_live_entries(gate):
    module, root = gate
    old = '00-governance/global-execution-standard.md'
    history = root / 'docs/history/before.md'
    history.parent.mkdir(parents=True)
    history.write_text(old, encoding='utf-8')
    assert module.check_rule_entries() == []
    with (root / 'AGENTS.md').open('a', encoding='utf-8') as stream:
        stream.write(old)
    assert any('retired cross-project' in problem for problem in module.check_rule_entries())


@pytest.mark.parametrize('extra, expected', [
    ('@missing.md\n', 'missing import'),
    ('@./AGENTS.md\n', 'duplicate import'),
    ('@../outside.md\n', 'unsafe import'),
])
def test_import_failures_are_actionable(gate, extra, expected):
    module, root = gate
    with (root / 'CLAUDE.md').open('a', encoding='utf-8') as stream:
        stream.write(extra)
    assert any(expected in problem for problem in module.check_rule_entries())


def test_import_cycle_is_detected(gate):
    module, root = gate
    with (root / 'AGENTS.md').open('a', encoding='utf-8') as stream:
        stream.write('@CLAUDE.md\n')
    assert any('import cycle' in problem for problem in module.check_rule_entries())


def test_plain_link_does_not_replace_native_import(gate):
    module, root = gate
    (root / 'CLAUDE.md').write_text(
        'Read docs/current/AAOS-ACTIVE-EXECUTION.json and [rules](AGENTS.md)\n', encoding='utf-8')
    assert any('native imports must include' in problem for problem in module.check_rule_entries())
