$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Add-Type -Path (Join-Path $repoRoot 'apps/ArcheAxis.Desktop/MachineLearningJourney.cs') -ReferencedAssemblies @((Join-Path $PSHOME 'ref/System.Text.Json.dll'), (Join-Path $PSHOME 'ref/System.Memory.dll'), (Join-Path $PSHOME 'ref/System.Collections.dll')) -CompilerOptions '/nullable:enable'
function Element($value) {
    $json = [System.Text.Json.JsonDocument]::Parse(($value | ConvertTo-Json -Depth 20 -Compress))
    try { return $json.RootElement.Clone() } finally { $json.Dispose() }
}
function Reject($action) {
    $rejected = $false
    try { & $action } catch { $rejected = $true }
    if (!$rejected) { throw 'expected refusal' }
}
$answer = @{ schema='archeaxis.machine-answer/v1'; answer_id='a1'; knowledge_id='k1'; question='original question'; answer=@{answer='original answer'} }
$journey = [ArcheAxis.Desktop.MachineLearningJourney]::new()
Reject { $journey.RetestRequest() }
Reject { $journey.CaptureAnswer((Element $answer), 'k2', 'original question') }
$journey.CaptureAnswer((Element $answer), 'k1', 'original question')
$request = Element $journey.CorrectionRequest('human corrected answer', 'human found error')
if ($request.GetProperty('answer_id').GetString() -cne 'a1' -or $request.GetProperty('question').GetString() -cne 'original question') { throw 'correction request drift' }
$correction = @{ schema='archeaxis.machine-correction/v1'; answer_id='a1'; corrects_knowledge_id='k1'; question='original question'; machine_answer='original answer'; corrected_answer='human corrected answer'; error_note='human found error'; correction_candidate_id='c1'; failed_task_id='f1' }
$wrong = $correction.Clone(); $wrong.answer_id = 'a2'
Reject { $journey.CaptureCorrection((Element $wrong), 'human corrected answer', 'human found error') }
$journey.CaptureCorrection((Element $correction), 'human corrected answer', 'human found error')
Reject { $journey.RetestRequest() }
Reject { $journey.MarkCorrectionAccepted((Element @{knowledge_id='c1';status='candidate'}), (Element @{knowledge_id='c1';active=$true})) }
Reject { $journey.MarkCorrectionAccepted((Element @{knowledge_id='c1';status='accepted'}), (Element @{knowledge_id='c1';active=$false})) }
$journey.MarkCorrectionAccepted((Element @{knowledge_id='c1';status='accepted'}), (Element @{knowledge_id='c1';active=$true}))
$retestRequest = Element $journey.RetestRequest()
if ($retestRequest.GetProperty('retest_of').GetString() -cne 'f1' -or $retestRequest.GetProperty('knowledge_id').GetString() -cne 'c1' -or $retestRequest.GetProperty('question').GetString() -cne 'original question') { throw 'retest request drift' }
$original = $answer.Clone(); $original.correction = $correction
$retest = @{schema='archeaxis.machine-retest/v1'; retest_task_id='r1'; answer_id='r1'; retest_of='f1'; knowledge_id='c1';question='original question';answer=@{answer='second answer'};prior=@{conditions=$original}}
$badRetest = $retest.Clone(); $badRetest.question = 'different question'
Reject { $journey.CaptureRetest((Element $badRetest)) }
$journey.CaptureRetest((Element $retest))
if ($journey.RetestText -cne 'second answer') { throw 'lost retest answer' }
$task = @{ task_id='r1'; scope='runtime.retest'; conditions=($retest | ConvertTo-Json -Depth 20 -Compress) }
$restored = [ArcheAxis.Desktop.MachineLearningJourney]::FromTask((Element $task))
if ($restored.AnswerText -cne 'original answer' -or $restored.CorrectedAnswer -cne 'human corrected answer' -or $restored.RetestText -cne 'second answer') { throw 'lost restart content' }
if ($restored.CorrectionAccepted) { throw 'acceptance must be re-read, never inferred from restart' }
$nextRequest = Element $restored.CorrectionRequest('second human correction', 'error in retest answer')
if ($nextRequest.GetProperty('answer_id').GetString() -cne 'r1' -or $nextRequest.GetProperty('knowledge_id').GetString() -cne 'c1' -or $nextRequest.GetProperty('machine_answer').GetString() -cne 'second answer') { throw 'next correction must bind the retest answer' }
$nextCorrection = @{schema='archeaxis.machine-correction/v1'; answer_id='r1'; corrects_knowledge_id='c1'; question='original question'; machine_answer='second answer'; corrected_answer='second human correction';error_note='error in retest answer';correction_candidate_id='c2';failed_task_id='f2'}
$restored.CaptureCorrection((Element $nextCorrection), 'second human correction', 'error in retest answer')
if ($restored.AnswerId -cne 'r1' -or $restored.KnowledgeId -cne 'c1') { throw 'next round identity drift' }
if (!$restored.HistoryText.Contains('original answer')) { throw 'lost earlier round history' }
Reject { $restored.RetestRequest() }
$restored.MarkCorrectionAccepted((Element @{knowledge_id='c2';status='accepted'}), (Element @{knowledge_id='c2';active=$true}))
$secondOriginal = $retest.Clone(); $secondOriginal.correction = $nextCorrection
$secondRetest = @{schema='archeaxis.machine-retest/v1'; retest_task_id='r2';answer_id='r2';retest_of='f2';knowledge_id='c2';question='original question';answer=@{answer='third answer'};prior=@{conditions=$secondOriginal}}
$restored.CaptureRetest((Element $secondRetest))
$secondTask = @{task_id='r2';scope='runtime.retest';conditions=($secondRetest | ConvertTo-Json -Depth 30 -Compress)}
$secondRestart = [ArcheAxis.Desktop.MachineLearningJourney]::FromTask((Element $secondTask))
if ($secondRestart.AnswerId -cne 'r1' -or $secondRestart.RetestText -cne 'third answer' -or !$secondRestart.HistoryText.Contains('original answer')) { throw 'multi-round restart drift' }
$task.task_id = 'wrong-id'
Reject { [ArcheAxis.Desktop.MachineLearningJourney]::FromTask((Element $task)) }
Write-Output 'JOURNEY PASS: receipt identity, human acceptance, same-question retest, restart content and negative cases'
