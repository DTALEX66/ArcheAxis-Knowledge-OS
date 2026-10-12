"""Explicit CI-only pinned ffmpeg preparation; no install, PATH or runtime fallback changes."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import urllib.parse
import urllib.request
import zipfile

REPO = Path(__file__).absolute().parents[2]
LOCK = Path(__file__).with_name('windows_ffmpeg.lock.json')
spec = importlib.util.spec_from_file_location('ffmpeg_asset_boundary', Path(__file__).with_name('prepare_common_asr.py'))
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)

def pin():
    return json.loads(LOCK.read_text(encoding='utf-8'))

def fetch(destination, source):
    boundary.no_link(destination)
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            allowed_url(newurl)
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    allowed_url(source['url'])
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'ArcheAxis-CI-ffmpeg/1'})
    with urllib.request.build_opener(Redirect()).open(request, timeout=60) as response, destination.open('xb') as output:
        allowed_url(response.geturl())
        count = 0
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > source['bytes']:
                raise ValueError('Archive download budget exceeded')
            output.write(chunk)
    return boundary.check_asset(destination, source)

def allowed_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'github.com', 'release-assets.githubusercontent.com'}:
        raise ValueError('Unexpected archive source host')

def selected_members(archive, source):
    infos = archive.infolist()
    if len(infos) > source['maximum_entries'] or sum(i.file_size for i in infos) > source['maximum_expanded_bytes']:
        raise ValueError('Archive expansion budget exceeded')
    seen = set()
    selected = {}
    for info in infos:
        name = info.filename
        path = PurePosixPath(name)
        if ('\\' in name or ':' in name or path.is_absolute() or '..' in path.parts
                or not path.parts or path.parts[0] != source['prefix']):
            raise ValueError('Unsafe archive member path')
        if name.casefold() in seen:
            raise ValueError('Duplicate archive member')
        seen.add(name.casefold())
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode) or (info.external_attr & 0x400):
            raise ValueError('Linked archive member')
        relative = path.relative_to(source['prefix']).as_posix()
        if relative in source['selected']:
            if info.is_dir() or info.flag_bits & 1:
                raise ValueError('Selected member is not a plain file')
            selected[relative] = info
    if set(selected) != set(source['selected']):
        raise ValueError('Required binaries and license missing')
    return selected

def extract(archive_path, root, source):
    identities = {}
    with zipfile.ZipFile(archive_path) as archive:
        members = selected_members(archive, source)
        for name, info in members.items():
            destination = root / name
            boundary.no_link(destination)
            destination.parent.mkdir(exist_ok=True)
            with archive.open(info) as stream, destination.open('xb') as output:
                count = 0
                while chunk := stream.read(1024 * 1024):
                    count += len(chunk)
                    if count > info.file_size:
                        raise ValueError('Member expansion budget exceeded')
                    output.write(chunk)
            identities[name] = boundary.identity(destination)
    return identities

def tool_output(binary, arguments):
    result = subprocess.run([str(binary), '-nostdin', *arguments], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=60)
    if result.returncode or len(result.stdout) + len(result.stderr) > 1024 * 1024:
        raise ValueError('ffmpeg capability check failed')
    return result.stdout

def verify_capabilities(binary, source):
    version = tool_output(binary, ['-version']).splitlines()[0]
    if not version.startswith('ffmpeg version ' + source['version'] + '-') or source['variant'] not in version:
        raise ValueError('Pinned ffmpeg version/build mismatch')
    listing = tool_output(binary, ['-hide_banner', '-encoders'])
    for encoder in source['required_encoders']:
        if not re.search(r'^\s*[A-Z.]{6}\s+' + re.escape(encoder) + r'\s', listing, re.MULTILINE):
            raise ValueError('Required media encoder missing: ' + encoder)
    return {'version': version, 'required_encoders': source['required_encoders']}

def prepare(root, project=REPO):
    root = boundary.owned_path(root, project)
    if root.exists():
        raise ValueError('Existing root refused; unknown assets preserved')
    root.mkdir(parents=True, exist_ok=False)
    receipt = {'ok': False, 'qualification': 'NOT_EXECUTED',
               'scope': 'EXPLICIT_CI_TOOL_ONLY_NOT_PRODUCT_DISTRIBUTION_QUALIFIED'}
    # Establish a failure receipt before any download or execution.
    receipt_path = root / 'receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    try:
        source = pin()
        receipt.update(license=source['license'], pin_sha256=boundary.identity(LOCK)['sha256'])
        receipt['archive'] = fetch(root / 'package.zip', source)
        receipt['members'] = extract(root / 'package.zip', root, source)
        binary = root / 'bin/ffmpeg.exe'
        receipt['capability'] = verify_capabilities(binary, source)
        receipt.update(ok=True, qualification='CI_TOOL_VERSION_ENCODERS_VERIFIED_NOT_MEDIA_ASR_CORE',
                       ffmpeg=str(binary), ffprobe=str(root / 'bin/ffprobe.exe'))
    except Exception as error:
        receipt.update(error_type=type(error).__name__, error='CI tool preparation failed; no media/Core qualification')
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = prepare(args.root)
        print(json.dumps({'ok': receipt['ok'], 'receipt': str(args.root / 'receipt.json'), 'ffmpeg': receipt.get('ffmpeg')}))
        return 0 if receipt['ok'] else 1
    except Exception as error:
        print(json.dumps({'ok': False, 'qualification': 'NOT_EXECUTED', 'error_type': type(error).__name__,
                          'error': 'Unsafe, unavailable, or existing output root; no root overwrite'}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
