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


def test_prepare_binds_current_interpreter_worker_and_persistent_test_database(tmp_path):
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
    assert database == Path(second['environment']['ARCHAXIS_VNEXT_DB'])
    assert database.is_relative_to(ROOT / '.project-local/state')
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
    # This unit test supplies synthetic build paths; the real shared-resource
    # boundary is covered by its dedicated tests and is unavailable on CI.
    monkeypatch.setattr(launcher.resource_boundaries, "check_resource_boundaries", lambda *args, **kwargs: {})
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
        'run': development / 'runs/worktree/run',
    })
    monkeypatch.setattr(launcher.dev, 'artifact_directory', lambda *args: artifacts)
    prepared = launcher.prepare_launch()
    assert prepared['environment']['ARCHAXIS_CORE_BIN'] == str(core)


def test_fresh_workspace_is_explicit_and_isolated(tmp_path):
    launcher = load_launcher()
    desktop, core = tmp_path / 'desktop.exe', tmp_path / 'core.exe'
    for path in (desktop, core):
        path.write_bytes(b'fixture')
    first = launcher.prepare_launch(desktop=desktop, core=core, fresh_workspace=True)
    second = launcher.prepare_launch(desktop=desktop, core=core, fresh_workspace=True)
    assert first['environment']['ARCHAXIS_VNEXT_DB'] != second['environment']['ARCHAXIS_VNEXT_DB']
    assert first['workspace_mode'] == 'ISOLATED_TEST'
