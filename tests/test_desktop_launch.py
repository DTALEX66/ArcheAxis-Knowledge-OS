import importlib.util
import hashlib
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def remove_receipt_artifact(receipt: dict | None) -> None:
    if receipt:
        shutil.rmtree(Path(receipt['receipt_path']).parent, ignore_errors=True)


def load_launcher():
    spec = importlib.util.spec_from_file_location('desktop_launch_test', ROOT / 'scripts/launch/desktop_launch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_binds_current_interpreter_worker_and_persistent_test_database(tmp_path):
    launcher = load_launcher()
    fixture_root = ROOT / '.project-local' / 'build' / 'test-fixtures' / tmp_path.name
    fixture_root.mkdir(parents=True, exist_ok=True)
    desktop = fixture_root / 'desktop.exe'
    core = fixture_root / 'archeaxis-api.exe'
    desktop.write_bytes(b'fixture')
    core.write_bytes(b'fixture')
    receipts = []
    try:
        first = launcher.prepare_launch(desktop=desktop, core=core)
        receipts.append(first)
        second = launcher.prepare_launch(desktop=desktop, core=core)
        receipts.append(second)
        assert first['command'] == [str(desktop)]
        profile = json.loads(Path(first['environment']['ARCHAXIS_WORKER_PROFILE']).read_text())
        assert profile['schema'] == 'archeaxis.worker-profile/v1'
        assert profile['script'] == str(ROOT / 'services/python-workers/transport/text_ndjson.py')
        assert Path(profile['python']).is_file()
        assert first['environment']['ARCHEAXIS_PYTHON'] == profile['python']
        assert first['environment']['ARCHEAXIS_SCHEDULER_WORKER'] == str(
            ROOT / 'services/python-workers/learning/worker_schedule.py'
        )
        assert first['environment']['ARCHAXIS_SCHEDULER_WORKER'] == first['environment']['ARCHEAXIS_SCHEDULER_WORKER']
        database = Path(first['environment']['ARCHAXIS_VNEXT_DB'])
        assert database == Path(second['environment']['ARCHAXIS_VNEXT_DB'])
        assert database.is_relative_to(ROOT / '.project-local/state')
        assert not database.exists()
        assert not Path(profile['staging']).exists()
    finally:
        for receipt in receipts:
            remove_receipt_artifact(receipt)
        shutil.rmtree(fixture_root, ignore_errors=True)


def test_prepare_prefers_explicit_archeaxis_python(tmp_path, monkeypatch):
    launcher = load_launcher()
    fixture_root = ROOT / '.project-local' / 'build' / 'test-fixtures' / tmp_path.name
    fixture_root.mkdir(parents=True, exist_ok=True)
    desktop = fixture_root / 'desktop.exe'
    core = fixture_root / 'archeaxis-api.exe'
    selected_python = fixture_root / 'selected-python.exe'
    for path in (desktop, core, selected_python):
        path.write_bytes(b'fixture')
    monkeypatch.setenv('ARCHEAXIS_PYTHON', str(selected_python))
    receipt = None
    try:
        receipt = launcher.prepare_launch(desktop=desktop, core=core)
        profile = json.loads(Path(receipt['environment']['ARCHAXIS_WORKER_PROFILE']).read_text())
        assert profile['python'] == str(selected_python)
        assert receipt['environment']['ARCHEAXIS_PYTHON'] == str(selected_python)
    finally:
        remove_receipt_artifact(receipt)
        shutil.rmtree(fixture_root, ignore_errors=True)


def test_explicit_paths_still_run_indexed_resource_preflight(tmp_path, monkeypatch):
    launcher = load_launcher()
    fixture_root = ROOT / '.project-local' / 'build' / 'test-fixtures' / tmp_path.name
    fixture_root.mkdir(parents=True, exist_ok=True)
    desktop = fixture_root / 'desktop.exe'
    core = fixture_root / 'archeaxis-api.exe'
    desktop.write_bytes(b'fixture')
    core.write_bytes(b'fixture')
    calls = []
    monkeypatch.setattr(
        launcher.resource_boundaries,
        'check_resource_boundaries',
        lambda *args, **kwargs: calls.append((args, kwargs)) or {
            'purpose': 'test', 'target': {'id': 'project_test_corpus'},
        },
    )

    receipt = None
    try:
        receipt = launcher.prepare_launch(desktop=desktop, core=core)
        assert calls == [((launcher.REPO,), {'purpose': 'test'})]
    finally:
        remove_receipt_artifact(receipt)
        shutil.rmtree(fixture_root, ignore_errors=True)


def test_prepared_receipt_contains_verifiable_boundary_and_artifact_identity(tmp_path, monkeypatch):
    launcher = load_launcher()
    fixture_root = ROOT / '.project-local' / 'build' / 'test-fixtures' / tmp_path.name
    fixture_root.mkdir(parents=True, exist_ok=True)
    desktop = fixture_root / 'desktop.exe'
    core = fixture_root / 'archeaxis-api.exe'
    desktop.write_bytes(b'desktop-fixture')
    core.write_bytes(b'core-fixture')
    monkeypatch.setattr(
        launcher.resource_boundaries,
        'check_resource_boundaries',
        lambda *args, **kwargs: {
            'schema': 'archeaxis.resource-boundaries/v1',
            'purpose': 'test',
            'target': {'id': 'project_test_corpus'},
        },
    )

    receipt = None
    try:
        receipt = launcher.prepare_launch(desktop=desktop, core=core)
        persisted = json.loads(Path(receipt['receipt_path']).read_text())
        assert persisted['schema'] == 'archeaxis.desktop-launch-prep/v1'
        assert persisted['launch_state'] == 'PREPARED_NOT_LAUNCHED'
        assert persisted['runtime_claim'] == 'none'
        assert persisted['path_scope'] == 'project-local'
        assert persisted['resource_boundary_target'] == 'project_test_corpus'
        assert persisted['source_head'] == launcher.dev.git(ROOT, 'rev-parse', 'HEAD')
        assert persisted['launcher_script_sha256'] == sha256(Path(launcher.__file__).resolve())
        assert persisted['desktop_sha256'] == sha256(desktop)
        assert persisted['core_sha256'] == sha256(core)
        profile = Path(persisted['environment']['ARCHAXIS_WORKER_PROFILE'])
        assert persisted['worker_profile_sha256'] == sha256(profile)
        assert Path(persisted['environment']['ARCHAXIS_VNEXT_DB']).is_relative_to(ROOT / '.project-local')
        assert persisted['receipt_path'] == receipt['receipt_path']
    finally:
        remove_receipt_artifact(locals().get('receipt'))
        shutil.rmtree(fixture_root, ignore_errors=True)


def test_missing_binary_is_rejected_before_artifact_allocation(tmp_path, monkeypatch):
    launcher = load_launcher()
    fixture_root = ROOT / '.project-local' / 'build' / 'test-fixtures' / tmp_path.name
    fixture_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(launcher.dev, 'artifact_directory', lambda *args: (_ for _ in ()).throw(AssertionError('must not allocate')))
    try:
        launcher.prepare_launch(desktop=fixture_root / 'absent.exe', core=fixture_root / 'absent-core.exe')
    except ValueError as error:
        assert 'missing' in str(error)
    else:
        raise AssertionError('missing binaries were accepted')
    finally:
        shutil.rmtree(fixture_root, ignore_errors=True)


def test_boundary_failure_is_fail_closed(monkeypatch):
    launcher = load_launcher()

    def fail_boundary(*args, **kwargs):
        raise ValueError('boundary denied')

    monkeypatch.setattr(launcher.resource_boundaries, 'check_resource_boundaries', fail_boundary)
    monkeypatch.setattr(
        launcher.dev,
        'artifact_directory',
        lambda *args: (_ for _ in ()).throw(AssertionError('must not allocate')),
    )
    try:
        launcher.prepare_launch()
    except ValueError as error:
        assert str(error) == 'boundary denied'
    else:
        raise AssertionError('boundary failure was not propagated')


@pytest.mark.parametrize('main_checkout', [True, False])
def test_default_core_uses_authoritative_cargo_directory(tmp_path, monkeypatch, main_checkout):
    launcher = load_launcher()
    # This unit test supplies synthetic build paths; the real shared-resource
    # boundary is covered by its dedicated tests and is unavailable on CI.
    monkeypatch.setattr(
        launcher.resource_boundaries,
        "check_resource_boundaries",
        lambda *args, **kwargs: {
            'purpose': 'test', 'target': {'id': 'project_test_corpus'},
        },
    )
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
    fixture_root = ROOT / '.project-local' / 'build' / 'test-fixtures' / tmp_path.name
    fixture_root.mkdir(parents=True, exist_ok=True)
    desktop, core = fixture_root / 'desktop.exe', fixture_root / 'core.exe'
    for path in (desktop, core):
        path.write_bytes(b'fixture')
    receipts = []
    try:
        first = launcher.prepare_launch(desktop=desktop, core=core, fresh_workspace=True)
        receipts.append(first)
        second = launcher.prepare_launch(desktop=desktop, core=core, fresh_workspace=True)
        receipts.append(second)
        assert first['environment']['ARCHAXIS_VNEXT_DB'] != second['environment']['ARCHAXIS_VNEXT_DB']
        assert first['workspace_mode'] == 'ISOLATED_TEST'
    finally:
        for receipt in receipts:
            remove_receipt_artifact(receipt)
        shutil.rmtree(fixture_root, ignore_errors=True)
