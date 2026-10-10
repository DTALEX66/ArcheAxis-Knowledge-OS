"""Owned candidate WebView2, actual embedded bytes, 13x3 simulated viewport sweep."""
import argparse
import uuid
import hashlib
import base64
import struct
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import traceback
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
if __package__:
    from scripts.runtime import dev
else:
    import importlib.util
    # Direct CLI: load only these repository-owned modules without sys.path edits.
    for module_name in ('dev',):
        spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts/runtime" / (module_name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        globals()[module_name] = module
import aaos01_tauri_webdriver_loop as owned
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-receipt', type=Path, required=True)
    parser.add_argument('--run-id', help='Fresh project-local run; existing runs are never overwritten')
    args = parser.parse_args()
    paths = dev.layout(ROOT, args.run_id or "native-matrix-" + uuid.uuid4().hex[:12])
    env = dict(os.environ)
    env.update(dev.prepare(paths))
    os.environ['ARCHEAXIS_RUN_ROOT'] = str(paths['run'])
    spec = importlib.util.spec_from_file_location('a0', ROOT / 'scripts/a0_browser_smoke.py')
    a0 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a0)
    # WebView2 CDP reports float noise: 1 becomes 1.0000000149011612.
    # Verify a 1e-6 bound and retain the raw value; all layout assertions stay exact.
    def check_native_geometry(geometry, **options):
        raw = geometry['devicePixelRatio']
        expected = options['scale']
        assert abs(raw - expected) <= 1e-6, (raw, expected)
        checked = a0.check_geometry({**geometry, 'devicePixelRatio': expected}, **options)
        checked['devicePixelRatio'] = raw
        checked['dpi_absolute_tolerance'] = 1e-6
        return checked

    build_path = dev.safe_path(args.build_receipt)
    build_path.relative_to(paths['dev'] / 'runs')
    build = json.loads(build_path.read_text(encoding='utf-8'))
    locator_path = dev.safe_path(Path(build['frontend_locator']))
    locator_path.relative_to(paths['dev'] / 'runs')
    locator = json.loads(locator_path.read_text(encoding='utf-8'))
    host = dev.safe_path(Path(build['host']))
    host.relative_to(paths['cargo_build'] / 'release')
    dist = dev.safe_path(Path(locator['frontend_dist']))
    dist.relative_to(paths['dev'] / 'runs')
    if build['status'] != 'PASS' or not build['source_consistent'] or build['source_patch_sha256'] != env['ARCHEAXIS_SOURCE_PATCH_SHA256']:
        raise RuntimeError('candidate source mismatch')
    if hashlib.sha256(host.read_bytes()).hexdigest() != build['host_sha256']:
        raise RuntimeError('host hash mismatch')
    core = dev.safe_path(host.parent / 'core/archeaxis-api.exe')
    if hashlib.sha256(core.read_bytes()).hexdigest() != build['core_sha256']:
        raise RuntimeError('host resource Core hash mismatch')
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
    env['ARCHEAXIS_PORTABLE_ROOT'] = str(paths['tmp'] / 'workspace')
    env['WEBVIEW2_USER_DATA_FOLDER'] = str(paths['tmp'] / 'webview')
    env['ARCHEAXIS_WEBDRIVER_CDP_PORT'] = str(port)
    env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = f'--remote-debugging-port={port} --remote-debugging-address=127.0.0.1'
    for key in ('ARCHEAXIS_DEV_EXTERNAL_BACKEND',):
        env.pop(key, None)
    report = {'status': 'FAIL', 'evidence': 'REAL_TAURI_WEBVIEW2_WITH_SIMULATED_VIEWPORT_DPI', 'host': str(host), 'host_sha256': build['host_sha256'], 'core': str(core), 'core_sha256': build['core_sha256'], 'source_patch_sha256': build['source_patch_sha256'], 'bridge_stub_injected': False, 'installed': False, 'physical_dpi_ime_human_acceptance': 'NOT_EXECUTED', 'cases': [], 'assets': {}, 'errors': [], 'owned_cleanup': False}
    log = (paths['logs'] / 'host.log').open('x', encoding='utf-8')
    process = subprocess.Popen([str(host)], cwd=host.parent, env=env, stdout=log, stderr=subprocess.STDOUT)
    report['host_pid'] = process.pid
    processes = []
    try:
        deadline = time.monotonic() + 60
        while True:
            if process.poll() is not None:
                raise RuntimeError('candidate exited before CDP')
            try:
                with owned.loopback_urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1) as response:
                    report['engine'] = json.load(response).get('Browser')
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('candidate CDP not ready')
                time.sleep(.25)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
            context = browser.contexts[0]
            deadline = time.monotonic() + 30
            while not any(urlsplit(p.url).hostname == 'tauri.localhost' for p in context.pages):
                if time.monotonic() >= deadline:
                    raise RuntimeError('no owned Tauri page: ' + repr([p.url for p in context.pages]))
                time.sleep(.2)
            page = next(p for p in context.pages if urlsplit(p.url).hostname == 'tauri.localhost')
            page.set_default_timeout(30000)
            page.on('pageerror', lambda error: report['errors'].append(str(error)))
            report['url'] = page.url
            report['initial_pages'] = [p.url for p in context.pages]
            report['startup_dom'] = page.evaluate('({title:document.title,body:document.body.innerText.slice(0,4000)})')
            report['recovery_status'] = page.evaluate("async () => await window.__TAURI__.core.invoke('recovery_status')")
            page.screenshot(path=str(paths['artifacts'] / 'startup.png'), full_page=True)
            page.locator('.status-bar').wait_for()
            report['url'] = page.url
            assert urlsplit(page.url).hostname == 'tauri.localhost', page.url
            assert page.evaluate('typeof window.__A0_DOCUMENT_FIXTURE__') == 'undefined'
            assert page.evaluate('typeof window.__TAURI__.core.invoke') == 'function'
            page.wait_for_function("async () => (await window.__TAURI__.core.invoke('backend_info'))?.ready === true", timeout=60000)
            version = page.evaluate("async () => await window.__TAURI__.core.invoke('core_command', {request:{operation:'system_version',payload:{}}})")
            assert version['status'] == 200, version
            report['system_version'] = version['body']
            cdp = context.new_cdp_session(page)
            cdp.send('Emulation.setEmulatedMedia', {'features': [{'name':'prefers-reduced-motion','value':'reduce'}]})
            page.locator('[data-space-id="library"]').click()
            page.get_by_role("heading", name="资料库").first.wait_for()
            for label, width, height, scale in a0.DESKTOP_MATRIX:
                cdp.send('Emulation.setDeviceMetricsOverride', {'width':width, 'height':height, 'deviceScaleFactor':scale, 'mobile':False})
                for theme in a0.AAOS_THEME_IDS:
                    page.get_by_label('界面主题').select_option(theme)
                    page.wait_for_timeout(180)
                    assert page.evaluate('document.documentElement.dataset.aaosTheme') == theme
                    page.wait_for_function("() => {const i=document.querySelector('.status-bar-brand img');return i?.complete && i.naturalWidth>0}")
                    cdp.send('Emulation.clearDeviceMetricsOverride')
                    cdp.send('Emulation.setDeviceMetricsOverride', {'width':width, 'height':height, 'deviceScaleFactor':scale, 'mobile':False})
                    page.wait_for_function('expected => Math.abs(window.devicePixelRatio-expected)<=1e-6', arg=scale)
                    page.wait_for_timeout(100)
                    case = {'viewport':label, 'theme':theme, 'viewport_mode':'CDP_SIMULATED_DPI', 'geometry':check_native_geometry(a0.measure_geometry(page, a0.CHROME_BANDS), width=width, height=height, scale=scale, bands=a0.CHROME_BANDS), 'status_accessibility':a0.check_status_accessibility(page)}
                    resources = page.evaluate("() => [...document.querySelectorAll('script[src],link[rel=stylesheet][href],.status-bar-brand img')].map(e=>e.src||e.href)")
                    for url in resources:
                        if url in report['assets']:
                            continue
                        parsed = urlsplit(url)
                        assert parsed.hostname == 'tauri.localhost', url
                        path = dev.safe_path(dist / unquote(parsed.path.lstrip('/')))
                        path.relative_to(dist)
                        assert path.is_file(), str(path)
                        data = page.evaluate("async url => { const r=await fetch(url); if(!r.ok)throw Error('asset fetch '+r.status); return Array.from(new Uint8Array(await r.arrayBuffer())); }", url)
                        actual = hashlib.sha256(bytes(data)).hexdigest()
                        expected = hashlib.sha256(path.read_bytes()).hexdigest()
                        assert actual == expected, path.name
                        report['assets'][url] = {'relative':path.relative_to(dist).as_posix(), 'bytes':len(data), 'sha256':actual, 'matches_current_dist':True}
                    shot = paths['artifacts'] / f'{theme}-{label}.png'
                    case['before_screenshot_metrics'] = page.evaluate('({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,visualScale:visualViewport.scale})')
                    captured = cdp.send('Page.captureScreenshot', {'format':'png','fromSurface':True,'captureBeyondViewport':False,'clip':{'x':0,'y':0,'width':width,'height':height,'scale':1}})
                    shot.write_bytes(base64.b64decode(captured['data']))
                    case['after_screenshot_metrics'] = page.evaluate('({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,visualScale:visualViewport.scale})')
                    assert abs(case['after_screenshot_metrics']['dpr']-scale)<=1e-6, case
                    assert case['after_screenshot_metrics']['width']==width and case['after_screenshot_metrics']['height']==height, case
                    png_width, png_height = struct.unpack('>II', shot.read_bytes()[16:24])
                    case['screenshot_dimensions'] = {'width':png_width,'height':png_height,'expected_width':round(width*scale),'expected_height':round(height*scale)}
                    assert (png_width,png_height)==(round(width*scale),round(height*scale)), case['screenshot_dimensions']
                    case['screenshot'] = str(shot)
                    report['cases'].append(case)
            assert len(report['cases']) == 39 and len(report['assets']) >= 5
            assert not report['errors'], report['errors']
            report['status'] = 'PASS'
            processes = owned.owned_process_rows(owned.native_process_rows(), process.pid)
            report['owned_process_metadata'] = processes
            with suppress(Exception):
                page.evaluate("() => window.__TAURI__.core.invoke('exit_application')")
            browser.close()
    except BaseException as error:
        report['failure'] = type(error).__name__ + ': ' + str(error)
        report['traceback'] = traceback.format_exc()
    finally:
        if not processes and process.poll() is None:
            with suppress(Exception):
                processes = owned.owned_process_rows(owned.native_process_rows(), process.pid)
        try:
            if process.poll() is None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    dev.stop_owned_process(process)
            current = {row['pid']:row for row in owned.native_process_rows()}
            remaining = [row['pid'] for row in processes if row['pid'] in current and current[row['pid']]['created'] == row['created']]
            deadline = time.monotonic() + 15
            while remaining and time.monotonic() < deadline:
                time.sleep(.25)
                current = {row['pid']:row for row in owned.native_process_rows()}
                remaining = [row['pid'] for row in processes if row['pid'] in current and current[row['pid']]['created'] == row['created']]
            report['owned_process_metadata'] = processes
            report['owned_cleanup'] = process.poll() is not None and not remaining
            report['remaining_owned_processes'] = remaining
            if not report['owned_cleanup']:
                report['status'] = 'FAIL'
        except BaseException as error:
            report['cleanup_failure'] = type(error).__name__ + ': ' + str(error)
            report['status'] = 'FAIL'
        log.close()
        _, after = dev.worktree_identity(ROOT)
        report['source_consistent'] = after == report['source_patch_sha256']
        report['host_hash_unchanged'] = hashlib.sha256(host.read_bytes()).hexdigest() == report['host_sha256']
        report['core_hash_unchanged'] = hashlib.sha256(core.read_bytes()).hexdigest() == report['core_sha256']
        if not all(report[k] for k in ('source_consistent','host_hash_unchanged','core_hash_unchanged')):
            report['status'] = 'FAIL'
        (paths['artifacts'] / 'receipt.json').open('x', encoding='utf-8').write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:report.get(k) for k in ('status','failure','url','engine','owned_cleanup','source_consistent')}))
    print('cases=' + str(len(report['cases'])) + '; assets=' + str(len(report['assets'])))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == "__main__":
    raise SystemExit(main())
