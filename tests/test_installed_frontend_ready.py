"""Synthetic owned processes and real Chromium/.NET transport; no installed Host."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import pytest
from playwright.sync_api import sync_playwright
from scripts import a0_browser_smoke
from scripts.probes import installed_frontend_ready as ready

PWSH = shutil.which('pwsh')
ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform != 'win32' or not PWSH,
                               reason='Actual Windows ownership and .NET transport require PowerShell 7')


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def identity(pid):
    result = subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-Command',
        f'$p=[Diagnostics.Process]::GetProcessById({pid});'
        '@{created=$p.StartTime.ToUniversalTime().ToFileTimeUtc().ToString();'
        'path=$p.MainModule.FileName}|ConvertTo-Json -Compress'],
        capture_output=True, text=True, encoding='utf-8', timeout=10, check=True)
    return json.loads(result.stdout)


def observe(pid, port, timeout=8):
    owned = identity(pid)
    return ready.observe(host_pid=pid, host_created=owned['created'],
                         host_path=Path(owned['path']), port=port, timeout_seconds=timeout)


def test_startup_port_and_environment_are_child_only(tmp_path, monkeypatch):
    monkeypatch.setenv('ARCHEAXIS_WEBDRIVER_CDP_PORT', 'PARENT_SENTINEL')
    output = tmp_path / 'child.json'
    child = tmp_path / 'child.py'
    child.write_text('import json,os,sys;from pathlib import Path;'
                     'Path(sys.argv[1]).write_text(json.dumps(dict(port=os.environ.get('
                     '"ARCHEAXIS_WEBDRIVER_CDP_PORT"))))', encoding='utf-8')
    driver = tmp_path / 'driver.ps1'
    driver.write_text(r"""
