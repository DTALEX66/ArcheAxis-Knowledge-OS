$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Add-Type -Path (Join-Path $repoRoot 'apps/ArcheAxis.Desktop/UserDisplay.cs') -ReferencedAssemblies @((Join-Path $PSHOME 'ref/System.Text.Json.dll'), (Join-Path $PSHOME 'ref/System.Memory.dll'), (Join-Path $PSHOME 'ref/System.Collections.dll')) -CompilerOptions '/nullable:enable'
if ([ArcheAxis.Desktop.UserDisplay]::Status('future-state') -ne '状态待确认') { throw 'unknown state must stay unknown' }
if ([ArcheAxis.Desktop.UserDisplay]::Status('failed') -ne '处理失败') { throw 'failure must remain visible' }
if ([ArcheAxis.Desktop.UserDisplay]::Date('invalid date') -ne '时间未提供') { throw 'invalid date must stay unknown' }
if ([ArcheAxis.Desktop.UserDisplay]::Failure('{"error":"资料损坏，无法提取正文"}') -ne '资料损坏，无法提取正文') { throw 'meaningful JSON failure must remain visible' }
if ([ArcheAxis.Desktop.UserDisplay]::Failure('{"unknown":{"internal":"value"}}') -ne '处理失败，请查看详细记录。') { throw 'raw JSON must not appear by default' }
if ([ArcheAxis.Desktop.UserDisplay]::Failure("资料损坏`n at Worker.Internal()") -ne '资料损坏') { throw 'stack must stay out of normal message' }
if ([ArcheAxis.Desktop.UserDisplay]::Failure('读取失败（HTTP 503），请重试') -ne '读取失败，请重试') { throw 'protocol detail must stay out of normal message' }
if ([ArcheAxis.Desktop.UserDisplay]::Failure('Core returned a different job_id') -ne '任务记录与请求不一致，请刷新后重试。') { throw 'source mismatch meaning must remain visible without protocol identifiers' }
Write-Output 'USER DISPLAY PASS'
