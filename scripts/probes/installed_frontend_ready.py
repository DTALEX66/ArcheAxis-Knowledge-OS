"""Read-only startup CDP observation for an already-owned installed Host.

No Host launch/close, business invoke, browser installation or third-party Python
dependency. PowerShell 7's .NET ClientWebSocket supplies the CDP transport.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def observation_script() -> str:
    tree = ast.parse((ROOT / 'scripts/probes/aaos01_tauri_webdriver_loop.py').read_text(encoding='utf-8'))
    values = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'NATIVE_FRONTEND_OBSERVATION_JS'
                      for target in node.targets)
              and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
    if len(values) != 1:
        raise ValueError('Expected one repository-owned frontend observation literal')
    return '(()=>{' + values[0] + '})()'


CDP_OBSERVER = r"""
$ErrorActionPreference='Stop'
function Test-ArcheAxisCimCreationIdentity {
  param([long]$NativeTime,[long]$CimTime)
  # Win32_Process CreationDate truncates FILETIME to whole microseconds.
  # Keep Int64 arithmetic: floating division loses precision at FILETIME scale.
  return ($CimTime % 10 -eq 0 -and ($NativeTime-($NativeTime % 10)) -eq $CimTime)
}
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$request=[Console]::In.ReadToEnd() | ConvertFrom-Json
$proof=[ordered]@{schema='archeaxis/installed-frontend-ready/v1';status='WAITING';
  observation_only=$true;host_pid=$request.host_pid;host_created=$request.host_created;
  port=$request.port;phase='OWNERSHIP';
  last_observation=@{url=$null;bridge_ready=$null;root_ready=$null;document_state=$null}}
