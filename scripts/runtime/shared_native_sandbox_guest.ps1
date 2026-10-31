# Offline SYSTEM mapping proof only. Never runs installer or historical native parent.
$ErrorActionPreference = 'Stop'
$binding = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__BINDING_BASE64__')) | ConvertFrom-Json -AsHashtable
$utf8 = [Text.UTF8Encoding]::new($false,$true)
$result = [ordered]@{schema='aaos.shared-native-inputs-guest-probe/v1';nonce=$binding.nonce;sandbox_id=$binding.sandbox_id;manifest_sha256=$binding.manifest_sha256;manifest_provenance='HOST_PINNED_NOT_GUEST_READ';status='FAIL';context='SYSTEM_MAPPING_PROBE_ONLY';groups=@{};readonly=@();members_verified=0;error=$null}
$private = @('.git','.codex','.hermes','.zcode','.mimosa','.trae','.dsh','.ui-task-tree','.hilo','.ssh','.agents','.env','.npmrc','.pypirc','.project-local','.venv','node_modules','__pycache__')
function Check-Name([string]$relative) {
    foreach ($part in ($relative -split '/')) {
        if (-not $part -or $part -in @('.','..') -or $part.TrimEnd(' ','.') -cne $part -or $part -match '[\x00-\x1f<>:"|?*\\]' -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)' -or $private -contains $part.ToLowerInvariant() -or $part.ToLowerInvariant().StartsWith('.env.')) {throw 'Private or unsafe native guest member'}
    }
}
try {
    if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18') {throw 'SYSTEM guest context required'}
    if ($binding.manifest_provenance -cne 'HOST_PINNED_NOT_GUEST_READ') {throw 'Unknown manifest provenance'}
    $expectedRoots = @{package='C:\AAOSInstall';input='C:\AAOSInput';tools='C:\AAOSTools'}
    if ($binding.groups.Count -ne 3) {throw 'Exactly three input groups required'}
    $trees = @{}
    # Inventory every group and reject private/reparse names before hashing any body.
    foreach ($group in @('package','input','tools')) {
        $root = $expectedRoots[$group]
        if ($binding.groups[$group].root -cne $root) {throw 'Guest root differs'}
        $rootInfo = [IO.DirectoryInfo]::new($root)
        if (-not $rootInfo.Exists -or ($rootInfo.Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'Invalid input mapping root'}
        $stack = [Collections.Generic.Stack[IO.DirectoryInfo]]::new()
        $stack.Push($rootInfo)
        $files = @{}
        $aliases = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        while ($stack.Count) {
            $directory = $stack.Pop()
            foreach ($item in $directory.EnumerateFileSystemInfos('*',[IO.SearchOption]::TopDirectoryOnly)) {
                $relative = [IO.Path]::GetRelativePath($root,$item.FullName).Replace('\','/')
                Check-Name $relative
                if (-not $aliases.Add($relative)) {throw 'Case alias in native input'}
                if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'Reparse native input rejected'}
                if ($item -is [IO.DirectoryInfo]) {$stack.Push($item)}
                elseif ($item -is [IO.FileInfo]) {$files.Add($relative,$item)}
                else {throw 'Nonregular native input'}
            }
        }
        $trees.Add($group,$files)
    }
    foreach ($group in @('package','input','tools')) {
        $files = $trees[$group]
        [string[]]$names = @($files.Keys)
        [Array]::Sort($names,[StringComparer]::Ordinal)
        $canonical = [IO.MemoryStream]::new()
        [long]$total = 0
        try {
            foreach ($relative in $names) {
                $item = $files[$relative]
                $item.Refresh()
                $beforeLength = $item.Length
                $beforeTime = $item.LastWriteTimeUtc.Ticks
                $stream = [IO.File]::Open($item.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
                try {
                    if ($stream.Length -ne $beforeLength) {throw 'Native member size raced'}
                    $sha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()
                } finally {$stream.Dispose()}
                $item.Refresh()
                if ($item.Length -ne $beforeLength -or $item.LastWriteTimeUtc.Ticks -ne $beforeTime -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'Native member changed while hashing'}
                $line = $relative + [char]0 + $beforeLength.ToString([Globalization.CultureInfo]::InvariantCulture) + [char]0 + $sha + [char]10
                $bytes = $utf8.GetBytes($line)
                $canonical.Write($bytes,0,$bytes.Length)
                $total += $beforeLength
            }
            $canonical.Position = 0
            $treeSha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($canonical)).ToLowerInvariant()
        } finally {$canonical.Dispose()}
        $proof = @{root=$expectedRoots[$group];members=$names.Count;bytes=$total;sha256=$treeSha}
        $expected = $binding.groups[$group]
        if ($proof.members -ne $expected.members -or $proof.bytes -ne $expected.bytes -or $proof.sha256 -cne $expected.sha256) {throw 'Complete native tree identity mismatch'}
        $result.groups.Add($group,$proof)
        $result.members_verified += $names.Count
    }
    foreach ($path in $binding.probes) {
        $denied = $false
        $handle = $null
        try {$handle = [IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)}
        catch {
            if (($_.Exception.GetBaseException().HResult -band 65535) -ne 5) {throw}
            $denied = $true
        } finally {if ($handle) {$handle.Dispose()}}
        $result.readonly += @{path=$path;write_open_access_denied=$denied}
        if (-not $denied) {throw 'Native input mapping allowed a write handle'}
    }
    $marker = $utf8.GetBytes('aaos-shared-probe:'+$binding.nonce)
    $stream = [IO.File]::Open($binding.output_marker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$stream.Write($marker,0,$marker.Length);$stream.Flush($true)} finally {$stream.Dispose()}
    $result.status = 'PASS_NATIVE_COMPLETE_TREES_READONLY_AND_FRESH_OUTPUT'
} catch {$result.error=@{type=$_.Exception.GetBaseException().GetType().FullName;message=$_.Exception.Message}}
$data = $utf8.GetBytes(($result | ConvertTo-Json -Depth 10))
$stream = [IO.File]::Open($binding.receipt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {$stream.Write($data,0,$data.Length);$stream.Flush($true)} finally {$stream.Dispose()}
if ($result.status -eq 'FAIL') {exit 1}
