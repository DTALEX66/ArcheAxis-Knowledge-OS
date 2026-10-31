"""C++ runtime staging and builder selection; synthetic bytes, never loads DLLs."""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from desktop.scripts import prepare_bundle
from scripts.release import stage_backend_runtime as stager


def row(payload, version):
    return dict(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(), version=version)


@pytest.fixture
def donors(tmp_path, monkeypatch):
    python = tmp_path / 'python'
    vc = tmp_path / 'vc'
    python.mkdir()
    vc.mkdir()
    old, cohort = {}, {}
    for name in ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'):
        payload = ('SYNTHETIC new ' + name).encode()
        (vc / name).write_bytes(payload)
        cohort[name] = row(payload, 'new')
        if name != 'msvcp140.dll':
            prior = ('SYNTHETIC old ' + name).encode()
            (python / name).write_bytes(prior)
            old[name] = (row(prior, 'old'), row(payload, 'new'))
    monkeypatch.setattr(stager, 'APP_LOCAL_VC_RUNTIME', old)
    monkeypatch.setattr(stager, 'APP_LOCAL_CPP_COHORTS', (cohort,))
    return python, vc, cohort


def test_explicit_cohort_replaces_only_owned_python_vc_and_records_locations(tmp_path, donors):
    python, vc, cohort = donors
    before = {p.name: p.read_bytes() for p in python.iterdir()}
    donor_before = {p.name: p.read_bytes() for p in vc.iterdir()}
    output = tmp_path / 'output'
    (output / 'core').mkdir(parents=True)
    shutil.copytree(python, output / 'runtime')
    receipt = stager.stage_app_local_vc_runtime(python, output, vc)
    for name in cohort:
        assert (output / 'runtime' / name).read_bytes() == donor_before[name]
    assert not (output / 'msvcp140.dll').exists() and not (output / 'core/msvcp140.dll').exists()
    for name in stager.APP_LOCAL_VC_RUNTIME:
        assert (output / name).read_bytes() == (output / 'core' / name).read_bytes() == donor_before[name]
    assert receipt['source'] == 'explicit VC runtime'
    assert receipt['original_python_members']['vcruntime140.dll']['version'] == 'old'
    assert receipt['members']['msvcp140.dll']['install_locations'] == ['runtime/']
    assert {p.name: p.read_bytes() for p in python.iterdir()} == before
    assert {p.name: p.read_bytes() for p in vc.iterdir()} == donor_before


def test_absent_explicit_donor_requires_complete_cohort_before_output(tmp_path, donors):
    python, vc, cohort = donors
    output = tmp_path / 'out'
    with pytest.raises(ValueError, match=r'C\+\+ runtime missing'):
        stager.stage_app_local_vc_runtime(python, output)
    assert not output.exists()
    for name in cohort:
        shutil.copyfile(vc / name, python / name)
    (output / 'core').mkdir(parents=True)
    receipt = stager.stage_app_local_vc_runtime(python, output)
    assert receipt['source'] == 'complete selected Python runtime'


@pytest.mark.parametrize('bad', ['missing','unknown','mixed','hardlink'])
def test_incomplete_unknown_mixed_or_linked_cohort_refuses(tmp_path, donors, bad):
    python, vc, cohort = donors
    member = vc / 'msvcp140.dll'
    if bad == 'missing':
        member.unlink()
    elif bad == 'unknown':
        member.write_bytes(b'unknown')
    elif bad == 'mixed':
        (vc / 'vcruntime140.dll').write_bytes((python / 'vcruntime140.dll').read_bytes())
    else:
        try:
            os.link(member, tmp_path / 'linked-msvcp')
        except OSError as error:
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                pytest.skip('Windows hardlink privilege unavailable')
            raise
    with pytest.raises(ValueError):
        stager.stage_app_local_vc_runtime(python, tmp_path / 'out', vc)
    assert not (tmp_path / 'out').exists()


def test_output_inside_donor_refused(tmp_path, donors):
    python, vc, cohort = donors
    with pytest.raises(ValueError, match='independent'):
        stager.stage_app_local_vc_runtime(python, vc / 'out', vc)
    assert not (vc / 'out').exists()


