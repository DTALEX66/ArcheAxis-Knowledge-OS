"""Synthetic archive regressions; no executable download or media qualification."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def module():
    spec = importlib.util.spec_from_file_location('ffmpeg_prepare_test', ROOT / 'scripts/ci/prepare_windows_ffmpeg.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def make_archive(module, extra=None):
    source = module.pin()
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name in source['selected']:
            archive.writestr(source['prefix'] + '/' + name, b'SYNTHETIC_NOT_EXECUTABLE:' + name.encode())
        if extra is not None:
            archive.writestr(extra, b'unknown')
    return output.getvalue()

def install_synthetic(module, monkeypatch):
    source = module.pin()
    raw = make_archive(module)
    source.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(module, 'pin', lambda: source)
    def fetch(path, expected):
        path.write_bytes(raw)
        return module.boundary.check_asset(path, expected)
    monkeypatch.setattr(module, 'fetch', fetch)
    monkeypatch.setattr(module, 'tool_output', lambda binary, args: (
        'ffmpeg version 8.1.2-essentials_build-www.gyan.dev\n' if '-version' in args else
        '\n'.join(' A..... ' + encoder + ' synthetic' for encoder in source['required_encoders'])))
    return source

def test_pin_matches_fixed_publisher_release_identity(module):
    source = module.pin()
    assert source['version'] == '8.1.2' and source['bytes'] == 109728040
    assert source['sha256'] == 'db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec'
    assert '/releases/download/8.1.2/' in source['url']
    assert source['license'] == 'GPL-3.0-or-later'
    assert source['scope'] == 'EXPLICIT_CI_TOOL_ONLY_NOT_PRODUCT_DISTRIBUTION_QUALIFIED'

@pytest.mark.parametrize('path', ['E:/forbidden/assets', 'F:/forbidden/assets', '//server/share', '\\\\server/share'])
def test_protected_path_refused_before_filesystem(module, monkeypatch, path):
    monkeypatch.setattr(Path, 'lstat', lambda *args: pytest.fail('must not access filesystem'))
    with pytest.raises(ValueError, match='Protected path'):
        module.prepare(path)

def test_unknown_existing_root_never_overwritten(module, tmp_path):
    root = tmp_path / '.project-local/assets'
    root.mkdir(parents=True)
    (root / 'receipt.json').write_bytes(b'OWNER')
    with pytest.raises(ValueError, match='Existing root'):
        module.prepare(root, tmp_path)
    assert (root / 'receipt.json').read_bytes() == b'OWNER'

@pytest.mark.parametrize('extra', ['../escape', '/absolute', 'ffmpeg-8.1.2-essentials_build/../escape',
                                  'ffmpeg-8.1.2-essentials_build/C:/escape', 'other/bin/tool.exe',
                                  'ffmpeg-8.1.2-essentials_build/BIN/FFMPEG.EXE'])
def test_unsafe_or_duplicate_member_refused_before_extraction(module, extra):
    with zipfile.ZipFile(io.BytesIO(make_archive(module, extra))) as archive:
        with pytest.raises(ValueError):
            module.selected_members(archive, module.pin())

def test_archive_expansion_budget_and_link_refused(module):
    source = module.pin()
    raw = make_archive(module)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        small = dict(source, maximum_expanded_bytes=1)
        with pytest.raises(ValueError, match='expansion budget'):
            module.selected_members(archive, small)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        link = zipfile.ZipInfo(source['prefix'] + '/link')
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, 'outside')
    with zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive:
        with pytest.raises(ValueError, match='Linked archive'):
            module.selected_members(archive, source)

def test_failed_download_keeps_failure_receipt(module, tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'fetch', lambda *args: (_ for _ in ()).throw(ValueError('transport')))
    root = tmp_path / '.project-local/assets'
    result = module.prepare(root, tmp_path)
    assert not result['ok'] and result['qualification'] == 'NOT_EXECUTED'
    assert json.loads((root / 'receipt.json').read_text()) == result
    assert result['error_type'] == 'ValueError'

def test_synthetic_success_retains_license_and_checks_capabilities(module, tmp_path, monkeypatch):
    install_synthetic(module, monkeypatch)
    root = tmp_path / '.project-local/assets'
    result = module.prepare(root, tmp_path)
    assert result['ok'] and 'NOT_MEDIA_ASR_CORE' in result['qualification']
    assert result['ffmpeg'] == str(root / 'bin/ffmpeg.exe')
    assert set(result['members']) == {'bin/ffmpeg.exe', 'bin/ffprobe.exe', 'LICENSE'}
    assert (root / 'LICENSE').read_bytes().startswith(b'SYNTHETIC_NOT_EXECUTABLE')

@pytest.mark.parametrize('failure', ['wrong_version', 'missing_encoder'])
def test_wrong_tool_version_or_missing_encoder_keeps_failure_receipt(module, tmp_path, monkeypatch, failure):
    install_synthetic(module, monkeypatch)
    valid = module.tool_output
    monkeypatch.setattr(module, 'tool_output', lambda binary, args: (
        'ffmpeg version 9.0.2-essentials_build\n' if failure == 'wrong_version' else
        valid(binary, args).replace('libmp3lame', 'unselected')))
    root = tmp_path / '.project-local/assets'
    result = module.prepare(root, tmp_path)
    assert not result['ok'] and result['qualification'] == 'NOT_EXECUTED'
    assert json.loads((root / 'receipt.json').read_text()) == result

def test_unexpected_download_source_rejected(module):
    with pytest.raises(ValueError, match='Unexpected archive source'):
        module.allowed_url('https://github.com.evil.invalid/asset')

def test_unreadable_lock_also_retains_failure_receipt(module, tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'pin', lambda: (_ for _ in ()).throw(ValueError('bad lock')))
    root = tmp_path / '.project-local/assets'
    result = module.prepare(root, tmp_path)
    assert not result['ok'] and result['qualification'] == 'NOT_EXECUTED'
    assert json.loads((root / 'receipt.json').read_text()) == result

@pytest.mark.parametrize('failure', ['oversize', 'bad_sha'])
def test_stream_budget_and_wrong_sha_reject_public_archive(module, tmp_path, monkeypatch, failure):
    class Response(io.BytesIO):
        def geturl(self):
            return 'https://release-assets.githubusercontent.com/fixed'
    from types import SimpleNamespace
    monkeypatch.setattr(module.urllib.request, 'build_opener', lambda *args:
                        SimpleNamespace(open=lambda *args, **kwargs: Response(b'fixed')))
    source = {'url': 'https://github.com/fixed', 'bytes': 1 if failure == 'oversize' else 5, 'sha256': '0' * 64}
    with pytest.raises(ValueError, match='budget exceeded' if failure == 'oversize' else 'bytes/SHA mismatch'):
        module.fetch(tmp_path / 'archive.zip', source)
