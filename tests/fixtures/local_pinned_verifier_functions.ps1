#requires -Version 7.0
param([Parameter(Mandatory=$true)][string]$Source)
$Proposal = $Source
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
if (-not $env:ARCHEAXIS_RUN_ROOT -or -not [IO.Path]::IsPathFullyQualified($env:ARCHEAXIS_RUN_ROOT)) {
    throw 'canonical dev.py ARCHEAXIS_RUN_ROOT is required'
}
$run = [IO.Path]::GetFullPath($env:ARCHEAXIS_RUN_ROOT)
$fixtureRoot = Join-Path $run ('artifacts/local-pinned-functions-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($fixtureRoot)
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Proposal, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'verifier does not parse' }
# Six audited local helpers, plus the separately audited pure mode guard.
$allowed = @('Assert-LocalPinnedFile', 'Read-LocalPinnedJson', 'Assert-LocalPinnedMemberName',
             'Read-LocalPinnedPackaging', 'Assert-LocalInstallerBinding', 'Read-InstalledLocalPinnedPayload',
             'Assert-LocalIdentityMode')
foreach ($name in $allowed) {
    $definitions = @($ast.FindAll({ param($node)
        $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
    }, $true))
    if ($definitions.Count -ne 1) { throw "expected exactly one audited definition: $name" }
    # Load ONLY a function definition's AST extent, never the lifecycle script.
    . ([scriptblock]::Create($definitions[0].Extent.Text))
}
function Native([string]$Path) { if ($IsWindows -and -not $Path.StartsWith('\\?\')) { '\\?\' + $Path } else { $Path } }
function Write-Synthetic([string]$Path, [byte[]]$Bytes) {
    $null = [IO.Directory]::CreateDirectory((Native ([IO.Path]::GetDirectoryName($Path))))
    [IO.File]::WriteAllBytes((Native $Path), $Bytes)
}
function Write-Json([string]$Path, $Object) {
    Write-Synthetic $Path ([Text.UTF8Encoding]::new($false).GetBytes(($Object | ConvertTo-Json -Depth 100)))
}
function Row([string]$Path) {
    @{bytes = ([IO.FileInfo]::new((Native $Path))).Length; sha256 = (Get-FileHash -LiteralPath (Native $Path)).Hash.ToLowerInvariant()}
}
function Save-Identity([string]$Raw = '') {
    if ($Raw) { Write-Synthetic $script:case.IdentityPath ([Text.UTF8Encoding]::new($false).GetBytes($Raw)) }
    else { Write-Json $script:case.IdentityPath $script:case.Identity }
    $script:case.Receipt.identity = Row $script:case.IdentityPath
    Write-Json $script:case.ReceiptPath $script:case.Receipt
    $script:ExpectedLocalPinnedIdentitySha256 = (Row $script:case.ReceiptPath).sha256
}
function New-Case {
    $root = Join-Path $fixtureRoot ([Guid]::NewGuid().ToString('N'))
    $script:installRoot = Join-Path $root 'synthetic-install'
    $files = [ordered]@{}
    $longName = 'runtime/' + ((@('long-directory-segment') * 14) -join '/') + '/.hash/member.bin'
    foreach ($name in @('ArcheAxis.exe', 'core/archeaxis-api.exe', 'backend-runtime-manifest.json',
                        'runtime/Lib/site-packages/app/release-manifest.json',
                        'runtime/Lib/site-packages/aiohttp/.hash/_cparser.pxd.hash', 'runtime/Scripts/.empty', $longName)) {
        $path = Join-Path $script:installRoot $name
        Write-Synthetic $path ([Text.Encoding]::UTF8.GetBytes('SYNTHETIC:' + $name))
        $files[$name] = Row $path
    }
    if ((Join-Path $script:installRoot $longName).Length -le 260) { throw 'long path fixture not actually long' }
    $files['portable.flag'] = @{bytes=0;sha256='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
    Write-Synthetic (Join-Path $script:installRoot 'uninstall.exe') ([Text.Encoding]::UTF8.GetBytes('SYNTHETIC-NOT-EXECUTABLE'))
    $script:Installer = Join-Path $root 'synthetic-installer.bin'
    Write-Synthetic $script:Installer ([Text.Encoding]::UTF8.GetBytes('SYNTHETIC-NOT-EXECUTABLE'))
    $identity = @{schema='local-pinned-packaging/v1';status='PINNED_INPUTS_VERIFIED';public=$false;
        release_status='unreleased';ci_qualification='NOT_CLAIMED';installed_qualification='NOT_RUN';data_restore='NOT_RUN';rollback='NOT_RUN';
        build_source=@{source_commit=('a'*40);source_tree=('b'*40);source_patch_sha256=('c'*64)};
        packaging_source=@{commit=('a'*40);inventory_sha256=('d'*64)};
        inputs=@{snapshot=@{path='SYNTHETIC-ORIGINAL-SNAPSHOT';sha256=('e'*64)};
            host_receipt=@{path='SYNTHETIC-ORIGINAL-BUILD';sha256=('f'*64)};candidate_manifest=('1'*64)};
        payload=@{schema='archeaxis.tauri-portable-candidate/v1';status='ASSEMBLED';installed=$false;published=$false;
            source_patch_sha256=('c'*64);host_sha256=$files['ArcheAxis.exe'].sha256;
            core_sha256=$files['core/archeaxis-api.exe'].sha256;files=$files}}
    $script:case = @{Root=$root;Identity=$identity;IdentityPath=(Join-Path $root 'local-pinned-identity.json');
        ReceiptPath=(Join-Path $root 'packaging-receipt.json');LongName=$longName;
        Receipt=@{schema='local-pinned-packaging/v1';status='LOCAL_PACKAGING_PASS';stage='COMPLETE';exit_code=0;
            installed_qualification='NOT_RUN';installer=(Row $script:Installer)}}
    $script:RequireLocalPinnedIdentity = $true
    $script:LocalPinnedIdentityReceipt = $script:case.ReceiptPath
    $script:ExpectedInstallerSha256 = (Row $script:Installer).sha256
    $script:ExpectedHostSha256 = $files['ArcheAxis.exe'].sha256
    $script:ExpectedCoreSha256 = $files['core/archeaxis-api.exe'].sha256
    $script:ExpectedRuntimeManifestSha256 = $files['backend-runtime-manifest.json'].sha256
    Save-Identity
    $script:localPinned = Read-LocalPinnedPackaging
}
$results = [Collections.Generic.List[object]]::new()
function Test([string]$CaseLabel, [scriptblock]$Body) {
    try { New-Case; & $Body; $results.Add(@{name=$CaseLabel;status='PASS'}) }
    catch { $results.Add(@{name=$CaseLabel;status='FAIL';error=$_.Exception.Message}) }
}
function Refuse([scriptblock]$Body, [string]$Pattern) {
    $caught = $null
    try { & $Body } catch { $caught = $_.Exception.Message }
    if (-not $caught -or $caught -notmatch $Pattern) { throw "expected refusal matching $Pattern, got: $caught" }
}
Test 'valid full real filesystem payload with dotdirs and >260 path' {
    $proof = Read-InstalledLocalPinnedPayload
    if ($proof.member_count -ne 7) { throw 'unexpected payload count' }
}
Test 'default and CI-only mode guards unchanged' {
    Assert-LocalIdentityMode; Assert-LocalIdentityMode -Candidate; Assert-LocalIdentityMode -Release
}
foreach ($flags in @(@{Release=$true;Candidate=$true},@{Release=$true;Local=$true},@{Candidate=$true;Local=$true},
                     @{Release=$true;Candidate=$true;Local=$true})) {
    Test ('mutually exclusive modes ' + ($flags.Keys -join ',')) { Refuse { Assert-LocalIdentityMode @flags } 'mutually exclusive' }
}
foreach ($field in @('Receipt','ReceiptSha','InstallerSha')) {
    Test ('local input refused without local mode: '+$field) {
        $arguments=@{}; $arguments[$field]='SYNTHETIC'; Refuse { Assert-LocalIdentityMode @arguments } 'require RequireLocalPinnedIdentity'
    }
}
foreach ($field in @('ExpectedLocalPinnedIdentitySha256','ExpectedInstallerSha256','ExpectedHostSha256','ExpectedCoreSha256','ExpectedRuntimeManifestSha256')) {
    Test ('missing digest: '+$field) { Set-Variable -Name $field -Value '' -Scope Script; Refuse { Read-LocalPinnedPackaging } 'digests are mandatory' }
}
Test 'changed payload' { Write-Synthetic (Join-Path $installRoot 'ArcheAxis.exe') ([byte[]]@(1,2)); Refuse { Read-InstalledLocalPinnedPayload } 'byte count differs|sha256 differs' }
Test 'missing payload' { [IO.File]::Delete((Native (Join-Path $installRoot 'core/archeaxis-api.exe'))); Refuse { Read-InstalledLocalPinnedPayload } 'missing installed member' }
Test 'extra payload' { Write-Synthetic (Join-Path $installRoot 'unexpected.pyc') ([byte[]]@(1)); Refuse { Read-InstalledLocalPinnedPayload } 'unmanifested installed member' }
Test 'portable flag must not install' { Write-Synthetic (Join-Path $installRoot 'portable.flag') ([byte[]]@()); Refuse { Read-InstalledLocalPinnedPayload } 'unmanifested installed member' }
Test 'near-name uninstaller not ignored' { Write-Synthetic (Join-Path $installRoot 'uninstall-extra.exe') ([byte[]]@(1)); Refuse { Read-InstalledLocalPinnedPayload } 'unmanifested installed member' }
Test 'changed installer between operations' { Write-Synthetic $Installer ([byte[]]@(1)); Refuse { Assert-LocalInstallerBinding } 'byte count differs|sha256 differs' }
Test 'changed receipt between operations' { Write-Synthetic $LocalPinnedIdentityReceipt ([Text.Encoding]::UTF8.GetBytes('{}')); Refuse { Assert-LocalInstallerBinding } 'sha256 differs' }
Test 'changed identity between operations' { Write-Synthetic $case.IdentityPath ([Text.Encoding]::UTF8.GetBytes('{}')); Refuse { Assert-LocalInstallerBinding } 'byte count differs|sha256 differs' }
Test 'partial receipt is not packaging PASS' { $case.Receipt.status='LOCAL_PASS'; Save-Identity; Refuse { Read-LocalPinnedPackaging } 'incomplete' }
Test 'duplicate JSON key' {
    $raw=[IO.File]::ReadAllText($case.IdentityPath); Save-Identity ('{"schema":"local-pinned-packaging/v1",'+$raw.Substring(1))
    Refuse { Read-LocalPinnedPackaging } 'duplicate or case-aliased'
}
Test 'case-aliased payload member' {
    $raw=[IO.File]::ReadAllText($case.IdentityPath)
    $raw=$raw.Replace('"ArcheAxis.exe":', ('"archeaxis.exe":{"bytes":1,"sha256":"'+('0'*64)+'"},"ArcheAxis.exe":'))
    Save-Identity $raw; Refuse { Read-LocalPinnedPackaging } 'duplicate or case-aliased'
}
foreach ($name in @('../escape','/absolute','C:/absolute','a\file','a//file','a/./file','a/../file','tail.','tail ',"a`nfile")) {
    $memberUnderTest = $name
    Test ('unsafe member '+$memberUnderTest.Replace("`n",'[LF]')) {
        Refuse { Assert-LocalPinnedMemberName -Name $memberUnderTest } 'unsafe|noncanonical'
    }
}
Test 'literal LF codepoint reaches the production member guard' {
    $literalControlMember = "a`nfile"
    if ([int][char]$literalControlMember[1] -ne 10 -or $literalControlMember.Contains('[LF]')) {
        throw 'control fixture must contain literal U+000A, not a display label'
    }
    Refuse { Assert-LocalPinnedMemberName -Name $literalControlMember } 'unsafe local pinned member name'
}
Test 'artifact identity member refused' {
    $case.Identity.payload.files['runtime/release-identity.json']=@{bytes=1;sha256=('0'*64)}
    Save-Identity; Refuse { Read-LocalPinnedPackaging } 'artifact identity forbidden'
}
Test 'fake CI metadata refused' {
    $case.Identity.build_source.verification_ci_run_id=123; Save-Identity
    Refuse { Read-LocalPinnedPackaging } 'CI identity fields are forbidden'
}
Test 'public identity refused' { $case.Identity.public=$true; Save-Identity; Refuse { Read-LocalPinnedPackaging } 'invalid non-public' }
Test 'enumeration errors propagate' {
    function Get-ChildItem { param($LiteralPath,[switch]$Force,[switch]$Recurse,$ErrorAction); throw 'SYNTHETIC_ENUMERATION_DENIED' }
    Refuse { Read-InstalledLocalPinnedPayload } 'SYNTHETIC_ENUMERATION_DENIED'
}
if ($IsWindows) {
    Test 'real hardlink rejected' {
        $target=Join-Path $case.Root 'hardlink-source.bin'; Write-Synthetic $target ([byte[]]@(9))
        $link=Join-Path $installRoot 'hardlink.bin'
        $null=New-Item -ItemType HardLink -Path (Native $link) -Target (Native $target)
        Refuse { Assert-LocalPinnedFile $link (Row $target).sha256 } 'independent regular file'
    }
    New-Case
    $link=Join-Path $installRoot 'linked-file'; $target=Join-Path $installRoot 'ArcheAxis.exe'
    try { $null=[IO.File]::CreateSymbolicLink((Native $link), (Native $target)) }
    catch {
        if ($_.Exception.Message -notmatch 'privilege|权限|特权|access.*denied|administrator|not.*held') { throw }
        $results.Add(@{name='real symlink rejected';status='SKIP';reason='symlink permission unavailable'})
    }
    if (Test-Path -LiteralPath $link) {
        try { Refuse { Read-InstalledLocalPinnedPayload } 'reparse point'; $results.Add(@{name='real symlink rejected';status='PASS'}) }
        catch { $results.Add(@{name='real symlink rejected';status='FAIL';error=$_.Exception.Message}) }
    }
}
$failed=@($results|Where-Object status -eq 'FAIL').Count
$report=@{schema='aaos.local-pinned-verifier-functions-test/v1';scope='SYNTHETIC_FUNCTIONS_ONLY_NO_INSTALLATION';
    verifier_sha256=(Get-FileHash $Proposal).Hash.ToLowerInvariant();fixture_root=$fixtureRoot;
    passed=@($results|Where-Object status -eq 'PASS').Count;skipped=@($results|Where-Object status -eq 'SKIP').Count;
    failed=$failed;results=$results}
Write-Json (Join-Path $fixtureRoot 'test-results.json') $report
$report|ConvertTo-Json -Depth 8
if ($failed) { exit 1 }
