# Runs only inside an offline test guest. All paths are the reviewed virtual mappings.
$ErrorActionPreference = 'Stop'
$binding = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__BINDING_BASE64__')) | ConvertFrom-Json
$result = [ordered]@{schema='aaos.shared-sandbox-guest-probe/v1';nonce=$binding.nonce;status='FAIL';context='SYSTEM_MAPPING_PROBE_ONLY';manifest_sha256=$binding.manifest_sha256;readonly=@();members_verified=0;error=$null}
try {
    if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18') {throw 'SYSTEM guest probe context required'}
    if ((Get-FileHash -LiteralPath $binding.manifest -Algorithm SHA256).Hash.ToLowerInvariant() -cne $binding.manifest_sha256) {throw 'Manifest identity mismatch'}
    $manifest = Get-Content -LiteralPath $binding.manifest -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($member in $manifest.files) {
        $item = Get-Item -LiteralPath $member.path -Force
        if ($item.Length -ne $member.bytes -or (Get-FileHash -LiteralPath $member.path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $member.sha256) {throw 'Guest member identity mismatch'}
        $result.members_verified++
    }
    foreach ($path in $binding.probes) {
        $denied = $false
        $handle = $null
        try {
            # Open for writing without modifying any original byte or truncating a file.
            $handle = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite)
        } catch {
            $base = $_.Exception.GetBaseException()
            if (($base.HResult -band 65535) -ne 5) {throw}
            $denied = $true
        } finally {if ($handle) {$handle.Dispose()}}
        $result.readonly += @{path=$path;write_open_access_denied=$denied}
        if (-not $denied) {throw 'Input mapping allowed a write handle'}
    }
    $marker = [Text.Encoding]::UTF8.GetBytes('aaos-shared-probe:'+$binding.nonce)
    $stream = [IO.File]::Open($binding.output_marker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$stream.Write($marker,0,$marker.Length);$stream.Flush($true)} finally {$stream.Dispose()}
    $result.status='PASS_READONLY_HANDLES_OUTPUT_WRITE_AND_INPUT_IDENTITIES'
} catch {$result.error=@{type=$_.Exception.GetBaseException().GetType().FullName;message=$_.Exception.Message}}
$data = [Text.UTF8Encoding]::new($false).GetBytes(($result | ConvertTo-Json -Depth 8))
$stream = [IO.File]::Open($binding.receipt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {$stream.Write($data,0,$data.Length);$stream.Flush($true)} finally {$stream.Dispose()}
if ($result.status -eq 'FAIL') {exit 1}
