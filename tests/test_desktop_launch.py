import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_launcher():
    spec = importlib.util.spec_from_file_location('desktop_launch_test', ROOT / 'scripts/launch/desktop_launch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_binds_current_interpreter_worker_and_isolated_database(tmp_path):
    launcher = load_launcher()
    desktop = tmp_path / 'desktop.exe'
    core = tmp_path / 'archeaxis-api.exe'
    desktop.write_bytes(b'fixture')
    core.write_bytes(b'fixture')
    first = launcher.prepare_launch(desktop=desktop, core=core)
    second = launcher.prepare_launch(desktop=desktop, core=core)
    assert first['command'] == [str(desktop)]
    profile = json.loads(Path(first['environment']['ARCHAXIS_WORKER_PROFILE']).read_text())
    assert profile['schema'] == 'archeaxis.worker-profile/v1'
    assert profile['script'] == str(ROOT / 'services/python-workers/transport/text_ndjson.py')
    assert Path(profile['python']).is_file()
    database = Path(first['environment']['ARCHAXIS_VNEXT_DB'])
    assert database != Path(second['environment']['ARCHAXIS_VNEXT_DB'])
    assert database.is_relative_to(ROOT / '.project-local/runs')
    assert not database.exists()
    assert not Path(profile['staging']).exists()


def test_missing_binary_is_rejected_before_artifact_allocation(tmp_path, monkeypatch):
    launcher = load_launcher()
    monkeypatch.setattr(launcher.dev, 'artifact_directory', lambda *args: (_ for _ in ()).throw(AssertionError('must not allocate')))
    try:
        launcher.prepare_launch(desktop=tmp_path / 'absent.exe', core=tmp_path / 'absent-core.exe')
    except ValueError as error:
        assert 'missing' in str(error)
    else:
        raise AssertionError('missing binaries were accepted')


@pytest.mark.parametrize('main_checkout', [True, False])
def test_default_core_uses_authoritative_cargo_directory(tmp_path, monkeypatch, main_checkout):
    launcher = load_launcher()
    development = tmp_path / 'development'
    build = development / 'build/worktree'
    desktop = build / 'dotnet/ArcheAxis.Desktop/bin/Debug/net10.0/ArcheAxis.Desktop.exe'
    cargo = development / 'build/cargo' if main_checkout else build / 'cargo'
    core = cargo / 'debug/archeaxis-api.exe'
    for path in (desktop, core):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
    artifacts = tmp_path / 'artifacts'
    artifacts.mkdir()
    monkeypatch.setattr(launcher.dev, 'layout', lambda root: {
        'dev': development, 'build': build, 'cargo_build': cargo,
    })
    monkeypatch.setattr(launcher.dev, 'artifact_directory', lambda *args: artifacts)
    prepared = launcher.prepare_launch()
    assert prepared['environment']['ARCHAXIS_CORE_BIN'] == str(core)
