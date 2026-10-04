$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Add-Type -Path @((Join-Path $repoRoot 'apps/ArcheAxis.Desktop/MachineLearningJourney.cs'),(Join-Path $repoRoot 'apps/ArcheAxis.Desktop/CourseLessonReadback.cs')) -ReferencedAssemblies @((Join-Path $PSHOME 'ref/System.Text.Json.dll'),(Join-Path $PSHOME 'ref/System.Memory.dll'),(Join-Path $PSHOME 'ref/System.Collections.dll')) -CompilerOptions '/nullable:enable'
function Json($value) { return [System.Text.Json.JsonDocument]::Parse(($value | ConvertTo-Json -Depth 30 -Compress)) }
function Reject($action) { $rejected=$false; try { & $action } catch { $rejected=$true }; if (!$rejected) { throw 'expected refusal' } }
function Fixture {
    $artifact=@{artifact_id='lesson1';artifact_type='lesson';title='actual title';status='candidate';interactive=$false;renderer='native-lesson';renderer_version='1.0.0';source_ids=@('source1');knowledge_ids=@('component1')}
    $manifest=@{manifest_id='course1';title='actual title';status='candidate';artifacts=@($artifact);knowledge_components=@(@{component_id='component1';title='actual title';kind='concept';statement='real canonical body';source_ids=@('source1')});learning_objectives=@(@{objective_id='objective1';title='Explain';statement='explain and cite source';knowledge_component_ids=@('component1')})}
    $course=@{manifest=$manifest;status='candidate';stale=$false;human_review_required=$true;bindings=@(@{component_id='component1';knowledge_id='knowledge1';knowledge_version='version1';source_id='source1';source_revision='revision1';stale=$false})}
    $generated=@{course=$course;human_review_required=$true;suggested_learning_item=@{item_key='course:course1:artifact:lesson1';course_id='course1';artifact_id='lesson1';knowledge_id='knowledge1';knowledge_version='version1';source_id='source1';source_revision='revision1'}}
    $content="# actual title`nManifest: ``course1```nArtifact: ``lesson1```n- ``source1```n- ``component1`` (concept): actual title — real canonical body`n- ``objective1``: Explain — explain and cite source`n"
    $render=@{course=$course;derived_only=$true;canonical_bindings_verified=$true;human_review_required=$true;render=@{schema='archeaxis.general-course-worker/v1';status='DERIVED';derived_only=$true;human_review_required=$true;manifest=$manifest;artifact=$artifact;lesson=@{content=$content}}}
    return @{generated=$generated;course=$course;render=$render}
}
function Generated($value) { $doc=Json $value; try { return [ArcheAxis.Desktop.CourseLessonReadback]::Generated($doc.RootElement,'knowledge1') } finally { $doc.Dispose() } }
function Rendered($lesson,$value) { $doc=Json $value; try { return $lesson.ReadRendered($doc.RootElement) } finally { $doc.Dispose() } }
$fixture=Fixture; $lesson=Generated $fixture.generated
$read=Json $fixture.course
try { $lesson=$lesson.ReadStored($read.RootElement) } finally { $read.Dispose() }
$actual=Rendered $lesson $fixture.render
if ($actual.ItemKey -ne 'course:course1:artifact:lesson1' -or !$actual.LessonText.Contains('real canonical body') -or !$actual.LessonText.Contains('explain and cite source') -or $actual.LessonText.Contains('component1')) { throw 'display must preserve actual text without diagnostic IDs' }
$fixture.generated.suggested_learning_item.knowledge_version='wrong'; Reject { Generated $fixture.generated }
$fixture=Fixture; $fixture.course.stale=$true; Reject { Generated $fixture.generated }
$fixture=Fixture; $fixture.generated.suggested_learning_item.item_key='desktop-learning-knowledge1'; Reject { Generated $fixture.generated }
$fixture=Fixture; $fixture.render.render.lesson.content='invented lesson'; Reject { Rendered $lesson $fixture.render }
$fixture=Fixture; $fixture.render.render.artifact.title='changed by worker'; Reject { Rendered $lesson $fixture.render }
$fixture=Fixture; $fixture.render.canonical_bindings_verified=$false; Reject { Rendered $lesson $fixture.render }
$fixture=Fixture; $fixture.render.course.bindings[0].source_revision='changed'; Reject { Rendered $lesson $fixture.render }
$assessment=@{item_key=$lesson.ItemKey;knowledge_id='knowledge1';knowledge_version='version1';assessment_id='assessment1'}
$doc=Json $assessment
try { [ArcheAxis.Desktop.CourseLessonReadback]::ValidateAssessment($doc.RootElement,$lesson.ItemKey,'knowledge1','version1') } finally { $doc.Dispose() }
$assessment.knowledge_version='wrong'; $doc=Json $assessment
try { Reject { [ArcheAxis.Desktop.CourseLessonReadback]::ValidateAssessment($doc.RootElement,$lesson.ItemKey,'knowledge1','version1') } } finally { $doc.Dispose() }
Write-Output 'COURSE READBACK PASS'
