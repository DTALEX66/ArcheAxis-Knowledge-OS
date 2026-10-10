# Execute the same pure C# answer-binding code used by the Avalonia shell.
# No GUI, learner records, or external services are involved.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$sourcePath = Join-Path $repoRoot 'apps/ArcheAxis.Desktop/LearningAnswerReadback.cs'
Add-Type -Path $sourcePath -ReferencedAssemblies ([System.Text.Json.JsonDocument].Assembly.Location) -CompilerOptions '/nullable:enable'

$cases = @(
    @{ Name = 'matching assessment'; Outcome = '{"assessment_id":"a1","answer":"saved answer"}'; Active = 'a1'; Expected = 'saved answer' },
    @{ Name = 'previous knowledge revision'; Outcome = '{"assessment_id":"a0","answer":"old answer"}'; Active = 'a1'; Expected = $null },
    @{ Name = 'missing assessment binding'; Outcome = '{"answer":"unbound answer"}'; Active = 'a1'; Expected = $null },
    @{ Name = 'assessment unavailable'; Outcome = '{"assessment_id":"a1","answer":"saved answer"}'; Active = $null; Expected = $null },
    @{ Name = 'empty assessment identity'; Outcome = '{"assessment_id":"","answer":"saved answer"}'; Active = ''; Expected = $null },
    @{ Name = 'blank answer'; Outcome = '{"assessment_id":"a1","answer":"  "}'; Active = 'a1'; Expected = $null },
    @{ Name = 'invalid answer type'; Outcome = '{"assessment_id":"a1","answer":123}'; Active = 'a1'; Expected = $null },
    @{ Name = 'invalid assessment type'; Outcome = '{"assessment_id":123,"answer":"saved answer"}'; Active = 'a1'; Expected = $null },
    @{ Name = 'preserve answer bytes'; Outcome = '{"assessment_id":"a1","answer":"  saved answer\n"}'; Active = 'a1'; Expected = "  saved answer`n" },
    @{ Name = 'malformed outcome shape'; Outcome = '[]'; Active = 'a1'; Expected = $null }
)

foreach ($case in $cases) {
    $document = [System.Text.Json.JsonDocument]::Parse($case.Outcome)
    try {
        $actual = [ArcheAxis.Desktop.LearningAnswerReadback]::AnswerForAssessment($document.RootElement, $case.Active)
        if ($actual -cne $case.Expected) {
            throw "FAIL: $($case.Name)"
        }
        Write-Output "PASS: $($case.Name)"
    } finally {
        $document.Dispose()
    }
}