param($Source,$Python,$Child,$Output)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw 'Parser errors'}
$names=@('New-ArcheAxisStartupPort','Start-ArcheAxisObservedShell')
foreach ($function in $ast.FindAll({param($n)
  $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$true)) {
  . ([scriptblock]::Create($function.Extent.Text))
}
$port=New-ArcheAxisStartupPort
$childProcess=Start-ArcheAxisObservedShell -Executable $Python -Port $port -Arguments @($Child,$Output)
if (-not $childProcess.WaitForExit(10000) -or $childProcess.ExitCode -ne 0) {throw 'Fixture failed'}
@{port=$port;parent=$env:ARCHEAXIS_WEBDRIVER_CDP_PORT}|ConvertTo-Json -Compress
""", encoding='utf-8')
    result = subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-File', str(driver),
        '-Source', str(ROOT / 'desktop/scripts/verify_nsis_install.ps1'),
        '-Python', sys.executable, '-Child', str(child), '-Output', str(output)],
        capture_output=True, text=True, encoding='utf-8', timeout=20, check=True)
    proof = json.loads(result.stdout)
    assert 1024 <= proof['port'] <= 65535
    assert proof['parent'] == os.environ['ARCHEAXIS_WEBDRIVER_CDP_PORT'] == 'PARENT_SENTINEL'
    assert json.loads(output.read_text())['port'] == str(proof['port'])
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', proof['port']))  # Allocator released its reservation.


def test_recycled_host_identity_is_rejected_before_connecting():
    owned = identity(os.getpid())
    code, proof = ready.observe(host_pid=os.getpid(), host_created='1',
                               host_path=Path(owned['path']), port=free_port(), timeout_seconds=3)
    assert code != 0 and proof['status'] == 'ERROR', proof
    assert proof['phase'] == 'OWNERSHIP', proof
    assert proof['failure_code'] == 'OWNED_HOST_IDENTITY_CHANGED', proof
    assert proof['last_observation']['bridge_ready'] is None


def test_absent_listener_waits_to_same_deadline():
    started = time.monotonic()
    code, proof = observe(os.getpid(), free_port(), timeout=3)
    assert code != 0 and proof['status'] == 'TIMEOUT', proof
    assert proof['phase'] == 'OWNERSHIP', proof
    assert 2.5 <= proof['seconds'] < 6, proof
    assert time.monotonic() - started < 15


def test_cim_creation_comparison_uses_actual_microsecond_truncation_and_rejects_recycling():
    command = r'''
$ErrorActionPreference='Stop'
$source=[Console]::In.ReadToEnd();$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw 'Observer parser errors'}
$function=@($ast.FindAll({param($n)
  $n -is [Management.Automation.Language.FunctionDefinitionAst] -and
  $n.Name -eq 'Test-ArcheAxisCimCreationIdentity'},$true))
if ($function.Count -ne 1) {throw 'Expected one identity comparator'}
. ([scriptblock]::Create($function[0].Extent.Text))
$native=[Diagnostics.Process]::GetProcessById($PID).StartTime.ToUniversalTime().ToFileTimeUtc()
$cim=(Get-CimInstance Win32_Process -Filter "ProcessId=$PID").CreationDate.ToUniversalTime().ToFileTimeUtc()
@{actual_match=(Test-ArcheAxisCimCreationIdentity $native $cim);delta=($native-$cim);cim_mod10=($cim%10);
  cases=@(
    (Test-ArcheAxisCimCreationIdentity 134376032241866830L 134376032241866830L)
    (Test-ArcheAxisCimCreationIdentity 134376032241866839L 134376032241866830L)
    (Test-ArcheAxisCimCreationIdentity 134376032241866840L 134376032241866830L)
    (Test-ArcheAxisCimCreationIdentity 134376032241866829L 134376032241866830L)
    (Test-ArcheAxisCimCreationIdentity 134376032241866830L 134376032241866831L)
  )}|ConvertTo-Json -Compress
'''
    result = subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-Command', command],
        input=ready.CDP_OBSERVER, capture_output=True, text=True, encoding='utf-8', timeout=10, check=True)
    proof = json.loads(result.stdout)
    assert proof['actual_match'] is True and proof['cim_mod10'] == 0, proof
    assert 0 <= proof['delta'] <= 9, proof
    assert proof['cases'] == [True, True, False, False, False], proof


@pytest.mark.parametrize('mode', ['http-error', 'websocket-error', 'wrong-owner'])
def test_real_transport_errors_and_foreign_listener_fail_closed(tmp_path, mode):
    port = free_port()
    server = tmp_path / 'server.py'
    server.write_text(r'''
import http.server,json,sys,threading
port=int(sys.argv[1]);mode=sys.argv[2]
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  if self.path=='/stop':
   self.send_response(200);self.end_headers();threading.Thread(target=self.server.shutdown).start();return
  if mode=='http-error' or self.path!='/json/list':
   self.send_response(500);self.end_headers();self.wfile.write(b'SYNTHETIC_PRIVATE_RESPONSE');return
  body=json.dumps([dict(type='page',url='http://tauri.localhost/?private=SYNTHETIC',
    webSocketDebuggerUrl=f'ws://127.0.0.1:{port}/devtools/page/synthetic')]).encode()
  self.send_response(200);self.end_headers();self.wfile.write(body)
server=http.server.HTTPServer(('127.0.0.1',port),Handler)
print('LISTENING',flush=True);server.serve_forever()
''', encoding='utf-8')
    owner = None
    process = subprocess.Popen([sys.executable, str(server), str(port), mode],
                               stdout=subprocess.PIPE, text=True, encoding='utf-8')
    try:
        assert process.stdout.readline().strip() == 'LISTENING'
        target_pid = process.pid
        if mode == 'wrong-owner':
            owner = subprocess.Popen([sys.executable, '-c', 'import sys;sys.stdin.read()'],
                                     stdin=subprocess.PIPE)
            target_pid = owner.pid  # Server is a sibling, never owned by this fixture.
        code, proof = observe(target_pid, port)
        assert code != 0 and proof['status'] == 'ERROR', proof
        if mode == 'wrong-owner':
            assert proof['phase'] == 'OWNERSHIP', proof
            assert proof['failure_code'] == 'OWNED_CDP_LISTENER_MISMATCH', proof
        elif mode == 'http-error':
            assert proof['phase'] == 'CDP_TARGET', proof
            assert proof['failure_code'] == 'CDP_CATALOG_STATUS', proof
        else:
            assert proof['phase'] == 'CDP_EVALUATE', proof
        assert 'SYNTHETIC' not in json.dumps(proof)
    finally:
        from urllib.request import urlopen
        with urlopen(f'http://127.0.0.1:{port}/stop', timeout=3):
            pass
        process.wait(timeout=10)
        if owner:
            owner.stdin.close()
            owner.wait(timeout=10)


def test_actual_dotnet_late_listener_ready_and_unready_chromium(tmp_path):
    executable = a0_browser_smoke._declared_tool('ext.toolchains.playwright-chromium', 'playwright-chromium')
    assert executable, 'Use existing declared Chromium, never install implicitly'
    port = free_port()
    process = None
    browser = None
    with ThreadPoolExecutor(max_workers=1) as pool, sync_playwright() as playwright:
        pending = pool.submit(observe, os.getpid(), port, 20)
        time.sleep(.5)  # Fixture intentionally starts its listener after observation begins.
        process = subprocess.Popen([executable, '--headless', '--no-first-run',
            '--disable-background-networking', '--remote-debugging-address=127.0.0.1',
            f'--remote-debugging-port={port}', f'--user-data-dir={tmp_path / "chromium"}', 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while browser is None:
                try:
                    browser = playwright.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=750)
                except Exception:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(.1)
            page = browser.contexts[0].pages[0]
            page.route('http://tauri.localhost/**', lambda route: route.fulfill(
                body='<html><body>synthetic fixture</body></html>', content_type='text/html'))
            page.goto('http://tauri.localhost/start?credential=SYNTHETIC#private')
            page.evaluate("""window.calls=0;window.reads=0;Object.defineProperty(window,'__TAURI__',{
              get(){window.reads++;return {core:{invoke(){window.calls++}}}}});""")
            try:
                page.wait_for_function('window.reads>0', timeout=12000)
            except Exception:
                if pending.done():
                    raise AssertionError(pending.result())
                raise
            page.evaluate("document.body.innerHTML='<div class=app-shell data-stitch-workspace></div>'")
            code, proof = pending.result(timeout=25)
            assert code == 0 and proof['status'] == 'PASS', proof
            assert proof['last_observation'] == dict(url='http://tauri.localhost/start',
                bridge_ready=True, root_ready=True, document_state='complete')
            assert 'SYNTHETIC' not in json.dumps(proof)
            assert page.evaluate('window.calls') == 0
            assert '?credential=SYNTHETIC#private' in page.url
            page.evaluate('document.querySelector(".app-shell").remove()')
            code, proof = observe(os.getpid(), port, timeout=4)
            assert code != 0 and proof['status'] == 'TIMEOUT', proof
            assert proof['last_observation']['bridge_ready'] is True
            assert proof['last_observation']['root_ready'] is False
            assert page.evaluate('window.calls') == 0
        finally:
            if browser:
                try:
                    browser.contexts[0].new_cdp_session(browser.contexts[0].pages[0]).send('Browser.close')
                except Exception:
                    pass  # Browser.close normally disconnects its CDP socket.
                browser.close()
            if process:
                process.wait(timeout=15)
