$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Add-Type -Path @((Join-Path $repoRoot 'apps/ArcheAxis.Desktop/MachineLearningJourney.cs'),(Join-Path $repoRoot 'apps/ArcheAxis.Desktop/SemanticSearchReadback.cs')) -ReferencedAssemblies @((Join-Path $PSHOME 'ref/System.Text.Json.dll'),(Join-Path $PSHOME 'ref/System.Memory.dll'),(Join-Path $PSHOME 'ref/System.Collections.dll')) -CompilerOptions '/nullable:enable'
function Read($value) {
    $json = [System.Text.Json.JsonDocument]::Parse(($value | ConvertTo-Json -Depth 20 -Compress))
    try { return [ArcheAxis.Desktop.SemanticSearchSnapshot]::Read($json.RootElement,'question') } finally { $json.Dispose() }
}
function Reject($action) { $rejected=$false;try { & $action } catch { $rejected=$true };if (!$rejected) { throw 'expected refusal' } }
$doc=@{schema='archeaxis.semantic-search/v1';q='question';status='PARTIAL';complete=$false;candidate_count=2;
 candidates=@(@{knowledge_id='k1';knowledge_version='v1';body='real first body';source_id='s1';status='accepted'},@{knowledge_id='k2';knowledge_version='v2';body='real second body';source_id=$null;status='accepted'});
 embedding=@{complete=$true;rank=@(@{knowledge_id='k2';knowledge_version='v2';score=.8},@{knowledge_id='k1';knowledge_version='v1';score=.4})};reranker=@{complete=$false;rank=@()}}
$snapshot=Read $doc
if ($snapshot.Status -ne 'PARTIAL' -or $snapshot.Hits.Count -ne 2 -or $snapshot.Hits[0].Body -ne 'real second body' -or $null -ne $snapshot.Hits[0].SourceId) { throw 'partial ranking must join actual knowledge bodies in rank order' }
$doc.complete=$true;Reject { Read $doc };$doc.complete=$false
$doc.embedding.rank[0].knowledge_version='wrong';Reject { Read $doc };$doc.embedding.rank[0].knowledge_version='v2'
$doc.embedding.rank[0].knowledge_id='not-submitted';Reject { Read $doc };$doc.embedding.rank[0].knowledge_id='k2'
$doc.q='different';Reject { Read $doc };$doc.q='question'
$doc.candidates[0].status='candidate';Reject { Read $doc };$doc.candidates[0].status='accepted'
$doc.embedding.complete=$false;$doc.embedding.rank=@();$doc.status='UNAVAILABLE'
$snapshot=Read $doc
if ($snapshot.Hits.Count -ne 0) { throw 'unavailable ranking must not display the entire corpus as search hits' }
$doc.status='EMPTY';Reject { Read $doc }
Write-Output 'SEMANTIC READBACK PASS'
