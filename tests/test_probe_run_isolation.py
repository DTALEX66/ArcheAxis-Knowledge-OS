"""Failure receipts from development probes must own one unique launcher artifact."""
import importlib
import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize('name', ['anchor_and_loss_probe', 'cold_start_probe',
                                  'exchange_export_probe', 'format_intake_probe'])
def test_probe_preflight_failure_preserves_only_its_unique_run(name, monkeypatch):
    probe = importlib.import_module('scripts.probes.' + name)
    # Before executing any producer, require its canonical allocator entry point.
    assert callable(getattr(probe, '_work_directory', None))
    workspaces = []
    original_run = probe.subprocess.run
    def migration(command, **kwargs):
        if command[0] == 'git':
            return original_run(command, **kwargs)
        assert command[-1] == 'migrate'
        work = Path(kwargs['env']['ARCHEAXIS_DATA_DIR'])
        assert work.is_relative_to(Path(os.environ['ARCHEAXIS_RUN_ROOT']) / 'artifacts')
        assert Path(kwargs['env']['ARCHEAXIS_DB_PATH']).parent == work
        workspaces.append(work)
        (work / 'failure-evidence.txt').write_bytes(b'original failure')
        return subprocess.CompletedProcess(command, 23, '', 'fixture migration failed')
    monkeypatch.setattr(probe.subprocess, 'run', migration)
    monkeypatch.setattr(probe.shutil, 'rmtree', lambda *a, **k: pytest.fail('failure evidence removed'))
    for _ in range(2):
        receipt = probe.run()
        assert receipt['ok'] is False
        assert receipt['failed_step'] == 'migrate'
        assert receipt['steps'] == [{'step': 'migrate', 'exit': 23}]
        assert Path(receipt['work_root']) == workspaces[-1]
    assert workspaces[0] != workspaces[1]
    assert all((p / 'failure-evidence.txt').read_bytes() == b'original failure' for p in workspaces)


@pytest.mark.parametrize('name', ['anchor_and_loss_probe', 'cold_start_probe',
                                  'exchange_export_probe', 'format_intake_probe'])
def test_probe_rejects_forged_run_before_migration(name, tmp_path, monkeypatch):
    probe = importlib.import_module('scripts.probes.' + name)
    unrelated = tmp_path / 'unrelated-run'
    unrelated.mkdir()
    sentinel = unrelated / 'sentinel'
    sentinel.write_bytes(b'prior evidence')
    monkeypatch.setenv('ARCHEAXIS_RUN_ROOT', str(unrelated))
    original_run = probe.subprocess.run
    def disallow_migration(command, **kwargs):
        if command[0] == 'git':
            return original_run(command, **kwargs)
        pytest.fail('forged run must fail before producer execution')
    monkeypatch.setattr(probe.subprocess, 'run', disallow_migration)
    with pytest.raises(ValueError, match='different worktree'):
        probe.run()
    assert list(unrelated.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b'prior evidence'


@pytest.mark.parametrize('name', ['real_asr_smoke', 'staged_format_matrix_smoke'])
def test_matrix_and_asr_allocate_unique_canonical_work(name):
    probe = importlib.import_module('scripts.probes.' + name)
    assert callable(getattr(probe, '_work_directory', None))
    first, second = probe._work_directory(), probe._work_directory()
    assert first != second
    expected = Path(os.environ['ARCHEAXIS_RUN_ROOT']) / 'artifacts'
    assert first.is_relative_to(expected) and second.is_relative_to(expected)
    (first / 'failed-evidence').write_bytes(b'preserve')
    probe._work_directory()
    assert (first / 'failed-evidence').read_bytes() == b'preserve'


def test_asr_cli_reports_relocated_receipt(tmp_path, monkeypatch, capsys):
    from scripts.probes import real_asr_smoke as probe
    monkeypatch.setattr(probe, 'MODEL_DIR', tmp_path)
    monkeypatch.setattr(probe, 'AUDIO_ROOT', tmp_path)
    audio = tmp_path / 'fixture.wav'
    audio.write_bytes(b'fixture-audio')
    monkeypatch.setattr(probe, 'pick_audio', lambda: audio)
    monkeypatch.setattr(probe, 'probe', lambda model: {'fixture': True})
    monkeypatch.setattr(probe, 'transcribe', lambda path: {'text_chars': 4})
    assert probe.main() == 0
    import json
    output = capsys.readouterr().out
    receipt_path = Path(output.split('receipt: ')[-1].strip())
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    assert receipt['ok'] is True
    assert receipt['receipt_path'] == str(receipt_path)
    assert receipt['legacy_receipt_path'].endswith('real-asr-receipt.json')
    assert receipt_path.is_relative_to(Path(os.environ['ARCHEAXIS_RUN_ROOT']) / 'artifacts')


def test_staged_matrix_preflight_uses_new_directory(tmp_path, monkeypatch):
    import sys
    from scripts.probes import staged_format_matrix_smoke as probe
    binary = tmp_path / 'fixture.exe'
    binary.write_bytes(b'fixture')
    monkeypatch.setattr(sys, 'argv', ['staged_format_matrix_smoke', str(binary), str(binary)])
    monkeypatch.setattr(probe, 'build_matrix', lambda: ([('fixture',)], False))
    observed = []
    def fail_staging(root, *args):
        assert root.is_relative_to(Path(os.environ['ARCHEAXIS_RUN_ROOT']) / 'artifacts')
        observed.append(root)
        (root / 'failure').write_bytes(b'preserve')
        raise RuntimeError('fixture staging failure')
    monkeypatch.setattr(probe, 'build_staged_tree', fail_staging)
    for _ in range(2):
        with pytest.raises(RuntimeError, match='fixture staging failure'):
            probe.main()
    assert observed[0] != observed[1]
    assert all((p / 'failure').read_bytes() == b'preserve' for p in observed)


def test_asr_foreign_run_is_rejected_before_any_engine(tmp_path, monkeypatch):
    from scripts.probes import real_asr_smoke as probe
    foreign = tmp_path / 'foreign-run'
    foreign.mkdir()
    sentinel = foreign / 'sentinel'
    sentinel.write_bytes(b'prior evidence')
    monkeypatch.setenv('ARCHEAXIS_RUN_ROOT', str(foreign))
    monkeypatch.setattr(probe, 'MODEL_DIR', tmp_path)
    monkeypatch.setattr(probe, 'AUDIO_ROOT', tmp_path)
    def forbidden(*args):
        pytest.fail('foreign run must be rejected before an engine starts')
    monkeypatch.setattr(probe, 'probe', forbidden)
    monkeypatch.setattr(probe, 'transcribe', forbidden)
    with pytest.raises(ValueError, match='different worktree'):
        probe.main()
    assert list(foreign.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b'prior evidence'
