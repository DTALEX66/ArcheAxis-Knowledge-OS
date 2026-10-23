param([switch]$IncludeLocalSources)
$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'MANIFEST.json') -Raw -Encoding utf8 | ConvertFrom-Json
if ($manifest.schema -ne 'aaos.owner-discussion-archive/v1') { throw 'Unexpected archive schema' }
$checked = 0
foreach ($member in $manifest.public_members) {
    $target = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $member.archive_path))
    if (-not $target.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path escapes project' }
    $item = Get-Item -LiteralPath $target
    if ($item.Length -ne $member.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $member.sha256) { throw "Public member mismatch: $($member.archive_path)" }
    $checked++
}
$localChecked = 0
if ($IncludeLocalSources) {
    $localRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot '.project-local/archives/owner-dialogue-20261022-desktop-launcher'))
    foreach ($member in $manifest.local_sources) {
        $target = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $member.archive_path))
        if (-not $target.StartsWith($localRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Local member escapes archive' }
        $item = Get-Item -LiteralPath $target
        if ($item.Length -ne $member.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $member.sha256) { throw "Local member mismatch: $($member.archive_path)" }
        $localChecked++
    }
}
$pointer = Get-Content -LiteralPath (Join-Path $repoRoot 'docs/current/AAOS-ACTIVE-EXECUTION.json') -Raw -Encoding utf8 | ConvertFrom-Json
foreach ($reference in @($manifest.decision_ref, $pointer.usable_release_and_launcher_decision.archive_ref, $pointer.usable_release_and_launcher_decision.design_ref, $pointer.active_progress)) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $reference))) { throw "Missing reference: $reference" }
}
[ordered]@{status='PASS'; evidence_level='STRUCTURAL_ARCHIVE_ONLY'; public_members=$checked; local_sources=$localChecked; product_tests='NOT_EXECUTED'; implementation_qualification='NOT_CHANGED'} | ConvertTo-Json