def test_controlled_replacement_rejects_unexpected_existing_runtime_bytes(tmp_path, donors):
    python, vc, cohort = donors
    output = tmp_path / 'output'
    (output / 'core').mkdir(parents=True)
    shutil.copytree(python, output / 'runtime')
    (output / 'runtime/vcruntime140.dll').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='replacement identity'):
        stager.stage_app_local_vc_runtime(python, output, vc)
    assert not (output / 'vcruntime140.dll').exists()


def test_copy_corruption_refused(tmp_path, monkeypatch, donors):
    python, vc, cohort = donors
    output = tmp_path / 'out'
    (output / 'core').mkdir(parents=True)
    original = stager.shutil.copy2
    def corrupt(source, target):
        original(source, target)
        if Path(target).name == 'msvcp140.dll':
            stager.filesystem_path(Path(target)).write_bytes(b'corrupt')
    monkeypatch.setattr(stager.shutil, 'copy2', corrupt)
    with pytest.raises(ValueError, match='copy mismatch'):
        stager.stage_app_local_vc_runtime(python, output, vc)


@pytest.fixture
def fake_builder_authority(monkeypatch):
    checked = []
    authority = SimpleNamespace(validate_cpp_runtime=lambda p: checked.append(p), reject_links_along=lambda p: None)
    monkeypatch.setattr(prepare_bundle.importlib.util, 'spec_from_file_location',
                        lambda *a: SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m: None)))
    monkeypatch.setattr(prepare_bundle.importlib.util, 'module_from_spec', lambda spec: authority)
    return checked


def test_builder_explicit_and_local_environment_are_validated(monkeypatch, tmp_path, fake_builder_authority):
    monkeypatch.setenv('ARCHEAXIS_VC_RUNTIME_DIR', str(tmp_path / 'env'))
    monkeypatch.setattr(prepare_bundle.subprocess, 'run', lambda *a, **k: pytest.fail('Unexpected discovery'))
    assert prepare_bundle.resolve_vc_runtime(tmp_path / 'explicit') == tmp_path / 'explicit'
    assert prepare_bundle.resolve_vc_runtime() == tmp_path / 'env'
    assert fake_builder_authority == [tmp_path / 'explicit', tmp_path / 'env']


def test_builder_official_vswhere_default_redist_version(monkeypatch, tmp_path, fake_builder_authority):
    monkeypatch.delenv('ARCHEAXIS_VC_RUNTIME_DIR', raising=False)
    monkeypatch.setenv('ProgramFiles(x86)', str(tmp_path / 'pf'))
    vswhere = tmp_path / 'pf/Microsoft Visual Studio/Installer/vswhere.exe'
    vswhere.parent.mkdir(parents=True)
    vswhere.write_bytes(b'SYNTHETIC')
    vc = tmp_path / 'vs/VC'
    version_file = vc / 'Auxiliary/Build/Microsoft.VCRedistVersion.default.txt'
    version_file.parent.mkdir(parents=True)
    version_file.write_text('14.44.35112\n')
    def discover(command, **kwargs):
        assert command[0] == str(vswhere) and '-latest' in command and 'installationPath' in command
        assert kwargs['check'] and kwargs['timeout'] == 30
        return subprocess.CompletedProcess(command, 0, str(vc.parent) + '\n', '')
    monkeypatch.setattr(prepare_bundle.subprocess, 'run', discover)
    expected = vc / 'Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT'
    assert prepare_bundle.resolve_vc_runtime() == expected
    assert fake_builder_authority == [expected]
    version_file.write_text('../escape')
    with pytest.raises(RuntimeError, match='invalid official'):
        prepare_bundle.resolve_vc_runtime()


def test_builder_missing_registration_never_searches_path(monkeypatch):
    monkeypatch.delenv('ARCHEAXIS_VC_RUNTIME_DIR', raising=False)
    monkeypatch.delenv('ProgramFiles(x86)', raising=False)
    with pytest.raises(RuntimeError, match='donor unavailable'):
        prepare_bundle.resolve_vc_runtime()


def test_ci_backend_builders_use_reviewed_vs2022_runtime_image():
    """Moving latest to VS2026 must not change the app-local donor/toolset."""
    import yaml
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
    builders = {
        name: job for name, job in workflow['jobs'].items()
        if any('--backend-candidate' in step.get('run', '') for step in job.get('steps', []))
    }
    assert builders, 'no app-local backend producers found'
    for name, job in builders.items():
        assert job['runs-on'] == 'windows-2022', name
