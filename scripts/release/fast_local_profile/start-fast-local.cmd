@echo off
setlocal DisableDelayedExpansion
set "AAOS_FAST_KIT=%~dp0"
set "AAOS_FAST_BACKEND=%~1"
set "AAOS_FAST_DATA=%~2"
set "AAOS_FAST_MODE=%~3"
powershell.exe -NoLogo -NoProfile -STA -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "try {" ^
  "  $kit = [IO.DirectoryInfo]$env:AAOS_FAST_KIT;" ^
  "  $target = $env:AAOS_FAST_BACKEND;" ^
  "  if (!$target -and $kit.Parent) {" ^
  "    foreach ($candidate in @($kit.Parent.FullName, (Join-Path $kit.Parent.FullName 'backend'))) {" ^
  "      if (Test-Path -LiteralPath (Join-Path $candidate 'backend-runtime-manifest.json') -PathType Leaf) { $target = $candidate; break }" ^
  "    }" ^
  "  }" ^
  "  if (!$target) {" ^
  "    Add-Type -AssemblyName System.Windows.Forms;" ^
  "    $pick = New-Object System.Windows.Forms.OpenFileDialog;" ^
  "    try {" ^
  "      $pick.Title = 'Select start-backend.cmd from your ArcheAxis backend';" ^
  "      $pick.Filter = 'ArcheAxis backend (start-backend.cmd)|start-backend.cmd';" ^
  "      if ($pick.ShowDialog() -ne 'OK') { exit 2 }; $target = $pick.FileName" ^
  "    } finally { $pick.Dispose() }" ^
  "  }" ^
  "  $item = Get-Item -LiteralPath $target;" ^
  "  if ($item.PSIsContainer) { $backend = $item.FullName }" ^
  "  elseif ($item.Name -ieq 'start-backend.cmd') { $backend = $item.DirectoryName }" ^
  "  else { throw 'Select the backend directory or its start-backend.cmd.' };" ^
  "  $python = Join-Path $backend 'runtime\python.exe';" ^
  "  if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw 'The selected folder has no packaged Python runtime.' };" ^
  "  $data = $env:AAOS_FAST_DATA;" ^
  "  if (!$data) { $data = Join-Path $env:LOCALAPPDATA 'ArcheAxis Knowledge\Fast Local\data' };" ^
  "  $launch = @('-I', '-B', (Join-Path $kit.FullName 'start-backend.py'), '--backend-root', $backend, '--machine-profile', 'fast-local', '--machine-profile-root', $kit.FullName.TrimEnd('\'), '--data-root', [IO.Path]::GetFullPath($data));" ^
  "  if ($env:AAOS_FAST_MODE) { if ($env:AAOS_FAST_MODE -ne '--smoke') { throw 'The optional third argument is --smoke.' }; $launch += '--smoke' };" ^
  "  & $python @launch; exit $LASTEXITCODE" ^
  "} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 2 }"
set "result=%errorlevel%"
if not "%result%"=="0" if not defined AAOS_FAST_BACKEND pause
exit /b %result%