$watch=[Diagnostics.Stopwatch]::StartNew()
$socket=$null
$http=$null
$cancellation=[Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds($request.timeout_seconds))
try {
  $hostProcess=[Diagnostics.Process]::GetProcessById([int]$request.host_pid)
  if ($hostProcess.StartTime.ToUniversalTime().ToFileTimeUtc().ToString() -ne [string]$request.host_created) {
    throw 'OWNED_HOST_IDENTITY_CHANGED'
  }
  if ([IO.Path]::GetFullPath($hostProcess.MainModule.FileName) -ne [IO.Path]::GetFullPath($request.host_path)) {
    throw 'OWNED_HOST_PATH_CHANGED'
  }
  $handler=[Net.Http.HttpClientHandler]::new();$handler.UseProxy=$false;$handler.AllowAutoRedirect=$false
  $http=[Net.Http.HttpClient]::new($handler);$http.Timeout=[TimeSpan]::FromSeconds(2)
  while ($watch.Elapsed.TotalSeconds -lt $request.timeout_seconds) {
    $hostProcess.Refresh()
    if ($hostProcess.HasExited) {throw 'OWNED_HOST_EXITED'}
    $proof.owned_window=@{responding=$hostProcess.Responding;has_window=($hostProcess.MainWindowHandle -ne [IntPtr]::Zero)}
    $proof.phase='OWNERSHIP'
    try {
      $listeners=@(Get-NetTCPConnection -LocalPort ([int]$request.port) -State Listen -ErrorAction Stop)
    } catch {
      if ($_.CategoryInfo.Category -ne 'ObjectNotFound') {throw}
      $listeners=@()
    }
    if (-not $listeners.Count) {Start-Sleep -Milliseconds 150;continue}
    if ($listeners.Count -ne 1) {throw 'OWNED_CDP_LISTENER_AMBIGUOUS'}
    $rows=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CreationDate)
    $owned=@{([int]$request.host_pid)=[long]$request.host_created}
    do {
      $changed=$false
      foreach ($row in $rows) {
        $pidValue=[int]$row.ProcessId; $parentValue=[int]$row.ParentProcessId
        if (-not $owned.ContainsKey($pidValue) -and $owned.ContainsKey($parentValue)) {
          $created=$row.CreationDate.ToUniversalTime().ToFileTimeUtc()
          if ($created -ge $owned[$parentValue]) {$owned[$pidValue]=$created;$changed=$true}
        }
      }
    } while ($changed)
    $ownerValue=[int]$listeners[0].OwningProcess
    if ($listeners[0].LocalAddress -ne '127.0.0.1' -or -not $owned.ContainsKey($ownerValue)) {
      throw 'OWNED_CDP_LISTENER_MISMATCH'
    }
    $ownerProcess=[Diagnostics.Process]::GetProcessById($ownerValue)
    $ownerCreated=$ownerProcess.StartTime.ToUniversalTime().ToFileTimeUtc()
    $sameCreation=if ($ownerValue -eq [int]$request.host_pid) {
      $ownerCreated -eq [long]$request.host_created
    } else {
      Test-ArcheAxisCimCreationIdentity -NativeTime $ownerCreated -CimTime $owned[$ownerValue]
    }
    if (-not $sameCreation) {
      throw 'OWNED_CDP_LISTENER_RECYCLED'
    }
    $proof.owned_listener_pids=@($ownerValue)
    $proof.phase='CDP_TARGET'
    $response=$http.GetAsync("http://127.0.0.1:$($request.port)/json/list",$cancellation.Token).GetAwaiter().GetResult()
    try {
      if ([int]$response.StatusCode -ne 200) {throw 'CDP_CATALOG_STATUS'}
      $catalog=$response.Content.ReadAsStringAsync($cancellation.Token).GetAwaiter().GetResult()
      if ($catalog.Length -gt 131072) {throw 'CDP_CATALOG_TOO_LARGE'}
      $targets=@(($catalog | ConvertFrom-Json) | Where-Object {
        $_.type -eq 'page' -and ($_.url -match '^http://tauri\.localhost/' -or $_.url -match '^tauri://localhost/')})
    } finally {$response.Dispose()}
    if ($targets.Count -gt 1) {throw 'CDP_NATIVE_PAGE_AMBIGUOUS'}
    if ($targets.Count -eq 0) {Start-Sleep -Milliseconds 150;continue}
    $address=[Uri]$targets[0].webSocketDebuggerUrl
    if ($address.Scheme -ne 'ws' -or $address.Host -ne '127.0.0.1' -or
        $address.Port -ne $request.port -or $address.UserInfo -or
        -not $address.AbsolutePath.StartsWith('/devtools/page/')) {throw 'CDP_ADDRESS_REFUSED'}
    $proof.phase='CDP_EVALUATE'
    $socket=[Net.WebSockets.ClientWebSocket]::new()
    $null=$socket.ConnectAsync($address,$cancellation.Token).GetAwaiter().GetResult()
    $message=@{id=1;method='Runtime.evaluate';params=@{expression=$request.expression;returnByValue=$true}}
    $bytes=[Text.Encoding]::UTF8.GetBytes(($message | ConvertTo-Json -Depth 6 -Compress))
    $null=$socket.SendAsync([ArraySegment[byte]]::new($bytes),[Net.WebSockets.WebSocketMessageType]::Text,$true,$cancellation.Token).GetAwaiter().GetResult()
    $stream=[IO.MemoryStream]::new();$buffer=[byte[]]::new(8192)
    try {
      do {
        $received=$socket.ReceiveAsync([ArraySegment[byte]]::new($buffer),$cancellation.Token).GetAwaiter().GetResult()
        if ($received.MessageType -ne [Net.WebSockets.WebSocketMessageType]::Text) {throw 'CDP_NON_TEXT_RESPONSE'}
        $stream.Write($buffer,0,$received.Count)
        if ($stream.Length -gt 65536) {throw 'CDP_RESPONSE_TOO_LARGE'}
      } while (-not $received.EndOfMessage)
      $reply=[Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
    } finally {$stream.Dispose();$socket.Dispose();$socket=$null}
    if ($reply.id -ne 1 -or $reply.error -or $reply.result.exceptionDetails) {throw 'CDP_EVALUATION_REFUSED'}
    $observed=$reply.result.result.value
    $proof.last_observation=$observed
    if ($observed.bridge_ready -eq $true -and $observed.root_ready -eq $true -and
        $observed.document_state -in @('interactive','complete')) {$proof.status='PASS';break}
    Start-Sleep -Milliseconds 150
  }
  if ($proof.status -ne 'PASS') {$proof.status='TIMEOUT'}
} catch {
  $proof.status=if ($watch.Elapsed.TotalSeconds -ge $request.timeout_seconds) {'TIMEOUT'} else {'ERROR'}
  # Type/phase only: never serialize HTTP bodies, page HTML or raw exception text.
  $proof.error_type=$_.Exception.GetType().Name
  if ($_.Exception.Message -match '^(OWNED_[A-Z_]+|CDP_[A-Z_]+)$') {$proof.failure_code=$_.Exception.Message}
} finally {
  if ($socket) {$socket.Dispose()}
  if ($cancellation) {$cancellation.Dispose()}
  if ($http) {$http.Dispose()}
  $proof.seconds=$watch.Elapsed.TotalSeconds
}
$proof | ConvertTo-Json -Depth 8 -Compress
if ($proof.status -ne 'PASS') {exit 1}
"""


def observe(*, host_pid: int, host_created: str, host_path: Path, port: int,
            timeout_seconds: float = 30) -> tuple[int, dict]:
    if host_pid <= 0 or not host_created.isdecimal() or not 1024 <= port <= 65535:
        raise ValueError('Invalid owned process/port identity')
    if not 0 < timeout_seconds <= 30:
        raise ValueError('Startup timeout must be positive and at most 30 seconds')
    powershell = shutil.which('pwsh')
    if not powershell:
        raise RuntimeError('Existing PowerShell 7 is required')
    # MainModule reports the loaded path, including any parent junction alias.
    # Preserve it for the observer's exact GetFullPath comparison on both sides.
    payload = {'host_pid': host_pid, 'host_created': host_created, 'host_path': str(host_path.absolute()),
               'port': port, 'timeout_seconds': timeout_seconds, 'expression': observation_script()}
    result = subprocess.run([powershell, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', CDP_OBSERVER],
                            input=json.dumps(payload), text=True, encoding='utf-8',
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        proof = json.loads(result.stdout)
    except (TypeError, ValueError):
        proof = {'schema':'archeaxis/installed-frontend-ready/v1','status':'ERROR',
                 'observation_only':True,'phase':'OBSERVER_PROTOCOL','error_type':'InvalidObserverResult'}
    return result.returncode, proof


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-pid', type=int, required=True)
    parser.add_argument('--host-created', required=True)
    parser.add_argument('--host-path', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    try:
        code, proof = observe(host_pid=args.host_pid, host_created=args.host_created,
                              host_path=args.host_path, port=args.port)
    except Exception as error:
        code, proof = 1, {'schema':'archeaxis/installed-frontend-ready/v1','status':'ERROR',
                          'observation_only':True,'phase':'OBSERVER','error_type':type(error).__name__}
    proof['source_commit'] = os.environ.get('ARCHEAXIS_SOURCE_COMMIT')
    proof['source_patch_sha256'] = os.environ.get('ARCHEAXIS_SOURCE_PATCH_SHA256')
    proof['qualification'] = 'READONLY_FRONTEND_STARTUP_ONLY'
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(proof, ensure_ascii=False))
    return 0 if code == 0 and proof.get('status') == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
